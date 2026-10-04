"""Pass 2 (cheap): rule-based branch labeller on the cached skeletons from extract.py, scored voxel-wise
against ImageCAS-X labels projected onto our binary masks.

    from label import load_case, label_case, score
"""
import json, numpy as np, networkx as nx
from scipy.spatial import cKDTree

LMIN = 20.0      # mm of downstream skeleton for a child to count as a major branch
BIFMODE = 'apsplit'
BIFWIN = 40.0
TREEMIN = 30.0   # mm of skeleton for a component to count as a tree
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}


def load_case(path):
    d = dict(np.load(path, allow_pickle=False))
    d['icx_stats'] = json.loads(str(d['icx_stats'])) if 'icx_stats' in d else None
    z = d['zooms']; A = d['A']
    d['P'] = d['V'] * z                                   # physical mm, axis-aligned with voxel grid
    d['RAS'] = d['V'] @ A[:3, :3].T + A[:3, 3]
    return d


def components(d):
    out = {}
    for k in np.unique(d['CID']):
        nodes = np.where(d['CID'] == k)[0]
        G = nx.Graph()
        G.add_nodes_from(nodes.tolist())
        sel = np.isin(d['E'][:, 0], nodes)
        for a, b in d['E'][sel]:
            G.add_edge(int(a), int(b), w=float(np.linalg.norm(d['P'][a] - d['P'][b])))
        if not nx.is_tree(G):
            if nx.is_connected(G):
                G = nx.minimum_spanning_tree(G, weight='w')
            else:  # rare: split skeleton -> take largest piece, rest become orphans
                G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
        out[int(k)] = G
    return out


def _walk_heavy(G, e, sizes_from, max_mm):
    """walk from endpoint e along the heavier side at each junction, collecting vertices up to max_mm"""
    prev, cur, acc, path = None, e, 0.0, [e]
    while acc < max_mm:
        nxt = [x for x in G.neighbors(cur) if x != prev]
        if not nxt:
            break
        x = max(nxt, key=lambda y: sizes_from(cur, y))
        acc += G[cur][x]['w']; prev, cur = cur, x; path.append(cur)
    return path


def endpoint_features(d, G, other_P=None):
    """features of every endpoint of tree G, for ostium selection"""
    P, R, V, shape = d['P'], d['R'], d['V'], d['shape']
    nodes = list(G.nodes())
    root0 = nodes[0]
    T0 = nx.bfs_tree(G, root0)
    L0 = {n: 0.0 for n in T0}
    for n in nx.dfs_postorder_nodes(T0, root0):
        for c in T0.successors(n):
            L0[n] += L0[c] + G[n][c]['w']
    tot = L0[root0]
    par = {c: p for p, c in T0.edges()}

    def sizes_from(cur, x):  # skeleton length beyond neighbour x, seen from cur
        return L0[x] if par.get(x) == cur else tot - L0[cur]
    zs = V[nodes, 2]; zmin, zmax = zs.min(), zs.max()
    okd = cKDTree(other_P) if other_P is not None and len(other_P) else None
    feats = []
    for e in nodes:
        if G.degree(e) != 1:
            continue
        p6 = _walk_heavy(G, e, sizes_from, 6.0)
        p3 = _walk_heavy(G, e, sizes_from, 3.0)
        # first stub length (to first junction of any kind)
        prev, cur, sl = None, e, 0.0
        while True:
            nxt = [x for x in G.neighbors(cur) if x != prev]
            if len(nxt) != 1:
                break
            sl += G[cur][nxt[0]]['w']; prev, cur = cur, nxt[0]
        edge = bool(np.any(V[e] < 2.5) or np.any(V[e] > shape - 3.5))
        f = dict(e=int(e), r6=float(np.mean(R[p6])), r3=float(np.mean(R[p3])), rmax6=float(np.max(R[p6])),
                 h=float((V[e, 2] - zmin) / max(zmax - zmin, 1e-6)), sl=sl, edge=edge,
                 beyond=float(sizes_from(e, next(iter(G.neighbors(e))))) / max(tot, 1e-6))
        f['dR'] = float(okd.query(P[e])[0]) if okd is not None else 0.0
        feats.append(f)
    # within-tree ranks (scale-free)
    for key in ('r6', 'r3', 'h', 'dR'):
        vals = np.array([f[key] for f in feats])
        order = vals.argsort().argsort() / max(len(vals) - 1, 1)
        for f, o in zip(feats, order):
            f[key + '_rk'] = float(o)
    return feats


