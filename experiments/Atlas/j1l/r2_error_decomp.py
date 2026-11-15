"""Atlas, Janus 1-L round 2 (#302, Round-1 ruling §5 item 5): where Janus 0's tF1 is lost on the tuning 60.

Every reference centreline point of class c that tree-F1 does not count as recalled is lost for exactly one reason.
This script re-runs the frozen metric's own recall computation (lib/segtrain_tf1.py at A1c 24441cf8…5254, the same
crop, ostia, 1.5 mm growth and small-component cleaning as icx4's in-job score) and keeps the reason:

  recall side (fractions of class c's reference centreline; they sum to 1):
    hit         predicted as c, in a piece rooted at an ostium                      (what tF1 recall counts)
    break_disc  predicted (any class) but in a piece not rooted: the vessel is drawn, cut off from the ostium
    break_gap   not predicted, in a run of missing centreline that has an unrooted predicted piece beyond it
                (the cut itself)
    hole        not predicted, in a run with predicted, rooted centreline on both sides (a gap within 1.5 mm,
                bridged by the tolerance: costs recall, breaks nothing)
    naming      predicted as another class, rooted
    distal      not predicted, in a run touching predicted centreline on one side only (a tip stopped early, or a
                side branch not drawn from its origin)
    absent      not predicted, in a run touching no predicted centreline (a whole tree missing)
  precision side (fractions of the predicted class-c centreline):
    in_class    inside reference class c                                          (what tF1 precision counts)
    in_other    inside another reference class (naming)
    outside     outside the reference (overreach: extent or FP)

Groups used by the plan (Atlas v2 §5): BREAKS = break_disc + break_gap; NAMING = naming (+ in_other);
EXTENT = distal + absent (+ outside); HOLE is reported apart (it is width-like, not topology).

Counterfactual gains (per class, then decisive macro as `decide.decisive`): tF1_c recomputed with one group's lost
points counted as hit (and, for NAMING, in_other counted as in_class). They are upper bounds of what a perfect fix of
that group alone would buy; they are not additive.

Cases: the tuning 60 only (dev 44 + the 16 open-36 cases D45 sends to training; Janus 0 never trained on them).
The script REFUSES any sealed case and any locked-100 case (L-A7: nothing on the locked 100 chooses anything).

Usage (Trillium login node, after Job 0; CPU, about 30-45 min at --np 8):
  python r2_error_decomp.py --pred $W/thr/t0.50 --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json \
      --lists $R/experiments/Crucible/j1l_r1/lists.json --np 8 --out $W/scores/decomp_tuning60_t0.50.json
  python r2_error_decomp.py --selftest
"""
import argparse
import json
import os
import sys
from collections import deque
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))

import tf1_score  # noqa: E402  (icx4's in-job scorer: crop, ostia, the frozen metric after its hash check)

NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
REC = ('hit', 'break_disc', 'break_gap', 'hole', 'naming', 'distal', 'absent')
PREC = ('in_class', 'in_other', 'outside')
GROUPS = {'BREAKS': ('break_disc', 'break_gap'), 'NAMING': ('naming',), 'EXTENT': ('distal', 'absent'),
          'HOLE': ('hole',)}


def _covered_components(cl, covered):
    """Label covered skeleton points by connectivity in the reference skeleton graph (BFS)."""
    lab = -np.ones(len(cl.pts), np.int64)
    k = 0
    for s in np.nonzero(covered)[0]:
        if lab[s] >= 0:
            continue
        lab[s] = k
        q = deque([s])
        while q:
            u = q.popleft()
            for w in cl.neighbours(u):
                if covered[w] and lab[w] < 0:
                    lab[w] = k
                    q.append(w)
        k += 1
    return lab


