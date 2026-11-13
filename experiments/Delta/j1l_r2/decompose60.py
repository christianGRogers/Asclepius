"""Delta, Janus 1-L round 2 (#302, Round 1 ruling §5 item 5): where Janus 0's tree-F1 is lost on the tuning 60.

Splits each class's tF1 loss into what a later round could act on: breaks, naming, extent and width/offset. It runs
on CPU after Job 0, on Janus 0's argmax export of the **tuning 60 only** (dev-44 + the 16 open-36 cases D45 sends to
training; Janus 0 never trained on them). It refuses every other case: the locked 100 is never decomposed (L-A7),
and a sealed case is never read (A14).

The metric is the frozen one (A1c 24441cf8…5254, through icx4's `tf1_score`, the same crop, ostia and flags as the
scorer of record). The script re-derives each class's recall and precision from the same pieces tree_f1 uses and
**asserts they equal tree_f1's own** before it splits them (classes on the fallback centreline are counted, not
split).

Recall side: every reference centreline point of class c is exactly one of
  hit        predicted c, in a piece connected to an ostium (tree_f1's recall numerator);
  naming     predicted as another vessel class, in a piece connected to an ostium;
  cut        predicted as a vessel, but its piece does not reach an ostium (a break upstream);
  miss_near  not predicted, but predicted vessel lies within 1.5 mm (an off-centre or thin drawing);
  miss_gap   not predicted, nothing within 1.5 mm, inside the tree (the missed run does not end at a tip): a gap;
  miss_tip   not predicted, nothing within 1.5 mm, the missed run reaches a centreline endpoint: extent lost.
Precision side: every predicted centreline point of class c is
  correct    inside reference class c (tree_f1's precision numerator);
  naming     inside another reference vessel class;
  out_near   outside the reference, within 1.5 mm of it (boundary or skeleton offset);
  out_far    outside the reference, farther (extra extent, a vein, a blob).
Reported per class: mean tF1, and for each category the mean tF1 gain if that category alone were fixed (its points
counted as hits / correct). Fixing naming also moves the other classes' points that lie in reference c into c's
predicted centreline (precision = (correct + in) / (predicted - naming + in)), so a swapped class gains in full. "Breaks" = cut + miss_gap, "extent" = miss_tip, "naming" = both naming terms,
"width/offset" = miss_near + out_near, "extra" = out_far.

Usage (Trillium login node, after Job 0; the lead runs it):
  python decompose60.py --pred $W/thr/t0.50 --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json \
      --lists $R/experiments/Crucible/j1l_r1/lists.json --out $W/decompose60_t0.50.json --np 8
Self-test (synthetic tree, no data):  python decompose60.py --selftest
"""
import argparse
import json
import os
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Atlas'))

import tf1_score  # noqa: E402  (frozen metric after the A1c hash check; same crop and flags as the scorer)
from territory import to_four  # noqa: E402

NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
REC = ('hit', 'naming', 'cut', 'miss_near', 'miss_gap', 'miss_tip')
PRE = ('correct', 'naming', 'out_near', 'out_far')
GROUPS = {'breaks': (('r', 'cut'), ('r', 'miss_gap')), 'extent': (('r', 'miss_tip'),),
          'naming': (('r', 'naming'), ('p', 'naming')), 'width_offset': (('r', 'miss_near'), ('p', 'out_near')),
          'extra': (('p', 'out_far'),)}


def f1(r, p):
    return 2 * r * p / (r + p) if r + p else 0.0


