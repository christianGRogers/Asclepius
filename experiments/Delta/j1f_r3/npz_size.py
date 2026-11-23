"""Janus 1-F round 3 (Delta): how big is one locked case's `--save_probabilities` npz? (ruling §5 item 3)

What nnU-Net 2.8.1 writes (read in the wheel, `inference/export_prediction.py` and `predict_from_raw_data.py`): logits
are accumulated as float16 on the 0.5 mm grid, resampled to the case's native grid keeping float16, soft-maxed in
float32 (`apply_inference_nonlin`: "softmax etc is not implemented for half"), un-cropped to the full image and saved
with `np.savez_compressed(probabilities=...)`: 13 float32 channels at the native shape. ImageCAS-X's native shape is
512 x 512 x 275 in all 620 training cases (72.1 M voxels), so the raw array is 13 x 4 x 72.1 M = 3.75 GB per case.

The compressed size depends on the logits, which nobody has yet (no 1-F model exists). Estimate: one training case
(smallest sha256('asclepius-j1f-r3-npz:' + id)), its 1-F reference turned into smooth synthetic logits on the 0.5 mm
grid (per class: 4 - d_c / 1.5 mm, capped; background: 4 + min(d_tree, 20 mm) / 4; plus a smooth noise field of SD 1),
cast to float16, resampled (order 1) to native, soft-maxed in float32, each channel deflated as savez_compressed does
(zlib level 6). Labels only; CPU. Usage: python npz_size.py <icx620_dir> <split_j1l.json>
"""
import hashlib, json, os, sys, zlib
import nibabel as nb
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_labels as L  # noqa: E402

icx, split = sys.argv[1], json.load(open(sys.argv[2]))
train = sorted(split['train620'])
c = min(train, key=lambda x: hashlib.sha256(('asclepius-j1f-r3-npz:' + x).encode()).hexdigest())
im = nb.load(os.path.join(icx, '%d.coronary.nii.gz' % (int(c[1:]) + 1)))
lab = np.asarray(im.dataobj).astype(np.uint8); z = np.array(im.header.get_zooms()[:3], float)
ref, _ = L.map13(lab, z); ref[ref == 255] = 0
shape = ref.shape
f = z / 0.5                                                   # native -> 0.5 mm
lo = ndi.zoom(ref, f, order=0)
z05 = np.array([0.5, 0.5, 0.5])
rng = np.random.default_rng(0)
logits = np.empty((13,) + lo.shape, np.float16)
dtree = np.minimum(ndi.distance_transform_edt(lo == 0, sampling=z05), 20.0)
noise = lambda: (ndi.gaussian_filter(rng.normal(size=lo.shape).astype(np.float32), 4) * 8).astype(np.float32)
logits[0] = (4 + dtree / 4 + noise()).astype(np.float16)
for k in range(1, 13):
    if (lo == k).any():
        d = np.minimum(ndi.distance_transform_edt(lo != k, sampling=z05), 60.0)
    else:
        d = np.full(lo.shape, 60.0, np.float32)
    logits[k] = (4 - d / 1.5 + noise()).astype(np.float16)
del dtree
print('case', c, 'native', shape, 'grid0.5', lo.shape, flush=True)
zf = np.array(shape) / np.array(lo.shape)
# native float16 logits, one channel at a time; then a float32 softmax in z-slabs, each channel deflated
nat = np.empty((13,) + shape, np.float16)
for k in range(13):
    nat[k] = ndi.zoom(logits[k].astype(np.float32), zf, order=1, output=np.float32)[:shape[0], :shape[1], :shape[2]]
del logits
raw = comp = 0
comps = [zlib.compressobj(6) for _ in range(13)]
sizes = np.zeros(13, int)
for s in range(0, shape[2], 25):
    x = nat[:, :, :, s:s + 25].astype(np.float32)
    x -= x.max(0, keepdims=True); np.exp(x, out=x); x /= x.sum(0, keepdims=True)
    for k in range(13):
        b = np.ascontiguousarray(x[k]).tobytes()
        raw += len(b); sizes[k] += len(comps[k].compress(b))
for k in range(13):
    sizes[k] += len(comps[k].flush())
comp = int(sizes.sum())
dec = np.zeros(shape, np.uint8)
out = {'case': c, 'native_shape': list(shape), 'raw_GB': round(raw / 1e9, 3), 'deflated_GB': round(comp / 1e9, 3),
       'ratio': round(raw / comp, 2), 'per_channel_MB': [round(s / 1e6, 1) for s in sizes],
       'decoded_F_T_wg_MB_upper': round(5 * len(zlib.compress(ref.tobytes(), 6)) / 1e6, 2)}
print(json.dumps(out))
json.dump(out, open(os.path.join(HERE, 'npz_size.json'), 'w'), indent=1)
