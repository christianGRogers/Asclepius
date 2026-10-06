"""Delta's Trillium experiment: metrics and post-processing (self-contained copy of
experiments/Delta/treelib.py + postproc.py from the Asclepius repo, plus tree-F1 on real 4-class
predictions). CPU code; numpy/scipy/scikit-image/cc3d/networkx only."""
import cc3d
import networkx as nx
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

OFFS = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)]


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


def segment_vote(binary, lab, sp):
    skel = skeletonise(binary)
    pts, G = skeleton_graph(skel, sp)
    if len(pts) == 0:
        return lab
    segs, deg = segments(G)
    seg_of = -np.ones(len(pts), np.int64)
    for i, s in enumerate(segs):
        inner = s[1:-1] if len(s) > 2 else s
        seg_of[inner] = i
    # junction / end nodes: give them the segment of any neighbour
    for v in np.nonzero(seg_of < 0)[0]:
        for u in G.neighbors(v):
            if seg_of[u] >= 0:
                seg_of[v] = seg_of[u]; break
    idx = -np.ones(binary.shape, np.int64); idx[tuple(pts.T)] = np.arange(len(pts))
    _, inds = ndi.distance_transform_edt(idx < 0, sampling=sp, return_indices=True)
    near = idx[tuple(inds)]
    del inds
    node_lab = lab[tuple(pts.T)]
    # interior islands along each segment: a run of label L on the centreline bounded on
    # both sides by runs of the same label M (M != L) is relabelled M. A label change at a
    # segment end (a real class boundary, or a junction the skeleton missed) is left alone.
    target = np.zeros(len(pts), np.uint8)
    for s in segs:
        sl = [int(x) for x in node_lab[s]]
        changed = True
        while changed:
            changed = False
            runs = []  # [label, start, stop]
            st = 0
            for i in range(1, len(sl) + 1):
                if i == len(sl) or sl[i] != sl[st]:
                    runs.append([sl[st], st, i]); st = i
            # the shortest interior run that is shorter than both neighbours and bounded on both
            # sides by the same label is an island; relabel it and re-scan
            best = None
            for j in range(1, len(runs) - 1):
                Lp, L, Ln = runs[j - 1][0], runs[j][0], runs[j + 1][0]
                n = runs[j][2] - runs[j][1]
                if Lp == Ln and L != Lp and Lp > 0 and n < min(runs[j - 1][2] - runs[j - 1][1],
                                                              runs[j + 1][2] - runs[j + 1][1]):
                    if best is None or n < best[0]:
                        best = (n, j, Lp)
            if best is not None:
                _, j, Lp = best
                for i in range(runs[j][1], runs[j][2]):
                    sl[i] = Lp
                    target[s[i]] = Lp
                changed = True
    fg = binary & (lab > 0)
    tv = target[near[fg]]
    lv = lab[fg]
    flip = (tv > 0) & (lv == node_lab[near[fg]])
    out = lab.copy()
    newv = lv.copy(); newv[flip] = tv[flip]
    out[fg] = newv
    return out


def absorb_islands(binary, lab, sp=(1, 1, 1), max_piece_mm3=25.0, max_iter=300):
    """Repeatedly take the smallest class piece that is not its class's largest piece in its
    tree, and give it the label it shares most contact with. Smallest-first matters: an island
    that splits a trunk in two must be absorbed before the trunk's halves are judged."""
    out = lab.copy()
    trees = cc3d.connected_components(binary, connectivity=26)
    for _ in range(max_iter):
        cands = []
        for c in (1, 2, 3, 4):
            cl = cc3d.connected_components(out == c, connectivity=26)
            n = int(cl.max())
            if n <= 1:
                continue
            m = cl > 0
            sizes = np.bincount(cl[m], minlength=n + 1)
            tree_of = np.zeros(n + 1, np.int64); tree_of[cl[m]] = trees[m]
            best = {}
            for k in range(1, n + 1):
                t = tree_of[k]
                if t not in best or sizes[k] > sizes[best[t]]:
                    best[t] = k
            objs = ndi.find_objects(cl)
            for k in range(1, n + 1):
                if k != best[tree_of[k]] and objs[k - 1] is not None:
                    cands.append((int(sizes[k]), c, k, cl, objs[k - 1]))
        vv = float(np.prod(sp))
        cands = [x for x in cands if x[0] * vv <= max_piece_mm3]
        if not cands:
            break
        size, c, k, cl, ob = min(cands, key=lambda x: x[0])
        sl = tuple(slice(max(a.start - 1, 0), a.stop + 1) for a in ob)
        piece = cl[sl] == k
        osl = out[sl]
        ring = ndi.binary_dilation(piece, np.ones((3, 3, 3), bool)) & ~piece & (osl > 0)
        nb = osl[ring]; nb = nb[nb != c]
        if len(nb) == 0:
            break  # isolated piece of its own tree: nothing to absorb into (should not happen)
        osl[piece] = np.bincount(nb, minlength=5)[1:].argmax() + 1
    return out


