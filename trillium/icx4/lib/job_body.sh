#!/bin/bash
# Body of every icx4 GPU job (1 x H100, 23:50). The launcher submits a chain of these; each one picks up where the
# previous stopped (marker files in $W, nnU-Net --c), so the chain is safe to over-provision: once DONE exists the
# remaining jobs exit at once. Expects: W, LIB, ICX, VENV, TSEG_VENV, TOTALSEG_HOME_DIR, FROZEN_SHA exported by the
# job script. Never scores a sealed case (A14, lib/sealed.py); the decisive score is tF1 (A1c, lib/tf1_score.py).
set -uo pipefail
T0=$(date +%s)
DEADLINE=$((T0 + 23 * 3600 + 35 * 60))          # stop everything 15 min before the 23:50 walltime
NPROC="${SLURM_CPUS_ON_NODE:-24}"
PLANS=nnUNetResEncUNetPlans_60G_iso05
DS=Dataset715_ICX4
TR=nnUNetTrainerICX4
echo "=== icx4 job ${SLURM_JOB_ID:-local} on $(hostname) at $(date -Is); cores $NPROC ==="
if [ -e "$W/DONE" ]; then echo "[job] already DONE; nothing to do"; exit 0; fi

if command -v module >/dev/null 2>&1; then
    module purge
    module load StdEnv/2023 python/3.11.5 cuda/12.6
fi
# shellcheck disable=SC1091
[ -f "$VENV/bin/activate" ] && source "$VENV/bin/activate"
# A14 (#55): refuse to start without the sealed list, or with a copy that differs from the experiment folder's.
python "$LIB/sealed.py" check "$W/sealed_test.json" \
    || { echo "[job] REFUSING: $W/sealed_test.json is missing or invalid (A14)"; exit 3; }
cmp -s "$W/sealed_test.json" "$LIB/../sealed_test.json" \
    || { echo "[job] REFUSING: $W/sealed_test.json differs from $LIB/../sealed_test.json (A14)"; exit 3; }
# A1c (#54): refuse to run on any tf1 but the frozen one (also checked by the launcher and by tf1_score.py).
python - "$LIB/segtrain_tf1.py" "${FROZEN_SHA:-unset}" <<'PY' || { echo "[job] REFUSING: tf1 hash differs from the frozen hash (A1c)"; exit 3; }
import hashlib, os, sys
sys.path.insert(0, os.path.dirname(sys.argv[1]))
import tf1_score
h = hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest()
print('[job] segtrain.tf1 sha256', h, 'frozen', sys.argv[2])
sys.exit(0 if h == sys.argv[2] == tf1_score.TF1_SHA256 else 1)
PY
DEV="${ICX4_DEVICE:-cuda}"   # cpu only in the local self-test
export nnUNet_raw="$W/nnunet_raw" nnUNet_preprocessed="$W/nnunet_preprocessed" nnUNet_results="$W/nnunet_results"
export nnUNet_def_n_proc=8 nnUNet_compile=f
nvidia-smi --query-gpu=name,memory.total --format=csv || true
stamp() { python - "$W/timings.json" "$1" "$T0" <<'PY'
import json, os, sys, time
f, k, t0 = sys.argv[1], sys.argv[2], float(sys.argv[3])
d = json.load(open(f)) if os.path.exists(f) else {}
d.setdefault(k, []).append(round((time.time() - t0) / 3600, 2)); json.dump(d, open(f, 'w'))
PY
}

# #82: the launcher's completeness check again, before preprocessing (a second guard; ICX4_ALLOW_PARTIAL=1 overrides)
python "$LIB/layout.py" check "$W/layout.json" "$ICX" \
    || { echo "[job] REFUSING: cases/ is incomplete (see above)"; exit 3; }

# ---- A. labels + plan + preprocess (CPU, first job only) ---------------------------------------
if [ ! -e "$W/.preprocess_done" ] || [ ! -e "$W/.predict_in_done" ]; then
    python "$LIB/prepare.py" "$W" "$W/layout.json" "$ICX" $((NPROC - 2)) || { echo "[job] prepare FAILED"; exit 1; }
    stamp prepare_h
fi

# ---- B. train (resumes with --c; stops cleanly before the deadline) ----------------------------
FOLD="$nnUNet_results/$DS/${TR}__${PLANS}__3d_fullres/fold_0"
if [ ! -e "$W/.train_done" ]; then
    CONT=""
    if [ -e "$FOLD/checkpoint_latest.pth" ] && [ -e "$FOLD/checkpoint_final.pth" ] && \
            [ "$FOLD/checkpoint_latest.pth" -nt "$FOLD/checkpoint_final.pth" ]; then
        # the previous job was killed after its last periodic save: resume from that, not the older final
        mv "$FOLD/checkpoint_final.pth" "$FOLD/checkpoint_final.older.pth"
    fi
    # either file means there is something to resume. (nnU-Net deletes checkpoint_latest.pth when it writes
    # checkpoint_final.pth, so after a clean deadline stop only the final exists; requiring both restarted job 2.)
    { [ -e "$FOLD/checkpoint_latest.pth" ] || [ -e "$FOLD/checkpoint_final.pth" ]; } && CONT="--c"
    echo "[job] training ${CONT:-from scratch} (1000 epochs in total, chunked)"
    ICX4_DEADLINE=$((DEADLINE - 900)) ICX4_COMPLETE_MARKER="$W/.train_done" nnUNet_n_proc_DA=$((NPROC - 2)) \
        nnUNetv2_train 715 3d_fullres 0 -tr "$TR" -p "$PLANS" -device "$DEV" $CONT >> "$W/logs/train.log" 2>&1 \
        || echo "[job] training exited nonzero (see logs/train.log)"
    stamp train_h
    grep -h "Epoch \|ICX4:" "$W/logs/train.log" | tail -n 3
