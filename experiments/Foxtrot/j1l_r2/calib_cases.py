"""Foxtrot, track 1-L round 2: the label-free calibration set for the transfer of t* (Foxtrot v2 section 3).

ImageCAS has 1000 cases (c0000-c0999); ImageCAS-X labels 800 of them (train 560, val 80, test 160). The other 200 are
ImageCAS-X's quality-0 group (`exclude.txt`). 20 of those are sealed (A14) and 24 were declared development cases.
This script derives the quality-0 ids from ids alone (all 1000 minus D45's 620 and 100 minus the sealed ImageCAS-X
80), drops the sealed 20 and the 24 development cases, and takes the 60 with the smallest
sha256('asclepius-j1l-calib:' + id).

Use: **images only, never labels.** Janus 0 and each Janus 1-L network predict these 60 with probabilities, and
`t_transfer.py` compares their foreground volumes. No label of any kind is read for them, nothing is trained on them,
and none of them is in the locked 100, the 620 or the sealed lists (asserted here).
Output: results/calib60.json.  Run:  python3 calib_cases.py
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SALT = 'asclepius-j1l-calib:'


def main():
    split = json.load(open(os.path.join(ROOT, 'experiments', 'Delta', 'j1l_r1', 'janus1_split_proposal.json')))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    train, locked = set(split['train620']), set(split['locked100'])
    assert len(train) == 620 and len(locked) == 100 and not train & locked
    icx = train | locked | set(S['sealed_icx_test'])
    assert len(icx) == 800, len(icx)
    q0 = {f'c{i:04d}' for i in range(1000)} - icx
    assert len(q0) == 200 and set(S['sealed_quality0']) <= q0
    assert set(S['excluded_dev_cases_in_quality0']) <= q0 and len(S['excluded_dev_cases_in_quality0']) == 24
    pool = sorted(q0 - set(S['sealed_quality0']) - set(S['excluded_dev_cases_in_quality0']))
    assert len(pool) == 156, len(pool)
    ranked = sorted(pool, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())
    calib = sorted(ranked[:60])
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    assert not set(calib) & (sealed | train | locked)
    out = {'rule': f"quality-0 minus sealed 20 minus 24 declared-development; 60 smallest sha256('{SALT}'+id)",
           'use': 'images only; labels never read; never trained on', 'n_quality0': 200, 'n_eligible': len(pool),
           'calib60': calib,
           'sha256_sorted_newline': hashlib.sha256('\n'.join(calib).encode()).hexdigest()}
    json.dump(out, open(os.path.join(HERE, 'results', 'calib60.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'calib60'}, indent=1))
    print(' '.join(calib))


if __name__ == '__main__':
    main()