def decompose_arrays(ref, pred, sp, aorta=None, ct=None):
    """Per class: the tree_f1 numbers, the category counts, and the one-category-fixed tF1."""
    T = tf1_score.T or tf1_score.load_metric()
    sp = np.asarray(sp, float)
    sl = tf1_score._bbox([ref > 0, pred > 0], sp, ref.shape)
    ref, pred = ref[sl], pred[sl]
    aorta = aorta[sl] if aorta is not None else None
    ct = ct[sl] if ct is not None else None
    rep = T.find_ostia(ref, sp, aorta=aorta, ct=ct)
    tol = T.TOLERANCE_MM
    official = T.tree_f1(ref, pred, sp, tol_mm=tol, ostia=rep)
    # -- the same pieces as tree_f1 (tf1.py lines 'pred = ...' to 'plab_sk')
    pred = np.where(T.remove_small_components(pred > 0, T.MIN_COMPONENT_VOXELS), pred, 0)
    cl = T._Centreline(ref > 0, sp)
    pm = pred > 0
    grown = ndimage.binary_dilation(pm, structure=T._ball(tol / 2.0, sp)) if pm.any() else pm
    gl, _ = T.components(grown)
    comp_of_pred = np.where(pm, gl, 0)
    reach = max(tol, float(sp.max()))
    rr = np.ceil(reach / sp).astype(int)
    rooted_comps = set()
    for p in rep.points:
        win = tuple(slice(max(p[k] - rr[k], 0), min(p[k] + rr[k] + 1, ref.shape[k])) for k in range(3))
        sub = comp_of_pred[win]
        g = np.argwhere(sub > 0)
        if len(g):
            off = np.array([s.start for s in win])
            d = np.linalg.norm((g + off - np.array(p)) * sp, axis=1)
            rooted_comps |= set(sub[tuple(g[d <= reach].T)].tolist())
    rpts = cl.pts
    rlab = ref[tuple(rpts.T)]
    plab = pred[tuple(rpts.T)]
    rooted = np.isin(comp_of_pred[tuple(rpts.T)], list(rooted_comps)) if rooted_comps else np.zeros(len(rpts), bool)
    d_pred = ndimage.distance_transform_edt(~pm, sampling=sp) if pm.any() else np.full(ref.shape, np.inf)
    near = d_pred[tuple(rpts.T)] <= tol
    # missed runs: connected runs (centreline graph) of not-predicted, not-near points; a run is a tip if it holds a
    # centreline endpoint (degree <= 1) farther than 3 mm from every ostium
    far_miss = (plab == 0) & ~near
    osts = np.array(rep.points) if rep.points else np.zeros((0, 3))
    d_ost = (np.min(np.linalg.norm((rpts[:, None, :] - osts[None]) * sp, axis=2), axis=1)
             if len(osts) else np.full(len(rpts), np.inf))
    endpoint = (cl.degree <= 1) & (d_ost > 3.0)
    tip = np.zeros(len(rpts), bool)
    seen = np.zeros(len(rpts), bool)
    for v in np.nonzero(far_miss)[0]:
        if seen[v]:
            continue
        run, stack = [], [int(v)]
        seen[v] = True
        while stack:
            u = stack.pop(); run.append(u)
            for w in cl.neighbours(u):
                w = int(w)
                if far_miss[w] and not seen[w]:
                    seen[w] = True; stack.append(w)
        if endpoint[run].any():
            tip[run] = True
    psk = T._skeletonise(pm)
    plab_sk = pred[psk]
    rlab_sk = ref[psk]
    d_ref = ndimage.distance_transform_edt(ref == 0, sampling=sp)[psk]
    out = {'provisional': bool(rep.provisional),
           'flagged_classes': [NAMES[c] for c in tf1_score.classes_flagged(ref, rep)],
           'fallback_classes': [NAMES[int(c)] for c in official.classes_without_centreline], 'classes': {}}
    for c in NAMES:
        if c not in official.per_class:
            continue
        name = NAMES[c]
        g = rlab == c
        if not g.any():                       # fallback-centreline class: tree_f1 scored it; not split here
            out['classes'][name] = {'tf1': float(official.per_class[c]), 'split': False}
            continue
        r = {'hit': int((g & (plab == c) & rooted).sum()),
             'naming': int((g & (plab > 0) & (plab != c) & rooted).sum()),
             'cut': int((g & (plab > 0) & ~rooted).sum()),
             'miss_near': int((g & (plab == 0) & near).sum()),
             'miss_gap': int((g & far_miss & ~tip).sum()),
             'miss_tip': int((g & far_miss & tip).sum())}
        assert sum(r.values()) == int(g.sum())
        pc = plab_sk == c
        p = {'correct': int((pc & (rlab_sk == c)).sum()),
             'naming': int((pc & (rlab_sk > 0) & (rlab_sk != c)).sum()),
             'out_near': int((pc & (rlab_sk == 0) & (d_ref <= tol)).sum()),
             'out_far': int((pc & (rlab_sk == 0) & (d_ref > tol)).sum())}
        p_in = int(((plab_sk > 0) & (plab_sk != c) & (rlab_sk == c)).sum())   # others' points inside reference c
        nr, npr = int(g.sum()), int(pc.sum())
        rec = r['hit'] / nr
        prec = p['correct'] / npr if npr else 0.0
        assert abs(rec - official.recall[c]) < 1e-9 and abs(prec - official.precision[c]) < 1e-9, \
            (name, rec, official.recall[c], prec, official.precision[c])
        base = f1(rec, prec)
        gain = {}
        for k in REC[1:]:
            gain['r_' + k] = f1((r['hit'] + r[k]) / nr, prec) - base
        def prec_fixed(keys):
            num, den = p['correct'] + sum(p[k] for k in keys if k != 'naming'), npr
            if 'naming' in keys:
                num, den = num + p_in, den - p['naming'] + p_in
            return num / den if den else 0.0
        for k in PRE[1:]:
            gain['p_' + k] = f1(rec, prec_fixed([k])) - base
        grp = {}
        for gname, parts in GROUPS.items():
            rr_ = r['hit'] + sum(r[k] for s_, k in parts if s_ == 'r')
            grp[gname] = f1(rr_ / nr, prec_fixed([k for s_, k in parts if s_ == 'p'])) - base
        out['classes'][name] = {'tf1': base, 'split': True, 'recall': r, 'precision': dict(p, others_in=p_in),
                                'gain': gain,
                                'group_gain': grp}
    return out


