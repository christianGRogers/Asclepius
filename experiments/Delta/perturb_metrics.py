"""E3: which metric sees which failure?  Simulate typical CNN errors on real GT masks
and score each corrupted copy against the GT with overlap and topology metrics.

Usage: python perturb_metrics.py <icx|pseudo> <out.jsonl> case [case ...]

Binary perturbations (applied to the binary GT):
  erode1      : 1-voxel 6-conn erosion (systematic under-segmentation of the wall)
  dilate1     : 1-voxel dilation (over-segmentation)
  gaps5       : 5 cuts (ball r=1.5 mm) at random thin-vessel skeleton points (centre EDT < 0.75 mm,
                i.e. lumen <= ~3 in-plane voxels / ~1.1 mm wide) >= 6 mm from any skeleton endpoint
  gaps5_thick : 5 cuts (ball r=2.5 mm) at random thick points (centre EDT >= 1.0 mm), same rule
  drop_term30 : delete 30 % of terminal (distal) branches entirely (voxels nearest to them)
  fp5         : add 5 false-positive blobs (r=2 mm) 5-11 mm from the tree
  thin_lost   : delete every voxel whose nearest skeleton point has r < 0.6 mm (thin tail loss)
Reference: ImageCAS-X lumen + segment labels mapped to 4 classes (subtree convention, see
treelib.ICX_TO_4); fallback 'pseudo' = original mask + geometric pseudo-labels.
Label perturbations (binary mask unchanged, labels corrupted):
  carina5     : first 5 mm (geodesic) of LCx relabelled LAD
  carina10    : first 10 mm of LCx relabelled LAD
  side_swap   : the largest side subtree hanging off the LAD main path relabelled LCx
  d1_as_lcx   : (ImageCAS-X only) every D1 voxel relabelled LCx
  im_as_lad   : (ImageCAS-X only) ramus intermedius relabelled LAD (a convention disagreement)
  lm_as_lad   : LM relabelled LAD
  islands     : 5 random 3 mm stretches inside LAD/LCx/RCA relabelled to a neighbour class

Metrics: Dice, clDice (skeleton-based, skimage Lee skeletons), skeleton recall, NSD@0.5mm,
beta0 error (26-conn components, |pred-gt|), segment detection (GT skeleton segments >= 3 mm,
detected if >= 50 % of their skeleton voxels are inside pred), terminal-segment detection,
rooted skeleton recall (fraction of GT skeleton inside a pred component that also contains
the GT ostium of that tree), macro per-class Dice, centreline label accuracy (fraction of GT
skeleton voxels whose pred label equals GT label), per-class component excess
(sum_c max(0, ncomp_c(pred)-ncomp_c(gt))).
"""
import json
import sys
import time

import cc3d
import networkx as nx
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import treelib as T  # noqa: E402

RNG = np.random.default_rng(0)


def ball(r_mm, sp):
    rr = np.ceil(r_mm / sp).astype(int)
    g = np.ogrid[tuple(slice(-k, k + 1) for k in rr)]
    return sum((g[i] * sp[i]) ** 2 for i in range(3)) <= r_mm ** 2


def stamp(arr, c, b, val):
    rr = np.array(b.shape) // 2
    lo = np.array(c) - rr; hi = lo + b.shape
    l2 = np.maximum(lo, 0); h2 = np.minimum(hi, arr.shape)
    sub = arr[l2[0]:h2[0], l2[1]:h2[1], l2[2]:h2[2]]
    bb = b[l2[0] - lo[0]:b.shape[0] - (hi[0] - h2[0]), l2[1] - lo[1]:b.shape[1] - (hi[1] - h2[1]),
           l2[2] - lo[2]:b.shape[2] - (hi[2] - h2[2])]
    sub[bb] = val


def surface(m):
    return m & ~ndi.binary_erosion(m)


def nsd(a, b, sp, tol=0.5):
    sa, sb = surface(a), surface(b)
    if sa.sum() == 0 or sb.sum() == 0:
        return float('nan')
    da = ndi.distance_transform_edt(~sa, sampling=sp); db = ndi.distance_transform_edt(~sb, sampling=sp)
    return float(((db[sa] <= tol).sum() + (da[sb] <= tol).sum()) / (sa.sum() + sb.sum()))


def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float('nan')


