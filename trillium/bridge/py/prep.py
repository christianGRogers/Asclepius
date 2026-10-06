"""Compute node (CPU part of the job): build the nnU-Net raw dataset of PROXY 4-class labels on the
ORIGINAL ImageCAS mask (D0), named from ImageCAS-X (territory D1, ramus -> LCx D1b), as in the master plan
(Atlas v3 §2.1): each mask voxel takes the ImageCAS-X class of the nearest ImageCAS-X voxel within 2 mm;
the rest inherit geodesically inside the mask; 'Other' (D3/D4/OM3/OM4) is left to inheritance from its parent.

Training cases = ImageCAS-X train list (560), nnU-Net validation fold = ImageCAS-X val list (80; the
master's own val split). ImageCAS-X test and excluded scans are not touched.
usage: python prep.py CASEMAP.json ICX_DIR NNUNET_RAW DATASET_NAME NPROC
"""
import json
import os
import sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

# 14 ImageCAS-X classes -> 4 (D1 territory, D1b ramus->LCx); 14 'Other' -> 0 (inherits from parent)
ICX4 = np.array([0, 1, 2, 3, 2, 2, 3, 3, 3, 4, 4, 4, 3, 3, 0], np.uint8)


def proxy(mask, icx_raw, sp, near_mm=2.0):
    m = mask > 0
    g = ICX4[np.clip(icx_raw, 0, 14)]
    lab = np.zeros(m.shape, np.uint8)
    if not m.any():
        return lab
    idx = np.argwhere(m | (g > 0))
    lo = np.maximum(idx.min(0) - 5, 0); hi = np.minimum(idx.max(0) + 6, m.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    mc, gc = m[sl], g[sl]
    out = np.zeros(mc.shape, np.uint8)
    if (gc > 0).any():
        d, ind = ndi.distance_transform_edt(gc == 0, sampling=sp, return_indices=True)
        near = mc & (d <= near_mm)
        out[near] = gc[tuple(ind)][near]
        # geodesic inheritance inside the mask (26-connected front propagation)
        st = np.ones((3, 3, 3), bool)
        for _ in range(2000):
            todo = mc & (out == 0)
            if not todo.any():
                break
            grown = ndi.grey_dilation(out, footprint=st)
            new = todo & (grown > 0)
            if not new.any():
                break
            out[new] = grown[new]
    rest = mc & (out == 0)  # mask pieces with no path to any named voxel: nearest named voxel
    if rest.any() and (out > 0).any():
        _, ind = ndi.distance_transform_edt(out == 0, sampling=sp, return_indices=True)
        out[rest] = out[tuple(ind)][rest]
    lab[sl] = out
    return lab


def one(args):
    case, ct, msk, icx, raw = args
    dst = os.path.join(raw, 'labelsTr', f'{case}.nii.gz')
    img = os.path.join(raw, 'imagesTr', f'{case}_0000.nii.gz')
    if os.path.exists(dst) and os.path.lexists(img):
        return case, 'exists'
    mi = nib.load(msk); gi = nib.load(icx)
    if mi.shape != gi.shape or not np.allclose(mi.affine[:2], gi.affine[:2], atol=1e-3):
        return case, f'SKIP grid mismatch mask {mi.shape} vs ImageCAS-X {gi.shape}'
    ci = nib.load(ct)
    if ci.shape != mi.shape:
        return case, f'SKIP ct/mask shape mismatch {ci.shape} vs {mi.shape}'
    sp = np.asarray(mi.header.get_zooms()[:3], float)
    lab = proxy(np.asanyarray(mi.dataobj) > 0.5, np.asanyarray(gi.dataobj).astype(np.int16), sp)
    nib.save(nib.Nifti1Image(lab, mi.affine), dst + '.part.nii.gz')
    os.replace(dst + '.part.nii.gz', dst)
    if not os.path.lexists(img):
        os.symlink(os.path.abspath(ct), img)
    return case, 'ok %s' % np.bincount(lab.ravel(), minlength=5)[1:].tolist()


def main(casemap, icx_dir, raw, name, nproc):
    cm = json.load(open(casemap))
    rd = lambda f: ['c%04d' % (int(x) - 1) for x in open(os.path.join(icx_dir, f)).read().split()]
    train, val = rd('train.txt'), rd('val.txt')
    os.makedirs(os.path.join(raw, 'imagesTr'), exist_ok=True)
    os.makedirs(os.path.join(raw, 'labelsTr'), exist_ok=True)
    jobs = [(c, cm[c][0], cm[c][1], os.path.join(icx_dir, f'{int(c[1:]) + 1}.coronary.nii.gz'), raw)
            for c in train + val if c in cm]
    missing = [c for c in train + val if c not in cm]
    print(f'prep: {len(jobs)} cases ({len(train)} train + {len(val)} val listed; {len(missing)} not in cases/)', flush=True)
    ok = []
    with Pool(nproc) as p:
        for c, msg in p.imap_unordered(one, jobs):
            if not msg.startswith('SKIP'):
                ok.append(c)
            else:
                print(c, msg, flush=True)
    tr = sorted(c for c in train if c in ok); va = sorted(c for c in val if c in ok)
    json.dump({'channel_names': {'0': 'CT'}, 'labels': {'background': 0, 'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4},
               'numTraining': len(tr) + len(va), 'file_ending': '.nii.gz', 'overwrite_image_reader_writer': 'NibabelIO',
               'name': name, 'description': 'Bridge Trillium experiment: territory proxy on ImageCAS masks (D0, D1, D1b)'},
              open(os.path.join(raw, 'dataset.json'), 'w'), indent=1)
    json.dump([{'train': tr, 'val': va}], open(os.path.join(raw, 'splits_bridge.json'), 'w'))
    print(f'prep done: train {len(tr)} val {len(va)}', flush=True)
    if len(tr) < int(os.environ.get('BRIDGE_MIN_TRAIN', 50)) or len(va) < int(os.environ.get('BRIDGE_MIN_VAL', 10)):
        raise SystemExit('ERROR: too few usable cases; check the case layout / ImageCAS-X grid match above')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
