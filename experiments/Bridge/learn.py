"""Light LEARNED stage 2: per-skeleton-vertex classifier (gradient boosting on root-independent geometric
features) + exact tree-structured MAP decoding under the anatomical grammar
    LM* -> (LAD subtree | LCx subtree)       (left tree),    RCA (right tree)
with the ostium chosen jointly as the root that minimises the decoding cost.

Labels for training: ImageCAS-X classes projected onto our skeleton vertices (majority of near voxels).
Label-efficiency curve: train on N cases, score voxel-wise on a fixed held-out set.

usage: learn.py EXDIR OUT.json
"""
import sys, os, glob, json, numpy as np, networkx as nx
from sklearn.ensemble import HistGradientBoostingClassifier
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb

ALLOWED = {1: (1, 2, 3), 2: (2,), 3: (3,)}


def case_graph(d):
    comps = Lb.components(d)
    tl = {k: sum(w for _, _, w in G.edges(data='w')) for k, G in comps.items()}
    trees = sorted([k for k in comps if tl[k] >= Lb.TREEMIN], key=lambda k: -tl[k])
    if len(trees) < 2:
        return None
    RAS = d['RAS']
    cx = {k: float(RAS[list(comps[k].nodes()), 0].mean()) for k in trees[:2]}
    left = min(trees[:2], key=lambda k: cx[k]); right = max(trees[:2], key=lambda k: cx[k])
    return comps, left, right


def vertex_features(d, G, cL, cR, scale):
    """root-independent features for every vertex of left tree G"""
    nodes = np.array(list(G.nodes()))
    RAS = d['RAS'][nodes]; R = d['R'][nodes]
    # local tangent (sign-free) from neighbours
    tang = np.zeros((len(nodes), 3))
    pos = {n: i for i, n in enumerate(nodes)}
    for i, n in enumerate(nodes):
        nb = list(G.neighbors(n))
        if len(nb) >= 1:
            v = d['RAS'][nb[0]] - d['RAS'][nb[-1]] if len(nb) >= 2 else d['RAS'][nb[0]] - d['RAS'][n]
            v = v / (np.linalg.norm(v) + 1e-9)
            tang[i] = v * np.sign(v[2] + 1e-9)
    deg = np.array([G.degree(n) for n in nodes])
    # radius smoothed over 2-hop neighbourhood
    rs = np.array([np.mean(d['R'][[n] + list(G.neighbors(n))]) for n in nodes])
    X = np.column_stack([(RAS - cL) / scale, (RAS - cR) / scale, RAS - cL, rs, deg, tang])
    return nodes, X


def vertex_labels(d, nodes):
    cnt = d['CNT'][nodes, 1:4]
    y = np.where(cnt.sum(1) > 0, cnt.argmax(1) + 1, 0)
    return y


def decode(G, nodes, logp, roots):
    """tree MAP under grammar for each candidate root; return best labelling and root"""
    idx = {n: i for i, n in enumerate(nodes)}
    best = None
    for r in roots:
        T = nx.bfs_tree(G, r)
        cost = {}
        arg = {}
        for n in nx.dfs_postorder_nodes(T, r):
            i = idx[n]
            c = np.zeros(4)
            kids = list(T.successors(n))
            for y in (2, 3):
                c[y] = -logp[i, y - 1] + sum(cost[ch][y] for ch in kids)
            # LM is a single path: at most one child continues LM, the others are LAD or LCx
            base = sum(min(cost[ch][2], cost[ch][3]) for ch in kids)
            gain = min([cost[ch][1] - min(cost[ch][2], cost[ch][3]) for ch in kids] + [0.0])
            c[1] = -logp[i, 0] + base + gain
            cost[n] = c
        # root must be LM
        tot = cost[r][1]
        if best is None or tot < best[0]:
            best = (tot, r, T, cost)
    tot, r, T, cost = best
    lab = {}
    stack = [(r, 1)]
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
    return lab, r


def prep(files):
    data = {}
    for f in files:
        d = Lb.load_case(f)
        if d['icx_stats'] is None:
            continue
        cg = case_graph(d)
        if cg is None:
            continue
        comps, left, right = cg
        G = comps[left]
        cL = d['RAS'][list(G.nodes())].mean(0); cR = d['RAS'][list(comps[right].nodes())].mean(0)
        scale = np.linalg.norm(cL - cR) + 1e-6
        nodes, X = vertex_features(d, G, cL, cR, scale)
        y = vertex_labels(d, nodes)
        w = d['CNT'][nodes, 1:4].sum(1)
        ef = Lb.endpoint_features(d, G, d['P'][list(comps[right].nodes())])
        data[os.path.basename(f)[:5]] = dict(d=d, comps=comps, left=left, right=right, nodes=nodes, X=X, y=y, w=w, ef=ef)
    return data


