"""What window does nnU-Net's CTNormalization choose on this cohort, and what does it clip?
nnU-Net clips CT to the [0.5, 99.5] percentiles of *foreground* (labelled) voxel intensities pooled over the
training set, then z-scores. Here foreground = coronary lumen only. For each CT-cached case with an ImageCAS-X
label: lumen HU percentiles (ImageCAS-X lumen, and our original binary mask), and the fraction of voxels in a
heart-sized box around the tree that fall below the lower clip (i.e. become indistinguishable).
Usage: ct_norm_window.py <out.json>"""
import os, sys, json
import numpy as np, nibabel as nib
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
W = SCR + '/work/Atlas'
excl = set(int(x) for x in open(W + '/icx/exclude.txt').read().split())
cases = sorted(f[:5] for f in os.listdir(SCR + '/data/ct') if f.endswith('.nii.gz') and int(f[1:5]) + 1 not in excl)
rng = np.random.default_rng(0)
pool_icx, pool_ours, boxes, per = [], [], [], []
for c in cases:
    lp = W + '/icx/%d.coronary.nii.gz' % (int(c[1:]) + 1)
    if not os.path.exists(lp): continue
    lab = np.asarray(nib.load(lp).dataobj) > 0
    ours = np.asarray(nib.load(SCR + '/data/masks/%s.nii.gz' % c).dataobj, dtype=np.float32) > 0.5
    ct = np.asarray(nib.load(SCR + '/data/ct/%s.nii.gz' % c).dataobj, dtype=np.int16)
    a = ct[lab]; b = ct[ours]
    pool_icx.append(rng.choice(a, min(len(a), 10000), replace=False)); pool_ours.append(rng.choice(b, min(len(b), 10000), replace=False))
    idx = np.nonzero(lab); lo = [i.min() for i in idx]; hi = [i.max() + 1 for i in idx]
    box = ct[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]].ravel()
    boxes.append(rng.choice(box, 200000, replace=False))
    per.append(dict(case=c, icx_p=np.percentile(a, [0.5, 5, 50, 95, 99.5]).tolist(), ours_p=np.percentile(b, [0.5, 5, 50, 95, 99.5]).tolist()))
    print(c, per[-1], flush=True)
I = np.concatenate(pool_icx); O = np.concatenate(pool_ours); B = np.concatenate(boxes)
res = dict(n_cases=len(per), per_case=per)
for nm, P in [('icx_lumen', I), ('ours_binary', O)]:
    lo, hi = np.percentile(P, [0.5, 99.5])
    res[nm] = dict(clip_lo=float(lo), clip_hi=float(hi), median=float(np.median(P)),
                   box_frac_below_lo=float((B < lo).mean()), box_frac_above_hi=float((B > hi).mean()),
                   box_frac_in_fat=float(((B > -200) & (B < -30)).mean()), box_frac_softtissue_0_200=float(((B >= 0) & (B < 200)).mean()))
res['box_hu_percentiles'] = np.percentile(B, [1, 5, 25, 50, 75, 95, 99]).tolist()
json.dump(res, open(sys.argv[1], 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'per_case'}, indent=1))
