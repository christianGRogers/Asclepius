"""Label-consistency post-processing for a 4-class coronary prediction (CPU, no learning).

relabel(binary, lab, sp):
  1. Skeletonise the binary prediction; split the skeleton graph into segments at junctions.
  2. Every foreground voxel is owned by its nearest skeleton voxel -> by a segment.
  3. Island repair along segments: the shortest run of label L on a segment's centreline that is
     bounded on both sides by the same label M *and is shorter than both of them* is relabelled M
     (with the L-voxels it owns); repeated until none is left. (Without the 'shorter than both'
     condition a trunk between two islands was itself treated as an island -- measured.)
     Label changes at segment ends (true class boundaries) are never touched.
  4. Island absorption (smallest first, iterated): any class piece that is not its class's
     largest piece in its binary tree takes the label it shares most 26-contact with -- but only
     pieces <= max_piece_mm3 (default 25 mm^3). Larger orphaned pieces are left alone: when the
     error is the *connection* (e.g. a carina stretch mislabelled), the orphan is usually a correct
     side branch, and absorbing it would spread the error (measured: 543 -> 1365 wrong voxels on
     c0039 carina5 without the cap).
Nothing is added or deleted: only labels of voxels the segmenter found change.
"""
import cc3d
import numpy as np
from scipy import ndimage as ndi

import treelib as T


def segment_vote(binary, lab, sp):
    skel = T.skeletonise(binary)
    pts, G = T.skeleton_graph(skel, sp)
    if len(pts) == 0:
        return lab
    segs, deg = T.segments(G)
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
