"""Round 2 ruling §5 item 3: the disk one locked case's `--save_probabilities` npz needs, to size the chunk of 10.
nnU-Net 2.8.1 writes `np.savez_compressed(probabilities=float32 (C, *original shape))` (export_prediction.py l. 101;
logits are cast to float before softmax, label_handling.py l. 138), plus a small .pkl. C = 13 for J1F-A.
No model exists here, so the softmax is built from a TRAINING label: logits = A x Gaussian-blurred one-hot of the
13-class map (sigma 1 voxel), plus i.i.d. noise of SD `noise` (0 = an idealised smooth network; 0.5 = rough
float32 mantissas everywhere). A slab of `slab` slices at full in-plane size is compressed and scaled to the
case's whole depth. Also prints the uncompressed size (the hard ceiling). Usage:
python3 npz_size.py <icx_dir> <case> [slab=48]"""
import io, json, os, sys, zipfile
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_sp = importlib.util.spec_from_file_location('atlas_scorer', os.path.join(HERE, '../../Atlas/j1f_r2/j1f_scorer.py'))
A = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(A)

d, c = sys.argv[1], sys.argv[2]
slab = int(sys.argv[3]) if len(sys.argv) > 3 else 48
ids = json.load(open(os.path.join(d, 'split.json')))['train620']
assert c in ids, 'training cases only'
im = nib.load(os.path.join(d, 'segmentations', f'{int(c[1:]) + 1}.coronary.nii.gz'))
icx = np.asarray(im.dataobj).astype(np.uint8)
z = np.array(im.header.get_zooms()[:3], float)
lab, _ = A.stage1_labels(icx, z)
lab = np.where(lab == 255, 0, lab)
ax = int(np.argmax(np.array(lab.shape) == min(lab.shape)))         # the slice axis (the short one)
mid = int(np.argwhere(lab > 0)[:, ax].mean())
sl = [slice(None)] * 3; sl[ax] = slice(mid - slab // 2, mid + slab // 2)
sub = lab[tuple(sl)]
full_depth = lab.shape[ax]
res = {'case': c, 'shape': list(lab.shape), 'channels': 13,
       'uncompressed_GB': round(13 * lab.size * 4 / 1e9, 2)}
rng = np.random.default_rng(0)
for noise in (0.0, 0.5):
    lg = np.stack([ndi.gaussian_filter((sub == k).astype(np.float32), 1.0) * 12 for k in range(13)])
    if noise:
        lg += rng.normal(0, noise, lg.shape).astype(np.float32)
    lg -= lg.max(0, keepdims=True)
    p = np.exp(lg); p /= p.sum(0, keepdims=True)
    p = p.astype(np.float32)
    buf = io.BytesIO()
    np.savez_compressed(buf, probabilities=p)
    gb = len(buf.getvalue()) / 1e9 * full_depth / sub.shape[ax]
    res[f'npz_GB_noise{noise}'] = round(gb, 2)
    del lg, p
print(json.dumps(res))
