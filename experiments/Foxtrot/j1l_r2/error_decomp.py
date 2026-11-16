"""Foxtrot, track 1-L round 2: where Janus 0's tree-F1 is lost on the tuning 60 (Judgement Round 1 section 5, item 5).

For each reference tree class, every reference centreline point that the decisive tF1 counts as *not recalled* is put
in exactly one bin, and every predicted centreline point it counts as *not precise* in exactly one bin:

  recall side (reference centreline of class c)
    hit        predicted as c and in a rooted predicted piece                       (what tF1 recall counts)
    cut        predicted as c, but in a piece not reached from the ostium           -> a BREAK upstream
    gap        not predicted at all, in a missed run with covered centreline on     -> a BREAK (a hole)
               both sides (no reference endpoint in the run)
    misnamed   predicted as another vessel class                                     -> NAMING
    extent     not predicted, in a missed run that contains a reference endpoint     -> EXTENT (a distal end or a
               (a vessel end or a whole side branch); fallback stub points missed       whole side branch not drawn)
  precision side (predicted centreline of class c)
    correct    inside reference class c                                              (what tF1 precision counts)
    misnamed   inside another reference class                                        -> NAMING
    outside    outside the reference                                                 -> OVERSHOOT (beyond the end,
                                                                                         a vein, or an FP piece)

The bins reproduce the frozen metric exactly: hit / n = tree_f1's recall_c and correct / m = its precision_c (asserted
per case and class). Each case is scored as the decisive score is (icx4's tf1_score: the same 15 mm crop, A1 ostia from
the TotalSegmentator aorta with the CT cross-check, flagged trees apart, provisional cases out, D3's 1.5 mm).
The frozen metric module is loaded through tf1_score.load_metric(), which refuses unless its hash is A1c's.

Counterfactuals per tree (what tF1_c would be with one kind of error removed and nothing else changed):
  breaks fixed   recall += cut + gap
  naming fixed   recall += misnamed; every predicted point inside the reference takes its reference class
  extent fixed   recall += extent
  overshoot gone precision: outside points removed from the predicted centreline
Their gains over the actual tF1 say which lever is worth a run: breaks -> a connectivity/topology arm (e.g. Skeleton
Recall), naming -> the namer or class weighting, extent -> an extent arm or the threshold, overshoot -> FP work.

**Cases: the tuning 60 only** (dev 44 + the 16 trained open-36; Janus 0 never trained on them). Any other id is refused,
so this can never read the locked 100 or a sealed case. Inputs are Job 0's outputs.

Lead's command (Trillium login node, after Job 0; CPU, about 30-60 min at 16 processes):
  source $HOME/icx14-venv/bin/activate; R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
  T=$(python -c "import json;print('%.2f' % json.load(open('$W/select.json'))['chosen_t'])")
  python $R/experiments/Foxtrot/j1l_r2/error_decomp.py --pred $W/thr/t0.50 --pred2 $W/thr/t$T \
     --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json --np 16 --out $W/scores/decomp_tuning60.json
Post on #302: the printed summary (the `summary` blocks). No per-case volume is written.
Self-test (synthetic trees):  python error_decomp.py --selftest
"""
import argparse
import json
import os
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
LIB = os.path.join(ROOT, 'trillium', 'icx4', 'lib')
sys.path.insert(0, LIB)
import tf1_score  # noqa: E402  (icx4's in-job scorer; loads the frozen metric after the A1c hash check)

NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
RBINS = ('hit', 'cut', 'gap', 'misnamed', 'extent')
PBINS = ('correct', 'misnamed', 'outside')
LISTS = os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')


def _runs(cl, missed):
    """Connected runs of missed reference-centreline points on the centreline graph; True where a run holds an
    endpoint of the full centreline (degree <= 1), i.e. it reaches a vessel end."""
    n = len(missed)
    lab = -np.ones(n, int)
    is_tip = np.zeros(n, bool)
    k = 0
    for s in np.nonzero(missed)[0]:
        if lab[s] >= 0:
            continue
        stack, members = [s], []
        lab[s] = k
        while stack:
            v = stack.pop()
            members.append(v)
            for u in cl.neighbours(v):
                if missed[u] and lab[u] < 0:
                    lab[u] = k
                    stack.append(u)
        is_tip[members] = bool((cl.degree[members] <= 1).any())
        k += 1
    return is_tip


