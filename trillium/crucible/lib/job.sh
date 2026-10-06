#!/bin/bash
# SLURM job for the Crucible two-reads experiment. Submitted by ../crucible from the GPU login node; do not sbatch by hand.
#SBATCH --job-name=crucible_2reads
#SBATCH --nodes=1
#SBATCH --gpus-per-node=1
#SBATCH --time=23:55:00
set -uo pipefail
: "${CRUCIBLE_WORK:?}" "${CRUCIBLE_HERE:?}" "${CRUCIBLE_VENV:?}"
module purge
module load StdEnv/2023 python/3.11.5 cuda/12.6
# shellcheck disable=SC1091
source "$CRUCIBLE_VENV/bin/activate"
export CRUCIBLE_JOB_END=$(( $(date +%s) + 23*3600 + 55*60 - 600 ))
export OMP_NUM_THREADS=1 nnUNet_n_proc_DA=${SLURM_CPUS_PER_TASK:-20} nnUNet_compile=false
nvidia-smi || true
python "$CRUCIBLE_HERE/lib/driver.py"
rc=$?
mkdir -p "$CRUCIBLE_WORK/results/logs"
cp "$CRUCIBLE_WORK"/logs/*.out "$CRUCIBLE_WORK/results/logs/" 2>/dev/null || true
for f in "$CRUCIBLE_WORK"/nnUNet_results/*/nnUNetTrainerCrucible__nnUNetPlans__3d_fullres/fold_all/training_log_*.txt; do
  [ -e "$f" ] && cp "$f" "$CRUCIBLE_WORK/results/logs/$(basename "$(dirname "$(dirname "$(dirname "$f")")")")_$(basename "$f")"
done
cp "$CRUCIBLE_WORK/state.json" "$CRUCIBLE_WORK/results/" 2>/dev/null || true
# copy back next to the entry point if that file system is writable from here (it is not when it lives in $HOME/$PROJECT)
if mkdir -p "$CRUCIBLE_HERE/results" 2>/dev/null && touch "$CRUCIBLE_HERE/results/.w" 2>/dev/null; then
  cp -r "$CRUCIBLE_WORK/results/." "$CRUCIBLE_HERE/results/" && rm -f "$CRUCIBLE_HERE/results/.w"
fi
exit $rc
