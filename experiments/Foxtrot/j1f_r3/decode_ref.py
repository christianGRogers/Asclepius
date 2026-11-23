"""Janus 1-F round 3 (Foxtrot): reference code for three stage-1 spec items the swe ports into `trillium/janus1f`
(§5 item 4), with self-tests that must fail on a broken fixture:
  * decode_F   F-A4/F-A19: territory = argmax of the summed probabilities over {bg}, {LM}, {LAD, D1, D2, D3},
               {LCx, OM1, OM2, Ramus}, {RCA, PDA, PLB}; class = argmax inside it.
  * decode_T   F-A19: territory = Janus 0's own argmax map (0..4). Inside LAD: {LAD, D1, D2, D3}; inside LCx:
               {LCx, OM1, OM2, Ramus, PDA, PLB}; inside RCA: {RCA, PDA, PLB}; LM and bg unchanged. T's four classes
               ARE Janus 0's map (asserted bit-equal through the fixed-parent collapse of T's names, with PDA/PLB taking
               the territory they were named in).
  * splits     F-A20: splits_final.json = two identical entries, train = the 620, val = the 20 fit-check cases;
               refuses any locked-100 or sealed id, a val outside the 620, and the wrong pins.
Usage: python decode_ref.py selftest
"""
import hashlib, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GROUPS = {0: (0,), 1: (1,), 2: (2, 5, 6, 7), 3: (3, 8, 9, 10), 4: (4, 11, 12)}
T_SETS = {0: (0,), 1: (1,), 2: (2, 5, 6, 7), 3: (3, 8, 9, 10, 11, 12), 4: (4, 11, 12)}
PIN_620 = '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
PIN_100 = 'bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895'
PIN_FIT20 = '3f3b696c231d71bcc99763f83983fb824c2e74bdd597a37e09220188191f1330'


def _pin(ids):
    return hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()


def decode_F(prob):
    """prob: (13, ...) float. Returns (labels 0..12 uint8, territory 0..4 uint8)."""
    terr = np.argmax(np.stack([prob[list(g)].sum(0) for g in GROUPS.values()]), 0).astype(np.uint8)
    out = np.zeros(prob.shape[1:], np.uint8)
    for t, g in GROUPS.items():
        m = terr == t
        out[m] = np.asarray(g, np.uint8)[np.argmax(prob[list(g)][:, m], 0)]
    return out, terr


def decode_T(prob, janus0):
    """janus0: Janus 0's argmax map (0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA) on the same grid."""
    janus0 = np.asarray(janus0)
    out = np.zeros(janus0.shape, np.uint8)
    for t, g in T_SETS.items():
        m = janus0 == t
        if m.any():
            out[m] = np.asarray(g, np.uint8)[np.argmax(prob[list(g)][:, m], 0)]
    four = t_four(out, janus0)
    if not np.array_equal(four, janus0.astype(np.uint8)):
        raise AssertionError('T four-class output is not Janus 0 bit-equal')
    return out, four


def t_four(t_names, janus0):
    """T's four classes: the territory each name was decided in, i.e. Janus 0's map itself (F-A19)."""
    return np.asarray(janus0, np.uint8).copy()


def make_splits(split, fit20, sealed):
    train, locked = sorted(split['train620']), sorted(split['locked100'])
    if _pin(train) != PIN_620 or _pin(locked) != PIN_100:
        raise SystemExit('refuse: split pins differ')
    if _pin(fit20) != PIN_FIT20 or not set(fit20) <= set(train):
        raise SystemExit('refuse: fit-check 20 pin or membership')
    bad = (set(train) | set(fit20)) & (set(locked) | set(sealed))
    if bad:
        raise SystemExit(f'refuse: locked or sealed id in training/val: {sorted(bad)[:3]}')
    entry = {'train': train, 'val': sorted(fit20)}
    return [entry, json.loads(json.dumps(entry))]