def decompose(ref, pred, sp, report, T):
    """Bins per class, mirroring T.tree_f1 (tol 1.5 mm, cleaned prediction, fallback centreline) line for line."""
    from scipy import ndimage
    sp = np.asarray(sp, float)
    tol = T.TOLERANCE_MM
    pred = np.where(T.remove_small_components(pred > 0, T.MIN_COMPONENT_VOXELS), pred, 0)
    cl = T._Centreline(ref > 0, sp)
    pm = pred > 0
    grown = ndimage.binary_dilation(pm, structure=T._ball(tol / 2.0, sp)) if pm.any() else pm
    gl, _ = T.components(grown)
    comp_of_pred = np.where(pm, gl, 0)
    reach = max(tol, float(sp.max()))
    rr = np.ceil(reach / sp).astype(int)
    rooted_comps = set()
    for p in report.points:
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
    rooted = (np.isin(comp_of_pred[tuple(rpts.T)], list(rooted_comps)) if rooted_comps
              else np.zeros(len(rpts), bool))
    tip = _runs(cl, plab == 0) if len(rpts) else np.zeros(0, bool)
    psk = T._skeletonise(pm)
    plab_sk = pred[psk]
    rlab_at_pred = ref[psk]
    present = set(np.unique(ref).tolist()) & set(T.CLASSES)
    missing = sorted(c for c in present if not (rlab == c).any())
    if missing:   # T.tree_f1's fallback centreline (the decisive default): missed stub points count as extent
        extra = np.concatenate([T._fallback_points(ref == c, sp) for c in missing])
        rlab = np.concatenate([rlab, ref[tuple(extra.T)]])
        plab = np.concatenate([plab, pred[tuple(extra.T)]])
        ex_root = (np.isin(comp_of_pred[tuple(extra.T)], list(rooted_comps)) if rooted_comps
                   else np.zeros(len(extra), bool))
        rooted = np.concatenate([rooted, ex_root])
        tip = np.concatenate([tip, np.ones(len(extra), bool)])
        on_pred = (pred[tuple(extra.T)] > 0) & ~psk[tuple(extra.T)]
        plab_sk = np.concatenate([plab_sk, pred[tuple(extra[on_pred].T)]])
        rlab_at_pred = np.concatenate([rlab_at_pred, ref[tuple(extra[on_pred].T)]])
    out = {}
    for c in T.CLASSES:
        g = rlab == c
        if not g.any():
            continue
        r = {'n_ref': int(g.sum()),
             'hit': int((g & (plab == c) & rooted).sum()),
             'cut': int((g & (plab == c) & ~rooted).sum()),
             'misnamed': int((g & (plab > 0) & (plab != c)).sum()),
             'gap': int((g & (plab == 0) & ~tip).sum()),
             'extent': int((g & (plab == 0) & tip).sum())}
        pc = plab_sk == c
        r.update(n_pred=int(pc.sum()), correct=int((pc & (rlab_at_pred == c)).sum()),
                 p_misnamed=int((pc & (rlab_at_pred > 0) & (rlab_at_pred != c)).sum()),
                 outside=int((pc & (rlab_at_pred == 0)).sum()),
                 other_in_ref=int(((plab_sk > 0) & ~pc & (rlab_at_pred == c)).sum()))
        assert sum(r[b] for b in RBINS) == r['n_ref'], r
        assert r['correct'] + r['p_misnamed'] + r['outside'] == r['n_pred'], r
        out[c] = r
    return out


def _f1(rec, prec):
    return 2 * rec * prec / (rec + prec) if rec + prec else 0.0


def tree_row(r):
    """Fractions and counterfactual tF1_c for one tree."""
    n, m = r['n_ref'], r['n_pred']
    rec = r['hit'] / n
    prec = r['correct'] / m if m else 0.0
    base = _f1(rec, prec)
    fr = {b: r[b] / n for b in RBINS}
    pf = {'p_misnamed': r['p_misnamed'] / m if m else 0.0, 'outside': r['outside'] / m if m else 0.0}
    cf = {'breaks_fixed': _f1(rec + fr['cut'] + fr['gap'], prec),
          # every predicted point renamed to its reference class: class c keeps its own correct and outside
          # points and gains the points other classes drew inside reference c
          'naming_fixed': _f1(rec + fr['misnamed'], (r['correct'] + r['other_in_ref']) /
                              (r['correct'] + r['other_in_ref'] + r['outside'])
                              if r['correct'] + r['other_in_ref'] + r['outside'] else 0.0),
          'extent_fixed': _f1(rec + fr['extent'], prec),
          'overshoot_gone': _f1(rec, r['correct'] / (m - r['outside']) if m - r['outside'] else 0.0)}
    return {'tf1': base, 'recall': rec, 'precision': prec, **{f'r_{b}': v for b, v in fr.items()}, **pf,
            **{f'gain_{k}': v - base for k, v in cf.items()}}


