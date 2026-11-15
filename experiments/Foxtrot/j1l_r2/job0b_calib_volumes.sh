#!/bin/bash
# Foxtrot, Janus 1-L Round 2, Job 0b: Janus 0's foreground volumes on the 60 label-free calibration images
# (results/calib60.json: open ImageCAS quality-0 cases; never labelled here, never trained on, not sealed, not in the
# 620 or the locked 100). No label is read. Only per-case voxel counts at each threshold are kept
# ($SCRATCH/j1l_job0b/vol_janus0.json); the probability files are deleted afterwards.
# It needs nothing from Job 0 and can run before, after or beside it. About 1 GPU-h.
# Submit from the Trillium GPU login node:  sbatch job0b_calib_volumes.sh
#SBATCH --job-name=j1l-job0b
#SBATCH --account=def-aso22
#SBATCH --gpus-per-node=1
#SBATCH --time=03:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
R=$SCRATCH/asclepius/repo
J0=$SCRATCH/janus0                      # Step T
W=$SCRATCH/j1l_job0b
F=$R/experiments/Foxtrot/j1l_r2
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate
export nnUNet_raw=$W/raw nnUNet_preprocessed=$W/pre nnUNet_results=$J0/nnunet_results nnUNet_compile=f
mkdir -p $W/in $W/probs
python - "$F/results/calib60.json" "$R/trillium/sealed_test.json" "$R/experiments/Crucible/j1l_r1/lists.json" <<'PY'
import json, sys
C = json.load(open(sys.argv[1]))['calib60']; S = json.load(open(sys.argv[2])); L = json.load(open(sys.argv[3]))
bad = set(C) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']) | set(L['locked100']) | set(L['train620']))
assert len(C) == 60 and not bad, bad
PY
for c in $(python -c "import json;print(' '.join(json.load(open('$F/results/calib60.json'))['calib60']))"); do
  ln -sf $SCRATCH/asclepius/cases/$c/ct.nii.gz $W/in/${c}_0000.nii.gz
done
nnUNetv2_predict -i $W/in -o $W/probs -d 715 -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 \
  -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth --disable_tta --save_probabilities \
  -npp 6 -nps 6 -device cuda
python $F/t_transfer.py volumes --probs $W/probs --out $W/vol_janus0.json --np 6
rm -f $W/probs/*.npz $W/probs/*.pkl
sha256sum $W/vol_janus0.json
