"""TotalSegmentator aorta masks (A1's ostium of record) for a list of cases, on the case's own grid.
TotalSegmentator 'total' fast model (3 mm), roi_subset=['aorta']; weights are downloaded on the login node into
$TOTALSEG_HOME_DIR (compute nodes have no internet; usage statistics are switched off in its config.json).
Idempotent: skips masks that exist. Refuses any sealed case (A14).
Usage: aorta.py <out_dir> <cases.json {case: ct_path}> <sealed_test.json> [cpu|gpu]"""
import json
import os
import sys
import time

import numpy as np
import nibabel as nib

out, cases_json, sealed_json = sys.argv[1], sys.argv[2], sys.argv[3]
device = sys.argv[4] if len(sys.argv) > 4 else 'gpu'
os.makedirs(out, exist_ok=True)
cases = json.load(open(cases_json))
S = json.load(open(sealed_json))
sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
bad = sorted(set(cases) & sealed)
if bad:
    sys.exit(f'[aorta] REFUSING: sealed cases requested: {bad[:5]}')

if os.environ.get('ATLAS2_FAKE_AORTA'):   # CPU self-test only: a box above the reference tree, never on Trillium
    def segment(ct_path, dest):
        img = nib.load(ct_path); a = np.zeros(img.shape[:3], np.uint8)
        x, y, z = (s // 2 for s in a.shape); a[x - 20:x + 20, y - 20:y + 20, z:] = 1
        nib.save(nib.Nifti1Image(a, img.affine), dest)
else:
    from totalsegmentator.python_api import totalsegmentator

    def segment(ct_path, dest):
        img = nib.load(ct_path)
        res = totalsegmentator(ct_path, None, fast=True, roi_subset=['aorta'], device=device,
                               nr_thr_resamp=2, nr_thr_saving=1, quiet=True)
        a = (np.asanyarray(res.dataobj) > 0).astype(np.uint8)
        if a.shape != img.shape[:3]:
            raise ValueError(f'aorta grid {a.shape} vs CT {img.shape[:3]}')
        nib.save(nib.Nifti1Image(a, img.affine), dest)

done = fail = 0
for c in sorted(cases):
    dest = f'{out}/{c}_aorta.nii.gz'
    if os.path.exists(dest):
        done += 1
        continue
    t = time.time()
    try:
        segment(cases[c], dest + '.part.nii.gz')
        os.replace(dest + '.part.nii.gz', dest); done += 1
        print(f'[aorta] {c} {time.time() - t:.0f}s', flush=True)
    except Exception as e:  # one failure must not stop the run; the case is then scored provisional (A1a)
        fail += 1
        print(f'[aorta] {c} FAILED: {e!r}'[:300], flush=True)
print(f'[aorta] {done} masks present, {fail} failed, in {out}', flush=True)
