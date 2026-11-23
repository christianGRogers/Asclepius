"""Janus 1-F round 3 (Atlas): the decode of record for `predict` (F-A4, F-A19, F-A20), plus a packed name map that lets
T and T_L be built from files after the probabilities are gone.

Stage-1 channels: 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB.

F (F-A4, kept by F-A19): territory = argmax of the summed probabilities over {bg}, {LM}, {LAD, D1, D2, D3},
   {LCx, OM1, OM2, Ramus}, {RCA, PDA, PLB}; class = argmax inside that territory.
NAMES (new): one uint8 per voxel holding three within-territory argmaxes at once:
   bits 0-1  the argmax over LAD_NAMES = (LAD, D1, D2, D3)
   bits 2-4  the argmax over LCX_NAMES = (LCx, OM1, OM2, Ramus, PDA, PLB)      (F-A19: the LCx territory admits PDA, PLB)
   bits 5-6  the argmax over RCA_NAMES = (RCA, PDA, PLB)
   Ties go to the lower index (numpy argmax), as in F.
compose(territory4, names): any four-class map (0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA) -> a stage-1 map, naming each voxel
   inside its territory. T = compose(Janus 0's Fir map, NAMES) (F-A19); T_L = compose(Janus 1-L's map, NAMES)
   (F-A24 / Q-F2-3). By construction the territory of compose(...) is the given map, bit for bit.

Why NAMES: F-A20 deletes each chunk's npz after decoding, so with only F and T written, T_L could never be built if
Janus 1-L is adopted after `predict` has run. NAMES is 1 byte per voxel, the size of F; with it, T and T_L are pure
functions of files, and `collect` can rebuild T from NAMES and check it against `predict`'s T byte for byte.

Self-test: python decode.py selftest
"""
import sys

import numpy as np

GROUPS = ((0,), (1,), (2, 5, 6, 7), (3, 8, 9, 10), (4, 11, 12))   # F's decode groups (F-A4)
LAD_NAMES = (2, 5, 6, 7)
LCX_NAMES = (3, 8, 9, 10, 11, 12)
RCA_NAMES = (4, 11, 12)
JANUS0_PARENT = (0, 1, 2, 3, 4, 2, 2, 2, 3, 3, 3, 4, 4)               # stage-1 channel -> Janus 0 channel (parent copy)


def _softmax(logits):
    m = logits.max(0, keepdims=True)
    e = np.exp(logits - m)
    return e / e.sum(0, keepdims=True)


def decode_F(prob):
    prob = np.asarray(prob)
    sums = np.stack([prob[list(g)].sum(0) for g in GROUPS])
    terr = sums.argmax(0)
    out = np.zeros(prob.shape[1:], np.uint8)
    for t, g in enumerate(GROUPS):
        sel = terr == t
        if sel.any():
            out[sel] = np.asarray(g, np.uint8)[prob[list(g)][:, sel].argmax(0)]
    return out


def names_pack(prob):
    prob = np.asarray(prob)
    a = prob[list(LAD_NAMES)].argmax(0).astype(np.uint8)
    b = prob[list(LCX_NAMES)].argmax(0).astype(np.uint8)
    c = prob[list(RCA_NAMES)].argmax(0).astype(np.uint8)
    return (a | (b << 2) | (c << 5)).astype(np.uint8)


def compose(territory4, names):
    t = np.asarray(territory4)
    n = np.asarray(names)
    if t.shape != n.shape:
        raise ValueError(f'territory {t.shape} and names {n.shape} differ')
    if not np.isin(t, (0, 1, 2, 3, 4)).all():
        raise ValueError('territory map has values outside 0..4')
    out = np.zeros(t.shape, np.uint8)
    out[t == 1] = 1
    for terr, table, shift, mask in ((2, LAD_NAMES, 0, 0b11), (3, LCX_NAMES, 2, 0b111), (4, RCA_NAMES, 5, 0b11)):
        sel = t == terr
        idx = (n[sel] >> shift) & mask
        if (idx >= len(table)).any():
            raise ValueError('corrupt names map')
        out[sel] = np.asarray(table, np.uint8)[idx]
    return out


def territory_of(stage1):
    """The decode territory of a stage-1 map, as a four-class map (F's groups; PDA/PLB -> RCA)."""
    lut = np.zeros(256, np.uint8)
    for t, g in enumerate(GROUPS):
        lut[list(g)] = t
    return lut[np.asarray(stage1)]


