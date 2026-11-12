"""Janus 1-F round 1 (Delta): is ImageCAS-X's branch numbering ordinal along the parent, and can D3 be recovered
from "Other"?

For each non-sealed case, on the left tree (LM, LAD, LCx, D1, D2, OM1, OM2, IM, L-PDA, L-PLA, Other) it computes the
geodesic distance (mm, inside the left-tree mask) from the LM (or, without LM, from the LAD/LCx voxel nearest the
other main vessel) to each branch piece's attachment point (the piece's geodesically nearest voxel). It reports:
  - D1 attaches before D2 (LAD side), OM1 before OM2 (LCx side);
  - every LAD-side "Other" piece (>= 20 voxels, touching LAD/D1/D2 more than the LCx side) attaches after D2;
  - per case: the LAD-side Other pieces in proximal-to-distal order with their attachment distance, so the
    proximal one is the candidate D3 (D44 has no D4: a further piece goes to LAD by territory, D1).
Labels only. Sealed cases are never opened.

Usage: python ordinal.py <icx_dir> <census.json> <out.json>
"""
import json, os, sys
from multiprocessing import Pool

import nibabel as nb
import numpy as np
from scipy import ndimage as ndi
from skimage.graph import MCP_Geometric

from census import SEALED, cid, LAD_SIDE, LCX_SIDE

LEFT = [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14]
STRUCT = np.ones((3, 3, 3), bool)
ICX = None


def attach(dist, piece):
    d = dist[piece]
    d = d[np.isfinite(d)]
    return round(float(d.min()), 1) if d.size else None


def one(c):
    n = int(c[1:]) + 1
    assert c not in SEALED
    im = nb.load(os.path.join(ICX, f'{n}.coronary.nii.gz'))
    lab = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    left = np.isin(lab, LEFT)
    if not left.any():
        return {'case': c, 'error': 'no left tree'}
    sl = ndi.find_objects(left.astype(np.uint8))[0]
    sl = tuple(slice(max(s.start - 1, 0), s.stop + 1) for s in sl)
    L, M = lab[sl], left[sl]
    if (L == 1).any():
        src = np.argwhere(L == 1)
    else:  # no LM: seed the LAD and the LCx at their most proximal (closest to each other) voxels
        a, b = np.argwhere(L == 2), np.argwhere(L == 3)
        if not len(a) or not len(b):
            return {'case': c, 'error': 'no LM and no LAD/LCx'}
        da = ndi.distance_transform_edt(L != 3, sampling=z)
        db = ndi.distance_transform_edt(L != 2, sampling=z)
        src = np.array([a[np.argmin(da[tuple(a.T)])], b[np.argmin(db[tuple(b.T)])]])
    cost = np.where(M, 1.0, np.inf)
    mcp = MCP_Geometric(cost, sampling=tuple(z))
    dist, _ = mcp.find_costs([tuple(p) for p in src])
    out = {'case': c}
    for k, nm in ((4, 'D1'), (5, 'D2'), (6, 'OM1'), (7, 'OM2'), (8, 'IM')):
        m = L == k
        if m.sum() >= 20:
            comp, nc = ndi.label(m, STRUCT)
            sizes = ndi.sum(m, comp, range(1, nc + 1))
            out[nm] = attach(dist, comp == (int(np.argmax(sizes)) + 1))
    o = L == 14
    lad_side, lcx_side = [], []
    if o.any():
        comp, nc = ndi.label(o, STRUCT)
        for i in range(1, nc + 1):
            p = comp == i
            if p.sum() < 20:
                continue
            ring = ndi.binary_dilation(p, STRUCT, iterations=2) & ~p
            v = L[ring]
            nl, ncx = int(np.isin(v, list(LAD_SIDE)).sum()), int(np.isin(v, list(LCX_SIDE)).sum())
            rec = {'attach_mm': attach(dist, p), 'voxels': int(p.sum())}
            (lad_side if nl > ncx else lcx_side if ncx > nl else []).append(rec)
    out['other_lad'] = sorted(lad_side, key=lambda r: (r['attach_mm'] is None, r['attach_mm']))
    out['other_lcx'] = sorted(lcx_side, key=lambda r: (r['attach_mm'] is None, r['attach_mm']))
    return out


def main(icx, census_json, out):
    global ICX
    ICX = icx
    cen = json.load(open(census_json))
    cases = [r['case'] for r in cen['rows']]
    with Pool(4) as p:
        rows = p.map(one, cases, chunksize=4)
    grp = {r['case']: r['group'] for r in cen['rows']}
    for r in rows:
        r['group'] = grp[r['case']]
    json.dump(rows, open(out, 'w'), indent=0)
    print(len(rows), 'cases ->', out)


if __name__ == '__main__':
    main(*sys.argv[1:4])
