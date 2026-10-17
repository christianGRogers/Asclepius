# Round 2, small-scale paired training experiment: data prep.
# For every cached CT with an ImageCAS-X label: crop to bbox(Girder mask U ICX lumen) + margin, save
#   ct.npy (int16), icx14.npy (uint8 0..14), thin4.npy (ICX lumen, territory 4-class), thick4.npy (Girder mask,
#   each voxel named by the nearest ICX voxel's territory class = Atlas's proxy without the geodesic step).
# Territory: LM=1; LAD,D1,D2 -> 2; LCx,OM1,OM2,L-PDA,L-PLA -> 3; RCA,R-PDA,R-PLA -> 4; IM / Other -> nearest of 2/3.
import os, sys, json, numpy as np, nibabel as nib
from scipy import ndimage as ndi
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path
W = SCR + '/work/Crucible'; OUT = W + '/r2data'; os.makedirs(OUT, exist_ok=True)
TERR = np.zeros(15, np.uint8); TERR[[1]] = 1; TERR[[2, 4, 5]] = 2; TERR[[3, 6, 7, 12, 13]] = 3; TERR[[9, 10, 11]] = 4
ex = {int(x) for x in open(W + '/icx/ImageCAS-X_dataset/filelist/exclude.txt').read().split()}
te = {int(x) for x in open(W + '/icx/ImageCAS-X_dataset/filelist/test.txt').read().split()}
meta = {}
for f in sorted(os.listdir(SCR + '/data/ct')):
    if not f.endswith('.nii.gz'): continue
    c = f[:5]; i = int(c[1:]) + 1
    if i in ex or os.path.exists(f'{OUT}/{c}_ct.npy'): continue
    L = np.asarray(nib.load(W + f'/icx/ImageCAS-X_dataset/segmentations/{i}.coronary.nii.gz').dataobj).astype(np.uint8)
    m = np.asarray(nib.load(mask_path(c)).dataobj) > 0.5
    u = np.argwhere((L > 0) | m); mg = np.array([16, 16, 12])
    lo = np.maximum(u.min(0) - mg, 0); hi = np.minimum(u.max(0) + mg + 1, L.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    ctimg = nib.load(SCR + '/data/ct/' + f)
    ct = np.asarray(ctimg.dataobj[sl]).astype(np.int16); L = L[sl]; m = m[sl]
    t4 = TERR[L]
    amb = (L == 8) | (L == 14)
    if amb.any():  # ramus / other -> nearest LAD/LCx territory voxel
        _, ind = ndi.distance_transform_edt(~np.isin(t4, (2, 3)), return_indices=True)
        t4[amb] = t4[tuple(ind)][amb]
    _, ind = ndi.distance_transform_edt(t4 == 0, return_indices=True)
    k4 = np.where(m, t4[tuple(ind)], 0).astype(np.uint8)
    np.save(f'{OUT}/{c}_ct.npy', ct); np.save(f'{OUT}/{c}_icx14.npy', L)
    np.save(f'{OUT}/{c}_thin4.npy', t4); np.save(f'{OUT}/{c}_thick4.npy', k4)
    meta[c] = {'id': i, 'test': i in te, 'lo': lo.tolist(), 'shape': list(ct.shape),
               'spacing': [float(x) for x in ctimg.header.get_zooms()[:3]]}
    print(c, ct.shape, 'test' if i in te else 'train', flush=True)
old = json.load(open(OUT + '/meta.json')) if os.path.exists(OUT + '/meta.json') else {}
old.update(meta); json.dump(old, open(OUT + '/meta.json', 'w'))
