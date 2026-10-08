"""Two reads per case (Human decision D2): training-label forms (A11), adjudication triggers (A11), scoring and
acceptance (A10). Pure numpy/scipy; the tree-F1 is trillium/atlas/lib/tf1.py (Delta's definition, validated
identical to Delta's scorer).

Training-label forms (labels 0..4, IGNORE = 5):
  a11_samples(A, B)        DEFAULT (A11). Each read is its own sample; voxels both reads call vessel but name
                           differently are IGNORE in both samples; extent differences keep each read's own label.
  agree_or_ignore(A, B)    Atlas v3 form: one label; any disagreement (names or extent) -> IGNORE.
  both_as_samples(A, B)    pure: (A, B) unchanged.
  The pre-registered A11 test compares the first two (and the third if budget allows) at the first wave with
  >= 150 double-read cases.

Adjudication (case level, A11): a third read is needed if
  inter-read macro tF1 < 0.80, or ostium disagreement > 5 mm, or LM-end (carina) disagreement > 5 mm,
  or LAD<->LCx swap > 5 % of LAD+LCx voxels both reads call vessel,
  EXCEPT a ramus-only disagreement (D1b resolves it, never a third read): the swap is the only trigger and the
  swapped voxels form one branch (one component, <= 25 % of LAD+LCx) that leaves within 10 mm of the carina. D1b then applies: that branch -> LCx in
  both reads. (Geometric heuristic: a branch leaving at the carina that the two reads assign to different trunks.)
Scoring (A10): per case, the mean of tF1(pred vs read A) and tF1(pred vs read B); after adjudication the overruled
read is replaced by the adjudicator's read. No fused reference is ever built for scoring.
Acceptance (A10): per class, lower bound of the paired bootstrap 95 % CI of (model - inter-read) > -0.02.
"""
import os, sys
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'trillium', 'atlas', 'lib'))
import tf1

IGNORE = 5
S26 = np.ones((3, 3, 3), bool)


# ------------------------------------------------------------------ training-label forms
def a11_samples(A, B):
    both = (A > 0) & (B > 0)
    name_dis = both & (A != B)
    a, b = A.copy(), B.copy()
    a[name_dis] = IGNORE; b[name_dis] = IGNORE
    return a, b


def agree_or_ignore(A, B):
    out = A.copy(); out[A != B] = IGNORE
    return out


def both_as_samples(A, B):
    return A.copy(), B.copy()


# ------------------------------------------------------------------ geometry helpers
def _carina(L, sp):
    """LM-end point: LM voxel closest to the union of LAD and LCx (None if no LM or no LAD/LCx)."""
    lm = np.argwhere(L == 1)
    if len(lm) == 0 or not np.isin(L, (2, 3)).any():
        return None
    d = ndi.distance_transform_edt(~np.isin(L, (2, 3)), sampling=sp)
    return lm[np.argmin(d[tuple(lm.T)])]


def _ostia(L, sp):
    sk = tf1.skeletonize(L > 0)
    rad = ndi.distance_transform_edt(L > 0, sampling=sp)
    return [np.array(r) for r in tf1._ostia(L, sk, rad, np.asarray(sp, float))]


def _match_mm(pa, pb, sp):
    """max over points in pa of the distance to the nearest point in pb (mm); inf if counts differ."""
    if len(pa) != len(pb):
        return float('inf')
    if not pa:
        return 0.0
    sp = np.asarray(sp, float)
    return float(max(min(np.linalg.norm((a - b) * sp) for b in pb) for a in pa))


# ------------------------------------------------------------------ inter-read agreement and adjudication
def inter_read(A, B, sp, tol=1.5):
    """Symmetric inter-read tF1 (mean of B scored against A and A against B), per class and macro."""
    ab = tf1.score(A, B, sp, tol=tol, min_comp=0); ba = tf1.score(B, A, sp, tol=tol, min_comp=0)
    per = {c: 0.5 * (ab['tf1_per_class'].get(c, np.nan) + ba['tf1_per_class'].get(c, np.nan))
           for c in set(ab['tf1_per_class']) | set(ba['tf1_per_class'])}
    return dict(tf1=0.5 * (ab['tf1'] + ba['tf1']), tf1_per_class=per)


