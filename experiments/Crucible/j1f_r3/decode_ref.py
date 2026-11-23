"""Janus 1-F round 3 (Crucible): reference decoding for J1F-A (F-A19, F-A20, F-A24), with the self-tests the swe
spec names. numpy only; no image is read.

Stage-1 channels: 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB.

  decode_F(P)              F: territory = argmax of the summed probabilities over the five decode groups (F-A4), then
                           the class = argmax inside the territory's group.
  name_maps(P, keep)       N: three uint8 maps, the argmax inside each NAMING SET of F-A19:
                             N_LAD = argmax over {LAD, D1, D2, D3};
                             N_LCx = argmax over {LCx, OM1, OM2, Ramus, PDA, PLB};
                             N_RCA = argmax over {RCA, PDA, PLB};
                           kept only where `keep` (default: 1 - p_bg >= KEEP_MIN, or Janus 0's foreground, as
                           `decode` passes it), 0 elsewhere, so the maps compress to almost nothing. Written by
                           `decode` beside F, so any four-class territory map can be named later without the
                           probabilities (the npz is deleted after each chunk, F-A20).
  name_territory(T4, N)    a reading from a four-class territory map: LM stays LM, bg stays bg, every LAD / LCx /
                           RCA voxel takes N_LAD / N_LCx / N_RCA; where N is 0 (outside `keep`), the trunk class.
                           T is bit-equal to the probabilities' reading because `keep` covers Janus 0's foreground;
                           T_L is equal wherever 1-L's foreground has 1 - p_bg >= KEEP_MIN in 1-F, and its trunk
                           class elsewhere (counted by `collect`). T = name_territory(Janus 0's argmax, N);
                           T_L = name_territory(Janus 1-L's shipped map, N) (F-A24, Q-F2-3).
  splits_final(train, val) F-A20's two identical entries, refusing a locked or sealed id anywhere.

Self-test: python decode_ref.py selftest
"""
import json
import sys

import numpy as np

GROUPS = ((0,), (1,), (2, 5, 6, 7), (3, 8, 9, 10), (4, 11, 12))         # F's decode groups (F-A4, F-A19)
NAMING = {2: (2, 5, 6, 7), 3: (3, 8, 9, 10, 11, 12), 4: (4, 11, 12)}       # T's naming sets (F-A19)
KEEP_MIN = 1e-3
TERR4 = np.array([0, 1, 2, 3, 4, 2, 2, 2, 3, 3, 3, 4, 4], np.uint8)       # F's group -> vessel (before F-A17's collapse)


def decode_F(P):
    P = np.asarray(P, np.float64)
    S = np.stack([P[list(g)].sum(0) for g in GROUPS])
    terr = np.argmax(S, 0)
    out = np.zeros(P.shape[1:], np.uint8)
    for gi, g in enumerate(GROUPS):
        m = terr == gi
        if m.any():
            out[m] = np.asarray(g, np.uint8)[np.argmax(P[list(g)][:, m], 0)]
    return out


def name_maps(P, keep=None):
    P = np.asarray(P)
    if keep is None:
        keep = (1 - P[0]) >= KEEP_MIN
    return {v: np.where(keep, np.asarray(s, np.uint8)[np.argmax(P[list(s)], 0)], 0).astype(np.uint8)
            for v, s in NAMING.items()}


def name_territory(T4, N):
    T4 = np.asarray(T4)
    out = np.where(T4 == 1, 1, 0).astype(np.uint8)
    for v, n in N.items():
        m = T4 == v
        out[m] = np.where(n[m] > 0, n[m], v)
    return out


def splits_final(train, val, locked, sealed):
    train, val = sorted(train), sorted(val)
    bad = (set(train) | set(val)) & (set(locked) | set(sealed))
    if bad:
        raise SystemExit(f'refused: locked or sealed id in splits_final.json: {sorted(bad)[:5]}')
    if not set(val) <= set(train):
        raise SystemExit('refused: val is not inside the 620')
    e = {'train': train, 'val': val}
    return [e, json.loads(json.dumps(e))]


def check_splits_file(path, locked, sealed):
    """F-A20's val test, on the file nnU-Net will read."""
    s = json.load(open(path))
    ids = {i for e in s for k in ('train', 'val') for i in e[k]}
    bad = ids & (set(locked) | set(sealed))
    assert len(s) == 2 and s[0] == s[1], 'splits_final.json must have two identical entries'
    assert not bad, f'locked or sealed id in splits_final.json: {sorted(bad)[:5]}'
    return True


def _softmax(x):
    e = np.exp(x - x.max(0, keepdims=True))
    return e / e.sum(0, keepdims=True)


