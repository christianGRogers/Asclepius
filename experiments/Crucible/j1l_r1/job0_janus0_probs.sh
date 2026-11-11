#!/bin/bash
# Crucible, Janus 1-L Round 1, Job 0: Janus 0's class probabilities on 160 non-sealed ImageCAS-X cases, a foreground
# threshold chosen on the 60 tuning cases, and Janus 0's argmax and thresholded scores on both sets.
#
# Cases (experiments/Crucible/j1l_r1/lists.json): tuning60 (dev-44 + 16 of open-36, never trained on by Janus 0;
# D45 sends them to training) and locked100 (val 80 + 20 of open-36). No sealed case: the list is checked against
# trillium/sealed_test.json before anything runs, and threshold_export.py refuses a sealed id again.
# Locked 100: only Janus 0's *argmax* score at t = 0.50 is computed here (the gate's baseline). Its thresholded
# exports are written but NOT scored until the gate (Crucible v1 section 5), so t is never chosen on the locked 100.
#
# Submit from the Trillium GPU login node (trillium-gpu.alliancecan.ca):  sbatch job0_janus0_probs.sh
#SBATCH --job-name=j1l-job0
#SBATCH --account=def-aso22
#SBATCH --gpus-per-node=1
#SBATCH --time=06:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
R=$SCRATCH/asclepius/repo
J0=$SCRATCH/janus0                      # copied from Fir (Crucible v1 section 6, step T)
W=$SCRATCH/j1l_job0
E=$R/experiments/Crucible/j1l_r1
MODEL=$J0/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate
export nnUNet_raw=$W/raw nnUNet_preprocessed=$W/pre nnUNet_results=$J0/nnunet_results nnUNet_compile=f
mkdir -p $W/in $W/probs $W/scores
python - "$E/lists.json" "$R/trillium/sealed_test.json" <<'PY'
import json, sys
L = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
bad = set(L['job0']) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']))
assert not bad and len(L['job0']) == 160, bad
PY
for c in $(python -c "import json;print(' '.join(json.load(open('$E/lists.json'))['job0']))"); do
  ln -sf $SCRATCH/asclepius/cases/$c/ct.nii.gz $W/in/${c}_0000.nii.gz
done
# 1. Janus 0, as in icx4's job (no TTA), plus the probabilities. About 1-1.5 GPU-h for 160 cases.
nnUNetv2_predict -i $W/in -o $W/probs -d 715 -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 \
  -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth --disable_tta --save_probabilities \
  -npp 6 -nps 6 -device cuda
# 2. Thresholded exports (CPU).
python $E/threshold_export.py --probs $W/probs --out $W/thr --t 0.5 0.45 0.4 0.35 0.3 --np 12
# 3. Splits files the r9 scorer reads ('val' = the cases to score), and CT paths for its A26-identical scoring.
python - "$E/lists.json" "$W" "$SCRATCH/asclepius/cases" <<'PY'
import json, sys
L = json.load(open(sys.argv[1])); W = sys.argv[2]; C = sys.argv[3]
json.dump({'val': L['tuning60']}, open(f'{W}/split_tuning60.json', 'w'))
json.dump({'val': L['locked100']}, open(f'{W}/split_locked100.json', 'w'))
json.dump({'cases': {c: {'ct': f'{C}/{c}/ct.nii.gz'} for c in L['job0']}}, open(f'{W}/layout.json', 'w'))
PY
SC="python $R/experiments/Atlas/r9_score_icx4.py --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json --set val --np 20"
for t in 0.50 0.45 0.40 0.35 0.30; do
  $SC --pred $W/thr/t$t --splits $W/split_tuning60.json --out $W/scores/tuning60_t$t.json > /dev/null
done
python $E/decide.py select --scores t0.50=$W/scores/tuning60_t0.50.json t0.45=$W/scores/tuning60_t0.45.json \
  t0.40=$W/scores/tuning60_t0.40.json t0.35=$W/scores/tuning60_t0.35.json t0.30=$W/scores/tuning60_t0.30.json \
  > $W/select.json
# 4. The gate's baseline: Janus 0 argmax on the locked 100 (its val-80 part must reproduce 0.909 on #43).
$SC --pred $W/thr/t0.50 --splits $W/split_locked100.json --out $W/scores/locked100_janus0_argmax.json > /dev/null
python - $W <<'PY'
import json, sys
W = sys.argv[1]; s = json.load(open(f'{W}/select.json'))
print('[job0] chosen t =', s['chosen_t'])
for t, v in s['per_threshold'].items():
    print(f"[job0] tuning60 t={t}: tF1 {v['tf1']:.4f} Dice {v['dice']:.4f} FP {v['fp']:.2f} qualifies {v['qualifies']}")
b = json.load(open(f'{W}/scores/locked100_janus0_argmax.json'))['summary']
print('[job0] locked100 Janus 0 argmax: decisive macro', b.get('decisive_macro_tf1'), b.get('decisive_macro_tf1_ci'),
      'Dice', b['dice_mean'].get('tree'))
PY
