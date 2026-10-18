"""Stage C2 (GPU): TotalSegmentator aorta masks (A1's ostium of record) for every non-sealed ImageCAS-X case that is
scored: ImageCAS-X's val 80 (fold 0; the A26 decision set) + open-36 + dev-44 from lib/sealed.py (A14) = 160 cases.
A sealed case is never segmented. atlas2's pattern (so the val masks match atlas2's): TotalSegmentator 2.18.0 'total'
fast model, roi_subset=['aorta'], on the case's own grid; weights downloaded on the login node into
$TOTALSEG_HOME_DIR (compute nodes have no internet; usage statistics off). Runs in the TotalSegmentator venv
(ICX4_TSEG_VENV), not the training venv.
Idempotent: skips masks that exist. A case that fails twice is given up (scored provisional, A1a); until then the
stage exits 1 so the next job retries it.
Usage: aorta.py <workdir> <icx_dir> [gpu|cpu]   (writes <workdir>/aorta/<case>_aorta.nii.gz; exit 3 = refused)
       aorta.py plan <workdir> <icx_dir>        (print the case set and exit; the launcher's check, no numpy)"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sealed  # noqa: E402

MAX_ATTEMPTS = 2
N_VAL = 80
GROUPS = ('val80',) + sealed.GROUPS


def icx_val_ids(icx_dir):
    """ImageCAS-X's val split (fold 0; filelist/val.txt, 1-based ImageCAS ids) as case ids: exactly 80, distinct."""
    p = os.path.join(icx_dir, 'val.txt')
    try:
        ids = ['c%04d' % (int(x) - 1) for x in open(p).read().split()]
    except (OSError, ValueError) as e:
        raise sealed.SealedError(f'ImageCAS-X val list {p} is missing or unreadable ({e!r})') from e
    if len(ids) != N_VAL or len(set(ids)) != N_VAL:
        raise sealed.SealedError(f'ImageCAS-X val list {p} has {len(ids)} ids ({len(set(ids))} distinct), '
                                 f'not {N_VAL}; refusing')
    return ids


def aorta_groups(W, icx):
    """{'val80', 'open36', 'dev44': [case, ...]} restricted to cases/, sorted; never a sealed case (SealedError)."""
    S = sealed.load(f'{W}/sealed_test.json')
    L = json.load(open(f'{W}/layout.json'))['cases']
    test = sealed.icx_test_ids(icx)
    g = sealed.scored_groups(S, test, set(L))
    val = icx_val_ids(icx)
    if set(val) & set(test):
        raise sealed.SealedError(f'ImageCAS-X val and test overlap ({sorted(set(val) & set(test))[:3]}); refusing')
    out = {'val80': sorted(c for c in val if c in L), **g}
    sealed.refuse_sealed([c for k in GROUPS for c in out[k]], S, 'aorta')
    return out


def cases_for_aorta(W, icx):
    """{case: ct_path} for val-80 + open-36 + dev-44 present in cases/; never a sealed case."""
    L = json.load(open(f'{W}/layout.json'))['cases']
    g = aorta_groups(W, icx)   # refuses a sealed case
    return {c: L[c]['ct'] for k in GROUPS for c in g[k]}


def describe(W, icx):
    g = aorta_groups(W, icx)
    S = sealed.load(f'{W}/sealed_test.json')
    n_sealed = len({c for v in g.values() for c in v} & sealed.sealed_set(S))
    return (f'[icx4] aorta set: {sum(map(len, g.values()))} cases (val 80: {len(g["val80"])}, '
            f'open 36: {len(g["open36"])}, dev 44: {len(g["dev44"])}), sealed {n_sealed}')


def segmenter(device):
    import numpy as np
    import nibabel as nib
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
    if sys.argv[1:2] == ['plan']:
        try:
            print(describe(sys.argv[2], sys.argv[3]), flush=True)
        except sealed.SealedError as e:
            print(f'[icx4] ERROR: {e}', file=sys.stderr)
            sys.exit(3)
        sys.exit(0)
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
    print(f'[aorta] {len(cases)} cases (val-80 + open-36 + dev-44; sealed never), device {device}', flush=True)
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
