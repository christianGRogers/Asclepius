"""Robustness of the rule labeller to stage-1-like errors, simulated on the cached skeleton graph:
  gaps: cut G random skeleton edges (length-weighted) in the two main trees and delete ~2 mm of skeleton
        around each cut -> the tree falls apart into fragments, as a stage-1 model with breaks would produce.
  prune: delete every terminal branch shorter than P mm (missed distal side branches).
Voxels owned by deleted vertices are dropped from scoring (stage-1 misses are stage-1's error, not naming's).
usage: perturb.py EXDIR OUT.jsonl METHOD
"""
import sys, os, glob, json, numpy as np, networkx as nx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb


def regraph(d, keep):
    """keep: boolean mask of vertices; rebuild E, CID, CNT, V... for the kept vertices"""
    idx = np.where(keep)[0]
    remap = -np.ones(len(keep), int); remap[idx] = np.arange(len(idx))
    E = d['E'][keep[d['E'][:, 0]] & keep[d['E'][:, 1]]]
    E = remap[E]
    G = nx.Graph(); G.add_nodes_from(range(len(idx))); G.add_edges_from(E.tolist())
    cid = np.zeros(len(idx), np.int32)
    for i, cc in enumerate(nx.connected_components(G)):
        cid[list(cc)] = i + 1
    e = dict(d)
    for k in ('V', 'R', 'CNT', 'P', 'RAS'):
        e[k] = d[k][idx]
    e['E'] = E.astype(np.int32); e['CID'] = cid
    return e


def gaps(d, n, rng, gap_mm=2.0):
    comps = Lb.components(d)
    tl = {k: sum(w for _, _, w in G.edges(data='w')) for k, G in comps.items()}
    trees = sorted(comps, key=lambda k: -tl[k])[:2]
    keep = np.ones(len(d['P']), bool)
    edges = [(a, b, w) for k in trees for a, b, w in comps[k].edges(data='w')]
    if not edges:
        return d
    w = np.array([x[2] for x in edges]); w /= w.sum()
    for i in rng.choice(len(edges), size=min(n, len(edges)), replace=False, p=w):
        a = edges[i][0]
        dd = np.linalg.norm(d['P'] - d['P'][a], axis=1)
        keep &= dd > gap_mm / 2
    return regraph(d, keep)


def prune(d, mm):
    comps = Lb.components(d)
    keep = np.ones(len(d['P']), bool)
    cnt = d['CNT'][:, 1:4]; is_lm = (cnt.argmax(1) == 0) & (cnt.sum(1) > 0)  # never prune the ostial (LM) end
    for k, G in comps.items():
        for e in [n for n in G if G.degree(n) == 1]:
            path, prev, cur, acc = [e], None, e, 0.0
            while True:
                nxt = [x for x in G.neighbors(cur) if x != prev]
                if len(nxt) != 1:
                    break
                acc += G[cur][nxt[0]]['w']; prev, cur = cur, nxt[0]
                if G.degree(cur) > 2:
                    break
                path.append(cur)
            if acc < mm and G.degree(cur) > 2 and not is_lm[path].any():
                keep[path] = False
    return regraph(d, keep)


if __name__ == '__main__':
    ex, outp, method, ostw, caselist = sys.argv[1:6]
    Lb.BRIDGE = float(os.environ.get('BRIDGE', 0))
    w = json.load(open(ostw)); Lb.OSTIUM_W = dict(F=w['F'], mean=np.array(w['mean']), scale=np.array(w['scale']), coef=np.array(w['coef']))
    keep = set(open(caselist).read().replace('\n', '').split(','))
    files = sorted(f for f in glob.glob(os.path.join(ex, 'c*.npz')) if not f.endswith('.part.npz') and os.path.basename(f)[:5] in keep)
    with open(outp, 'w') as fo:
        for f in files:
            d = Lb.load_case(f)
            if d['icx_stats'] is None:
                continue
            c = os.path.basename(f)[:5]
            for kind, lvl in [('gaps', 0), ('gaps', 1), ('gaps', 3), ('gaps', 6), ('prune', 10), ('prune', 25)]:
                rng = np.random.RandomState(int(c[1:]) * 7 + lvl)
                e = gaps(d, lvl, rng) if kind == 'gaps' else prune(d, lvl)
                try:
                    lab, olab, res, ef = Lb.label_case(e, method)
                    C = Lb.confusion(e, lab, olab)
                    dice = {k: (None if np.isnan(v) else float(v)) for k, v in Lb.dice_from_conf(C).items()}
                except Exception as ex_:
                    dice = None; res = dict(fail=repr(ex_)[:100])
                fo.write(json.dumps(dict(case=c, kind=kind, lvl=lvl, dice=dice, ncomp=int(e['CID'].max()),
                                         kept_vox=float(e['CNT'][:, 8].sum() / d['CNT'][:, 8].sum()), fail=res.get('fail'))) + '\n')
