"""Janus 1-F round 2 (Bridge), CPU, on the 620 D45 training cases ONLY (split.json from fetch_seg620.py).

Per case it measures three things the round-1 ruling sends to round 2:

1. contact : SegQueue 0.20.0's D47 collapse rule (`segqueue14.labels.assign_contact_branches`, imported, not copied)
             applied to ImageCAS-X's posterior branches with the side prefix removed (PDA = R-PDA | L-PDA,
             PLB = R-PLA | L-PLA), parents RCA = {RCA} and LCx = {LCx, OM1, OM2, IM}. Each component's verdict is
             compared with ImageCAS-X's own side (majority of its voxels R- or L-). Item 2 (the origin collapse).
2. band    : how much ImageCAS-X background a stage-2 label-set band releases (item 4): background voxels within
             d mm (d = 4, 8, 15) of the traced tree, in mm^3, split by the territory of the nearest tree voxel
             (LAD side, LCx side, RCA side, LM), and for the territory-restricted band (LAD side and RCA side,
             plus the first 30 mm of the LCx, where S1-S3, SN, Conus and RMA arise).
3. twigs   : unnamed side twigs of the trunk classes (LAD, LCx, RCA), census of record (item 10): the skeleton's
             longest path is the trunk; every other skeleton component is a twig, measured by its voxel count x the
             mean spacing; reported at >= 3 and >= 5 mm.

Usage: census_r2.py <icx_dir> <out.jsonl> [n_proc]
"""
import json
import os
import sys
from multiprocessing import Pool

import cc3d
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'src'))
from segqueue14.labels import assign_contact_branches  # noqa: E402

LM, LAD, LCX, D1, D2, OM1, OM2, IM, RCA, RPDA, RPLA, LPDA, LPLA, OTHER = range(1, 15)
BANDS = (4.0, 8.0, 15.0)
LCX_PROX_MM = 30.0
ST26 = ndi.generate_binary_structure(3, 3)


def side_of(lab):
    """Territory per tree voxel: 1 LAD side, 2 LCx side, 3 RCA side, 4 LM; 'Other' by the side it touches."""
    terr = np.zeros(lab.shape, np.uint8)
    terr[np.isin(lab, (LAD, D1, D2))] = 1
    terr[np.isin(lab, (LCX, OM1, OM2, IM, LPDA, LPLA))] = 2
    terr[np.isin(lab, (RCA, RPDA, RPLA))] = 3
    terr[lab == LM] = 4
    oth, n = cc3d.connected_components((lab == OTHER).astype(np.uint8), connectivity=26, return_N=True)
    for k in range(1, n + 1):
        m = oth == k
        ring = ndi.binary_dilation(m, ST26) & ~m
        t = terr[ring]
        t = t[t > 0]
        terr[m] = np.bincount(t, minlength=5).argmax() if t.size else 1
    return terr


def geodesic_mm(mask, seeds, z):
    """Geodesic distance (mm, 26-neighbour steps weighted by length) inside mask from seed voxels."""
    from skimage.graph import MCP_Geometric
    cost = np.where(mask, 1.0, np.inf)
    d, _ = MCP_Geometric(cost, sampling=tuple(z)).find_costs([tuple(s) for s in seeds])
    return d


