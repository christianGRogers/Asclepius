"""Janus-M read seeds (JA7): ``heartchambers_highres``, mapped to JA1, coarsened to 2 mm
and smoothed (Golf's guard against anchoring).

A seed is a deliberately rough start: fine enough to save the reader drawing the
heart, too coarse to be accepted as it is. Steps, per case:

1. map TotalSegmentator ``heartchambers_highres`` to JA1 (myocardium -> 1, LV -> 2,
   RV -> 3, LA -> 4; RA, aorta and pulmonary artery -> 0);
2. per class, a soft mask averaged onto a 2 mm grid (an anti-aliasing blur then
   linear resampling);
3. smoothed on that grid (Gaussian, ``smooth_mm``);
4. resampled back to the CT grid and assigned by largest soft value (background
   wins unless a class reaches 0.5).

The 2 mm comes from JA7; ``smooth_mm`` (1 mm) is confirmed by border protocol v1
(Hotel v3 section 5.1).

This module only transforms arrays. The Fir job that runs TotalSegmentator and
then this is ``tools/janusm/make_seeds.py``; the lead runs it (JA10).
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence

import numpy as np
from scipy import ndimage

from . import labels as L

#: TotalSegmentator ``heartchambers_highres`` class name -> JA1 value.
TS_TO_JA1: Dict[str, int] = {
    "heart_myocardium": L.LV_MYO,
    "heart_ventricle_left": L.LV_POOL,
    "heart_ventricle_right": L.RV_POOL,
    "heart_atrium_left": L.LA_POOL,
}
#: The published multilabel order, used only when TotalSegmentator is not installed
#: to say otherwise (as Juliet's ``geometry_m0.py``).
TS_FALLBACK_IDS: Dict[int, str] = {
    1: "heart_myocardium", 2: "heart_atrium_left", 3: "heart_ventricle_left",
    4: "heart_atrium_right", 5: "heart_ventricle_right", 6: "aorta", 7: "pulmonary_artery",
}

COARSE_MM = 2.0
SMOOTH_MM = 1.0


def ts_class_ids() -> Dict[int, str]:
    """TotalSegmentator's multilabel ids for ``heartchambers_highres``."""
    try:
        from totalsegmentator.map_to_binary import class_map

        return {int(k): v for k, v in class_map["heartchambers_highres"].items()}
    except Exception:  # noqa: BLE001 - no TotalSegmentator here: the published order
        return dict(TS_FALLBACK_IDS)


def map_to_ja1(multilabel: np.ndarray, ids: Optional[Mapping[int, str]] = None) -> np.ndarray:
    """A ``heartchambers_highres`` multilabel volume in JA1's values (uint8)."""
    ids = ids or ts_class_ids()
    out = np.zeros(multilabel.shape, dtype=np.uint8)
    for value, name in ids.items():
        if name in TS_TO_JA1:
            out[multilabel == value] = TS_TO_JA1[name]
    return out


def coarsen(labels: np.ndarray, spacing: Sequence[float], coarse_mm: float = COARSE_MM,
            smooth_mm: float = SMOOTH_MM) -> np.ndarray:
    """``labels`` (JA1 values) coarsened to ``coarse_mm`` and smoothed, on its own grid."""
    spacing = np.asarray(spacing, dtype=float)
    nz = np.nonzero(labels)
    out = np.zeros(labels.shape, dtype=np.uint8)
    if not nz[0].size:
        return out
    # Work on the heart's box (plus a margin), not the whole scan.
    pad = np.ceil((2 * coarse_mm + 3 * smooth_mm) / spacing).astype(int)
    box = tuple(slice(max(0, int(i.min()) - p), min(s, int(i.max()) + 1 + p))
                for i, p, s in zip(nz, pad, labels.shape))
    sub = labels[box]
    factor = spacing / coarse_mm
    coarse_shape = np.maximum(1, np.round(np.array(sub.shape) * factor)).astype(int)
    soft = []
    for value in L.REQUIRED:
        m = (sub == value).astype(np.float32)
        # Anti-aliasing before downsampling: sigma ~ half a coarse voxel, in voxels.
        m = ndimage.gaussian_filter(m, sigma=(coarse_mm / 2.0) / spacing)
        c = ndimage.zoom(m, coarse_shape / np.array(sub.shape), order=1)
        if smooth_mm > 0:
            c = ndimage.gaussian_filter(c, sigma=smooth_mm / coarse_mm)
        back = ndimage.zoom(c, np.array(sub.shape) / np.array(c.shape), order=1)
        # zoom can be off by one voxel; pad or trim to the box.
        fixed = np.zeros(sub.shape, dtype=np.float32)
        sl = tuple(slice(0, min(a, b)) for a, b in zip(sub.shape, back.shape))
        fixed[sl] = back[sl]
        soft.append(fixed)
    stack = np.stack(soft)
    best = stack.argmax(axis=0)
    keep = stack.max(axis=0) >= 0.5
    sub_out = np.where(keep, np.asarray(L.REQUIRED, dtype=np.uint8)[best], 0).astype(np.uint8)
    out[box] = sub_out
    return out


def make_seed(multilabel: np.ndarray, spacing: Sequence[float],
              ids: Optional[Mapping[int, str]] = None, coarse_mm: float = COARSE_MM,
              smooth_mm: float = SMOOTH_MM) -> np.ndarray:
    return coarsen(map_to_ja1(multilabel, ids), spacing, coarse_mm, smooth_mm)
