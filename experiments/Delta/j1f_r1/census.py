"""Janus 1-F round 1 (Delta): per-class census of ImageCAS-X's 14 classes on the D45 split, labels only (no CT).

For every non-sealed ImageCAS-X case (720: train 560, val 80, open test 80) it measures, per class:
  presence, voxels, volume (mm^3), 26-connected pieces, centreline length (mm) and median lumen radius (mm,
  Euclidean distance transform sampled on the 3-D skeleton);
and per case:
  - which parent "Other" (label 14: D3/D4, OM3/OM4) touches: LAD side (LAD, D1, D2) or LCx side (LCx, OM1, OM2,
    IM, L-PDA, L-PLA), and how many separate Other pieces sit on each side;
  - unnamed side branches inside the LAD and RCA classes (the voxels D44 would call S1-S3, D3 (no: D3 is in Other),
    SN, Conus, RMA): skeleton branches >= 5 mm that leave the class's main path, with length and median radius.
Sealed cases (sealed_test.json) are never opened; fetch_allowed.py never downloaded them.

Usage: python census.py <icx_dir> <out.json>
"""
import hashlib, json, os, sys
from multiprocessing import Pool

import networkx as nx
import nibabel as nb
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

ROOT = os.path.dirname(os.path.abspath(__file__)) + '/../../..'
S = json.load(open(f'{ROOT}/trillium/icx4/sealed_test.json'))
SEALED = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'D1', 5: 'D2', 6: 'OM1', 7: 'OM2', 8: 'IM', 9: 'RCA', 10: 'R-PDA',
         11: 'R-PLA', 12: 'L-PDA', 13: 'L-PLA', 14: 'Other'}
LAD_SIDE, LCX_SIDE = {2, 4, 5}, {3, 6, 7, 8, 12, 13}
STRUCT = np.ones((3, 3, 3), bool)
MIN_BRANCH_MM = 5.0


def cid(n):
    return 'c%04d' % (int(n) - 1)


def split(icx):
    """D45: train 620 = train 560 + dev 44 + 16 of open-36; locked 100 = val 80 + 20 of open-36 (smallest
    sha256('asclepius-janus1-locked100:' + id)). The id is the project's ImageCAS-X id, c0000-style (as in
    sealed_test.json and D43); the alternative reading (ImageCAS number) is reported by split_check.py."""
    rd = lambda s: [cid(x) for x in open(os.path.join(icx, f'{s}.txt')).read().split()]
    train, val = rd('train'), rd('val')
    open36 = S['open_icx_test']
    key = lambda c: hashlib.sha256(('asclepius-janus1-locked100:' + c).encode()).hexdigest()
    ranked = sorted(open36, key=key)
    locked_open, train_open = ranked[:20], ranked[20:]
    return {'train560': train, 'dev44': S['excluded_dev_cases_in_test'], 'train_open16': sorted(train_open),
            'val80': val, 'locked_open20': sorted(locked_open)}


def skeleton_graph(mask):
    sk = skeletonize(mask)
    pts = np.argwhere(sk)
    idx = {tuple(p): i for i, p in enumerate(pts)}
    G = nx.Graph()
    G.add_nodes_from(range(len(pts)))
    offs = [np.array(o) for o in np.ndindex(3, 3, 3) if o != (1, 1, 1)]
    for i, p in enumerate(pts):
        for o in offs:
            q = tuple(p + o - 1)
            j = idx.get(q)
            if j is not None and j > i:
                G.add_edge(i, j, w=float(np.linalg.norm(o - 1)))
    return pts, G


def path_len(G, nodes, sp):
    return len(nodes) * sp


def class_stats(lab, k, zooms):
    m = lab == k
    n = int(m.sum())
    if n == 0:
        return None
    vox = float(np.prod(zooms))
    sl = ndi.find_objects(m.astype(np.uint8))[0]
    sl = tuple(slice(max(s.start - 2, 0), s.stop + 2) for s in sl)
    mc = m[sl]
    _, pieces = ndi.label(mc, STRUCT)
    edt = ndi.distance_transform_edt(mc, sampling=zooms)
    sk = skeletonize(mc)
    r = edt[sk]
    step = float(np.mean(zooms))  # skeleton voxels -> mm, approximate
    return {'voxels': n, 'mm3': round(n * vox, 1), 'pieces': int(pieces),
            'cl_mm': round(float(sk.sum()) * step, 1),
            'r_med_mm': round(float(np.median(r)), 3) if r.size else None,
            'r_p10_mm': round(float(np.percentile(r, 10)), 3) if r.size else None}


