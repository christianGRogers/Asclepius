"""Scoring for Atlas run 2 (Round 5, A1/A1a/A1b/A15/A16). One case at a time; used for run 1's val predictions
(Phase A) and for the window-ablation model (Phase B), so both arms are scored by identical code.

* tF1 by the frozen `segtrain.tf1` (vendored as segtrain_tf1.py; the entry point and the job refuse to run unless
  its sha256 equals the hash frozen in vault/Plans/Master plan.md, A1c). Ostium of record: the reference
  centreline voxel nearest the TotalSegmentator aorta (A1). A case without an aorta mask is scored but marked
  provisional and decides nothing (A1a). Classes whose tree has a flagged ostium are reported separately and left
  out of the decisive aggregate (A1b); paired comparisons may include them (every arm shares the ostia).
* Validation columns only: distance of each A1 ostium to the nearest ImageCAS-X start point of the same side, and
  the `thick` / `pool_thick` candidates (inside the ostium rows).
* FP census (A15): every raw FP component (>= 100 voxels, 26-connected, touching no reference voxel), with size,
  class, vessel probability, overlap with ImageCAS-X, distance to the tree and to the aorta, HU, and a category
  fixed here before any result is seen:
      icx_vessel      >= 50 % of its voxels lie within 1 mm of an ImageCAS-X vessel voxel (real vessel the
                      ImageCAS mask omits);
      low_confidence  otherwise, and the 90th percentile of its vessel probability (1 - p_background) < 0.90;
      confident_other otherwise (a confident detection that neither reference contains).
* Threshold sweep (A15's only admissible "raw" lever): one global vessel-probability threshold t, prediction =
  argmax over the 4 vessel classes where 1 - p_background >= t; FP count and tF1 per t (val only; choosing and
  freezing t is a later, separate decision).
"""
import os
import sys

import numpy as np
import nibabel as nib
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import segtrain_tf1 as T  # noqa: E402  (the frozen metric; hash checked by the caller)

CLASSES = (1, 2, 3, 4)
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
SIDE_OF = {1: 'left', 2: 'left', 3: 'left', 4: 'right'}
ICX_NEAR_MM = 1.0
ICX_VESSEL_FRAC = 0.5
LOW_CONF_P90 = 0.90
THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)
CROP_MARGIN_MM = 15.0


def _load(path, dtype=None):
    img = nib.load(path)
    a = np.asanyarray(img.dataobj)
    return (a.astype(dtype) if dtype is not None else a), img


def load_probabilities(npz_path, shape):
    """nnU-Net's exported softmax: key 'probabilities', (C, z, y, x) in SimpleITK order -> (C, x, y, z)."""
    with np.load(npz_path) as z:
        p = z['probabilities']
    p = np.transpose(p, (0, 3, 2, 1))
    if p.shape[1:] != tuple(shape):
        raise ValueError(f'{npz_path}: probabilities {p.shape[1:]} vs label grid {tuple(shape)}')
    return p