def parent_copy_logits(j0_logits):
    """Round 1's parent copy (Delta `parent_copy.py`): each child row copies its parent's row minus log(group size),
    so each territory's summed probability equals Janus 0's."""
    j0 = np.asarray(j0_logits, np.float64)
    size = {p: JANUS0_PARENT.count(p) for p in range(5)}
    return np.stack([j0[p] - np.log(size[p]) for p in JANUS0_PARENT])


def selftest():
    rng = np.random.default_rng(303)
    shape = (24, 20, 16)
    # 1. F's territory is the argmax of the summed probabilities; a plain 13-way argmax is not
    lg = rng.normal(0, 2.0, (13,) + shape)
    p = _softmax(lg)
    f = decode_F(p)
    sums = np.stack([p[list(g)].sum(0) for g in GROUPS])
    assert (territory_of(f) == sums.argmax(0)).all()
    plain = territory_of(p.argmax(0).astype(np.uint8))
    moved = float((plain != sums.argmax(0)).mean())
    assert moved > 0.01, moved
    # 2. parent copy: territory sums equal Janus 0's softmax within 1e-5, and F's territory equals Janus 0's argmax
    j0 = rng.normal(0, 3.0, (5,) + shape)
    pj = _softmax(j0)
    p13 = _softmax(parent_copy_logits(j0))
    s13 = np.stack([p13[list(g)].sum(0) for g in GROUPS])
    assert np.abs(s13 - pj).max() < 1e-5
    assert (territory_of(decode_F(p13)) == pj.argmax(0)).all()
    broken = parent_copy_logits(j0); broken[5] += 1.0                  # one head row not copied
    sb = np.stack([_softmax(broken)[list(g)].sum(0) for g in GROUPS])
    assert np.abs(sb - pj).max() > 1e-5
    # 3. F-A19: a left PDA inside Janus 0's LCx territory is named PDA by T; T's territory is Janus 0's map bit for bit
    names = names_pack(p)
    j0map = rng.integers(0, 5, shape).astype(np.uint8)
    lg2 = lg.copy()
    v = (3, 4, 5)
    j0map[v] = 3
    lg2[:, v[0], v[1], v[2]] = -5.0
    lg2[11, v[0], v[1], v[2]] = 5.0                                    # 1-F says PDA there
    p2 = _softmax(lg2)
    t = compose(j0map, names_pack(p2))
    assert t[v] == 11, t[v]
    assert (territory_of(t)[j0map != 3] == j0map[j0map != 3]).all()
    four = np.zeros(256, np.uint8); four[[1]] = 1; four[[2, 5, 6, 7]] = 2; four[[3, 8, 9, 10]] = 3; four[[4]] = 4
    tt = compose(j0map, names)
    terr_t = four[tt]; pp = np.isin(tt, (11, 12))
    terr_t[pp] = j0map[pp]                                             # PDA/PLB keep the territory they were named in
    assert (terr_t == j0map).all(), 'T must keep Janus 0 territory bit for bit'
    # 4. compose with names equals the direct within-territory argmax from probabilities
    direct = np.zeros(shape, np.uint8)
    direct[j0map == 1] = 1
    for terr, table in ((2, LAD_NAMES), (3, LCX_NAMES), (4, RCA_NAMES)):
        sel = j0map == terr
        direct[sel] = np.asarray(table, np.uint8)[p[list(table)][:, sel].argmax(0)]
    assert (direct == tt).all()
    # 5. F's own territory composed with NAMES reproduces F outside F's LCx territory (same name sets); inside it,
    #    compose may say PDA/PLB where F, whose LCx group has no PDA/PLB, cannot (F-A19 applies to T only)
    cf, tf = compose(territory_of(f), names), territory_of(f)
    assert (cf[tf != 3] == f[tf != 3]).all()
    assert np.isin(cf[tf == 3], LCX_NAMES).all() and ((cf[tf == 3] == f[tf == 3]) | np.isin(cf[tf == 3], (11, 12))).all()
    # 6. T_L: another territory map gives its own territories
    lmap = rng.integers(0, 5, shape).astype(np.uint8)
    tl = compose(lmap, names)
    assert (tl[lmap == 0] == 0).all() and (tl[lmap == 1] == 1).all()
    assert np.isin(tl[lmap == 2], LAD_NAMES).all() and np.isin(tl[lmap == 4], RCA_NAMES).all()
    # 7. refusals
    for bad in (np.full(shape, 7, np.uint8),):
        try:
            compose(bad, names); raise AssertionError('accepted a bad territory map')
        except ValueError:
            pass
    print(f'decode selftest ok (plain argmax moves {moved:.1%} of voxels across territories)')


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
