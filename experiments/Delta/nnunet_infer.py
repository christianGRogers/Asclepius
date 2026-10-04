"""E8: real CNN errors.  Run ImageCAS-X's released nnU-Net (binary lumen, 3d_fullres, fold 0,
checkpoint_best; Zenodo 10.5281/zenodo.21887809 pretrained_weights.zip) on CPU on our cached CTs
of ImageCAS-X *test* cases (never seen in any fold), and save the foreground probability.

Usage: python nnunet_infer.py <model_dir> <out_dir> <tile_step> case [case ...]

To fit the shared CPU, the CT is cropped to the ImageCAS-X reference tree's bounding box grown by
ROI_MARGIN_MM (default 10 mm) before inference (false positives far outside the tree are not measured), mirroring TTA
is off, and tile_step_size is a parameter (nnU-Net default 0.5).
Output per case: <case>_prob.npy (float16 foreground probability, crop grid, nibabel axis order)
and <case>_meta.json (crop offset, spacing, timing).
"""
import json
import os
import sys
import time

import nibabel as nib
import numpy as np
import torch

SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
from girder import ct_path  # noqa: E402
import treelib as T  # noqa: E402

MARGIN = float(os.environ.get("ROI_MARGIN_MM", "10"))
torch.set_num_threads(int(os.environ.get('TORCH_THREADS', '1')))
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor  # noqa: E402

if __name__ == '__main__':
    model_dir, out_dir, step = sys.argv[1], sys.argv[2], float(sys.argv[3])
    os.makedirs(out_dir, exist_ok=True)
    pred = nnUNetPredictor(tile_step_size=step, use_gaussian=True, use_mirroring=False,
                           perform_everything_on_device=False, device=torch.device('cpu'),
                           verbose=False, verbose_preprocessing=False, allow_tqdm=False)
    pred.initialize_from_trained_model_folder(model_dir, use_folds=(0,), checkpoint_name='checkpoint_best.pth')
    for case in sys.argv[4:]:
        if os.path.exists(f'{out_dir}/{case}_prob.npy'):
            continue
        t0 = time.time()
        img = nib.load(ct_path(case))
        sp = np.array(img.header.get_zooms()[:3], float)
        ref = np.asanyarray(nib.load(T.icx_path(case)).dataobj) > 0
        idx = [np.nonzero(ref.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
        mv = np.ceil(MARGIN / sp).astype(int)
        lo = np.maximum([a[0] for a in idx] - mv, 0)
        hi = np.minimum([a[-1] + 1 for a in idx] + mv, ref.shape)
        ct = np.asanyarray(img.dataobj)[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]].astype(np.float32)
        x = ct.transpose(2, 1, 0)[None]  # (c, z, y, x) as SimpleITK would read it
        props = {'spacing': [float(sp[2]), float(sp[1]), float(sp[0])]}
        seg, prob = pred.predict_single_npy_array(x, props, None, None, True)
        p = prob[1].transpose(2, 1, 0).astype(np.float16)
        np.save(f'{out_dir}/{case}_prob.npy', p)
        json.dump(dict(case=case, lo=lo.tolist(), hi=hi.tolist(), spacing=sp.tolist(), step=step,
                       seconds=time.time() - t0, threads=torch.get_num_threads()),
                  open(f'{out_dir}/{case}_meta.json', 'w'))
        print(case, round(time.time() - t0), 's', p.shape, flush=True)
