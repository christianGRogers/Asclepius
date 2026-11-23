"""Janus 1-F round 3 (Foxtrot): disk per locked case of `nnUNetv2_predict --save_probabilities` for the 13-class
1-F network (§5 item 3), estimated on ONE training case's geometry (no CT, no model).

nnU-Net 2.8.1 (`export_prediction.py`): the logits are resampled to the original grid, softmaxed in float32
(`apply_inference_nonlin`: logits.float()), un-cropped to `shape_before_cropping`, and written with
np.savez_compressed(probabilities=float32 (13, X, Y, Z)) plus a .pkl and the argmax .nii.gz.
A network's background softmax is never exactly 0/1, so the low-order mantissa bits are what zlib must store. The
field is modelled as logit_c = 8 - 1.5 * d_c(mm) for each class c present (d_c = distance to class c), background
logit 0 at the tree and +k * d(mm) away from it, with i.i.d. N(0, s) noise of the size half-precision accumulation and
resampling leave (s = 0.01, 0.05). The written npz is measured, then deleted. A no-noise field is the lower bound.
Usage: python npz_size.py <icx620_dir> <case id in the 620> <tmp_dir>"""
import json, os, sys, time
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]
import j1f_scorer as S  # noqa: E402

d, case, tmp = sys.argv[1:4]
train = set(json.load(open(os.path.join(HERE, '../../Atlas/j1l/split_j1l.json')))['train620'])
assert case in train
im = nib.load(os.path.join(d, f'{int(case[1:]) + 1}.coronary.nii.gz'))
icx = np.asarray(im.dataobj).astype(np.uint8); z = np.array(im.header.get_zooms()[:3], float)
lab, _ = S.stage1_labels(icx, z)
lab[lab == S.IGNORE] = 0
shape = lab.shape
out = {'case': case, 'shape': list(shape), 'raw_float32_GB': round(13 * np.prod(shape) * 4 / 1e9, 3)}
dtree = ndi.distance_transform_edt(lab == 0, sampling=z).astype(np.float32)
rng = np.random.default_rng(0)
for s in (0.0, 0.01, 0.05):
    logit = np.empty((13,) + shape, np.float32)
    logit[0] = 0.4 * dtree
    for c in range(1, 13):
        if (lab == c).any():
            logit[c] = 8 - 1.5 * ndi.distance_transform_edt(lab != c, sampling=z)
        else:
            logit[c] = -4 - 0.4 * dtree
        if s:
            logit[c] += rng.normal(0, s, shape).astype(np.float32)
    if s:
        logit[0] += rng.normal(0, s, shape).astype(np.float32)
    logit -= logit.max(0, keepdims=True)
    np.exp(logit, out=logit); logit /= logit.sum(0, keepdims=True)
    p = os.path.join(tmp, f'{case}_s{s}.npz')
    t0 = time.time(); np.savez_compressed(p, probabilities=logit); dt = time.time() - t0
    out[f'noise_{s}'] = {'npz_GB': round(os.path.getsize(p) / 1e9, 3), 'write_s': round(dt, 1),
                         'zero_fraction': round(float((logit == 0).mean()), 4)}
    os.remove(p); del logit
    print(out, flush=True)
json.dump(out, open(os.path.join(HERE, 'results', f'npz_size_{case}.json'), 'w'), indent=1)
