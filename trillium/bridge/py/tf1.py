"""Tree-F1 (A1/D3) for one case, self-contained (this folder runs without the repo).
Same construction as Delta's provisional implementation (vault: Delta - Dice cannot see ...):
  recall_c    = reference centreline of class c that is (i) inside the prediction, (ii) named c, and
                (iii) in a predicted piece connected to the reference ostium, gaps <= tol mm forgiven
  precision_c = predicted centreline named c that lies inside reference voxels of class c
  tF1 = macro mean over classes present in the reference.
Ostia (same for every arm, so paired differences are unaffected): left = reference LM centreline endpoint
farthest from LAD/LCx; right = thickest RCA centreline endpoint. NOT the A1 aorta-contact ostium (A9):
these numbers are provisional by the master's own rule and are reported as such.
"""
import cc3d
import networkx as nx
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize


def ball(r_mm, sp):
    rv = np.ceil(r_mm / np.asarray(sp)).astype(int)
    g = np.meshgrid(*[np.arange(-k, k + 1) * s for k, s in zip(rv, sp)], indexing='ij')
    return (g[0] ** 2 + g[1] ** 2 + g[2] ** 2) <= r_mm ** 2 + 1e-9


def skel(m):
    return skeletonize(m.astype(np.uint8)).astype(bool) if m.any() else np.zeros_like(m, bool)


class Ref:
    def __init__(self, lab, sp):
        self.lab = lab.astype(np.uint8); self.m = lab > 0; self.sp = np.asarray(sp, float)
        self.sk = skel(self.m)
        self.pts = np.argwhere(self.sk)
        self.lab_sk = self.lab[tuple(self.pts.T)]
        # endpoints of the skeleton graph (26-neighbourhood count == 1)
        k = np.ones((3, 3, 3)); nb = ndi.convolve(self.sk.astype(np.uint8), k, mode='constant') - 1
        deg = nb[tuple(self.pts.T)]
        ends = deg == 1
        rad = ndi.distance_transform_edt(self.m, sampling=self.sp)[tuple(self.pts.T)]
        self.roots = []
        P = self.pts * self.sp
        lm = np.where(self.lab_sk == 1)[0]; ll = np.where(np.isin(self.lab_sk, (2, 3)))[0]
        if len(lm) and len(ll):
            d = cKDTree(P[ll]).query(P[lm])[0]
            cand = lm[ends[lm]] if ends[lm].any() else lm
            dc = cKDTree(P[ll]).query(P[cand])[0]
            self.roots.append(tuple(self.pts[cand[np.argmax(dc)]]))
        elif len(ll):
            cand = ll[ends[ll]] if ends[ll].any() else ll
            self.roots.append(tuple(self.pts[cand[np.argmax(rad[cand])]]))
        rc = np.where(self.lab_sk == 4)[0]
        if len(rc):
            cand = rc[ends[rc]] if ends[rc].any() else rc
            kd = cKDTree(P)
            score = [np.median(rad[kd.query_ball_point(P[i], 4.0)]) for i in cand]
            self.roots.append(tuple(self.pts[cand[int(np.argmax(score))]]))


def score(ref, pred_lab, tol=1.5):
    pred = pred_lab > 0
    out = {}
    dil = ndi.binary_dilation(pred, ball(tol / 2, ref.sp)) if tol > 0 else pred
    comp = cc3d.connected_components(dil, connectivity=26)
    rooted_ids = {comp[r] for r in ref.roots if comp[r] > 0}
    inside = pred[tuple(ref.pts.T)]
    rooted = np.isin(comp[tuple(ref.pts.T)], list(rooted_ids)) & inside
    psk_ref = pred_lab[tuple(ref.pts.T)]
    sk_p = skel(pred)
    pl = pred_lab[sk_p]; rl = ref.lab[sk_p]
    tf, per, swapped = [], {}, []
    for c in (1, 2, 3, 4):
        g = ref.lab_sk == c
        if not g.any():
            continue
        rec = float((rooted & g & (psk_ref == c)).sum() / g.sum())
        pc = pl == c
        prec = float((rl[pc] == c).mean()) if pc.any() else 0.0
        f = 2 * rec * prec / (rec + prec) if rec + prec else 0.0
        tf.append(f); per[c] = f
        det = g & inside
        if det.sum() >= 10 and (psk_ref[det] == c).mean() < 0.5:
            swapped.append(c)
    out['tf1'] = float(np.mean(tf)) if tf else 0.0
    out['tf1_per_class'] = per
    out['swapped_classes'] = swapped
    out['centreline_label_acc'] = float((psk_ref[inside] == ref.lab_sk[inside]).mean()) if inside.any() else 0.0
    ds = []
    for c in (1, 2, 3, 4):
        a, b = ref.lab == c, pred_lab == c
        if a.any():
            ds.append(2 * (a & b).sum() / (a.sum() + b.sum()))
    out['macro_dice'] = float(np.mean(ds))
    out['binary_dice'] = float(2 * (ref.m & pred).sum() / max(ref.m.sum() + pred.sum(), 1))
    return out
