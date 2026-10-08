#!/bin/bash
# Body of the single Atlas GPU job (1 x H100, 23:50). Stages are idempotent (marker files in $W), so a resubmission
# resumes. Expects: W, LIB, ICX, VENV exported by the job script.
set -uo pipefail
T0=$(date +%s)
DEADLINE=$((T0 + 23 * 3600 + 40 * 60))          # stop everything 10 min before the 23:50 walltime
NPROC="${SLURM_CPUS_ON_NODE:-24}"
PLANS=nnUNetResEncUNetPlans_60G_iso05
echo "=== atlas job ${SLURM_JOB_ID:-local} on $(hostname) at $(date -Is); cores $NPROC ==="

module purge
module load StdEnv/2023 python/3.11.5 cuda/12.6
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export nnUNet_raw="$W/nnunet_raw" nnUNet_preprocessed="$W/nnunet_preprocessed" nnUNet_results="$W/nnunet_results"
export nnUNet_def_n_proc=8 nnUNet_compile=f
nvidia-smi --query-gpu=name,memory.total --format=csv || true

# ---- A. proxy labels + plan + preprocess (CPU) ------------------------------------------------
if [ ! -e "$W/.preprocess_done" ]; then
    python "$LIB/prepare.py" "$W" "$W/layout.json" "$ICX" $((NPROC - 2)) || echo "[job] prepare FAILED"
fi

# ---- B. R0 benchmark: 4 epochs at nnUNet_n_proc_DA = 12 and 22 ----------------------------------
bench() {  # $1 = n_proc_DA
    local out="$W/bench_da$1.json"
    [ -s "$out" ] && return 0
    ATLAS_BENCH_OUT="$out" ATLAS_BENCH_EPOCHS=4 nnUNet_n_proc_DA="$1" \
        nnUNetv2_train 713 3d_fullres 0 -tr nnUNetTrainerAtlasBench -p "$PLANS" > "$W/logs/bench_da$1.log" 2>&1 \
        || echo "[job] bench n_proc_DA=$1 exited nonzero (see logs/bench_da$1.log)"
}
if [ -e "$W/.preprocess_done" ] && [ ! -e "$W/.bench_done" ]; then
    bench 12
    bench $((NPROC - 2))
    if ! ls "$W"/bench_da*.json >/dev/null 2>&1; then
        # nothing completed an epoch: most likely out of VRAM at 256^3 -> measured fallback (plan v3 §2.3)
        echo "[job] no benchmark epoch completed at 256^3; switching to the 192x256x256 fallback"
        python - "$W/nnunet_preprocessed/Dataset713_AtlasProxy/$PLANS.json" <<'PY'
import json, sys
p = json.load(open(sys.argv[1])); p['configurations']['3d_fullres']['patch_size'] = [192, 256, 256]
json.dump(p, open(sys.argv[1], 'w'), indent=1)
PY
        echo '{"fallback_patch": [192, 256, 256]}' > "$W/fallback.json"
        bench $((NPROC - 2))
    fi
    touch "$W/.bench_done"
fi

# ---- C. short R1: as many epochs as fit, full poly-LR schedule over that length --------------
if [ -e "$W/.bench_done" ] && [ ! -e "$W/.train_done" ]; then
    read -r EPOCHS DA <<<"$(python - "$W" "$DEADLINE" <<'PY'
import json, glob, sys, time, statistics
W, deadline = sys.argv[1], int(sys.argv[2])
best = None
for f in glob.glob(W + '/bench_da*.json'):
    b = json.load(open(f)); ep = b['epochs'][1:] or b['epochs']
    s = statistics.median(e['epoch_s'] for e in ep)
    if best is None or s < best[0]: best = (s, b['n_proc_DA'])
reserve = 5400  # final validation of 80 cases + scoring
budget = deadline - time.time() - reserve
epochs = max(10, min(1000, int(budget / (best[0] * 1.03)))) if best else 0
json.dump(dict(s_per_epoch_bench=best[0] if best else None, n_proc_DA=best[1] if best else None, epochs=epochs,
               train_budget_s=budget), open(W + '/schedule.json', 'w'))
print(epochs, best[1] if best else 22)
PY
)"
    echo "[job] training $EPOCHS epochs with nnUNet_n_proc_DA=$DA"
    CONT=""
    ls "$nnUNet_results"/Dataset713_AtlasProxy/nnUNetTrainerAtlas__*/fold_0/checkpoint_latest.pth >/dev/null 2>&1 && CONT="--c"
    if [ "$EPOCHS" -gt 0 ]; then
        ATLAS_EPOCHS="$EPOCHS" ATLAS_DEADLINE=$((DEADLINE - 4500)) nnUNet_n_proc_DA="$DA" \
            nnUNetv2_train 713 3d_fullres 0 -tr nnUNetTrainerAtlas -p "$PLANS" --npz $CONT > "$W/logs/train.log" 2>&1 \
            && touch "$W/.train_done" || echo "[job] training exited nonzero (see logs/train.log)"
    fi
fi

# --npz (A13): the final validation also saves the val-fold softmax (<case>.npz + .pkl) next to the predicted
# segmentations, so other experiments can run inference-only analyses (naming R/H, P1') on this model.

# ---- D. score + report (always, also on partial results) ---------------------------------------
mkdir -p "$W/export" && cp "$LIB/atlas_trainers.py" "$W/export/"   # trainer source for inference-only reuse (A13)
python "$LIB/report.py" "$W" "$W/results" "$NPROC" || echo "[job] report FAILED"
cp "$W"/logs/*.log "$W/results/" 2>/dev/null || true
cp "$nnUNet_results"/Dataset713_AtlasProxy/nnUNetTrainerAtlas__*/fold_0/{training_log_*.txt,progress.png} "$W/results/" 2>/dev/null || true
cp "$W"/planner_output.json "$W"/schedule.json "$W"/bench_da*.json "$W/results/" 2>/dev/null || true
cp "$nnUNet_preprocessed"/Dataset713_AtlasProxy/{nnUNetResEncUNetPlans_60G_iso05.json,dataset.json,splits_final.json} "$W/results/" 2>/dev/null || true
[ -e "$W/.train_done" ] && [ -s "$W/results/per_case_val.json" ] && touch "$W/DONE"
echo "=== atlas job finished $(date -Is) after $(( ($(date +%s) - T0) / 60 )) min ==="
