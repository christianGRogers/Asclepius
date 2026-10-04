"""Label-consistency post-processing for a 4-class coronary prediction (CPU, no learning).

relabel(binary, lab, sp):
  1. Skeletonise the binary prediction; split the skeleton graph into segments at junctions.
  2. Every foreground voxel is owned by its nearest skeleton voxel -> by a segment.
  3. Segment vote: each segment takes the majority label of the voxels it owns
     (voxel-count weighted). A segment cannot be split-labelled internally.
  4. Island absorption: for each class, 26-connected components of that class other than
     the largest one in each binary tree are relabelled to the class they share the most
     face-adjacent voxels with (if any), so each class is one piece per tree.
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
    fg = binary & (lab > 0)
    sv = seg_of[near[fg]]
    lv = lab[fg]
    ok = sv >= 0
    nseg = len(segs)
    counts = np.zeros((nseg, 5), np.int64)
    np.add.at(counts, (sv[ok], lv[ok]), 1)
    maj = counts[:, 1:].argmax(1) + 1
    out = lab.copy()
    newv = lv.copy()
    newv[ok] = maj[sv[ok]]
    out[fg] = newv
    return out


def absorb_islands(binary, lab):
    out = lab.copy()
    trees = cc3d.connected_components(binary, connectivity=26)
    for c in (1, 2, 3, 4):
        cl = cc3d.connected_components(out == c, connectivity=26)
        n = cl.max()
        if n <= 1:
            continue
        sizes = np.bincount(cl.ravel())
        # keep the largest class-c piece per tree
        keep = set()
        tree_of = {}
        m = cl > 0
        tree_of_arr = np.zeros(n + 1, np.int64)
        tree_of_arr[cl[m]] = trees[m]
        tree_of = {k: int(tree_of_arr[k]) for k in range(1, n + 1)}
        for t in set(tree_of.values()):
            ks = [k for k in tree_of if tree_of[k] == t]
            keep.add(max(ks, key=lambda k: sizes[k]))
        objs = ndi.find_objects(cl)
        for k in range(1, n + 1):
            if k in keep or objs[k - 1] is None:
                continue
            sl = tuple(slice(max(a.start - 1, 0), a.stop + 1) for a in objs[k - 1])
            piece = cl[sl] == k
            osl = out[sl]  # view
            ring = ndi.binary_dilation(piece) & ~piece & (osl > 0)
            nb = osl[ring]
            nb = nb[nb != c]
            if len(nb):
                osl[piece] = np.bincount(nb, minlength=5)[1:].argmax() + 1
    return out


def relabel(binary, lab, sp):
    return absorb_islands(binary, segment_vote(binary, lab, sp))
