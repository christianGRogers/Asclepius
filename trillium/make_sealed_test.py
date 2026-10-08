"""Compute the official sealed test (Round 4 ruling, amendment A14).

    python3 trillium/make_sealed_test.py <imagecas-x dir with test.txt, exclude.txt>

Ranks the ImageCAS-X test cases and the quality-0 cases by
sha256('asclepius-sealed-round4:' + case_id), after removing every advocate's
declared development cases (experiments/<Name>/dev_cases.txt), and seals the
first 80 and the first 20 respectively. Writes trillium/sealed_test.json and
prints the lists. Deterministic: re-running gives the same answer.
"""
import glob
import hashlib
import json
import os
import sys

SALT = 'asclepius-sealed-round4:'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def icx_ids(path):
    return ['c%04d' % (int(x) - 1) for x in open(path).read().split()]


def rank(cases):
    return sorted(cases, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())


icx = sys.argv[1]
test, q0 = icx_ids(os.path.join(icx, 'test.txt')), icx_ids(os.path.join(icx, 'exclude.txt'))
assert len(test) == 160 and len(q0) == 200, (len(test), len(q0))

dev = {}
for f in sorted(glob.glob(os.path.join(REPO, 'experiments', '*', 'dev_cases.txt'))):
    who = os.path.basename(os.path.dirname(f))
    ids = {t.strip() for t in open(f).read().replace(',', '\n').split('\n')
           if t.strip().startswith('c')}
    dev[who] = sorted(ids)
excluded = set().union(*dev.values()) if dev else set()

test_ok = [c for c in rank(test) if c not in excluded]
q0_ok = [c for c in rank(q0) if c not in excluded]
assert len(test_ok) >= 80 and len(q0_ok) >= 20, (len(test_ok), len(q0_ok))
out = {
    'rule': "A14 (Round 4): rank by sha256('asclepius-sealed-round4:'+case) after excluding "
            'declared development cases; first 80 ImageCAS-X test and first 20 quality-0 are sealed',
    'sealed_icx_test': sorted(test_ok[:80]),
    'open_icx_test': sorted(test_ok[80:]),
    'sealed_quality0': sorted(q0_ok[:20]),
    'excluded_dev_cases_in_test': sorted(set(test) & excluded),
    'excluded_dev_cases_in_quality0': sorted(set(q0) & excluded),
    'declared_dev_cases': dev,
}
json.dump(out, open(os.path.join(REPO, 'trillium', 'sealed_test.json'), 'w'), indent=1)
print(json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in out.items()}, indent=1))
