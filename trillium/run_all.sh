#!/bin/bash
# Download the cases and submit all four plan-tournament experiments on Trillium.
#
#   bash ~/Asclepius/trillium/run_all.sh
#
# Run it on the GPU login node (trig-login01), inside tmux: the first run downloads ~91 GB.
# It is safe to run again at any time, and you should: Delta only submits once Atlas has
# finished, and finished experiments copy their results back on the next run. Re-running
# never re-downloads finished files or duplicates a queued job.
#
# Layout (trillium/README.md): $ROOT/cases/ and $ROOT/experiments/{atlas,bridge,crucible,delta}/
# ROOT defaults to $SCRATCH/asclepius. Girder login is prompted once (or set GIRDER_TOKEN, or
# GIRDER_USER and GIRDER_PASSWORD).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${SCRATCH:?SCRATCH is not set; run this on a Trillium login node}"
ROOT="${ROOT:-$SCRATCH/asclepius}"
say() { printf '\n[run_all] %s\n' "$*"; }

say "updating the repository in $REPO"
git -C "$REPO" pull --ff-only || say "git pull failed; continuing with the checkout as it is"

say "1/3 cases -> $ROOT/cases"
mkdir -p "$ROOT/cases" "$ROOT/experiments"
python3 "$REPO/trillium/fetch_cases.py" "$ROOT/cases"

say "2/3 experiments -> $ROOT/experiments (results/ folders are kept)"
for e in atlas bridge crucible delta; do
    mkdir -p "$ROOT/experiments/$e"
    cp -a "$REPO/trillium/$e/." "$ROOT/experiments/$e/"
done

say "3/3 submitting (Atlas first; Bridge queues after it; Delta waits for Atlas to finish)"
status=0
for e in atlas bridge crucible delta; do
    say "./$e"
    (cd "$ROOT/experiments/$e" && "./$e") || { status=1; say "./$e failed (see above); continuing"; }
done

say "collecting any finished results"
for e in atlas bridge crucible; do
    (cd "$ROOT/experiments/$e" && "./$e" collect >/dev/null 2>&1) && say "$e: results in $ROOT/experiments/$e/results/" || true
done

say "done. squeue -u $USER shows the jobs."
say "Run this script again when Atlas has finished (submits Delta) and when everything has finished"
say "(copies results back). Results: $ROOT/experiments/*/results/"
exit $status