OSTIUM_W = None  # set by fit; dict of feature -> weight


def ostium_score(f, method):
    if f['edge']:
        return -1e9
    if method == 'tr':
        return f['r3'] + 0.5 * f['h']
    if method == 'r6':
        return f['r6']
    if method == 'combo':
        return f['r6'] + 0.5 * f['h'] - 0.02 * f['dR']
    if method == 'learned':  # OSTIUM_W = dict(F=[...], mean=[...], scale=[...], coef=[...]) from ostium_learn.py
        x = (np.array([f[k] for k in OSTIUM_W['F']]) - OSTIUM_W['mean']) / OSTIUM_W['scale']
        return float(x @ OSTIUM_W['coef'])
    raise ValueError(method)


def rooted(G, root, P):
    T = nx.bfs_tree(G, root)
    L = {n: 0.0 for n in T}; S = {n: np.zeros(3) for n in T}
    for n in nx.dfs_postorder_nodes(T, root):
        for c in T.successors(n):
            w = G[n][c]['w']
            L[n] += L[c] + w
            S[n] += S[c] + w * (P[n] + P[c]) / 2
    dist = nx.single_source_dijkstra_path_length(G, root, weight='w')
    return T, L, S, dist


def label_left(d, G, root, lmin=LMIN, ramus='closer'):
    P, A, z = d['P'], d['A'], d['zooms']
    T, L, S, dist = rooted(G, root, P)
    lab = {n: 1 for n in T}
    cur, bif = root, None
    if BIFMODE == 'first':
        while True:
            ch = list(T.successors(cur))
            if not ch:
                break
            major = [c for c in ch if L[c] >= lmin]
            if len(major) >= 2:
                bif = cur; break
            cur = max(ch, key=lambda c: L[c])
    else:
        # 'balanced': along the heavy path from the ostium, within BIFWIN mm, the junction whose
        # second-heaviest child subtree is largest (the LAD/LCx split is the most balanced split near the ostium)
        best = None
        while dist[cur] <= BIFWIN:
            ch = sorted(T.successors(cur), key=lambda c: -L[c])
            if not ch:
                break
            if len(ch) >= 2 and L[ch[1]] >= lmin:
                if BIFMODE == 'balanced':
                    sc = L[ch[1]] + G[cur][ch[1]]['w']
                else:  # 'apsplit': LAD/LCx split = big second branch AND one child anterior, one posterior
                    R3 = d['A'][:3, :3] / d['zooms']
                    y = [float((R3 @ (S[c] / L[c] - P[cur]))[1]) for c in ch[:2]]
                    sc = L[ch[1]] / max(L[root], 1) + max(0.0, -y[0] * y[1]) ** 0.5 / 25 - dist[cur] / 100
                if best is None or sc > best[0] * 1.0:
                    best = (sc, cur)
            cur = ch[0]
        bif = best[1] if best else None
    info = dict(bif=bif, lm_len=float(dist[bif]) if bif is not None else None)
    if bif is None:
        for n in T:
            lab[n] = 2
        info['fail'] = 'no_bifurcation'
        return lab, info
    ch = list(T.successors(bif))
    major = [c for c in ch if L[c] >= lmin]
    R3 = A[:3, :3] / z  # physical displacement -> RAS displacement
    feats = np.array([R3 @ (S[c] / L[c] - P[bif]) for c in major])
    ant = feats[:, 1]
    i_lad, i_lcx = int(np.argmax(ant)), int(np.argmin(ant))
    cls = {}
    for i, c in enumerate(major):
        if i == i_lad:
            cls[c] = 2
        elif i == i_lcx:
            cls[c] = 3
        else:
            cls[c] = 2 if (ant[i] - ant[i_lcx]) > (ant[i_lad] - ant[i]) else 3
    for c in ch:
        if c not in cls:
            dv = R3 @ ((S[c] / L[c]) if L[c] > 0 else P[c]) - R3 @ P[bif]
            j = int(np.argmax([np.dot(dv, f) / (np.linalg.norm(dv) * np.linalg.norm(f) + 1e-9) for f in feats]))
            cls[c] = cls[major[j]]
    for c, k in cls.items():
        for n in nx.descendants(T, c) | {c}:
            lab[n] = k
    info.update(n_major=len(major), ant_sep=float(ant[i_lad] - ant[i_lcx]),
                lad_len=float(sum(L[c] + G[bif][c]['w'] for c in cls if cls[c] == 2)),
                lcx_len=float(sum(L[c] + G[bif][c]['w'] for c in cls if cls[c] == 3)),
                lad_dir=feats[i_lad].tolist(), lcx_dir=feats[i_lcx].tolist())
    return lab, info


