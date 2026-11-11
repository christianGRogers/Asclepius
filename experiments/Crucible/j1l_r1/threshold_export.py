"""Crucible, Janus 1-L Round 1: export a segmentation from saved nnU-Net probabilities at a foreground threshold t.

Janus 0 places the lumen boundary about one voxel inside ImageCAS-X's (volume ratio 0.867, [[icx4 - Results]]).
nnU-Net's export is argmax over the five classes. Here a voxel is vessel when the summed vessel probability is at
least t, and its class is the argmax among the four vessels. t = 0.5 reproduces argmax up to ties.

Input: a directory of nnU-Net v2 `--save_probabilities` outputs (`<case>.npz` with `probabilities`, shape
(5, *spatial) in nnU-Net's SimpleITK axis order, plus `<case>.nii.gz`, the argmax segmentation).
Output: `<out>/t<t>/<case>.nii.gz` for each t, on the segmentation's own grid and header, ready for
experiments/Atlas/r9_score_icx4.py --pred <out>/t<t>.

Guards:
  * the axis order is found by matching argmax(probabilities) to the saved segmentation (>= 99.9 % of voxels);
    a case that matches neither order is refused;
  * a case named in trillium/sealed_test.json (sealed ImageCAS-X 80, quality-0 20) is refused.

Usage (Trillium login node or CPU job, the icx4 venv):
  python threshold_export.py --probs $W/probs --out $W/thr --t 0.5 0.45 0.4 0.35 0.3 --np 8
  python threshold_export.py --selftest
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def sealed():
    s = json.load(open(os.path.join(REPO, 'trillium', 'sealed_test.json')))
    return set(s['sealed_icx_test']) | set(s['sealed_quality0'])


def threshold(prob, t):
    """prob: (5, ...) class probabilities. Vessel where sum(prob[1:]) >= t (argmax when t == 0.5)."""
    vessel = prob[1:].argmax(0).astype(np.uint8) + 1
    fg = prob.argmax(0) > 0 if t == 0.5 else prob[1:].sum(0) >= t
    return np.where(fg, vessel, 0).astype(np.uint8)


def orient(prob, seg):
    """Return prob in the segmentation's (nibabel) axis order."""
    for cand in (prob.transpose(0, 3, 2, 1), prob):
        if cand.shape[1:] == seg.shape and (cand.argmax(0) == seg).mean() >= 0.999:
            return cand
    raise ValueError('probabilities match the saved segmentation in neither axis order')


def one(job):
    npz, out, ts = job
    c = os.path.basename(npz)[:-4]
    if c in SEALED:
        raise RuntimeError(f'refusing sealed case {c}')
    img = nib.load(npz[:-4] + '.nii.gz')
    seg = np.asarray(img.dataobj).astype(np.uint8)
    prob = orient(np.load(npz)['probabilities'].astype(np.float32), seg)
    row = dict(case=c)
    for t in ts:
        d = os.path.join(out, f't{t:.2f}')
        os.makedirs(d, exist_ok=True)
        p = threshold(prob, t)
        nib.save(nib.Nifti1Image(p, img.affine, img.header), os.path.join(d, c + '.nii.gz'))
        row[f'{t:.2f}'] = int((p > 0).sum())
    return row


SEALED = sealed()


def selftest():
    rng = np.random.default_rng(0)
    logits = rng.normal(size=(5, 6, 7, 8)).astype(np.float32)
    prob = np.exp(logits) / np.exp(logits).sum(0)
    seg = prob.argmax(0)
    assert (threshold(prob, 0.5) == seg).all()                       # t = 0.5 is argmax
    a, b = (threshold(prob, t) > 0 for t in (0.3, 0.4))
    assert (b <= a).all() and (threshold(prob, 0.5) > 0).sum() <= a.sum()   # lower t only adds vessel
    sitk_order = prob.transpose(0, 3, 2, 1)                          # nnU-Net's order, back to nibabel's
    assert (orient(sitk_order, seg) == prob).all()
    print('[threshold_export] self-test passed')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probs'); ap.add_argument('--out'); ap.add_argument('--np', type=int, default=8)
    ap.add_argument('--t', type=float, nargs='+', default=[0.5, 0.45, 0.4, 0.35, 0.3])
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    files = sorted(glob.glob(os.path.join(a.probs, '*.npz')))
    if not files:
        sys.exit(f'no .npz in {a.probs}')
    with Pool(a.np) as p:
        rows = p.map(one, [(f, a.out, a.t) for f in files], chunksize=1)
    json.dump(rows, open(os.path.join(a.out, 'voxels.json'), 'w'), indent=1)
    print(f'[threshold_export] {len(rows)} cases x {len(a.t)} thresholds -> {a.out}')


if __name__ == '__main__':
    main()
