# What are the voxels where our Girder binary mask (original ImageCAS label) and ImageCAS-X disagree?
# Uses the cached CTs (every 25th case) that are also in ImageCAS-X. Reports HU percentiles of:
#   both (agreed lumen), icx_only, ours_only_shell (<=1 voxel from ICX lumen), ours_only_near (2-5 vox),
#   ours_only_far (>5 vox from any ICX lumen: separate structures / untraced branches).
import sys, os, json, numpy as np, nibabel as nib
from scipy import ndimage as ndi
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path
W = SCR + '/work/Crucible'
rows = []
for i in [k + 1 for k in range(0, 1000, 25)]:
    f = W + f'/icx/ImageCAS-X_dataset/segmentations/{i}.coronary.nii.gz'; c = 'c%04d' % (i - 1)
    ctp = SCR + f'/data/ct/{c}.nii.gz'
    if not (os.path.exists(f) and os.path.exists(ctp)): continue
    L = np.asarray(nib.load(f).dataobj) > 0
    m = np.asarray(nib.load(mask_path(c)).dataobj) > 0.5
    u = np.argwhere(L | m); lo = np.maximum(u.min(0) - 8, 0); hi = u.max(0) + 9
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    ct = np.asarray(nib.load(ctp).dataobj[sl]).astype(np.float32); L = L[sl]; m = m[sl]
    d = ndi.distance_transform_edt(~L)
    groups = {'both': L & m, 'icx_only': L & ~m, 'ours_shell': m & ~L & (d <= 1.5),
              'ours_near': m & ~L & (d > 1.5) & (d <= 5), 'ours_far': m & ~L & (d > 5)}
    r = {'id': i, 'case': c}
    for k, g in groups.items():
        v = ct[g]; r[k] = {'n': int(g.sum()), 'p10': float(np.percentile(v, 10)) if len(v) else None,
                           'p50': float(np.median(v)) if len(v) else None, 'p90': float(np.percentile(v, 90)) if len(v) else None}
    rows.append(r); print(i, c, {k: (r[k]['n'], r[k]['p50']) for k in groups}, flush=True)
json.dump(rows, open(W + '/hu_disagreement.json', 'w'))
