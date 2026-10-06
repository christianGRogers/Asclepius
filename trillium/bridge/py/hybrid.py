"""H (A7 candidate P3b): keep the direct model's own class evidence (softmax), but decode it on the
predicted tree's skeleton under the anatomical grammar, so every class becomes a connected sub-tree:
  right tree (highest mean P(RCA))           -> RCA
  left tree, rooted at the best ostium      -> LM is ONE path from the root; every subtree below it is
                                               wholly LAD or wholly LCx (exact tree MAP)
  other components                           -> the model's majority class over the component
Unary per skeleton vertex = mean log-softmax over the mask voxels that vertex owns.
"""
import networkx as nx
import numpy as np

import label as Lb
from namer import skeleton_case


def decode(G, nodes, logp, roots):
    idx = {n: i for i, n in enumerate(nodes)}
    best = None
    for r in roots:
        T = nx.bfs_tree(G, r)
        cost = {}
        for n in nx.dfs_postorder_nodes(T, r):
            i = idx[n]
            c = np.zeros(4)
            kids = list(T.successors(n))
            for y in (2, 3):
                c[y] = -logp[i, y - 1] + sum(cost[ch][y] for ch in kids)
            base = sum(min(cost[ch][2], cost[ch][3]) for ch in kids)
            gain = min([cost[ch][1] - min(cost[ch][2], cost[ch][3]) for ch in kids] + [0.0])
            c[1] = -logp[i, 0] + base + gain
            cost[n] = c
        if best is None or cost[r][1] < best[0]:
            best = (cost[r][1], r, T, cost)
    _, r, T, cost = best
    lab, stack = {}, [(r, 1)]
    while stack:
        n, y = stack.pop()
        lab[n] = y
        kids = list(T.successors(n))
        if y == 1:
            g = [cost[ch][1] - min(cost[ch][2], cost[ch][3]) for ch in kids]
            cont = kids[int(np.argmin(g))] if kids and min(g) < 0 else None
            for ch in kids:
                stack.append((ch, 1 if ch is cont else (2 if cost[ch][2] <= cost[ch][3] else 3)))
        else:
            for ch in kids:
                stack.append((ch, y))
    return lab


def hybrid(m, prob, A, z, lo, full_shape, K=8):
    """m: bool crop (D's foreground); prob: (5, *crop) softmax of the direct model on the same crop."""
    d, assign, orph_idx = skeleton_case(m, A, z, lo, full_shape)
    out = np.zeros(m.shape, np.uint8)
    if d is None:
        return out, {'fail': 'empty'}
    nv = len(d['P'])
    lp = np.full((nv, 5), 0.0)
    cnt = np.zeros(nv)
    for k, (idx, j) in assign.items():
        pv = prob[:, idx[:, 0], idx[:, 1], idx[:, 2]].T  # (nvox, 5)
        np.add.at(lp, j, np.log(np.clip(pv, 1e-6, 1)))
        np.add.at(cnt, j, 1)
    lp /= np.maximum(cnt, 1)[:, None]
    Lb.BRIDGE = 4.0
    comps = Lb.components(d)
    comps = Lb.bridge(comps, d['P'], Lb.BRIDGE)
    tl = {k: sum(w for _, _, w in G.edges(data='w')) for k, G in comps.items()}
    trees = sorted([k for k in comps if tl[k] >= Lb.TREEMIN], key=lambda k: -tl[k])[:2]
    vlab = np.zeros(nv, np.uint8)
    info = {'n_trees': len(trees)}
    if len(trees) == 2:
        pr = {k: float(np.mean(lp[list(comps[k].nodes()), 4])) for k in trees}
        right = max(trees, key=lambda k: pr[k]); left = min(trees, key=lambda k: pr[k])
    elif len(trees) == 1:
        left, right = trees[0], None
        if np.mean(lp[list(comps[left].nodes()), 4]) > np.mean(lp[list(comps[left].nodes()), 1:4].max(1)):
            left, right = None, trees[0]
    else:
        left = right = None
    if right is not None:
        vlab[list(comps[right].nodes())] = 4
    if left is not None:
        G = comps[left]
        nodes = list(G.nodes())
        other = d['P'][list(comps[right].nodes())] if right is not None else None
        ef = Lb.endpoint_features(d, G, other)
        cands = sorted([f for f in ef if not f['edge']], key=lambda f: -Lb.ostium_score(f, 'learned'))[:K] or ef[:K]
        logp = lp[nodes][:, 1:4]
        labmap = decode(G, nodes, logp, [f['e'] for f in cands])
        for n, y in labmap.items():
            vlab[n] = y
    for k, G in comps.items():
        if k in (left, right):
            continue
        ns = list(G.nodes())
        vlab[ns] = int(np.argmax(lp[ns, 1:5].sum(0))) + 1
    miss = np.where(vlab == 0)[0]
    if len(miss):
        vlab[miss] = np.argmax(lp[miss, 1:5], 1) + 1
    for k, (idx, j) in assign.items():
        out[tuple(idx.T)] = vlab[j]
    for idx in orph_idx:
        pv = prob[:, idx[:, 0], idx[:, 1], idx[:, 2]]
        out[tuple(idx.T)] = int(np.argmax(pv[1:].sum(1))) + 1
    return out, info
