"""Round 6 (Q2): reference-side attributes per case and class, to explain where tree-F1 is lost.

No predictions exist on CPU (they stay on Trillium $SCRATCH), so the per-class scores come from the
round-5 GPU results and this script measures what each reference tree is like:

  geometry    voxels, centreline length (mm), median radius, fraction of centreline thinner than
              1.0 / 0.75 mm radius (the distal calibre nnU-Net loses first)
  field of view  distance of the class's voxels to each face of the scan, fraction of its
              centreline within 5 mm of a face (truncation), which face
  dominance   from the ImageCAS-X 14-class labels: R-PDA/R-PLA (right) vs L-PDA/L-PLA (left)
  convention  ImageCAS-X class voxels > 1 mm outside the ImageCAS mask (vessel the reference lacks)
              and mask voxels > 2 mm from any ImageCAS-X voxel (named only by geodesic growth)
  ostium      segtrain.tf1 thick-only ostia (= the RefTree / R1 provisional roots) vs the expert
              start points; components (is the RCA joined to the left tree? split in pieces?)

Reference = Atlas's proxy (trillium/atlas/lib/proxy.make_label), the one every R1 number used.
Usage: python r6_attrs.py <out.jsonl> case [case ...]"""
import json
import os
import sys

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import r5_cut_anatomy as M  # noqa: E402
from segtrain import tf1 as S  # noqa: E402

FACES = ('x0', 'x1', 'y0', 'y1', 'z0', 'z1')


def run(case):
    icx_id = int(case[1:]) + 1
    mpath = f'{M.SCR}/data/masks/{case}.nii.gz'
    ipath = M.T.icx_path(case)
    lab_full, A, stats = M.AP.make_label(mpath, ipath)
    img = nib.load(mpath)
    sp = np.array(img.header.get_zooms()[:3], float)
    shape = np.array(lab_full.shape)
    raw_full = np.asanyarray(nib.load(ipath).dataobj).astype(np.uint8)
    mask_full = np.asanyarray(img.dataobj) > 0.5
    idx = np.nonzero((lab_full > 0) | (raw_full > 0))
    mg = np.ceil(6.0 / sp).astype(int)
    lo = np.maximum([i.min() for i in idx] - mg, 0)
    hi = np.minimum([i.max() + 1 for i in idx] + mg, shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    R, raw, mk = lab_full[sl].copy(), raw_full[sl].copy(), mask_full[sl].copy()
    del lab_full, raw_full, mask_full
    Rm = R > 0
    cl = S._Centreline(Rm, sp)
    lsk = R[tuple(cl.pts.T)]
    gpts = cl.pts + lo                                   # centreline in full-grid voxels
    face_mm = np.stack([gpts[:, 0], shape[0] - 1 - gpts[:, 0], gpts[:, 1], shape[1] - 1 - gpts[:, 1],
                        gpts[:, 2], shape[2] - 1 - gpts[:, 2]], 1) * np.repeat(sp, 2)[None]
    comps, n = S.components(Rm)
    csk = comps[tuple(cl.pts.T)]
    lut = np.zeros(256, np.uint8)
    for k, v in M.T.ICX_TO_4.items():
        lut[k] = v
    icx4 = lut[raw]
    icx_any = raw > 0
    d_mask = ndi.distance_transform_edt(~mk, sampling=sp)
    d_icx = ndi.distance_transform_edt(~icx_any, sampling=sp)
    step = float(np.mean(sp))
    out = dict(case=case, shape=shape.tolist(), sp=sp.round(4).tolist(), ref_components=int(n),
               dominance=('co' if np.isin(raw, (10, 11)).any() and np.isin(raw, (12, 13)).any() else
                          'right' if np.isin(raw, (10, 11)).any() else
                          'left' if np.isin(raw, (12, 13)).any() else 'unknown'),
               classes={})
    for c in (1, 2, 3, 4):
        on = lsk == c
        cv = R == c
        if not cv.any():
            continue
        r = cl.radius[on]
        fm = face_mm[on]
        comp_ids = set(csk[on].tolist())
        rc = dict(vox=int(cv.sum()), length_mm=round(float(on.sum() * step), 1),
                  median_r=round(float(np.median(r)), 3) if on.any() else None,
                  thin100=round(float((r < 1.0).mean()), 3) if on.any() else None,
                  thin075=round(float((r < 0.75).mean()), 3) if on.any() else None,
                  min_face_mm=round(float(fm.min()), 1) if on.any() else None,
                  min_face=FACES[int(np.argmin(fm.min(0)))] if on.any() else None,
                  near_face5=round(float((fm.min(1) <= 5.0).mean()), 3) if on.any() else None,
                  n_comp=len(comp_ids),
                  icx_outside_mask=round(float(((icx4 == c) & (d_mask > 1.0)).sum() / max((icx4 == c).sum(), 1)), 3),
                  mask_unnamed=round(float((cv & (d_icx > 2.0)).sum() / cv.sum()), 3))
        out['classes'][str(c)] = rc
    left = set(csk[np.isin(lsk, (1, 2, 3))].tolist())
    right = set(csk[lsk == 4].tolist())
    out['rca_joined_left'] = bool(left & right)
    # ostia: thick-only per component (the R1/RefTree provisional rule) vs expert start points
    rep = S.find_ostia(R, sp, _centreline=cl)
    true = {}
    for side in ('left', 'right'):
        for d in M.CL_DIRS:
            p = f'{d}/{icx_id}.coronary_{side}_centerline.vtk'
            if os.path.exists(p):
                P = np.array(M.starts(p))
                true[side] = (np.linalg.inv(A) @ np.c_[P, np.ones(len(P))].T).T[:, :3] - lo
                break
    ost = []
    for o in rep.ostia:
        c = int(R[o.point])
        side = 'right' if c == 4 else 'left'
        P = true.get(side)
        d = float(np.min(np.linalg.norm((P - np.array(o.point)) * sp, axis=1))) if P is not None else None
        ost.append(dict(side=side, cls=c, d_true_mm=None if d is None else round(d, 2)))
    out['ostia_thick'] = ost
    out['has_truth'] = sorted(true)
    out['proxy'] = {k: stats.get(k) for k in ('near_frac', 'geodesic_frac', 'unreached_frac')}
    return out


if __name__ == '__main__':
    with open(sys.argv[1], 'a') as f:
        for c in sys.argv[2:]:
            try:
                r = run(c)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            f.write(json.dumps(r) + '\n')
            f.flush()
            print(c, r.get('error', ''), flush=True)
