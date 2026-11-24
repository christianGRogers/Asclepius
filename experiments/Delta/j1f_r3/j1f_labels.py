"""Janus 1-F round 3 (Delta): the stage-1 label converter of record (F-A18), ImageCAS-X 14 classes -> 13 values.

  0 bg  1 LM  2 LAD  3 LCx  4 RCA  5 D1  6 D2  7 D3  8 OM1  9 OM2  10 Ramus  11 PDA  12 PLB  255 ignore

This is Delta's round-1 `j1f_labels.py` (`experiments/Delta/j1f_r1/`) with F-A18's two changes:
  * D47 Q1 (A) hard-wired: L-PDA -> PDA, L-PLA -> PLB. The `--left-pda` switch is gone.
  * F-A3's ignore rule: an "Other" piece touching neither the LAD side nor the LCx side (it touches only the RCA, or
    nothing) -> 255. Other "Other" pieces as round 1: >= 20 voxels and more LAD-side contact -> the first along the
    left tree (geodesic from the LM) is D3, later ones LAD; >= 20 voxels and more LCx-side contact -> LCx; otherwise
    (small, or tied) -> the nearest LAD/LCx voxel in mm (territory.py's rule).

Expected on the 620 (F-A18, F-A26): {'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}.
Self-test: python j1f_labels.py selftest
"""
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

IGNORE = 255
STRUCT = np.ones((3, 3, 3), bool)
MIN_PIECE_VOX = 20
# ImageCAS-X: 1 LM 2 LAD 3 LCx 4 D1 5 D2 6 OM1 7 OM2 8 IM 9 RCA 10 R-PDA 11 R-PLA 12 L-PDA 13 L-PLA 14 Other
DIRECT = {1: 1, 2: 2, 3: 3, 4: 5, 5: 6, 6: 8, 7: 9, 8: 10, 9: 4, 10: 11, 11: 12, 12: 11, 13: 12}
LAD_SIDE = (2, 4, 5)
LCX_SIDE = (3, 6, 7, 8, 12, 13)
LEFT = (1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14)
INFO_KEYS = ('d3', 'd4_to_lad', 'other_lcx', 'other_nearest', 'other_ignore')


def map13(icx, zooms):
    """(labels uint8, info) for one ImageCAS-X label volume."""
    icx = np.asarray(icx)
    z = np.asarray(zooms[:3], float)
    out = np.zeros(icx.shape, np.uint8)
    for k, v in DIRECT.items():
        out[icx == k] = v
    info = dict.fromkeys(INFO_KEYS, 0)
    o = icx == 14
    if not o.any():
        return out, info
    comp, nc = ndi.label(o, STRUCT)
    lad_pieces, near = [], np.zeros_like(o)
    for i in range(1, nc + 1):
        p = comp == i
        ring = ndi.binary_dilation(p, STRUCT, iterations=2) & ~p
        v = icx[ring]
        nl, ncx = int(np.isin(v, LAD_SIDE).sum()), int(np.isin(v, LCX_SIDE).sum())
        big = int(p.sum()) >= MIN_PIECE_VOX
        if big and nl > ncx:
            lad_pieces.append(p)
        elif big and ncx > nl:
            out[p] = 3
            info['other_lcx'] += 1
        elif nl + ncx > 0:
            near |= p
            info['other_nearest'] += 1
        else:
            out[p] = IGNORE
            info['other_ignore'] += 1
    if lad_pieces:
        from skimage.graph import MCP_Geometric
        left = np.isin(icx, LEFT)
        bb = ndi.find_objects(left.astype(np.uint8))[0]
        bb = tuple(slice(max(b.start - 1, 0), b.stop + 1) for b in bb)
        lc, labc = left[bb], icx[bb]
        src = np.argwhere(labc == 1) if (labc == 1).any() else np.argwhere(labc == 2)[:1]
        dist, _ = MCP_Geometric(np.where(lc, 1.0, np.inf), sampling=tuple(z)).find_costs([tuple(s) for s in src])
        att = [float(np.min(dist[p[bb]])) for p in lad_pieces]
        for r, j in enumerate(np.argsort(att, kind='stable')):
            out[lad_pieces[j]] = 7 if r == 0 else 2
        info['d3'] += 1
        info['d4_to_lad'] += len(lad_pieces) - 1
    if near.any():
        srcm = np.isin(out, (2, 3))
        if srcm.any():
            pts, op = np.argwhere(srcm), np.argwhere(near)
            _, ii = cKDTree(pts * z).query(op * z)
            out[tuple(op.T)] = out[tuple(pts[ii].T)]
    return out, info


def selftest():
    sp = (0.5, 0.5, 0.5)
    icx = np.zeros((40, 90, 90), np.uint8)
    icx[20, 10:14, 10] = 1; icx[20, 14:70, 10] = 2; icx[20, 25, 11:32] = 4; icx[20, 45, 11:32] = 5
    icx[20, 60, 11:32] = 14; icx[20, 66, 11:32] = 14            # two LAD-side Others: D3, then LAD
    icx[21:38, 13, 10] = 3; icx[37, 14:36, 10] = 12; icx[30, 13, 11:32] = 13
    icx[25:33, 12, 11:14] = 14                                  # Other touching the LCx -> LCx
    icx[5:15, 60, 60] = 9; icx[15, 60, 61:85] = 14              # Other touching only the RCA -> 255
    icx[2, 2, 2:30] = 14                                        # Other touching nothing -> 255
    icx[5:15, 70, 70] = 10; icx[5:15, 80, 80] = 11
    lab, info = map13(icx, sp)
    assert (lab[icx == 12] == 11).all() and (lab[icx == 13] == 12).all(), 'D47 (A): L-PDA/L-PLA keep their names'
    assert (lab[icx == 10] == 11).all() and (lab[icx == 11] == 12).all()
    assert (lab[20, 60, 11:32] == 7).all() and (lab[20, 66, 11:32] == 2).all(), 'first LAD-side Other is D3'
    assert (lab[25:33, 12, 11:14] == 3).all()
    assert (lab[15, 60, 61:85] == IGNORE).all() and (lab[2, 2, 2:30] == IGNORE).all()
    assert info == {'d3': 1, 'd4_to_lad': 1, 'other_lcx': 1, 'other_nearest': 0, 'other_ignore': 2}, info
    print('j1f_labels selftest ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
