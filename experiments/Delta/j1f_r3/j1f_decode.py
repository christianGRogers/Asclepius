"""Janus 1-F round 3 (Delta): reference implementations, with self-tests, of the stage-1 spec items that are not the
scorer (ruling §5 item 4): the F and T decodes (F-A19), the within-group maps that let T (and T_L, Q-F2-3) be built
from ANY later four-class map without keeping probabilities, the parent-copy identity check (F-A2), the
`splits_final.json` builder and its no-locked-id test (F-A20), the fit-check ids (F-A5), and the chunked
predict -> decode -> delete loop with `collect`'s marker check (F-A20). numpy only; synthetic data only.

1-F stage-1 channels: 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB.
Usage: python j1f_decode.py selftest
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../j1f_r1'))
import parent_copy as PC  # noqa: E402  (round 1's rule, F-A2)

# F's decode groups (F-A4, kept by F-A19): territory value -> channels
F_GROUPS = {0: (0,), 1: (1,), 2: (2, 5, 6, 7), 3: (3, 8, 9, 10), 4: (4, 11, 12)}
# T's name sets inside Janus 0's territories (F-A19): the LCx territory admits PDA and PLB
T_SETS = {2: (2, 5, 6, 7), 3: (3, 8, 9, 10, 11, 12), 4: (4, 11, 12)}
WG_DTYPE = np.uint8
FITCHECK_SALT = 'asclepius-j1f-fitcheck:'
MARKER = '.j1f_decoded'


def decode_f(prob):
    """prob (13, ...) summing to 1 -> 13-class map. Territory = argmax of summed group probabilities; class = argmax
    inside it."""
    terr = np.argmax(np.stack([prob[list(g)].sum(0) for g in F_GROUPS.values()]), 0).astype(np.uint8)
    return decode_in_territory(terr, within_group(prob, F_GROUPS))


def within_group(prob, sets=None):
    """{territory: uint8 map of the argmax channel inside its name set}. Kept per case after the npz is deleted (three
    uint8 volumes), so T and T_L can be built later from any four-class map."""
    sets = T_SETS if sets is None else {k: v for k, v in sets.items() if k >= 2}
    out = {}
    for t, chans in sets.items():
        chans = np.asarray(chans)
        out[t] = chans[np.argmax(prob[chans], 0)].astype(WG_DTYPE)
    return out


def decode_in_territory(terr4, wg):
    """terr4: 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA (any four-class map on the case's grid) -> 13-class names."""
    out = np.zeros(terr4.shape, np.uint8)
    out[terr4 == 1] = 1
    for t in (2, 3, 4):
        m = terr4 == t
        out[m] = wg[t][m]
    return out


def decode_t(janus0_4, wg):
    """Reading T (F-A19): Janus 0's territories, 1-F's names inside them. Returns (13-class map, four-class map); the
    four-class map IS janus0_4, asserted bit-equal (not a collapse of T's names)."""
    t13 = decode_in_territory(janus0_4, wg)
    four = np.asarray(janus0_4).astype(np.uint8)
    back = np.zeros_like(four)
    back[t13 == 1] = 1
    for t in (2, 3, 4):
        back[(janus0_4 == t) & (t13 > 0)] = t
    assert np.array_equal(back, four), 'T must keep Janus 0 territory for territory'
    return t13, four


def fitcheck_ids(train620):
    return sorted(sorted(train620, key=lambda c: hashlib.sha256((FITCHECK_SALT + c).encode()).hexdigest())[:20])


def splits_final(train620, locked100):
    """F-A20: two identical entries, train = the 620, val = the 20 fit-check cases (inside the 620)."""
    tr = sorted(train620)
    assert len(tr) == 620 and len(set(tr)) == 620 and not set(tr) & set(locked100)
    entry = {'train': tr, 'val': fitcheck_ids(tr)}
    return [entry, json.loads(json.dumps(entry))]


def check_splits_final(splits, locked100):
    """Refuse a splits_final with any locked id, or entries that are not the F-A20 shape."""
    lk = set(locked100)
    if len(splits) != 2 or splits[0] != splits[1]:
        raise ValueError('splits_final must hold two identical entries')
    for e in splits:
        bad = (set(e['train']) | set(e['val'])) & lk
        if bad:
            raise ValueError(f'locked id in splits_final: {sorted(bad)[:3]}')
        if not set(e['val']) <= set(e['train']) or len(e['val']) != 20:
            raise ValueError('val must be the 20 fit-check training cases')
    return True


# ---------------------------------------------------------------------------- chunked predict -> decode -> delete
def decode_chunk(pred_dir, out_dir, janus0_dir, cases, load_prob):
    """For each case: read nnU-Net's npz, write F, T and the within-group maps, then delete the npz, its pkl and
    nnU-Net's own argmax export. `collect` reads only maps that carry the marker."""
    os.makedirs(out_dir, exist_ok=True)
    for c in cases:
        prob = load_prob(os.path.join(pred_dir, c + '.npz'))
        wg = within_group(prob)
        f = decode_f(prob)
        j0 = np.load(os.path.join(janus0_dir, c + '.npy'))
        t13, _ = decode_t(j0, wg)
        np.savez_compressed(os.path.join(out_dir, c + '.npz'), F=f, T=t13, wg2=wg[2], wg3=wg[3], wg4=wg[4])
        for ext in ('.npz', '.pkl', '.nii.gz'):
            p = os.path.join(pred_dir, c + ext)
            if os.path.exists(p):
                os.remove(p)
        open(os.path.join(out_dir, c + MARKER), 'w').write(hashlib.sha256(f.tobytes()).hexdigest())


def collect_inputs(out_dir, cases):
    """Refuse any case whose decoded maps lack the marker, or whose marker does not match F."""
    for c in cases:
        m = os.path.join(out_dir, c + MARKER)
        if not os.path.exists(m):
            raise RuntimeError(f'{c}: no decode marker; collect reads only decode output')
        f = np.load(os.path.join(out_dir, c + '.npz'))['F']
        if open(m).read() != hashlib.sha256(f.tobytes()).hexdigest():
            raise RuntimeError(f'{c}: decode marker does not match F')
    return True


# ---------------------------------------------------------------------------- self-test
def _softmax(z):
    z = z - z.max(0, keepdims=True)
    e = np.exp(z)
    return e / e.sum(0, keepdims=True)


def _must_fail(fn, *a):
    try:
        fn(*a)
    except (AssertionError, ValueError, RuntimeError):
        return True
    return False


def selftest():
    rng = np.random.default_rng(0)
    shape = (13, 24, 24, 24)
    prob = _softmax(rng.normal(size=shape) * 2)
    # 1. F decode = argmax of summed group probabilities, then argmax inside; differs from plain argmax (tripwire)
    f = decode_f(prob)
    terr = np.argmax(np.stack([prob[list(g)].sum(0) for g in F_GROUPS.values()]), 0)
    back = np.zeros_like(terr)
    for t, g in F_GROUPS.items():
        back[np.isin(f, g)] = t
    assert np.array_equal(back, terr)
    plain = np.argmax(prob, 0)
    assert (plain != f).mean() > 0.01, 'hierarchical decode should differ from plain argmax on random logits'
    # fixture: a decode that takes plain argmax fails the territory identity
    pb = np.zeros_like(terr)
    for t, g in F_GROUPS.items():
        pb[np.isin(plain, g)] = t
    assert not np.array_equal(pb, terr)
    # 2. F-A19's T test: a left PDA in Janus 0's LCx territory is named PDA
    p = np.full((13, 1, 1, 3), 1e-3)
    p[3, 0, 0, :] = 0.30; p[11, 0, 0, :] = 0.50; p[4, 0, 0, :] = 0.15     # PDA most likely; LCx territory per Janus 0
    p /= p.sum(0, keepdims=True)
    j0 = np.full((1, 1, 3), 3, np.uint8)
    t13, four = decode_t(j0, within_group(p))
    assert (t13 == 11).all() and np.array_equal(four, j0), 'a left PDA in Janus 0 LCx territory must be named PDA'
    # fixture: T with F's groups inside the LCx territory cannot name it
    bad = decode_in_territory(j0, within_group(p, F_GROUPS))
    assert not (bad == 11).any()
    #    and a PDA in the RCA territory is still PDA; a D1 in the LAD territory is D1
    j0r = np.full((1, 1, 3), 4, np.uint8)
    assert (decode_t(j0r, within_group(p))[0] == 11).all()
    # 3. T's four classes are Janus 0's, bit-equal, on random maps
    j0 = rng.integers(0, 5, size=shape[1:]).astype(np.uint8)
    t13, four = decode_t(j0, within_group(prob))
    assert np.array_equal(four, j0) and ((t13 > 0) == (j0 > 0)).all()
    # T_L: the same within-group maps decode any later four-class map (1-L's), no probabilities needed
    jl = rng.integers(0, 5, size=shape[1:]).astype(np.uint8)
    assert np.array_equal(decode_t(jl, within_group(prob))[1], jl)
    # 4. parent copy: territory sums equal Janus 0's softmax within 1e-5, the hierarchical decode equals Janus 0's argmax
    F_, V = 32, 20000
    W0, b0 = rng.normal(size=(5, F_)), rng.normal(size=5)
    x = rng.normal(size=(F_, V)) * 3
    p0 = _softmax(W0 @ x + b0[:, None])
    W1, b1 = PC.parent_copy(W0, b0, PC.JANUS0, PC.STAGE1)
    p1 = _softmax(W1 @ x + b1[:, None])
    sums = np.stack([p1[list(g)].sum(0) for g in F_GROUPS.values()])
    assert np.abs(sums - p0).max() < 1e-5
    f1 = decode_f(p1)
    t1 = np.zeros_like(f1)
    for t, g in F_GROUPS.items():
        t1[np.isin(f1, g)] = t
    assert np.array_equal(t1, np.argmax(p0, 0))
    #    fixture: one head row not copied (OM2 left at a random init)
    W1b, b1b = W1.copy(), b1.copy(); W1b[9] = rng.normal(size=F_); b1b[9] = 0.0
    p1b = _softmax(W1b @ x + b1b[:, None])
    assert np.abs(np.stack([p1b[list(g)].sum(0) for g in F_GROUPS.values()]) - p0).max() > 1e-5
    # 5. splits_final (F-A20): no locked id; two identical entries; val = the 20 fit-check training cases
    ids = ['c%04d' % i for i in range(1000)]
    train, locked = ids[:620], ids[620:720]
    sp = splits_final(train, locked)
    assert check_splits_final(sp, locked) and sp[0]['val'] == fitcheck_ids(train)
    leak = json.loads(json.dumps(sp)); leak[0]['val'][0] = locked[0]; leak[1]['val'][0] = locked[0]
    assert _must_fail(check_splits_final, leak, locked)
    lk2 = json.loads(json.dumps(sp)); lk2[0]['train'].append(locked[5]); lk2[1]['train'].append(locked[5])
    assert _must_fail(check_splits_final, lk2, locked)
    assert _must_fail(check_splits_final, [sp[0]], locked)
    # 6. chunked predict -> decode -> delete, and collect's marker check
    tmp = tempfile.mkdtemp()
    try:
        pred, out, j0d = (os.path.join(tmp, d) for d in ('pred', 'dec', 'j0'))
        for d in (pred, j0d):
            os.makedirs(d)
        cases = ['c%04d' % i for i in range(3)]
        for c in cases:
            pr = _softmax(rng.normal(size=(13, 8, 8, 8)))
            np.savez_compressed(os.path.join(pred, c + '.npz'), probabilities=pr.astype(np.float16))
            open(os.path.join(pred, c + '.pkl'), 'w').write('x'); open(os.path.join(pred, c + '.nii.gz'), 'w').write('x')
            np.save(os.path.join(j0d, c + '.npy'), rng.integers(0, 5, size=(8, 8, 8)).astype(np.uint8))
        decode_chunk(pred, out, j0d, cases, lambda p: np.load(p)['probabilities'].astype(np.float32))
        assert os.listdir(pred) == [], 'decode must delete the npz, pkl and nnU-Net argmax export'
        assert collect_inputs(out, cases)
        os.remove(os.path.join(out, cases[1] + MARKER))
        assert _must_fail(collect_inputs, out, cases)
    finally:
        shutil.rmtree(tmp)
    print('j1f_decode selftest ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
