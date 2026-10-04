"""Cohort-level topology + ImageCAS vs ImageCAS-X lumen relationship, from extract.py caches and evaluate.py output."""
import sys, os, glob, json, numpy as np
ex, ev = sys.argv[1], sys.argv[2]
R = {json.loads(l)['case']: json.loads(l) for l in open(ev)}
rows = []
for f in sorted(glob.glob(os.path.join(ex, 'c*.npz'))):
    if f.endswith('.part.npz'):
        continue
    d = np.load(f); c = os.path.basename(f)[:5]
    cs = d['comp_sizes']; tot = cs.sum()
    r = R.get(c, {})
    rows.append(dict(case=c, n26=len(cs), n100=int((cs >= 100).sum()), n6=int(d['ncomp6']), top2=float(cs[:2].sum() / tot),
                     ntrees=r.get('n_trees'), zooms=d['zooms'].tolist(), shape=d['shape'].tolist(),
                     icx=json.loads(str(d['icx_stats'])) if 'icx_stats' in d else None, lr=r.get('lr_sep_x'),
                     f3=r.get('frac_vox_3mm_bif'), f5=r.get('frac_vox_5mm_bif'), lm=r.get('L_lm_len'),
                     pc2=r.get('pcont_2'), pc3=r.get('pcont_3'), nv2=r.get('never_2'), nv3=r.get('never_3')))
n = len(rows); print('cases', n)
a = lambda k: np.array([x[k] for x in rows])
for k in ('n26', 'n100', 'n6'):
    v = a(k); print(k, 'dist', {int(u): int((v == u).sum()) for u in np.unique(v)})
print('top2 comps hold >=99%% of voxels: %.3f; >=95%%: %.3f; min %.3f' % ((a('top2') >= .99).mean(), (a('top2') >= .95).mean(), a('top2').min()))
nt = np.array([x['ntrees'] for x in rows if x['ntrees'] is not None]); print('trees (>=30mm skeleton):', {int(u): int((nt == u).sum()) for u in np.unique(nt)})
z = np.array([x['zooms'] for x in rows]); print('xy spacing %.3f-%.3f median %.3f; z spacing values' % (z[:, 0].min(), z[:, 0].max(), np.median(z[:, 0])), np.unique(z[:, 2]))
sh = np.array([x['shape'] for x in rows]); print('z slices', sh[:, 2].min(), np.median(sh[:, 2]), sh[:, 2].max())
I = [x['icx'] for x in rows if x['icx']]
if I:
    inc = np.array([i['icx_in_ours'] / i['icx_in_crop'] for i in I]); near = np.array([i['ours_near'] / i['ours_nvox'] for i in I])
    ratio = np.array([i['ours_nvox'] / i['icx_nvox'] for i in I]); dice = 2 * np.array([i['icx_in_ours'] for i in I]) / np.array([i['icx_nvox'] + i['ours_nvox'] for i in I])
    print('ICX cases', len(I))
    print(' ICX voxels inside our mask: median %.3f p10 %.3f' % (np.median(inc), np.percentile(inc, 10)))
    print(' our voxels within 2 mm of an ICX vessel: median %.3f p10 %.3f' % (np.median(near), np.percentile(near, 10)))
    print(' our/ICX voxel ratio: median %.2f; binary Dice median %.3f IQR %.3f-%.3f' % (np.median(ratio), np.median(dice), *np.percentile(dice, [25, 75])))
    miss = np.array([i['icx_missed_by_ours'] for i in I]).sum(0); cls = np.array([i['icx_class_vox'] for i in I]).sum(0)
    print(' ICX voxels missed by our mask, per class (LM,LAD,LCx,RCA,IM,Other):', [round(m / max(c_, 1), 3) for m, c_ in zip(miss[1:], cls[1:])])
for k in ('f3', 'f5', 'lm'):
    v = np.array([x[k] for x in rows if x[k] is not None]); print(k, 'median %.3f p10 %.3f p90 %.3f' % (np.median(v), np.percentile(v, 10), np.percentile(v, 90)))
for k in ('pc2', 'pc3', 'nv2', 'nv3'):
    v = [x[k] for x in rows if x[k]]
    if v:
        print(k, {W: round(float(np.mean([q[W] for q in v])), 3) for W in v[0]})
