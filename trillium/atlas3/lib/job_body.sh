#!/bin/bash
# Body of the single Atlas run-3 GPU job (1 x H100, 23:50): the FP-aware loss pilot (Round 8, A24).
# Both arms warm-start from run 2's arm B (default window) with the A17a trainer, same seed, same data and
# augmentation stream, EQUAL epochs set from the time actually left before training starts (A22: the poly schedule
# always completes). Stages are idempotent (markers in $W).
# Expects W, LIB, VENV, FROZEN_SHA, SOURCE, DATASET, WINDOW, S_EPOCH, REF, R2, ICX, CL, PLANS, SEED exported.
set -uo pipefail
T0=$(date +%s)
DEADLINE=$((T0 + 23 * 3600 + 40 * 60))          # 10 min before the 23:50 walltime
NPROC="${SLURM_CPUS_ON_NODE:-24}"
MAX_EPOCHS=200
echo "=== atlas3 job ${SLURM_JOB_ID:-local} on $(hostname) at $(date -Is); cores $NPROC ==="

if [ "${ATLAS3_LOCAL_TEST:-0}" != "1" ]; then
    module purge
    module load StdEnv/2023 python/3.11.5 cuda/12.6
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    nvidia-smi --query-gpu=name,memory.total --format=csv || true
fi
export PYTHONPATH="$LIB/vendor${PYTHONPATH:+:$PYTHONPATH}"
export nnUNet_raw="$R2/nnunet_raw" nnUNet_preprocessed="$R2/nnunet_preprocessed" nnUNet_results="$W/nnunet_results"
export nnUNet_def_n_proc=8 nnUNet_compile=f OMP_NUM_THREADS=1 nnUNet_n_proc_DA=12
export SEGTRAIN_FINETUNE_FROM="$SOURCE" SEGTRAIN_CT_WINDOW="$WINDOW" SEGTRAIN_SEED="$SEED"
export SEGTRAIN_SEALED_LIST="$W/sealed_test.json" SEGTRAIN_SAVE_PROBABILITIES=1
export SEGTRAIN_FP_LAMBDA=1 SEGTRAIN_FP_GAMMA=2 SEGTRAIN_FP_BAND_MM=1.5
mkdir -p "$W/logs" "$W/results"
stamp() { python - "$W/timings.json" "$1" "$T0" <<'PY'
import json, os, sys, time
p, k, t0 = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = json.load(open(p)) if os.path.exists(p) else {}
d[k] = round((time.time() - t0) / 3600, 3); json.dump(d, open(p, 'w'), indent=1)
PY
}

# ---- 0. the frozen metric (A1c): refuse to run on any other version of segtrain.tf1 ------------------------------
python - "$LIB/vendor/segtrain/tf1.py" "$FROZEN_SHA" "$W/tf1_hash.json" <<'PY' || { echo "[job] REFUSING: tf1 hash differs from the pinned hash"; exit 3; }
import hashlib, json, sys
h = hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest()
json.dump(dict(sha256=h, frozen=sys.argv[2], match=h == sys.argv[2]), open(sys.argv[3], 'w'))
print('[job] segtrain.tf1 sha256', h, 'pinned', sys.argv[2]); sys.exit(0 if h == sys.argv[2] else 1)
PY
stamp start

# ---- 1. equal epochs for both arms, from the time actually left (A22) --------------------------------------------
if [ ! -s "$W/schedule.json" ]; then
    python - "$W/schedule.json" "$DEADLINE" "$S_EPOCH" "$MAX_EPOCHS" <<'PY'
import json, sys, time
out, deadline, s_epoch, cap = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
reserve = 2 * 2700 + 1800 + 600          # two final validations (80 cases + softmax), F1 scoring, report
f1_cost = 1.10                           # the FP term's extra softmax + band per step (upper estimate)
left = deadline - time.time() - reserve
epochs = int(min(cap, left / (s_epoch * (1.0 + f1_cost) * 1.02)))
json.dump(dict(epochs=epochs, s_epoch_b=s_epoch, f1_cost_factor=f1_cost, train_budget_s=left,
               warmup_iters=2500), open(out, 'w'), indent=1)
