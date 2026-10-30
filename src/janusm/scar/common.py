"""Steps shared by JA29's QC and JA30's Scar-0: the carried wall, LIE smoothing, the remote.

All of it is on the LIE grid (JA29: the LIE is fixed and is never resampled).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from scipy import ndimage as ndi

#: JA30 common step: the registered LIE is smoothed by a Gaussian of FWHM 1.5 mm.
SMOOTH_FWHM_MM = 1.5
#: JA30 remote: the core voxels of the 6 lowest-median segments.
REMOTE_N_SEGMENTS = 6
#: Robust SD = 1.4826 x MAD (JA30).
MAD_TO_SD = 1.4826
#: A segment's core enters the remote ranking only with more than this many voxels (Kilo E5).
MIN_CORE_VOXELS = 20
#: Fixed: 2.3548 = 2 sqrt(2 ln 2).
FWHM_TO_SIGMA = 1.0 / (2.0 * np.sqrt(2.0 * np.log(2.0)))

_FACE = ndi.generate_binary_structure(3, 1)


@dataclass
class CarriedGeometry:
    """First-pass geometry carried onto the LIE grid (JA29).

    ``myo`` and ``cavity`` came through their signed distances; ``segments`` (AHA 1-17, 0 off the
    wall), ``u`` (JA2 depth, NaN off the wall) and ``column`` (the JA30 E-D 3-degree x 2 mm column
    id, -1 off the wall) by nearest neighbour.
    """

    myo: np.ndarray
    cavity: np.ndarray
    segments: np.ndarray
    u: np.ndarray
    column: np.ndarray
    spacing: np.ndarray
    affine: np.ndarray

    def core(self) -> np.ndarray:
        """Wall voxels at least one voxel inside both carried borders (JA30)."""
        return core_mask(self.myo)

    def d_endo_mm(self) -> np.ndarray:
        """Distance (mm) from each voxel centre to the carried endocardial surface, which lies
        half a voxel beyond the last cavity voxel (the :func:`janusm.geometry.depth` convention)."""
        if not self.cavity.any():
            return np.full(self.myo.shape, np.inf)
        h = 0.5 * float(np.mean(self.spacing))
        return np.maximum(ndi.distance_transform_edt(~self.cavity, sampling=self.spacing) - h, 0.0)


def core_mask(myo: np.ndarray) -> np.ndarray:
    """One-voxel (face) erosion of the wall: off both the endocardial and epicardial border."""
    return ndi.binary_erosion(myo, _FACE)


def smooth(lie: np.ndarray, spacing, fwhm_mm: float = SMOOTH_FWHM_MM) -> np.ndarray:
    """Gaussian smoothing of FWHM ``fwhm_mm`` on a grid of ``spacing`` mm."""
    sigma = fwhm_mm * FWHM_TO_SIGMA / np.asarray(spacing, float)
    return ndi.gaussian_filter(np.asarray(lie, np.float32), sigma)


@dataclass
class Remote:
    """Remote myocardium on the smoothed LIE (JA30): median and robust SD of the pooled core voxels
    of the ``REMOTE_N_SEGMENTS`` segments with the lowest core median."""

    median: float
    sd: float
    segments: List[int]
    n_voxels: int
    #: Core median of every eligible segment (more than MIN_CORE_VOXELS core voxels).
    segment_medians: dict
    #: The eligible segment with the highest core median (P-K's "brightest segment").
    brightest: int


def remote(
    smoothed: np.ndarray,
    segments: np.ndarray,
    core: np.ndarray,
    *,
    n_segments: int = REMOTE_N_SEGMENTS,
    min_core_voxels: int = MIN_CORE_VOXELS,
) -> Optional[Remote]:
    """The JA30 remote, or None when fewer than ``n_segments`` segments have a usable core."""
    med = {}
    for s in range(1, 18):
        v = smoothed[core & (segments == s)]
        if v.size > min_core_voxels:
            med[s] = float(np.median(v))
    if len(med) < n_segments:
        return None
    low = sorted(med, key=lambda s: (med[s], s))[:n_segments]
    pool = smoothed[core & np.isin(segments, low)]
    mu = float(np.median(pool))
    sd = float(MAD_TO_SD * np.median(np.abs(pool - mu)))
    top = max(med, key=lambda s: (med[s], -s))
    return Remote(
        median=mu,
        sd=sd,
        segments=sorted(low),
        n_voxels=int(pool.size),
        segment_medians=med,
        brightest=top,
    )
