#!/bin/bash
# Body of the single Atlas run-2 GPU job (1 x H100, 23:50). Stages are idempotent (marker files in $W), so a
# resubmission resumes. Expects W, LIB, RUN1, ICX, CL, VENV, TOTALSEG_HOME_DIR, FROZEN_SHA, S_EPOCH exported by
# the job script, plus PLANS, RUN1_VAL (run 1's validation dir) and RUN1_REF (run 1's labelsTr).
#
#   Phase A (no training, ~1 h): TotalSegmentator aortas (80 val + 36 clean open test) and the 36 open-test
#            predictions with run 1's checkpoint, on the GPU; meanwhile Phase B's preprocessing on the CPU.
#            Then run 1's val re-score (A1) + FP census + threshold sweep in the background, on 4 cores.
#   Phase B (~21 h): the A2 window ablation, 412 epochs (run 1's length), --npz; scored by the same code.
#   Report: paired B - run 1, decided by the rule fixed in A16.
set -uo pipefail
T0=$(date +%s)
DEADLINE=$((T0 + 23 * 3600 + 40 * 60))          # 10 min before the 23:50 walltime
NPROC="${SLURM_CPUS_ON_NODE:-24}"
EPOCHS_B=412
echo "=== atlas2 job ${SLURM_JOB_ID:-local} on $(hostname) at $(date -Is); cores $NPROC ==="

if [ "${ATLAS2_LOCAL_TEST:-0}" != "1" ]; then
    module purge
    module load StdEnv/2023 python/3.11.5 cuda/12.6
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    nvidia-smi --query-gpu=name,memory.total --format=csv || true
fi
export nnUNet_raw="$W/nnunet_raw" nnUNet_preprocessed="$W/nnunet_preprocessed" nnUNet_results="$W/nnunet_results"
export nnUNet_def_n_proc=8 nnUNet_compile=f OMP_NUM_THREADS=1
mkdir -p "$W/logs" "$W/results"
stamp() { python - "$W/timings.json" "$1" "$T0" <<'PY'
import json, os, sys, time
p, k, t0 = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = json.load(open(p)) if os.path.exists(p) else {}
d[k] = round((time.time() - t0) / 3600, 3); json.dump(d, open(p, 'w'), indent=1)
PY
}

# ---- 0. the frozen metric (A1c): refuse to run on any other version of segtrain.tf1 ---------------------------
python - "$LIB/segtrain_tf1.py" "$FROZEN_SHA" "$W/tf1_hash.json" <<'PY' || { echo "[job] REFUSING: tf1 hash differs from the frozen hash"; exit 3; }
import hashlib, json, sys
h = hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest()
json.dump(dict(sha256=h, frozen=sys.argv[2], match=h == sys.argv[2]), open(sys.argv[3], 'w'))
print('[job] segtrain.tf1 sha256', h, 'frozen', sys.argv[2]); sys.exit(0 if h == sys.argv[2] else 1)
PY
stamp start

# ---- A0. Phase B preprocessing in the background (CPU, <= 10 workers, ~40 min) -------------------------------
PREP_PID=""
if [ ! -e "$W/.b_preprocess_done" ]; then
    nice -n 5 python "$LIB/prepare_b.py" "$W" "$RUN1/results/manifest.json" 10 > "$W/logs/prepare_b.log" 2>&1 &
    PREP_PID=$!
fi

# ---- A1. aortas (GPU, TotalSegmentator fast) for the 80 val + 36 open cases ---------------------------------
if [ ! -e "$W/.aorta_done" ]; then
    python "$LIB/aorta.py" "$W/aorta" "$W/aorta_cases.json" "$W/sealed_test.json" gpu > "$W/logs/aorta.log" 2>&1 \
        && touch "$W/.aorta_done" || echo "[job] aorta stage exited nonzero (see logs/aorta.log)"
    tail -n 1 "$W/logs/aorta.log"
fi
stamp aortas_done

# ---- A2. run 1 val: A1 re-score + FP census + threshold sweep (background, 4 workers) ------------------------
SCORE1_PID=""
if [ ! -s "$W/score_run1.json" ]; then
    nice -n 5 python "$LIB/score_run.py" run1 "$RUN1_VAL" "$RUN1_REF" "$W/layout.json" "$W/aorta" "$ICX" "$CL" \
        "$W/val_cases.json" "$W/sealed_test.json" "$W/score_run1.json" "${SCORE1_WORKERS:-4}" > "$W/logs/score_run1.log" 2>&1 &
    SCORE1_PID=$!