def decompose_arrays(ref, pred, sp, ostia):
    """Per class: recall-side and precision-side counts, mirroring tree_f1 at TOLERANCE_MM (A1c)."""
    T = tf1_score.T
    sp = np.asarray(sp, float)
    tol = T.TOLERANCE_MM
    pred = np.where(T.remove_small_components(pred > 0, T.MIN_COMPONENT_VOXELS), pred, 0)
    cl = T._Centreline(ref > 0, sp)
    pm = pred > 0
    grown = T.ndimage.binary_dilation(pm, structure=T._ball(tol / 2.0, sp)) if pm.any() else pm
    gl, _ = T.components(grown)
    comp = np.where(pm, gl, 0)
    reach = max(tol, float(sp.max()))
    rr = np.ceil(reach / sp).astype(int)
    rooted_comps = set()
    for p in ostia.points:
        win = tuple(slice(max(p[k] - rr[k], 0), min(p[k] + rr[k] + 1, ref.shape[k])) for k in range(3))
        sub = comp[win]
        g = np.argwhere(sub > 0)
        if len(g):
            off = np.array([s.start for s in win])
            d = np.linalg.norm((g + off - np.array(p)) * sp, axis=1)
            rooted_comps |= set(sub[tuple(g[d <= reach].T)].tolist())
    pts = cl.pts
    rlab = ref[tuple(pts.T)]
    plab = pred[tuple(pts.T)]
    rooted = np.isin(comp[tuple(pts.T)], list(rooted_comps)) if rooted_comps else np.zeros(len(pts), bool)
    covered = plab > 0
    clab = _covered_components(cl, covered)
    comp_rooted = {}
    for i in np.nonzero(covered)[0]:
        comp_rooted[clab[i]] = comp_rooted.get(clab[i], False) or bool(rooted[i])
    reason = np.empty(len(pts), object)
    reason[covered & rooted & (plab == rlab)] = 'hit'
    reason[covered & ~rooted] = 'break_disc'
    reason[covered & rooted & (plab != rlab)] = 'naming'
    # runs of uncovered centreline (any class), classified by what they touch
    miss = ~covered
    seen = np.zeros(len(pts), bool)
    for s in np.nonzero(miss)[0]:
        if seen[s]:
            continue
        run, touch = [s], set()
        seen[s] = True
        q = deque([s])
        while q:
            u = q.popleft()
            for w in cl.neighbours(u):
                if miss[w]:
                    if not seen[w]:
                        seen[w] = True
                        run.append(w)
                        q.append(w)
                else:
                    touch.add(int(clab[w]))
        if not touch:
            why = 'absent'
        elif len(touch) == 1:
            why = 'distal'
        elif all(comp_rooted[t] for t in touch):
            why = 'hole'
        else:
            why = 'break_gap'
        reason[run] = why
    psk = T._skeletonise(pm)
    pl, rl = pred[psk], ref[psk]
    out = {}
    for c in T.CLASSES:
        g = rlab == c
        if not g.any():
            continue
        r = {k: int((reason[g] == k).sum()) for k in REC}
        pc = pl == c
        pr = {'in_class': int((rl[pc] == c).sum()), 'in_other': int(((rl[pc] > 0) & (rl[pc] != c)).sum()),
              'outside': int((rl[pc] == 0).sum())}
        out[NAMES[c]] = {'n_ref': int(g.sum()), 'recall': r, 'precision': pr}
    return out


def tf1_from(r, p, fix=()):
    n = sum(r.values())
    hit = r['hit'] + sum(r[k] for g in fix for k in GROUPS[g])
    rec = hit / n if n else 0.0
    good = p['in_class'] + (p['in_other'] if 'NAMING' in fix else 0)
    tot = sum(p.values())
    prec = good / tot if tot else 0.0
    return 2 * rec * prec / (rec + prec) if rec + prec else 0.0


