"""Diagnostic (dev cases only): branches leaving near the LM bifurcation, their geometry, and whether
ImageCAS-X calls them IM (ramus). Used to design the A8/D1b ramus detector."""
import sys, os, glob, json, numpy as np, networkx as nx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb
ex, ostw, devf = sys.argv[1:4]
w = json.load(open(ostw)); Lb.OSTIUM_W = dict(F=w['F'], mean=np.array(w['mean']), scale=np.array(w['scale']), coef=np.array(w['coef']))
dev = set(open(devf).read().replace('\n', '').split(','))
rows = []
for f in sorted(glob.glob(ex + '/c*.npz')):
    c = os.path.basename(f)[:5]
    if c not in dev:
        continue
    d = Lb.load_case(f)
    if d['icx_stats'] is None:
        continue
    lab, olab, res, ef = Lb.label_case(d, 'rerank_learned')
    if 'bif_vox' not in res:
        continue
    comps = Lb.components(d)
    root = int(np.argmin(np.linalg.norm(d['V'] - np.array(res['ostium_vox']), axis=1)))
    k = d['CID'][root]; G = comps[int(k)]
    T, L, S, dist = Lb.rooted(G, root, d['P'])
    bif = int(np.argmin(np.linalg.norm(d['V'] - np.array(res['bif_vox']), axis=1)))
    R3 = d['A'][:3, :3] / d['zooms']
    kids = sorted(T.successors(bif), key=lambda x: -L[x])
    ys = {x: float((R3 @ (S[x] / L[x] - d['P'][bif]))[1]) for x in kids if L[x] > 0}
    # walk each of the two heaviest children 12 mm, list side branches >= 10 mm
    for c0 in kids[:2]:
        cur = c0
        while cur in T and dist[cur] - dist[bif] <= 12:
            ch = sorted(T.successors(cur), key=lambda x: -L[x])
            if not ch:
                break
            for sd in ch[1:]:
                if L[sd] < 10:
                    continue
                nodes = list(nx.descendants(T, sd) | {sd})
                cnt = d['CNT'][nodes, :8].sum(0)
                frac_im = cnt[5] / max(cnt[1:7].sum(), 1)
                a_ = float((R3 @ (S[sd] / L[sd] - d['P'][bif]))[1])
                ylad, ylcx = max(ys[kids[0]], ys[kids[1]]), min(ys[kids[0]], ys[kids[1]])
                rows.append(dict(case=c, off=dist[cur] - dist[bif], L=L[sd], rel=(a_ - ylcx) / max(ylad - ylcx, 1e-6),
                                 parent_is_lad=ys[c0] == ylad, im=frac_im, lab=int(lab[sd])))
            cur = ch[0]
for r in rows:
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
