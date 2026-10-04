"""Cohort-wide geometry. Headers (shape, spacing, orientation) for all 1000 binary masks; mask statistics
(tree bounding box, foreground voxels, connected components) on every STRIDE-th case.
Usage: cohort_geometry.py <out.csv> [STRIDE]"""
import sys, os, csv
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import case_ids
out = sys.argv[1]
STRIDE = int(sys.argv[2]) if len(sys.argv) > 2 else 1
rows = []
for c in case_ids():
    p = os.path.join(SCR, 'data/masks', c + '.nii.gz')
    if not os.path.exists(p): continue
    im = nib.load(p)
    sp = [float(x) for x in im.header.get_zooms()[:3]]
    r = dict(case=c, nx=im.shape[0], ny=im.shape[1], nz=im.shape[2], sx=sp[0], sy=sp[1], sz=sp[2],
             ornt=''.join(nib.aff2axcodes(im.affine)))
    if int(c[1:]) % STRIDE == 0:
        m = np.asarray(im.dataobj, dtype=np.float32) > 0.5
        idx = np.nonzero(m)
        lo = [int(i.min()) for i in idx]; hi = [int(i.max()) for i in idx]
        lab, n = ndi.label(m)
        sizes = np.sort(np.bincount(lab.ravel())[1:])[::-1]
        r.update(bx=hi[0]-lo[0]+1, by=hi[1]-lo[1]+1, bz=hi[2]-lo[2]+1, fg=int(m.sum()), ncc=n,
                 cc1=int(sizes[0]), cc2=int(sizes[1]) if n > 1 else 0, cc3=int(sizes[2]) if n > 2 else 0,
                 zlo=lo[2], zhi=hi[2])
    rows.append(r)
    if len(rows) % 100 == 0: print(len(rows), flush=True)
keys = ['case','nx','ny','nz','sx','sy','sz','ornt','bx','by','bz','fg','ncc','cc1','cc2','cc3','zlo','zhi']
with open(out, 'w') as f:
    w = csv.DictWriter(f, fieldnames=keys, restval=''); w.writeheader(); w.writerows(rows)
print('done', len(rows))
