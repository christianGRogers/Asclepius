"""Reference implementations, with self-tests, for the converged stage-1 spec (Round 2 ruling §5 item 4):
  * decode_F   F's hierarchical decode (master plan §1): territory = argmax of the summed probabilities over the five
               groups, class = argmax inside it;
  * decode_T   F-A19: territory = Janus 0's argmax; inside its LCx territory the class runs over {LCx, OM1, OM2, Ramus,
               PDA, PLB}, inside its RCA territory over {RCA, PDA, PLB}; LAD over {LAD, D1, D2, D3}; LM and bg kept.
               T's four classes ARE Janus 0's map (asserted bit-equal through T4);
  * splits     F-A20: splits_final.json with two identical entries, train = the 620, val = the 20 fit-check cases (the
               smallest sha256('asclepius-j1f-fitcheck:' + id)); refuses any locked or sealed id anywhere in it.
Values: 0 bg 1 LM 2 LAD 3 LCx 4 RCA 5 D1 6 D2 7 D3 8 OM1 9 OM2 10 Ramus 11 PDA 12 PLB. Usage: python3 decode_ref.py
selftest [icx_dir]  (with icx_dir: also prints the 20 fit-check ids and their list sha256 from split.json)"""
import hashlib, json, os, sys
import numpy as np

GROUPS = [(0,), (1,), (2, 5, 6, 7), (3, 8, 9, 10), (4, 11, 12)]
TO4 = np.array([0, 1, 2, 3, 4, 2, 2, 2, 3, 3, 3, 4, 4], np.uint8)       # the decode group of each class (not D47's collapse)
T_ALLOWED = {0: (0,), 1: (1,), 2: (2, 5, 6, 7), 3: (3, 8, 9, 10, 11, 12), 4: (4, 11, 12)}
FITCHECK_SALT = 'asclepius-j1f-fitcheck:'


def decode_F(p):
    """p: (13, ...) probabilities that sum to 1 over axis 0 -> uint8 class map."""
    g = np.stack([p[list(k)].sum(0) for k in GROUPS])
    terr = g.argmax(0)
    out = np.zeros(p.shape[1:], np.uint8)
    for t, k in enumerate(GROUPS):
        m = terr == t
        out[m] = np.asarray(k, np.uint8)[p[list(k)][:, m].argmax(0)]
    return out, terr.astype(np.uint8)


def decode_T(p, j0):
    """p: (13, ...) 1-F probabilities; j0: Janus 0's argmax (0 bg 1 LM 2 LAD 3 LCx 4 RCA) on the same grid."""
    out = np.zeros(p.shape[1:], np.uint8)
    for t, k in T_ALLOWED.items():
        m = j0 == t
        out[m] = np.asarray(k, np.uint8)[p[list(k)][:, m].argmax(0)]
    four = np.where(np.isin(out, (11, 12)), j0, TO4[out])                 # T's four classes = Janus 0's, by construction
    assert np.array_equal(four, j0), 'T must keep Janus 0 territory for territory (F-A19)'
    return out


def fitcheck20(train620):
    return sorted(sorted(train620, key=lambda c: hashlib.sha256((FITCHECK_SALT + c).encode()).hexdigest())[:20])


def splits(train620, locked100, sealed):
    tr = sorted(train620)
    bad = (set(tr) & set(locked100)) | (set(tr) & set(sealed))
    if len(tr) != 620 or bad:
        raise SystemExit(f'REFUSE: train is not the 620 ({len(tr)}) or holds locked/sealed ids {sorted(bad)[:5]}')
    val = fitcheck20(tr)
    s = [{'train': tr, 'val': val}, {'train': tr, 'val': val}]
    check_splits(s, locked100, sealed)
    return s


def check_splits(s, locked100, sealed):
    ids = {c for e in s for k in ('train', 'val') for c in e[k]}
    bad = ids & (set(locked100) | set(sealed))
    if bad:
        raise SystemExit(f'REFUSE: splits_final.json holds locked or sealed ids {sorted(bad)[:5]}')
    if len(s) != 2 or s[0] != s[1] or not set(s[0]['val']) <= set(s[0]['train']):
        raise SystemExit('REFUSE: splits_final.json must be two identical entries with val inside train')


def selftest(icx_dir=None):
    rng = np.random.default_rng(0)
    p = rng.dirichlet(np.ones(13), size=(6, 7, 8)).transpose(3, 0, 1, 2).astype(np.float64)
    f, terr = decode_F(p)
    g = np.stack([p[list(k)].sum(0) for k in GROUPS])
    assert (terr == g.argmax(0)).all() and (TO4[f] == terr).all()
    assert (f != p.argmax(0)).mean() > 0.01, 'tripwire: hierarchical decode must differ from plain argmax'
    # T: one voxel in Janus 0's LCx territory where PDA is 1-F's best class: T names it PDA (F-A19)
    q = np.full((13, 1, 1, 3), 0.01); q[11, 0, 0, 0] = 0.5; q[3, 0, 0, 0] = 0.3          # PDA > LCx
    q[12, 0, 0, 1] = 0.6; q[4, 0, 0, 1] = 0.2                                              # PLB in J0's RCA
    q[8, 0, 0, 2] = 0.6; q[2, 0, 0, 2] = 0.2                                               # OM1 wins, but J0 says LAD
    q /= q.sum(0, keepdims=True)
    j0 = np.array([[[3, 4, 2]]], np.uint8)
    t = decode_T(q, j0)
    assert t[0, 0, 0] == 11, 'a left PDA in Janus 0 LCx territory must be named PDA'
    assert t[0, 0, 1] == 12 and t[0, 0, 2] in (2, 5, 6, 7), t
    # the old T (Delta v2: LCx territory over {LCx, OM1, OM2, Ramus}) could not do it
    assert (3, 8, 9, 10)[int(np.argmax(q[[3, 8, 9, 10], 0, 0, 0]))] != 11
    # T on random probabilities keeps Janus 0's map
    j0r = rng.integers(0, 5, size=(6, 7, 8)).astype(np.uint8)
    decode_T(p, j0r)
    # splits: a locked id refuses; the right file passes
    tr = [f'c{i:04d}' for i in range(620)]; lk = [f'c{i:04d}' for i in range(620, 720)]; se = ['c0900']
    s = splits(tr, lk, se)
    assert len(s[0]['val']) == 20 and s[0] == s[1]
    for broken in ([{'train': tr, 'val': s[0]['val'][:19] + ['c0650']}] * 2, [{'train': tr + ['c0700'], 'val': s[0]['val']}] * 2):
        try:
            check_splits(broken, lk, se); raise AssertionError('locked id not refused')
        except SystemExit:
            pass
    try:
        splits(tr[:-1] + ['c0650'], lk, se); raise AssertionError('locked id in train not refused')
    except SystemExit:
        pass
    print('decode_ref selftest ok')
    if icx_dir:
        sp = json.load(open(os.path.join(icx_dir, 'split.json')))
        fc = fitcheck20(sp['train620'])
        print('fitcheck20', fc)
        print('fitcheck20 sha256', hashlib.sha256('\n'.join(fc).encode()).hexdigest())
        sealed = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../trillium/sealed_test.json')))
        sealed = list(sealed['sealed_icx_test']) + list(sealed['sealed_quality0'])
        assert len(sealed) == 100
        s = splits(sp['train620'], sp['locked100'], sealed)
        print('splits_final sha256', hashlib.sha256(json.dumps(s, indent=1).encode()).hexdigest())


if __name__ == '__main__':
    if sys.argv[1:2] == ['selftest']:
        selftest(sys.argv[2] if len(sys.argv) > 2 else None)
