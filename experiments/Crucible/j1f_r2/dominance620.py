"""Item 10: dominance of record on the 620, from ImageCAS-X's own labels (no Descriptors.xlsx: it lists every case,
the locked and sealed ones included, so it is not opened). Left-sided = an L-PDA (12) or L-PLA (13) voxel; right-sided =
an R-PDA (10) or R-PLA (11) voxel. Usage: dominance620.py <icx_dir> <split.json>"""
import json, os, sys
import numpy as np, nibabel as nib
d, S = sys.argv[1], json.load(open(sys.argv[2]))
cnt = {'left_only': 0, 'right_only': 0, 'both': 0, 'neither': 0, 'L-PDA': 0, 'L-PLA': 0}
for c in S['train620']:
    u = set(np.unique(np.asarray(nib.load(os.path.join(d, '%d.coronary.nii.gz' % (int(c[1:]) + 1))).dataobj)).tolist())
    L, Rr = bool(u & {12, 13}), bool(u & {10, 11})
    cnt['both' if L and Rr else 'left_only' if L else 'right_only' if Rr else 'neither'] += 1
    cnt['L-PDA'] += 12 in u; cnt['L-PLA'] += 13 in u
cnt['any_left'] = cnt['left_only'] + cnt['both']
print(json.dumps(cnt))
