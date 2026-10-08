#!/bin/bash
# Bridge Trillium experiment, ONE single-GPU job (<= 24 h): prep -> plan/preprocess -> train (deadline-bounded)
# -> predict val with softmax -> score D / R / H / O by tree-F1. Submitted by ./bridge (#SBATCH lines are
# passed on the sbatch command line there). Every step is resumable via marker files in $W.
set -uo pipefail
: "${W:?}" "${HERE:?}" "${VENV:?}"
DS_ID=750
DS_NAME=Dataset${DS_ID}_BridgeProxy
LOG=$W/logs
mkdir -p "$LOG" "$W/results"
echo "=== bridge job ${SLURM_JOB_ID:-local} on $(hostname) $(date -Is) cores=${SLURM_CPUS_ON_NODE:-?} gpus=${SLURM_GPUS_ON_NODE:-?}"
JOB_START=$(date +%s)

if [ "${BRIDGE_DRYRUN:-0}" != 1 ]; then
  module purge
  module load StdEnv/2023 cuda/12.6 python/3.11.5
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export nnUNet_raw=$W/nnunet/raw nnUNet_preprocessed=$W/nnunet/preprocessed nnUNet_results=$W/nnunet/results
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
NCPU=${SLURM_CPUS_ON_NODE:-${BRIDGE_NCPU:-4}}
export nnUNet_n_proc_DA=$(( NCPU > 4 ? NCPU - 2 : 2 ))
NPREP=$(( NCPU > 2 ? NCPU - 1 : 1 ))
nvidia-smi 2>/dev/null | head -15 || true

if [ "${BRIDGE_DRYRUN:-0}" = 1 ]; then
  PLANNER=ExperimentPlanner; PLANS=nnUNetPlans_bridge_dry; SPACING="2.0 2.0 2.0"; MEM=8; DEVICE=cpu
  TRAIN_HOURS=${BRIDGE_TRAIN_HOURS:-0.02}
else
  PLANNER=ResEncUNetPlanner; PLANS=nnUNetResEncUNetPlans_bridge60; SPACING="0.5 0.5 0.5"; MEM=60; DEVICE=cuda
  TRAIN_HOURS=${BRIDGE_TRAIN_HOURS:-19.5}   # leaves >= 4.5 h of the 24 h job for val prediction + scoring
