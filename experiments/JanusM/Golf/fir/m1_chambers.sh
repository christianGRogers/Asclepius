#!/bin/bash
#SBATCH --job-name=jm-m1 --account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=64G --time=12:00:00
# Golf Job M1: TotalSegmentator heartchambers_highres on the 900 ImageCAS cases outside the coronary A14 seal.
# Resumable: re-submit until it prints "chambers: 900 of 900". Never reads a coronary-sealed case (refused below).
# Needs: $HOME/icx4-tseg-venv (Job S's venv), the licence already set with totalseg_set_license (typed by the lead,
# never committed), $SCRATCH/icx4/layout.json (icx4's case layout) and the repo at $SCRATCH/asclepius/repo.
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg
OUT=$SCRATCH/janusm/chambers; mkdir -p $OUT
python - <<'PY'
import json, os, subprocess, sys
R = os.environ['SCRATCH'] + '/asclepius/repo'
sys.path.insert(0, R + '/trillium/icx4/lib')
import sealed as S
seal = S.load(R + '/trillium/icx4/sealed_test.json')
ct = json.load(open(os.environ['SCRATCH'] + '/icx4/layout.json'))['cases']
cases = S.refuse_sealed(sorted(c for c in ct if c not in S.sealed_set(seal)), seal, 'janusm M1')
out = os.environ['SCRATCH'] + '/janusm/chambers'
for c in cases:
    o = f'{out}/{c}.nii.gz'
    if not os.path.exists(o):
        subprocess.run(['TotalSegmentator', '-i', ct[c]['ct'], '-o', o, '-ta', 'heartchambers_highres',
                        '--ml', '-d', 'gpu', '-q'])
print('chambers:', len([f for f in os.listdir(out) if f.endswith('.nii.gz')]), 'of', len(cases))
PY
