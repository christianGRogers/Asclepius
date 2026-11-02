#!/bin/bash
# Janus-M Job M1 (India v1): TotalSegmentator `heartchambers_highres` on the public TotalSegmentator v1 cardiac
# subjects that are NOT in the SegQueue14 pool (fetch_ts_cardiac.py excludes all 16 pool subjects).
# The lead runs it; nothing here reads a pool volume. The licence number is typed by the lead on Fir
# (`totalseg_set_license -l ...`) and is never written into the repository.
#
# Login node, once:
#   module load StdEnv/2023 python/3.11.5
#   python -m venv $HOME/jm-venv && source $HOME/jm-venv/bin/activate
#   pip install TotalSegmentator remotezip nibabel scipy scikit-image
#   totalseg_set_license -l <licence number, typed by the lead>
#   totalseg_download_weights -t heartchambers_highres
#   mkdir -p $SCRATCH/janusm && cd $SCRATCH/janusm
#   git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
#   python repo/experiments/JanusM/India/fetch_ts_cardiac.py ts        # ~6 GB, resumable
#   sbatch repo/experiments/JanusM/India/fir/m1_heartchambers.sh
# Then, on the login node (CPU, ~1 h):
#   python repo/experiments/JanusM/India/fir/m1_compare.py ts/Totalsegmentator_dataset ts/hc ts/m1_compare.json
# Send back: ts/m1_compare.json (numbers only, no images).
#SBATCH --job-name=jm-m1
#SBATCH --account=def-aso22
#SBATCH --nodes=1
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=%x-%j.out
set -euo pipefail
module load StdEnv/2023 python/3.11.5
source $HOME/jm-venv/bin/activate
cd $SCRATCH/janusm
mkdir -p ts/hc
for d in ts/Totalsegmentator_dataset/s*/; do
  s=$(basename "$d")
  [ -f "ts/hc/$s/heart_myocardium.nii.gz" ] && continue
  TotalSegmentator -i "$d/ct.nii.gz" -o "ts/hc/$s" --task heartchambers_highres
done
