"""Janus 1-F round 1 (Atlas): what ImageCAS-X's 14 classes give a 4-vessel + 14-branch model, on the training cases
only (split.json 'training_620_both': 613 cases; no locked, sealed or quality-0 case is opened). Labels only, no CT.

Per case and ImageCAS-X class: presence, voxels, mm^3; calibre (2 x Euclidean distance to background of the WHOLE tree,
in mm, sampled on the class's skeleton voxels); skeleton end points (a proxy for how many unnamed side twigs a class
carries). Per case: the 'Other' components (>= 20 voxels, 26-connected) and the classes each one touches (one-voxel
dilation): touching LAD/D1/D2 = a D3/D4 candidate, touching LCx/OM1/OM2/L-PDA/L-PLA = OM3/OM4. Ordinal consistency:
the geodesic distance (voxel steps x mean spacing) from the LM along the left tree to the first voxel of D1 vs D2 and
of OM1 vs OM2. Dominance from ImageCAS-X's Descriptors.xlsx.
Usage: python census.py <data_dir> <split.json> <Descriptors.xlsx> <out.jsonl> [n_proc]"""
import os, sys, json
from collections import deque
from multiprocessing import Pool
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

DATA, SPLIT, DESC, OUT = (sys.argv[1:5] + [None] * 4)[:4]   # importable: ordinal_rule.py reuses geodesic_from
NP = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5].isdigit() else 4
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'D1', 5: 'D2', 6: 'OM1', 7: 'OM2', 8: 'IM', 9: 'RCA', 10: 'R-PDA',
         11: 'R-PLA', 12: 'L-PDA', 13: 'L-PLA', 14: 'Other'}
LEFT = [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14]
LAD_SIDE, LCX_SIDE = {2, 4, 5}, {3, 6, 7, 12, 13}
S26 = np.ones((3, 3, 3), bool)
OFFS = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)]


def geodesic_from(mask, seeds):
    """BFS steps over a 26-connected mask from the seed voxels (unweighted; times mean spacing later)."""
    dist = np.full(mask.shape, -1, np.int32)
    q = deque(map(tuple, np.argwhere(seeds)))
    for p in q:
        dist[p] = 0
    sh = mask.shape
    while q:
        p = q.popleft(); d = dist[p] + 1
        for o in OFFS:
            n = (p[0] + o[0], p[1] + o[1], p[2] + o[2])
            if 0 <= n[0] < sh[0] and 0 <= n[1] < sh[1] and 0 <= n[2] < sh[2] and mask[n] and dist[n] < 0:
                dist[n] = d; q.append(n)
    return dist


def one(cid):
    num = int(cid[1:]) + 1
    im = nib.load(os.path.join(DATA, f'{num}.coronary.nii.gz'))
    lab = np.asarray(im.dataobj).astype(np.uint8)
    nz = np.argwhere(lab > 0)
    lo, hi = np.maximum(nz.min(0) - 3, 0), nz.max(0) + 4
    lab = lab[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    z = np.array(im.header.get_zooms()[:3], float)
    vox = float(np.prod(z)); mean_sp = float(z.mean())
    tree = lab > 0
    edt = ndi.distance_transform_edt(tree, sampling=z)
    skel = skeletonize(tree).astype(bool)
    nb = ndi.convolve(skel.astype(np.uint8), S26.astype(np.uint8), mode='constant') - 1  # skeleton neighbours
    r = {'case': cid, 'zooms': [round(float(v), 3) for v in z], 'cls': {}}
    for v, n in NAMES.items():
        m = lab == v
        nv = int(m.sum())
        if not nv:
            continue
        sk = skel & m
        d = {'vox': nv, 'mm3': round(nv * vox, 1)}
        if sk.any():
            diam = 2 * edt[sk]
            d.update(diam_med=round(float(np.median(diam)), 3), diam_p10=round(float(np.percentile(diam, 10)), 3),
                     skel_len_mm=round(float(sk.sum()) * mean_sp, 1),
                     end_points=int(((nb == 1) & sk).sum()))
        cc, ncc = ndi.label(m, S26)
        d['components'] = int(ncc)
        r['cls'][n] = d
    # 'Other' components and what they touch
    oth = []
    cc, ncc = ndi.label(lab == 14, S26)
    for k in range(1, ncc + 1):
        c = cc == k
        if c.sum() < 20:
            continue
        ring = ndi.binary_dilation(c, S26) & ~c
        touch = sorted({int(x) for x in np.unique(lab[ring]) if x not in (0, 14)})
        side = 'LAD' if set(touch) & LAD_SIDE and not set(touch) & LCX_SIDE else \
               'LCx' if set(touch) & LCX_SIDE and not set(touch) & LAD_SIDE else \
               'both' if set(touch) & LAD_SIDE else 'none'
        oth.append({'vox': int(c.sum()), 'touch': [NAMES[t] for t in touch], 'side': side,
                    'diam_med': round(float(np.median(2 * edt[skel & c])), 3) if (skel & c).any() else None})
    r['other'] = oth
    # ordinal consistency along the left tree, from the LM
    left = np.isin(lab, LEFT)
    if (lab == 1).any():
        g = geodesic_from(left, lab == 1)
        first = {}
        for v in (4, 5, 6, 7):
            m = (lab == v) & (g >= 0)
            if m.any():
                first[NAMES[v]] = round(float(g[m].min()) * mean_sp, 1)
        for kind in ('LAD', 'LCx'):
            m = (lab == (2 if kind == 'LAD' else 3)) & (g >= 0)
            if m.any():
                first[kind + '_end'] = round(float(g[m].max()) * mean_sp, 1)
        # Other components' origin distance (for D3 ordering)
        for o, k in zip(oth, [k for k in range(1, ncc + 1) if (cc == k).sum() >= 20]):
            m = (cc == k) & (g >= 0)
            o['origin_mm'] = round(float(g[m].min()) * mean_sp, 1) if m.any() else None
        r['first_mm'] = first
    return r


if __name__ == '__main__':
    import openpyxl
    cases = json.load(open(SPLIT))['training_620_both']
    ws = openpyxl.load_workbook(DESC, read_only=True).worksheets[0]
    dom = {}
    for row in list(ws.iter_rows(values_only=True))[1:]:
        if row[0] is not None:
            c = 'c%04d' % (int(row[0]) - 1)
            if c in set(cases):
                dom[c] = {'quality': row[1], 'dominance': row[2], 'disease': row[3]}
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)['case'] for l in open(OUT)}
    todo = [c for c in cases if c not in done]
    print(f'{len(cases)} cases, {len(todo)} to do', flush=True)
    with Pool(NP) as p, open(OUT, 'a') as f:
        for i, r in enumerate(p.imap_unordered(one, todo, chunksize=2)):
            r.update(dom.get(r['case'], {}))
            f.write(json.dumps(r) + '\n'); f.flush()
            if i % 50 == 0:
                print(i, flush=True)
