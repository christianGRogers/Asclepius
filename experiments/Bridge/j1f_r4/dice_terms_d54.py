"""Janus 1-F round 4 (Bridge): Foxtrot's round-2 `dice_terms.py` re-run with D54's labels for the extended read.

`experiments/Foxtrot/j1f_r2/dice_terms.py` builds the extended-read sample as D47 Q3 left it without a tick: the LAD
group's voxels are the set {LAD-group, S1} ("without D47 Q3's complete flag"). Under D54 an undrawn branch is
confirmed absent, so those voxels are the singleton LAD-group. This script runs Foxtrot's own `case` twice on the same
training cases: once as written (`d47q3`), once with that one line removed (`d54`). Nothing else changes: the same
tube, patch, predictions, Dice options and CE.

Usage: python dice_terms_d54.py <label_dir with ids.json> <out.json> [n=10]
"""
import inspect
import json
import os
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
FOX = os.path.join(REPO, 'experiments', 'Foxtrot', 'j1f_r2')
split = json.load(open(os.path.join(REPO, 'experiments', 'Atlas', 'j1l', 'split_j1l.json')))
stub = types.ModuleType('pass1')
stub.TRAIN = set(split['train620'])                    # dice_terms imports only TRAIN from pass1 (the 620 check)
sys.modules['pass1'] = stub
sys.path.insert(0, FOX)
import dice_terms as D  # noqa: E402

LINE = 'S_ext[2, f(grp)] = True'
src = inspect.getsource(D.case)
assert src.count(LINE) == 1, 'dice_terms.case changed'
ns = dict(vars(D))
exec(src.replace('def case(', 'def case_d54(').replace(LINE, 'pass  # D54: the LAD group is a singleton'), ns)
case_d54 = ns['case_d54']

if __name__ == '__main__':
    d, outp = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    ids = json.load(open(os.path.join(d, 'ids.json')))[:n]
    res = {'d47q3': [], 'd54': []}
    for c in ids:
        p = os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz')
        res['d47q3'].append(D.case(p))
        res['d54'].append(case_d54(p))
        print(c, flush=True)
    names = ['LADgrp', 'S1', 'OM1', 'other']
    summ = {}
    for mode, rows in res.items():
        for sc in rows[0]['ext']:
            k = f'{mode}:ext:{sc}'
            summ[k] = {opt: dict(zip(names, np.mean([r['ext'][sc][opt] for r in rows], 0).round(4).tolist()))
                       for opt in ('leaf', 'ignore', 'merged')}
            summ[k]['ce'] = round(float(np.mean([r['ext'][sc]['ce'] for r in rows])), 5)
    json.dump({'cases': ids, 'mean': summ}, open(outp, 'w'), indent=1, sort_keys=True)
    for k, v in summ.items():
        print(k, json.dumps(v))