def plausibility_penalty(d, inf, f):
    """anatomical sanity of a candidate labelling: LM length, LAD anterior / LCx posterior, ostium not below bifurcation"""
    if inf.get('bif') is None:
        return 10.0
    pen = 0.0
    lm = inf['lm_len']
    if lm > 30: pen += (lm - 30) / 10
    if lm < 1.5: pen += 0.5
    if inf['lad_dir'][1] < 0: pen += 0.5          # LAD subtree should lie anterior of the bifurcation
    if inf['lcx_dir'][1] > 0: pen += 0.5          # LCx posterior
    A, z = d['A'], d['zooms']
    zo = (d['RAS'][f['e']])[2]; zb = (d['V'][inf['bif']] @ A[:3, :3].T + A[:3, 3])[2]
    if zo < zb - 5: pen += (zb - 5 - zo) / 10      # ostium more than 5 mm below the bifurcation
    return pen


BRIDGE = 0.0  # mm; >0 joins a component to its nearest neighbour component when an endpoint lies within BRIDGE mm


def bridge(comps, P, thr):
    """merge components across small gaps: endpoint of one component within thr mm of any vertex of another"""
    comps = dict(comps)
    changed = True
    while changed and len(comps) > 1:
        changed = False
        for k in sorted(comps, key=lambda k: comps[k].number_of_nodes()):
            G = comps[k]
            ends = [n for n in G if G.degree(n) <= 1]
            others = [j for j in comps if j != k]
            on = np.concatenate([np.array(list(comps[j].nodes())) for j in others])
            oc = np.concatenate([np.full(comps[j].number_of_nodes(), j) for j in others])
            dd, jj = cKDTree(P[on]).query(P[ends])
            i = int(np.argmin(dd))
            if dd[i] <= thr:
                j = int(oc[jj[i]])
                H = nx.union(comps[j], G)
                H.add_edge(ends[i], int(on[jj[i]]), w=float(dd[i]))
                comps[j] = H; del comps[k]; changed = True
                break
    return comps


