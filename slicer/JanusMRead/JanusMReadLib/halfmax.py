"""The half-maximum helper (Janus-M read protocol v1, section 3), free of Slicer.

A border lies halfway between the plateaus on either side of it. The plateaus are
measured from the seed when a case opens (a blank case: from ROIs the reader
places), and for the border being drawn the module opens on the **border window**
(Hotel v2 section 5.4, JA21): level = (p1 + p2) / 2, width = 1.5 x |p1 - p2|. A fixed
800 / 300 window stays available, but is not the default.

numpy only (Slicer bundles it). The erosions here are voxel steps, an
approximation of the server's millimetre distances: this is a drawing aid, and
the server's automatic check (``janusm_reads.checker``) is the authority.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, Optional, Sequence, Tuple

import numpy as np

LV_BLOOD = "LV blood"
MYOCARDIUM = "myocardium"
RV_BLOOD = "RV blood"
FAT = "fat"

#: The plateaus a reader measures, in the order the panel shows them.
PLATEAUS = (LV_BLOOD, MYOCARDIUM, RV_BLOOD, FAT)

ENDOCARDIAL = "endocardial"
EPICARDIAL = "epicardial"
SEPTAL_RV = "septal (RV side)"

#: border -> the two plateaus it lies between (protocol section 3).
BORDERS: Dict[str, Tuple[str, str]] = {
    ENDOCARDIAL: (LV_BLOOD, MYOCARDIUM),
    EPICARDIAL: (MYOCARDIUM, FAT),
    SEPTAL_RV: (RV_BLOOD, MYOCARDIUM),
}

#: The border window's width, as a multiple of the gap between its two plateaus.
BORDER_WIDTH_FACTOR = 1.5
#: The narrowest border window (HU), for plateaus measured almost equal.
MIN_BORDER_WIDTH_HU = 10.0
#: The border a case opens on.
DEFAULT_BORDER = "endocardial"
#: The fixed window, available on request (never the default): width, level.
FIXED_WINDOW = (800.0, 300.0)

#: Epicardial fat is measured inside this HU window (JA11).
FAT_WINDOW_HU = (-180.0, 0.0)

#: Depths used when the plateaus come from labels (protocol section 4.2).
POOL_DEPTH_MM = 2.0
MYO_DEPTH_MM = 1.0
FAT_SHELL_MM = (1.0, 4.0)

# The label values of janusm_reads.labels (JA1); repeated so this file needs nothing
# but numpy, and checked against labels.py by the tests.
LV_MYO, LV_POOL, RV_POOL, LA_POOL = 1, 2, 3, 4


def threshold(border: str, plateaus: Dict[str, Optional[float]]) -> float:
    """The half-maximum threshold of one border. ``ValueError`` names what is missing."""
    if border not in BORDERS:
        raise ValueError(f"unknown border {border!r}")
    a, b = BORDERS[border]
    missing = [name for name in (a, b) if plateaus.get(name) is None]
    if missing:
        raise ValueError("Measure the {} plateau first.".format(" and ".join(missing)))
    return (float(plateaus[a]) + float(plateaus[b])) / 2.0


def thresholds(plateaus: Dict[str, Optional[float]]) -> Dict[str, float]:
    """Every border whose two plateaus are known -> its threshold."""
    out = {}
    for border in BORDERS:
        try:
            out[border] = threshold(border, plateaus)
        except ValueError:
            continue
    return out


def warnings(plateaus: Dict[str, Optional[float]]) -> list:
    """Plateaus that cannot be right, in words a reader can act on."""
    out = []
    myo = plateaus.get(MYOCARDIUM)
    for pool in (LV_BLOOD, RV_BLOOD):
        value = plateaus.get(pool)
        if value is not None and myo is not None and value <= myo:
            out.append(f"The {pool} plateau ({value:.0f} HU) is not brighter than the "
                       f"myocardium ({myo:.0f} HU); measure both again away from any edge.")
    fat = plateaus.get(FAT)
    if fat is not None and not FAT_WINDOW_HU[0] <= fat <= FAT_WINDOW_HU[1]:
        out.append(f"The fat plateau ({fat:.0f} HU) is outside {FAT_WINDOW_HU[0]:.0f}.."
                   f"{FAT_WINDOW_HU[1]:.0f} HU; place the ROI in epicardial fat.")
    return out


def window_for(border: str, plateaus: Dict[str, Optional[float]]) -> Tuple[float, float]:
    """``(window, level)`` for drawing one border: level at its half-maximum, width
    1.5 x the gap between its plateaus."""
    level = threshold(border, plateaus)
    a, b = BORDERS[border]
    width = BORDER_WIDTH_FACTOR * abs(float(plateaus[a]) - float(plateaus[b]))
    return max(MIN_BORDER_WIDTH_HU, width), level


# ------------------------------------------------------------ the profile


#: The columns of :func:`profile_table`, in order.
PROFILE_COLUMNS = ("signed distance (mm)", "median HU", "half-maximum", "plateau inside",
                   "plateau outside")


def profile_table(profile: Dict) -> np.ndarray:
    """The plot of a returned read's border profile (``ReadInfo.check_profile[border]``):
    HU against signed distance from the read's border (+ away from the region), with
    the half level and both plateaus as flat lines. Columns: :data:`PROFILE_COLUMNS`."""
    s = np.asarray(profile.get("s_mm") or [], dtype=float)
    hu = np.asarray(profile.get("hu") or [], dtype=float)
    if not s.size or s.size != hu.size:
        raise ValueError("This border has no profile to show.")
    pl = list(profile.get("plateausHU") or [])
    pl = (pl + [None, None])[:2]
    half = profile.get("thresholdHU")
    cols = [s, hu]
    for value in (half, pl[0], pl[1]):
        cols.append(np.full(s.shape, np.nan if value is None else float(value)))
    return np.stack(cols, axis=1)


def profile_caption(border: str, profile: Dict) -> str:
    """One line under the plot, in the canonical sign (JA44)."""
    offset = profile.get("offsetMm")
    if offset is None:
        return "{}: no half-maximum crossing near your border.".format(border)
    where = "past" if offset > 0 else "short of"
    return "{}: your border is {:.2f} mm {} the half-maximum edge{}.".format(
        border, abs(offset), where, " (this failed the check)" if profile.get("failed") else "")


# ------------------------------------------------------------ morphology


def _steps(mm: float, spacing: Sequence[float]) -> int:
    return max(1, int(math.ceil(float(mm) / max(1e-6, min(float(s) for s in spacing)))))


def erode(mask: np.ndarray, steps: int) -> np.ndarray:
    """6-neighbour erosion, ``steps`` times; outside the array counts as background."""
    out = mask.astype(bool)
    for _ in range(int(steps)):
        if not out.any():
            break
        padded = np.pad(out, 1, constant_values=False)
        core = padded[1:-1, 1:-1, 1:-1].copy()
        for axis in range(3):
            for shift in (0, 2):
                index = [slice(1, -1)] * 3
                index[axis] = slice(shift, shift + out.shape[axis])
                core &= padded[tuple(index)]
        out = core
    return out


def dilate(mask: np.ndarray, steps: int) -> np.ndarray:
    """6-neighbour dilation, ``steps`` times; nothing grows in from outside the array."""
    out = mask.astype(bool)
    for _ in range(int(steps)):
        padded = np.pad(out, 1, constant_values=False)
        grown = out.copy()
        for axis in range(3):
            for shift in (0, 2):
                index = [slice(1, -1)] * 3
                index[axis] = slice(shift, shift + out.shape[axis])
                grown |= padded[tuple(index)]
        out = grown
    return out


def _median(ct: np.ndarray, mask: np.ndarray) -> Optional[float]:
    # The median, as the server's checker takes: a seed drawn a little off puts a
    # rim of the neighbouring tissue in the region, which moves a mean and not this.
    return float(np.median(ct[mask])) if mask.any() else None


def plateaus_from_labels(ct: np.ndarray, labels: np.ndarray,
                         spacing: Sequence[float]) -> Dict[str, Optional[float]]:
    """Plateaus (medians) measured from a label volume on the CT grid (the seed or the
    reader's segments): pools well inside the pool, mid-wall myocardium, and fat in
    a shell outside the myocardium within the fat window. ``None`` where there is
    nothing to measure.
    """
    ct = np.asarray(ct, dtype=np.float32)
    labels = np.asarray(labels)
    out: Dict[str, Optional[float]] = {}
    for name, value in ((LV_BLOOD, LV_POOL), (RV_BLOOD, RV_POOL)):
        region = labels == value
        deep = erode(region, _steps(POOL_DEPTH_MM, spacing))
        out[name] = _median(ct, deep if deep.any() else region)
    myo = labels == LV_MYO
    mid = erode(myo, _steps(MYO_DEPTH_MM, spacing))
    out[MYOCARDIUM] = _median(ct, mid if mid.any() else myo)
    heart = np.isin(labels, (LV_MYO, LV_POOL))
    near, far = (_steps(mm, spacing) for mm in FAT_SHELL_MM)
    shell = dilate(heart, far) & ~dilate(heart, near) & (labels == 0)
    shell &= (ct >= FAT_WINDOW_HU[0]) & (ct <= FAT_WINDOW_HU[1])
    out[FAT] = _median(ct, shell)
    return out


def box_slices(corners_ijk: Iterable[Sequence[float]],
               shape: Sequence[int]) -> Optional[Tuple[slice, slice, slice]]:
    """Array slices ``(k, j, i)`` of the voxel box that holds an ROI, from its
    corners in IJK. ``None`` when the box misses the volume."""
    pts = np.asarray(list(corners_ijk), dtype=float)
    lo = np.floor(pts.min(axis=0) + 0.5).astype(int)
    hi = np.floor(pts.max(axis=0) + 0.5).astype(int)
    # shape is the array's (k, j, i); corners are (i, j, k).
    dims = (int(shape[2]), int(shape[1]), int(shape[0]))
    lo = np.maximum(lo, 0)
    hi = np.minimum(hi, np.array(dims) - 1)
    if np.any(hi < lo):
        return None
    return (slice(lo[2], hi[2] + 1), slice(lo[1], hi[1] + 1), slice(lo[0], hi[0] + 1))


def roi_mean(ct: np.ndarray, slices: Optional[Tuple[slice, slice, slice]]) -> Optional[float]:
    if slices is None:
        return None
    block = np.asarray(ct)[slices]
    return float(block.mean()) if block.size else None
