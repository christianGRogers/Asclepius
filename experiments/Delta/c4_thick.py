"""C4 (Round 3 ruling): re-read the bridge audit against the decided THICK reference.

Usage: python c4_thick.py <pred_dir> <aorta_dir> <out.jsonl> case [case ...]

Same first-pass predictions, anchors and 3 mm bridging as bridge_eval.py. For every bridge, report
whether the orphan touches the thin ImageCAS-X reference (the Round 2 'true join'), the thick
original ImageCAS mask (the binding reference, Human decisions D0), and what fraction of the
orphan's voxels lie inside the thick mask.
"""
import json
import sys

import cc3d
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import analyse_preds as A  # noqa: E402
import bridge_eval as BE  # noqa: E402
import postproc  # noqa: E402
import treelib as T  # noqa: E402

if __name__ == '__main__':
    pdir, adir, out = sys.argv[1:4]
    with open(out, 'a') as f:
        for case in sys.argv[4:]:
            meta = json.load(open(f'{pdir}/{case}_meta.json'))
            lo, hi = meta['lo'], meta['hi']
            prob = np.load(f'{pdir}/{case}_prob.npy').astype(np.float32)
            gt = A.CropGT(case, lo, hi)
            thick = (np.asanyarray(nib.load(T.mask_path(case)).dataobj) > 0.5)[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
            ao, kind = BE.anchor_structure(case, lo, hi, gt, adir)
            d_ao = ndi.distance_transform_edt(~ao, sampling=gt.sp) if ao.any() else None
            pred = A.remove_small(prob >= 0.5)
            lab = pred.astype(np.uint8)
            anchors = BE.anchor_components(pred, d_ao) if d_ao is not None else np.zeros_like(pred)
            _, br = postproc.bridge(lab, anchors, gt.sp, max_gap_mm=3.0, min_vox=100)
            cl = cc3d.connected_components(pred, connectivity=26)
            rows = []
            for b in br:
                comp = cl == cl[tuple(b['p'])]
                rows.append(dict(gap_mm=round(b['gap_mm'], 2), comp_vox=b['comp_vox'],
                                 touches_thin=bool((comp & gt.m).any()), touches_thick=bool((comp & thick).any()),
                                 frac_in_thick=round(float((comp & thick).sum() / comp.sum()), 3)))
            # also: how many raw predicted components are FP against thin vs thick reference
            ids = set(np.unique(cl[pred])) - {0}
            fp_thin = len(ids - set(np.unique(cl[pred & gt.m])))
            fp_thick = len(ids - set(np.unique(cl[pred & thick])))
            f.write(json.dumps(dict(case=case, bridges=rows, fp_comp_thin=fp_thin, fp_comp_thick=fp_thick,
                                    anchor=kind)) + '\n'); f.flush()
            print(case, 'done', flush=True)