def score_case(D, labmap):
    d = D['d']; comps = D['comps']
    lab = np.zeros(len(d['P']), np.uint8)
    for n, y in labmap.items():
        lab[n] = y
    for n in comps[D['right']].nodes():
        lab[n] = 4
    done = lab > 0
    from scipy.spatial import cKDTree
    kd = cKDTree(d['P'][done]); dl = lab[done]
    miss = np.where(lab == 0)[0]
    if len(miss):
        _, j = kd.query(d['P'][miss]); lab[miss] = dl[j]
    olab = np.zeros(len(d['ORPH']), np.uint8)
    if len(d['ORPH']):
        _, j = kd.query(d['ORPH'][:, :3] * d['zooms']); olab = dl[j]
    C = Lb.confusion(d, lab, olab)
    return C


def run(data, train, test, K=8):
    Xtr = np.concatenate([data[c]['X'][data[c]['y'] > 0] for c in train])
    ytr = np.concatenate([data[c]['y'][data[c]['y'] > 0] for c in train])
    clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, max_leaf_nodes=31, random_state=0)
    clf.fit(Xtr, ytr)
    out = {}
    for c in test:
        D = data[c]
        p = np.full((len(D['nodes']), 3), 1e-4)
        p[:, [k - 1 for k in clf.classes_]] = clf.predict_proba(D['X'])
        logp = np.log(np.clip(p, 1e-4, 1))
        cands = sorted([f for f in D['ef'] if not f['edge']], key=lambda f: -Lb.ostium_score(f, 'learned'))[:K]
        labmap, root = decode(D['comps'][D['left']], D['nodes'], logp, [f['e'] for f in cands])
        out[c] = score_case(D, labmap)
    return out


if __name__ == '__main__':
    ex, outp, ostw, caselist = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    w = json.load(open(ostw)); Lb.OSTIUM_W = dict(F=w['F'], mean=np.array(w['mean']), scale=np.array(w['scale']), coef=np.array(w['coef']))
    keep = set(open(caselist).read().replace('\n', '').split(','))
    files = sorted(f for f in glob.glob(os.path.join(ex, 'c*.npz')) if not f.endswith('.part.npz') and os.path.basename(f)[:5] in keep)
    data = prep(files)
    cases = sorted(data)
    rng = np.random.RandomState(0)
    perm = list(rng.permutation(cases))
    ntest = len(perm) // 3
    test, pool = perm[:ntest], perm[ntest:]
    res = dict(n_cases=len(cases), n_test=len(test), curve={})
    rd = []
    for c in test:
        lab, olab, rr, ef = Lb.label_case(data[c]['d'], 'rerank_learned')
        rd.append(Lb.dice_from_conf(Lb.confusion(data[c]['d'], lab, olab)))
    res['rule'] = {k: float(np.nanmean([x[k] for x in rd])) for k in ('LM', 'LAD', 'LCx', 'RCA', 'acc')} | {
        'cases_all_ge_0.8': float(np.mean([all(x[k] >= 0.8 for k in ('LM', 'LAD', 'LCx', 'RCA') if not np.isnan(x[k])) for x in rd]))}
    print('rule v3 on same test:', res['rule'], flush=True)
    for N in [5, 10, 20, 40, 80, 160, 320]:
        if N > len(pool):
            break
        accs = []
        for rep in range(3 if N <= 40 else 1):
            tr = list(np.random.RandomState(rep).choice(pool, N, replace=False))
            sc = run(data, tr, test)
            dic = [Lb.dice_from_conf(C) for C in sc.values()]
            accs.append({k: float(np.nanmean([x[k] for x in dic])) for k in ('LM', 'LAD', 'LCx', 'RCA', 'acc')} |
                        {'cases_all_ge_0.8': float(np.mean([all(x[k] >= 0.8 for k in ('LM', 'LAD', 'LCx', 'RCA') if not np.isnan(x[k])) for x in dic]))})
        res['curve'][N] = {k: float(np.mean([a[k] for a in accs])) for k in accs[0]} | {'reps': len(accs)}
        print(N, res['curve'][N], flush=True)
    json.dump(dict(res, test=test), open(outp, 'w'))