def label_case(d, method='combo', lmin=LMIN):
    comps = components(d)
    if BRIDGE > 0:
        comps = bridge(comps, d['P'], BRIDGE)
    P, RAS = d['P'], d['RAS']
    tl = {k: sum(w for _, _, w in G.edges(data='w')) for k, G in comps.items()}
    trees = sorted([k for k in comps if tl[k] >= TREEMIN], key=lambda k: -tl[k])
    res = dict(ncomp=len(d['comp_sizes']), n_skel_comp=len(comps), n_trees=len(trees),
               ncomp6=int(d['ncomp6']), tree_lens=[round(tl[k], 1) for k in trees[:4]])
    lab = np.zeros(len(P), np.uint8)
    if not trees:
        res['fail'] = 'no_tree'; return lab, np.zeros(len(d['ORPH']), np.uint8), res, []
    cx = {k: float(RAS[list(comps[k].nodes()), 0].mean()) for k in trees}
    if len(trees) >= 2:
        left = min(trees[:2], key=lambda k: cx[k]); right = max(trees[:2], key=lambda k: cx[k])
        res['lr_sep_x'] = cx[right] - cx[left]
    else:
        left, right = trees[0], None
        res['fail'] = 'single_tree'
    other = P[list(comps[right].nodes())] if right is not None else None
    ef = endpoint_features(d, comps[left], other)
    if method.startswith('rerank'):
        base = 'learned' if method == 'rerank_learned' else 'combo'
        cands = sorted([f for f in ef if not f['edge']], key=lambda f: -ostium_score(f, base))[:5]
        best = None
        for rank, f in enumerate(cands):
            lb, inf = label_left(d, comps[left], f['e'], lmin=lmin)
            pen = plausibility_penalty(d, inf, f)
            sc = ostium_score(f, base) - pen
            if best is None or sc > best[0]:
                best = (sc, f['e'], lb, inf, pen, rank)
        _, root, labL, info, pen, rank = best
        res['rerank_pen'] = pen; res['rerank_rank'] = rank
    else:
        root = max(ef, key=lambda f: ostium_score(f, method))['e']
        labL, info = label_left(d, comps[left], root, lmin=lmin)
    res['ostium_vox'] = d['V'][root].tolist()
    res.update({'L_' + k: v for k, v in info.items() if k != 'bif'})
    if info.get('bif') is not None:
        res['bif_vox'] = d['V'][info['bif']].tolist()
    for n, k in labL.items():
        lab[n] = k
    if right is not None:
        for n in comps[right].nodes():
            lab[n] = 4
        Tr, Lr, Sr, dr = rooted(comps[right], max(endpoint_features(d, comps[right], P[list(comps[left].nodes())]),
                                                   key=lambda f: ostium_score(f, 'r6'))['e'], P)
        res['rca_main_len'] = float(max(dr.values()))
        res['rca_tree_len'] = tl[right]
    res['left_tree_len'] = tl[left]
    # everything else: nearest labelled vertex
    done = lab > 0
    kd = cKDTree(P[done]); dl = lab[done]
    for k, G in comps.items():
        if k in (left, right):
            continue
        nodes = list(G.nodes())
        _, j = kd.query(P[nodes])
        lab[nodes] = np.bincount(dl[j], minlength=5).argmax()
    res['extra_skel_vox'] = int(d['CNT'][[n for k, G in comps.items() if k not in (left, right) for n in G.nodes()], 8].sum()) if len(comps) > 2 else 0
    # vertices dropped from a non-tree component (rare) get nearest label too
    miss = np.where(lab == 0)[0]
    if len(miss):
        _, j = kd.query(P[miss]); lab[miss] = dl[j]
    # orphans (no skeleton)
    olab = np.zeros(len(d['ORPH']), np.uint8)
    if len(d['ORPH']):
        _, j = kd.query(d['ORPH'][:, :3] * d['zooms']); olab = dl[j]
    res['orphan_vox'] = int(d['ORPH'][:, 3].sum()) if len(d['ORPH']) else 0
    return lab, olab, res, ef


def confusion(d, lab, olab):
    """rows: ICX class 0..7 (7 = no ICX vessel within 2 mm), cols: our class 0..4; counts are mask voxels"""
    C = np.zeros((8, 5), np.int64)
    for c in range(1, 5):
        C[:, c] += d['CNT'][lab == c, :8].sum(0)
    if len(d['ORPH']):
        for c in range(1, 5):
            C[:, c] += d['ORPH'][olab == c, 4:12].sum(0).astype(np.int64)
    return C


def dice_from_conf(C):
    """per-class Dice restricted to voxels whose ICX class is one of 1..4 (near, not IM/Other)"""
    M = C[1:5, 1:5].astype(float)
    out = {}
    for k in range(4):
        tp = M[k, k]; den = M[k, :].sum() + M[:, k].sum()
        out[NAMES[k + 1]] = (2 * tp / den) if den > 0 else np.nan
    out['acc'] = np.trace(M) / max(M.sum(), 1)
    return out