def _bbox(masks, sp, shape):
    u = np.zeros(shape, bool)
    for m in masks:
        if m is not None:
            u |= m
    if not u.any():
        return tuple(slice(0, s) for s in shape)
    idx = [np.nonzero(u.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    mv = np.ceil(CROP_MARGIN_MM / sp).astype(int)
    lo = np.maximum([a[0] for a in idx] - mv, 0)
    hi = np.minimum([a[-1] + 1 for a in idx] + mv, shape)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def classes_flagged(ref, report):
    """A1b: the reference classes whose tree carries a flagged ostium (by component and side)."""
    comp, _ = T.components(ref > 0)
    out = set()
    for o in report.ostia:
        if not o.flagged:
            continue
        on = comp == o.tree
        for c in CLASSES:
            if (o.side == 'tree' or o.side == SIDE_OF[c]) and np.any(on & (ref == c)):
                out.add(c)
    return sorted(out)


def _starts_vox(starts_world, affine, offset):
    if starts_world is None or len(starts_world) == 0:
        return None
    v = (np.linalg.inv(affine) @ np.c_[starts_world, np.ones(len(starts_world))].T).T[:, :3]
    return v - np.asarray(offset, float)


def _ostium_side(ref, o):
    if o.side in ('left', 'right'):
        return o.side
    return 'right' if ref[tuple(o.point)] == 4 else 'left'


def a1_score(ref, pred, sp, aorta=None, ct=None, starts=None, rep=None):
    """tF1 @1.5 and @0 with the A1 ostium of record; flags; FP gate; ostium validation rows."""
    rep = rep if rep is not None else T.find_ostia(ref, sp, aorta=aorta, ct=ct)
    r15 = T.tree_f1(ref, pred, sp, tol_mm=1.5, ostia=rep)
    r0 = T.tree_f1(ref, pred, sp, tol_mm=0.0, ostia=rep)
    rows = []
    for o in rep.ostia:
        row = o.as_row()
        side = _ostium_side(ref, o)
        row['side_resolved'] = side
        s = (starts or {}).get(side)
        row['to_icx_start_mm'] = (float(np.min(np.linalg.norm((s - np.asarray(o.point)) * sp, axis=1)))
                                  if s is not None and len(s) else None)
        rows.append(row)
    flagged = classes_flagged(ref, rep)
    return dict(tf1=r15.tf1, tf1_tol0=r0.tf1,
                per_class={int(c): float(v) for c, v in r15.per_class.items()},
                recall={int(c): float(v) for c, v in r15.recall.items()},
                precision={int(c): float(v) for c, v in r15.precision.items()},
                rooted_fraction=r15.rooted_fraction, provisional=bool(rep.provisional),
                flagged_classes=flagged, ostia=rows,
                fp_components=T.fp_components(ref, pred))


def threshold_prediction(prob, t):
    fg = 1.0 - prob[0]
    lab = (np.argmax(prob[1:], axis=0) + 1).astype(np.uint8)
    return np.where(fg >= t, lab, 0).astype(np.uint8)


def census(ref, pred, prob, sp, ct=None, aorta=None, icx=None):
    """One row per raw FP component of ``pred`` (A15)."""
    raw = T.raw_prediction(pred)
    lab, n = T.components(raw > 0)
    if n == 0:
        return []
    touched = set(np.unique(lab[(raw > 0) & (ref > 0)]).tolist()) - {0}
    d_ref = ndi.distance_transform_edt(ref == 0, sampling=sp)
    d_icx = ndi.distance_transform_edt(icx == 0, sampling=sp) if icx is not None and icx.any() else None
    d_ao = ndi.distance_transform_edt(~aorta, sampling=sp) if aorta is not None and aorta.any() else None
    fg = (1.0 - prob[0]) if prob is not None else None
    rows = []
    objs = ndi.find_objects(lab)
    for k in range(1, n + 1):
        if k in touched or objs[k - 1] is None:
            continue
        sl = objs[k - 1]
        m = lab[sl] == k
        vox = int(m.sum())
        cls = np.bincount(raw[sl][m], minlength=5)[1:]
        row = dict(voxels=vox, mm3=float(vox * np.prod(sp)), cls=NAMES[int(np.argmax(cls)) + 1],
                   centroid=[int(round(float(x))) for x in np.mean(np.argwhere(m), axis=0) + [s.start for s in sl]],
                   extent_mm=float(np.linalg.norm([(s.stop - s.start) * sp[i] for i, s in enumerate(sl)])),
                   dist_to_ref_mm=float(d_ref[sl][m].min()))
        if fg is not None:
            f = fg[sl][m]
            row.update(p_mean=float(f.mean()), p_median=float(np.median(f)), p90=float(np.percentile(f, 90)),
                       p_max=float(f.max()))
        if d_icx is not None:
            row['icx_frac'] = float((d_icx[sl][m] <= ICX_NEAR_MM).mean())
        if d_ao is not None:
            row['dist_to_aorta_mm'] = float(d_ao[sl][m].min())
        if ct is not None:
            row['hu_mean'] = float(ct[sl][m].mean())
        if row.get('icx_frac', 0.0) >= ICX_VESSEL_FRAC:
            row['category'] = 'icx_vessel'
        elif 'p90' in row and row['p90'] < LOW_CONF_P90:
            row['category'] = 'low_confidence'
        elif 'p90' in row:
            row['category'] = 'confident_other'
        else:
            row['category'] = 'unknown_no_softmax'
        rows.append(row)
    return rows


def score_case(case, pred_path, ref_path, ct_path=None, aorta_path=None, icx_path=None, npz_path=None,
               starts_world=None, sweep=True):
    """Everything for one case. ``starts_world`` = {'left': (k,3) RAS, 'right': ...} or None."""
    ref, rimg = _load(ref_path, np.uint8)
    pred, _ = _load(pred_path, np.uint8)
    if pred.shape != ref.shape:
        raise ValueError(f'{case}: prediction {pred.shape} vs reference {ref.shape}')
    sp = np.array(rimg.header.get_zooms()[:3], float)
    aorta = _load(aorta_path, np.uint8)[0] > 0 if aorta_path and os.path.exists(aorta_path) else None
    ct = _load(ct_path, np.float32)[0] if ct_path and os.path.exists(ct_path) else None
    icx = _load(icx_path, np.uint8)[0] if icx_path and os.path.exists(icx_path) else None
    prob = load_probabilities(npz_path, ref.shape) if npz_path and os.path.exists(npz_path) else None
    for name, a in (('aorta', aorta), ('ct', ct), ('icx', icx)):
        if a is not None and a.shape != ref.shape:
            raise ValueError(f'{case}: {name} grid {a.shape} vs reference {ref.shape}')
    fgm = (1.0 - prob[0]) >= min(THRESHOLDS) if prob is not None else None
    sl = _bbox([ref > 0, pred > 0, fgm], sp, ref.shape)
    off = [s.start for s in sl]
    ref, pred = ref[sl], pred[sl]
    aorta = aorta[sl] if aorta is not None else None
    ct = ct[sl] if ct is not None else None
    icx = icx[sl] if icx is not None else None
    prob = prob[(slice(None),) + sl] if prob is not None else None
    starts = {k: _starts_vox(v, rimg.affine, off) for k, v in (starts_world or {}).items()}
    out = dict(case=case, spacing=sp.tolist(), has_aorta=aorta is not None, has_softmax=prob is not None,
               crop_offset=off)
    rep = T.find_ostia(ref, sp, aorta=aorta, ct=ct)
    out['a1'] = a1_score(ref, pred, sp, aorta=aorta, ct=ct, starts=starts, rep=rep)
    out['census'] = census(ref, pred, prob, sp, ct=ct, aorta=aorta, icx=icx) if prob is not None else \
        census(ref, pred, None, sp, ct=ct, aorta=aorta, icx=icx)
    if sweep and prob is not None:
        out['sweep'] = {}
        for t in THRESHOLDS:
            pt = threshold_prediction(prob, t)
            r = T.tree_f1(ref, pt, sp, tol_mm=1.5, ostia=rep)
            out['sweep'][str(t)] = dict(tf1=r.tf1, per_class={int(c): float(v) for c, v in r.per_class.items()},
                                        fp_components=T.fp_components(ref, pt))
    return out


# ------------------------------------------------------------------------------------- aggregation
def decisive_case_score(a1, classes=CLASSES):
    """A1a/A1b: macro tF1 over the unflagged classes of a non-provisional case (None if nothing is decisive)."""
    if a1['provisional']:
        return None
    v = [a1['per_class'][c] for c in classes if c in a1['per_class'] and c not in a1['flagged_classes']]
    return float(np.mean(v)) if v else None


def _key(d, c):
    return d.get(c, d.get(str(c)))


def aggregate(per):
    """Summary over cases: decisive (unflagged, aorta) aggregate, flagged trees apart, FP gate, census."""
    def fl(a1):
        return [int(c) for c in a1['flagged_classes']]
    dec = [decisive_case_score(dict(p['a1'], per_class={int(k): v for k, v in p['a1']['per_class'].items()},
                                    flagged_classes=fl(p['a1']))) for p in per]
    out = dict(n=len(per), n_with_aorta=sum(p['has_aorta'] for p in per),
               n_provisional=sum(p['a1']['provisional'] for p in per))
    ok = [d for d in dec if d is not None]
    out['decisive_macro_tf1'] = float(np.mean(ok)) if ok else None
    out['n_decisive_cases'] = len(ok)
    pc, fpc = {}, {}
    n_trees = n_flag = 0
    for c in CLASSES:
        un, fg = [], []
        for p in per:
            a1 = p['a1']
            v = _key(a1['per_class'], c)
            if v is None or a1['provisional']:
                continue
            n_trees += 1
            (fg if c in fl(a1) else un).append(v)
        n_flag += len(fg)
        pc[NAMES[c]] = float(np.mean(un)) if un else None
        fpc[NAMES[c]] = dict(n=len(fg), mean=float(np.mean(fg)) if fg else None)
    out.update(decisive_per_class=pc, flagged_per_class=fpc, n_class_trees=n_trees, n_flagged_class_trees=n_flag)
    out['all_macro_tf1_incl_flagged'] = float(np.mean([p['a1']['tf1'] for p in per])) if per else None
    out['all_macro_tf1_tol0'] = float(np.mean([p['a1']['tf1_tol0'] for p in per])) if per else None
    fp = np.array([p['a1']['fp_components'] for p in per], float)
    out['fp_components_mean'] = float(fp.mean()) if len(fp) else None
    out['fp_cases_le_1'] = int((fp <= 1).sum())
    rows = [r for p in per for r in p['census']]
    cats = {}
    for r in rows:
        cats.setdefault(r['category'], []).append(r['mm3'])
    tot_n, tot_v = len(rows), sum(r['mm3'] for r in rows)
    out['census'] = dict(n_components=tot_n, mm3_total=tot_v,
                         by_category={k: dict(n=len(v), share_n=len(v) / tot_n if tot_n else None,
                                              mm3=float(sum(v)), share_mm3=float(sum(v)) / tot_v if tot_v else None)
                                      for k, v in sorted(cats.items())})
    if tot_n:
        top = max(out['census']['by_category'].items(), key=lambda kv: kv[1]['n'])
        out['census']['majority_by_count'] = top[0] if top[1]['share_n'] > 0.5 else 'none (no category > 50 %)'
    ost = [o for p in per for o in p['a1']['ostia'] if o.get('to_icx_start_mm') is not None]
    if ost:
        d = np.array([o['to_icx_start_mm'] for o in ost])
        out['ostium_validation'] = dict(n=len(d), median_mm=float(np.median(d)), within_5mm=int((d <= 5).sum()),
                                        flagged=int(sum(o['flagged'] for o in ost)),
                                        silent_misses=int(sum((o['to_icx_start_mm'] > 5) and not o['flagged']
                                                              for o in ost)))
    sw = [p['sweep'] for p in per if p.get('sweep')]
    if sw:
        out['sweep'] = {t: dict(tf1=float(np.mean([s[t]['tf1'] for s in sw])),
                                fp_components=float(np.mean([s[t]['fp_components'] for s in sw])))
                        for t in sw[0]}
    return out


def paired(per_a, per_b, n_boot=10000, seed=0):
    """B - A on the cases both arms scored. tF1: decisive per-case macro (A1b: flagged classes left out; the
    ostia are identical across arms because reference and aorta are). FP: components per case."""
    a = {p['case']: p for p in per_a}
    b = {p['case']: p for p in per_b}
    cs = sorted(set(a) & set(b))
    rng = np.random.default_rng(seed)

    def fl(p):
        return dict(p['a1'], per_class={int(k): v for k, v in p['a1']['per_class'].items()},
                    flagged_classes=[int(c) for c in p['a1']['flagged_classes']])

    def boot(d):
        d = np.asarray(d, float)
        if len(d) == 0:
            return dict(n=0, mean=None, ci=None)
        bs = rng.choice(d, (n_boot, len(d))).mean(axis=1)
        return dict(n=len(d), mean=float(d.mean()), ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                    better=int((d > 0).sum()), worse=int((d < 0).sum()))
    dt = []
    for c in cs:
        x, y = decisive_case_score(fl(a[c])), decisive_case_score(fl(b[c]))
        if x is not None and y is not None:
            dt.append(y - x)
    dfp = [b[c]['a1']['fp_components'] - a[c]['a1']['fp_components'] for c in cs]
    return dict(n_cases=len(cs), tf1_b_minus_a=boot(dt), fp_b_minus_a=boot(dfp))


def decide_window(pr):
    """The accepted rule (Round 5, A16): paired tF1 under A1 with the CI excluding 0 decides; on a tie, the
    window with fewer FP components wins."""
    t = pr['tf1_b_minus_a']
    if t['ci'] is None:
        return dict(winner=None, reason='no paired decisive cases')
    if t['ci'][0] > 0:
        return dict(winner='default', reason=f"tF1 B−A {t['mean']:+.4f}, CI {t['ci'][0]:+.4f}..{t['ci'][1]:+.4f} > 0")
    if t['ci'][1] < 0:
        return dict(winner='fixed', reason=f"tF1 B−A {t['mean']:+.4f}, CI {t['ci'][0]:+.4f}..{t['ci'][1]:+.4f} < 0")
    f = pr['fp_b_minus_a']['mean']
    if f is None or f == 0:
        return dict(winner='fixed', reason='tF1 tie and equal FP: the plan keeps its fixed window (no change)')
    return dict(winner='default' if f < 0 else 'fixed',
                reason=f"tF1 tie (CI {t['ci'][0]:+.4f}..{t['ci'][1]:+.4f}); FP B−A {f:+.3f} per case")