fi
# 24 h total budget across resubmissions: previous jobs' wall time is logged in $W/gpu_seconds
USED=$(awk '{s+=$1} END {print s+0}' "$W/gpu_seconds" 2>/dev/null || echo 0)
trap 'echo $(( $(date +%s) - JOB_START )) >> "$W/gpu_seconds"' EXIT
BRIDGE_TRAIN_DEADLINE=$(python -c "
used=float('$USED'); h=float('$TRAIN_HOURS')
left=24*3600-used-4.5*3600            # keep 4.5 h for val prediction + scoring inside the budget
print(int($JOB_START + max(0.0, min(h*3600, left))))")
export BRIDGE_TRAIN_DEADLINE
echo "budget: previous jobs used $USED s; training deadline $(date -d @"$BRIDGE_TRAIN_DEADLINE" -Is 2>/dev/null || echo "$BRIDGE_TRAIN_DEADLINE")"

# 1. proxy labels + nnU-Net raw dataset (CPU)
if [ ! -f "$W/done.prep" ]; then
  python "$HERE/py/prep.py" "$W/casemap.json" "$W/icx" "$nnUNet_raw/$DS_NAME" "$DS_NAME" "$NPREP" || { echo "PREP FAILED"; exit 2; }
  touch "$W/done.prep"
fi

# 2. fingerprint, fixed window, plan, preprocess (CPU)
plan_and_preprocess () {
  local planner=$1 plans=$2 mem=$3
  nnUNetv2_extract_fingerprint -d $DS_ID -np "$NPREP" || return 1
  python "$HERE/py/patch_fp.py" "$nnUNet_preprocessed/$DS_NAME/dataset_fingerprint.json" || return 1
  # shellcheck disable=SC2086
  nnUNetv2_plan_experiment -d $DS_ID -pl "$planner" -gpu_memory_target "$mem" -overwrite_target_spacing $SPACING \
      -overwrite_plans_name "$plans" || return 1
  nnUNetv2_preprocess -d $DS_ID -plans_name "$plans" -c 3d_fullres -np "$NPREP" || return 1
  cp "$nnUNet_raw/$DS_NAME/splits_bridge.json" "$nnUNet_preprocessed/$DS_NAME/splits_final.json"
}
if [ ! -f "$W/done.preprocess.$PLANS" ]; then
  plan_and_preprocess $PLANNER $PLANS $MEM || { echo "PREPROCESS FAILED"; exit 3; }
  touch "$W/done.preprocess.$PLANS"
fi
python - "$nnUNet_preprocessed/$DS_NAME/$PLANS.json" <<'EOF' | tee "$W/results/plan.txt"
import json, sys
p = json.load(open(sys.argv[1]))['configurations']['3d_fullres']
print('3d_fullres patch', p['patch_size'], 'batch', p['batch_size'], 'spacing', p['spacing'])
EOF

# 3. train (deadline-bounded), then nnU-Net's own validation = prediction of the 80 val cases with softmax
MODEL=$nnUNet_results/$DS_NAME/nnUNetTrainer_bridge__${PLANS}__3d_fullres/fold_0
run_train () {
  local plans=$1 extra=""
  [ -f "$nnUNet_results/$DS_NAME/nnUNetTrainer_bridge__${plans}__3d_fullres/fold_0/checkpoint_latest.pth" ] && extra="--c"
  # shellcheck disable=SC2086
  nnUNetv2_train $DS_ID 3d_fullres 0 -tr nnUNetTrainer_bridge -p "$plans" --npz -device $DEVICE $extra 2>&1 | tee -a "$LOG/train.log"
  return "${PIPESTATUS[0]}"
}
if [ ! -f "$MODEL/checkpoint_final.pth" ]; then
  run_train $PLANS; rc=$?
  if [ $rc -ne 0 ] && [ ! -f "$MODEL/checkpoint_final.pth" ] && grep -qi "out of memory" "$LOG/train.log" \
     && [ ! -f "$MODEL/checkpoint_latest.pth" ] && [ "${BRIDGE_DRYRUN:-0}" != 1 ]; then
    echo "OOM at 60 GB plan: falling back to a 40 GB plan (patch shrinks; recorded in results)"
    PLANS=nnUNetResEncUNetPlans_bridge40; MEM=40
    MODEL=$nnUNet_results/$DS_NAME/nnUNetTrainer_bridge__${PLANS}__3d_fullres/fold_0
    plan_and_preprocess $PLANNER $PLANS $MEM && touch "$W/done.preprocess.$PLANS"
    run_train $PLANS; rc=$?
  fi
fi
if [ -f "$MODEL/checkpoint_final.pth" ] && [ ! -f "$MODEL/validation/summary.json" ]; then
  # a job killed during validation: redo validation only
  # shellcheck disable=SC2086
  nnUNetv2_train $DS_ID 3d_fullres 0 -tr nnUNetTrainer_bridge -p "$PLANS" --npz --val -device $DEVICE 2>&1 | tee -a "$LOG/val.log"
fi
[ -f "$MODEL/validation/summary.json" ] || { echo "NO VALIDATION PREDICTIONS"; exit 4; }

# 4. score D / R / H / O
python - "$MODEL" "$W/results/meta.json" "$PLANS" "$JOB_START" <<'EOF'
import json, re, sys, os, glob, time
model, out, plans, start = sys.argv[1:5]
logs = sorted(glob.glob(os.path.join(model, 'training_log_*.txt')))
txt = ''.join(open(l).read() for l in logs)
ep = re.findall(r'Epoch (\d+)', txt)
pp = json.load(open(os.path.join(os.environ['nnUNet_preprocessed'], 'Dataset750_BridgeProxy', plans + '.json')))['configurations']['3d_fullres']
split = json.load(open(os.path.join(os.environ['nnUNet_preprocessed'], 'Dataset750_BridgeProxy', 'splits_final.json')))[0]
json.dump(dict(plans=plans, patch=pp['patch_size'], batch=pp['batch_size'], spacing=pp['spacing'],
               epochs_trained=(int(ep[-1]) + 1) if ep else None, n_train=len(split['train']), n_val=len(split['val']),
               train_hours=round((os.path.getmtime(os.path.join(model, 'checkpoint_final.pth')) - float(start)) / 3600, 2)),
          open(out, 'w'), indent=1)
EOF
python "$HERE/py/evaluate_val.py" "$nnUNet_raw/$DS_NAME" "$MODEL/validation" "$W/results" "$(( NCPU > 9 ? 8 : NCPU ))" \
    2>&1 | tee "$LOG/evaluate.log"
cp "$MODEL"/training_log_*.txt "$MODEL/progress.png" "$W/results/" 2>/dev/null || true
cp "$MODEL/validation/summary.json" "$W/results/nnunet_val_summary.json" 2>/dev/null || true
cp "$LOG"/*.log "$W/results/" 2>/dev/null || true
cp "$W"/logs/slurm-*.out "$W/results/" 2>/dev/null || true
# try to put results next to the experiment (works only if it lives on $SCRATCH; otherwise run ./bridge collect)
mkdir -p "$HERE/results" 2>/dev/null && cp -r "$W/results/." "$HERE/results/" 2>/dev/null || echo "results stay in $W/results (run ./bridge collect)"
touch "$W/done.all"
echo "=== bridge job finished $(date -Is)"
