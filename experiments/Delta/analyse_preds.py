"""E8 analysis: what do a real nnU-Net's errors look like topologically, and does hysteresis
gap-bridging (a post-processing step that needs only the probability map) repair them?

Usage: python analyse_preds.py <pred_dir> <out.jsonl> case [case ...]

Reference: ImageCAS-X lumen (+ its segment labels, 4-class subtree convention, for per-class
breakdown) on the same crop the prediction was made on.
Post-processing variants (all followed by removal of components < 100 voxels, ImageCAS-X's rule):
  t50      : threshold 0.5 (ImageCAS-X's protocol)
  hyst20   : hysteresis -- voxels >= 0.2 kept if 26-connected to a voxel >= 0.5
  hyst10   : same with low threshold 0.1
  t30      : plain threshold 0.3 (to separate 'bridging' from 'just a lower threshold')
Metrics as in perturb_metrics.score (binary part) + per-class centreline recall and rooted
recall, + a description of every missed stretch of the reference centreline: interior gap
(both ends covered) vs distal truncation, length (mm), local reference diameter, and the max
foreground probability along it.
"""
import json
import sys

import cc3d
import networkx as nx
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import perturb_metrics as P  # noqa: E402
import treelib as T  # noqa: E402


def remove_small(m, k=100):
    lab = cc3d.connected_components(m, connectivity=26)
    sz = np.bincount(lab.ravel()); keep = sz >= k; keep[0] = False
    return keep[lab]


def hysteresis(prob, lo, hi):
    low = prob >= lo
    lab = cc3d.connected_components(low, connectivity=26)
    seeds = np.unique(lab[(prob >= hi) & low]); seeds = seeds[seeds > 0]
    return np.isin(lab, seeds)


class CropGT(P.GT):
    """GT on the prediction's crop grid."""

    def __init__(self, case, lo, hi):
        p = T.icx_path(case)
        img = nib.load(p)
        sp = np.array(img.header.get_zooms()[:3], float)
        raw = np.asanyarray(img.dataobj)[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]].astype(np.uint8)
        lut = np.zeros(256, np.uint8)
        for k, v in T.ICX_TO_4.items():
            lut[k] = v
        lab = lut[raw]; m = raw > 0
        rest = m & (lab == 0)
        if rest.any():
            _, inds = ndi.distance_transform_edt(lab == 0, sampling=sp, return_indices=True)
            lab[rest] = lab[tuple(inds)][rest]
        self.m, self.lab, self.raw, self.sp, self.info = m, lab, raw, sp, {}
        self._finish()


def _finish(self):
    # the part of P.GT.__init__ after loading (copied logic)
    self.skel = T.skeletonise(self.m)
    self.pts, self.G = T.skeleton_graph(self.skel, self.sp)
    self.rad = T.radius_mm(self.m, self.sp)
    self.r_sk = self.rad[tuple(self.pts.T)]
    segs, deg = T.segments(self.G)
    self.deg = deg
    self.segs = [s for s in segs if T.path_len(self.G, s) >= 3.0]
    self.term = [s for s in self.segs if deg[s[0]] == 1 or deg[s[-1]] == 1]
    self.ncomp = cc3d.connected_components(self.m, connectivity=26, return_N=True)[1]
    self.roots = []
    lsk = self.lab[tuple(self.pts.T)]
    dg = np.array([self.G.degree(i) for i in range(len(self.pts))])
    for cls_set in ((1,), (1, 2, 3), (4,)):
        if cls_set == (1, 2, 3) and self.roots:
            continue
        cand = np.nonzero(np.isin(lsk, cls_set) & (dg == 1))[0]
        if len(cand) == 0:
            continue
        best = max(cand, key=lambda v: np.median([self.r_sk[u] for u in
                                                  nx.single_source_shortest_path_length(self.G, v, cutoff=20)]))
        self.roots.append(tuple(self.pts[best]))
    self.ncomp_c = {c: cc3d.connected_components(self.lab == c, connectivity=26, return_N=True)[1]
                    for c in (1, 2, 3, 4)}
    self.lab_sk = lsk


CropGT._finish = _finish


def missed_stretches(gt, pred, prob):
    """Connected runs of reference-centreline voxels not inside pred."""
    inside = pred[tuple(gt.pts.T)]
    miss = np.nonzero(~inside)[0]
    sub = gt.G.subgraph(miss)
    out = []
    diam = 2 * gt.r_sk - gt.sp[0]
    pr = prob[tuple(gt.pts.T)].astype(np.float32)
    for comp in nx.connected_components(sub):
        comp = list(comp)
        # boundary: neighbours of the run that are covered
        nb = {u for v in comp for u in gt.G.neighbors(v) if inside[u]}
        is_end = any(gt.G.degree(v) == 1 for v in comp)
        length = sum(d['w'] for a, b, d in gt.G.subgraph(comp).edges(data=True)) + 0.35
        out.append(dict(n=len(comp), len_mm=float(length), interior=bool(len(nb) >= 2 and not is_end),
                        touches_end=bool(is_end), med_diam_mm=float(np.median(diam[comp])),
                        max_prob=float(pr[comp].max()), med_prob=float(np.median(pr[comp])),
                        cls=int(np.bincount(gt.lab_sk[comp], minlength=5).argmax())))
    return out


if __name__ == '__main__':
    pdir, out = sys.argv[1], sys.argv[2]
    with open(out, 'a') as f:
        for case in sys.argv[3:]:
            meta = json.load(open(f'{pdir}/{case}_meta.json'))
            prob = np.load(f'{pdir}/{case}_prob.npy').astype(np.float32)
            gt = CropGT(case, meta['lo'], meta['hi'])
            variants = {
                't50': remove_small(prob >= 0.5),
                't30': remove_small(prob >= 0.3),
                'hyst20': remove_small(hysteresis(prob, 0.2, 0.5)),
                'hyst10': remove_small(hysteresis(prob, 0.1, 0.5)),
            }
            for k, pred in variants.items():
                r = P.score(gt, pred)
                inside = pred[tuple(gt.pts.T)]
                pl = cc3d.connected_components(pred, connectivity=26)
                rc = {pl[rt] for rt in gt.roots if pl[rt] > 0}
                rooted = np.isin(pl[tuple(gt.pts.T)], list(rc))
                r['class_skel_recall'] = {int(c): float(inside[gt.lab_sk == c].mean()) for c in (1, 2, 3, 4)
                                          if (gt.lab_sk == c).any()}
                r['class_rooted_recall'] = {int(c): float(rooted[gt.lab_sk == c].mean()) for c in (1, 2, 3, 4)
                                            if (gt.lab_sk == c).any()}
                r['missed'] = missed_stretches(gt, pred, prob)
                r.update(case=case, variant=k, ncomp_gt=gt.ncomp, nroots=len(gt.roots),
                         pred_vox=int(pred.sum()), gt_vox=int(gt.m.sum()))
                for x in ('dice_per_class', 'tf1_per_class'):
                    r.pop(x, None)
                f.write(json.dumps(r) + '\n'); f.flush()
            print(case, 'done', flush=True)
