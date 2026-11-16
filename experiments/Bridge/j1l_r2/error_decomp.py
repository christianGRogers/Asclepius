"""Bridge, track 1-L round 2 (#302, Janus 1-L Round 1 §5 item 5): where Janus 0 loses tF1 on the tuning 60.

The tuning 60 (dev-44 + the 16 trained open-36 cases) are the only ImageCAS-X cases that Janus 0 never trained on
and that the locked 100 does not hold. Job 0 predicts them. This script splits each class's tF1 loss on them into
the error kinds a later recipe arm could target. It reads Job 0's argmax export (`$W/thr/t0.50`), the ImageCAS-X
labels, the aortas and the CTs that Step T copied. It is CPU only.

**It refuses every case outside the tuning 60**, so it can never read the locked 100 or a sealed case.

Every reference centreline point and every predicted centreline point of the frozen metric (A1c,
`src/segtrain/tf1.py`, sha256 24441cf8...5254) is put in exactly one category. The script recomputes tree_f1's
recall and precision from the categories and refuses the case if they differ from the frozen function's own
numbers, so the decomposition adds up to the metric of record.

Recall side (reference centreline of class c; tree_f1 counts a point when the prediction there is c AND rooted):
  hit         predicted c, in a piece connected to an ostium (counted by tF1)
  name        predicted as another vessel class                                 -> NAMING
  break       predicted c, but the piece is not connected to an ostium          -> BREAKS
  fragment    predicted, but in a piece < 100 voxels that tF1 drops (A2)        -> BREAKS
  gap         not predicted, an interior run (no tip, no ostium in the run)     -> BREAKS
  root        not predicted, the run holds the ostium (the tree's root is lost) -> BREAKS
  distal      not predicted, the run ends at a tip (a short vessel or a lost side branch)  -> EXTENT
              (also reported: the share of its points below A23's contrast line, 0.3 x aortic HU)
  absent_fb   not predicted, a fallback point of a class with no skeleton (A1c); no graph to place it -> OTHER
Precision side (predicted centreline of class c; tree_f1 counts a point when the reference there is c):
  ok          inside reference class c
  pname       inside another reference vessel class                             -> NAMING
  edge        outside the reference, within 1.5 mm of it (boundary jitter)      -> OTHER (width)
  overextent  outside, further than 1.5 mm, in a piece connected to an ostium   -> EXTENT
  stray       outside, further than 1.5 mm, in a piece not connected            -> OTHER (FP)

Per case and class it then asks one counterfactual per group: tF1_c if every point of that group were right
(recall += the group's recall share, precision += its precision share). The group's **ceiling** is the mean gain
over cases, per class and as a macro (the decisive definition: provisional cases out, flagged classes out, A1a/A1b).
A ceiling is the most a perfect fix of that kind could buy. It is not a prediction of what an arm would buy.

Usage (Trillium login node, after Job 0; ~20-40 CPU-min with --np 8):
  python error_decomp.py --pred $W/thr/t0.50 --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json \
      --np 8 --out $W/scores/error_decomp_tuning60.json
Self-test (synthetic trees, no data):  python error_decomp.py --selftest
"""
import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
LIB = os.path.join(ROOT, 'trillium', 'icx4', 'lib')
sys.path.insert(0, LIB)

import tf1_score  # noqa: E402  (icx4's in-job scorer: crop, hash check, the frozen metric as tf1_score.T)

NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
LISTS = os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')
SEALED = os.path.join(ROOT, 'trillium', 'sealed_test.json')
RECALL_CATS = ('hit', 'name', 'break', 'fragment', 'gap', 'root', 'distal', 'absent_fb')
PREC_CATS = ('ok', 'pname', 'edge', 'overextent', 'stray')
GROUPS = {'breaks': (('break', 'fragment', 'gap', 'root'), ()),
          'naming': (('name',), ('pname',)),
          'extent': (('distal',), ('overextent',)),
          'other': (('absent_fb',), ('edge', 'stray'))}
CONTRAST_FRACTION = 0.3      # A23's line
CONTRAST_SMOOTH_MM = 0.7


