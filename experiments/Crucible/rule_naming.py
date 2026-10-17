# Rule-based 4-class naming of a BINARY coronary tree (no CT, no learning), scored against ImageCAS-X.
# Question: how good are "manufactured" 4-class pseudo-labels derived automatically from a binary mask?
#   input A = ImageCAS-X merged lumen (isolates the naming step from mask quality)
#   input B = our Girder binary mask (the original ImageCAS label) -> scored on voxels both masks call vessel
# Rules: two largest components = left/right tree (left = lower header-x centroid; verified on ICX);
# right tree -> RCA; left tree: skeletonize, root = skeleton endpoint with the largest lumen radius (ostium is
# a blunt cut), LM = root..first junction where >=2 child subtrees are each >= MINLEN mm; among the large
# children LAD = most anterior (header +y), LCx = most posterior, any middle child -> 'ramus' (ignored).
# Voxels take the label of their nearest skeleton voxel; small fragments take the label of the nearest tree voxel.
import sys, json, glob, os, re, numpy as np, nibabel as nib, networkx as nx
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path
W = SCR + '/work/Crucible'
MINLEN = 20.0  # mm
TERR = {1: 1, 2: 2, 4: 2, 5: 2, 3: 3, 6: 3, 7: 3, 12: 3, 13: 3, 9: 4, 10: 4, 11: 4}  # 8 (IM), 14 (Other) -> ignore
MAIN = {1: 1, 2: 2, 3: 3, 9: 4}


def map_icx(L, table):
    out = np.full(L.shape, 255, np.uint8); out[L == 0] = 0
    for k, v in table.items(): out[L == k] = v
    return out  # 255 = ignore


def name_tree(m, sp):
    lab, n = ndi.label(m, structure=np.ones((3, 3, 3)))
    sz = np.bincount(lab.ravel()); sz[0] = 0
    big = np.argsort(sz)[::-1][:2]
    big = [b for b in big if sz[b] > 0]
    cx = {b: np.argwhere(lab == b)[:, 0].mean() for b in big}
    left = max(big, key=lambda b: cx[b]) if len(big) == 2 else big[0]  # header x axis is negative: left tree = higher voxel i
    right = [b for b in big if b != left]
    out = np.zeros(m.shape, np.uint8)
    if right: out[lab == right[0]] = 4
    L = lab == left
    sk = skeletonize(L)
    dt = ndi.distance_transform_edt(L, sampling=sp)
    pts = np.argwhere(sk); ix = {tuple(p): i for i, p in enumerate(pts)}
    G = nx.Graph()
    offs = [np.array(o) for o in np.ndindex(3, 3, 3) if o != (1, 1, 1)]
    for i, p in enumerate(pts):
        for o in offs:
            q = tuple(p + o - 1)
            j = ix.get(q)
            if j is not None and j > i: G.add_edge(i, j, w=float(np.linalg.norm((o - 1) * sp)))
    G.add_nodes_from(range(len(pts)))
    comp = max(nx.connected_components(G), key=len); G = G.subgraph(comp).copy()
    ends = [v for v in G if G.degree(v) == 1]
    root = max(ends, key=lambda v: dt[tuple(pts[v])])
    T = nx.bfs_tree(G, root)  # directed tree from the root (cycles broken arbitrarily)
    dist = nx.single_source_dijkstra_path_length(G, root, weight='w')
    # subtree length (mm) for every node: post-order accumulation
    sub = {}
    for v in reversed(list(nx.topological_sort(T))):
        sub[v] = sum(sub[c] + G[v][c]['w'] for c in T.successors(v))
    # walk down from root until a junction with >=2 big children
    v = root; lm_nodes = [root]; lab_node = {}
    while True:
        ch = list(T.successors(v))
        bigch = [c for c in ch if sub[c] + G[v][c]['w'] >= MINLEN]
        if len(bigch) >= 2 or not ch: break
        v = max(ch, key=lambda c: sub[c]); lm_nodes.append(v)
    for u in nx.descendants(T, root) | {root}: lab_node[u] = 3  # default
    for u in lm_nodes: lab_node[u] = 1
    ch = [c for c in T.successors(v) if sub[c] + G[v][c]['w'] >= MINLEN]
    if len(ch) >= 2:
        ys = {c: np.mean([pts[u][1] for u in nx.descendants(T, c) | {c}]) for c in ch}
        order = sorted(ch, key=lambda c: ys[c])  # ascending y: posterior first
        roles = {order[-1]: 2, order[0]: 3}
        for c in order[1:-1]: roles[c] = 255  # ramus / third branch: ignore
        for c in ch:
            for u in nx.descendants(T, c) | {c}: lab_node[u] = roles[c]
        # small side twigs off the bifurcation node stay LCx default; give them the nearest big child's label instead
    sklab = np.zeros(m.shape, np.uint8)
    for u, l in lab_node.items(): sklab[tuple(pts[u])] = l
    _, ind = ndi.distance_transform_edt(sklab == 0, return_indices=True)
    nearest = sklab[tuple(ind)]
    out[L] = nearest[L]
    # fragments -> label of nearest labelled voxel
    rest = m & (out == 0)
    if rest.any():
        _, ind = ndi.distance_transform_edt(out == 0, return_indices=True)
        out[rest] = out[tuple(ind)][rest]
    return out


def dice(a, b):
    s = a.sum() + b.sum(); return float(2 * (a & b).sum() / s) if s else None


def score(pred, ref, valid):
    r = {}
    for k in (1, 2, 3, 4):
        r[k] = dice((pred == k) & valid, (ref == k) & valid)
    acc = float(((pred == ref) & valid & (ref > 0)).sum() / max(1, (valid & (ref > 0)).sum()))
    return r, acc


if __name__ == '__main__':
    SH, NS, NMAX = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    files = sorted(glob.glob(W + '/icx/ImageCAS-X_dataset/segmentations/*.nii.gz'),
                   key=lambda f: int(os.path.basename(f).split('.')[0]))[::NMAX][SH::NS]  # every NMAX-th case
    rows = []
    for f in files:
        i = int(os.path.basename(f).split('.')[0]); c = 'c%04d' % (i - 1)
        im = nib.load(f); Lf = np.asarray(im.dataobj).astype(np.uint8)
        mo = np.asarray(nib.load(mask_path(c)).dataobj) > 0.5
        u = np.argwhere((Lf > 0) | mo); lo = np.maximum(u.min(0) - 4, 0); hi = u.max(0) + 5
        sl = tuple(slice(a, b) for a, b in zip(lo, hi)); Lf = Lf[sl]; mo = mo[sl]
        sp = np.array(im.header.get_zooms()[:3], float)
        r = {'id': i, 'case': c}
        try: pA = name_tree(Lf > 0, sp)
        except Exception as e: pA = e
        for tag, table in (('terr', TERR), ('main', MAIN)):
            ref = map_icx(Lf, table)
            try:
                if isinstance(pA, Exception): raise pA
                d, acc = score(pA, ref, (ref != 255) & (Lf > 0)); r[f'A_{tag}'] = d; r[f'A_{tag}_acc'] = acc
            except Exception as e: r[f'A_{tag}'] = str(e)
            if tag == 'terr':
                try:
                    pB = name_tree(mo, sp)
                    d, acc = score(pB, ref, (ref != 255) & (Lf > 0) & mo); r['B_terr'] = d; r['B_terr_acc'] = acc
                except Exception as e: r['B_terr'] = str(e)
        rows.append(r); print(json.dumps(r), flush=True)
    json.dump(rows, open(W + f'/rule_naming_{SH}.json', 'w'))
