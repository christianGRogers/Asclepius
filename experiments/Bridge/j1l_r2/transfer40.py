"""Bridge v2 §3: the 40 train-560 cases on which Janus 0 and a1 are both predicted *in sample* after training, to see
whether a1's rim calibration moved away from Janus 0's (the t* transfer report). Deterministic: the 40 train-560 ids
(train 620 minus the tuning 60) with the smallest sha256('asclepius-j1l-r2-transfer:' + id). No locked or sealed id.
    python transfer40.py      # writes transfer40.json
"""
import hashlib, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
train560 = sorted(set(L['train620']) - set(L['tuning60']))
assert len(train560) == 560
pick = sorted(sorted(train560, key=lambda c: hashlib.sha256(f'asclepius-j1l-r2-transfer:{c}'.encode()).hexdigest())[:40])
assert not set(pick) & (set(L['locked100']) | set(S['sealed_icx_test']) | set(S['sealed_quality0']))
pin = hashlib.sha256('\n'.join(pick).encode()).hexdigest()
json.dump({'salt': 'asclepius-j1l-r2-transfer:', 'transfer40': pick, 'sha256_sorted_newline': pin},
          open(os.path.join(HERE, 'transfer40.json'), 'w'), indent=1)
print(len(pick), pin)
