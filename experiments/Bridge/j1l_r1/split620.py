"""Bridge, track 1-L round 1: the D45 ImageCAS-X split, computed and checked.

D45: 620 training cases = ImageCAS-X train 560 + the 44 dev cases + 16 of open-36; 100 locked validation cases =
Janus 0's val 80 + the 20 of open-36 whose sha256('asclepius-janus1-locked100:' + id) is smallest, ids as in
`vault/Plans/Sealed test.md` (c-ids). The 80 sealed ImageCAS-X test cases and the 20 sealed quality-0 cases are
never in either list. Reads only id lists (no image, no label, no score).

    python3 experiments/Bridge/j1l_r1/split620.py      # writes split620.json next to this file
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SALT = 'asclepius-janus1-locked100:'

sealed = json.load(open(os.path.join(REPO, 'trillium', 'sealed_test.json')))
splits = json.load(open(os.path.join(REPO, 'trillium-results', 'icx14', 'results', 'splits.json')))  # ImageCAS-X's own
train560, val80, test160 = sorted(splits['train']), sorted(splits['val']), sorted(splits['test'])
open36 = sorted(sealed['open_icx_test'])
dev44 = sorted(sealed['excluded_dev_cases_in_test'])
sealed80 = set(sealed['sealed_icx_test'])
sealedq0 = set(sealed['sealed_quality0'])

rank = sorted(open36, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())
locked20, train16 = sorted(rank[:20]), sorted(rank[20:])
train620 = sorted(train560 + dev44 + train16)
locked100 = sorted(val80 + locked20)

checks = {
    'train560': len(train560) == 560, 'val80': len(val80) == 80, 'test160 = 80 + 36 + 44':
        set(test160) == sealed80 | set(open36) | set(dev44) and len(test160) == 160,
    'train620 has 620 distinct': len(set(train620)) == 620,
    'locked100 has 100 distinct': len(set(locked100)) == 100,
    'train620 and locked100 disjoint': not set(train620) & set(locked100),
    'no sealed case in either': not (set(train620) | set(locked100)) & (sealed80 | sealedq0),
    'every non-sealed ImageCAS-X case is in exactly one list':
        set(train620) | set(locked100) == set(train560 + val80 + test160) - sealed80,
}
assert all(checks.values()), checks

declared = set().union(*sealed['declared_dev_cases'].values())
out = {
    'rule': "D45: train 560 + dev 44 + 16 of open-36; locked = val 80 + the 20 of open-36 with the smallest "
            "sha256('asclepius-janus1-locked100:' + c-id)",
    'checks': checks,
    'locked20_from_open36': locked20,
    'train16_from_open36': train16,
    'counts': {'train620': len(train620), 'locked100': len(locked100)},
    'declared_development_cases_in_locked100': sorted(declared & set(locked100)),
    'declared_development_cases_in_train620': len(declared & set(train620)),
    'sha256_locked100_list': hashlib.sha256(','.join(locked100).encode()).hexdigest(),
    'sha256_train620_list': hashlib.sha256(','.join(train620).encode()).hexdigest(),
    'locked100': locked100,
    'train620': train620,
}
json.dump(out, open(os.path.join(HERE, 'split620.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('locked100', 'train620')}, indent=1))