class GT:
    def __init__(self, case, source='icx'):
        self.raw = None
        if source == 'icx':
            # real per-segment reference: ImageCAS-X lumen, 4-class subtree convention
            self.m, self.lab, self.raw, self.sp, lo, axc = T.load_icx(case, margin_mm=12.0)
            self.info = {}
        else:
            self.m, self.sp, lo, axc = T.load_crop(case, margin_mm=12.0)
            self.m = self.m.astype(bool)
            self.lab, self.info = T.pseudo_labels(self.m.astype(np.uint8), self.sp, axc)
        self.skel = T.skeletonise(self.m)
        self.pts, self.G = T.skeleton_graph(self.skel, self.sp)
        self.rad = T.radius_mm(self.m, self.sp)
        self.r_sk = self.rad[tuple(self.pts.T)]
        segs, deg = T.segments(self.G)
        self.segs = [s for s in segs if T.path_len(self.G, s) >= 3.0]
        self.term = [s for s in self.segs if deg[s[0]] == 1 or deg[s[-1]] == 1]
        ends = [v for v, d in deg.items() if d == 1]
        de = nx.multi_source_dijkstra_path_length(self.G, ends, weight='w')
        self.d_end = np.array([de.get(i, 0.0) for i in range(len(self.pts))])
        self.ncomp = cc3d.connected_components(self.m, connectivity=26, return_N=True)[1]
        # ostia: per tree (left = classes 1-3, right = 4), the thickest skeleton endpoint
        # (median radius over ~20 neighbouring skeleton voxels); LM endpoints preferred on the left
        self.roots = []
        lsk = self.lab[tuple(self.pts.T)]
        dg = np.array([self.G.degree(i) for i in range(len(self.pts))])
        for cls_set in ((1,), (1, 2, 3), (4,)):
            if cls_set == (1, 2, 3) and self.roots:
                continue  # LM endpoint already found
            sel = np.isin(lsk, cls_set)
            cand = np.nonzero(sel & (dg == 1))[0]
            if len(cand) == 0:
                continue
            best = max(cand, key=lambda v: np.median([self.r_sk[u] for u in
                                                      nx.single_source_shortest_path_length(self.G, v, cutoff=20)]))
            self.roots.append(tuple(self.pts[best]))
        self.ncomp_c = {c: cc3d.connected_components(self.lab == c, connectivity=26, return_N=True)[1]
                        for c in (1, 2, 3, 4)}
        # nearest skeleton index for every voxel (for branch deletion)
        idx = -np.ones(self.m.shape, np.int64); idx[tuple(self.pts.T)] = np.arange(len(self.pts))
        _, inds = ndi.distance_transform_edt(idx < 0, sampling=self.sp, return_indices=True)
        self.near = idx[tuple(inds)]
        self.lab_sk = self.lab[tuple(self.pts.T)]


