"""E4: can a coarse (1-2 mm) localiser find the ROI that a native-resolution model needs?

Usage: python coarse_roi.py <out.jsonl> case [case ...]

The coarse-stage stand-in is the GT mask itself, area-downsampled to S mm isotropic
(block-mean via linear zoom of the float mask) and re-thresholded at t. This is an
*optimistic* localiser (a perfect coarse model); what it tests is whether the information
that survives at S mm is enough to place an ROI that contains the full native-resolution
tree. For each S in {1.0, 1.5, 2.0} and t in {0.5, 0.25}:
  surv_frac   : fraction of fine foreground voxels whose coarse cell survives
  ncomp       : 26-conn components of the coarse mask
  roi_recall  : fraction of fine foreground voxels inside the coarse bbox + margin (5/10/15 mm)
  roi_frac    : that ROI's volume as a fraction of the full CT volume
"""
import json
import sys
import time

import cc3d
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import mask_path  # noqa: E402


def run(case):
    img = nib.load(mask_path(case))
    sp = np.array(img.header.get_zooms()[:3], float)
    m = (np.asanyarray(img.dataobj) > 0.5)
    shape = np.array(m.shape)
    fine_pts = np.argwhere(m)
    res = dict(case=case, fg=int(len(fine_pts)))
    mf = m.astype(np.float32)
    for S in (1.0, 1.5, 2.0):
        z = sp / S
        c = ndi.zoom(mf, z, order=1, prefilter=False)
        for t in (0.5, 0.25):
            cm = c >= t
            key = f'{S}_{t}'
            if not cm.any():
                res[key] = dict(empty=True); continue
            n = cc3d.connected_components(cm, connectivity=26, return_N=True)[1]
            # map fine voxels to coarse cells
            ci = np.minimum((fine_pts * z).astype(int), np.array(cm.shape) - 1)
            surv = cm[tuple(ci.T)].mean()
            idx = np.argwhere(cm)
            lo_mm = idx.min(0) * S; hi_mm = (idx.max(0) + 1) * S
            d = dict(surv_frac=float(surv), ncomp=int(n))
            for marg in (5, 10, 15):
                lo = np.maximum(np.floor((lo_mm - marg) / sp), 0).astype(int)
                hi = np.minimum(np.ceil((hi_mm + marg) / sp), shape).astype(int)
                inside = np.all((fine_pts >= lo) & (fine_pts < hi), axis=1).mean()
                d[f'roi_recall_{marg}'] = float(inside)
                d[f'roi_frac_{marg}'] = float(np.prod(hi - lo) / np.prod(shape))
                d[f'roi_vox_{marg}'] = (hi - lo).tolist()
            res[key] = d
    return res


if __name__ == '__main__':
    out = sys.argv[1]
    with open(out, 'a') as f:
        for case in sys.argv[2:]:
            t = time.time()
            try:
                r = run(case)
            except Exception as e:  # noqa
                r = dict(case=case, error=repr(e))
            f.write(json.dumps(r) + '\n'); f.flush()
            print(case, round(time.time() - t), flush=True)
