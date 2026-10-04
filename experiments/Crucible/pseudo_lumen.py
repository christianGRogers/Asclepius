# Can we manufacture a tight lumen from (Girder binary mask + CT) without any new labels?
# pseudo = our_mask & (HU > T), T fixed or adaptive (fraction of the 95th-percentile HU inside our mask, i.e. a
# half-maximum rule), optionally keeping only components that touch the two largest. Scored vs ImageCAS-X lumen
# on the cached CTs that have ICX labels. Also scores the raw Girder mask for reference.
import sys, os, json, numpy as np, nibabel as nib
from scipy import ndimage as ndi
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path
W = SCR + '/work/Crucible'


def dice(a, b): return float(2 * (a & b).sum() / (a.sum() + b.sum()))


def keep_big(p, n=2):
    lab, k = ndi.label(p, structure=np.ones((3, 3, 3)))
    if k <= n: return p
    sz = np.bincount(lab.ravel()); sz[0] = 0
    return np.isin(lab, np.argsort(sz)[::-1][:n])


rows = []
for i in [k + 1 for k in range(0, 1000, 25)]:
    f = W + f'/icx/ImageCAS-X_dataset/segmentations/{i}.coronary.nii.gz'; c = 'c%04d' % (i - 1)
    ctp = SCR + f'/data/ct/{c}.nii.gz'
    if not (os.path.exists(f) and os.path.exists(ctp)): continue
    L = np.asarray(nib.load(f).dataobj) > 0
    m = np.asarray(nib.load(mask_path(c)).dataobj) > 0.5
    u = np.argwhere(L | m); lo = np.maximum(u.min(0) - 4, 0); hi = u.max(0) + 5
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    ct = np.asarray(nib.load(ctp).dataobj[sl]).astype(np.float32); L = L[sl]; m = m[sl]
    r = {'id': i, 'case': c, 'raw': dice(m, L)}
    p95 = float(np.percentile(ct[m], 95)); r['p95'] = p95
    for T in (150, 200, 250, 300):
        r[f'T{T}'] = dice(m & (ct > T), L)
    for fr in (0.4, 0.5, 0.6):
        p = m & (ct > fr * p95); r[f'half{fr}'] = dice(p, L); r[f'half{fr}_big2'] = dice(keep_big(p), L)
        r[f'half{fr}_sens'] = float((p & L).sum() / L.sum()); r[f'half{fr}_prec'] = float((p & L).sum() / p.sum())
    rows.append(r); print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
json.dump(rows, open(W + '/pseudo_lumen.json', 'w'))