def tuning60():
    L = json.load(open(LISTS))
    S = json.load(open(SEALED))
    cases = sorted(L['tuning60'])
    bad = (set(cases) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']))) | (set(cases) & set(L['locked100']))
    assert len(cases) == 60 and not bad, bad
    return cases


def _runs(cl, sel):
    """Connected runs (26-neighbourhood on the reference centreline graph) of the points where sel is True."""
    lab = -np.ones(len(sel), int)
    k = 0
    for v in np.nonzero(sel)[0]:
        if lab[v] >= 0:
            continue
        stack, lab[v] = [v], k
        while stack:
            u = stack.pop()
            for w in cl.neighbours(u):
                if sel[w] and lab[w] < 0:
                    lab[w] = k
                    stack.append(w)
        k += 1
    return lab, k


def decompose_arrays(ref, pred, sp, aorta=None, ct=None):
    """The categories of one case, from 4-class arrays on one grid (as tf1_score.score_arrays receives them)."""
    T = tf1_score.T or tf1_score.load_metric()
    sp = np.asarray(sp, float)
    sl = tf1_score._bbox([ref > 0, pred > 0], sp, ref.shape)
    ref, raw = ref[sl], pred[sl]
    aorta = aorta[sl] if aorta is not None else None
    ct = ct[sl] if ct is not None else None
    rep = T.find_ostia(ref, sp, aorta=aorta, ct=ct)
    tol = T.TOLERANCE_MM
    truth = T.tree_f1(ref, raw, sp, tol_mm=tol, ostia=rep)
    flagged = [NAMES[c] for c in tf1_score.classes_flagged(ref, rep)]

    # ---- tree_f1's internals, step for step (src/segtrain/tf1.py, A1c) ----
    pred = np.where(T.remove_small_components(raw > 0, T.MIN_COMPONENT_VOXELS), raw, 0)
    cl = T._Centreline(ref > 0, sp)
    pm = pred > 0
    grown = ndi_dilate(pm, T._ball(tol / 2.0, sp)) if pm.any() else pm
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
    rc = list(rooted_comps)
    rpts = cl.pts
    n_graph = len(rpts)
    rlab = ref[tuple(rpts.T)]
    plab = pred[tuple(rpts.T)]
    rawlab = raw[tuple(rpts.T)]
    rooted = np.isin(comp_of_pred[tuple(rpts.T)], rc) if rc else np.zeros(n_graph, bool)
    psk = T._skeletonise(pm)
    ppts = np.argwhere(psk)
    plab_sk = pred[psk]
    rlab_at_pred = ref[psk]
    present = set(np.unique(ref).tolist()) & set(T.CLASSES)
    missing = sorted(c for c in present if not (rlab == c).any())
    if missing:   # the decisive fallback centreline (A1c), exactly as tree_f1 adds it
        extra = np.concatenate([T._fallback_points(ref == c, sp) for c in missing])
        rlab = np.concatenate([rlab, ref[tuple(extra.T)]])
        plab = np.concatenate([plab, pred[tuple(extra.T)]])
        rawlab = np.concatenate([rawlab, raw[tuple(extra.T)]])
        ex_root = np.isin(comp_of_pred[tuple(extra.T)], rc) if rc else np.zeros(len(extra), bool)
        rooted = np.concatenate([rooted, ex_root])
        on_pred = (pred[tuple(extra.T)] > 0) & ~psk[tuple(extra.T)]
        plab_sk = np.concatenate([plab_sk, pred[tuple(extra[on_pred].T)]])
        rlab_at_pred = np.concatenate([rlab_at_pred, ref[tuple(extra[on_pred].T)]])
        ppts = np.concatenate([ppts, extra[on_pred]])
    n_all = len(rlab)
    is_graph = np.arange(n_all) < n_graph

    # ---- recall categories ----
    cat = np.full(n_all, '', dtype=object)
    cat[(plab > 0) & (plab != rlab)] = 'name'
    same = plab == rlab
    cat[same & rooted] = 'hit'
    cat[same & ~rooted] = 'break'
    absent = plab == 0
    cat[absent & (rawlab > 0)] = 'fragment'
    cat[absent & (rawlab == 0) & ~is_graph] = 'absent_fb'
    miss = np.zeros(n_graph, bool)
    miss[:] = absent[:n_graph] & (rawlab[:n_graph] == 0)
    run, nrun = _runs(cl, miss)
    ostium_idx = set()
    if n_graph:
        index = {tuple(p): i for i, p in enumerate(rpts)}
        ostium_idx = {index[tuple(o)] for o in rep.points if tuple(o) in index}
    tips = cl.degree == 1
    kind = {}
    for k in range(nrun):
        on = np.nonzero(run == k)[0]
        if any(int(v) in ostium_idx for v in on):
            kind[k] = 'root'
        elif tips[on].any():
            kind[k] = 'distal'
        else:
            kind[k] = 'gap'
    for v in np.nonzero(miss)[0]:
        cat[v] = kind[run[v]]
    assert not (cat == '').any()

    # contrast support of the distal misses (A23's line; report only)
    low = np.zeros(n_all, bool)
    if ct is not None and aorta is not None and aorta.any() and n_graph:
        from scipy import ndimage
        hu = ndimage.gaussian_filter(np.asarray(ct, np.float32), sigma=CONTRAST_SMOOTH_MM / sp)
        thr = CONTRAST_FRACTION * float(np.median(hu[aorta]))
        low[:n_graph] = hu[tuple(rpts.T)] < thr

    # ---- precision categories ----
    pcat = np.full(len(plab_sk), '', dtype=object)
    pcat[rlab_at_pred == plab_sk] = 'ok'
    pcat[(rlab_at_pred > 0) & (rlab_at_pred != plab_sk)] = 'pname'
    bg = rlab_at_pred == 0
    if bg.any():
        from scipy import ndimage
        dist = ndimage.distance_transform_edt(ref == 0, sampling=sp)
        d = dist[tuple(ppts.T)]
        prooted = np.isin(comp_of_pred[tuple(ppts.T)], rc) if rc else np.zeros(len(ppts), bool)
        pcat[bg & (d <= tol)] = 'edge'
        pcat[bg & (d > tol) & prooted] = 'overextent'
        pcat[bg & (d > tol) & ~prooted] = 'stray'
    assert not (pcat == '').any()

    # ---- per class, with the frozen metric's own numbers as the check ----
    out = {}
    for c in T.CLASSES:
        g = rlab == c
        if not g.any():
            continue
        n_r = int(g.sum())
        rc_counts = {k: int((g & (cat == k)).sum()) for k in RECALL_CATS}
        pc = plab_sk == c
        n_p = int(pc.sum())
        pc_counts = {k: int((pc & (pcat == k)).sum()) for k in PREC_CATS}
        rec = rc_counts['hit'] / n_r
        prec = pc_counts['ok'] / n_p if n_p else 0.0
        if abs(rec - truth.recall[c]) > 1e-9 or abs(prec - truth.precision[c]) > 1e-9:
            raise AssertionError(f'class {c}: recomputed R/P {rec:.6f}/{prec:.6f} != tree_f1 '
                                 f'{truth.recall[c]:.6f}/{truth.precision[c]:.6f}')
        # predicted centreline of another vessel class lying in reference c: it becomes c's if naming is fixed
        inbound = int(((rlab_at_pred == c) & (plab_sk > 0) & (plab_sk != c)).sum())
        dist_low = int((g & (cat == 'distal') & low).sum())
        out[NAMES[c]] = dict(n_ref=n_r, n_pred=n_p, recall=rec, precision=prec, tf1=truth.per_class[c],
                             recall_counts=rc_counts, precision_counts=pc_counts, inbound=inbound, distal_low_hu=dist_low,
                             n_gap_runs=len({int(run[v]) for v in np.nonzero(g[:n_graph] & (cat[:n_graph] == 'gap'))[0]}),
                             n_root_runs=len({int(run[v]) for v in np.nonzero(g[:n_graph] & (cat[:n_graph] == 'root'))[0]}),
                             n_distal_runs=len({int(run[v]) for v in np.nonzero(g[:n_graph] & (cat[:n_graph] == 'distal'))[0]}),
                             n_break_pieces=len(set(comp_of_pred[tuple(rpts[np.nonzero(g[:n_graph] & (cat[:n_graph] == 'break'))[0]].T)].tolist())))
    return dict(tf1=float(truth.tf1), provisional=bool(rep.provisional), flagged_classes=flagged,
                classes_without_centreline=[NAMES[int(c)] for c in truth.classes_without_centreline],
                spacing=sp.tolist(), per_class=out)


def ndi_dilate(m, ball):
    from scipy import ndimage
    return ndimage.binary_dilation(m, structure=ball)


def f1(r, p):
    return 2 * r * p / (r + p) if r + p else 0.0


def counterfactual(row):
    """Per class: tF1 if one group were fixed, minus tF1 as scored.

    Recall: the group's missed reference points become hits. Precision: the group's wrong predicted points are
    removed (an FP or an over-extension fixed is gone, not relabelled); for naming they move to their true class,
    and the other classes' points lying in reference c ('inbound') join c as correct."""
    out = {}
    for n, v in row['per_class'].items():
        base = f1(v['recall'], v['precision'])
        d = {}
        for gname, (rk, pk) in GROUPS.items():
            r = v['recall'] + sum(v['recall_counts'][k] for k in rk) / v['n_ref']
            ok = v['precision_counts']['ok']
            npd = v['n_pred'] - sum(v['precision_counts'][k] for k in pk)
            if gname == 'naming':
                ok += v['inbound']
                npd += v['inbound']
            p = ok / npd if npd > 0 else 0.0
            d[gname] = f1(min(r, 1.0), min(p, 1.0)) - base
        out[n] = d
    return out


def summarise(rows):
    """Decisive definition (A1a/A1b): provisional cases out; a flagged class is out of that case."""
    dec = [r for r in rows if 'error' not in r and not r['provisional']]
    per = {n: defaultdict(list) for n in NAMES.values()}
    macro = defaultdict(list)
    shares = {n: {'recall': defaultdict(int), 'precision': defaultdict(int), 'distal_low_hu': 0}
              for n in NAMES.values()}
    for r in dec:
        cf = counterfactual(r)
        keep = [n for n in r['per_class'] if n not in r['flagged_classes']]
        if not keep:
            continue
        for g in GROUPS:
            macro[g].append(float(np.mean([cf[n][g] for n in keep])))
        macro['loss'].append(float(np.mean([1.0 - r['per_class'][n]['tf1'] for n in keep])))
        for n in keep:
            v = r['per_class'][n]
            per[n]['loss'].append(1.0 - v['tf1'])
            for g in GROUPS:
                per[n][g].append(cf[n][g])
            for k, x in v['recall_counts'].items():
                shares[n]['recall'][k] += x
            for k, x in v['precision_counts'].items():
                shares[n]['precision'][k] += x
            shares[n]['distal_low_hu'] += v['distal_low_hu']
            for k in ('n_gap_runs', 'n_root_runs', 'n_distal_runs', 'n_break_pieces'):
                per[n][k].append(v[k])
    out = {'n_cases': len(dec), 'macro': {k: round(float(np.mean(v)), 4) for k, v in macro.items()}, 'per_class': {}}
    for n in NAMES.values():
        if not per[n]['loss']:
            continue
        R = shares[n]['recall']
        P = shares[n]['precision']
        nr, npd = sum(R.values()), sum(P.values())
        out['per_class'][n] = {
            'n_trees': len(per[n]['loss']),
            'mean_tf1_loss': round(float(np.mean(per[n]['loss'])), 4),
            'ceiling_if_fixed': {g: round(float(np.mean(per[n][g])), 4) for g in GROUPS},
            'recall_points_share': {k: round(R[k] / nr, 4) for k in RECALL_CATS} if nr else {},
            'precision_points_share': {k: round(P[k] / npd, 4) for k in PREC_CATS} if npd else {},
            'distal_points_below_A23_line': round(shares[n]['distal_low_hu'] / R['distal'], 3) if R['distal'] else None,
            'per_tree_mean': {k: round(float(np.mean(per[n][k])), 3)
                              for k in ('n_gap_runs', 'n_root_runs', 'n_distal_runs', 'n_break_pieces')},
        }
    out['verdict'] = verdict(out)
    return out


def verdict(s):
    """Bridge v2 section 5's pre-registered reading (it proposes; the round decides)."""
    m = s['macro']
    lcx = s['per_class'].get('LCx', {}).get('ceiling_if_fixed', {})
    lead = max(('breaks', 'naming', 'extent'), key=lambda g: lcx.get(g, 0.0)) if lcx else None
    v = {'lcx_largest_group': lead}
    for g, arm in (('breaks', 'a topology arm (e.g. Skeleton Recall)'), ('naming', 'a naming arm (class-weighted CE '
                   'via icx4\'s hook, or the namer)'), ('extent', 'an extent arm')):
        c = m.get(g, 0.0)
        v[g] = (f'ceiling {c:.4f} >= 0.030: {arm} is worth a run in a later round' if c >= 0.03 else
                f'ceiling {c:.4f} in [0.015, 0.030): {arm} only if a no-training test (export or post-processing) '
                'first recovers half of it on these 60' if c >= 0.015 else
                f'ceiling {c:.4f} < 0.015: no {arm.split(" (")[0]}; even a perfect fix sits under the locked 100\'s MDE')
    return v


# ------------------------------------------------------------------------------------------------- I/O
def _load(p, dt):
    import nibabel as nib
    img = nib.load(p)
    return np.asanyarray(img.dataobj).astype(dt), img


def one(args):
    case, pred_dir, icx_dir, aorta_dir, ct_path = args
    try:
        from territory import to_four
        pred, _ = _load(os.path.join(pred_dir, f'{case}.nii.gz'), np.uint8)
        icx, li = _load(os.path.join(icx_dir, f'{int(case[1:]) + 1}.coronary.nii.gz'), np.int64)
        sp = np.array(li.header.get_zooms()[:3], float)
        ref = to_four(icx, sp).astype(np.uint8)
        ap = os.path.join(aorta_dir, f'{case}_aorta.nii.gz') if aorta_dir else None
        aorta = _load(ap, np.uint8)[0] > 0 if ap and os.path.exists(ap) else None
        ct = _load(ct_path, np.float32)[0] if ct_path and os.path.exists(ct_path) else None
        for name, a in (('prediction', pred), ('aorta', aorta), ('ct', ct)):
            if a is not None and a.shape != ref.shape:
                raise ValueError(f'{name} grid {a.shape} vs ImageCAS-X {ref.shape}')
        return dict(case=case, **decompose_arrays(ref, pred, sp, aorta=aorta, ct=ct))
    except Exception as e:  # noqa: BLE001 - one bad case is a row, never a crash
        return dict(case=case, error=repr(e)[:300])


def run(cases, pred, icx, aorta, cts, n_proc):
    allowed = set(tuning60())
    bad = sorted(set(cases) - allowed)
    if bad:
        sys.exit(f'[decomp] REFUSING: cases outside the tuning 60 requested: {bad[:5]}')
    with Pool(n_proc, initializer=tf1_score.load_metric, maxtasksperchild=4) as p:
        return p.map(one, [(c, pred, icx, aorta, cts.get(c)) for c in cases], chunksize=1)


# ------------------------------------------------------------------------------------------------- self-test
def selftest():
    sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Atlas'))
    import r9_score_icx4 as r9
    r9.check_hash()
    ref, aorta, sp = r9.synthetic()
    cases = {}
    cases['perfect'] = ref.copy()
    cut = ref.copy()
    s = cut[60:66]
    s[s == 2] = 0
    cases['cut'] = cut                                    # 3 mm interior cut across the LAD
    swap = ref.copy()
    swap[ref == 3] = 2
    cases['swap'] = swap                                  # LCx named LAD
    trunc = ref.copy()
    s = trunc[88:]
    s[s == 2] = 0
    cases['trunc'] = trunc                                # distal LAD missing
    blob = ref.copy()
    blob[88:108, 3:8, 3:8] = 4
    cases['blob'] = blob                                  # FP bar away from the tree (even-width bars and cubes skeletonise to nothing in skimage 0.26)
    ext = ref.copy()
    ext[100:108, 52:57, 34:39] = 4                        # RCA drawn on past its end, attached
    cases['ext'] = ext
    res = {k: decompose_arrays(ref, v, sp, aorta=aorta) for k, v in cases.items()}
    P = res['perfect']['per_class']
    assert all(v['recall'] == 1.0 and v['precision'] == 1.0 for v in P.values()), P
    lad = res['cut']['per_class']['LAD']['recall_counts']
    assert lad['gap'] > 0 and lad['break'] > 0 and lad['name'] == 0 and lad['distal'] == 0, lad
    lcx = res['swap']['per_class']['LCx']['recall_counts']
    assert lcx['name'] == res['swap']['per_class']['LCx']['n_ref'], lcx
    assert res['swap']['per_class']['LAD']['precision_counts']['pname'] > 0
    tr = res['trunc']['per_class']['LAD']['recall_counts']
    assert tr['distal'] > 0 and tr['gap'] == 0 and tr['break'] == 0, tr
    assert res['blob']['per_class']['RCA']['precision_counts']['stray'] > 0
    assert res['ext']['per_class']['RCA']['precision_counts']['overextent'] > 0
    cf = {k: counterfactual(dict(per_class=v['per_class'])) for k, v in res.items()}
    assert abs(cf['swap']['LCx']['naming'] - 1.0) < 1e-9
    assert cf['cut']['LAD']['breaks'] > 0.3 and cf['cut']['LAD']['naming'] == 0
    assert cf['trunc']['LAD']['extent'] > 0 and cf['trunc']['LAD']['breaks'] == 0
    # the file path, the refusal and the summary
    with tempfile.TemporaryDirectory() as W:
        t60 = tuning60()[:2]
        for c, k in zip(t60, ('cut', 'swap')):
            r9.write_case(W, c, cases[k], ref, aorta)
        rows = run(t60, os.path.join(W, 'predictions'), os.path.join(W, 'icx'), os.path.join(W, 'aorta'),
                   {c: os.path.join(W, 'ct', f'{c}.nii.gz') for c in t60}, 2)
        assert all('error' not in r for r in rows), rows
        s = summarise(rows)
        assert s['n_cases'] == 2 and s['per_class']['LCx']['ceiling_if_fixed']['naming'] > 0.4, s
        L = json.load(open(LISTS))
        try:
            run([L['locked100'][0]], W, W, W, {}, 1)
            raise AssertionError('a locked-100 case was not refused')
        except SystemExit as e:
            assert 'REFUSING' in str(e)
    print('[decomp] self-test passed: R/P reproduce tree_f1 on 6 fixtures; cut -> gap+break, swap -> naming, '
          'truncation -> distal, blob -> stray, extension -> overextent; locked-100 case refused')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--pred'); ap.add_argument('--icx'); ap.add_argument('--aorta'); ap.add_argument('--layout')
    ap.add_argument('--np', type=int, default=8); ap.add_argument('--out')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    tf1_score.load_metric()
    cases = tuning60()
    cts = {c: v.get('ct') for c, v in json.load(open(a.layout))['cases'].items()} if a.layout else {}
    rows = run(cases, a.pred, a.icx, a.aorta, cts, a.np)
    res = {'tf1_sha256': tf1_score.TF1_SHA256, 'pred': a.pred, 'n_errors': sum('error' in r for r in rows),
           'summary': summarise(rows), 'rows': rows}
    json.dump(res, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps({k: v for k, v in res.items() if k != 'rows'}, indent=1))


if __name__ == '__main__':
    main()
