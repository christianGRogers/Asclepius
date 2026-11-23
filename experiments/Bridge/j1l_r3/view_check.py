"""Bridge, Janus 1-L round 3 (#302, Round 2 ruling §5 item 3): the 115 mm view check for S's 0.45 mm form.

Janus 0 trains on 256^3 patches at 0.5 mm, a 128 mm cube. Re-planned at 0.45 mm with the same ResEnc 60 GB planner,
the patch stays at most 256^3 (the memory target binds, not the image size), so the cube shrinks to 115.2 mm. This
script measures, on the D45 train 620's ImageCAS-X labels only (collapsed by territory.to_four, D25), what a smaller
cube loses in context. Labels only; no CT; no aorta (TotalSegmentator) file; no locked-100 or sealed id (refused).

Measures, per case, for cube sides L in {128.0 (0.5 mm), 115.2 (0.45 mm), 102.4 (0.4 mm, report)}:
  fit_tree    the whole tree's axis-aligned bounding box fits in one cube (all three extents <= L);
  fit_left    the left tree (LM + LAD + LCx) fits;   fit_rca   the RCA fits;
  root_view   per class, the share of its voxels v whose tree root r lies inside a cube of side L centred on v
              (Chebyshev distance |v - r|_inf <= L / 2). This is the best-placed sliding window's context: can the
              network see where the vessel comes from when it labels v? Roots are proxies (no aorta is read):
              left root = the centroid of LM; RCA root = the RCA voxel nearest the left root.
  coverage    the largest share of the tree's voxels any one cube of side L holds (a 2 mm occupancy grid, exact
              box sums by an integral image).

PRE-REGISTERED RULE (written before the first run; Bridge v3 §3):
  The 0.45 mm form PASSES the view check when both hold, against the 0.5 mm cube on the same 620:
    (V1) the share of cases whose whole tree fits falls by <= 10 percentage points;
    (V2) in every class, the voxel-weighted root_view share falls by <= 5 percentage points.
  Otherwise it FAILS, and S at 0.45 mm needs a larger patch (288^3 = 129.6 mm) or is not run at 0.45 mm.

Usage: python3 view_check.py <dir of the 620 labels, cNNNN.nii.gz> [n_proc] > view_check.json
       python3 view_check.py --selftest
"""
from __future__ import annotations

import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'trillium', 'icx4', 'lib'))

SIDES = {'0.50mm': 128.0, '0.45mm': 115.2, '0.40mm': 102.4}
CLASSES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
GRID_MM = 2.0


def banned():
    sp = json.load(open(os.path.join(REPO, 'experiments/Delta/j1l_r1/janus1_split_proposal.json')))
    se = json.load(open(os.path.join(REPO, 'trillium/sealed_test.json')))
    return set(sp['locked100']) | set(se['sealed_icx_test']) | set(se['sealed_quality0']), set(sp['train620'])


def best_cube_share(pts_mm, L):
    """Largest fraction of points inside any axis-aligned cube of side L (2 mm occupancy grid, integral image)."""
    if len(pts_mm) == 0:
        return float('nan')
    q = np.floor((pts_mm - pts_mm.min(0)) / GRID_MM).astype(int)
    shape = q.max(0) + 1
    occ = np.zeros(shape, np.int64)
    np.add.at(occ, tuple(q.T), 1)
    k = int(round(L / GRID_MM))
    if (shape <= k).all():
        return 1.0
    S = np.zeros(tuple(s + 1 for s in shape), np.int64)
    S[1:, 1:, 1:] = occ.cumsum(0).cumsum(1).cumsum(2)
    kx, ky, kz = (min(k, s) for s in shape)
    box = (S[kx:, ky:, kz:] - S[:-kx, ky:, kz:] - S[kx:, :-ky, kz:] - S[kx:, ky:, :-kz]
           + S[:-kx, :-ky, kz:] + S[:-kx, ky:, :-kz] + S[kx:, :-ky, :-kz] - S[:-kx, :-ky, :-kz])
    return float(box.max() / len(pts_mm))


def measure(lab4, zooms):
    sp = np.asarray(zooms[:3], float)
    out = {'n_vox': {}, 'extent_mm': None, 'fit_tree': {}, 'fit_left': {}, 'fit_rca': {}, 'root_view': {},
           'coverage': {}}
    pts = {c: np.argwhere(lab4 == c) * sp for c in CLASSES}
    allp = np.concatenate([p for p in pts.values() if len(p)]) if any(len(p) for p in pts.values()) else np.zeros((0, 3))
    left = np.concatenate([pts[c] for c in (1, 2, 3) if len(pts[c])] or [np.zeros((0, 3))])
    ext = lambda p: (p.max(0) - p.min(0) + sp) if len(p) else np.zeros(3)
    out['extent_mm'] = [round(float(x), 1) for x in ext(allp)]
    out['extent_left_mm'] = [round(float(x), 1) for x in ext(left)]
    out['extent_rca_mm'] = [round(float(x), 1) for x in ext(pts[4])]
    lroot = pts[1].mean(0) if len(pts[1]) else (left[np.argmin(left[:, 2])] if len(left) else None)
    rroot = None
    if len(pts[4]) and lroot is not None:
        rroot = pts[4][np.argmin(np.linalg.norm(pts[4] - lroot, axis=1))]
    for name, L in SIDES.items():
        out['fit_tree'][name] = bool(len(allp) and (ext(allp) <= L).all())
        out['fit_left'][name] = bool(len(left) and (ext(left) <= L).all())
        out['fit_rca'][name] = bool(len(pts[4]) and (ext(pts[4]) <= L).all())
        out['coverage'][name] = round(best_cube_share(allp, L), 4)
        rv = {}
        for c, cn in CLASSES.items():
            root = rroot if c == 4 else lroot
            if len(pts[c]) == 0 or root is None:
                rv[cn] = None
                continue
            rv[cn] = [int((np.abs(pts[c] - root).max(1) <= L / 2).sum()), int(len(pts[c]))]
        out['root_view'][name] = rv
    out['n_vox'] = {cn: int(len(pts[c])) for c, cn in CLASSES.items()}
    return out