fi

# ---- A3. the 36 clean open test cases with run 1's checkpoint, softmax saved (GPU) ---------------------------
if [ ! -e "$W/.open36_done" ]; then
    python "$LIB/open36.py" "$W" "$RUN1/results/manifest.json" "$W/layout.json" "$ICX" "$W/sealed_test.json" \
        > "$W/logs/open36.log" 2>&1 && touch "$W/.open36_done" || echo "[job] open36 stage exited nonzero (see logs/open36.log)"
    tail -n 1 "$W/logs/open36.log"
fi
stamp open36_done

# ---- B. window ablation: wait for preprocessing, then 412 epochs ---------------------------------------------
if [ -n "$PREP_PID" ]; then wait "$PREP_PID" || echo "[job] prepare_b exited nonzero (see logs/prepare_b.log)"; fi
stamp b_preprocess_done
if [ -e "$W/.b_preprocess_done" ] && [ ! -e "$W/.b_train_done" ]; then
    NEED=$(python -c "print(int($EPOCHS_B * $S_EPOCH * 1.03 + 5400))")
    LEFT=$((DEADLINE - $(date +%s)))
    if [ "$LEFT" -lt "$NEED" ]; then
        echo "[job] WARNING: $LEFT s left, $NEED s needed for $EPOCHS_B epochs: training stops at the deadline (unpaired)"
    fi
    CONT=""
    ls "$nnUNet_results"/Dataset714_*/nnUNetTrainerAtlas__*/fold_0/checkpoint_latest.pth >/dev/null 2>&1 && CONT="--c"
    echo "[job] phase B: $EPOCHS_B epochs, default window"
    ATLAS_EPOCHS="$EPOCHS_B" ATLAS_DEADLINE=$((DEADLINE - 5400)) nnUNet_n_proc_DA=12 \
        nnUNetv2_train 714 3d_fullres 0 -tr nnUNetTrainerAtlas -p "$PLANS" --npz $CONT > "$W/logs/train_b.log" 2>&1 \
        && touch "$W/.b_train_done" || echo "[job] phase B training exited nonzero (see logs/train_b.log)"
fi
stamp b_train_done

# ---- B scoring (same code as run 1; the sweep only if > 40 min remain after scoring) -------------------------
FOLD_B=$(find "$nnUNet_results" -maxdepth 3 -type d -path "*/Dataset714_*/nnUNetTrainerAtlas__*/fold_0" 2>/dev/null | head -1)
if [ -n "$FOLD_B" ] && [ -d "$FOLD_B/validation" ] && [ ! -s "$W/score_b.json" ]; then
    LEFT=$((DEADLINE - $(date +%s)))
    SWEEP=1; [ "$LEFT" -lt 4800 ] && SWEEP=0
    SCORE_SWEEP=$SWEEP python "$LIB/score_run.py" b "$FOLD_B/validation" "$RUN1_REF" "$W/layout.json" "$W/aorta" \
        "$ICX" "$CL" "$W/val_cases.json" "$W/sealed_test.json" "$W/score_b.json" $((NPROC - 6)) > "$W/logs/score_b.log" 2>&1 \
        || echo "[job] scoring B exited nonzero (see logs/score_b.log)"
fi
if [ -n "$SCORE1_PID" ]; then wait "$SCORE1_PID" || echo "[job] scoring run 1 exited nonzero (see logs/score_run1.log)"; fi
stamp scored

# ---- report ------------------------------------------------------------------------------------------------
python "$LIB/report2.py" "$W" "$W/results" > "$W/logs/report.log" 2>&1 || echo "[job] report FAILED (see logs/report.log)"
cp "$W"/logs/*.log "$W"/timings.json "$W"/window_b.json "$W"/tf1_hash.json "$W/results/" 2>/dev/null || true
[ -n "$FOLD_B" ] && cp "$FOLD_B"/{training_log_*.txt,progress.png} "$W/results/" 2>/dev/null || true
[ -e "$W/.b_train_done" ] && [ -s "$W/score_b.json" ] && [ -s "$W/score_run1.json" ] && touch "$W/DONE"
echo "=== atlas2 job finished $(date -Is) after $(( ($(date +%s) - T0) / 60 )) min ==="