def case_rows(case, pred_path, icx_path, aorta_path, ct_path):
    """One case: the decisive row's conventions (crop, ostia, flags), then the bins. Errors are rows."""
    try:
        T = tf1_score.T or tf1_score.load_metric()
        pred, _ = tf1_score._load(pred_path, np.uint8)
        icx, li = tf1_score._load(icx_path, np.int64)
        sp = np.array(li.header.get_zooms()[:3], float)
        ref = tf1_score.to_four(icx, sp).astype(np.uint8)
        aorta = tf1_score._load(aorta_path, np.uint8)[0] > 0 if aorta_path and os.path.exists(aorta_path) else None
        ct = tf1_score._load(ct_path, np.float32)[0] if ct_path and os.path.exists(ct_path) else None
        sl = tf1_score._bbox([ref > 0, pred > 0], sp, ref.shape)
        ref, pred = ref[sl], pred[sl]
        aorta = aorta[sl] if aorta is not None else None
        ct = ct[sl] if ct is not None else None
        rep = T.find_ostia(ref, sp, aorta=aorta, ct=ct)
        bins = decompose(ref, pred, sp, rep, T)
        chk = T.tree_f1(ref, pred, sp, tol_mm=T.TOLERANCE_MM, ostia=rep)
        for c, r in bins.items():    # the bins must be the decisive metric's own numbers
            assert abs(r['hit'] / r['n_ref'] - chk.recall[c]) < 1e-9, (case, c, 'recall')
            assert abs((r['correct'] / r['n_pred'] if r['n_pred'] else 0.0) - chk.precision[c]) < 1e-9, (case, c)
        flagged = [NAMES[c] for c in tf1_score.classes_flagged(ref, rep)]
        return {'case': case, 'provisional': bool(rep.provisional), 'flagged_classes': flagged,
                'trees': {NAMES[c]: {**r, **tree_row(r)} for c, r in bins.items()}}
    except Exception as e:  # noqa: BLE001
        return {'case': case, 'error': repr(e)[:300]}


def summarise(rows):
    """Decisive trees only (non-provisional cases, unflagged classes): mean fraction per bin and mean tF1 gain per
    counterfactual, per class and macro over the four classes."""
    keys = None
    per = {}
    for r in rows:
        if 'error' in r or r['provisional']:
            continue
        for name, t in r['trees'].items():
            if name in r['flagged_classes']:
                continue
            keys = keys or [k for k in t if k.startswith(('r_', 'p_', 'outside', 'gain_')) or k in ('tf1',)]
            per.setdefault(name, []).append(t)
    out = {'n_cases': sum(1 for r in rows if 'error' not in r and not r['provisional']),
           'errors': [r['case'] for r in rows if 'error' in r], 'per_class': {}}
    for name in NAMES.values():
        ts = per.get(name, [])
        if ts:
            out['per_class'][name] = {'n_trees': len(ts), **{k: round(float(np.mean([t[k] for t in ts])), 4)
                                                             for k in keys}}
    if out['per_class']:
        out['macro'] = {k: round(float(np.mean([v[k] for v in out['per_class'].values()])), 4) for k in keys}
    return out


def run(pred, icx, aorta, cases, cts, n_proc):
    jobs = [(c, os.path.join(pred, f'{c}.nii.gz'), os.path.join(icx, f'{int(c[1:]) + 1}.coronary.nii.gz'),
             os.path.join(aorta, f'{c}_aorta.nii.gz') if aorta else None, cts.get(c)) for c in cases]
    with Pool(n_proc, initializer=tf1_score.load_metric, maxtasksperchild=4) as p:
        return p.starmap(case_rows, jobs, chunksize=1)


def tuning60():
    L = json.load(open(LISTS))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    cases = sorted(L['tuning60'])
    bad = set(cases) & (set(L['locked100']) | set(S['sealed_icx_test']) | set(S['sealed_quality0']))
    assert len(cases) == 60 and not bad, bad
    return cases


