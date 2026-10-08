#!/bin/bash
# A13 mode: inference/scoring ONLY on the Atlas run's outputs (no training). One short 1-GPU job:
#   (re)predict Atlas's 80 val cases with softmax from Atlas's checkpoint_final if the softmax was not saved,
#   then score D / R / H / O by tree-F1 against Atlas's own proxy labels (same reference as Atlas's report).
set -uo pipefail
: "${W:?}" "${HERE:?}" "${VENV:?}"
echo "=== bridge A13 job ${SLURM_JOB_ID:-local} on $(hostname) $(date -Is)"
export JOB_START; JOB_START=$(date +%s)
trap 'echo $(( $(date +%s) - JOB_START )) >> "$W/gpu_seconds"' EXIT
if [ "${BRIDGE_DRYRUN:-0}" != 1 ]; then
  module purge
  module load StdEnv/2023 cuda/12.6 python/3.11.5
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
NCPU=${SLURM_CPUS_ON_NODE:-${BRIDGE_NCPU:-4}}
OUT=$W/results
mkdir -p "$OUT" "$W/logs"

# re-check at job start (the job may have waited behind the Atlas job)
python "$HERE/py/atlas_link.py" "$HERE" "$W/atlas_link.json" || exit 2
python - "$W/atlas_link.json" <<'EOF' || { echo "Atlas outputs not ready: run ./bridge again (it will then decide again)"; exit 3; }
import json, sys
d = json.load(open(sys.argv[1]))
sys.exit(0 if d['mode'] == 'atlas-ready' else 1)
EOF
eval "$(python - "$W/atlas_link.json" <<'EOF'
import json, sys, shlex
d = json.load(open(sys.argv[1]))
for k in ('fold_dir', 'validation_dir', 'softmax_dir', 'labels_dir', 'images_dir', 'nnunet_results', 'plans', 'trainer', 'trainer_py'):
    print(f"A_{k.upper()}={shlex.quote(str(d.get(k) or ''))}")
print(f"A_DSID={int(d.get('dataset_id') or 713)}")
print(f"A_NEED_PREDICT={1 if d.get('need_predict') else 0}")
print('A_VAL=' + shlex.quote(' '.join(d['val_cases'])))
EOF
)"
export BRIDGE_KEEP_NPZ=1   # never delete the Atlas run's files
VDIR=$W/atlas_val_links; mkdir -p "$VDIR"
if [ "$A_NEED_PREDICT" != 1 ]; then
  # Atlas's own validation segmentations + softmax, linked (read-only use)
  for c in $A_VAL; do
    ln -sfn "$A_VALIDATION_DIR/$c.nii.gz" "$VDIR/$c.nii.gz"
    ln -sfn "${A_SOFTMAX_DIR:-$A_VALIDATION_DIR}/$c.npz" "$VDIR/$c.npz"
  done
else
  echo "Atlas val softmax incomplete: re-predicting its val cases from checkpoint_final"
  TDIR=$(python -c "import nnunetv2, os; print(os.path.join(os.path.dirname(nnunetv2.__file__), 'training', 'nnUNetTrainer', 'variants', 'atlas'))")
  mkdir -p "$TDIR"; touch "$TDIR/__init__.py"; cp "$A_TRAINER_PY" "$TDIR/atlas_trainers.py"
  IN=$W/atlas_val_in; VDIR=$W/atlas_val_pred
  mkdir -p "$IN" "$VDIR"
  for c in $A_VAL; do ln -sfn "$(readlink -f "$A_IMAGES_DIR/${c}_0000.nii.gz")" "$IN/${c}_0000.nii.gz"; done
  DEV=cuda; NPP=4; [ "${BRIDGE_DRYRUN:-0}" = 1 ] && { DEV=cpu; NPP=0; }   # sequential on small dev boxes
  # nnU-Net needs the model folder under $nnUNet_results; Atlas's is read in place (read-only use)
  nnUNet_results=$A_NNUNET_RESULTS nnUNet_raw=$W/nnunet/raw nnUNet_preprocessed=$W/nnunet/preprocessed \
    nnUNetv2_predict -i "$IN" -o "$VDIR" -d "$A_DSID" -c 3d_fullres -tr "$A_TRAINER" -p "$A_PLANS" -f 0 \
      -chk checkpoint_final.pth --save_probabilities --disable_tta -device $DEV -npp $NPP -nps $NPP 2>&1 | tee "$W/logs/atlas_predict.log"
  [ "${PIPESTATUS[0]}" = 0 ] || { echo "PREDICT FAILED"; exit 4; }
fi
# reference = Atlas's own proxy labels; case list = Atlas's val split
RAW=$W/atlas_ref; mkdir -p "$RAW"
ln -sfn "$A_LABELS_DIR" "$RAW/labelsTr"
python -c "import json,sys; json.dump([{'train': [], 'val': sys.argv[1].split()}], open('$RAW/splits_bridge.json', 'w'))" "$A_VAL"
python - "$OUT/meta.json" "$W/atlas_link.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[2]))
json.dump(dict(mode='A13 inference-only on the Atlas run', plans=d.get('plans'), atlas_fold_dir=d.get('fold_dir'),
               softmax='re-predicted from checkpoint_final' if d.get('need_predict') else 'Atlas validation --npz',
               n_val=len(d['val_cases']), epochs_trained='see Atlas results', train_hours='see Atlas results',
               n_train=560, patch='see Atlas results'), open(sys.argv[1], 'w'), indent=1)
EOF
python "$HERE/py/evaluate_val.py" "$RAW" "$VDIR" "$OUT" "$(( NCPU > 9 ? 8 : NCPU ))" 2>&1 | tee "$W/logs/evaluate.log"
cp "$W"/logs/*.log "$OUT/" 2>/dev/null || true
cp "$W/atlas_link.json" "$OUT/" 2>/dev/null || true
mkdir -p "$HERE/results" 2>/dev/null && cp -r "$OUT/." "$HERE/results/" 2>/dev/null || echo "results stay in $OUT (run ./bridge collect)"
[ -s "$OUT/SUMMARY.md" ] && touch "$W/done.all"
echo "=== bridge A13 job finished $(date -Is)"