def adjudication(A, B, sp, tf1_min=0.80, mm=5.0, swap_max=0.05, ramus_win_mm=10.0, ramus_max_frac=0.25):
    sp = np.asarray(sp, float)
    ir = inter_read(A, B, sp)
    ost = _match_mm(_ostia(A, sp), _ostia(B, sp), sp)
    ca, cb = _carina(A, sp), _carina(B, sp)
    car = float(np.linalg.norm((ca - cb) * sp)) if ca is not None and cb is not None else (0.0 if ca is None and cb is None else float('inf'))
    both = (A > 0) & (B > 0)
    swapped = both & (((A == 2) & (B == 3)) | ((A == 3) & (B == 2)))
    ladlcx = both & np.isin(A, (2, 3)) & np.isin(B, (2, 3))
    swap = float(swapped.sum() / max(ladlcx.sum(), 1))
    trig = dict(inter_read_tf1=ir['tf1'] < tf1_min, ostium=ost > mm, carina=car > mm, swap=swap > swap_max)
    ramus_only = False
    # a ramus is ONE side branch: the swapped voxels must be a minority of LAD+LCx (a wholesale LAD/LCx swap is not)
    if trig['swap'] and not (trig['ostium'] or trig['carina']) and swap <= ramus_max_frac:
        lab, n = ndi.label(swapped, structure=S26)
        if n:
            sizes = np.bincount(lab.ravel())[1:]
            main = np.argmax(sizes) + 1
            frac_main = sizes[main - 1] / sizes.sum()
            if ca is not None and frac_main >= 0.9:
                pts = np.argwhere(lab == main)
                dmin = float(np.min(np.linalg.norm((pts - ca) * sp, axis=1)))
                ramus_only = dmin <= ramus_win_mm
    # a ramus-only disagreement also drags inter-read tF1 down; it does not count against the case on its own
    needed = trig['ostium'] or trig['carina'] or (trig['swap'] and not ramus_only) or \
        (trig['inter_read_tf1'] and not ramus_only)
    return dict(needed=bool(needed), ramus_only=bool(ramus_only), triggers={k: bool(v) for k, v in trig.items()},
                inter_read_tf1=ir['tf1'], inter_read_per_class=ir['tf1_per_class'], ostium_mm=ost, carina_mm=car,
                ladlcx_swap=swap, swapped_voxels=int(swapped.sum()))


def apply_d1b(A, B, sp):
    """Resolve a ramus-only disagreement by D1b: the swapped branch is LCx in both reads."""
    both = (A > 0) & (B > 0)
    sw = both & (((A == 2) & (B == 3)) | ((A == 3) & (B == 2)))
    a, b = A.copy(), B.copy(); a[sw] = 3; b[sw] = 3
    return a, b


# ------------------------------------------------------------------ scoring and acceptance (A10)
def case_score(pred, A, B, sp, adjudicated=None):
    """Mean tF1 of pred against each read. adjudicated = (which, C): read 'A' or 'B' was overruled by read C."""
    if adjudicated:
        which, C = adjudicated
        A, B = (C, B) if which == 'A' else (A, C)
    sa = tf1.score(A, pred, sp); sb = tf1.score(B, pred, sp)
    per = {c: 0.5 * (sa['tf1_per_class'].get(c, np.nan) + sb['tf1_per_class'].get(c, np.nan))
           for c in set(sa['tf1_per_class']) | set(sb['tf1_per_class'])}
    return dict(tf1=0.5 * (sa['tf1'] + sb['tf1']), tf1_per_class=per,
                fp_components=0.5 * (sa['fp_components'] + sb['fp_components']), swap_rate=0.5 * (sa['swap_rate'] + sb['swap_rate']))


def acceptance(model_per_case, inter_per_case, margin=0.02, n_boot=5000, seed=0):
    """model_per_case / inter_per_case: lists (same cases, same order) of {class: tF1}. Returns per class the paired
    mean difference, its bootstrap 95 % CI and whether the non-inferiority bound (lower CI > -margin) holds."""
    rng = np.random.default_rng(seed); out = {}
    for c in (1, 2, 3, 4):
        d = np.array([m[c] - i[c] for m, i in zip(model_per_case, inter_per_case)
                      if c in m and c in i and not np.isnan(m[c]) and not np.isnan(i[c])])
        if len(d) < 2:
            out[c] = dict(n=len(d), passed=None); continue
        boots = rng.choice(d, (n_boot, len(d)), replace=True).mean(1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out[c] = dict(n=len(d), mean_diff=float(d.mean()), ci=[float(lo), float(hi)], passed=bool(lo > -margin))
    return out
