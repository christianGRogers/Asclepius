"""E1: cohort-wide survey of the binary masks: geometry, connectivity, tree ROI size.

Usage: python survey_masks.py <shard> <nshards> <out.jsonl>
For every mask: shape, spacing, foreground voxels, 26-connected components
(sizes, bbox), whole-tree bbox (vox, mm), ROI size with 10/20 mm margin.
"""
import json
import os
import sys

import cc3d
import nibabel as nib
import numpy as np

SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import case_ids, mask_path  # noqa: E402


def survey(case):
    img = nib.load(mask_path(case))
    sp = np.array(img.header.get_zooms()[:3], float)
    m = (np.asanyarray(img.dataobj) > 0.5).astype(np.uint8)
    shape = m.shape
    nz = np.nonzero(m.any(axis=(1, 2)))[0], np.nonzero(m.any(axis=(0, 2)))[0], np.nonzero(m.any(axis=(0, 1)))[0]
    lo = np.array([a[0] for a in nz]); hi = np.array([a[-1] for a in nz]) + 1
    sub = m[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    lab, n = cc3d.connected_components(sub, connectivity=26, return_N=True)
    sizes = np.bincount(lab.ravel())[1:]
    order = np.argsort(-sizes)
    comps = []
    stats = cc3d.statistics(lab)
    for i in order[:12]:
        bb = stats['bounding_boxes'][i + 1]
        cen = stats['centroids'][i + 1]
        comps.append(dict(size=int(sizes[i]),
                          centroid_vox=[float(c + lo[k]) for k, c in enumerate(cen)],
                          bbox_lo=[int(bb[k].start + lo[k]) for k in range(3)],
                          bbox_hi=[int(bb[k].stop + lo[k]) for k in range(3)]))
    ext_mm = (hi - lo) * sp
    roi = {}
    for marg in (0, 10, 20):
        mv = np.ceil(marg / sp).astype(int)
        a = np.maximum(lo - mv, 0); b = np.minimum(hi + mv, shape)
        roi[str(marg)] = dict(vox=[int(x) for x in (b - a)], frac=float(np.prod(b - a) / np.prod(shape)))
    aff = img.affine
    return dict(case=case, shape=[int(s) for s in shape], spacing=[float(s) for s in sp],
                axcodes=''.join(nib.aff2axcodes(aff)), fg=int(m.sum()), ncomp=int(n),
                comps=comps, tree_lo=lo.tolist(), tree_hi=hi.tolist(),
                tree_ext_mm=ext_mm.tolist(), roi=roi, dtype=str(img.get_data_dtype()))


if __name__ == '__main__':
    shard, nsh, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['case'] for l in open(out)}
    with open(out, 'a') as f:
        for c in case_ids()[shard::nsh]:
            if c in done:
                continue
            try:
                r = survey(c)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            f.write(json.dumps(r) + '\n'); f.flush()
