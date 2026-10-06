"""Projected 4-class proxy labels in the project's binding convention (Human decisions D0, D1, D1b): the ORIGINAL
ImageCAS mask split into LM/LAD/LCx/RCA, territory rule, ramus -> LCx. Names come from ImageCAS-X (expert
per-segment labels on the same grid): each mask voxel takes the class of the nearest ImageCAS-X voxel within 2 mm;
the remaining mask voxels inherit a class by geodesic growth inside the mask; unreachable specks stay background.
Same recipe as Atlas's plan §2.1 / Bridge's extract.py projection.
Usage (module): make_label(mask_path, icx_path) -> (uint8 label, affine, stats)"""
import numpy as np, nibabel as nib
from scipy import ndimage as ndi

# ImageCAS-X 14 classes -> project 4 classes (D1 territory, D1b ramus -> LCx)
#  1 LM 2 LAD 3 LCx 4 D1 5 D2 6 OM1 7 OM2 8 IM 9 RCA 10 R-PDA 11 R-PLA 12 L-PDA 13 L-PLA 14 Other(D3/D4/OM3/OM4)
MAP = np.zeros(256, np.uint8)
for k, v in {1: 1, 2: 2, 4: 2, 5: 2, 3: 3, 6: 3, 7: 3, 8: 3, 12: 3, 13: 3, 9: 4, 10: 4, 11: 4}.items():
    MAP[k] = v
# 14 'Other' (D3/D4/OM3/OM4) has no fixed parent: it is left to the geodesic step (inherits from the vessel it hangs off)

def make_label(mask_path, icx_path, near_mm=2.0, max_iter=600):
    mi = nib.load(mask_path); li = nib.load(icx_path)
    if mi.shape[:3] != li.shape[:3] or not np.allclose(mi.affine, li.affine, atol=1e-2):
        raise ValueError(f'grid mismatch {mask_path} vs {icx_path}')
    sp = np.array(mi.header.get_zooms()[:3], float)
    m = np.asarray(mi.dataobj) > 0.5
    L = np.asarray(li.dataobj).astype(np.uint8)
    out = np.zeros(m.shape, np.uint8)
    stats = dict(mask_vox=int(m.sum()), icx_vox=int((L > 0).sum()))
    if not m.any() or not (L > 0).any():
        stats['empty'] = True
        return out, mi.affine, stats
    idx = np.nonzero(m | (L > 0))
    lo = np.maximum([i.min() - 3 for i in idx], 0); hi = np.minimum([i.max() + 4 for i in idx], m.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    mc, Lc = m[sl], MAP[L[sl]]
    named = Lc > 0
    d, inds = ndi.distance_transform_edt(~named, sampling=sp, return_indices=True)
    near = mc & (d <= near_mm)
    lab = np.zeros(mc.shape, np.uint8)
    lab[near] = Lc[tuple(ind[near] for ind in inds)]
    del d, inds
    stats['near_frac'] = float(near.sum() / mc.sum())
    todo = mc & (lab == 0); it = 0
    st = np.ones((3, 3, 3), bool)
    while todo.any() and it < max_iter:
        grown = ndi.grey_dilation(lab, footprint=st)
        new = todo & (grown > 0)
        if not new.any():
            break
        lab[new] = grown[new]; todo &= ~new; it += 1
    stats['geodesic_frac'] = float(((lab > 0) & ~near & mc).sum() / mc.sum())
    stats['unreached_frac'] = float(todo.sum() / mc.sum())
    stats['class_vox'] = {c: int((lab == c).sum()) for c in range(1, 5)}
    out[sl] = lab * mc
    return out, mi.affine, stats