def decompose_case(args):
    case, pred_dir, icx_dir, aorta_dir, ct_path = args
    import nibabel as nib
    try:
        if tf1_score.T is None:
            tf1_score.load_metric()
        pred = np.asarray(nib.load(os.path.join(pred_dir, f'{case}.nii.gz')).dataobj).astype(np.uint8)
        li = nib.load(os.path.join(icx_dir, f'{int(case[1:]) + 1}.coronary.nii.gz'))
        sp = np.array(li.header.get_zooms()[:3], float)
        ref = to_four(np.asarray(li.dataobj).astype(np.int64), sp).astype(np.uint8)
        ap = os.path.join(aorta_dir, f'{case}_aorta.nii.gz') if aorta_dir else None
        aorta = np.asarray(nib.load(ap).dataobj) > 0 if ap and os.path.exists(ap) else None
        ct = np.asarray(nib.load(ct_path).dataobj).astype(np.float32) if ct_path and os.path.exists(ct_path) else None
        return dict(case=case, **decompose_arrays(ref, pred, sp, aorta=aorta, ct=ct))
    except Exception as e:  # noqa: BLE001
        return dict(case=case, error=repr(e)[:300])


def summarise(rows):
    """Decisive rows only (A1a/A1b): per class mean tF1 and mean gain per category and group; macro by case."""
    ok = [r for r in rows if 'error' not in r and not r['provisional']]
    out = {'n_cases': len(ok), 'n_errors': sum('error' in r for r in rows), 'per_class': {}, 'macro_group_gain': {}}
    for name in NAMES.values():
        cr = [r['classes'][name] for r in ok if name in r['classes'] and name not in r['flagged_classes']]
        sp = [x for x in cr if x['split']]
        if not cr:
            continue
        out['per_class'][name] = {
            'n': len(cr), 'n_split': len(sp), 'tf1': round(float(np.mean([x['tf1'] for x in cr])), 4),
            'loss': round(float(1 - np.mean([x['tf1'] for x in cr])), 4),
            'group_gain': {g: round(float(np.mean([x['group_gain'][g] for x in sp])), 4) for g in GROUPS} if sp else {},
            'gain': {k: round(float(np.mean([x['gain'][k] for x in sp])), 4) for k in sp[0]['gain']} if sp else {}}
    for g in GROUPS:
        per_case = []
        for r in ok:
            v = [r['classes'][n]['group_gain'][g] if r['classes'][n]['split'] else 0.0
                 for n in r['classes'] if n not in r['flagged_classes']]
            if v:
                per_case.append(float(np.mean(v)))
        out['macro_group_gain'][g] = round(float(np.mean(per_case)), 4) if per_case else None
    out['worth_an_arm'] = {g: (v is not None and v >= 0.03) for g, v in out['macro_group_gain'].items()}
    return out


