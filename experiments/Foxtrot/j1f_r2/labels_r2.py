"""Janus 1-F round 2 (Foxtrot): ImageCAS-X 14 classes -> 1-F stage-1 labels as ruled (F-A3, D47 Q1 = A).

  0 bg  1 LM  2 LAD  3 LCx  4 RCA  5 D1  6 D2  7 D3  8 OM1  9 OM2  10 Ramus  11 PDA  12 PLB  255 ignore

Delta v1's `j1f_labels.py` map (the plan of record) with the ruling's two changes:
  - L-PDA / L-PLA -> PDA / PLB (D47 Q1: keep the D44 name, collapse by the vessel left);
  - an "Other" piece touching no LAD-side and no LCx-side voxel (RCA only, or nothing) -> 255 (F-A3).
Every other "Other" rule is Delta's (first LAD-side piece by geodesic attachment -> D3, later -> LAD;
LCx-side -> LCx; small two-sided pieces -> nearest LAD/LCx voxel).
Also: `collapse4(lab13, spacing)` -- F-A4's origin collapse (D1-D3 -> LAD; OM1, OM2, Ramus -> LCx; each PDA/PLB
26-component -> the one of LCx/RCA it touches most, ties -> RCA). Reads training labels only.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.graph import MCP_Geometric

NAMES13 = ['bg', 'LM', 'LAD', 'LCx', 'RCA', 'D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
PARENT = {5: 2, 6: 2, 7: 2, 8: 3, 9: 3, 10: 3}          # PDA/PLB: by touch (collapse4)
LAD_SIDE, LCX_SIDE, LEFT = {2, 4, 5}, {3, 6, 7, 8, 12, 13}, {1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14}
S26 = np.ones((3, 3, 3), bool)
DIRECT = {1: 1, 2: 2, 3: 3, 4: 5, 5: 6, 6: 8, 7: 9, 8: 10, 9: 4, 10: 11, 11: 12, 12: 11, 13: 12}


def crop(lab, margin=40):
    sl = ndi.find_objects((lab > 0).astype(np.uint8))[0]
    return tuple(slice(max(s.start - margin, 0), min(s.stop + margin, n)) for s, n in zip(sl, lab.shape))


def map13(lab, z):
    out = np.zeros(lab.shape, np.uint8)
    for k, v in DIRECT.items():
        out[lab == k] = v
    info = {'d3': 0, 'd4_to_lad': 0, 'other_lcx': 0, 'other_nearest': 0, 'other_ignore': 0}
    o = lab == 14
    if not o.any():
        return out, info
    comp, nc = ndi.label(o, S26)
    lad_pieces, rest = [], []
    for i in range(1, nc + 1):
        p = comp == i
        ring = ndi.binary_dilation(p, S26, iterations=2) & ~p
        v = lab[ring]
        nl, ncx = int(np.isin(v, list(LAD_SIDE)).sum()), int(np.isin(v, list(LCX_SIDE)).sum())
        if nl == 0 and ncx == 0:
            out[p] = 255; info['other_ignore'] += 1
        elif p.sum() >= 20 and nl > ncx:
            lad_pieces.append(p)
        elif p.sum() >= 20 and ncx > nl:
            out[p] = 3; info['other_lcx'] += 1
        else:
            rest.append(p)
    if lad_pieces:
        left = np.isin(lab, list(LEFT))
        src = np.argwhere(lab == 1) if (lab == 1).any() else np.argwhere(lab == 2)[:1]
        dist, _ = MCP_Geometric(np.where(left, 1.0, np.inf), sampling=tuple(z)).find_costs([tuple(s) for s in src])
        att = [float(np.min(dist[p])) for p in lad_pieces]
        for r, j in enumerate(np.argsort(att)):
            out[lad_pieces[j]] = 7 if r == 0 else 2
        info['d3'] += 1; info['d4_to_lad'] += len(lad_pieces) - 1
    if rest:
        m = np.zeros_like(o)
        for p in rest:
            m |= p
        srcm = np.isin(out, [2, 3])
        sp_pts, op = np.argwhere(srcm), np.argwhere(m)
        _, i = cKDTree(sp_pts * z).query(op * z)
        out[tuple(op.T)] = out[tuple(sp_pts[i].T)]
        info['other_nearest'] += len(rest)
    return out, info


def pda_plb_side(lab13):
    """{component id: (class, 'LCx'|'RCA')} for every PDA/PLB 26-component, by voxels touched."""
    res = {}
    for c in (11, 12):
        comp, n = ndi.label(lab13 == c, S26)
        for i in range(1, n + 1):
            p = comp == i
            ring = ndi.binary_dilation(p, S26, iterations=2) & ~p
            v = lab13[ring]
            nl = int(np.isin(v, [3, 8, 9, 10]).sum()); nr = int((v == 4).sum())
            res[(c, i)] = 'LCx' if nl > nr else 'RCA'
    return res


def collapse4(lab13):
    """F-A4 / D47 Q1: origin collapse to 0..4 (255 kept)."""
    out = np.zeros(lab13.shape, np.uint8)
    for k, v in {1: 1, 2: 2, 3: 3, 4: 4, 5: 2, 6: 2, 7: 2, 8: 3, 9: 3, 10: 3}.items():
        out[lab13 == k] = v
    out[lab13 == 255] = 255
    for c in (11, 12):
        comp, n = ndi.label(lab13 == c, S26)
        for i in range(1, n + 1):
            p = comp == i
            ring = ndi.binary_dilation(p, S26, iterations=2) & ~p
            v = lab13[ring]
            nl = int(np.isin(v, [3, 8, 9, 10]).sum()); nr = int((v == 4).sum())
            out[p] = 3 if nl > nr else 4
    return out