def twigs(mask, z):
    """Lengths (mm) of skeleton pieces off the trunk's longest path."""
    if mask.sum() < 10:
        return []
    sk = skeletonize(mask) > 0
    lab, n = ndi.label(sk, ST26)
    if n == 0:
        return []
    sizes = ndi.sum(sk, lab, range(1, n + 1))
    sk = lab == (1 + int(np.argmax(sizes)))
    pts = np.argwhere(sk)
    idx = {tuple(p): i for i, p in enumerate(pts)}
    offs = [np.array(o) for o in np.ndindex(3, 3, 3) if o != (1, 1, 1)]
    offs = [o - 1 for o in offs]
    nb = [[idx[t] for o in offs if (t := tuple(p + o)) in idx] for p in pts]

    def bfs(s):
        dist = np.full(len(pts), -1)
        dist[s] = 0
        q, par = [s], np.full(len(pts), -1)
        for u in q:
            for v in nb[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    par[v] = u
                    q.append(v)
        return dist, par

    d0, _ = bfs(0)
    a = int(np.argmax(d0))
    da, par = bfs(a)
    b = int(np.argmax(da))
    path = set()
    u = b
    while u >= 0:
        path.add(u)
        u = par[u]
    rest = np.zeros_like(sk)
    for i, p in enumerate(pts):
        if i not in path:
            rest[tuple(p)] = True
    rl, rn = ndi.label(rest, ST26)
    step = float(np.mean(z))
    return sorted((round(float(c) * step, 1) for c in ndi.sum(rest, rl, range(1, rn + 1))), reverse=True)


def one(args):
    icx, c = args
    img = nib.load(os.path.join(icx, 'segmentations', f'{int(c[1:]) + 1}.coronary.nii.gz'))
    lab = np.asarray(img.dataobj).astype(np.uint8)
    z = np.array(img.header.get_zooms()[:3], float)
    pad = np.ceil(max(BANDS) / z).astype(int) + 2
    nz = np.argwhere(lab > 0)
    lo = np.maximum(nz.min(0) - pad, 0)
    hi = np.minimum(nz.max(0) + pad + 1, lab.shape)
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    vv = float(np.prod(z))
    out = {'case': c, 'spacing': [round(float(v), 3) for v in z]}

    # 1. contact rule
    branches = [('PDA', np.isin(lab, (RPDA, LPDA))), ('PLB', np.isin(lab, (RPLA, LPLA)))]
    parents = {'RCA': lab == RCA, 'LCx': np.isin(lab, (LCX, OM1, OM2, IM))}
    res = assign_contact_branches(branches, parents)
    comps = []
    for name, m in branches:
        cc, n = cc3d.connected_components(m.astype(np.uint8), connectivity=26, return_N=True)
        for k in range(1, n + 1):
            cm = cc == k
            nl = int(np.isin(lab[cm], (LPDA, LPLA)).sum())
            nr = int(cm.sum()) - nl
            got = 'LCx' if res['masks']['LCx'][cm].any() else 'RCA'
            comps.append({'cls': name, 'vox': int(cm.sum()), 'icx_side': 'L' if nl > nr else 'R', 'rule': got})
    out['contact'] = {'components': comps, 'fallback': res['fallback'],
                      'fallbackUnattached': res['fallbackUnattached'], 'fallbackTie': res['fallbackTie']}

    # 2. bands
    tree = lab > 0
    terr = side_of(lab)
    dist, ind = ndi.distance_transform_edt(~tree, sampling=z, return_indices=True)
    near = terr[tuple(ind)]
    # first 30 mm of the LCx from its LM end (or from its most proximal voxel if no LM)
    lcx = lab == LCX
    prox = np.zeros_like(lcx)
    if lcx.any():
        seeds = np.argwhere(lcx & ndi.binary_dilation(lab == LM, ST26))
        if len(seeds) == 0:
            seeds = np.argwhere(lcx)[:1]
        g = geodesic_mm(lcx, seeds, z)
        prox = lcx & (g <= LCX_PROX_MM)
    host = np.isin(terr, (1, 3)) | prox
    dh = ndi.distance_transform_edt(~host, sampling=z) if host.any() else np.full(lab.shape, np.inf)
    out['tree_mm3'] = round(tree.sum() * vv, 1)
    d_lad = ndi.distance_transform_edt(terr != 1, sampling=z)
    d_rca = ndi.distance_transform_edt(terr != 3, sampling=z)
    out['band'] = {}
    for d in BANDS:
        b = (~tree) & (dist <= d)
        bt = (~tree) & (dh <= d)
        out['band'][str(d)] = {
            'all_mm3': round(b.sum() * vv, 1),
            'by_side_mm3': {s: round(float((b & (near == k)).sum()) * vv, 1)
                            for k, s in ((1, 'LAD'), (2, 'LCx'), (3, 'RCA'), (4, 'LM'))},
            'host_mm3': round(bt.sum() * vv, 1),
            'host_LAD_and_RCA_both_mm3': round(float((bt & (d_lad <= d) & (d_rca <= d)).sum()) * vv, 1)}

    # 3. trunk twigs
    out['twigs_mm'] = {n: twigs(lab == k, z) for k, n in ((LAD, 'LAD'), (LCX, 'LCx'), (RCA, 'RCA'))}
    return out


def main():
    icx, dst = sys.argv[1], sys.argv[2]
    npr = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    cases = json.load(open(os.path.join(icx, 'split.json')))['train620']
    assert len(cases) == 620
    done = set()
    if os.path.exists(dst):                      # resumable: keep finished cases
        done = {json.loads(line)['case'] for line in open(dst) if line.strip()}
    todo = [c for c in cases if c not in done]
    with Pool(npr) as p, open(dst, 'a') as f:
        for r in p.imap_unordered(one, [(icx, c) for c in todo]):
            f.write(json.dumps(r) + '\n')
            f.flush()


if __name__ == '__main__':
    main()
