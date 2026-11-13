"""Janus 1-F round 1 (Foxtrot): what ImageCAS-X's 14 classes give D44/D45's 18 classes, on the 613 cases that are in
D45's 620 training set under either reading of the locked-20 salt (split620.json 'census_613').

Per case and class: presence, volume (mm^3), skeleton length (mm) and median lumen diameter along the skeleton (mm).
'Other' (14): each 26-connected component is classed by the labels it touches (diagonal side = LAD/D1/D2; marginal
side = LCx/OM1/OM2/IM), giving how often a D3 candidate exists. Unlabelled side twigs: the LAD-only (2) and RCA-only
(9) masks are skeletonised; the longest skeleton path is the trunk; every other skeleton component of >= 3 mm hanging
off it is a twig (septals and unlabelled diagonals for LAD; conus, SN, RV and right marginal branches for RCA).
Dominance from the labels: right (R-PDA or R-PLA, no L-PDA/L-PLA), left (L only), co (both), none.
Usage: python3 census14.py <label_dir> <split620.json> <out_dir> [n_proc]"""
import json, os, sys
from collections import deque
from multiprocessing import Pool
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

SEG = ['LM', 'LAD', 'LCx', 'D1', 'D2', 'OM1', 'OM2', 'IM', 'RCA', 'R-PDA', 'R-PLA', 'L-PDA', 'L-PLA', 'Other']
DIAG = {2, 4, 5}; MARG = {3, 6, 7, 8}
OFFS = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)]


def crop(m, pad=2):
    sl = ndi.find_objects(m.astype(np.uint8))[0]
    return tuple(slice(max(s.start - pad, 0), s.stop + pad) for s in sl)


def skel_stats(mask, z):
    """skeleton length (mm), median diameter (mm) along it; returns skeleton coords too."""
    if mask.sum() < 4:
        return 0.0, 0.0, None, None
    sl = crop(mask); m = mask[sl]
    sk = skeletonize(m) > 0
    edt = ndi.distance_transform_edt(m, sampling=z)
    pts = np.argwhere(sk)
    if len(pts) == 0:
        return 0.0, 0.0, None, None
    length = path_len(pts, z)
    return length, float(2 * np.median(edt[sk])), sk, edt


def path_len(pts, z):
    """total skeleton edge length in mm: every pair of 26-neighbouring skeleton voxels is one edge."""
    pts = np.asarray(pts)
    if len(pts) < 2:
        return 0.0
    lo = pts.min(0); sh = pts.max(0) - lo + 3
    m = np.zeros(sh, bool); q = pts - lo + 1; m[q[:, 0], q[:, 1], q[:, 2]] = True
    zz = np.asarray(z); L = 0.0
    for o in OFFS:
        if o <= (0, 0, 0):
            continue  # each undirected edge once
        a = m[1:-1, 1:-1, 1:-1]
        b = m[1 + o[0]:sh[0] - 1 + o[0], 1 + o[1]:sh[1] - 1 + o[1], 1 + o[2]:sh[2] - 1 + o[2]]
        L += int((a & b).sum()) * float(np.sqrt(((np.asarray(o) * zz) ** 2).sum()))
    return L


def graph(sk):
    pts = list(map(tuple, np.argwhere(sk))); S = set(pts)
    nb = {p: [(p[0] + o[0], p[1] + o[1], p[2] + o[2]) for o in OFFS if (p[0] + o[0], p[1] + o[1], p[2] + o[2]) in S]
          for p in pts}
    return nb


def far(nb, src, z):
    zz = np.asarray(z); dist = {src: 0.0}; prev = {src: None}; dq = deque([src])
    while dq:  # BFS in hops is fine for a tree skeleton; weight by mm for the far point
        p = dq.popleft()
        for q in nb[p]:
            if q not in dist:
                dist[q] = dist[p] + float(np.sqrt((((np.asarray(q) - p) * zz) ** 2).sum())); prev[q] = p; dq.append(q)
    end = max(dist, key=dist.get)
    return end, dist, prev


