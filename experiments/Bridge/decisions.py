"""Are naming disagreements between two independent namings of the SAME lumen concentrated in a few discrete
decisions (ostium, LM end, which child is LAD/LCx), or diffuse?  Stand-in for the two-read question (D2):
'read A' = ImageCAS-X names projected onto our thick mask (territory, ramus -> LCx),
'read B' = the frozen rule namer (ramus -> LCx). Both on the cached skeletons from extract.py.

Per case, decisions are extracted from each labelled skeleton the same way:
  ostium  = LM-labelled vertex farthest from any LAD/LCx-labelled vertex
  LM end  = LM-labelled vertex nearest to the LAD/LCx-labelled vertices
  LAD/LCx = which side of the bifurcation each class occupies (swap = majority of A's LAD is B's LCx or vice versa)
A decision disagrees if ostium or LM end differ by > 5 mm, or a swap is present.
Every disagreeing voxel (near ImageCAS-X, classes LM..RCA) is attributed to:
  'band'      within 3 mm (Euclidean) of either naming's LM end   (the carina convention)
  'decision'  in a case where some decision disagrees (outside the band)
  'diffuse'   otherwise
usage: decisions.py EXDIR OSTIUM_W.json OUT.json
"""
import sys, os, glob, json, numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb


def extract(P, lab):
    lm = np.where(lab == 1)[0]; ll = np.where((lab == 2) | (lab == 3))[0]
    if not len(lm) or not len(ll):
        return None
    d, j = cKDTree(P[ll]).query(P[lm])
    return dict(ostium=P[lm[np.argmax(d)]], lmend=P[lm[np.argmin(d)]])


if __name__ == '__main__':
    ex, ostw, outp = sys.argv[1:4]
    w = json.load(open(ostw)); Lb.OSTIUM_W = dict(F=w['F'], mean=np.array(w['mean']), scale=np.array(w['scale']), coef=np.array(w['coef']))
    Lb.RAMUS = 'LCx'; Lb.BRIDGE = 4.0
    tot = dict(band=0, decision=0, diffuse=0, agree=0); tot3 = dict(decision=0, diffuse=0)
    rows = []
    for f in sorted(glob.glob(ex + '/c*.npz')):
        d = Lb.load_case(f)
        if d['icx_stats'] is None:
            continue
        lab, olab, res, ef = Lb.label_case(d, 'rerank_learned')
        cnt = d['CNT'][:, :8].astype(float)
        cnt[:, 3] += cnt[:, 5]            # ramus -> LCx (D1b)
        near = cnt[:, 1:5]                 # near voxels per class 1..4
        prox = np.where(near.sum(1) > 0, near.argmax(1) + 1, 0)
        P = d['P']
        a, b = extract(P, prox), extract(P, lab.astype(int))
        if a is None or b is None:
            continue
        sel = prox > 0
        # LAD/LCx swap: majority of A-LAD vertices named LCx by B, or vice versa (voxel weighted)
        def frac(x, y):
            m = sel & (prox == x); wgt = near[m].sum(1)
            return float(wgt[lab[m] == y].sum() / max(wgt.sum(), 1))
        swap = frac(2, 3) > 0.5 or frac(3, 2) > 0.5
        # tree identity (left vs right): A's RCA mostly named left-tree by B, or A's left tree named RCA
        tree_sw = (1 - frac(4, 4)) > 0.5 or max(frac(1, 4), frac(2, 4), frac(3, 4)) > 0.5
        # ramus: ImageCAS-X IM voxels (raw column 5) mostly not named LCx by B
        imw = d['CNT'][:, 5].astype(float)
        ram_dis = imw.sum() > 0 and float(imw[lab != 3].sum() / imw.sum()) > 0.5
        d_ost = float(np.linalg.norm(a['ostium'] - b['ostium'])); d_end = float(np.linalg.norm(a['lmend'] - b['lmend']))
        dec3 = d_ost > 5 or d_end > 5 or swap          # the three decisions as first pre-registered
        dec = dec3 or tree_sw or ram_dis                 # + tree identity + ramus (the full decision list)
        # voxel attribution: each vertex carries near[v, prox] voxels of A's class; disagreement if B's label differs
        wv = near[np.arange(len(prox)), np.clip(prox - 1, 0, 3)] * sel
        dis = sel & (lab != prox)
        inband = (np.linalg.norm(P - a['lmend'], axis=1) <= 3) | (np.linalg.norm(P - b['lmend'], axis=1) <= 3)
        band = float(wv[dis & inband].sum()); rest = float(wv[dis & ~inband].sum())
        tot['band'] += band; tot['agree'] += float(wv[sel & ~dis].sum())
        tot['decision' if dec else 'diffuse'] += rest
        tot3['decision' if dec3 else 'diffuse'] += rest
        rows.append(dict(case=os.path.basename(f)[:5], d_ost=d_ost, d_end=d_end, swap=bool(swap), tree_swap=bool(tree_sw),
                         ramus_dis=bool(ram_dis), decision_disagree=bool(dec), decision3=bool(dec3),
                         band=band, rest=rest, total=float(wv.sum())))
    n = len(rows); dis_tot = tot['band'] + tot['decision'] + tot['diffuse']
    summ = dict(cases=n, decision_disagree_cases=sum(r['decision_disagree'] for r in rows),
                ostium_gt5=sum(r['d_ost'] > 5 for r in rows), lmend_gt5=sum(r['d_end'] > 5 for r in rows),
                swaps=sum(r['swap'] for r in rows),
                disagree_frac_of_voxels=dis_tot / (dis_tot + tot['agree']),
                share_band=tot['band'] / dis_tot, share_decision=tot['decision'] / dis_tot, share_diffuse=tot['diffuse'] / dis_tot,
                share_decision_3only=tot3['decision'] / dis_tot, share_diffuse_3only=tot3['diffuse'] / dis_tot,
                tree_swaps=sum(r['tree_swap'] for r in rows), ramus_disagree=sum(r['ramus_dis'] for r in rows),
                cases_with_IM=None,
                median_case_diffuse_frac=float(np.median([r['rest'] / max(r['total'], 1) for r in rows if not r['decision_disagree']])))
    summ = {k: (int(v) if isinstance(v, (np.integer, np.bool_)) else v) for k, v in summ.items()}
    print(json.dumps(summ, indent=1))
    json.dump(dict(summary=summ, rows=rows), open(outp, 'w'))
