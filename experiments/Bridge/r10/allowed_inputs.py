"""Bridge, Round 10: the pool volumes Janus 0 may predict before wave 1 (A31 inputs), as a fetch list.

Allowed: every pool volume that is neither sealed (D27/D32, through the project's guard) nor in the seal's reserve
(the 200 and 250 steps as re-stated around the D35 decision set, `decision_set_proposal.json`). The decision set's own
volumes are allowed: Janus 0's predictions on them are the baseline every fine-tune is compared with.
Reserved volumes are left out until rule C has decided the seal size; the ones then released can be predicted later.

Output: a subset of ``trillium/totalseg/inputs.json`` (Girder item ids of SegQueue/cases) for
``trillium/totalseg/lib/fetch.py``, plus a plain name list. Refuses (exit 2) if anything sealed or reserved would be
written.

Usage: python3 experiments/Bridge/r10/allowed_inputs.py --out DIR      (writes DIR/inputs.json, DIR/volumes.txt)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
from segtrain.pool_seal import ingest_patient, load_pool_seal  # noqa: E402

INPUTS = os.path.join(REPO, 'trillium', 'totalseg', 'inputs.json')
PROPOSAL = os.path.join(HERE, 'decision_set_proposal.json')
STEP1 = 'reserve_200_step (extension_order[:50], unchanged)'
STEP2 = 'reserve_250_step (extension_order[50:] skipping decision patients, then continued)'


def allowed(items, guard, reserved):
    keep, refused = [], {'sealed': 0, 'reserved': 0}
    for it in items:
        stem = it['name'][:-len('.nii.gz')]
        if guard.is_sealed(stem) or guard.is_sealed(it['name']):
            refused['sealed'] += 1
        elif ingest_patient(stem) in reserved:
            refused['reserved'] += 1
        else:
            keep.append(it)
    return keep, refused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    guard = load_pool_seal()
    prop = json.load(open(PROPOSAL))
    reserved = set(prop[STEP1]) | set(prop[STEP2])
    items = json.load(open(INPUTS))
    keep, refused = allowed(items, guard, reserved)
    # defence in depth
    for it in keep:
        stem = it['name'][:-len('.nii.gz')]
        if guard.is_sealed(stem) or ingest_patient(stem) in reserved:
            sys.exit(2)
    os.makedirs(a.out, exist_ok=True)
    json.dump(keep, open(os.path.join(a.out, 'inputs.json'), 'w'), indent=1)
    open(os.path.join(a.out, 'volumes.txt'), 'w').write('\n'.join(it['name'] for it in keep) + '\n')
    dec = {v for v in prop['volumes']}
    print(json.dumps({'allowed': len(keep), 'of_which_decision_set': sum(it['name'] in dec for it in keep),
                      'refused': refused, 'GB': round(sum(it['size'] for it in keep) / 1e9, 1)}))


if __name__ == '__main__':
    main()