def decompose_case(args):
    case, pred_path, icx_path, aorta_path, ct_path = args
    try:
        if tf1_score.T is None:
            tf1_score.load_metric()
        T = tf1_score.T
        pred, _ = tf1_score._load(pred_path, np.uint8)
        icx, li = tf1_score._load(icx_path, np.int64)
        sp = np.array(li.header.get_zooms()[:3], float)
        ref = tf1_score.to_four(icx, sp).astype(np.uint8)
        aorta = tf1_score._load(aorta_path, np.uint8)[0] > 0 if aorta_path and os.path.exists(aorta_path) else None
        ct = tf1_score._load(ct_path, np.float32)[0] if ct_path and os.path.exists(ct_path) else None
        row = tf1_score.score_arrays(ref, pred, sp, aorta=aorta, ct=ct)       # the decisive row, unchanged
        sl = tf1_score._bbox([ref > 0, pred > 0], sp, ref.shape)
        ref_c, pred_c = ref[sl], pred[sl]
        rep = T.find_ostia(ref_c, sp, aorta=aorta[sl] if aorta is not None else None,
                           ct=ct[sl] if ct is not None else None)
        dec = decompose_arrays(ref_c, pred_c, sp, rep)
        # consistency with the frozen metric: our 'hit' fraction must equal its recall where no fallback applies
        mism = {k: (v['recall']['hit'] / v['n_ref'], row['recall'].get(k)) for k, v in dec.items()
                if k not in row['classes_without_centreline'] and row['recall'].get(k) is not None
                and abs(v['recall']['hit'] / v['n_ref'] - row['recall'][k]) > 1e-9}
        return dict(case=case, provisional=row['provisional'], flagged_classes=row['flagged_classes'],
                    classes_without_centreline=row['classes_without_centreline'], per_class_tf1=row['per_class'],
                    fp_components=row['fp_components'], decomp=dec, recall_mismatch=mism)
    except Exception as e:  # noqa: BLE001
        return dict(case=case, error=repr(e)[:300])


def summarise(rows):
    ok = [r for r in rows if 'error' not in r and not r['provisional']]
    per = {}
    for c in NAMES.values():
        rs = [r for r in ok if c in r['decomp'] and c not in r['flagged_classes']
              and c not in r['classes_without_centreline']]
        if not rs:
            continue
        lost = {k: float(np.mean([r['decomp'][c]['recall'][k] / r['decomp'][c]['n_ref'] for r in rs])) for k in REC}
        prec = {k: float(np.mean([r['decomp'][c]['precision'][k] / max(1, sum(r['decomp'][c]['precision'].values()))
                                  for r in rs])) for k in PREC}
        base = [tf1_from(r['decomp'][c]['recall'], r['decomp'][c]['precision']) for r in rs]
        gain = {g: float(np.mean([tf1_from(r['decomp'][c]['recall'], r['decomp'][c]['precision'], (g,)) - b
                                  for r, b in zip(rs, base)])) for g in GROUPS}
        worst = sorted(rs, key=lambda r: r['per_class_tf1'].get(c, 1))[:5]
        per[c] = {'n': len(rs), 'tf1_mean': float(np.mean(base)), 'recall_share': lost, 'precision_share': prec,
                  'counterfactual_gain': gain,
                  'worst5': [{'case': r['case'], 'tf1': r['per_class_tf1'].get(c),
                              'lost': {k: round(r['decomp'][c]['recall'][k] / r['decomp'][c]['n_ref'], 3)
                                       for k in REC if k != 'hit'}} for r in worst]}
    macro = {}
    for g in (None,) + tuple(GROUPS):
        vals = []
        for r in ok:
            v = [tf1_from(r['decomp'][c]['recall'], r['decomp'][c]['precision'], (g,) if g else ())
                 for c in r['decomp'] if c not in r['flagged_classes'] and c not in r['classes_without_centreline']]
            if v:
                vals.append(float(np.mean(v)))
        macro[g or 'as_is'] = float(np.mean(vals)) if vals else None
    gains = {g: (macro[g] - macro['as_is']) if macro['as_is'] is not None else None for g in GROUPS}
    return {'n_cases': len(ok), 'n_errors': sum('error' in r for r in rows),
            'n_recall_mismatch': sum(bool(r.get('recall_mismatch')) for r in rows),
            'per_class': per, 'macro_as_is': macro['as_is'], 'macro_counterfactual_gain': gains,
            'note': 'macro over decisive classes with a centreline (fallback-centreline classes left out)'}


def cases_checked(lists_json, sealed_json):
    L = json.load(open(lists_json))
    S = json.load(open(sealed_json))
    cases = sorted(L['tuning60'])
    bad = set(cases) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']) | set(L['locked100']))
    if bad or len(cases) != 60:
        sys.exit(f'[decomp] REFUSING: {len(cases)} cases; sealed or locked-100 ids present: {sorted(bad)[:5]}')
    return cases