def twigs(mask, z, min_mm=3.0):
    L, d, sk, edt = skel_stats(mask, z)
    if sk is None:
        return {'trunk_mm': 0, 'twigs': []}
    nb = graph(sk)
    # largest skeleton component only
    lab, n = ndi.label(sk, structure=np.ones((3, 3, 3)))
    big = np.argmax(np.bincount(lab.ravel())[1:]) + 1
    nodes = [p for p in nb if lab[p] == big]
    a, _, _ = far(nb, nodes[0], z); b, dist, prev = far(nb, a, z)
    trunk = set(); p = b
    while p is not None:
        trunk.add(p); p = prev[p]
    rest = sk.copy()
    for p in trunk:
        rest[p] = False
    # keep only twig components that touch the trunk (hang off it)
    tl, tn = ndi.label(rest, structure=np.ones((3, 3, 3)))
    near = ndi.binary_dilation(np.isin(np.arange(1), [0]) if False else _mask_of(trunk, sk.shape), structure=np.ones((3, 3, 3)))
    out = []
    for i, objsl in enumerate(ndi.find_objects(tl), start=1):
        comp = tl == i
        if not (comp & near).any():
            continue
        pts = np.argwhere(comp); ln = path_len(pts, z) + float(min(z))  # + the joint step
        if ln >= min_mm:
            out.append({'len_mm': round(ln, 1), 'diam_mm': round(float(2 * np.median(edt[comp])), 2)})
    return {'trunk_mm': round(dist[b], 1), 'trunk_diam_mm': round(float(2 * np.median(edt[_mask_of(trunk, sk.shape)])), 2),
            'twigs': out}


def _mask_of(pts, shape):
    m = np.zeros(shape, bool)
    for p in pts:
        m[p] = True
    return m


def one(path):
    im = nib.load(path); a = np.asarray(im.dataobj).astype(np.int16)
    nzc = np.argwhere(a > 0); lo = np.maximum(nzc.min(0) - 3, 0); hi = nzc.max(0) + 4
    a = np.ascontiguousarray(a[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]])  # the tree's box: every count is unchanged
    z = tuple(float(x) for x in im.header.get_zooms()[:3])
    vox = float(np.prod(z)); cnt = np.bincount(a.ravel().clip(0), minlength=15)[:15]
    r = {'case': 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1), 'zooms': z, 'cls': {}}
    for k in range(1, 15):
        if cnt[k] == 0:
            continue
        m = a == k
        L, d, _, _ = skel_stats(m, z)
        ncomp = ndi.label(m, structure=np.ones((3, 3, 3)))[1]
        r['cls'][SEG[k - 1]] = {'mm3': round(cnt[k] * vox, 1), 'len_mm': round(L, 1), 'diam_mm': round(d, 2), 'ncomp': int(ncomp)}
    # Other components
    oth = []
    if cnt[14]:
        ol, on = ndi.label(a == 14, structure=np.ones((3, 3, 3)))
        for i, s in enumerate(ndi.find_objects(ol), start=1):
            s2 = tuple(slice(max(x.start - 2, 0), x.stop + 2) for x in s)
            c = ol[s2] == i; ring = ndi.binary_dilation(c, structure=np.ones((3, 3, 3))) & ~c
            touch = set(np.unique(a[s2][ring]).tolist()) - {0, 14}
            side = 'diag' if touch & DIAG and not touch & MARG else 'marg' if touch & MARG and not touch & DIAG else \
                'both' if touch & DIAG and touch & MARG else 'none'
            oth.append({'mm3': round(int(c.sum()) * vox, 1), 'touch': sorted(SEG[t - 1] for t in touch), 'side': side})
    r['other_components'] = oth
    for k, nm in ((2, 'LAD'), (9, 'RCA')):
        if cnt[k]:
            r[f'{nm}_twigs'] = twigs(a == k, z)
    R = bool(cnt[10] or cnt[11]); Lf = bool(cnt[12] or cnt[13])
    r['dominance'] = 'co' if R and Lf else 'right' if R else 'left' if Lf else 'none'
    return r


if __name__ == '__main__':
    lab_dir, split_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
    npr = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    keep = set(json.load(open(split_json))['census_613'])
    files = sorted(os.path.join(lab_dir, f) for f in os.listdir(lab_dir) if f.endswith('.coronary.nii.gz')
                   and 'c%04d' % (int(f.split('.')[0]) - 1) in keep)
    assert len(files) == len(keep), (len(files), len(keep))
    os.makedirs(out, exist_ok=True)
    with Pool(npr) as p:
        res = p.map(one, files, chunksize=4)
    json.dump(res, open(os.path.join(out, 'census14_per_case.json'), 'w'))
    print('cases', len(res))
