"""Crucible, Janus 1-L Round 2: where Janus 0 loses tree-F1 on the tuning 60, split into breaks, naming and extent
(Janus 1-L Round 1, section 5 item 5; Bridge v1 section 7).

Cases. Only the tuning 60 (dev 44 + the 16 trained open-36 cases of D45), read from Crucible's round-1 `lists.json`.
Janus 0 never trained on them; Janus 1-L will. The script REFUSES any locked-100 id and any sealed id
(`trillium/sealed_test.json`), whatever `--cases` says.

Inputs (Job 0's outputs; nothing new runs on a GPU):
  --pred   Janus 0's exports for the 60 (`$W/thr/t0.50` = argmax; optionally also `$W/thr/t<t*>`);
  --icx    the ImageCAS-X labels (`<n>.coronary.nii.gz`), collapsed by `territory.to_four` as dataset 715;
  --aorta  Janus 0's A1 aortas; --layout  Job 0's layout.json (the CT, for the pool_thick cross-check).

Method. Each case goes through exactly the decisive scorer's path (icx4's `tf1_score`: the same crop, the same
`find_ostia` with aorta and CT, the frozen A1c metric `segtrain_tf1`), and then through a re-statement of
`tree_f1`'s own recall and precision steps that keeps *why* each centreline point is lost. The re-statement is checked
against the metric on every case: its "hit" fraction must equal `tree_f1`'s recall per class, and its "correct"
fraction its precision, to 1e-9; a case that does not match is reported, not used.

For reference class c, every reference centreline point is exactly one of:
  hit      predicted c, in a piece connected to an ostium (what recall counts);
  break    predicted c, but in a piece not connected to any ostium (a cut tree: topology);
  naming   predicted as another vessel class (rooted or not);
  missed   not predicted at all (extent: a vessel or segment the model did not draw).
For predicted class c, every predicted centreline point is exactly one of:
  correct  inside reference class c (what precision counts);
  naming   inside another reference vessel class;
  overshoot outside every reference vessel (extent beyond the reference, or a false branch).

What each error type costs. Per case and class, tF1_c is recomputed with one error type removed (break: break points
become hits; naming: both naming fractions become hits/correct; extent: missed points become hits and overshoot
points correct). The gain over the actual tF1_c is that type's cost. The three costs do not add up to 1 - tF1_c
exactly (F1 is not linear); the report gives all three and the joint residual.

Decisive rows only (A1a/A1b): provisional cases and flagged trees are kept apart, exactly as the scorer does.

Usage (Trillium login node, CPU, ~20 min with --np 20; Janus 1-L Round 2, Crucible v2 section 5):
  python decompose60.py --pred $W/thr/t0.50 --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json \
      --lists $R/experiments/Crucible/j1l_r1/lists.json --np 20 --out $W/decompose60_t0.50.json
Self-test (synthetic tree, no data):  python decompose60.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'src'))

import tf1_score  # noqa: E402  (icx4's in-job scorer; loads the frozen segtrain_tf1 after its A1c hash check)

NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
TYPES = ('break', 'naming', 'extent')


def f1(r, p):
    return 2 * r * p / (r + p) if r + p else 0.0


def decompose_arrays(ref, pred, sp, aorta=None, ct=None):
    """One case on one grid. Mirrors tf1_score.score_arrays (crop, ostia) and segtrain_tf1.tree_f1 (tol 1.5 mm,
    fallback centreline on), keeping the reason each centreline point is lost."""
    T = tf1_score.T or tf1_score.load_metric()
    sp = np.asarray(sp, float)
    sl = tf1_score._bbox([ref > 0, pred > 0], sp, ref.shape)
    ref, pred = ref[sl], pred[sl]
    aorta = aorta[sl] if aorta is not None else None
    ct = ct[sl] if ct is not None else None
    rep = T.find_ostia(ref, sp, aorta=aorta, ct=ct)
    official = T.tree_f1(ref, pred, sp, tol_mm=T.TOLERANCE_MM, ostia=rep)

    # --- tree_f1's own steps (segtrain/tf1.py, A1c), unchanged except that the labels are kept ---
    tol = T.TOLERANCE_MM
    pred = np.where(T.remove_small_components(pred > 0, T.MIN_COMPONENT_VOXELS), pred, 0)
    cl = T._Centreline(ref > 0, sp)
    pm = pred > 0
    from scipy import ndimage
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
    plab_at_ref = pred[tuple(rpts.T)]
    rooted = (np.isin(comp_of_pred[tuple(rpts.T)], list(rooted_comps)) if rooted_comps
              else np.zeros(len(rpts), dtype=bool))
    psk = T._skeletonise(pm)
    plab_sk = pred[psk]
    rlab_at_pred = ref[psk]
    present = set(np.unique(ref).tolist()) & set(NAMES)
    missing = sorted(c for c in present if not (rlab == c).any())
    if missing:
        extra = np.concatenate([T._fallback_points(ref == c, sp) for c in missing])
        rlab = np.concatenate([rlab, ref[tuple(extra.T)]])
        plab_at_ref = np.concatenate([plab_at_ref, pred[tuple(extra.T)]])
        ex_root = (np.isin(comp_of_pred[tuple(extra.T)], list(rooted_comps)) if rooted_comps
                   else np.zeros(len(extra), dtype=bool))
        rooted = np.concatenate([rooted, ex_root])
        on_pred = (pred[tuple(extra.T)] > 0) & ~psk[tuple(extra.T)]
        plab_sk = np.concatenate([plab_sk, pred[tuple(extra[on_pred].T)]])
        rlab_at_pred = np.concatenate([rlab_at_pred, ref[tuple(extra[on_pred].T)]])

    out, mismatch = {}, []
    for c in NAMES:
        g = rlab == c
        if not g.any():
            continue
        n = int(g.sum())
        hit = float(((plab_at_ref == c) & rooted & g).sum() / n)
        brk = float(((plab_at_ref == c) & ~rooted & g).sum() / n)
        nam_r = float(((plab_at_ref > 0) & (plab_at_ref != c) & g).sum() / n)
        miss = float(((plab_at_ref == 0) & g).sum() / n)
        confused = {NAMES[k]: int(((plab_at_ref == k) & g).sum()) for k in NAMES if k != c}
        pc = plab_sk == c
        m = int(pc.sum())
        if m:
            cor = float((rlab_at_pred[pc] == c).mean())
            nam_p = float(((rlab_at_pred[pc] > 0) & (rlab_at_pred[pc] != c)).mean())
            over = float((rlab_at_pred[pc] == 0).mean())
        else:
            cor = nam_p = over = 0.0
        tf = f1(hit, cor)
        if abs(hit - official.recall.get(c, np.nan)) > 1e-9 or abs(cor - official.precision.get(c, np.nan)) > 1e-9:
            mismatch.append(NAMES[c])
        out[NAMES[c]] = dict(
            n_ref=n, n_pred=m, tf1=tf, recall=hit, precision=cor,
            recall_lost=dict(break_=brk, naming=nam_r, missed=miss), precision_lost=dict(naming=nam_p, overshoot=over),
            reference_predicted_as=confused,
            cost=dict(**{'break': f1(hit + brk, cor) - tf if m or brk else 0.0},
                      naming=f1(hit + nam_r, cor + nam_p) - tf if (m or nam_r) else 0.0,
                      extent=f1(hit + miss, min(cor + over, 1.0)) - tf if (m or miss) else 0.0,
                      all=1.0 - tf))
    flagged = tf1_score.classes_flagged(ref, rep)
    return dict(classes=out, provisional=bool(rep.provisional), flagged_classes=[NAMES[c] for c in flagged],
                official_tf1=float(official.tf1), mismatch=mismatch)


def run_case(args):
    case, pred_dir, icx_dir, aorta_dir, ct_path = args
    import nibabel as nib
    from territory import to_four
    try:
        if tf1_score.T is None:
            tf1_score.load_metric()
        pred = np.asanyarray(nib.load(os.path.join(pred_dir, f'{case}.nii.gz')).dataobj).astype(np.uint8)
        li = nib.load(os.path.join(icx_dir, f'{int(case[1:]) + 1}.coronary.nii.gz'))
        sp = np.array(li.header.get_zooms()[:3], float)
        ref = to_four(np.asanyarray(li.dataobj).astype(np.int64), sp).astype(np.uint8)
        ap = os.path.join(aorta_dir, f'{case}_aorta.nii.gz') if aorta_dir else None
        aorta = np.asanyarray(nib.load(ap).dataobj) > 0 if ap and os.path.exists(ap) else None
        ct = (np.asanyarray(nib.load(ct_path).dataobj).astype(np.float32)
              if ct_path and os.path.exists(ct_path) else None)
        return dict(case=case, **decompose_arrays(ref, pred, sp, aorta=aorta, ct=ct))
    except Exception as e:  # noqa: BLE001
        return dict(case=case, error=repr(e)[:300])


def summarise(rows):
    """Decisive rows only: provisional cases out (A1a), flagged trees out per class (A1b), mismatches out."""
    ok = [r for r in rows if 'error' not in r and not r['provisional']]
    s = {}
    for k in NAMES.values():
        vals = [r['classes'][k] for r in ok if k in r['classes'] and k not in r['flagged_classes']
                and k not in r['mismatch']]
        if not vals:
            continue
        mean = lambda f: round(float(np.mean([f(v) for v in vals])), 4)  # noqa: E731
        costs = {t: mean(lambda v, t=t: v['cost'][t]) for t in TYPES}
        s[k] = dict(n=len(vals), tf1=mean(lambda v: v['tf1']), loss=mean(lambda v: v['cost']['all']),
                    cost=costs, share_of_loss={t: (round(costs[t] / mean(lambda v: v['cost']['all']), 3)
                                                   if mean(lambda v: v['cost']['all']) else None) for t in TYPES},
                    recall_lost={t: mean(lambda v, t=t: v['recall_lost'][t]) for t in ('break_', 'naming', 'missed')},
                    precision_lost={t: mean(lambda v, t=t: v['precision_lost'][t]) for t in ('naming', 'overshoot')},
                    cases_where_break_costs_over_0p05=sum(v['cost']['break'] > 0.05 for v in vals),
                    reference_predicted_as={o: int(sum(v['reference_predicted_as'].get(o, 0) for v in vals))
                                            for o in NAMES.values() if o != k})
    return dict(n_cases=len(rows), n_decisive=len(ok), errors=[r['case'] for r in rows if 'error' in r],
                provisional=[r['case'] for r in rows if 'error' not in r and r['provisional']],
                mismatched=[(r['case'], r['mismatch']) for r in rows if 'error' not in r and r['mismatch']],
                per_class=s)


def allowed_cases(lists_json, sealed_json):
    L = json.load(open(lists_json))
    S = json.load(open(sealed_json))
    cases = sorted(L['tuning60'])
    forbidden = set(L['locked100']) | set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    bad = sorted(set(cases) & forbidden)
    if bad or len(cases) != 60:
        sys.exit(f'[decompose60] REFUSING: {len(cases)} cases, forbidden ids {bad[:5]}')
    return cases


# ------------------------------------------------------------------------------------------------- self-test
def _chk(r):
    assert not r['mismatch'], r['mismatch']
    return r['classes']


def selftest():
    sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Atlas'))
    from r9_score_icx4 import synthetic
    ref, aorta, sp = synthetic()
    tf1_score.load_metric()
    # 1. perfect prediction: every point a hit
    r = decompose_arrays(ref, ref.copy(), sp, aorta=aorta)
    assert not r['mismatch'], r['mismatch']
    for k, v in r['classes'].items():
        assert abs(v['tf1'] - 1) < 1e-9 and all(abs(x) < 1e-9 for x in v['cost'].values()), (k, v)
    # 2. naming: the distal half of LCx predicted as LAD
    p = ref.copy()
    x0 = 30
    p[(ref == 3) & (np.indices(ref.shape)[0] > x0 + 45)] = 2
    r = _chk(decompose_arrays(ref, p, sp, aorta=aorta))['LCx']
    assert r['recall_lost']['naming'] > 0.3 and r['recall_lost']['break_'] < 0.02 and r['recall_lost']['missed'] < 0.02, r
    assert r['cost']['naming'] > 0.15 and r['cost']['break'] < 0.02, r
    # 3. break: a 4 mm gap cut into the RCA (beyond the 1.5 mm tolerance), the distal piece kept as RCA
    p = ref.copy()
    xi = np.indices(ref.shape)[0]
    p[(ref == 4) & (xi >= x0 + 30) & (xi < x0 + 38)] = 0
    r = _chk(decompose_arrays(ref, p, sp, aorta=aorta))['RCA']
    assert r['recall_lost']['break_'] > 0.3 and r['cost']['break'] > r['cost']['extent'], r
    # 4. extent: the distal RCA not drawn at all
    p = ref.copy()
    p[(ref == 4) & (xi >= x0 + 40)] = 0
    r = _chk(decompose_arrays(ref, p, sp, aorta=aorta))['RCA']
    assert r['recall_lost']['missed'] > 0.3 and r['recall_lost']['break_'] < 0.02 and r['cost']['extent'] > 0.15, r
    # 5. the guard
    L = {'tuning60': ['c%04d' % i for i in range(59)] + ['c0068'], 'locked100': ['c0068']}
    import tempfile
    d = tempfile.mkdtemp()
    json.dump(L, open(os.path.join(d, 'l.json'), 'w'))
    try:
        allowed_cases(os.path.join(d, 'l.json'), os.path.join(ROOT, 'trillium', 'sealed_test.json'))
        raise AssertionError('locked id not refused')
    except SystemExit:
        pass
    print('[decompose60] selftest OK: perfect, naming, break, extent and the locked/sealed refusal')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pred'); ap.add_argument('--icx'); ap.add_argument('--aorta'); ap.add_argument('--layout')
    ap.add_argument('--lists', default=os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json'))
    ap.add_argument('--sealed', default=os.path.join(ROOT, 'trillium', 'sealed_test.json'))
    ap.add_argument('--np', type=int, default=8); ap.add_argument('--out'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    cases = allowed_cases(a.lists, a.sealed)
    cts = {c: v.get('ct') for c, v in json.load(open(a.layout))['cases'].items()} if a.layout else {}
    with Pool(a.np, initializer=tf1_score.load_metric, maxtasksperchild=4) as p:
        rows = p.map(run_case, [(c, a.pred, a.icx, a.aorta, cts.get(c)) for c in cases], chunksize=1)
    res = dict(pred=a.pred, summary=summarise(rows), rows=rows)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res['summary'], indent=1))


if __name__ == '__main__':
    main()
