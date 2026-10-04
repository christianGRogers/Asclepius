"""Header-only geometry of all 1000 binary masks (shape, spacing); writes headers.json used by planner_sweep.py.
Usage: header_stats.py <out headers.json>"""
import glob, json, sys
import numpy as np, nibabel as nib
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
S, SH = [], []
for p in sorted(glob.glob(SCR + '/data/masks/c*.nii.gz')):
    h = nib.load(p).header; S.append([float(x) for x in h.get_zooms()[:3]]); SH.append(list(h.get_data_shape()[:3]))
S, SH = np.array(S), np.array(SH)
json.dump(dict(sp=S.tolist(), sh=SH.tolist()), open(sys.argv[1], 'w'))
x = S[:, 0]
print(len(S), 'xy spacing min/median/max', x.min(), np.median(x), x.max(), 'z spacings', np.unique(S[:, 2]))
print('slices min/median/max', SH[:, 2].min(), np.median(SH[:, 2]), SH[:, 2].max(), '| >10% off 0.35:', int((abs(x / 0.35 - 1) > 0.1).sum()))
