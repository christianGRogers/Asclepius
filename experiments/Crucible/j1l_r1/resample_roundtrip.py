"""Crucible, Janus 1-L Round 1: how much of Janus 0's thin lumen is nnU-Net's 0.5 mm resampling alone?

Janus 0 (icx4) trains at 0.5 mm isotropic (`-overwrite_target_spacing 0.5 0.5 0.5`, trillium/icx4/lib/prepare.py).
ImageCAS-X is drawn at about 0.33-0.43 mm in-plane. On val 80 Janus 0's volume ratio is 0.867 and its whole-tree
Dice 0.880 against a 1-voxel-tolerant Dice of 0.971 ([[icx4 - Results]]).

This script takes ImageCAS-X's own labels (a *perfect* network) through the same round trip nnU-Net v2.8.1 makes:
  1. preprocessing: each class resized to the target spacing with order-1 interpolation, kept where >= 0.5
     (nnunetv2.preprocessing.resampling.default_resampling.resample_data_or_seg, is_seg=True, order 1, no
     anisotropic branch: max/min spacing < 3);
  2. a perfect network outputs that resampled label as one-hot logits;
  3. export: logits resized back to the original shape with order 1, then argmax
     (convert_predicted_logits_to_segmentation_with_correct_shape).
It compares the result with the original label: Dice, 1-voxel-tolerant Dice and volume ratio, exactly as
experiments/Atlas/r10_dice_check.measure() defines them. It also tries an export-time foreground threshold t
(vessel if the summed vessel probability >= t, class by argmax among vessels) and other target spacings.

Cases: ImageCAS-X **train 560 only** (filelist/train.txt). The locked 100 (val 80 + 20 of open-36), the other
ImageCAS-X test cases and every sealed case are never opened. Labels only; no CT. CPU.

Usage: python3 resample_roundtrip.py <ImageCAS-X_dataset dir> [n_cases] [n_proc] > resample_roundtrip.json
"""
from __future__ import annotations

import json
import os
import sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from skimage.transform import resize

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'trillium', 'icx4', 'lib'))
from territory import to_four  # noqa: E402  (the D25 collapse icx4 trains on)

S26 = np.ones((3, 3, 3), bool)
TARGETS = (0.5, 0.45, 0.4)          # 0.5 = Janus 0
THRESH = (0.5, 0.4, 0.3)            # 0.5 = argmax (Janus 0's export)
MARGIN = 8                          # voxels of context around the tree's bounding box


def sealed_ids():
    d = json.load(open(os.path.join(REPO, 'trillium', 'sealed_test.json')))
    return set(d['sealed_icx_test']) | set(d['sealed_quality0'])


def resize_seg(seg, shape):
    """nnU-Net's resize_segmentation, order 1."""
    out = np.zeros(shape, seg.dtype)
    for c in np.unique(seg):
        if c == 0:
            continue
        m = resize((seg == c).astype(np.float32), shape, order=1, mode='edge', clip=True, anti_aliasing=False)
        out[m >= 0.5] = c
    return out


def measure(p, r):
    p, r = p > 0, r > 0
    pd, rd = ndi.binary_dilation(p, S26), ndi.binary_dilation(r, S26)
    s = p.sum() + r.sum()
    return dict(dice=float(2 * (p & r).sum() / s), tolerant_dice=float(((p & rd).sum() + (r & pd).sum()) / s),
                volume_ratio=float(p.sum() / r.sum()))


def per_class_dice(p, r):
    out = {}
    for c, n in ((1, 'LM'), (2, 'LAD'), (3, 'LCx'), (4, 'RCA')):
        a, b = p == c, r == c
        if b.sum():
            out[n] = float(2 * (a & b).sum() / (a.sum() + b.sum()))
    return out


def one(path):
    img = nib.load(path)
    zooms = np.asarray(img.header.get_zooms()[:3], float)
    lab = to_four(np.asarray(img.dataobj).astype(np.uint8), zooms)
    nz = np.argwhere(lab > 0)
    lo = np.maximum(nz.min(0) - MARGIN, 0)
    hi = np.minimum(nz.max(0) + MARGIN + 1, lab.shape)
    ref = lab[tuple(slice(a, b) for a, b in zip(lo, hi))]
    row = dict(case=os.path.basename(path).split('.')[0], spacing=[round(float(z), 4) for z in zooms], runs={})
    for tsp in TARGETS:
        shp = tuple(int(round(n * z / tsp)) for n, z in zip(ref.shape, zooms))
        low = resize_seg(ref, shp)
        # a perfect network: one-hot logits of the resampled label, resized back with order 1 (per channel)
        prob = np.stack([resize((low == c).astype(np.float32), ref.shape, order=1, mode='edge', clip=True,
                                anti_aliasing=False) for c in range(5)])
        for t in THRESH:
            fg = prob[1:].sum(0)
            pred = np.where(fg >= t if t < 0.5 else prob.argmax(0) > 0, prob[1:].argmax(0) + 1, 0).astype(np.uint8)
            m = measure(pred, ref)
            m['class_dice'] = per_class_dice(pred, ref)
            row['runs'][f'{tsp}_{t}'] = m
    return row


def summarise(rows):
    keys = rows[0]['runs'].keys()
    out = {}
    for k in keys:
        v = {m: np.array([r['runs'][k][m] for r in rows]) for m in ('dice', 'tolerant_dice', 'volume_ratio')}
        out[k] = {m: dict(mean=round(float(a.mean()), 4), p10=round(float(np.percentile(a, 10)), 4),
                          p90=round(float(np.percentile(a, 90)), 4)) for m, a in v.items()}
        out[k]['class_dice_mean'] = {c: round(float(np.mean([r['runs'][k]['class_dice'][c] for r in rows
                                                             if c in r['runs'][k]['class_dice']])), 4)
                                     for c in ('LM', 'LAD', 'LCx', 'RCA')}
    return out


def main():
    root = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 560
    npr = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    train = [int(x) for x in open(os.path.join(root, 'filelist', 'train.txt')).read().split()]
    banned = set()
    for name in ('val', 'test'):
        banned |= {int(x) for x in open(os.path.join(root, 'filelist', name + '.txt')).read().split()}
    sealed = sealed_ids()
    assert not banned & set(train), 'train overlaps val/test'
    assert not {'c%04d' % (i - 1) for i in train} & sealed, 'a sealed case is in train'
    ids = sorted(train)
    ids = ids[::max(1, len(ids) // n)][:n]       # evenly spaced over the sorted train list
    paths = [os.path.join(root, 'segmentations', f'{i}.coronary.nii.gz') for i in ids]
    with Pool(npr) as p:
        rows = p.map(one, paths)
    sp = np.array([r['spacing'] for r in rows])
    json.dump(dict(cases=len(rows), cases_from='ImageCAS-X train.txt only (no val, test or sealed case opened)',
                   spacing_mean=sp.mean(0).round(4).tolist(), spacing_min=sp.min(0).round(4).tolist(),
                   spacing_max=sp.max(0).round(4).tolist(),
                   janus0_val80=dict(dice=0.880, tolerant_dice=0.971, volume_ratio=0.867),
                   summary=summarise(rows), per_case=rows), sys.stdout, indent=1)


if __name__ == '__main__':
    main()
