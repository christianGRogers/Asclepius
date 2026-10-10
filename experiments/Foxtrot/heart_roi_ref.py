"""Foxtrot, round 6: does the ImageCAS reference coronary mask lie inside a TotalSegmentator heart+aorta ROI?

For each non-sealed case with a cached CT:
  1. resample the CT to 3 mm (TotalSegmentator's own fast-model spacing; keeps RSS small),
  2. TotalSegmentator fast (3 mm), roi_subset = heart, aorta  (CPU),
  3. upsample the ROI mask to a 1 mm grid, Euclidean distance (mm) to the ROI,
  4. for every reference (Girder/ImageCAS) mask voxel, its distance to the ROI (trilinear-free: nearest 1 mm cell),
     and per connected component (26-conn) of the reference, its MIN distance to the ROI
     (a component-level ROI filter deletes a component only if all of it lies beyond d).
Writes one JSON line per case. Usage:
  TOTALSEG_HOME_DIR=$SCR/tshome nice -n 10 python3 heart_roi_ref.py OUT.jsonl c0000 c0025 ...
"""
import os, sys, json, time, tempfile
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import ct_path, mask_path


def resample(arr, sp, new, order):
    f = np.asarray(sp, float) / new
    return ndi.zoom(arr, f, order=order, prefilter=False)


def run(c, tmpdir):
    from totalsegmentator.python_api import totalsegmentator
    ci = nib.load(ct_path(c)); sp = np.array(ci.header.get_zooms()[:3], float)
    ct = np.asanyarray(ci.dataobj).astype(np.float32)
    ct3 = resample(ct, sp, 3.0, 1); del ct
    A3 = ci.affine.copy(); A3[:3, :3] = ci.affine[:3, :3] @ np.diag(3.0 / sp)
    p = os.path.join(tmpdir, f'{c}_3mm.nii.gz')
    nib.save(nib.Nifti1Image(ct3.astype(np.int16), A3), p)
    seg = totalsegmentator(p, None, fast=True, roi_subset=['heart', 'aorta'], device='cpu',
                           nr_thr_resamp=1, nr_thr_saving=1, quiet=True, ml=True)
    s = np.asanyarray(seg.dataobj)
    os.remove(p)
    # TotalSegmentator v2 class ids: heart=51, aorta=52 (multilabel output); keep both explicitly
    roi3 = np.isin(s, [51, 52]); heart_vox = int((s == 51).sum()); aorta_vox = int((s == 52).sum())
    roi1 = resample(roi3.astype(np.float32), [3.0] * 3, 1.0, 1) > 0.5
    dist1 = ndi.distance_transform_edt(~roi1)  # mm, on 1 mm grid
    m = np.asanyarray(nib.load(mask_path(c)).dataobj) > 0
    lab, n = ndi.label(m, structure=np.ones((3, 3, 3)))
    idx = np.argwhere(m)
    # voxel -> 1 mm grid index (same origin, axis-aligned)
    g = np.floor(idx * sp[None, :] / 1.0).astype(int)
    g = np.minimum(g, np.array(dist1.shape) - 1)
    d = dist1[g[:, 0], g[:, 1], g[:, 2]]
    comp = lab[idx[:, 0], idx[:, 1], idx[:, 2]]
    comps = []
    for k in range(1, n + 1):
        sel = comp == k
        comps.append({'size': int(sel.sum()), 'min_d': float(d[sel].min()), 'max_d': float(d[sel].max())})
    res = {'case': c, 'spacing': sp.round(3).tolist(), 'heart_vox3mm': heart_vox, 'aorta_vox3mm': aorta_vox,
           'n_ref_vox': int(m.sum()), 'n_comp': n, 'comps': comps,
           'frac_vox_beyond': {str(t): float((d > t).mean()) for t in (0, 2, 5, 10, 15, 20)},
           'vox_beyond': {str(t): int((d > t).sum()) for t in (0, 2, 5, 10, 15, 20)},
           'max_d': float(d.max()), 'p99_d': float(np.percentile(d, 99))}
    return res


if __name__ == '__main__':
    out = sys.argv[1]
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)['case'] for l in open(out)}
    with tempfile.TemporaryDirectory(dir=SCR + '/work/Foxtrot') as td:
        for c in sys.argv[2:]:
            if c in done:
                continue
            t = time.time()
            try:
                r = run(c, td)
            except Exception as e:  # keep going
                r = {'case': c, 'error': repr(e)}
            r['sec'] = round(time.time() - t, 1)
            with open(out, 'a') as f:
                f.write(json.dumps(r) + '\n')
            print(c, r.get('max_d'), r.get('sec'), flush=True)
