"""E2+E7: calibre of the trees, and which metrics survive a change of lumen-boundary convention.

Usage: python convention_metrics.py <out.jsonl> case [case ...]

For each case with both references -- the project's original binary mask (ImageCAS label, which
the labelling team splits into 4 classes) and the ImageCAS-X lumen (expert re-annotation) -- on a
common crop:
  calibre (per reference): skeleton length (mm) by local lumen diameter, fraction of length in
     lumens < 3 / 4 / 6 in-plane voxels and < 1.5 / 2 mm, number of skeleton segments >= 3 mm
     (diameter = 2*EDT(centreline voxel) - in-plane spacing; EDT to nearest background voxel
     centre overestimates the boundary distance by half a voxel)
  agreement (orig vs ICX): Dice, NSD@0.5mm and @1.0mm, clDice, skeleton recall each way,
     component counts, segment detection each way (segments >= 3 mm, >= 50 % covered)
The point: two expert-ish references of the *same* vessels disagree on the boundary; a decisive
metric should measure what they agree on (which vessels, where) rather than the boundary.
"""
import json
import sys
import time

import cc3d
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import treelib as T  # noqa: E402
from perturb_metrics import dice, nsd  # noqa: E402

BINS = [0, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 99]


def calibre(m, sp):
    skel = T.skeletonise(m)
    pts, G = T.skeleton_graph(skel, sp)
    rad = ndi.distance_transform_edt(m, sampling=sp)
    diam = 2 * rad[tuple(pts.T)] - sp[0]
    nl = np.zeros(len(pts))
    for a, b, d in G.edges(data=True):
        nl[a] += d['w'] / 2; nl[b] += d['w'] / 2
    segs, deg = T.segments(G)
    segs3 = [s for s in segs if T.path_len(G, s) >= 3.0]
    L = nl.sum(); dv = diam / sp[0]
    out = dict(skel_len_mm=float(L), nseg3=len(segs3),
               nterm3=int(sum(deg[s[0]] == 1 or deg[s[-1]] == 1 for s in segs3)),
               len_by_diam_mm=np.histogram(diam, bins=BINS, weights=nl)[0].round(1).tolist(),
               frac_lt3vox=float(nl[dv < 3].sum() / L), frac_lt4vox=float(nl[dv < 4].sum() / L),
               frac_lt6vox=float(nl[dv < 6].sum() / L), frac_lt1_5mm=float(nl[diam < 1.5].sum() / L),
               frac_lt2mm=float(nl[diam < 2.0].sum() / L), median_diam_mm=float(np.median(diam)),
               ncomp=int(cc3d.connected_components(m, connectivity=26, return_N=True)[1]))
    return out, skel, pts, segs3


def run(case):
    a = nib.load(T.mask_path(case)); b = nib.load(T.icx_path(case))
    sp = np.array(a.header.get_zooms()[:3], float)
    mo = np.asanyarray(a.dataobj) > 0.5
    mi = np.asanyarray(b.dataobj) > 0
    u = mo | mi
    idx = [np.nonzero(u.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    sl = tuple(slice(max(x[0] - 4, 0), x[-1] + 5) for x in idx)
    mo = mo[sl].copy(); mi = mi[sl].copy(); del u
    co, so, po, sego = calibre(mo, sp)
    ci, si, pi, segi = calibre(mi, sp)
    r = dict(case=case, spacing=sp.tolist(), orig=co, icx=ci)
    r['dice'] = dice(mo, mi)
    r['nsd05'] = nsd(mo, mi, sp, 0.5); r['nsd10'] = nsd(mo, mi, sp, 1.0)
    # skeleton recall each way: fraction of A's centreline inside B's lumen
    r['icx_skel_in_orig'] = float(mo[si].mean()); r['orig_skel_in_icx'] = float(mi[so].mean())
    tp, ts = r['orig_skel_in_icx'], r['icx_skel_in_orig']  # orig as 'prediction', icx as reference
    r['cldice'] = 2 * tp * ts / (tp + ts) if tp + ts else 0.0
    insi = mo[tuple(pi.T)]
    r['icx_seg_found_in_orig'] = float(np.mean([insi[s].mean() >= 0.5 for s in segi])) if segi else None
    inso = mi[tuple(po.T)]
    r['orig_seg_found_in_icx'] = float(np.mean([inso[s].mean() >= 0.5 for s in sego])) if sego else None
    # tolerant skeleton recall: centreline within 1 mm of the other lumen
    do = ndi.distance_transform_edt(~mo, sampling=sp); di = ndi.distance_transform_edt(~mi, sampling=sp)
    r['icx_skel_within1mm_orig'] = float((do[si] <= 1.0).mean())
    r['orig_skel_within1mm_icx'] = float((di[so] <= 1.0).mean())
    return r


if __name__ == '__main__':
    out = sys.argv[1]
    with open(out, 'a') as f:
        for c in sys.argv[2:]:
            t = time.time()
            try:
                r = run(c)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            f.write(json.dumps(r) + '\n'); f.flush()
            print(c, round(time.time() - t), flush=True)
