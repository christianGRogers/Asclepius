"""Janus 1-F round 1 (Delta): ImageCAS-X's 14 classes -> Janus 1-F stage-1 labels (13 values, 0-12).

  0 background   1 LM   2 LAD   3 LCx   4 RCA   5 D1   6 D2   7 D3   8 OM1   9 OM2   10 Ramus   11 PDA   12 PLB

| ImageCAS-X | 1-F stage 1 |
|---|---|
| LM, LAD, LCx, RCA, D1, D2, OM1, OM2 | the same |
| IM | Ramus |
| R-PDA, R-PLA | PDA, PLB |
| L-PDA, L-PLA | LCx (default, `--left-pda lcx`: D25's territory, so the four-class collapse is Janus 0's) or PDA/PLB (`--left-pda name`); the lead's question |
| Other, LAD side | the piece that attaches first along the left tree (geodesic, from the LM) -> D3; any further LAD-side piece -> LAD (D44 has no D4) |
| Other, LCx side | LCx (D44 has no OM3/OM4) |
| Other, unassigned (touches neither side more) | the nearest LAD/LCx class, as icx4's territory.py |

Stage 2's classes (S1-S3, SN, Conus, RMA) are not in ImageCAS-X: its protocol did not trace septal perforators, acute
marginals or nodal arteries (arXiv:2608.30404, Supplementary B), so they are background there.

The four-class collapse of the result is checked against `trillium/icx4/lib/territory.py` (D25) for every case.

Usage: python j1f_labels.py <icx_dir> <census.json> <out.json> [--left-pda lcx|name]
       (writes per-case stage-1 class counts and the collapse check; no label files are written here)
"""
import json, os, sys
from multiprocessing import Pool

import nibabel as nb
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../trillium/icx4/lib'))
import territory  # noqa: E402  (D25's collapse, icx4's own code)
from census import SEALED, LAD_SIDE, LCX_SIDE  # noqa: E402
from ordinal import LEFT  # noqa: E402
from skimage.graph import MCP_Geometric  # noqa: E402

STAGE1 = ['background', 'LM', 'LAD', 'LCx', 'RCA', 'D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
TO4 = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 2, 6: 2, 7: 2, 8: 3, 9: 3, 10: 3, 11: 4, 12: 4}
STRUCT = np.ones((3, 3, 3), bool)


def map_case(lab, z, left_pda='lcx'):
    out = np.zeros_like(lab)
    direct = {1: 1, 2: 2, 3: 3, 4: 5, 5: 6, 6: 8, 7: 9, 8: 10, 9: 4, 10: 11, 11: 12}
    for k, v in direct.items():
        out[lab == k] = v
    out[lab == 12] = 3 if left_pda == 'lcx' else 11
    out[lab == 13] = 3 if left_pda == 'lcx' else 12
    info = {'d3': 0, 'd4_to_lad': 0, 'other_lcx': 0, 'other_nearest': 0}
    o = lab == 14
    if o.any():
        comp, nc = ndi.label(o, STRUCT)
        lad_pieces, rest = [], []
        for i in range(1, nc + 1):
            p = comp == i
            ring = ndi.binary_dilation(p, STRUCT, iterations=2) & ~p
            v = lab[ring]
            nl, ncx = int(np.isin(v, list(LAD_SIDE)).sum()), int(np.isin(v, list(LCX_SIDE)).sum())
            if p.sum() >= 20 and nl > ncx:
                lad_pieces.append(p)
            elif p.sum() >= 20 and ncx > nl:
                out[p] = 3
                info['other_lcx'] += 1
            else:
                rest.append(p)
        if lad_pieces:
            left = np.isin(lab, LEFT)
            bb = ndi.find_objects(left.astype(np.uint8))[0]
            bb = tuple(slice(max(b.start - 1, 0), b.stop + 1) for b in bb)  # geodesics on the left tree's box only
            lc, labc = left[bb], lab[bb]
            src = np.argwhere(labc == 1) if (labc == 1).any() else np.argwhere(labc == 2)[:1]
            dist, _ = MCP_Geometric(np.where(lc, 1.0, np.inf), sampling=tuple(z)).find_costs([tuple(s) for s in src])
            att = [float(np.min(dist[p[bb]])) for p in lad_pieces]
            order = np.argsort(att)
            for r, j in enumerate(order):
                out[lad_pieces[j]] = 7 if r == 0 else 2
            info['d3'] += 1
            info['d4_to_lad'] += len(lad_pieces) - 1
        if rest:  # small or two-sided pieces: nearest LAD/LCx voxel in mm, as territory.py does for Other
            m = np.zeros_like(o)
            for p in rest:
                m |= p
            srcm = np.isin(out, [2, 3])
            if srcm.any():
                sp_pts, op = np.argwhere(srcm), np.argwhere(m)
                _, i = cKDTree(sp_pts * z).query(op * z)
                out[tuple(op.T)] = out[tuple(sp_pts[i].T)]
            info['other_nearest'] += len(rest)
    return out, info


def one(args):
    path, left_pda = args
    c = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    assert c not in SEALED
    im = nb.load(path)
    lab = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    out, info = map_case(lab, z, left_pda)
    four = np.array([TO4[i] for i in range(13)], np.uint8)[out]
    ref4 = territory.to_four(lab, z)
    return {'case': c, **info, 'counts': {STAGE1[k]: int((out == k).sum()) for k in range(1, 13) if (out == k).any()},
            'collapse_mismatch_voxels': int((four != ref4).sum()),
            'collapse_mismatch_other_voxels': int(((four != ref4) & (lab == 14)).sum()),
            'tree_voxels': int((lab > 0).sum())}


def main(icx, census_json, out, left_pda='lcx'):
    cen = json.load(open(census_json))
    paths = [(os.path.join(icx, f"{int(r['case'][1:]) + 1}.coronary.nii.gz"), left_pda) for r in cen['rows']]
    with Pool(3, maxtasksperchild=20) as p:
        rows = []
        for i, r in enumerate(p.imap(one, paths, chunksize=1)):
            rows.append(r)
            if i % 50 == 0:
                print(i, flush=True)
    grp = {r['case']: r['group'] for r in cen['rows']}
    for r in rows:
        r['group'] = grp[r['case']]
    json.dump(rows, open(out, 'w'), indent=0)
    print(len(rows), 'cases ->', out)


if __name__ == '__main__':
    a = sys.argv[1:]
    lp = a[a.index('--left-pda') + 1] if '--left-pda' in a else 'lcx'
    main(a[0], a[1], a[2], lp)
