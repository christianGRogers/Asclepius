"""ImageCAS-X's 14 classes -> the project's four (D25 = D1 territory + D1b ramus -> LCx), for prepare.py and
score.py. The same mapping as src/segqueue14/labels.py ICX14_TO_4; "Other" (14: D3/D4, OM3/OM4) takes the class of
the nearest LAD/LCx voxel (in mm), as segtrain.reads.icx_to_territory does. Copied here because the job venv has no
segtrain."""
import numpy as np
from scipy.spatial import cKDTree

# ImageCAS-X value -> class (D1 territory, D1b ramus -> LCx); 14 "Other" is resolved by nearest LAD/LCx below.
TERRITORY = np.zeros(15, np.uint8)
TERRITORY[[1]] = 1
TERRITORY[[2, 4, 5]] = 2
TERRITORY[[3, 6, 7, 8, 12, 13]] = 3
TERRITORY[[9, 10, 11]] = 4


def to_four(icx, zooms):
    out = TERRITORY[np.clip(icx, 0, 14)]
    other = icx == 14
    if other.any():
        src = np.isin(out, (2, 3))
        if src.any():
            sp = np.asarray(zooms[:3], float)
            sp_pts = np.argwhere(src)
            op = np.argwhere(other)
            _, i = cKDTree(sp_pts * sp).query(op * sp)
            out[tuple(op.T)] = out[tuple(sp_pts[i].T)]
    return out
