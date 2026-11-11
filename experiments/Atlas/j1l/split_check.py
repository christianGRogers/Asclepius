"""Janus 1-L (D45): rebuild the 620/100 ImageCAS-X split from the repo's own lists and check it.

Reads only id lists (no image, no label, no score): trillium/sealed_test.json and ImageCAS-X's
train/val split as recorded by the icx14 job (trillium-results/icx14/results/splits.json, the same
filelists icx4 used). Writes experiments/Atlas/j1l/split_j1l.json.
"""
import hashlib, json, os, sys

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
S = json.load(open(os.path.join(R, 'trillium/sealed_test.json')))
SP = json.load(open(os.path.join(R, 'trillium-results/icx14/results/splits.json')))
SALT = 'asclepius-janus1-locked100:'

def key(c):
    return hashlib.sha256((SALT + c).encode()).hexdigest()

train, val, test = sorted(SP['train']), sorted(SP['val']), sorted(SP['test'])
open36 = sorted(S['open_icx_test']); dev44 = sorted(S['excluded_dev_cases_in_test'])
sealed80 = sorted(S['sealed_icx_test']) if 'sealed_icx_test' in S else None
q0 = None
for k, v in S.items():
    if isinstance(v, list) and len(v) == 20:
        q0 = sorted(v)
if sealed80 is None:
    sealed80 = sorted(c for c in test if c not in open36 and c not in dev44)
ranked = sorted(open36, key=key)
locked20, open16 = sorted(ranked[:20]), sorted(ranked[20:])
locked100 = sorted(val + locked20)
train620 = sorted(train + dev44 + open16)
checks = {
    'n_train560': len(train), 'n_val80': len(val), 'n_test160': len(test),
    'n_open36': len(open36), 'n_dev44': len(dev44), 'n_sealed80': len(sealed80),
    'n_locked100': len(locked100), 'n_train620': len(train620),
    'test_is_sealed_open_dev': sorted(sealed80 + open36 + dev44) == test,
    'train_locked_disjoint': not set(train620) & set(locked100),
    'sealed_in_train_or_locked': sorted(set(sealed80) & set(train620 + locked100)),
    'q0_sealed_in_train_or_locked': sorted(set(q0 or []) & set(train620 + locked100)),
    'q0_list_found': q0 is not None,
    'all_800': len(set(train620 + locked100 + sealed80)) == 800,
}
out = {'salt': SALT, 'locked20_ranked': [(c, key(c)[:12]) for c in ranked[:20]], 'locked20': locked20,
       'open16_to_train': open16, 'locked100': locked100, 'train620': train620, 'checks': checks,
       'sha256_locked100': hashlib.sha256('\n'.join(locked100).encode()).hexdigest(),
       'sha256_train620': hashlib.sha256('\n'.join(train620).encode()).hexdigest()}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'split_j1l.json'), 'w'), indent=1)
print(json.dumps(checks, indent=1)); print('locked20', locked20); print('open16', open16)
print('sha256 locked100', out['sha256_locked100']); print('sha256 train620', out['sha256_train620'])
ok = all(v for k, v in checks.items() if k.startswith(('test_is', 'train_locked', 'all_', 'q0_list'))) \
    and not checks['sealed_in_train_or_locked'] and not checks['q0_sealed_in_train_or_locked'] \
    and (checks['n_locked100'], checks['n_train620']) == (100, 620)
sys.exit(0 if ok else 1)