def relabel(binary, lab, sp, max_piece_mm3=25.0):
    return absorb_islands(binary, segment_vote(binary, lab, sp), sp, max_piece_mm3)


# ------------------------------------------------------------------ geometric gap bridging (round 2)
def _line_voxels(p, q, sp, r_vox=1):
    """Voxels of a straight tube from p to q (index coords), radius r_vox voxels."""
    p = np.asarray(p, float); q = np.asarray(q, float)
    n = int(np.ceil(np.linalg.norm((q - p) * sp) / (0.25 * sp.min()))) + 2
    pts = np.round(p[None] + (q - p)[None] * np.linspace(0, 1, n)[:, None]).astype(int)
    if r_vox <= 0:
        return pts
    offs = np.array([(a, b, c) for a in range(-r_vox, r_vox + 1) for b in range(-r_vox, r_vox + 1)
                     for c in range(-r_vox, r_vox + 1) if a * a + b * b + c * c <= r_vox * r_vox])
    return (pts[:, None, :] + offs[None]).reshape(-1, 3)


def bridge(lab, anchors, sp, max_gap_mm=3.0, min_vox=100, r_vox=1, eligible=None):
    """Join every component (>= min_vox) not connected to an anchor to the nearest anchored
    component if the gap is <= max_gap_mm, with a straight tube of radius r_vox voxels.
    lab: uint8 class map (0 = background; binary also works). anchors: bool mask of voxels that
    define 'connected to an ostium' (e.g. predicted voxels within 3 mm of the aorta).
    The tube takes the class of the orphan component (its majority class).
    Returns (new lab, list of bridges as dicts). Iterates until no component can be joined, so
    chains of pieces are joined one hop at a time (nearest first).
    eligible: optional bool mask; a component is joined only if >= 50 % of its voxels are eligible
    (the 'support rule': the orphan was predicted again by a gap-centred second look)."""
    lab = lab.copy()
    sp = np.asarray(sp, float)
    bridges = []
    for _ in range(200):
        fg = lab > 0
        cl, n = cc3d.connected_components(fg, connectivity=26, return_N=True)
        if n == 0:
            break
        sizes = np.bincount(cl.ravel())
        anc_ids = set(np.unique(cl[anchors & fg])) - {0}
        if not anc_ids:
            break
        anc = np.isin(cl, list(anc_ids))
        dist, inds = ndi.distance_transform_edt(~anc, sampling=sp, return_indices=True)
        best = None
        for k in range(1, n + 1):
            if k in anc_ids or sizes[k] < min_vox:
                continue
            m = cl == k
            if eligible is not None and eligible[m].mean() < 0.5:
                continue
            dk = dist[m]
            j = int(np.argmin(dk))
            if dk[j] <= max_gap_mm and (best is None or dk[j] < best[0]):
                p = np.argwhere(m)[j]
                best = (float(dk[j]), k, p)
        if best is None:
            break
        d, k, p = best
        q = np.array([inds[a][tuple(p)] for a in range(3)])
        cls = int(np.bincount(lab[cl == k], minlength=5)[1:].argmax() + 1)
        vox = _line_voxels(p, q, sp, r_vox)
        vox = vox[np.all((vox >= 0) & (vox < np.array(lab.shape)), axis=1)]
        vox = np.unique(vox, axis=0)
        newv = vox[lab[tuple(vox.T)] == 0]
        lab[tuple(newv.T)] = cls
        bridges.append(dict(gap_mm=d, comp_vox=int(sizes[k]), cls=cls, added_vox=int(len(newv)),
                            p=p.tolist(), q=q.tolist()))
        del dist, inds
    return lab, bridges