def side_branches(lab, k, zooms):
    """Skeleton branches of class k that leave its main (longest) path, >= MIN_BRANCH_MM."""
    m = lab == k
    if not m.any():
        return []
    sl = ndi.find_objects(m.astype(np.uint8))[0]
    sl = tuple(slice(max(s.start - 2, 0), s.stop + 2) for s in sl)
    mc = m[sl]
    edt = ndi.distance_transform_edt(mc, sampling=zooms)
    pts, G = skeleton_graph(mc)
    if G.number_of_nodes() < 3:
        return []
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    for u, v, d in G.edges(data=True):
        d['mm'] = float(np.linalg.norm((pts[u] - pts[v]) * zooms))
    a = next(iter(G.nodes))
    far = nx.single_source_dijkstra_path_length(G, a, weight='mm')
    b = max(far, key=far.get)
    db, paths = nx.single_source_dijkstra(G, b, weight='mm')
    c = max(db, key=db.get)
    main = set(paths[c])
    rest = G.subgraph(set(G.nodes) - main)
    out = []
    for comp in nx.connected_components(rest):
        touch = any(nb_ in main for n in comp for nb_ in G.neighbors(n))
        if not touch:
            continue
        L = sum(d['mm'] for u, v, d in G.subgraph(comp).edges(data=True)) + float(np.mean(zooms))
        if L >= MIN_BRANCH_MM:
            r = [edt[tuple(pts[n])] for n in comp]
            out.append({'mm': round(L, 1), 'r_med_mm': round(float(np.median(r)), 3)})
    return sorted(out, key=lambda x: -x['mm'])


def other_sides(lab):
    o = lab == 14
    if not o.any():
        return None
    comp, n = ndi.label(o, STRUCT)
    res = {'lad': 0, 'lcx': 0, 'none': 0, 'pieces': int(n)}
    for i in range(1, n + 1):
        c = comp == i
        if c.sum() < 20:
            continue
        ring = ndi.binary_dilation(c, STRUCT, iterations=2) & ~c
        vals = lab[ring]
        nl = int(np.isin(vals, list(LAD_SIDE)).sum())
        nc = int(np.isin(vals, list(LCX_SIDE)).sum())
        res['lad' if nl > nc else 'lcx' if nc > nl else 'none'] += 1
    return res


def one(path):
    name = os.path.basename(path)
    c = cid(name.split('.')[0])
    assert c not in SEALED, c
    im = nb.load(path)
    lab = np.asarray(im.dataobj).astype(np.uint8)
    zooms = np.array(im.header.get_zooms()[:3], float)
    row = {'case': c, 'zooms': [round(float(z), 4) for z in zooms], 'classes': {}}
    for k, nm in NAMES.items():
        s = class_stats(lab, k, zooms)
        if s:
            row['classes'][nm] = s
    row['other_sides'] = other_sides(lab)
    row['lad_side_branches'] = side_branches(lab, 2, zooms)
    row['rca_side_branches'] = side_branches(lab, 9, zooms)
    row['lcx_side_branches'] = side_branches(lab, 3, zooms)
    return row


def main(icx, out):
    sp = split(icx)
    allowed = {c: g for g, cs in sp.items() for c in cs}
    files = sorted(f for f in os.listdir(icx) if f.endswith('.coronary.nii.gz'))
    todo = [os.path.join(icx, f) for f in files if cid(f.split('.')[0]) in allowed]
    assert not any(cid(os.path.basename(f).split('.')[0]) in SEALED for f in todo)
    with Pool(4) as p:
        rows = p.map(one, todo, chunksize=4)
    for r in rows:
        r['group'] = allowed[r['case']]
    json.dump({'split': sp, 'rows': rows}, open(out, 'w'), indent=0)
    print(f'{len(rows)} cases written to {out}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
