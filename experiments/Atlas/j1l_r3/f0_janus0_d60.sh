#!/bin/bash
# Atlas, Janus 1-L round 3, F0: Janus 0's label-free pass on D60, the reference of Rule T (L-A15), run beside Job 0.
#
# D60 = experiments/Delta/j1l_r2/drift60.json (60 ImageCAS quality-0 CTs; not sealed, not declared development, not in
# the 620 or the locked 100). D49 Q-R2-2: CT images only; no label and no original ImageCAS mask is read (fetch_cases.py
# without --masks fetches CTs only); nothing is trained on them. This job reads no label at all.
# Output: $SCRATCH/j1l_f0/probs (nnU-Net probabilities) and thr/t<t>/ for Rule W's five thresholds (t* is one of them),
# plus thr/voxels.json (predicted voxel counts per case and t; the F0 check of Atlas v3 §7).
# About 1 GPU-h. Needs Step T only. Submit from the Trillium GPU login node:  sbatch f0_janus0_d60.sh
#SBATCH --job-name=j1l-f0
#SBATCH --account=def-aso22
#SBATCH --gpus-per-node=1
#SBATCH --time=02:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
R=$SCRATCH/asclepius/repo
J0=$SCRATCH/janus0
W=$SCRATCH/j1l_f0
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate
export nnUNet_raw=$W/raw nnUNet_preprocessed=$W/pre nnUNet_results=$J0/nnunet_results nnUNet_compile=f
mkdir -p $W/in $W/probs
python - "$R" <<'PY'
import json, sys
R = sys.argv[1]
D = json.load(open(f'{R}/experiments/Delta/j1l_r2/drift60.json'))['drift60']
S = json.load(open(f'{R}/trillium/sealed_test.json'))
L = json.load(open(f'{R}/experiments/Crucible/j1l_r1/lists.json'))
bad = set(D) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']) | set(L['locked100']) | set(L['train620']))
assert len(D) == 60 and not bad, bad
PY
for c in $(python -c "import json;print(' '.join(json.load(open('$R/experiments/Delta/j1l_r2/drift60.json'))['drift60']))"); do
  ln -sf $SCRATCH/asclepius/cases/$c/ct.nii.gz $W/in/${c}_0000.nii.gz
done
nnUNetv2_predict -i $W/in -o $W/probs -d 715 -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 \
  -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth --disable_tta --save_probabilities \
  -npp 6 -nps 6 -device cuda
python $R/experiments/Crucible/j1l_r1/threshold_export.py --probs $W/probs --out $W/thr --t 0.5 0.45 0.4 0.35 0.3 --np 12
python - $W <<'PY'
import json, sys
W = sys.argv[1]
v = json.load(open(f'{W}/thr/voxels.json'))
for t in ('0.50', '0.45', '0.40', '0.35', '0.30'):
    print(f'[f0] D60 t={t}: {sum(r[t] == 0 for r in v)} of {len(v)} cases with an empty prediction')
PY
