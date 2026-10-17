"""E9b: ostium rules applied per *tree component* (not per left/right side), so that cases with
separate LAD and LCx ostia (absent LM) get one ostium per tree.

Usage: python ostium_eval_cc.py <aorta_dir> <cl_dir> <out.jsonl> case [case ...]

Each reference lumen component >= 1000 voxels is a tree. Per tree: `thick` (thickest endpoint,
LM-labelled endpoints preferred) and `pool_thick` (thickest endpoint within 3 mm of the endpoint
nearest the blood pool), and, where a TotalSegmentator aorta exists, `aorta5` (endpoints within 5 mm).
Each true ImageCAS-X start point (left and right files pooled) is matched to the tree containing it
(nearest tree voxel); distance to that tree's chosen ostium is reported, and whether the two cheap
rules disagree by > 5 mm on that tree (the human-review flag).
"""
import glob
import json
import os
import sys

import cc3d
import networkx as nx
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import treelib as T  # noqa: E402
from ostium_eval import starts  # noqa: E402


def run(case, aorta_dir, cl_dir):
    icx_id = int(case[1:]) + 1
    img = nib.load(T.icx_path(case)); A = img.affine
    m, lab, raw, sp, lo, axc = T.load_icx(case, margin_mm=8.0)
    lo = np.array(lo)
    sl = tuple(slice(lo[k], lo[k] + m.shape[k]) for k in range(3))
    ct = np.asanyarray(nib.load(T.ct_path(case)).dataobj)[sl]
    pool = T.blood_pool(ct, sp, exclude=m)
    d_pool = ndi.distance_transform_edt(~pool, sampling=sp)
    apath = f'{aorta_dir}/{case}_aorta.nii.gz'
    d_ao = None
    if os.path.exists(apath):
        ao = (np.asanyarray(nib.load(apath).dataobj) > 0)[sl]
        d_ao = ndi.distance_transform_edt(~ao, sampling=sp)
    comps, n = cc3d.connected_components(m, connectivity=26, return_N=True)
    sizes = np.bincount(comps.ravel())
    skel = T.skeletonise(m)
    pts, G = T.skeleton_graph(skel, sp)
    rad = ndi.distance_transform_edt(m, sampling=sp)
    r_sk = rad[tuple(pts.T)]
    lsk = lab[tuple(pts.T)]
    csk = comps[tuple(pts.T)]
    deg = np.array([G.degree(i) for i in range(len(pts))])
    rmed = lambda u: np.median([r_sk[w] for w in nx.single_source_shortest_path_length(G, u, cutoff=20)])
    trees = {}
    for k in range(1, n + 1):
        if sizes[k] < 1000:
            continue
        ends = np.nonzero((csk == k) & (deg == 1))[0]
        if len(ends) == 0:
            continue
        cand = ends[lsk[ends] == 1] if np.any(lsk[ends] == 1) else ends
        t = dict(thick=pts[max(cand, key=rmed)])
        dp = d_pool[tuple(pts[ends].T)]
        pc = ends[dp <= dp.min() + 3.0]
        t['pool_thick'] = pts[max(pc, key=rmed)]
        if d_ao is not None:
            de = d_ao[tuple(pts[ends].T)]
            t['aorta5'] = pts[ends[de <= 5.0]] if (de <= 5.0).any() else pts[[ends[int(np.argmin(de))]]]
        trees[k] = t
    S = []
    for side in ('left', 'right'):
        for f in glob.glob(f'{cl_dir}/**/{icx_id}.coronary_{side}_centerline.vtk', recursive=True):
            S += list(starts(f))
    S = np.array(S)
    sv = (np.linalg.inv(A) @ np.c_[S, np.ones(len(S))].T).T[:, :3] - lo
    _, inds = ndi.distance_transform_edt(comps == 0, return_indices=True)
    res = dict(case=case, n_trees=len(trees), n_true=len(S), lm_present=bool((lab == 1).any()),
               has_ts=d_ao is not None, matches=[])
    for s in sv:
        si = np.clip(np.round(s).astype(int), 0, np.array(m.shape) - 1)
        k = int(comps[tuple(inds[:, si[0], si[1], si[2]])])
        if k not in trees:
            res['matches'].append(dict(tree=k, missing=True)); continue
        t = trees[k]
        d = {name: float(np.min(np.linalg.norm((np.atleast_2d(v) - s) * sp, axis=1))) for name, v in t.items()}
        d['tree'] = k
        d['rules_disagree'] = bool(np.linalg.norm((t['thick'] - t['pool_thick']) * sp) > 5.0)
        res['matches'].append(d)
    return res


if __name__ == '__main__':
    ad, cd, out = sys.argv[1:4]
    with open(out, 'a') as f:
        for c in sys.argv[4:]:
            try:
                r = run(c, ad, cd)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            f.write(json.dumps(r) + '\n'); f.flush()
            print(c, flush=True)
