"""Shared helpers for Delta's topology experiments (mask-only, CPU).

load_crop      : binary mask cropped to tree bbox + margin, uint8, with spacing
skeleton_graph : skeleton (skimage Lee), EDT radius (mm), networkx voxel graph
segments       : decompose skeleton graph into branch segments between junction/end nodes
pseudo_labels  : geometric 4-class pseudo-labelling (LM/LAD/LCx/RCA) of a GT tree.
                 NOT anatomical ground truth -- a plausible partition used only to
                 test how metrics respond to label errors.
"""
import sys

import cc3d
import networkx as nx
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import mask_path, ct_path  # noqa: E402

OFFS = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)]


def load_crop(case, margin_mm=6.0):
    img = nib.load(mask_path(case))
    sp = np.array(img.header.get_zooms()[:3], float)
    m = np.asanyarray(img.dataobj) > 0.5
    idx = [np.nonzero(m.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    mv = np.ceil(margin_mm / sp).astype(int)
    lo = np.maximum([a[0] for a in idx] - mv, 0)
    hi = np.minimum([a[-1] + 1 for a in idx] + mv, m.shape)
    crop = m[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]].astype(np.uint8)
    axc = ''.join(nib.aff2axcodes(img.affine))
    return crop, sp, lo, axc


def skeletonise(mask):
    return skeletonize(mask.astype(bool)).astype(bool)  # 3D -> Lee 1994


def skeleton_graph(skel, sp):
    pts = np.argwhere(skel)
    index = -np.ones(skel.shape, np.int64)
    index[tuple(pts.T)] = np.arange(len(pts))
    G = nx.Graph()
    G.add_nodes_from(range(len(pts)))
    pad = np.pad(index, 1, constant_values=-1)
    for o in OFFS:
        if o < (0, 0, 0):
            continue  # each pair once
        nb = pad[tuple(pts[:, k] + 1 + o[k] for k in range(3))]
        ok = nb >= 0
        w = float(np.sqrt(sum((o[k] * sp[k]) ** 2 for k in range(3))))
        G.add_edges_from((int(a), int(b), {'w': w}) for a, b in zip(np.nonzero(ok)[0], nb[ok]))
    return pts, G


def segments(G):
    """Branch segments: maximal paths whose interior nodes have degree 2."""
    deg = dict(G.degree())
    key = {n for n, d in deg.items() if d != 2}
    seen_edges = set()
    segs = []
    for s in key:
        for nb in G.neighbors(s):
            e = (min(s, nb), max(s, nb))
            if e in seen_edges:
                continue
            path = [s, nb]; seen_edges.add(e)
            prev, cur = s, nb
            while cur not in key:
                nxt = [x for x in G.neighbors(cur) if x != prev]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                e = (min(prev, cur), max(prev, cur))
                if e in seen_edges:
                    break
                seen_edges.add(e); path.append(cur)
            segs.append(path)
    # pure cycles / isolated degree-2 loops are ignored (rare)
    return segs, deg


def path_len(G, path):
    return sum(G[a][b]['w'] for a, b in zip(path[:-1], path[1:]))


def radius_mm(mask, sp):
    return ndi.distance_transform_edt(mask, sampling=sp)


def pseudo_labels(mask, sp, axc, min_sub_mm=15.0):
    """Return (labels uint8 same shape as mask, info dict).

    Left vs right tree: the two largest components; the one whose centroid is further
    toward patient-Left is the left tree (RCA = the other). LM root = the left-tree
    skeleton endpoint with the largest radius. LM bifurcation = first junction on the
    geodesic tree from the root where >=2 child subtrees each carry >= min_sub_mm of
    skeleton. LAD = the child subtree whose centroid is more Anterior; LCx = the other
    (other children with >= min_sub_mm, e.g. a ramus, go to LCx-or-LAD by the same
    anterior rule against the two largest). Every mask voxel takes the label of its
    nearest skeleton voxel. Small extra components keep label of nearest labelled voxel.
    """
    lab, n = cc3d.connected_components(mask, connectivity=26, return_N=True)
    sizes = np.bincount(lab.ravel())[1:]
    order = np.argsort(-sizes) + 1
    # axis direction of patient Left and Anterior in index space
    lr_axis = [i for i, c in enumerate(axc) if c in 'LR'][0]; lr_sign = 1 if axc[lr_axis] == 'L' else -1
    ap_axis = [i for i, c in enumerate(axc) if c in 'AP'][0]; ap_sign = 1 if axc[ap_axis] == 'A' else -1
    big = [k for k in order[:2]]
    cents = {k: np.argwhere(lab == k).mean(0) for k in big}
    if len(big) == 2:
        left = max(big, key=lambda k: lr_sign * cents[k][lr_axis]); right = [k for k in big if k != left][0]
    else:
        left, right = big[0], None
    out = np.zeros(mask.shape, np.uint8)
    skel = skeletonise(lab == left)
    pts, G = skeleton_graph(skel, sp)
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    rad = radius_mm(mask, sp)
    deg = dict(G.degree())
    ends = [v for v, d in deg.items() if d == 1]
    r_at = {v: rad[tuple(pts[v])] for v in G.nodes}
    def term_r(v, k=25):
        # median radius over the first k skeleton voxels walking in from endpoint v
        prev, cur, rs = None, v, []
        for _ in range(k):
            rs.append(r_at[cur])
            nxt = [x for x in G.neighbors(cur) if x != prev]
            if len(nxt) != 1 and cur != v:
                break
            if not nxt:
                break
            prev, cur = cur, nxt[0]
        return float(np.median(rs))
    root = max(ends, key=term_r)
    T = nx.bfs_tree(G, root)  # geodesic-ish tree (BFS on voxel graph)
    # subtree skeleton length (mm) bottom-up
    sublen = {}
    for v in reversed(list(nx.topological_sort(T))):
        sublen[v] = sum(sublen[c] + G[v][c]['w'] for c in T.successors(v))
    node_lab = {}
    cur = root; lm_path = [root]; bif = None
    while True:
        ch = list(T.successors(cur))
        bigch = [c for c in ch if sublen[c] + G[cur][c]['w'] >= min_sub_mm]
        if len(bigch) >= 2:
            bif = cur; break
        if not ch:
            break
        cur = max(ch, key=lambda c: sublen[c]); lm_path.append(cur)
    for v in lm_path:
        node_lab[v] = 1
    if bif is not None:
        ch = sorted([c for c in T.successors(bif)], key=lambda c: -sublen[c])
        two = ch[:2]

        def desc(c):
            return [c] + list(nx.descendants(T, c))
        dc = {c: desc(c) for c in ch}
        ant = {c: ap_sign * pts[dc[c]][:, ap_axis].mean() for c in two}
        lad = max(two, key=lambda c: ant[c]); lcx = [c for c in two if c != lad][0]
        for c in ch:
            if c in two:
                L = 2 if c == lad else 3
            else:
                a = ap_sign * pts[dc[c]][:, ap_axis].mean()
                L = 2 if abs(a - ant[lad]) < abs(a - ant[lcx]) else 3
            for v in dc[c]:
                node_lab[v] = L
    for v in G.nodes:
        node_lab.setdefault(v, 2)
    skl = np.zeros(mask.shape, np.uint8)
    for v, L in node_lab.items():
        skl[tuple(pts[v])] = L
    left_m = lab == left
    _, inds = ndi.distance_transform_edt(skl == 0, sampling=sp, return_indices=True)
    near = skl[tuple(inds)]
    out[left_m] = near[left_m]
    if right is not None:
        out[lab == right] = 4
    rest = (mask > 0) & (out == 0)
    if rest.any():
        _, inds = ndi.distance_transform_edt(out == 0, sampling=sp, return_indices=True)
        out[rest] = out[tuple(inds)][rest]
    info = dict(root=pts[root].tolist(), bif=pts[bif].tolist() if bif is not None else None,
                lm_len_mm=path_len(G, lm_path), n_left_skel=len(pts))
    return out, info


# ---------------------------------------------------------------- ImageCAS-X reference labels
# ImageCAS-X (Bransby et al., arXiv:2608.30404, Zenodo 10.5281/zenodo.21887809) class ids:
# 1 LM, 2 LAD, 3 LCx, 4 D1, 5 D2, 6 OM1, 7 OM2, 8 IM, 9 RCA, 10 R-PDA, 11 R-PLA, 12 L-PDA, 13 L-PLA, 14 Other
# Project 4-class, "subtree" convention: side branches inherit their parent trunk's class.
# IM (ramus) has no parent trunk; it is put with LCx here (a convention choice, flagged).
ICX_TO_4 = {1: 1, 2: 2, 4: 2, 5: 2, 3: 3, 6: 3, 7: 3, 8: 3, 12: 3, 13: 3, 9: 4, 10: 4, 11: 4}
# "trunk-only" convention: only the four named trunks are labelled; side branches are background
ICX_TRUNK = {1: 1, 2: 2, 3: 3, 9: 4}
ICX_MAP_FILE = SCR + '/work/Delta/icxmap_copy.json'


def icx_path(case):
    import json
    import os
    mp = json.load(open(ICX_MAP_FILE))
    if case not in mp:
        return None
    icx_id = mp[case][0]
    for d in ('Crucible', 'Bridge', 'Atlas'):
        for p in (f'{SCR}/work/{d}/icx/ImageCAS-X_dataset/segmentations/{icx_id}.coronary.nii.gz',
                  f'{SCR}/work/{d}/icx/{icx_id}.coronary.nii.gz'):
            if os.path.exists(p):
                return p
    return None


def load_icx(case, margin_mm=6.0, convention='subtree'):
    """Return (mask bool crop, 4-class labels crop, raw 14-class crop, sp, lo, axcodes)."""
    p = icx_path(case)
    img = nib.load(p)
    sp = np.array(img.header.get_zooms()[:3], float)
    raw = np.asanyarray(img.dataobj).astype(np.uint8)
    m = raw > 0
    idx = [np.nonzero(m.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    mv = np.ceil(margin_mm / sp).astype(int)
    lo = np.maximum([a[0] for a in idx] - mv, 0)
    hi = np.minimum([a[-1] + 1 for a in idx] + mv, m.shape)
    sl = tuple(slice(lo[k], hi[k]) for k in range(3))
    raw = raw[sl]; m = m[sl]
    lut = np.zeros(256, np.uint8)
    for k, v in (ICX_TO_4 if convention == 'subtree' else ICX_TRUNK).items():
        lut[k] = v
    lab = lut[raw]
    if convention == 'subtree':
        rest = m & (lab == 0)  # 'Other' (14): nearest labelled voxel
        if rest.any():
            _, inds = ndi.distance_transform_edt(lab == 0, sampling=sp, return_indices=True)
            lab[rest] = lab[tuple(inds)][rest]
    else:
        m = lab > 0
    return m, lab, raw, sp, lo, ''.join(nib.aff2axcodes(img.affine))


# ---------------------------------------------------------------- blood-pool ostium proxy (round 2)
def blood_pool(ct, sp, exclude=None, thr_hu=200.0, open_mm=3.0, min_cc_mm3=2000.0):
    """Large contrast-filled pools (aortic root, chambers) from a CT crop, CPU-cheap.
    Smooth (sigma 0.7 mm), threshold > thr_hu, remove `exclude` (coronary mask) dilated 1 mm,
    morphological opening with a ball of radius open_mm (removes vessel-calibre structures),
    keep 26-components >= min_cc_mm3. Used as a stand-in for the TotalSegmentator aorta when
    memory does not allow it (TotalSegmentator fast used 4.6 + 2.7 GB RSS here)."""
    g = ndi.gaussian_filter(ct.astype(np.float32), sigma=0.7 / np.asarray(sp))
    m = g > thr_hu
    if exclude is not None:
        m &= ~ndi.binary_dilation(exclude, iterations=2)
    # opening by a ball of radius open_mm, via two Euclidean distance transforms
    er = ndi.distance_transform_edt(m, sampling=sp) > open_mm
    m = ndi.distance_transform_edt(~er, sampling=sp) <= open_mm
    lab, n = cc3d.connected_components(m, connectivity=26, return_N=True)
    if n == 0:
        return m
    sz = np.bincount(lab.ravel()) * float(np.prod(sp)); sz[0] = 0
    return np.isin(lab, np.nonzero(sz >= min_cc_mm3)[0])
