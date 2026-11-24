#!/bin/bash
# Delta v3, Janus 1-L round 3 (#302, D50): the short Trillium identity check, needed before a1/a2 train when Job 0
# ran on Fir. Janus 0 (Step T's copy in $SCRATCH/janus0, SHA256SUMS verified) re-predicts the locked 100 on Trillium,
# exactly as Job 0 does (no TTA, checkpoint_final, nnUNet_compile=f), with probabilities saved.
#  * L0 reads only its val-80 part: decisive macro 0.909 +- 0.003, each class within 0.01 of Fir's, and >= 95 % of
#    cases within 0.01 of Fir's own predictions ($J0/pred_fir).
#  * Its locked-100 argmax export is the decision baseline (Delta v3 §6.3) and its probabilities give Janus 0 at t_C
#    (the share-sentence report). Nothing else on the locked 100 is scored here.
# If Job 0 itself ran on Trillium, its L0 is this check and this job is not needed.
# Submit from trillium-gpu.scinet.utoronto.ca:  sbatch l0_trillium.sh
#SBATCH --job-name=j1l-l0t
#SBATCH --account=def-aso22
#SBATCH --gpus-per-node=1
#SBATCH --time=03:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
R=$SCRATCH/asclepius/repo; J0=$SCRATCH/janus0; W=$SCRATCH/j1l_l0t; E=$R/experiments/Crucible/j1l_r1
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate
export nnUNet_raw=$W/raw nnUNet_preprocessed=$W/pre nnUNet_results=$J0/nnunet_results nnUNet_compile=f
mkdir -p $W/in $W/probs $W/scores
python - "$E/lists.json" "$R/trillium/sealed_test.json" "$W" "$SCRATCH/asclepius/cases" <<'PY'
import json, sys
L = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2])); W = sys.argv[3]; C = sys.argv[4]
lk = L['locked100']
assert len(lk) == 100 and not set(lk) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']))
val80 = [c for c in lk if c not in L['locked20_of_open36']]
assert len(val80) == 80
json.dump({'val': val80}, open(f'{W}/split_val80.json', 'w'))
json.dump({'val': lk}, open(f'{W}/split_locked100.json', 'w'))
json.dump({'cases': {c: {'ct': f'{C}/{c}/ct.nii.gz'} for c in lk}}, open(f'{W}/layout.json', 'w'))
open(f'{W}/ids.txt', 'w').write(' '.join(lk))
PY
for c in $(cat $W/ids.txt); do ln -sf $SCRATCH/asclepius/cases/$c/ct.nii.gz $W/in/${c}_0000.nii.gz; done
nnUNetv2_predict -i $W/in -o $W/probs -d 715 -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 \
  -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth --disable_tta --save_probabilities \
  -npp 6 -nps 6 -device cuda
python $E/threshold_export.py --probs $W/probs --out $W/thr --t 0.5 --np 12
python $R/experiments/Atlas/r9_score_icx4.py --pred $W/thr/t0.50 --pair $J0/pred_fir --icx $J0/icx --aorta $J0/aorta \
  --layout $W/layout.json --splits $W/split_val80.json --set val --np 20 --out $W/scores/identity_val80_trillium.json
echo "[l0t] done; post the summary and paired blocks above"