def selftest():
    sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Atlas'))
    import r9_score_icx4 as R
    R.check_hash()
    ref, aorta, sp = R.synthetic()
    variants = {}
    variants['c0001'] = ref.copy()                                   # perfect
    v = ref.copy(); s = v[60:66]; s[s == 2] = 0; variants['c0003'] = v  # 3 mm hole in the LAD -> gap + cut
    v = ref.copy(); v[ref == 3] = 2; variants['c0004'] = v           # LCx drawn as LAD -> naming
    v = ref.copy(); s = v[85:]; s[s == 4] = 0; variants['c0005'] = v   # RCA's distal 12 mm not drawn -> extent
    v = ref.copy()                                                   # a vein-like FP tube beside the RCA -> outside
    gx, gy = np.ogrid[:ref.shape[0], :ref.shape[1]]
    v[((gx - 100) ** 2 + (gy - 8) ** 2 <= 4)[:, :, None] & (np.arange(ref.shape[2]) >= 6)[None, None, :]
      & (np.arange(ref.shape[2]) <= 40)[None, None, :]] = 4
    variants['c0006'] = v
    with tempfile.TemporaryDirectory() as W:
        cts = {c: R.write_case(W, c, p, ref, aorta) for c, p in variants.items()}
        rows = {r['case']: r for r in run(os.path.join(W, 'predictions'), os.path.join(W, 'icx'),
                                          os.path.join(W, 'aorta'), sorted(variants), cts, 2)}
    assert all('error' not in r for r in rows.values()), rows
    t = lambda c, k: rows[c]['trees'][k]  # noqa: E731
    assert t('c0001', 'LAD')['r_hit'] == 1.0 and t('c0001', 'RCA')['precision'] == 1.0
    lad = t('c0003', 'LAD')
    assert lad['r_cut'] > 0.3 and lad['r_gap'] > 0 and lad['r_extent'] == 0 and lad['gain_breaks_fixed'] > 0.2, lad
    lcx = t('c0004', 'LCx')
    assert lcx['r_misnamed'] > 0.9 and lcx['gain_naming_fixed'] > 0.9, lcx
    assert t('c0004', 'LAD')['p_misnamed'] > 0.3
    rca = t('c0005', 'RCA')
    assert rca['r_extent'] > 0.1 and rca['r_cut'] == 0 and rca['r_gap'] == 0 and rca['gain_extent_fixed'] > 0.05, rca
    fp = t('c0006', 'RCA')
    assert fp['outside'] > 0 and fp['r_hit'] == 1.0 and fp['gain_overshoot_gone'] > 0, fp
    s = summarise(list(rows.values()))
    assert s['n_cases'] == 5 and 'macro' in s
    assert not set(json.load(open(LISTS))['locked100']) & set(tuning60())
    print('[decomp] self-test passed: perfect tree clean; LAD hole -> cut', round(lad['r_cut'], 3), 'gap',
          round(lad['r_gap'], 3), '; LCx as LAD -> misnamed', round(lcx['r_misnamed'], 3), '; RCA end missing -> extent',
          round(rca['r_extent'], 3), '; FP piece -> outside', round(fp['outside'], 3),
          '; bins equal the frozen recall and precision on every tree')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--pred'); ap.add_argument('--pred2', help='a second export (e.g. t*), same cases')
    ap.add_argument('--icx'); ap.add_argument('--aorta'); ap.add_argument('--layout')
    ap.add_argument('--np', type=int, default=8); ap.add_argument('--out')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    tf1_score.load_metric()
    cases = tuning60()
    cts = {c: v.get('ct') for c, v in json.load(open(a.layout))['cases'].items()} if a.layout else {}
    res = {'tf1_sha256': tf1_score.TF1_SHA256, 'cases': 'tuning60', 'pred': a.pred}
    rows = run(a.pred, a.icx, a.aorta, cases, cts, a.np)
    res['summary'] = summarise(rows)
    res['rows'] = rows
    if a.pred2:
        rows2 = run(a.pred2, a.icx, a.aorta, cases, cts, a.np)
        res.update(pred2=a.pred2, summary2=summarise(rows2), rows2=rows2)
    json.dump(res, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps({k: v for k, v in res.items() if k.startswith('summary')}, indent=1))


if __name__ == '__main__':
    main()