def check_cases(lists_json, sealed_json, cases):
    L = json.load(open(lists_json)); S = json.load(open(sealed_json))
    allowed = set(L['tuning60'])
    bad = sorted(set(cases) - allowed)
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    if bad or set(cases) & sealed or set(cases) & set(L['locked100']):
        sys.exit(f'[decompose60] REFUSING: only the tuning 60 may be decomposed; got {bad[:5]}')
    return sorted(cases)


def selftest():
    sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Atlas'))
    import r9_score_icx4 as r9
    r9.check_hash()
    ref, aorta, sp = r9.synthetic()
    sp = np.asarray(sp, float)
    perfect = decompose_arrays(ref, ref.copy(), sp, aorta=aorta)
    assert all(abs(v['tf1'] - 1) < 1e-9 for v in perfect['classes'].values()), perfect
    cut = ref.copy(); s_ = cut[60:66]; s_[s_ == 2] = 0               # 3 mm gap across the LAD: breaks
    o = decompose_arrays(ref, cut, sp, aorta=aorta)['classes']['LAD']
    assert o['recall']['cut'] > 0 and o['recall']['miss_gap'] + o['recall']['miss_near'] > 0, o
    assert o['group_gain']['breaks'] > 0.3 and o['group_gain']['extent'] == 0, o
    tipc = ref.copy(); s_ = tipc[85:]; s_[s_ == 3] = 0                # distal LCx tip removed: extent
    o = decompose_arrays(ref, tipc, sp, aorta=aorta)['classes']['LCx']
    assert o['recall']['miss_tip'] > 0 and o['group_gain']['extent'] > 0.05 and o['recall']['cut'] == 0, o
    swap = ref.copy(); swap[ref == 3] = 2                               # LCx named LAD: naming both ways
    oc = decompose_arrays(ref, swap, sp, aorta=aorta)['classes']
    assert oc['LCx']['recall']['naming'] > 0 and oc['LCx']['group_gain']['naming'] > 0.9, oc['LCx']
    assert oc['LAD']['precision']['naming'] > 0, oc['LAD']
    thin = ref.copy(); thin[(ndimage.distance_transform_edt(ref > 0) < 1.5) & (ref > 0)] = 0   # one voxel thinner
    o = decompose_arrays(ref, thin, sp, aorta=aorta)['classes']
    assert all(v['tf1'] > 0.9 for v in o.values()), o
    blob = ref.copy(); blob[60:96, 28:33, 40:45] = 4                   # an 18 mm FP vessel away from the tree
    o = decompose_arrays(ref, blob, sp, aorta=aorta)['classes']['RCA']
    assert o['precision']['out_far'] > 0 and o['group_gain']['extra'] > 0, o
    rows = [dict(case='c%04d' % i, **decompose_arrays(ref, x, sp, aorta=aorta)) for i, x in
            enumerate((ref, cut, tipc, swap))]
    s = summarise(rows)
    assert s['n_cases'] == 4 and s['macro_group_gain']['naming'] > 0, s
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    try:
        check_cases(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json'),
                    os.path.join(ROOT, 'trillium', 'sealed_test.json'), [L['locked100'][0]])
        raise AssertionError('a locked case was not refused')
    except SystemExit as e:
        assert 'REFUSING' in str(e)
    print('[decompose60] self-test passed: recall/precision equal tree_f1 on every case; gap -> breaks, '
          'tip -> extent, swap -> naming, blob -> extra; locked case refused')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--pred'); ap.add_argument('--icx'); ap.add_argument('--aorta'); ap.add_argument('--layout')
    ap.add_argument('--lists'); ap.add_argument('--out'); ap.add_argument('--np', type=int, default=8)
    ap.add_argument('--sealed', default=os.path.join(ROOT, 'trillium', 'sealed_test.json'))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    tf1_score.load_metric()
    cases = check_cases(a.lists, a.sealed, json.load(open(a.lists))['tuning60'])
    cts = {c: v.get('ct') for c, v in json.load(open(a.layout))['cases'].items()} if a.layout else {}
    with Pool(a.np, initializer=tf1_score.load_metric, maxtasksperchild=4) as p:
        rows = p.map(decompose_case, [(c, a.pred, a.icx, a.aorta, cts.get(c)) for c in cases], chunksize=1)
    res = {'tf1_sha256': tf1_score.TF1_SHA256, 'pred': a.pred, 'summary': summarise(rows), 'rows': rows}
    json.dump(res, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps(res['summary'], indent=1))


if __name__ == '__main__':
    main()