fi

# ---- C. predict all cases (resumable with --c; cut off before the deadline) --------------------
if [ -e "$W/.train_done" ] && [ ! -e "$W/.predict_done" ]; then
    LEFT=$((DEADLINE - $(date +%s) - 1200))
    if [ "$LEFT" -gt 1800 ]; then
        mkdir -p "$W/predictions"
        echo "[job] predicting $(ls "$W/predict_in" | wc -l) cases (up to $((LEFT / 60)) min in this job)"
        timeout "$LEFT" nnUNetv2_predict -i "$W/predict_in" -o "$W/predictions" -d 715 -c 3d_fullres -f 0 \
            -tr "$TR" -p "$PLANS" -chk checkpoint_final.pth --disable_tta --continue_prediction -npp 6 -nps 6 -device "$DEV" \
            >> "$W/logs/predict.log" 2>&1 || echo "[job] prediction stopped or failed (see logs/predict.log)"
        stamp predict_h
        # score.py also deletes unreadable files (a kill mid-write), so the next job redoes exactly those.
        # It scores open-36 + dev-44 only (lib/sealed.py, A14); the sealed cases are predicted, never scored.
        python "$LIB/score.py" "$W" "$ICX" "$W/results" $((NPROC - 2)) && touch "$W/.predict_done" \
            || echo "[job] predictions incomplete (or the sealed filter refused); the next job continues"
    else
        echo "[job] not enough time left to start prediction; the next job does it"
    fi
fi

# ---- C2. TotalSegmentator aortas (GPU), val-80 + open-36 + dev-44, never sealed (A1 ostium; ~1 h) ---
if [ -e "$W/.predict_done" ] && [ ! -e "$W/.aorta_done" ]; then
    LEFT=$((DEADLINE - $(date +%s) - 900))
    if [ "$LEFT" -gt 1200 ]; then
        echo "[job] aortas for val 80 + the open cases (up to $((LEFT / 60)) min in this job)"
        # shellcheck disable=SC1091
        ( [ -f "$TSEG_VENV/bin/activate" ] && source "$TSEG_VENV/bin/activate"
          TOTALSEG_HOME_DIR="$TOTALSEG_HOME_DIR" timeout "$LEFT" python "$LIB/aorta.py" "$W" "$ICX" "${ICX4_AORTA_DEVICE:-gpu}" ) \
            >> "$W/logs/aorta.log" 2>&1 && touch "$W/.aorta_done" \
            || echo "[job] aorta stage incomplete (see logs/aorta.log); the next job continues"
        tail -n 1 "$W/logs/aorta.log"
        stamp aorta_h
    else
        echo "[job] not enough time left for the aortas; the next job does them"
    fi
fi

# ---- C3. decisive tree-F1 @ 1.5 mm (CPU, frozen segtrain.tf1), open-36 + dev-44 only ---------------
if [ -e "$W/.aorta_done" ] && [ ! -e "$W/.tf1_done" ]; then
    LEFT=$((DEADLINE - $(date +%s) - 600))
    if [ "$LEFT" -gt 600 ]; then
        echo "[job] tree-F1 for the open cases (up to $((LEFT / 60)) min in this job)"
        timeout "$LEFT" python "$LIB/tf1_score.py" "$W" "$ICX" $((NPROC - 2)) >> "$W/logs/tf1.log" 2>&1 \
            && touch "$W/.tf1_done" || echo "[job] tF1 stage incomplete or had errors (see logs/tf1.log); the next job retries"
        tail -n 1 "$W/logs/tf1.log"
        stamp tf1_h
    else
        echo "[job] not enough time left for tF1; the next job does it"
    fi
fi

# ---- D. results (small; no weights, no volumes; never a sealed case) -----------------------------
mkdir -p "$W/results"
if [ -e "$W/.predict_done" ]; then
    python "$LIB/report.py" "$W" "$W/results" > "$W/logs/report.log" 2>&1 || echo "[job] report FAILED (see logs/report.log)"
fi
cp "$W"/logs/*.log "$W/results/" 2>/dev/null || true
cp "$FOLD"/{training_log_*.txt,progress.png} "$W/results/" 2>/dev/null || true
cp "$FOLD/validation/summary.json" "$W/results/val_summary.json" 2>/dev/null || true
cp "$W"/{planner_output.json,label_census.json,timings.json,splits.json} "$W/results/" 2>/dev/null || true
cp "$nnUNet_preprocessed/$DS"/{$PLANS.json,dataset.json} "$W/results/" 2>/dev/null || true
cp "$LIB/icx4_trainers.py" "$W/results/" 2>/dev/null || true
cp "$W/tf1_per_case.json" "$W/results/" 2>/dev/null || true
[ -e "$W/.predict_done" ] && [ -e "$W/.tf1_done" ] && [ -s "$W/results/SUMMARY.md" ] && touch "$W/DONE"
echo "=== icx4 job finished $(date -Is) after $(( ($(date +%s) - T0) / 60 )) min ==="