def score(gt, pred, plab=None):
    m = gt.m
    r = dict(dice=dice(m, pred))
    if pred is gt.m or np.array_equal(pred, gt.m):
        sp_ = gt.skel  # same binary mask: reuse the GT skeleton
    else:
        sp_ = T.skeletonise(pred) if pred.any() else np.zeros_like(pred)
    tprec = float((sp_ & m).sum() / max(sp_.sum(), 1)); tsens = float(pred[tuple(gt.pts.T)].mean())
    r['cldice'] = 2 * tprec * tsens / (tprec + tsens) if tprec + tsens else 0.0
    r['skel_recall'] = tsens
    r['nsd05'] = nsd(m, pred, gt.sp, 0.5)
    pl, n = cc3d.connected_components(pred, connectivity=26, return_N=True)
    r['ncomp'] = int(n); r['beta0_err'] = abs(int(n) - gt.ncomp)
    inside = pred[tuple(gt.pts.T)]
    r['seg_det'] = float(np.mean([inside[s].mean() >= 0.5 for s in gt.segs]))
    r['term_det'] = float(np.mean([inside[s].mean() >= 0.5 for s in gt.term]))
    rootcomps = {pl[rt] for rt in gt.roots if pl[rt] > 0}
    r['rooted_recall'] = float(np.isin(pl[tuple(gt.pts.T)], list(rootcomps)).mean()) if rootcomps else 0.0
    if plab is None:
        plab = np.where(pred, gt.lab, 0)
        # newly added voxels take nearest GT label
        add = pred & (gt.lab == 0)
        if add.any():
            _, inds = ndi.distance_transform_edt(gt.lab == 0, sampling=gt.sp, return_indices=True)
            plab[add] = gt.lab[tuple(inds)][add]
    ds = [dice(gt.lab == c, plab == c) for c in (1, 2, 3, 4) if (gt.lab == c).any()]
    r['macro_dice'] = float(np.mean(ds))
    r['dice_per_class'] = [float(x) for x in ds]
    psk = plab[tuple(gt.pts.T)]
    det = psk > 0
    r['cl_label_acc'] = float((psk == gt.lab_sk).mean())
    r['swap_rate'] = float(((psk != gt.lab_sk) & det).sum() / max(det.sum(), 1))
    exc = 0
    for c in (1, 2, 3, 4):
        nc = cc3d.connected_components(plab == c, connectivity=26, return_N=True)[1]
        exc += max(0, nc - gt.ncomp_c[c])
    r['class_comp_excess'] = int(exc)
    # tree-F1 (proposed decisive metric): per class c,
    #   recall_c    = GT-centreline of class c that is predicted as c AND lies in a predicted component
    #                 that contains a GT ostium (i.e. reachable from the aorta through the prediction)
    #   precision_c = predicted-centreline labelled c that lies inside GT voxels of class c
    # tF1_c = harmonic mean; macro over classes present in GT.
    pcomp_sk = pl[tuple(gt.pts.T)]
    rooted = np.isin(pcomp_sk, list(rootcomps)) if rootcomps else np.zeros(len(gt.pts), bool)
    psk_lab = plab[sp_]
    gsk_at_p = gt.lab[sp_]
    tf = []; rec_l = []; prec_l = []
    for c in (1, 2, 3, 4):
        g = gt.lab_sk == c
        if not g.any():
            continue
        rec = float(((psk == c) & rooted & g).sum() / g.sum())
        pc = psk_lab == c
        prec = float((gsk_at_p[pc] == c).mean()) if pc.any() else 0.0
        rec_l.append(rec); prec_l.append(prec)
        tf.append(2 * rec * prec / (rec + prec) if rec + prec else 0.0)
    r['tf1'] = float(np.mean(tf)); r['tf1_rec'] = float(np.mean(rec_l)); r['tf1_prec'] = float(np.mean(prec_l))
    r['tf1_per_class'] = tf
    # per-class clDice (labelled skeletons, no rooting) for comparison
    cl = []
    for c in (1, 2, 3, 4):
        g = gt.lab_sk == c
        if not g.any():
            continue
        sens = float((psk[g] == c).mean())
        pc = psk_lab == c
        prec = float((gsk_at_p[pc] == c).mean()) if pc.any() else 0.0
        cl.append(2 * sens * prec / (sens + prec) if sens + prec else 0.0)
    r['class_cldice'] = float(np.mean(cl))
    return r


def perturb_binary(gt, kind):
    m = gt.m.copy()
    if kind == 'erode1':
        return ndi.binary_erosion(m)
    if kind == 'dilate1':
        return ndi.binary_dilation(m)
    if kind in ('gaps5', 'gaps5_thick'):
        # cut points >= 6 mm (geodesic) from any skeleton endpoint, so a cut severs rather than trims
        cand = np.nonzero((gt.r_sk < 0.75) & (gt.d_end >= 6))[0] if kind == 'gaps5' else \
            np.nonzero((gt.r_sk >= 1.0) & (gt.d_end >= 6))[0]
        if len(cand) == 0:
            return None
        b = ball(1.5 if kind == 'gaps5' else 2.5, gt.sp)
        for v in RNG.choice(cand, size=min(5, len(cand)), replace=False):
            stamp(m, gt.pts[v], b, False)
        return m
    if kind == 'drop_term30':
        k = max(1, int(round(0.3 * len(gt.term))))
        chosen = [gt.term[i] for i in RNG.choice(len(gt.term), size=k, replace=False)]
        nodes = np.zeros(len(gt.pts), bool)
        for s in chosen:
            nodes[s[1:-1] if len(s) > 2 else s] = True
        m[nodes[gt.near] & m] = False
        return m
    if kind == 'thin_lost':
        thin = gt.r_sk < 0.6
        m[thin[gt.near] & m] = False
        return m
    if kind == 'fp5':
        d = ndi.distance_transform_edt(~m, sampling=gt.sp)
        cand = np.argwhere((d > 5) & (d < 11))
        b = ball(2.0, gt.sp)
        for c in cand[RNG.choice(len(cand), size=5, replace=False)]:
            stamp(m, c, b, True)
        return m
    raise ValueError(kind)