# ======================================================================= round-3 additions
def ball(r_mm, sp):
    rr = np.ceil(r_mm / np.asarray(sp)).astype(int)
    g = np.ogrid[tuple(slice(-k, k + 1) for k in rr)]
    return sum((g[i] * sp[i]) ** 2 for i in range(3)) <= r_mm ** 2


def remove_small(binary, k=100):
    lab = cc3d.connected_components(binary, connectivity=26)
    sz = np.bincount(lab.ravel()); keep = sz >= k; keep[0] = False
    return keep[lab]


class RefTree:
    """Reference 4-class label map (cropped) -> centreline graph, per-voxel class, ostia.

    Ostia (validated in vault note 'Two cheap ostium rules find 116 of 116 true ostia'):
    per reference tree component (>= 1000 voxels), rule `thick` (thickest centreline endpoint, LM
    endpoints preferred) and rule `pool_thick` (thickest endpoint within 3 mm of the endpoint
    nearest the contrast blood pool). Trees where the two disagree by > 5 mm are flagged.
    """

    def __init__(self, lab, sp, ct=None):
        self.lab = lab.astype(np.uint8); self.sp = np.asarray(sp, float)
        self.m = self.lab > 0
        self.skel = skeletonise(self.m)
        self.pts, self.G = skeleton_graph(self.skel, self.sp)
        rad = ndi.distance_transform_edt(self.m, sampling=self.sp)
        self.r_sk = rad[tuple(self.pts.T)]
        self.lab_sk = self.lab[tuple(self.pts.T)]
        comps, n = cc3d.connected_components(self.m, connectivity=26, return_N=True)
        sizes = np.bincount(comps.ravel())
        csk = comps[tuple(self.pts.T)]
        deg = np.array([self.G.degree(i) for i in range(len(self.pts))])
        rmed = lambda u: np.median([self.r_sk[w] for w in nx.single_source_shortest_path_length(self.G, u, cutoff=20)])
        d_pool = None
        if ct is not None:
            pool = blood_pool(ct, self.sp, exclude=self.m)
            if pool.any():
                d_pool = ndi.distance_transform_edt(~pool, sampling=self.sp)
        self.roots, self.roots_pool, self.flags = [], [], []
        for k in range(1, n + 1):
            if sizes[k] < 1000:
                continue
            ends = np.nonzero((csk == k) & (deg == 1))[0]
            if len(ends) == 0:
                continue
            cand = ends[self.lab_sk[ends] == 1] if np.any(self.lab_sk[ends] == 1) else ends
            t = max(cand, key=rmed)
            self.roots.append(tuple(self.pts[t]))
            if d_pool is not None:
                dp = d_pool[tuple(self.pts[ends].T)]
                p = max(ends[dp <= dp.min() + 3.0], key=rmed)
                self.roots_pool.append(tuple(self.pts[p]))
                if np.linalg.norm((self.pts[t] - self.pts[p]) * self.sp) > 5.0:
                    self.flags.append(dict(tree=int(k), thick=self.pts[t].tolist(), pool=self.pts[p].tolist()))
        self.ncomp = int(n)