# ----------------------------------------------------------------------------------------------- self-test
def selftest():
    sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Atlas'))
    from r9_score_icx4 import synthetic  # the tests/test_tf1.py fixture
    tf1_score.load_metric()
    T = tf1_score.T
    ref, aorta, sp = synthetic()
    sp = np.asarray(sp)
    rep = T.find_ostia(ref, sp, aorta=aorta)

    def run(pred):
        d = decompose_arrays(ref, pred, sp, rep)
        t = T.tree_f1(ref, pred, sp, ostia=rep)
        for k, v in d.items():
            c = {n: i for i, n in NAMES.items()}[k]
            assert abs(v['recall']['hit'] / v['n_ref'] - t.recall[c]) < 1e-9, (k, v, t.recall)
            assert sum(v['recall'].values()) == v['n_ref']
        return d
    d = run(ref)
    assert all(v['recall']['hit'] == v['n_ref'] for v in d.values()), d
    cut = ref.copy(); s = cut[60:66]; s[s == 2] = 0                               # 3 mm cut across the LAD
    d = run(cut)['LAD']['recall']
    assert d['break_gap'] > 0 and d['break_disc'] > 0 and d['hole'] == 0, d
    hole = ref.copy(); s = hole[60:62]; s[s == 2] = 0                             # 1 mm hole: bridged by 1.5 mm
    d = run(hole)['LAD']['recall']
    assert d['hole'] > 0 and d['break_disc'] == 0 and d['break_gap'] == 0, d
    swap = ref.copy(); swap[ref == 3] = 2                                         # LCx named LAD
    d = run(swap)
    assert d['LCx']['recall']['naming'] == d['LCx']['n_ref'] and d['LAD']['precision']['in_other'] > 0, d
    tip = ref.copy(); s = tip[80:]; s[s == 3] = 0                                 # LCx stopped 25 mm early
    d = run(tip)['LCx']['recall']
    assert d['distal'] > 0 and d['break_gap'] == 0 and d['break_disc'] == 0, d
    norca = ref.copy(); norca[ref == 4] = 0                                       # RCA tree not drawn
    d = run(norca)['RCA']['recall']
    assert d['absent'] == sum(d.values()), d
    r, p = run(cut)['LAD']['recall'], run(cut)['LAD']['precision']
    assert tf1_from(r, p, ('BREAKS',)) > tf1_from(r, p) and abs(tf1_from(r, p, ('BREAKS',)) - 1) < 1e-9
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    assert len(cases_checked(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json'),
                             os.path.join(ROOT, 'trillium', 'sealed_test.json'))) == 60
    import tempfile
    with tempfile.TemporaryDirectory() as W:
        for bad in (L['locked100'][:1], S['sealed_icx_test'][:1]):
            f = os.path.join(W, 'l.json')
            json.dump(dict(L, tuning60=L['tuning60'][:-1] + bad), open(f, 'w'))
            try:
                cases_checked(f, os.path.join(ROOT, 'trillium', 'sealed_test.json'))
                raise AssertionError('refusal failed')
            except SystemExit as e:
                assert 'REFUSING' in str(e)
    print('[decomp] self-test passed: hit = frozen recall on every fixture; cut -> break_gap + break_disc; '
          '1 mm hole -> hole; swap -> naming; short LCx -> distal; missing RCA -> absent; '
          'locked-100 and sealed ids refused')


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
    cases = cases_checked(a.lists, a.sealed)
    cts = {c: v.get('ct') for c, v in json.load(open(a.layout))['cases'].items()} if a.layout else {}
    jobs = [(c, os.path.join(a.pred, f'{c}.nii.gz'), os.path.join(a.icx, f'{int(c[1:]) + 1}.coronary.nii.gz'),
             os.path.join(a.aorta, f'{c}_aorta.nii.gz'), cts.get(c)) for c in cases]
    with Pool(a.np, initializer=tf1_score.load_metric, maxtasksperchild=4) as p:
        rows = p.map(decompose_case, jobs, chunksize=1)
    res = {'tf1_sha256': tf1_score.TF1_SHA256, 'pred': a.pred, 'summary': summarise(rows), 'rows': rows}
    json.dump(res, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps(res['summary'], indent=1, default=float))


if __name__ == '__main__':
    main()
