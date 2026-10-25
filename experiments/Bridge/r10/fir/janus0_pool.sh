#!/bin/bash
# Bridge v9 (Round 10), Fir job F1: Janus 0 (icx4, D34) predicts the allowed pool volumes, and TotalSegmentator makes
# their aortas (A1's ostium of record). These are the A31 inputs for wave 1 (model-vs-read, s_d, rho) and the baseline
# every Janus-1 fine-tune is compared with on the D35 decision set. Nothing is scored here and no read is opened.
#
# Allowed = not sealed (D27/D32) and not reserved (the seal's 200/250 steps): experiments/Bridge/r10/allowed_inputs.py.
# Runs on Fir after icx4: reuses $HOME/icx14-venv (nnU-Net + the icx4 trainer), $HOME/icx4-tseg-venv and the
# TotalSegmentator weights icx4 downloaded into $SCRATCH/icx4/totalseg.
#
#   cd $SCRATCH/asclepius/repo && git pull --ff-only
#   bash experiments/Bridge/r10/fir/janus0_pool.sh prepare     # login node: list, fetch (~19 GB), stage; no GPU
#   bash experiments/Bridge/r10/fir/janus0_pool.sh submit      # one job: h100:1, 12 cores, 280G, 6 h, def-aso22
#   bash experiments/Bridge/r10/fir/janus0_pool.sh status
set -euo pipefail
MODE="${1:-}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
W="${JANUS0_POOL_W:-$SCRATCH/janus0-pool}"
ICX4W="${ICX4_W:-$SCRATCH/icx4}"
VENV="${ICX4_VENV:-$HOME/icx14-venv}"
TSEG_VENV="${ICX4_TSEG_VENV:-$HOME/icx4-tseg-venv}"
PLANS=nnUNetResEncUNetPlans_60G_iso05
TR=nnUNetTrainerICX4
say() { printf '[janus0-pool] %s\n' "$*"; }
die() { printf '[janus0-pool] ERROR: %s\n' "$*" >&2; exit 1; }
[ -n "${SCRATCH:-}" ] || die '$SCRATCH is not set'
CKPT="$ICX4W/nnunet_results/Dataset715_ICX4/${TR}__${PLANS}__3d_fullres/fold_0/checkpoint_final.pth"

case "$MODE" in
prepare)
    [ -f "$CKPT" ] || die "Janus 0 checkpoint not found at $CKPT"
    mkdir -p "$W/in" "$W/ct" "$W/pred" "$W/aorta" "$W/logs"
    python3 "$REPO/experiments/Bridge/r10/allowed_inputs.py" --out "$W" || die 'allowed list refused'
    python3 "$REPO/trillium/totalseg/lib/fetch.py" "$W/inputs.json" "$W/ct"     # Girder login once; resumable
    n=0
    while read -r v; do
        [ -n "$v" ] || continue
        [ -s "$W/ct/$v" ] || die "missing CT after fetch: $v (re-run prepare)"
        ln -sf "$W/ct/$v" "$W/in/${v%.nii.gz}_0000.nii.gz"; n=$((n + 1))
    done < "$W/volumes.txt"
    say "staged $n volumes in $W/in (expect 212)"
    ;;
submit)
    [ -d "$W/in" ] || die 'run prepare first'
    cat > "$W/job.sh" <<EOF
#!/bin/bash
#SBATCH --job-name=janus0-pool
#SBATCH --account=${ACCOUNT:-def-aso22}
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=12
#SBATCH --mem=280G
#SBATCH --time=06:00:00
#SBATCH --output=$W/logs/slurm-%j.out
set -uo pipefail
module load StdEnv/2023 python/3.11.5 cuda/12.6 2>/dev/null || true
source "$VENV/bin/activate"
export nnUNet_raw="$ICX4W/nnunet_raw" nnUNet_preprocessed="$ICX4W/nnunet_preprocessed" nnUNet_results="$ICX4W/nnunet_results"
export nnUNet_compile=f PYTHONUNBUFFERED=1
nnUNetv2_predict -i "$W/in" -o "$W/pred" -d 715 -c 3d_fullres -f 0 -tr $TR -p $PLANS -chk checkpoint_final.pth \\
    --disable_tta --continue_prediction -npp 6 -nps 6 -device cuda > "$W/logs/predict.log" 2>&1
deactivate
source "$TSEG_VENV/bin/activate"
export TOTALSEG_HOME_DIR="$ICX4W/totalseg"
python - <<'PY' > "$W/logs/aorta.log" 2>&1
import os, numpy as np, nibabel as nib
from totalsegmentator.python_api import totalsegmentator
W = "$W"
for v in open(os.path.join(W, 'volumes.txt')).read().split():
    out = os.path.join(W, 'aorta', v.replace('.nii.gz', '_aorta.nii.gz'))
    if os.path.exists(out):
        continue
    try:   # as trillium/icx4/lib/aorta.py: binary mask on the CT's own grid, never empty
        ct = os.path.join(W, 'ct', v)
        img = nib.load(ct)
        res = totalsegmentator(ct, None, fast=True, roi_subset=['aorta'], device='gpu',
                               nr_thr_resamp=2, nr_thr_saving=1, quiet=True)
        a = (np.asanyarray(res.dataobj) > 0).astype(np.uint8)
        if a.shape != img.shape[:3] or not a.any():
            raise ValueError(f'aorta grid {a.shape} vs CT {img.shape[:3]} or empty')
        nib.save(nib.Nifti1Image(a, img.affine), out)
        print('ok', v, flush=True)
    except Exception as e:
        print('FAILED', v, repr(e), flush=True)
PY
echo "pred \$(ls "$W/pred"/*.nii.gz 2>/dev/null | wc -l) aorta \$(ls "$W/aorta" | wc -l) of \$(wc -l < "$W/volumes.txt")"
EOF
    grep SBATCH "$W/job.sh"
    sbatch "$W/job.sh"
    ;;
status)
    squeue -u "$USER" --name janus0-pool || true
    echo "pred $(ls "$W/pred"/*.nii.gz 2>/dev/null | wc -l) aorta $(ls "$W/aorta" 2>/dev/null | wc -l) of $(wc -l < "$W/volumes.txt")"
    ;;
*) die "usage: $0 prepare|submit|status" ;;
esac