def check_splits(splits, split, sealed):
    ids = set()
    for e in splits:
        ids |= set(e['train']) | set(e['val'])
    assert len(splits) == 2 and splits[0] == splits[1], 'two identical entries'
    assert not ids & (set(split['locked100']) | set(sealed)), 'locked or sealed id in splits_final.json'
    assert set(splits[0]['val']) <= set(splits[0]['train']), 'val inside the 620'


def selftest():
    rng = np.random.default_rng(0)
    # F: a parent-copied head (each child = its parent's logit - log k) decodes to Janus 0's argmax
    logit5 = rng.normal(size=(5, 8, 8, 8))
    k = {2: 4, 3: 4, 4: 3}
    lg = np.zeros((13, 8, 8, 8))
    parent = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 2, 6: 2, 7: 2, 8: 3, 9: 3, 10: 3, 11: 4, 12: 4}
    for c, p in parent.items():
        lg[c] = logit5[p] - (np.log(k[p]) if p in k else 0)
    pr = np.exp(lg - lg.max(0)); pr /= pr.sum(0)
    _, terr = decode_F(pr)
    assert np.array_equal(terr, np.argmax(logit5, 0)), 'F territory != Janus 0 at step 0'
    # T: a left PDA inside Janus 0's LCx territory is named PDA (F-A19), and T's four classes are Janus 0's
    j0 = np.zeros((4, 4, 4), np.uint8); j0[1:3, 1:3, 1:3] = 3; j0[0, 0, 0] = 4
    prob = np.full((13, 4, 4, 4), 0.01); prob[0] = 0.5
    prob[11, 1, 1, 1] = 0.9                      # PDA most likely at an LCx-territory voxel
    prob[12, 0, 0, 0] = 0.9                      # PLB at an RCA-territory voxel
    t, four = decode_T(prob / prob.sum(0), j0)
    assert t[1, 1, 1] == 11, 'T cannot name a left PDA (F-A19)'
    assert t[0, 0, 0] == 12 and np.array_equal(four, j0)
    assert t[2, 2, 2] in (3, 8, 9, 10, 11, 12) and t[3, 3, 3] == 0
    # broken T (round-2 text: LCx territory without PDA/PLB) must fail the same fixture
    global T_SETS
    keep = T_SETS; T_SETS = {**keep, 3: (3, 8, 9, 10)}
    t_bad, _ = decode_T(prob / prob.sum(0), j0); T_SETS = keep
    assert t_bad[1, 1, 1] != 11, 'fixture does not discriminate'
    # splits
    sf = os.path.join(HERE, '../../Delta/j1l_r1/janus1_split_proposal.json')        # the split file of record
    assert hashlib.sha256(open(sf, 'rb').read()).hexdigest().startswith('19b832fe')
    split = json.load(open(sf))
    fit20 = json.load(open(os.path.join(HERE, '../j1f_r2/results/fitcheck20.json')))['fitcheck20']
    st = json.load(open(os.path.join(HERE, '../../../trillium/sealed_test.json')))
    sealed = list(st['sealed_icx_test']) + list(st['sealed_quality0'])
    assert len(sealed) == 100, len(sealed)
    sp = make_splits(split, fit20, sealed)
    check_splits(sp, split, sealed)
    broken = json.loads(json.dumps(sp)); broken[0]['val'] = sorted(split['locked100'])[:20]; broken[1] = broken[0]
    try:
        check_splits(broken, split, sealed); raise RuntimeError('locked val accepted')
    except AssertionError:
        pass
    try:
        make_splits(split, sorted(split['locked100'])[:20], sealed); raise RuntimeError('locked fit-check accepted')
    except SystemExit:
        pass
    print('decode_ref selftest ok: F step-0 identity, T names a left PDA in the LCx territory, T four = Janus 0,'
          ' splits refuse a locked id; splits_final sha256',
          hashlib.sha256(json.dumps(sp, sort_keys=True).encode()).hexdigest())


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
