"""E6: are the reference labels themselves topologically 'clean'?  Can a label-consistency
rule ("each branch = one connected piece, attached to its parent") be imposed without
damaging correct labels?

Usage: python icx_topology.py <out.jsonl> [case ...]   (default: every case with an ImageCAS-X file)

Per ImageCAS-X case: lumen components (26-conn) and their sizes; for the 4-class mapping
under both conventions (subtree: side branches inherit the trunk; trunk: only LM/LAD/LCx/RCA),
per-class presence, voxel count, component count and sizes; parent attachment
(LAD-LM, LCx-LM face/edge/corner adjacency = 26-neighbourhood contact), and LAD-LCx contact.
Also the raw 14-class presence, and the component count of the project's original binary mask
for the same case (survey) for comparison.
"""
import json
import sys

import cc3d
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import treelib as T  # noqa: E402

S26 = np.ones((3, 3, 3), bool)


def comps(m):
    lab, n = cc3d.connected_components(m, connectivity=26, return_N=True)
    s = np.bincount(lab.ravel())[1:] if n else np.array([], int)
    return int(n), sorted(s.tolist(), reverse=True)[:6]


def touches(a, b):
    if not a.any() or not b.any():
        return None
    sl = ndi.find_objects(a.astype(np.uint8))[0]
    sl = tuple(slice(max(x.start - 1, 0), x.stop + 1) for x in sl)
    return bool((ndi.binary_dilation(a[sl], S26) & b[sl]).any())


def run(case):
    p = T.icx_path(case)
    img = nib.load(p)
    raw = np.asanyarray(img.dataobj).astype(np.uint8)
    m = raw > 0
    idx = [np.nonzero(m.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    sl = tuple(slice(max(a[0] - 3, 0), a[-1] + 4) for a in idx)
    raw = raw[sl]; m = m[sl]
    r = dict(case=case, raw_present=[int(v) for v in np.unique(raw) if v],
             raw_vox={int(v): int((raw == v).sum()) for v in np.unique(raw) if v})
    r['lumen_ncomp'], r['lumen_sizes'] = comps(m)
    for conv, lutd in (('subtree', T.ICX_TO_4), ('trunk', T.ICX_TRUNK)):
        lut = np.zeros(256, np.uint8)
        for k, v in lutd.items():
            lut[k] = v
        lab = lut[raw]
        if conv == 'subtree':
            rest = m & (lab == 0)
            if rest.any():
                # 'Other' (D3/D4/OM3/OM4): nearest labelled voxel, computed inside the bbox of
                # the unassigned voxels grown by 15 voxels
                bb = ndi.find_objects(rest.astype(np.uint8))[0]
                bb = tuple(slice(max(x.start - 15, 0), x.stop + 15) for x in bb)
                sub = lab[bb]
                _, inds = ndi.distance_transform_edt(sub == 0, return_indices=True)
                rs = rest[bb]
                sub[rs] = sub[tuple(inds)][rs]
        d = {}
        for c in (1, 2, 3, 4):
            n, s = comps(lab == c)
            d[c] = dict(vox=int((lab == c).sum()), ncomp=n, sizes=s)
        d['lad_lm'] = touches(lab == 2, lab == 1)
        d['lcx_lm'] = touches(lab == 3, lab == 1)
        d['lad_lcx'] = touches(lab == 2, lab == 3)
        d['rca_left'] = touches(lab == 4, (lab >= 1) & (lab <= 3))
        r[conv] = d
    return r


if __name__ == '__main__':
    out = sys.argv[1]
    cases = sys.argv[2:]
    if not cases:
        mp = json.load(open(T.ICX_MAP_FILE))
        cases = sorted(c for c in mp if T.icx_path(c))[::int(__import__('os').environ.get('STRIDE', '1'))]
    with open(out, 'a') as f:
        for c in cases:
            try:
                r = run(c)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            f.write(json.dumps(r) + '\n'); f.flush()