print('[job] schedule', json.load(open(out)))
if epochs < 50:
    sys.exit('[job] fewer than 50 epochs fit: refusing to run a pilot that cannot complete')
PY
    [ -s "$W/schedule.json" ] || exit 4
fi
EPOCHS=$(python -c "import json; print(json.load(open('$W/schedule.json'))['epochs'])")
export SEGTRAIN_EPOCHS="$EPOCHS"
echo "[job] both arms: $EPOCHS epochs, seed $SEED, warm from $SOURCE"
stamp scheduled

arm() {  # $1 = F0 | F1
    local tr="nnUNetTrainer_segtrain_fppilot_$1"
    [ -e "$W/.train_$1_done" ] && return 0
    local cont=""
    ls "$nnUNet_results/$DATASET/${tr}__${PLANS}__3d_fullres/fold_0/checkpoint_latest.pth" >/dev/null 2>&1 && cont="--c"
    # a hard stop that still leaves time for this arm's validation and the report; a paused arm makes the
    # comparison "reported, not decided" (A22)
    local left=$((DEADLINE - $(date +%s) - 3600))
    SEGTRAIN_MAX_SECONDS="$left" \
    nnUNetv2_train "$DATASET" 3d_fullres 0 -tr "$tr" -p "$PLANS" --npz $cont > "$W/logs/train_$1.log" 2>&1 \
        && touch "$W/.train_$1_done" || echo "[job] arm $1 exited nonzero (see logs/train_$1.log)"
}
score() {  # $1 = arm, $2 = workers
    local fold="$nnUNet_results/$DATASET/nnUNetTrainer_segtrain_fppilot_$1__${PLANS}__3d_fullres/fold_0"
    [ -s "$W/score_$1.json" ] && return 0
    [ -d "$fold/validation" ] || { echo "[job] no validation for $1"; return 1; }
    SCORE_SWEEP=0 python "$LIB/score_run.py" "$1" "$fold/validation" "$REF" "$W/layout.json" "$R2/aorta" "$ICX" "$CL" \
        "$W/val_cases.json" "$W/sealed_test.json" "$W/score_$1.json" "$2" > "$W/logs/score_$1.log" 2>&1 \
        || echo "[job] scoring $1 exited nonzero (see logs/score_$1.log)"
}

# ---- 2. F0 (plain), then F1 (FP-aware); F0 is scored on the CPU while F1 trains ---------------------------------
arm F0
stamp f0_done
SCORE_F0_PID=""
if [ -e "$W/.train_F0_done" ]; then
    score F0 4 &
    SCORE_F0_PID=$!
fi
arm F1
stamp f1_done
[ -e "$W/.train_F1_done" ] && score F1 $((NPROC - 6))
if [ -n "$SCORE_F0_PID" ]; then wait "$SCORE_F0_PID" || true; fi
score F0 $((NPROC - 6))                      # no-op if the background scoring finished
stamp scored

# ---- 3. report -------------------------------------------------------------------------------------------------
python "$LIB/report3.py" "$W" "$W/results" > "$W/logs/report.log" 2>&1 || echo "[job] report FAILED (see logs/report.log)"
cp "$W"/logs/*.log "$W"/timings.json "$W"/schedule.json "$W"/tf1_hash.json "$W"/run2_inputs.json "$W/results/" 2>/dev/null || true
for a in F0 F1; do
    f="$nnUNet_results/$DATASET/nnUNetTrainer_segtrain_fppilot_${a}__${PLANS}__3d_fullres/fold_0"
    for t in "$f"/training_log_*.txt; do [ -e "$t" ] && cp "$t" "$W/results/training_log_$a.txt"; done
    [ -e "$f/progress.png" ] && cp "$f/progress.png" "$W/results/progress_$a.png"
done
[ -e "$W/.train_F0_done" ] && [ -e "$W/.train_F1_done" ] && [ -s "$W/score_F0.json" ] && [ -s "$W/score_F1.json" ] && touch "$W/DONE"
echo "=== atlas3 job finished $(date -Is) after $(( ($(date +%s) - T0) / 60 )) min ==="
