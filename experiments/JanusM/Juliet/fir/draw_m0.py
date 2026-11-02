"""Janus-M case draws (Juliet v1), from ImageCAS-X *training* cases only, by salted hashes, in this order:
  1. the proposed Janus-M seal: 60 cases, salt 'asclepius-janusm-seal-r1:' (never opened until acceptance);
  2. the proposed Janus-M decision set: 40 cases, salt 'asclepius-janusm-decision-r1:' (never trained on);
  3. Job M0: 40 cases, salt 'asclepius-janusm-juliet-r1:', from the training cases left after 1 and 2.
Only 3 is used now. 1 and 2 are drawn first so that M0 can never touch them, whatever the judge rules later.

Training cases only (splits.json 'train'): no sealed case (A14), no val-80 or ImageCAS-X test case is touched, so no
coronary decision set is read. The script also refuses any case listed in trillium/icx4/sealed_test.json.

Usage (Fir login node): python draw_m0.py $SCRATCH/icx4/splits.json $SCRATCH/janusm/m0_cases.txt
  (also writes janusm_seal_proposal.txt and janusm_decision_proposal.txt next to the output)
"""
import hashlib
import json
import sys
from pathlib import Path

DRAWS = [('janusm_seal_proposal.txt', 'asclepius-janusm-seal-r1:', 60),
         ('janusm_decision_proposal.txt', 'asclepius-janusm-decision-r1:', 40),
         (None, 'asclepius-janusm-juliet-r1:', 40)]
REPO = Path(__file__).resolve().parents[4]


def sealed_ids():
    """The A14 sealed 100, plus every ImageCAS-X test-split case named in the file (open 36, development 44):
    none of these is a training case, so a hit means the split file is not what it should be."""
    sys.path.insert(0, str(REPO / 'trillium/icx4/lib'))
    import sealed  # the project's own validated loader
    S = sealed.load(str(REPO / 'trillium/icx4/sealed_test.json'))
    return sealed.sealed_set(S) | set(S['open_icx_test']) | set(S['excluded_dev_cases_in_test'])


def main(splits, out):
    train = json.load(open(splits))['train']
    sealed = sealed_ids()
    bad = sorted(set(train) & sealed)
    if bad:
        sys.exit(f'REFUSED: {len(bad)} training cases are sealed: {bad[:5]}')
    left = sorted(train)
    for name, salt, n in DRAWS:
        pick = sorted(left, key=lambda c: hashlib.sha256((salt + c).encode()).hexdigest())[:n]
        left = [c for c in left if c not in pick]
        path = Path(out) if name is None else Path(out).with_name(name)
        path.write_text('\n'.join(sorted(pick)) + '\n')
        print(f'{path.name}: {len(pick)} cases')
    print(f'from {len(train)} training cases; 0 sealed; {len(left)} left for Janus-M training')


if __name__ == '__main__':
    main(*sys.argv[1:3])
