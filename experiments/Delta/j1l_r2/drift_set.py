"""Delta, Janus 1-L round 2: the drift set D60 for the label-free t* transfer check (Rule T).

D60 = 60 ImageCAS quality-0 cases that are not sealed and not a declared development case, ranked by
sha256('asclepius-janus1l-drift60:' + id). Derived from ids only, no image or label read:

  * ImageCAS-X = train 620 + locked 100 + sealed 80 (= 800, from Crucible's lists.json and sealed_test.json);
  * quality-0 = c0000..c0999 minus ImageCAS-X (= 200); minus sealed_quality0 (20) = 180;
  * minus excluded_dev_cases_in_quality0 (24) = 156; the first 60 by the salted hash are D60.

Why these cases: no Janus model trained on them (they have no ImageCAS-X label), they are not the locked 100, not
sealed (A14), not in the SegQueue14 pool (so not D27, D35 or reserve) and not in Janus-M's sets. Their images are
read only to compare two models' predicted volumes; their original ImageCAS masks are never read.

Usage: python drift_set.py            (writes drift60.json and checks it)
"""
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SALT = 'asclepius-janus1l-drift60:'


def derive():
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    icx = set(L['train620']) | set(L['locked100']) | set(S['sealed_icx_test'])
    assert len(icx) == 800
    q0 = {'c%04d' % i for i in range(1000)} - icx
    assert len(q0) == 200 and set(S['sealed_quality0']) <= q0
    pool = q0 - set(S['sealed_quality0']) - set(S['excluded_dev_cases_in_quality0'])
    assert len(pool) == 156, len(pool)
    ranked = sorted(pool, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())
    d60 = sorted(ranked[:60])
    # guards: nothing sealed, locked, trained on, or in Janus-M's sets
    jm = set(re.findall(r'c\d{4}', open(os.path.join(ROOT, 'configs', 'janusm', 'sealed-r1.json')).read()))
    bad = set(d60) & (set(S['sealed_quality0']) | set(S['sealed_icx_test']) | set(L['locked100'])
                      | set(L['train620']) | jm)
    assert not bad, bad
    ids = '\n'.join(d60)
    return dict(rule="quality-0, not sealed, not declared dev; first 60 by sha256('%s'+id)" % SALT,
                n_quality0=200, n_unsealed=180, n_eligible=156, drift60=d60,
                drift60_sha256_sorted_newline=hashlib.sha256(ids.encode()).hexdigest())


if __name__ == '__main__':
    out = derive()
    json.dump(out, open(os.path.join(HERE, 'drift60.json'), 'w'), indent=1)
    print(out['drift60_sha256_sorted_newline'], len(out['drift60']), out['drift60'][:5])
