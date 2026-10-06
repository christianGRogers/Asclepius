"""Tree-F1 (Delta's definition, the master plan's decisive metric) and companion metrics, self-contained.

Per class c present in the reference:
  recall_c    = fraction of reference class-c centreline that is predicted as class c AND lies in a predicted
                component that contains the reference ostium of its tree (pieces within `tol` mm count as
                connected; the ostium is matched within max(tol, 1 voxel))
  precision_c = fraction of predicted class-c centreline lying inside reference class-c voxels
  tF1_c = harmonic mean; macro over classes present in the reference.
Ostium: Delta's `thick` rule (thickest reference centreline endpoint, LM endpoints preferred on the left tree).
PROVISIONAL under amendment A9: the decisive implementation is the port in src/segtrain with the aorta-contact
ostium; this one exists so the Trillium experiment can report numbers without TotalSegmentator.
Validated on CPU against experiments/Delta/perturb_metrics.score at tol=0 (see selftest)."""
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

S26 = np.ones((3, 3, 3), bool)

def _ball(r_mm, sp):
    rr = np.ceil(r_mm / sp).astype(int)
    g = np.mgrid[-rr[0]:rr[0] + 1, -rr[1]:rr[1] + 1, -rr[2]:rr[2] + 1].astype(float)
    return ((g[0] * sp[0]) ** 2 + (g[1] * sp[1]) ** 2 + (g[2] * sp[2]) ** 2) <= r_mm ** 2 + 1e-9

def _ostia(ref, sk, rad, sp):
    pts = np.argwhere(sk)
    if len(pts) == 0:
        return []
    nb = ndi.convolve(sk.astype(np.uint8), S26.astype(np.uint8), mode='constant') - 1
    deg = nb[tuple(pts.T)]
    lab = ref[tuple(pts.T)]
    r = rad[tuple(pts.T)]
    P = pts * sp
    roots = []
    for cls_set in ((1,), (1, 2, 3), (4,)):
        if cls_set == (1, 2, 3) and roots:
            continue
        cand = np.nonzero(np.isin(lab, cls_set) & (deg == 1))[0]
        if len(cand) == 0:
            continue
        best, bv = None, -1
        for v in cand:
            near = np.linalg.norm(P - P[v], axis=1) <= 3.0
            mv = np.median(r[near])
            if mv > bv:
                bv, best = mv, v
        roots.append(tuple(pts[best]))
    return roots

def score(ref, pred, sp, tol=1.5, min_comp=100):
    """ref, pred: uint8 4-class arrays on the same grid. Returns dict."""
    sp = np.asarray(sp, float)
    out = {}
    union = (ref > 0) | (pred > 0)
    if not (ref > 0).any():
        return dict(empty_reference=True)
    idx = np.nonzero(union)
    m = np.ceil(4.0 / sp).astype(int)
    lo = np.maximum([i.min() for i in idx] - m, 0); hi = np.minimum([i.max() + 1 for i in idx] + m, ref.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    R, Pr = ref[sl].copy(), pred[sl].copy()
    # raw prediction hygiene (always-on rule): drop predicted components < min_comp voxels
    pl, n = ndi.label(Pr > 0, structure=S26)
    if n:
        sizes = np.bincount(pl.ravel()); small = sizes < min_comp; small[0] = False
        Pr[small[pl]] = 0
    Rm, Pm = R > 0, Pr > 0
    rsk = skeletonize(Rm); psk = skeletonize(Pm) if Pm.any() else np.zeros_like(Pm)
    rad = ndi.distance_transform_edt(Rm, sampling=sp)
    roots = _ostia(R, rsk, rad, sp)
    # connectivity with gap tolerance: grow each predicted voxel by tol/2 and label
    if tol > 0:
        grown = ndi.binary_dilation(Pm, structure=_ball(tol / 2.0, sp))
    else:
        grown = Pm
    gl, _ = ndi.label(grown, structure=S26)
    comp_of_pred = np.where(Pm, gl, 0)
    rtol = max(tol, float(sp.max()))
    rootcomps = set()
    for rt in roots:
        rr = np.ceil(rtol / sp).astype(int)
        s2 = tuple(slice(max(rt[k] - rr[k], 0), min(rt[k] + rr[k] + 1, R.shape[k])) for k in range(3))
        sub = comp_of_pred[s2]
        g = np.argwhere(sub > 0)
        if len(g):
            off = np.array([s.start for s in s2])
            dist = np.linalg.norm((g + off - np.array(rt)) * sp, axis=1)
            rootcomps |= set(sub[tuple(g[dist <= rtol].T)].tolist())
    rp = np.argwhere(rsk); rl = R[tuple(rp.T)]; pl_at_r = Pr[tuple(rp.T)]
    rooted = np.isin(comp_of_pred[tuple(rp.T)], list(rootcomps)) if rootcomps else np.zeros(len(rp), bool)
    pp = np.argwhere(psk); plab = Pr[tuple(pp.T)]; rlab_at_p = R[tuple(pp.T)]
    tf, cl, dice = {}, {}, {}
    for c in (1, 2, 3, 4):
        g = rl == c
        if not g.any():
            continue
        rec = float(((pl_at_r == c) & rooted & g).sum() / g.sum())
        sens = float((pl_at_r[g] == c).mean())
        pc = plab == c
        prec = float((rlab_at_p[pc] == c).mean()) if pc.any() else 0.0
        tf[c] = 2 * rec * prec / (rec + prec) if rec + prec else 0.0
        cl[c] = 2 * sens * prec / (sens + prec) if sens + prec else 0.0
        a, b2 = R == c, Pr == c
        dice[c] = float(2 * (a & b2).sum() / max(a.sum() + b2.sum(), 1))
    out['tf1'] = float(np.mean(list(tf.values())))
    out['tf1_per_class'] = {int(k): v for k, v in tf.items()}
    out['class_cldice'] = float(np.mean(list(cl.values())))
    out['cldice_per_class'] = {int(k): v for k, v in cl.items()}
    out['dice_per_class'] = {int(k): v for k, v in dice.items()}
    out['macro_dice'] = float(np.mean(list(dice.values())))
    # FP gate on the raw prediction: predicted components (26-conn) touching no reference voxel
    pl2, n2 = ndi.label(Pm, structure=S26)
    touched = set(np.unique(pl2[Pm & Rm]).tolist()) - {0}
    out['fp_components'] = int(n2 - len(touched))
    out['pred_components'] = int(n2)
    out['ref_components'] = int(ndi.label(Rm, structure=S26)[1])
    det = pl_at_r > 0
    out['swap_rate'] = float(((pl_at_r != rl) & det).sum() / max(det.sum(), 1))
    out['n_roots'] = len(roots)
    return out
