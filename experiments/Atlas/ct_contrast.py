"""What does resampling the CT to coarser isotropic spacing do to the coronary trunks the model must see?
For the 32 CT-cached cases that have ImageCAS-X labels: crop CT around the tree, resample (cubic spline, no
anti-aliasing, like nnU-Net's image resampling) to 0.5 / 0.7 mm isotropic and back to native, then measure, at
centreline (skeleton) points of the 4 trunk classes binned by lumen radius:
  contrast = centre HU - local background HU (median HU in a 1.0-2.5 mm shell outside the lumen)
  retention = contrast_after / contrast_native ; noise = MAD of high-pass residual in the shell.
Usage: ct_contrast.py <out.jsonl>"""
import os, sys, glob, json
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
W = SCR + '/work/Atlas'
out = sys.argv[1]
excl = set(int(x) for x in open(W + '/icx/exclude.txt').read().split())
cases = sorted(f[:5] for f in os.listdir(SCR + '/data/ct') if f.endswith('.nii.gz'))
cases = [c for c in cases if int(c[1:]) + 1 not in excl]
done = set()
if os.path.exists(out): done = {json.loads(l)['case'] for l in open(out)}
TRUNK = {1: 'LM', 2: 'LAD', 3: 'LCx', 9: 'RCA'}
BINS = [0, 0.6, 0.9, 1.3, 9]
def rt(x, sp, t):
    lo = ndi.zoom(x, sp / t, order=3, mode='nearest')
    return ndi.zoom(lo, np.array(x.shape) / np.array(lo.shape), order=3, mode='nearest')
def hp_mad(x, sp):
    r = x - ndi.gaussian_filter(x, sigma=1.0 / sp)
    return r
with open(out, 'a') as fo:
    for c in cases:
        if c in done: continue
        lp = W + '/icx/%d.coronary.nii.gz' % (int(c[1:]) + 1)
        if not os.path.exists(lp): continue
        li = nib.load(lp); lab = np.asarray(li.dataobj).astype(np.uint8)
        ct = nib.load(SCR + '/data/ct/%s.nii.gz' % c)
        sp = np.array(li.header.get_zooms()[:3], float)
        assert np.allclose(ct.affine, li.affine, atol=1e-3), c
        idx = np.nonzero(lab); m = np.ceil(10 / sp).astype(int)
        lo = np.maximum([i.min() for i in idx] - m, 0); hi = np.minimum([i.max() + 1 for i in idx] + m, lab.shape)
        sl = tuple(slice(a, b) for a, b in zip(lo, hi))
        lab = lab[sl]; img = np.asarray(ct.dataobj[sl], dtype=np.float32)
        lumen = lab > 0
        rad = ndi.distance_transform_edt(lumen, sampling=sp)
        dout = ndi.distance_transform_edt(~lumen, sampling=sp)
        shell = (dout >= 1.0) & (dout <= 2.5)
        sk = skeletonize(lumen) & np.isin(lab, list(TRUNK))
        # local background: median shell HU within ~6 mm, via nearest-shell lookup on a smoothed map
        shell_vals = np.where(shell, img, np.nan)
        # approximate local median by per-skeleton-point neighbourhood: use uniform filter of shell HU (mean) as proxy
        k = np.ceil(6 / sp).astype(int) | 1
        num = ndi.uniform_filter(np.where(shell, img, 0), size=k); den = ndi.uniform_filter(shell.astype(np.float32), size=k)
        bg = num / np.maximum(den, 1e-6)
        pts = np.argwhere(sk); r_pts = rad[sk]; cls = lab[sk]
        res = dict(case=c, sp=sp.tolist(), n_pts=int(len(pts)))
        imgs = {'native': img}
        for t in (0.5, 0.7):
            imgs[str(t)] = rt(img, sp, t)
        bgp = bg[sk]
        for nm, im in imgs.items():
            cen = im[sk]
            res['contrast_' + nm] = {}
            for name in TRUNK.values():
                pass
            noise = float(np.median(np.abs(hp_mad(im, sp)[shell])) * 1.4826)
            res['noise_' + nm] = noise
            d = {}
            for b0, b1 in zip(BINS[:-1], BINS[1:]):
                s = (r_pts >= b0) & (r_pts < b1)
                d[f'{b0}-{b1}'] = [int(s.sum()), float(np.mean(cen[s] - bgp[s])) if s.any() else None]
            res['contrast_' + nm] = d
            res['contrast_by_class_' + nm] = {TRUNK[k2]: float(np.mean(cen[cls == k2] - bgp[cls == k2])) if (cls == k2).any() else None for k2 in TRUNK}
        res['radius_pts_q'] = np.round(np.quantile(r_pts, [0.1, 0.25, 0.5, 0.75, 0.9]), 3).tolist()
        fo.write(json.dumps(res) + '\n'); fo.flush()
print('done')
