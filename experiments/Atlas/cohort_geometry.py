"""Cohort-wide geometry from all 1000 binary masks: shape, spacing, z-extent (mm), tree bounding box
(voxels and mm), foreground voxels, connected components. Writes CSV to argv[1]."""
import sys, os, csv
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import case_ids
out = sys.argv[1]
rows = []
for c in case_ids():
    p = os.path.join(SCR, 'data/masks', c + '.nii.gz')
    if not os.path.exists(p): continue
    im = nib.load(p)
    sp = im.header.get_zooms()[:3]
    m = np.asarray(im.dataobj, dtype=np.float32) > 0.5
    idx = np.nonzero(m)
    lo = [int(i.min()) for i in idx]; hi = [int(i.max()) for i in idx]
    lab, n = ndi.label(m, structure=np.ones((3, 3, 3)))
    sizes = np.sort(np.bincount(lab.ravel())[1:])[::-1]
    rows.append(dict(case=c, nx=m.shape[0], ny=m.shape[1], nz=m.shape[2], sx=sp[0], sy=sp[1], sz=sp[2],
                     bx=hi[0]-lo[0]+1, by=hi[1]-lo[1]+1, bz=hi[2]-lo[2]+1, fg=int(m.sum()), ncc=n,
                     cc1=int(sizes[0]), cc2=int(sizes[1]) if n > 1 else 0, cc3=int(sizes[2]) if n > 2 else 0,
                     zlo=lo[2], zhi=hi[2], ornt=''.join(nib.aff2axcodes(im.affine))))
    if len(rows) % 100 == 0: print(len(rows), flush=True)
with open(out, 'w') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('done', len(rows))
