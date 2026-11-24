#!/bin/bash
# Foxtrot, Janus 1-L round 3: J0T, Janus 0 on Trillium (D50's identity check, plus Rule T's reference).
#
# D50: if Job 0 ran on Fir, L0 there is a determinism check only, and "before a1/a2 train on Trillium, a short identity
# check runs there". This job is that check. It also does the two Janus 0 predictions the plan needs on Trillium, so
# the candidate and everything it is compared with come from one cluster and one software stack:
#   1. Janus 0 re-predicts the locked 100 and D60 on Trillium (no TTA, probabilities saved), as Job 0 does.
#   2. L0-T: Trillium's val-80 argmax against Fir's own predictions ($J0/pred_fir), all three L0 clauses
#      (l0_check.py --mode trillium-identity). It exits 3 on FAIL, and nothing after it runs.
#   3. Rule T's reference: Janus 0 on D60 exported at t* (select.json from Job 0, checked against its posted sha256).
# What it never does: score a locked-20 case, score any threshold other than argmax on the locked 100, or read a D60
# label (none is read anywhere). The locked-100 probabilities wait for `collect` (Janus 0 at argmax = the baseline of
# record, Janus 0 at t_C = a report).
# If Job 0 itself ran on Trillium, step 2 repeats Job 0's own L0 and may be skipped; steps 1 and 3 still run.
#
# Submit from the Trillium GPU login node (trillium-gpu.scinet.utoronto.ca):
#   SELECT_SHA256=<the sha256 posted on #302 for select.json> sbatch j0t_trillium.sh
#SBATCH --job-name=j1l-j0t
#SBATCH --account=def-aso22
#SBATCH --gpus-per-node=1
#SBATCH --time=04:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
R=${R:-$SCRATCH/asclepius/repo}
J0=${J0:-$SCRATCH/janus0}                 # Step T's copy of Janus 0 (sha256-verified on Trillium, #302)
JOB0=${JOB0:-$SCRATCH/j1l_job0}           # Job 0's outputs: select.json (copied from Fir if Job 0 ran there)
V=${V:-$SCRATCH/j1l_j0t}
E=$R/experiments/Crucible/j1l_r1
F=$R/experiments/Foxtrot/j1l_r3
CASES=${CASES:-$SCRATCH/asclepius/cases}
: "${SELECT_SHA256:?set SELECT_SHA256 to the sha256 of select.json posted on #302}"
echo "$SELECT_SHA256  $JOB0/select.json" | sha256sum -c -
mkdir -p $V/in_l100 $V/in_d60 $V/scores
python3 - "$E/lists.json" "$R/experiments/Delta/j1l_r2/drift60.json" "$R/trillium/sealed_test.json" "$V" "$CASES" <<'PY'
import json, sys
L = json.load(open(sys.argv[1])); D = json.load(open(sys.argv[2]))['drift60']; S = json.load(open(sys.argv[3]))
V, C = sys.argv[4], sys.argv[5]
sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
assert len(L['locked100']) == 100 and len(D) == 60 and not (set(L['locked100']) | set(D)) & sealed
assert not set(D) & (set(L['train620']) | set(L['locked100']))
json.dump({'val': [c for c in L['locked100'] if c not in L['locked20_of_open36']]}, open(f'{V}/split_val80.json', 'w'))
json.dump({'cases': {c: {'ct': f'{C}/{c}/ct.nii.gz'} for c in L['locked100']}}, open(f'{V}/layout.json', 'w'))
open(f'{V}/locked100.txt', 'w').write('\n'.join(L['locked100']))
open(f'{V}/d60.txt', 'w').write('\n'.join(D))
PY
for c in $(cat $V/locked100.txt); do ln -sf $CASES/$c/ct.nii.gz $V/in_l100/${c}_0000.nii.gz; done
for c in $(cat $V/d60.txt); do ln -sf $CASES/$c/ct.nii.gz $V/in_d60/${c}_0000.nii.gz; done
if [ -z "${DRYRUN:-}" ]; then
  module load StdEnv/2023 python/3.11.5
  source $HOME/icx14-venv/bin/activate
  export nnUNet_raw=$V/raw nnUNet_preprocessed=$V/pre nnUNet_results=$J0/nnunet_results nnUNet_compile=f
  P="-d 715 -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth \
     --disable_tta --save_probabilities -npp 6 -nps 6 -device cuda"
  nnUNetv2_predict -i $V/in_l100 -o $V/probs_l100 $P        # 1. about 1 GPU-h
  nnUNetv2_predict -i $V/in_d60 -o $V/probs_d60 $P          #    about 0.5 GPU-h
fi
# 2. L0-T (CPU): argmax export, val 80 only, against Fir's predictions
python $E/threshold_export.py --probs $V/probs_l100 --out $V/thr_l100 --t 0.5 --np 12
python $R/experiments/Atlas/r9_score_icx4.py --pred $V/thr_l100/t0.50 --pair $J0/pred_fir --icx $J0/icx \
  --aorta $J0/aorta --layout $V/layout.json --splits $V/split_val80.json --set val --np 12 \
  --out $V/scores/identity_val80_trillium.json > /dev/null
python $F/l0_check.py --scores $V/scores/identity_val80_trillium.json --mode trillium-identity --out $V/l0_trillium.json
# 3. Rule T's reference: Janus 0 on D60 at t* (the `--j0` input of rule_t.py)
T=$(python -c "import json;print('%.2f' % float(json.load(open('$JOB0/select.json'))['chosen_t']))")
python $E/threshold_export.py --probs $V/probs_d60 --out $V/d60_j0 --t $T --np 12
du -sh $V/probs_l100 $V/probs_d60
echo "[j0t] done: L0-T in $V/l0_trillium.json; Rule T reference at t*=$T in $V/d60_j0/t$T"
