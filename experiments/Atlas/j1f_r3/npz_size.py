"""Janus 1-F round 3 (Atlas): how much disk does one locked case's `--save_probabilities` npz take? (ruling §5 item 3)

nnU-Net 2.8.1 writes `np.savez_compressed(<case>.npz, probabilities=...)` (export_prediction.py l. 100) with the
probabilities at the ORIGINAL image grid (resampled back and un-cropped), C x Z x Y x X. No model output exists
here, so the probabilities are synthetic but shaped like a network's: on a real training case's grid (labels only),
class c's logit is 6 - 1.5 * d_c(mm), with d_c the distance to that class's reference voxels (capped at 40 mm), plus
smooth noise (sigma 2 voxels, sd 0.5); background's logit is 0; softmax over 13 channels. Two dtypes are written
because nnU-Net's array dtype follows the resampling path (float32 when resampled in numpy, float16 if kept half):
both sizes, the uncompressed size (the ceiling: C x voxels x bytes), and the time to write, are reported.
Usage: python npz_size.py <icx620_dir> <split_j1l.json> <case> <tmpdir>
"""
import json
import os
import sys
import time

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402


def main(d, split, case, tmp):
    assert case in set(json.load(open(split))['train620']), 'training cases only'
    im = nib.load(os.path.join(d, f'{int(case[1:]) + 1}.coronary.nii.gz'))
    icx = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    lab, _ = S.stage1_labels(icx, z)
    lab = np.where(lab == S.IGNORE, 0, lab)
    rng = np.random.default_rng(0)
    shape = lab.shape
    logits = np.zeros((13,) + shape, np.float32)
    for c in range(1, 13):
        m = lab == c
        dc = ndi.distance_transform_edt(~m, sampling=z) if m.any() else np.full(shape, 40.0)
        noise = ndi.gaussian_filter(rng.normal(0, 1, shape).astype(np.float32), 2.0)
        noise *= 0.5 / max(float(noise.std()), 1e-6)
        logits[c] = 6 - 1.5 * np.minimum(dc, 40.0) + noise
    logits -= logits.max(0, keepdims=True)
    np.exp(logits, out=logits)
    logits /= logits.sum(0, keepdims=True)
    out = {'case': case, 'shape': list(shape), 'voxels': int(np.prod(shape)), 'channels': 13}
    for dt in ('float32', 'float16'):
        a = logits.astype(dt)
        f = os.path.join(tmp, f'{case}_{dt}.npz')
        t0 = time.time()
        np.savez_compressed(f, probabilities=a)
        out[dt] = {'npz_bytes': os.path.getsize(f), 'uncompressed_bytes': int(a.nbytes),
                   'write_s': round(time.time() - t0, 1)}
        os.remove(f)
        del a
    print(json.dumps(out))


if __name__ == '__main__':
    main(*sys.argv[1:5])
