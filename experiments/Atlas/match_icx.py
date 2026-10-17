"""Match ImageCAS-X segmentation files (named by ImageCAS id) to our Girder case ids (c0000..c0999)
by NIfTI header signature (shape + affine). Writes icx_map.csv: case,icx_id,n_candidates."""
import os, sys, glob, csv
import numpy as np, nibabel as nib
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
W = SCR + '/work/Atlas'
def sig(p):
    h = nib.load(p).header
    return (tuple(int(x) for x in h.get_data_shape()[:3]),
            tuple(np.round(h.get_best_affine().ravel()[:12], 3)))
ours = {}
for p in sorted(glob.glob(SCR + '/data/masks/c*.nii.gz')):
    ours.setdefault(sig(p), []).append(os.path.basename(p)[:5])
rows = []
for p in sorted(glob.glob(W + '/icx/*.coronary.nii.gz')):
    i = int(os.path.basename(p).split('.')[0])
    try: s = sig(p)
    except Exception: continue
    c = ours.get(s, [])
    rows.append(dict(icx_id=i, case=c[0] if len(c) == 1 else '|'.join(c), n_candidates=len(c)))
with open(W + '/icx_map.csv', 'w') as f:
    w = csv.DictWriter(f, fieldnames=['icx_id', 'case', 'n_candidates']); w.writeheader(); w.writerows(rows)
from collections import Counter
print(len(rows), Counter(r['n_candidates'] for r in rows))
print(rows[:10])
