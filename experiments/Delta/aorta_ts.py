"""Aorta masks with TotalSegmentator (fast 3 mm model, roi_subset=aorta, CPU) for the ostium rule.
Usage: TOTALSEG_HOME_DIR=... python aorta_ts.py <outdir> case [case ...]"""
import os, sys, time
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import ct_path
from totalsegmentator.python_api import totalsegmentator
if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for c in sys.argv[2:]:
        dest = f'{out}/{c}_aorta.nii.gz'
        if os.path.exists(dest):
            continue
        t = time.time()
        # memory: run on the CT cropped to the ImageCAS-X tree bbox + 40 mm (the ostia and aortic
        # root are inside it), then paste the mask back on the full grid
        import nibabel as nib, numpy as np
        sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
        import treelib as T
        ref = nib.load(T.icx_path(c)); sp = np.array(ref.header.get_zooms()[:3], float)
        m = np.asanyarray(ref.dataobj) > 0
        idx = [np.nonzero(m.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
        mv = np.ceil(40.0 / sp).astype(int)
        lo = np.maximum([a[0] for a in idx] - mv, 0); hi = np.minimum([a[-1] + 1 for a in idx] + mv, m.shape)
        ctimg = nib.load(ct_path(c))
        sub = np.asanyarray(ctimg.dataobj)[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
        A = ctimg.affine.copy(); A[:3, 3] = A[:3, :3] @ lo + A[:3, 3]
        tmp = f'{out}/_{c}_crop.nii.gz'
        nib.save(nib.Nifti1Image(sub.astype(np.int16), A), tmp)
        img = totalsegmentator(tmp, None, fast=True, roi_subset=['aorta'], device='cpu',
                               nr_thr_resamp=1, nr_thr_saving=1, quiet=True)
        os.remove(tmp)
        d = np.zeros(m.shape, np.uint8)
        d[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = (np.asanyarray(img.dataobj) > 0)
        nib.save(nib.Nifti1Image(d, ctimg.affine), dest)
        print(c, round(time.time() - t), 's', int(d.sum()), flush=True)
