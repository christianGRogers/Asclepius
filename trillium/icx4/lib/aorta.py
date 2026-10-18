"""Stage C2 (GPU): TotalSegmentator aorta masks (A1's ostium of record) for the open ImageCAS-X test cases only.
The case list is open-36 + dev-44 from lib/sealed.py (A14); a sealed case is never segmented. atlas2's pattern:
TotalSegmentator 'total' fast model, roi_subset=['aorta'], on the case's own grid; weights downloaded on the login
node into $TOTALSEG_HOME_DIR (compute nodes have no internet; usage statistics off). Runs in the TotalSegmentator
venv (ICX4_TSEG_VENV), not the training venv.
Idempotent: skips masks that exist. A case that fails twice is given up (scored provisional, A1a); until then the
stage exits 1 so the next job retries it.
Usage: aorta.py <workdir> <icx_dir> [gpu|cpu]   (writes <workdir>/aorta/<case>_aorta.nii.gz; exit 3 = refused)"""
import json
import os
import sys
import time

import numpy as np
import nibabel as nib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sealed  # noqa: E402

MAX_ATTEMPTS = 2


def cases_for_aorta(W, icx):
    """{case: ct_path} for open-36 + dev-44 present in cases/; never a sealed case."""
    S = sealed.load(f'{W}/sealed_test.json')
    L = json.load(open(f'{W}/layout.json'))['cases']
    g = sealed.scored_groups(S, sealed.icx_test_ids(icx), set(L))
    todo = sealed.refuse_sealed([c for k in sealed.GROUPS for c in g[k]], S, 'aorta')
    return {c: L[c]['ct'] for c in todo}


def segmenter(device):
    if os.environ.get('ICX4_FAKE_AORTA'):   # CPU self-test only, never on a cluster: CT above 500 HU
        def segment(ct_path, dest):
            img = nib.load(ct_path)
            a = (np.asanyarray(img.dataobj) > 500).astype(np.uint8)
            if not a.any():
                raise ValueError('empty aorta mask')
            nib.save(nib.Nifti1Image(a, img.affine), dest)
        return segment
    from totalsegmentator.python_api import totalsegmentator

    def segment(ct_path, dest):
        img = nib.load(ct_path)
        res = totalsegmentator(ct_path, None, fast=True, roi_subset=['aorta'], device=device,
                               nr_thr_resamp=2, nr_thr_saving=1, quiet=True)
        a = (np.asanyarray(res.dataobj) > 0).astype(np.uint8)
        if a.shape != img.shape[:3]:
            raise ValueError(f'aorta grid {a.shape} vs CT {img.shape[:3]}')
        if not a.any():
            raise ValueError('empty aorta mask')
        nib.save(nib.Nifti1Image(a, img.affine), dest)
    return segment


if __name__ == '__main__':
    W, icx = sys.argv[1], sys.argv[2]
    device = sys.argv[3] if len(sys.argv) > 3 else 'gpu'
    try:
        cases = cases_for_aorta(W, icx)
    except sealed.SealedError as e:
        print(f'[aorta] {e}', flush=True)
        sys.exit(3)
    out = f'{W}/aorta'
    os.makedirs(out, exist_ok=True)
    af = f'{out}/attempts.json'
    attempts = json.load(open(af)) if os.path.exists(af) else {}
    print(f'[aorta] {len(cases)} open cases (open-36 + dev-44; sealed never), device {device}', flush=True)
    segment = segmenter(device)
    done = fail = gave_up = 0
    for c in sorted(cases):
        dest = f'{out}/{c}_aorta.nii.gz'
        if os.path.exists(dest):
            done += 1
            continue
        if attempts.get(c, 0) >= MAX_ATTEMPTS:
            gave_up += 1
            continue
        t = time.time()
        try:
            segment(cases[c], dest + '.part.nii.gz')
            os.replace(dest + '.part.nii.gz', dest)
            done += 1
            print(f'[aorta] {c} {time.time() - t:.0f}s', flush=True)
        except Exception as e:  # one failure must not stop the run; after 2 the case is scored provisional (A1a)
            attempts[c] = attempts.get(c, 0) + 1
            json.dump(attempts, open(af, 'w'))
            fail += 1
            if attempts[c] >= MAX_ATTEMPTS:
                gave_up += 1
            print(f'[aorta] {c} FAILED (attempt {attempts[c]}): {e!r}'[:300], flush=True)
    print(f'[aorta] {done} masks present, {fail} failed now, {gave_up} given up (provisional), in {out}', flush=True)
    sys.exit(0 if done + gave_up == len(cases) else 1)
