"""E2: where does the coronary tree's length live?  Vessel calibre along the skeleton.

Usage: python tree_stats.py <orig|icx> <out.jsonl> case [case ...]
  orig: the project's binary mask (original ImageCAS label); 4-class split = geometric pseudo-labels
  icx : the ImageCAS-X lumen for the same case; 4-class split = ImageCAS-X segments (subtree convention)

For each GT binary mask: Lee skeleton, EDT radius (mm) at each skeleton voxel, skeleton
graph segments. Reports skeleton length (mm) by local diameter bin (in mm and in in-plane
voxels), terminal vs internal segments, number of segments >= 3 mm, and pseudo-label
(geometric LM/LAD/LCx/RCA) length and calibre. Lengths are graph-edge lengths in mm.
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import treelib as T  # noqa: E402

BINS_MM = [0, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 99]

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    with open(out, 'a') as f:
        for case in sys.argv[3:]:
            t = time.time()
            try:
                if src == 'icx':
                    m, lab, raw, sp, lo, axc = T.load_icx(case, margin_mm=3.0)
                    m = m.astype(np.uint8); info = {}
                else:
                    m, sp, lo, axc = T.load_crop(case, margin_mm=3.0)
                    lab, info = T.pseudo_labels(m, sp, axc)
                skel = T.skeletonise(m)
                pts, G = T.skeleton_graph(skel, sp)
                rad = T.radius_mm(m, sp)
                # EDT at a centreline voxel is the distance to the nearest *background voxel centre*,
                # which overestimates the radius to the boundary by half a voxel: a lumen k voxels wide
                # has centre EDT (k+1)/2 voxels. Calibre estimate = 2*EDT - in-plane spacing.
                r = rad[tuple(pts.T)] - 0.5 * sp[0]
                diam = 2 * r
                # per-node length = half the sum of incident edge lengths
                nl = np.zeros(len(pts))
                for a, b, d in G.edges(data=True):
                    nl[a] += d['w'] / 2; nl[b] += d['w'] / 2
                segs, deg = T.segments(G)
                seg_len = [T.path_len(G, s) for s in segs]
                term = [(deg[s[0]] == 1 or deg[s[-1]] == 1) for s in segs]
                seg_d = [float(np.median(diam[s])) for s in segs]
                L = nl.sum()
                hist = np.histogram(diam, bins=BINS_MM, weights=nl)[0]
                dvox = diam / sp[0]
                res = dict(case=case, src=src, spacing=sp.tolist(), skel_len_mm=float(L),
                           len_by_diam_mm=dict(zip([f'{a}-{b}' for a, b in zip(BINS_MM[:-1], BINS_MM[1:])],
                                                   hist.tolist())),
                           frac_len_diam_lt4vox=float(nl[dvox < 4].sum() / L),
                           frac_len_diam_lt3vox=float(nl[dvox < 3].sum() / L),
                           frac_len_diam_lt6vox=float(nl[dvox < 6].sum() / L),
                           frac_len_diam_lt1_5mm=float(nl[diam < 1.5].sum() / L),
                           frac_len_diam_lt2mm=float(nl[diam < 2.0].sum() / L),
                           nseg=len(segs), nseg3=int(sum(l >= 3 for l in seg_len)),
                           nterm3=int(sum(l >= 3 and t for l, t in zip(seg_len, term))),
                           term_median_diam=[d for d, l, t in zip(seg_d, seg_len, term) if t and l >= 3],
                           frac_len_terminal=float(sum(l for l, t in zip(seg_len, term) if t) / max(sum(seg_len), 1)),
                           info=info)
                lsk = lab[tuple(pts.T)]
                import cc3d
                res['ncomp'] = int(cc3d.connected_components(m > 0, connectivity=26, return_N=True)[1])
                res['class_len_mm'] = {int(c): float(nl[lsk == c].sum()) for c in (1, 2, 3, 4)}
                res['class_med_diam'] = {int(c): float(np.median(diam[lsk == c])) if (lsk == c).any() else None
                                         for c in (1, 2, 3, 4)}
                res['class_frac_lt4vox'] = {int(c): float(nl[(lsk == c) & (dvox < 4)].sum() / max(nl[lsk == c].sum(), 1e-9))
                                            for c in (1, 2, 3, 4)}
            except Exception as e:  # noqa
                res = dict(case=case, error=repr(e))
            f.write(json.dumps(res) + '\n'); f.flush()
            print(case, round(time.time() - t), flush=True)
