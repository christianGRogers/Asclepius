"""E9: does the aorta-contact ostium rule (judge's condition for tree-F1) find the true ostia?

Usage: python ostium_eval.py <aorta_dir> <cl_dir> <out.jsonl> case [case ...]

Truth: ImageCAS-X centreline start points (`start_points` attribute of
<id>.coronary_{left,right}_centerline.vtk, LPS world mm; ImageCAS-X defines them as degree-1
centreline vertices within 5 mm of a TotalSegmentator aorta, then reviewed).
Candidates, computed on the ImageCAS-X reference lumen (this is the ostium tree-F1 will use):
  pool_nearest / pool2 : per tree the endpoint nearest to (all endpoints within 2 mm of) the large
           contrast blood pools (treelib.blood_pool: CT > 200 HU, 3 mm opening, >= 2 cm^3) -- a
           memory-cheap stand-in for the aorta (TotalSegmentator needed ~7 GB RSS here)
  thick  : v1 heuristic -- per tree (left = classes LM/LAD/LCx, right = RCA) the skeleton endpoint
           with the largest median radius over ~20 neighbouring centreline voxels (LM end preferred)
  aorta  : per tree, every skeleton endpoint within 5 mm of the TotalSegmentator (fast, 3 mm)
           aorta mask; the closest one is the ostium (all within 5 mm are kept as extra ostia)
Reports the distance (mm) from each true start point to the nearest candidate of its tree.
"""
import glob
import json
import sys

import networkx as nx
import nibabel as nib
import numpy as np
import vtk
from scipy import ndimage as ndi
from vtk.util.numpy_support import vtk_to_numpy as v2n

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import treelib as T  # noqa: E402


def starts(path):
    r = vtk.vtkPolyDataReader(); r.SetFileName(path); r.Update(); p = r.GetOutput()
    P = v2n(p.GetPoints().GetData()).astype(float)
    s = v2n(p.GetPointData().GetArray('start_points'))
    return P[s > 0] * np.array([-1, -1, 1])  # LPS -> RAS (nibabel world)


def run(case, aorta_dir, cl_dir):
    icx_id = int(case[1:]) + 1
    img = nib.load(T.icx_path(case)); A = img.affine
    sp = np.array(img.header.get_zooms()[:3], float)
    m_full, lab_full, raw, sp, lo, axc = T.load_icx(case, margin_mm=8.0)
    lo = np.array(lo)
    sl = tuple(slice(lo[k], lo[k] + m_full.shape[k]) for k in range(3))
    import os
    apath = f'{aorta_dir}/{case}_aorta.nii.gz'
    ao = (np.asanyarray(nib.load(apath).dataobj) > 0)[sl] if os.path.exists(apath) else None
    d_ao = ndi.distance_transform_edt(~ao, sampling=sp) if ao is not None and ao.any() else None
    ct = np.asanyarray(nib.load(T.ct_path(case)).dataobj)[sl]
    pool = T.blood_pool(ct, sp, exclude=m_full)
    d_pool = ndi.distance_transform_edt(~pool, sampling=sp)
    skel = T.skeletonise(m_full)
    pts, G = T.skeleton_graph(skel, sp)
    rad = ndi.distance_transform_edt(m_full, sampling=sp)
    r_sk = rad[tuple(pts.T)]
    lsk = lab_full[tuple(pts.T)]
    deg = np.array([G.degree(i) for i in range(len(pts))])
    out = dict(case=case, has_ts_aorta=d_ao is not None)
    Ainv = np.linalg.inv(A)
    for side, cls in (('left', (1, 2, 3)), ('right', (4,))):
        f = glob.glob(f'{cl_dir}/**/{icx_id}.coronary_{side}_centerline.vtk', recursive=True)
        if not f:
            continue
        S = starts(f[0])
        sv = (Ainv @ np.c_[S, np.ones(len(S))].T).T[:, :3] - lo  # crop voxel coords
        ends = np.nonzero(np.isin(lsk, cls) & (deg == 1))[0]
        if len(ends) == 0:
            continue
        # thick heuristic (LM preferred on the left)
        cand = ends
        if side == 'left' and np.any(lsk[ends] == 1):
            cand = ends[lsk[ends] == 1]
        thick = max(cand, key=lambda u: np.median([r_sk[w] for w in
                                                   nx.single_source_shortest_path_length(G, u, cutoff=20)]))
        res = dict(n_true=len(S), n_ends=int(len(ends)))
        cands = [('thick', [thick])]
        dp = d_pool[tuple(pts[ends].T)]
        cands += [('pool_nearest', [ends[int(np.argmin(dp))]]), ('pool2', list(ends[dp <= 2.0]))]
        res['n_pool2_ends'] = int((dp <= 2.0).sum())
        if d_ao is not None:
            de = d_ao[tuple(pts[ends].T)]
            cands += [('aorta5', list(ends[de <= 5.0])), ('aorta_nearest', [ends[int(np.argmin(de))]])]
            res['n_aorta5_ends'] = int((de <= 5.0).sum())
        for name, cs in cands:
            if not cs:
                res[name] = None; continue
            cp = pts[cs] * sp
            dd = [float(np.min(np.linalg.norm(cp - s * sp, axis=1))) for s in sv]
            res[name] = dd
        out[side] = res
    return out


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