def tree_f1(ref, plab, tol_mm=1.5, roots=None, sk=None):
    """Macro tree-F1 over classes present in the reference.
    recall_c: reference class-c centreline predicted as class c AND lying in a predicted piece
    connected (pieces < tol_mm apart count as connected) to a piece containing a reference ostium.
    precision_c: predicted class-c centreline inside reference class-c voxels."""
    roots = ref.roots if roots is None else roots
    pred = plab > 0
    if not pred.any():
        return dict(tf1=0.0, per_class={}, rooted=0.0)
    dil = ndi.binary_dilation(pred, ball(tol_mm / 2, ref.sp)) if tol_mm > 0 else pred
    dl = cc3d.connected_components(dil, connectivity=26)
    rcs = {dl[r] for r in roots if dl[r] > 0}
    psk_ref = plab[tuple(ref.pts.T)]
    ok = np.isin(dl[tuple(ref.pts.T)], list(rcs)) & (psk_ref > 0)
    sk = skeletonise(pred) if sk is None else sk
    plab_sk = plab[sk]; rlab_at = ref.lab[sk]
    per = {}
    for c in (1, 2, 3, 4):
        g = ref.lab_sk == c
        if not g.any():
            continue
        rec = float((ok & g & (psk_ref == c)).sum() / g.sum())
        pc = plab_sk == c
        prec = float((rlab_at[pc] == c).mean()) if pc.any() else 0.0
        per[c] = 2 * rec * prec / (rec + prec) if rec + prec else 0.0
    return dict(tf1=float(np.mean(list(per.values()))), per_class=per, rooted=float(ok.mean()))


def fp_components(ref, pred_bin):
    pl = cc3d.connected_components(pred_bin, connectivity=26)
    return len(set(np.unique(pl[pred_bin])) - set(np.unique(pl[pred_bin & ref.m])) - {0})


def macro_dice(ref, plab):
    ds = []
    for c in (1, 2, 3, 4):
        a = ref.lab == c; b = plab == c
        if a.any():
            ds.append(2 * (a & b).sum() / (a.sum() + b.sum()))
    return float(np.mean(ds))


def anchor_components(pred, d_struct, maxd=3.0, keep=2):
    """Deployable anchors (no reference): the `keep` largest predicted components with a voxel
    within maxd mm of the anchor structure (contrast blood pool / aorta)."""
    cl = cc3d.connected_components(pred, connectivity=26)
    ids = np.unique(cl[pred & (d_struct <= maxd)]); ids = ids[ids > 0]
    if len(ids) == 0:
        return np.zeros_like(pred)
    sz = np.bincount(cl.ravel())
    return np.isin(cl, sorted(ids, key=lambda k: -sz[k])[:keep])


def gap_sites(pred, anchors, sp, maxd=15.0):
    """Un-anchored components >= 100 voxels within maxd mm of the anchored set: gap midpoints."""
    cl, n = cc3d.connected_components(pred, connectivity=26, return_N=True)
    sizes = np.bincount(cl.ravel())
    anc_ids = set(np.unique(cl[anchors & pred])) - {0}
    if not anc_ids:
        return []
    anc = np.isin(cl, list(anc_ids))
    dist, inds = ndi.distance_transform_edt(~anc, sampling=sp, return_indices=True)
    sites = []
    for k in range(1, n + 1):
        if k in anc_ids or sizes[k] < 100:
            continue
        m = cl == k
        dk = dist[m]; j = int(np.argmin(dk))
        if dk[j] <= maxd:
            p = np.argwhere(m)[j]
            q = np.array([inds[a][tuple(p)] for a in range(3)])
            sites.append(dict(comp_vox=int(sizes[k]), gap_mm=float(dk[j]),
                              mid=((p + q) / 2).round().astype(int).tolist()))
    return sites


def audit(br, pred_bin, ref):
    cl = cc3d.connected_components(pred_bin, connectivity=26)
    side = lambda c: 2 if c == 4 else (1 if c > 0 else 0)
    out = []
    for b in br:
        k = cl[tuple(b['p'])]
        comp = cl == k if k > 0 else np.zeros_like(pred_bin)
        rl = ref.lab[comp & ref.m]
        o_side = side(int(np.bincount(rl, minlength=5)[1:].argmax() + 1)) if len(rl) else 0
        a_side = side(int(ref.lab[tuple(b['q'])])) if ref.lab[tuple(b['q'])] > 0 else 0
        out.append(dict(gap_mm=round(b['gap_mm'], 2), comp_vox=b['comp_vox'], true_join=bool(len(rl)),
                        cross_tree=bool(o_side and a_side and o_side != a_side)))
    return out
