"""Synthetic pool cases for the wave-1 self-test: a 4-class coronary tree of tubes beside an aorta, reads that
perturb it, a binary seed (the tree plus a vein-like tube, as a TotalSegmentator seed might carry), and a
prediction. Written in the segqueue14-export layout that score_wave1.py reads."""
from __future__ import annotations

import os

import nibabel as nib
import numpy as np

SHAPE = (128, 128, 112)
K = 1.35   # scale of the path coordinates below (drawn for a 96 x 96 x 80 grid)
SP = (0.5, 0.5, 0.5)


def _tube(m, pts, r_vox, val):
    zz, yy, xx = np.ogrid[:m.shape[0], :m.shape[1], :m.shape[2]]
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        n = int(np.ceil(np.linalg.norm(b - a) * 2)) + 1
        for t in np.linspace(0, 1, n):
            c = a + t * (b - a)
            lo = np.maximum(np.floor(c - r_vox - 1).astype(int), 0)
            hi = np.minimum(np.ceil(c + r_vox + 2).astype(int), m.shape)
            sub = (slice(lo[0], hi[0]), slice(lo[1], hi[1]), slice(lo[2], hi[2]))
            d = (zz[sub[0], :, :] - c[0]) ** 2 + (yy[:, sub[1], :] - c[1]) ** 2 + (xx[:, :, sub[2]] - c[2]) ** 2
            m[sub][(d <= r_vox ** 2) & (m[sub] == 0)] = val


def tree(rng, jitter=0.0, lad_len=1.0, lcx_len=1.0, rca_len=1.0, r=3.2):
    """Labels 1-4 and an aorta. ``jitter`` moves the path points (voxels); *_len trims distal ends."""
    m = np.zeros(SHAPE, np.uint8)
    def j(p):
        p = np.asarray(p, float) * K
        return tuple(p + rng.normal(0, jitter, 3)) if jitter else tuple(p)
    lm0, lm1 = j((40, 52, 30)), j((40, 60, 40))
    _tube(m, [lm0, lm1], r, 1)
    lad = [lm1, j((44, 68, 52)), j((52, 74, 66))]
    lcx = [lm1, j((32, 70, 46)), j((22, 74, 58))]
    rca = [j((40, 40, 30)), j((40, 30, 42)), j((48, 20, 56))]
    def cut(path, f):
        if f >= 1.0:
            return path
        a, b = np.asarray(path[-2], float), np.asarray(path[-1], float)
        return path[:-1] + [tuple(a + f * (b - a))]
    _tube(m, cut(lad, lad_len), r * 0.9, 2)
    _tube(m, cut(lcx, lcx_len), r * 0.9, 3)
    _tube(m, cut(rca, rca_len), r, 4)
    aorta = np.zeros(SHAPE, bool)
    zz, yy, xx = np.ogrid[:SHAPE[0], :SHAPE[1], :SHAPE[2]]
    aorta |= ((yy - 46 * K) ** 2 + (xx - 22 * K) ** 2 <= (9 * K) ** 2) & (zz >= 10) & (zz <= 108)
    m[aorta] = 0
    return m, aorta


def case(rng, anchored: bool):
    """(read A, read B, seed, prediction, aorta).

    The seed is wrong on its own, as a TotalSegmentator seed is (Dice about 0.70 against ImageCAS-X): its own
    jitter and distal ends, plus a vein-like tube that touches nothing.
    ``anchored``: both readers keep the seed's extent and only delete the vein (D26's worst case).
    Otherwise each reader draws the true tree with their own small errors, independent of the seed."""
    truth, aorta = tree(rng)
    seed_tree, _ = tree(rng, jitter=2.0, lad_len=rng.uniform(0.3, 1.0), lcx_len=rng.uniform(0.3, 1.0),
                        rca_len=rng.uniform(0.3, 1.0), r=rng.uniform(2.4, 4.2))
    vein = np.zeros(SHAPE, np.uint8)
    _tube(vein, [(81, 95, 45), (89, 81, 81)], 2.4, 1)
    seed = (seed_tree > 0) | (vein > 0)
    if anchored:
        a = b = seed_tree.copy()
    else:
        a, b = (tree(rng, jitter=0.8, lad_len=rng.uniform(0.8, 1.0), lcx_len=rng.uniform(0.8, 1.0),
                     rca_len=rng.uniform(0.8, 1.0), r=rng.uniform(2.9, 3.5))[0] for _ in range(2))
    pred, _ = tree(rng, jitter=0.8, lad_len=rng.uniform(0.5, 1.0), lcx_len=rng.uniform(0.4, 1.0))
    return a, b, seed, pred, aorta


def write(root, volume, rng, anchored=False, n_reads=2):
    """Writes reads, seed, prediction and aorta for ``volume`` under ``root``; returns the four dirs."""
    a, b, seed, pred, aorta = case(rng, anchored)
    aff = np.diag(list(SP) + [1.0])
    stem = volume[:-len('.nii.gz')]
    dirs = {k: os.path.join(root, k) for k in ('reads', 'seeds', 'pred', 'aorta')}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    names = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
    for i, r in enumerate([a, b][:n_reads]):
        d = os.path.join(dirs['reads'], stem + ('' if i == 0 else f'__r{i + 1}'), 'segmentations')
        os.makedirs(d, exist_ok=True)
        for c, n in names.items():
            nib.save(nib.Nifti1Image((r == c).astype(np.uint8), aff), os.path.join(d, n + '.nii.gz'))
    nib.save(nib.Nifti1Image(seed.astype(np.uint8), aff), os.path.join(dirs['seeds'], stem + '__totalseg-coronary.nii.gz'))
    nib.save(nib.Nifti1Image(pred.astype(np.uint8), aff), os.path.join(dirs['pred'], volume))
    nib.save(nib.Nifti1Image(aorta.astype(np.uint8), aff), os.path.join(dirs['aorta'], stem + '_aorta.nii.gz'))
    return dirs
