"""A synthetic heart for testing the Janus-M read checker and queue. Not anatomy.

A spherical LV pool inside a myocardial shell, an RV pool against the septum, an LA
pool at the base, all in epicardial fat; a CT made from it by assigning each class
a plateau HU and blurring (partial volume). Because the CT's edges are where the
labels' edges are, the exact labels pass the half-maximum rule, and a read with a
border moved by a known distance fails by that distance.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from scipy import ndimage

from . import labels as L

HU = {L.BACKGROUND: -100.0, L.LV_MYO: 120.0, L.LV_POOL: 420.0, L.RV_POOL: 380.0,
      L.LA_POOL: 400.0}


def heart(shape: Tuple[int, int, int] = (96, 96, 96), spacing: float = 0.5,
          pool_mm: float = 12.0, wall_mm: float = 7.0, papillary: bool = False):
    """``(labels, spacing)``: the true labels of the phantom (uint8)."""
    z, y, x = np.indices(shape, dtype=np.float32) * spacing
    c = np.array(shape, dtype=np.float32) * spacing / 2.0
    c[2] -= 6.0  # leave room for the RV on +x
    r = np.sqrt((z - c[0]) ** 2 + (y - c[1]) ** 2 + (x - c[2]) ** 2)
    out = np.zeros(shape, dtype=np.uint8)
    outer = pool_mm + wall_mm
    rv_c = c + np.array([0.0, 0.0, outer + 7.0], dtype=np.float32)
    r_rv = np.sqrt((z - rv_c[0]) ** 2 + (y - rv_c[1]) ** 2 + (x - rv_c[2]) ** 2)
    la_c = c + np.array([-(outer + 6.0), 0.0, 0.0], dtype=np.float32)
    r_la = np.sqrt((z - la_c[0]) ** 2 + (y - la_c[1]) ** 2 + (x - la_c[2]) ** 2)
    out[r_rv <= 11.0] = L.RV_POOL
    out[r_la <= 8.0] = L.LA_POOL
    out[r <= outer] = L.LV_MYO
    out[r <= pool_mm] = L.LV_POOL
    if papillary:
        pm = np.sqrt((z - c[0]) ** 2 + (y - c[1]) ** 2 + (x - (c[2] - 6.0)) ** 2) <= 2.0
        out[pm] = L.LV_MYO
    return out, (spacing, spacing, spacing)


def ct_from(truth: np.ndarray, spacing, blur_mm: float = 0.6, noise_hu: float = 0.0,
            seed: int = 0, papillary_hu: Optional[float] = None) -> np.ndarray:
    """A CT (float32 HU) whose edges are the truth's, blurred by ``blur_mm`` (sigma)."""
    ct = np.zeros(truth.shape, dtype=np.float32)
    for value, hu in HU.items():
        ct[truth == value] = hu
    sigma = [blur_mm / float(s) for s in spacing]
    ct = ndimage.gaussian_filter(ct, sigma)
    if noise_hu:
        ct += np.random.default_rng(seed).normal(0.0, noise_hu, ct.shape).astype(np.float32)
    return ct


def move_border(truth: np.ndarray, spacing, border: str, mm: float,
                octant: Optional[int] = None) -> np.ndarray:
    """A read with one border moved outward (``mm > 0``) or inward by ``mm``.

    ``endocardial``: the LV pool grows into (or shrinks out of) the myocardium.
    ``epicardial``: the myocardium grows into (or shrinks out of) the fat.
    ``octant`` limits the move to one octant about the LV pool's centre.
    """
    read = truth.copy()
    if border == "endocardial":
        region, grow_into, shrink_to = truth == L.LV_POOL, L.LV_MYO, L.LV_MYO
        value = L.LV_POOL
    elif border == "epicardial":
        region = np.isin(truth, (L.LV_MYO, L.LV_POOL))
        grow_into, shrink_to, value = L.BACKGROUND, L.BACKGROUND, L.LV_MYO
    else:
        raise ValueError(border)
    if mm >= 0:
        dist = ndimage.distance_transform_edt(~region, sampling=spacing)
        change = (~region) & (dist <= mm) & (truth == grow_into)
        new = value
    else:
        dist = ndimage.distance_transform_edt(region, sampling=spacing)
        change = region & (dist <= -mm) & (truth == value)
        new = shrink_to
    if octant is not None:
        centre = np.array(ndimage.center_of_mass(truth == L.LV_POOL))
        idx = np.indices(truth.shape)
        oct_id = np.zeros(truth.shape, dtype=np.uint8)
        for axis in range(3):
            oct_id |= ((idx[axis] >= centre[axis]).astype(np.uint8) << axis)
        change &= oct_id == octant
    read[change] = new
    return read