def selftest():
    rng = np.random.default_rng(0)
    fails = []

    def check(name, cond):
        print(('PASS ' if cond else 'FAIL ') + name); cond or fails.append(name)

    # 1. F's territory equals the argmax of the group sums; a plain argmax differs (tripwire)
    P = _softmax(rng.normal(0, 2, (13, 24, 24, 24)))
    F = decode_F(P)
    S = np.stack([P[list(g)].sum(0) for g in GROUPS])
    check('F: territory = argmax of the group sums', (TERR4[F] == np.array([0, 1, 2, 3, 4])[np.argmax(S, 0)]).all())
    check(f'F: plain argmax differs on > 1 % of voxels ({(np.argmax(P, 0) != F).mean():.3f})',
          (np.argmax(P, 0) != F).mean() > 0.01)
    # 2. T from the name maps equals T computed directly from the probabilities (so the npz may be deleted)
    J0 = rng.integers(0, 5, (24, 24, 24)).astype(np.uint8)
    N = name_maps(P, ((1 - P[0]) >= KEEP_MIN) | (J0 > 0))      # as decode passes keep
    T = name_territory(J0, N)
    Td = np.zeros_like(T)
    Td[J0 == 1] = 1
    for v, s in NAMING.items():
        m = J0 == v
        Td[m] = np.asarray(s, np.uint8)[np.argmax(P[list(s)][:, m], 0)]
    check('T via name maps = T from probabilities, every voxel', (T == Td).all())
    # 3. T's four classes are Janus 0's map itself (F-A19), before any collapse
    check('T: vessel of each voxel = Janus 0\'s territory (bit-equal)',
          (np.where(np.isin(T, (11, 12)) & (J0 == 3), 3, TERR4[T]) == J0).all())
    # 4. F-A19's test: a left PDA in Janus 0's LCx territory is named PDA
    P2 = np.full((13, 8, 8, 8), 1e-3); P2[0] = 1.0
    P2[:, 4, 4, 1:7] = 1e-3; P2[3, 4, 4, 1:7] = 0.40; P2[11, 4, 4, 1:7] = 0.45; P2[4, 4, 4, 1:7] = 0.10
    P2 /= P2.sum(0, keepdims=True)
    J0b = np.zeros((8, 8, 8), np.uint8); J0b[4, 4, 1:7] = 3                # Janus 0 calls it LCx
    Tb = name_territory(J0b, name_maps(P2, J0b > 0))
    check('T: a left PDA inside Janus 0\'s LCx territory is named PDA', (Tb[4, 4, 1:7] == 11).all())
    # the broken fixture: Delta v2's naming set for LCx (no PDA/PLB) cannot name it
    broken = {2: (2, 5, 6, 7), 3: (3, 8, 9, 10), 4: (4, 11, 12)}
    Nb = {v: np.where(J0b > 0, np.asarray(s, np.uint8)[np.argmax(P2[list(s)], 0)], 0) for v, s in broken.items()}
    check('broken fixture (LCx set without PDA/PLB) fails the test', not (name_territory(J0b, Nb)[4, 4, 1:7] == 11).all())
    # F on the same voxels: PDA group sum 0.45 + 0.10 > LCx group 0.40 -> RCA group, named PDA; collapse decides side
    check('F: the same voxels decode as PDA (RCA group), side left to F-A17', (decode_F(P2)[4, 4, 1:7] == 11).all())
    # 5. T_L uses the same name maps with 1-L's territories
    L1 = J0.copy(); L1[J0 == 4] = 3
    TL = name_territory(L1, N)
    check('T_L: vessels are 1-L\'s map (bit-equal on LM/LAD/LCx territories)',
          (np.where(np.isin(TL, (11, 12)) & (L1 == 3), 3, TERR4[TL]) == L1).all())
    # outside keep, a territory voxel takes its trunk class
    Nk = name_maps(P, np.zeros(J0.shape, bool))
    check('outside keep: every territory voxel takes its trunk class', (name_territory(J0, Nk) == J0).all())
    # 6. F-A20: splits_final has no locked id
    train = ['c%04d' % i for i in range(30)]; locked = ['c%04d' % i for i in range(100, 110)]
    s = splits_final(train, train[:5], locked, [])
    check('splits_final: two identical entries, val inside train', s[0] == s[1] and set(s[0]['val']) <= set(train))
    try:
        splits_final(train + ['c0105'], train[:5], locked, []); check('a locked id in train is refused', False)
    except SystemExit:
        check('a locked id in train is refused', True)
    try:
        splits_final(train, ['c0101'], locked, []); check('a locked id as val is refused (L-A21 leak)', False)
    except SystemExit:
        check('a locked id as val is refused (L-A21 leak)', True)
    print('ALL PASS' if not fails else f'{len(fails)} FAIL')
    return not fails


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        sys.exit(0 if selftest() else 1)
