#!/bin/bash
# Body of every icx14 GPU job (1 x H100, 23:50). The launcher submits a chain of these; each one picks up where the
# previous stopped (marker files in $W, nnU-Net --c), so the chain is safe to over-provision: once DONE exists the
# remaining jobs exit at once. Expects: W, LIB, ICX, VENV exported by the job script.
set -uo pipefail
T0=$(date +%s)
DEADLINE=$((T0 + 23 * 3600 + 35 * 60))          # stop everything 15 min before the 23:50 walltime
NPROC="${SLURM_CPUS_ON_NODE:-24}"
PLANS=nnUNetResEncUNetPlans_60G_iso05
DS=Dataset714_ICX14
TR=nnUNetTrainerICX14
echo "=== icx14 job ${SLURM_JOB_ID:-local} on $(hostname) at $(date -Is); cores $NPROC ==="
if [ -e "$W/DONE" ]; then echo "[job] already DONE; nothing to do"; exit 0; fi

if command -v module >/dev/null 2>&1; then
    module purge
    module load StdEnv/2023 python/3.11.5 cuda/12.6
fi
# shellcheck disable=SC1091
[ -f "$VENV/bin/activate" ] && source "$VENV/bin/activate"
DEV="${ICX14_DEVICE:-cuda}"   # cpu only in the local self-test
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
    ls "$FOLD"/checkpoint_{latest,final}.pth >/dev/null 2>&1 && CONT="--c"
    echo "[job] training ${CONT:-from scratch} (1000 epochs in total, chunked)"
    ICX14_DEADLINE=$((DEADLINE - 900)) ICX14_COMPLETE_MARKER="$W/.train_done" nnUNet_n_proc_DA=$((NPROC - 2)) \
        nnUNetv2_train 714 3d_fullres 0 -tr "$TR" -p "$PLANS" -device "$DEV" $CONT >> "$W/logs/train.log" 2>&1 \
        || echo "[job] training exited nonzero (see logs/train.log)"
    stamp train_h
    grep -h "Epoch \|ICX14:" "$W/logs/train.log" | tail -n 3
fi

# ---- C. predict all cases (resumable with --c; cut off before the deadline) --------------------
if [ -e "$W/.train_done" ] && [ ! -e "$W/.predict_done" ]; then
    LEFT=$((DEADLINE - $(date +%s) - 1200))
    if [ "$LEFT" -gt 1800 ]; then
        mkdir -p "$W/predictions"
        echo "[job] predicting $(ls "$W/predict_in" | wc -l) cases (up to $((LEFT / 60)) min in this job)"
        timeout "$LEFT" nnUNetv2_predict -i "$W/predict_in" -o "$W/predictions" -d 714 -c 3d_fullres -f 0 \
            -tr "$TR" -p "$PLANS" -chk checkpoint_final.pth --disable_tta --continue_prediction -npp 6 -nps 6 -device "$DEV" \
            >> "$W/logs/predict.log" 2>&1 || echo "[job] prediction stopped or failed (see logs/predict.log)"
        stamp predict_h
        # score.py also deletes unreadable files (a kill mid-write), so the next job redoes exactly those
        python "$LIB/score.py" "$W" "$ICX" "$W/results" $((NPROC - 2)) && touch "$W/.predict_done" \
            || echo "[job] predictions incomplete; the next job continues"
    else
        echo "[job] not enough time left to start prediction; the next job does it"
    fi
fi

# ---- D. results (small; no weights, no volumes) -------------------------------------------------
mkdir -p "$W/results"
cp "$W"/logs/*.log "$W/results/" 2>/dev/null || true
cp "$FOLD"/{training_log_*.txt,progress.png} "$W/results/" 2>/dev/null || true
cp "$FOLD/validation/summary.json" "$W/results/val_summary.json" 2>/dev/null || true
cp "$W"/{planner_output.json,label_census.json,timings.json,splits.json} "$W/results/" 2>/dev/null || true
cp "$nnUNet_preprocessed/$DS"/{$PLANS.json,dataset.json} "$W/results/" 2>/dev/null || true
cp "$LIB/icx14_trainers.py" "$W/results/" 2>/dev/null || true
[ -e "$W/.predict_done" ] && [ -s "$W/results/SUMMARY.md" ] && touch "$W/DONE"
echo "=== icx14 job finished $(date -Is) after $(( ($(date +%s) - T0) / 60 )) min ==="