def geodesic_from(gt, sources, cls_mask_nodes):
    sub = gt.G.subgraph(np.nonzero(cls_mask_nodes)[0])
    return nx.multi_source_dijkstra_path_length(sub, [s for s in sources if s in sub], weight='w')


def perturb_labels(gt, kind):
    lab = gt.lab.copy()
    sk = gt.lab_sk
    relabel_nodes = np.zeros(len(gt.pts), bool); new = None
    if kind in ('carina5', 'carina10'):
        # LCx skeleton nodes adjacent to LM/LAD = start of LCx
        lcx = sk == 3
        starts = [v for v in np.nonzero(lcx)[0] if any(sk[u] in (1, 2) for u in gt.G.neighbors(v))]
        if not starts:
            return None
        dist = geodesic_from(gt, starts, lcx)
        lim = 5.0 if kind == 'carina5' else 10.0
        for v, d in dist.items():
            if d <= lim:
                relabel_nodes[v] = True
        new = 2
    elif kind == 'lm_as_lad':
        relabel_nodes = sk == 1; new = 2
    elif kind == 'side_swap':
        lad = sk == 2
        sub = gt.G.subgraph(np.nonzero(lad)[0])
        starts = [v for v in np.nonzero(lad)[0] if any(sk[u] == 1 for u in gt.G.neighbors(v))]
        if not starts:
            return None
        # main LAD path = longest geodesic path from start; side subtrees = components after removing it
        dist = nx.single_source_dijkstra_path_length(sub, starts[0], weight='w')
        far = max(dist, key=dist.get)
        main = set(nx.dijkstra_path(sub, starts[0], far, weight='w'))
        rest = sub.subgraph([v for v in sub.nodes if v not in main])
        comps = sorted(nx.connected_components(rest), key=len, reverse=True)
        if not comps:
            return None
        relabel_nodes[list(comps[0])] = True; new = 3
    elif kind in ('d1_as_lcx', 'im_as_lad'):
        if gt.raw is None:
            return None
        src, new = (4, 3) if kind == 'd1_as_lcx' else (8, 2)
        if not (gt.raw == src).any():
            return None
        lab[gt.raw == src] = new
        return lab
    elif kind == 'islands':
        out = lab.copy()
        cand = np.nonzero(np.isin(sk, (2, 3, 4)))[0]
        for v in RNG.choice(cand, size=5, replace=False):
            c = sk[v]
            nl = {2: 3, 3: 2, 4: 2}[c]
            d = nx.single_source_dijkstra_path_length(gt.G, v, cutoff=1.5, weight='w')
            nodes = np.zeros(len(gt.pts), bool); nodes[list(d)] = True
            out[nodes[gt.near] & gt.m] = nl
        return out
    else:
        raise ValueError(kind)
    lab[relabel_nodes[gt.near] & gt.m] = new
    return lab


BIN = ['identity', 'erode1', 'dilate1', 'gaps5', 'gaps5_thick', 'drop_term30', 'thin_lost', 'fp5']
LAB = ['carina5', 'carina10', 'side_swap', 'd1_as_lcx', 'im_as_lad', 'lm_as_lad', 'islands']

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    with open(out, 'a') as f:
        for case in sys.argv[3:]:
            t = time.time()
            gt = GT(case, source=src)
            base = dict(case=case, src=src, nseg=len(gt.segs), nterm=len(gt.term), ncomp_gt=gt.ncomp,
                        lm_len=gt.info.get('lm_len_mm'), class_vox=np.bincount(gt.lab.ravel(), minlength=5)[1:].tolist())
            for k in BIN:
                p = gt.m.copy() if k == 'identity' else perturb_binary(gt, k)
                if p is None:
                    continue
                r = score(gt, p); r.update(base, kind=k)
                f.write(json.dumps(r) + '\n'); f.flush()
            for k in LAB:
                pl = perturb_labels(gt, k)
                if pl is None:
                    continue
                r = score(gt, gt.m, pl); r.update(base, kind=k)
                r['relabelled_vox'] = int((pl != gt.lab).sum())
                f.write(json.dumps(r) + '\n'); f.flush()
            print(case, 'done', round(time.time() - t), 's', flush=True)
