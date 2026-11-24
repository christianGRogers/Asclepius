"""§5 item 3: a disk estimate for one locked case's 13-class probability npz, as nnU-Net 2.x writes it
(`np.savez_compressed(..., probabilities=float32 array (C, X, Y, Z))` at the original image shape).

No CT and no model: a TRAINING case's label (hash-chosen from the 620) is turned into a plausible trained-model
softmax (each class's one-hot blurred by sigma = 1 voxel, a 1e-6-scale floor with float noise so no voxel is exactly
0 or 1, renormalised), and saved both as float32 and float16. A real softmax is noisier than this in the background,
so the float32 figure is also bounded from above by scaling the measured untrained 5-class npz (1.25 GB / case,
Atlas's Trillium R0 note) to 13 channels.
Usage: python npz_size.py <icx620_dir>"""
import hashlib, json, os, sys, tempfile
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402

src = sys.argv[1]
train = json.load(open(os.path.join(src, 'split.json')))['train620']
c = min(train, key=lambda x: hashlib.sha256(('asclepius-j1f-r3-npz:' + x).encode()).hexdigest())
im = nib.load(os.path.join(src, '%d.coronary.nii.gz' % (int(c[1:]) + 1)))
icx = np.asarray(im.dataobj).astype(np.uint8)
lab, _ = S.stage1_labels(icx, im.header.get_zooms())
lab[lab == S.IGNORE] = 0
rng = np.random.default_rng(0)
P = np.empty((13,) + lab.shape, np.float32)
for k in range(1, 13):
    P[k] = ndi.gaussian_filter((lab == k).astype(np.float32), 1.0)
P[1:] += rng.random(P[1:].shape, dtype=np.float32) * 1e-6
P[0] = np.clip(1 - P[1:].sum(0), 1e-6, 1)
P /= P.sum(0, keepdims=True)
out = {'case': c, 'shape': list(lab.shape), 'voxels_M': round(lab.size / 1e6, 1),
       'uncompressed_GB_f32': round(P.nbytes / 1e9, 2)}
with tempfile.TemporaryDirectory() as d:
    for tag, arr in (('f32', P), ('f16', P.astype(np.float16))):
        f = os.path.join(d, tag + '.npz'); np.savez_compressed(f, probabilities=arr)
        out[f'npz_GB_{tag}'] = round(os.path.getsize(f) / 1e9, 3)
out['upper_bound_GB_f32_from_untrained_5class'] = round(1.25 * 13 / 5, 2)
print(json.dumps(out))