def one(path):
    import nibabel as nib
    from territory import to_four
    c = os.path.basename(path).split('.')[0]
    img = nib.load(path)
    icx = np.asarray(img.dataobj).astype(np.int16)
    z = img.header.get_zooms()
    r = measure(to_four(icx, z), z)
    r['case'] = c
    r['zooms'] = [round(float(x), 3) for x in z[:3]]
    return r


def summarise(rows):
    s = {'n': len(rows), 'rule': 'V1: fit_tree share falls <= 10 pp; V2: every class root_view falls <= 5 pp'}
    for key in ('fit_tree', 'fit_left', 'fit_rca'):
        s[key] = {n: round(float(np.mean([r[key][n] for r in rows])), 4) for n in SIDES}
    s['coverage_median'] = {n: round(float(np.median([r['coverage'][n] for r in rows])), 4) for n in SIDES}
    s['coverage_p10'] = {n: round(float(np.percentile([r['coverage'][n] for r in rows], 10)), 4) for n in SIDES}
    rv = {}
    for n in SIDES:
        rv[n] = {}
        for cn in CLASSES.values():
            num = sum(r['root_view'][n][cn][0] for r in rows if r['root_view'][n][cn])
            den = sum(r['root_view'][n][cn][1] for r in rows if r['root_view'][n][cn])
            rv[n][cn] = round(num / den, 4) if den else None
    s['root_view_voxel_share'] = rv
    ext = np.array([r['extent_mm'] for r in rows])
    s['extent_mm_median'] = [round(float(x), 1) for x in np.median(ext, 0)]
    s['extent_mm_p90'] = [round(float(x), 1) for x in np.percentile(ext, 90, 0)]
    s['extent_mm_max_axis_median'] = round(float(np.median(ext.max(1))), 1)
    a, b = '0.50mm', '0.45mm'
    v1 = s['fit_tree'][a] - s['fit_tree'][b]
    v2 = {cn: rv[a][cn] - rv[b][cn] for cn in CLASSES.values()}
    s['V1_drop_pp'] = round(100 * v1, 2)
    s['V2_drop_pp'] = {k: round(100 * v, 2) for k, v in v2.items()}
    s['verdict_0.45mm'] = 'PASS' if (v1 <= 0.10 and all(v <= 0.05 for v in v2.values())) else 'FAIL'
    return s


def selftest():
    sp = (0.4, 0.4, 0.5)
    lab = np.zeros((400, 400, 300), np.uint8)
    # LM at the origin corner, an LAD running 120 mm along x, an RCA 60 mm along y.
    lab[10:20, 10:20, 10:20] = 1
    lab[20:320, 14:16, 14:16] = 2                           # 300 x 0.4 = 120 mm
    lab[10:12, 30:180, 14:16] = 4                           # 60 mm
    r = measure(lab, sp)
    assert r['fit_tree']['0.50mm'] and not r['fit_tree']['0.45mm'], r['extent_mm']    # 128 mm extent in x
    assert r['fit_rca']['0.40mm']
    lad128 = r['root_view']['0.50mm']['LAD']; lad115 = r['root_view']['0.45mm']['LAD']
    assert lad128[0] > lad115[0] and lad128[1] == lad115[1]
    assert abs(best_cube_share(np.argwhere(lab > 0) * np.array(sp), 128.0) - 1.0) < 1e-9
    assert best_cube_share(np.argwhere(lab > 0) * np.array(sp), 60.0) < 0.9
    bad, train = banned()
    assert not (bad & train)
    print('[view_check] self-test passed')


def main():
    if sys.argv[1:2] == ['--selftest']:
        return selftest()
    d = sys.argv[1]
    npr = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    bad, train = banned()
    files = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.nii.gz'))
    ids = {os.path.basename(f).split('.')[0] for f in files}
    if ids & bad or ids - train:
        sys.exit(f'[view_check] REFUSING: ids outside the train 620: {sorted((ids & bad) | (ids - train))[:5]}')
    with Pool(npr) as p:
        rows = p.map(one, files, chunksize=4)
    print(json.dumps({'summary': summarise(rows), 'rows': rows}, indent=1))


if __name__ == '__main__':
    main()
