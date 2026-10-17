"""E2 check: area-equivalent mean lumen diameter = 2*sqrt(V/(pi*L)), V = lumen volume (mm^3),
L = centreline length (mm) from conv.jsonl. Usage: python area_diam.py conv.jsonl"""
import json, sys
import nibabel as nib
import numpy as np
import treelib as T
for l in open(sys.argv[1]):
    r = json.loads(l)
    if 'error' in r:
        continue
    out = []
    for src, p in (('orig', T.mask_path(r['case'])), ('icx', T.icx_path(r['case']))):
        img = nib.load(p); vv = float(np.prod(img.header.get_zooms()[:3]))
        V = (np.asanyarray(img.dataobj) > 0.5).sum() * vv
        out.append(2 * np.sqrt(V / (np.pi * r[src]['skel_len_mm'])))
    print(r['case'], 'area-equiv mean diameter mm  orig %.2f  icx %.2f' % tuple(out))
