"""Amendment A4 dry run: what does using Bridge's frozen rule labeller (v3, rerank_learned + learned ostium
weights, 4 mm component bridging) as QA on the projected ImageCAS-X proxy cost and catch?
Proxy = ImageCAS-X class (territory mapping, Bridge's ICX4: D->LAD, OM/L-PDA/L-PLA->LCx, R-PDA/R-PLA->RCA)
projected onto our mask voxels within 2 mm (Bridge extract.py caches per-skeleton-vertex counts).
Per case: voxels where proxy (near, class 1-4) != labeller -> 'ignore'; their distance to the labeller's LM
bifurcation; case flags (LM disagreement, ostium error > 5 mm vs ICX-derived ostium, LAD/LCx swap > 5 %).
Uses Bridge's code read-only. Usage: proxy_qa.py <out.jsonl>"""
import sys, os, glob, json
import numpy as np
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, '/home/user/Asclepius/experiments/Bridge')
import label as Lb
Lb.BRIDGE = 4.0
w = json.load(open(SCR + '/work/Bridge/ostium_w_dev2.json'))
Lb.OSTIUM_W = dict(F=w['F'], mean=np.array(w['mean']), scale=np.array(w['scale']), coef=np.array(w['coef']))
dev = set(open(SCR + '/work/Bridge/devset3.txt').read().replace('\n', '').split(','))
out = open(sys.argv[1], 'w')
for f in sorted(glob.glob(SCR + '/work/Bridge/ex/c*.npz')):
    c = os.path.basename(f)[:5]
    d = Lb.load_case(f)
    if d['icx_stats'] is None: continue
    try:
        lab, olab, res, ef = Lb.label_case(d, 'rerank_learned')
    except Exception as e:
        out.write(json.dumps(dict(case=c, fail=repr(e)[:100])) + '\n'); continue
    CNT = d['CNT']; P = d['P']
    near = CNT[:, 1:5]                       # proxy voxels per vertex with ICX class 1..4
    tot_near = near.sum(); tot = CNT[:, 8].sum()
    agree = np.array([near[i, lab[i] - 1] if 1 <= lab[i] <= 4 else 0 for i in range(len(lab))])
    dis = near.sum(1) - agree                # voxels at vertex i where proxy != labeller
    r = dict(case=c, held_out=c not in dev, nvox=int(tot), near_vox=int(tot_near), ignore_vox=int(dis.sum()),
             ignore_frac_of_mask=float(dis.sum() / tot), ignore_frac_of_near=float(dis.sum() / max(tot_near, 1)))
    # per proxy class: fraction ignored
    r['ignore_by_proxy_class'] = {}
    for k, nm in Lb.NAMES.items():
        tk = near[:, k - 1].sum()
        r['ignore_by_proxy_class'][nm] = float((near[:, k - 1] * (lab != k)).sum() / tk) if tk else None
    if 'bif_vox' in res:
        b = np.asarray(res['bif_vox']) * d['zooms']; dd = np.linalg.norm(P - b, axis=1)
        r['ignore_within_10mm_bif'] = float(dis[dd < 10].sum() / max(dis.sum(), 1))
        r['ignore_within_20mm_bif'] = float(dis[dd < 20].sum() / max(dis.sum(), 1))
    # case flags
    lm_p = near[:, 0].sum(); lm_l = near[lab == 1].sum() if (lab == 1).any() else 0
    lm_agree = near[lab == 1, 0].sum()
    r['lm_dice'] = float(2 * lm_agree / max(lm_p + (CNT[lab == 1, 8].sum()), 1))
    ladlcx = near[:, 1:3].sum(); swap = near[lab == 3, 1].sum() + near[lab == 2, 2].sum()
    r['ladlcx_swap'] = float(swap / max(ladlcx, 1))
    r['ostium_err'] = None
    cnt = CNT[:, 1:4]; maj = np.where(cnt.sum(1) > 0, cnt.argmax(1) + 1, 0)
    Mv = np.where(maj == 1)[0]; Bv = np.where((maj == 2) | (maj == 3))[0]
    if len(Mv) and len(Bv):
        from scipy.spatial import cKDTree
        dist = cKDTree(P[Bv]).query(P[Mv])[0]; ost = P[Mv[np.argmax(dist)]]
        r['ostium_err'] = float(np.linalg.norm(np.asarray(res['ostium_vox']) * d['zooms'] - ost))
    r['flag'] = bool(r['lm_dice'] < 0.5 or (r['ostium_err'] is not None and r['ostium_err'] > 5) or r['ladlcx_swap'] > 0.05)
    r['fail'] = res.get('fail')
    out.write(json.dumps(r) + '\n'); out.flush()
