"""Janus-M border-error harness (JA15, JA16): one error model, one unit, on synthetic phantoms.

Round 2 left three perturbation harnesses (``experiments/JanusM/{Hotel,Lima,India}``). JA15
(``vault/JanusM/Judgements/Round 2 - rest-ccta.md``) keeps one error model and one set of measures,
shared by the harness, the read checks and the scorer. This module is that code. It works on label
maps already in memory and never opens a case, so it cannot touch a held-out subject.

**The error model (JA15).** Golf's half-voxel-corrected signed distance of each border on the
native 0.5 mm grid, plus an independent smooth Gaussian field per border (8 mm correlation; 4 and
16 mm as sensitivity), plus a constant bias per border. This is India's U and Lima's ``lima_c8``.
The correlation length is the Gaussian kernel's standard deviation in mm, as both coded it. The
field is rescaled to the nominal standard deviation, but results are indexed by what was realised,
never by the nominal value.

**The measures (JA8, JA15).** Per border (endocardium = surface of the LV blood pool; epicardium =
surface of blood pool plus myocardium):

- ``assd_pp``: Hotel E6's sub-voxel point-to-plane ASSD in mm (JA39). It scores JA8's d (both terms)
  and the absolute ASSD guard.
- ``surface_assd``: the voxel ASSD in mm between the two masks' surface voxels. Reported beside pp
  (JA39); the read checks and JA21 anchoring keep it.
- ``signed_bias``: mean signed normal displacement in mm, + outward. It is the volume change
  divided by the mean area of the two surfaces, the area taken from marching cubes on each mask
  smoothed by one voxel. For a uniform offset b of a smooth closed surface this is b to second
  order (the curvature terms cancel in the mean area). The Round 2 estimators sampled a voxel
  signed-distance map at surface voxels and read about 0.35-0.45 mm for a true 0.5 mm shift (Round
  2 judgement section 1.3); ``validate_bias_estimator`` is JA16's check of this one. It is the
  guard's estimator (JA37).
- ``signed_bias_pp``: Hotel E6's point-to-plane signed bias, same sign. Reported beside
  ``signed_bias`` for JA37's transfer check (median |vol - pp| over the first decision reads).
- ``segment_thickness`` / ``thickness_error``: the geometry module's wall thickness per AHA segment
  (``janusm.geometry.layers``: the median thickness of the segment's mid-wall voxels), and the
  error summarised as the **median over segments 1-16** (JA15).
- ``sta``: Kilo's segmental transmurality agreement (16 segments x 4 virtual subendocardial scars,
  Kim bins). Still reported (JA8, JA15).
- ``mean_abs_d``: Hotel's mean |d| (changed volume / mean area). Reported beside ASSD, never in its
  place (JA15).

**JA16, JA61.** The signed-bias guard is 0.3 mm only if the estimator recovers a known 0.5 mm
shift, in each direction and on each border, to within 0.05 mm here; otherwise it stays 0.5 mm.
``validate_bias_estimator`` runs that check on analytic phantoms whose true offset is exact, and
returns the guard it supports. JA61 adds the open-base check (``open_base=True``): masks cut at a
base plane, as real ones are, measured in JA37's band (``ja37_band``: +-3 mm of the border, less
3 mm around label 4 and the open LV-pool faces). That check, on India's E6-style phantom, misses
0.05 mm on the epicardium, so the guard in force (``BIAS_GUARD_VALIDATED_MM``) is 0.5 mm.
``transfer_check`` is JA37's check on the first 20 decision reads (JA62).

**Known shifts are exact (JA38).** ``perturb``'s biases are nominal: the voxel signed-distance rule
realises about 1.3x. ``run`` records the nominal and the realised bias side by side. A fixture
that needs a known shift uses ``exact_shift_phantom``, whose borders are exact signed-distance
level sets.

**Point-to-plane (pp) surfaces.** Each mask is smoothed by a Gaussian of 0.7 voxel, its 0.5 level
is found by linear interpolation along each grid axis, and each crossing is kept on its dominant
normal axis, weighted by the area it stands for. A point's distance to the other surface is taken
along that surface's normal at its nearest point (point to plane), both ways. Hotel E6 validated it
within 0.03 mm of the truth up to 0.5 mm and 0.07 mm at 1.0 mm, on two grids, oblique and rough
walls (JA39).
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes, mesh_surface_area

from janusm import geometry as G
from segtrain.metrics import surface_distances

#: Bump on any change that can move a reported number.
HARNESS_VERSION = "1.2.0"

GRID_MM = 0.5  # JA15: the native grid
CORR_MM = 8.0  # JA15: primary correlation length
CORR_SENSITIVITY_MM = (4.0, 16.0)

BIAS_CHECK_SHIFT_MM = 0.5  # JA16: the known shift the estimator must recover
BIAS_CHECK_TOLERANCE_MM = 0.05
BIAS_GUARD_TIGHT_MM = 0.3  # JA16: the guard a check supports when it passes
BIAS_GUARD_FALLBACK_MM = 0.5
#: The guard from the freeze PR on (JA61, R4-S4). It was 0.3 mm. JA61's open-base check, on India's
#: E6-style phantom with JA37's band (two grids, three walls, both borders, +-0.3 / +-0.5 mm),
#: misses 0.05 mm on the epicardium at +-0.5 mm (worst 0.068 mm; the endocardium is within
#: 0.015 mm), and ``validate_bias_estimator(open_base=True)`` on the cut capsule misses it narrowly
#: (worst 0.0504 mm, epicardium; endocardium 0.024 mm). The band as ruled keeps the cut myocardial
#: base cap, which adjoins label 0 but is no LV-pool face, so it enters the area and not the
#: volume change. JA61: the guard is 0.5 mm.
BIAS_GUARD_VALIDATED_MM = BIAS_GUARD_FALLBACK_MM

PP_SMOOTH_VOX = 0.7  # Hotel E6: the Gaussian (voxels) whose 0.5 level is the sub-voxel surface
#: JA39's fixture tolerances as JA65 restates them: |pp ASSD - truth| (and |pp bias - truth|) for
#: displacements up to the key (mm), compared unrounded as ``abs(err) <= tol``. Hotel E6's worst is
#: 0.032 at 0.5 mm and 0.067 at 1.0 mm; Lima E7's is 0.0322 at 0.5 mm.
PP_ASSD_TOLERANCE_MM = {0.5: 0.035, 1.0: 0.07}

#: JA37 / JA61: the band is +-3 mm of the border, less 3 mm around label 4 and the open pool faces.
JA37_BAND_MM = 3.0
#: JA62 / R4-S5: the transfer check runs on the first 20 decision cases, limit 0.05 mm.
TRANSFER_N_FIRST = 20
TRANSFER_LIMIT_MM = 0.05

TAUS = (0.15, 0.40, 0.65, 0.90)  # STA virtual-scar depths
KIM = np.array([0.0, 0.25, 0.50, 0.75, 1.0001])
MIN_SEGMENT_VOXELS = 50


# ---------------------------------------------------------------------------------- error model
def _spacing(spacing) -> np.ndarray:
    sp = np.broadcast_to(np.asarray(spacing, float), (3,)).copy()
    if (sp <= 0).any():
        raise ValueError(f"bad spacing {spacing}")
    return sp


def corrected_sdf(mask, spacing) -> np.ndarray:
    """Golf's signed distance (mm, negative inside): the border lies half a voxel beyond the last
    inside voxel centre, so a face-neighbour pair across the border reads -h/2 and +h/2."""
    m = np.asarray(mask, bool)
    sp = _spacing(spacing)
    h = float(sp.mean()) / 2
    di = ndi.distance_transform_edt(m, sampling=sp)
    do = ndi.distance_transform_edt(~m, sampling=sp)
    return np.where(m, h - di, do - h).astype(np.float32)


def smooth_field(shape, spacing, sigma_mm: float, corr_mm: float, rng) -> np.ndarray:
    """Zero-mean Gaussian random field with standard deviation ``sigma_mm`` over the array, smoothed
    by a Gaussian kernel of standard deviation ``corr_mm``."""
    if sigma_mm == 0:
        return np.zeros(shape, np.float32)
    sp = _spacing(spacing)
    f = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), corr_mm / sp)
    f -= f.mean()
    return (f * (sigma_mm / (f.std() + 1e-12))).astype(np.float32)


def borders(labels) -> Tuple[np.ndarray, np.ndarray]:
    """(cavity, solid): the LV blood pool, and blood pool plus myocardium. Their surfaces are the
    endocardium and the epicardium."""
    lab = np.asarray(labels)
    cav = lab == G.LV
    return cav, cav | (lab == G.MYO)


def relabel(ref_labels, cavity, solid) -> np.ndarray:
    """A JA1 label map with new LV borders. RV and LA keep the reference voxels the new solid does
    not cover; voxels the wall leaves become background."""
    ref = np.asarray(ref_labels)
    cavity = np.asarray(cavity, bool)
    solid = np.asarray(solid, bool) | cavity
    out = np.zeros(ref.shape, np.int16)
    for k in (G.RV, G.LA):
        out[(ref == k) & ~solid] = k
    out[solid] = G.MYO
    out[cavity] = G.LV
    return out


def perturb(
    labels,
    spacing,
    *,
    sigma_endo: float = 0.0,
    sigma_epi: float = 0.0,
    bias_endo: float = 0.0,
    bias_epi: float = 0.0,
    corr_mm: float = CORR_MM,
    rng=None,
) -> np.ndarray:
    """The JA15 error model applied to one label map. Biases are in mm, + outward (endocardium
    outward = a larger cavity). The two borders get independent fields. Returns new labels."""
    if rng is None:
        rng = np.random.default_rng()
    sp = _spacing(spacing)
    cav, sol = borders(labels)
    if not cav.any() or not (sol & ~cav).any():
        raise ValueError("perturb needs LV myocardium (1) and LV blood pool (2)")
    n_endo = smooth_field(cav.shape, sp, sigma_endo, corr_mm, rng)
    n_epi = smooth_field(cav.shape, sp, sigma_epi, corr_mm, rng)
    cav_p = (corrected_sdf(cav, sp) + n_endo - bias_endo) < 0
    sol_p = ((corrected_sdf(sol, sp) + n_epi - bias_epi) < 0) | cav_p
    return relabel(labels, cav_p, sol_p)


# ---------------------------------------------------------------------------------- measures
def surface_assd(a, b, spacing) -> float:
    """Symmetric surface ASSD (mm) between the surface voxels of two masks; NaN if one is empty."""
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    da, db = surface_distances(a, b, _spacing(spacing))  # segtrain's, one voxel ASSD (JA65)
    if not da.size or not db.size:
        return float("nan")
    return float((da.sum() + db.sum()) / (da.size + db.size))


def _crop_pair(ref, test, roi, margin: int):
    """The two masks (and ROI) cut to their joint bounding box plus ``margin`` voxels, clipped to
    the array, so the pp surfaces of a small heart in a large volume cost what the heart costs.
    The Gaussian sees the same values either way: outside the box the masks are empty."""
    nz = np.argwhere(ref | test)
    lo = np.maximum(nz.min(0) - margin, 0)
    hi = np.minimum(nz.max(0) + margin + 1, ref.shape)
    box = tuple(slice(a, b) for a, b in zip(lo, hi))
    return ref[box], test[box], (None if roi is None else roi[box])


def surface_points(mask, spacing, roi=None, smooth_vox: float = PP_SMOOTH_VOX):
    """(points mm, outward unit normals, area weights mm^2) of a mask's sub-voxel surface (E6).

    The surface is the 0.5 level of the mask smoothed by a Gaussian of ``smooth_vox`` voxels,
    found by linear interpolation between grid neighbours along each axis. Each crossing is kept
    only on its dominant normal axis and weighted by the area it stands for (the product of the
    other two spacings over |n_axis|). ``roi`` (bool, same shape) keeps the crossings whose lower
    voxel lies in it. Points are in mm from the array's first voxel corner."""
    sp = _spacing(spacing)
    phi = ndi.gaussian_filter(np.asarray(mask, bool).astype(np.float32), smooth_vox) - 0.5
    gr = np.gradient(phi, *sp)
    P, N, W = [], [], []
    for a in range(3):
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[a], sl1[a] = slice(0, -1), slice(1, None)
        sl0, sl1 = tuple(sl0), tuple(sl1)
        p0, p1 = phi[sl0], phi[sl1]
        cross = (p0 > 0) != (p1 > 0)
        if roi is not None:
            cross &= np.asarray(roi, bool)[sl0]
        idx = np.argwhere(cross)
        v0, v1 = p0[cross], p1[cross]
        t = v0 / (v0 - v1)
        g0 = np.stack([g[sl0][cross] for g in gr], 1)
        g1 = np.stack([g[sl1][cross] for g in gr], 1)
        g = g0 + t[:, None] * (g1 - g0)
        n = -g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)  # phi > 0 inside
        dom = np.argmax(np.abs(n), 1) == a
        pos = (idx + 0.5).astype(float)
        pos[:, a] += t
        pos = pos * sp
        o = [k for k in range(3) if k != a]
        P.append(pos[dom])
        N.append(n[dom])
        W.append(sp[o[0]] * sp[o[1]] / np.abs(n[dom, a]))
    return np.concatenate(P), np.concatenate(N), np.concatenate(W)


def _pp(ref, test, spacing, roi=None) -> Tuple[float, float]:
    """(signed bias, ASSD) in mm by symmetric point to plane; + = ``test`` outside ``ref``."""
    ref, test = np.asarray(ref, bool), np.asarray(test, bool)
    if ref.shape != test.shape:
        raise ValueError(f"masks differ in shape: {ref.shape} vs {test.shape}")
    if roi is not None:
        roi = np.asarray(roi, bool)
        if roi.shape != ref.shape:
            raise ValueError("roi differs in shape from the masks")
    sp = _spacing(spacing)
    if not ref.any() or not test.any():
        return float("nan"), float("nan")
    ref, test, roi = _crop_pair(ref, test, roi, int(np.ceil(4 * PP_SMOOTH_VOX)) + 3)
    pt, nt, wt = surface_points(test, sp, roi)
    pr, nr, wr = surface_points(ref, sp, roi)
    if not len(pt) or not len(pr):
        return float("nan"), float("nan")
    _, ir = cKDTree(pr).query(pt)
    d_tr = np.einsum("ij,ij->i", pt - pr[ir], nr[ir])  # + : test's surface outside ref
    _, it = cKDTree(pt).query(pr)
    d_rt = np.einsum("ij,ij->i", pr - pt[it], nt[it])  # + : ref's surface outside test
    bias = 0.5 * (np.average(d_tr, weights=wt) - np.average(d_rt, weights=wr))
    assd = (np.sum(wt * np.abs(d_tr)) + np.sum(wr * np.abs(d_rt))) / (wt.sum() + wr.sum())
    return float(bias), float(assd)


def signed_bias_pp(ref, test, spacing, roi=None) -> float:
    """Hotel E6's point-to-plane signed bias (mm, + = ``test`` lies outside ``ref``), symmetric:
    half the difference of the area-weighted mean signed distances in the two directions. NaN if
    either mask is empty. ``roi`` restricts both surfaces (for example, away from a valve plane)."""
    return _pp(ref, test, spacing, roi)[0]


def assd_pp(ref, test, spacing, roi=None) -> float:
    """Hotel E6's point-to-plane ASSD (mm, JA39): the area-weighted mean |distance| of each
    sub-voxel surface to the other's tangent plane, pooled both ways. NaN if either is empty."""
    return _pp(ref, test, spacing, roi)[1]


def surface_area(mask, spacing, smooth_vox: float = 1.0, roi=None) -> float:
    """Surface area (mm^2) of a mask: marching cubes at 0.5 on the mask smoothed by a Gaussian of
    ``smooth_vox`` voxels, which removes most of the staircase's excess area. ``roi`` (bool, the
    mask's shape) counts only the faces whose centroids lie in it (nearest voxel; JA61)."""
    m = np.asarray(mask, bool)
    sp = _spacing(spacing)
    if not m.any():
        return 0.0
    pad = int(np.ceil(4 * smooth_vox)) + 2
    nz = np.argwhere(m)
    lo = nz.min(0)
    box = tuple(slice(a, b + 1) for a, b in zip(lo, nz.max(0)))
    f = np.pad(m[box].astype(np.float32), pad)
    if smooth_vox > 0:
        f = ndi.gaussian_filter(f, smooth_vox)
    v, faces, _, _ = marching_cubes(f, 0.5, spacing=tuple(sp))
    if roi is None:
        return float(mesh_surface_area(v, faces))
    roi = np.asarray(roi, bool)
    if roi.shape != m.shape:
        raise ValueError("roi differs in shape from the mask")
    c = v[faces].mean(1) / sp  # face centroids, padded-box voxel index
    ijk = np.rint(c).astype(int) - pad + lo
    ok = ((ijk >= 0) & (ijk < np.array(m.shape))).all(1)
    keep = np.zeros(len(faces), bool)
    keep[ok] = roi[tuple(ijk[ok].T)]
    return float(mesh_surface_area(v, faces[keep])) if keep.any() else 0.0


def signed_bias(ref, test, spacing, smooth_vox: float = 1.0, roi=None) -> float:
    """Mean signed displacement (mm, + = ``test`` lies outside ``ref``) of one border: the volume
    change over the mean area of the two surfaces. NaN if either mask is empty.

    ``roi`` (bool, the masks' shape; JA61) restricts both terms: the volume change counts only
    the voxels in it, and each marching-cubes area only the faces whose centroids lie in it.
    The guard passes JA37's band (``ja37_band``). On whole masks that are open (cut at a base
    plane, as every real LV mask is) the fixed cap enters the area but not the volume change, and
    the estimate under-reads by about 24 % (India IG1, JA61's record).

    Disclosed error (JA37): on exact closed shells the estimator is within 0.01 mm (E4) and on
    JA16's phantoms within 0.05 mm; in the band on open-base phantoms it is checked by
    ``validate_bias_estimator(open_base=True)``. On real walls JA37 disclosed that the error is
    not known from phantoms alone; the transfer check (``transfer_check``) measures how far it
    sits from the point-to-plane estimator on the first 20 decision reads before any seal read."""
    ref, test = np.asarray(ref, bool), np.asarray(test, bool)
    if ref.shape != test.shape:
        raise ValueError(f"masks differ in shape: {ref.shape} vs {test.shape}")
    sp = _spacing(spacing)
    if not ref.any() or not test.any():
        return float("nan")
    if roi is not None:
        roi = np.asarray(roi, bool)
        if roi.shape != ref.shape:
            raise ValueError("roi differs in shape from the masks")
    area = 0.5 * (surface_area(ref, sp, smooth_vox, roi) + surface_area(test, sp, smooth_vox, roi))
    if area <= 0:
        return float("nan")
    if roi is None:
        dv = int(test.sum()) - int(ref.sum())
    else:
        dv = int((test & roi).sum()) - int((ref & roi).sum())
    return float(dv * float(np.prod(sp)) / area)


def ja37_band(ref_labels, spacing, border: str, width_mm: float = JA37_BAND_MM) -> np.ndarray:
    """JA37's band (JA61) for one border of the reference read: the voxels within +-``width_mm``
    of that border, less the voxels within ``width_mm`` of label 4 (LA) and of any LV-pool face
    adjoining label 0 (the outflow and the aortic opening, which the labels mark only by being
    open; the array's edge counts as label 0). No aorta label is needed.

    Distances: to the border by Golf's corrected signed distance (the border half a voxel beyond
    the last inside voxel centre); to label 4 from voxel centre to voxel centre; to an open pool
    face from the voxel centre to the face's centre."""
    if border not in ("endo", "epi"):
        raise ValueError(f"border must be 'endo' or 'epi', not {border!r}")
    lab = np.asarray(ref_labels)
    sp = _spacing(spacing)
    cav, sol = borders(lab)
    m = cav if border == "endo" else sol
    if not m.any():
        return np.zeros(lab.shape, bool)
    band = np.abs(corrected_sdf(m, sp)) <= width_mm
    la = lab == G.LA
    if la.any():
        band &= ndi.distance_transform_edt(~la, sampling=sp) > width_mm
    # open pool faces: a pool voxel and a face neighbour of label 0 (padding = label 0)
    pool = np.pad(cav, 1)
    bg = np.pad(lab == 0, 1, constant_values=True)
    centres = []
    for a in range(3):
        for step in (1, -1):
            nb = np.roll(bg, -step, axis=a)  # nb[i] = bg[i + step]
            idx = np.argwhere(pool & nb).astype(float)
            idx[:, a] += 0.5 * step
            centres.append(idx)
    c = np.concatenate(centres)
    if len(c):
        c = (c - 1.0) * sp  # unpad, mm
        cand = np.argwhere(band)
        d, _ = cKDTree(c).query(cand * sp, distance_upper_bound=width_mm + 1e-9)
        near = np.isfinite(d) & (d <= width_mm)
        band[tuple(cand[near].T)] = False
    return band


def mean_abs_d(ref, test, spacing, smooth_vox: float = 1.0) -> float:
    """Hotel's mean |d| (mm): changed volume over the mean area. Reported beside ASSD only."""
    ref, test = np.asarray(ref, bool), np.asarray(test, bool)
    sp = _spacing(spacing)
    area = 0.5 * (surface_area(ref, sp, smooth_vox) + surface_area(test, sp, smooth_vox))
    if area <= 0:
        return float("nan")
    return float(int((ref ^ test).sum()) * float(np.prod(sp)) / area)


def segment_thickness(
    labels, spacing=None, affine=None, segments=None
) -> Tuple[Dict[int, float], Optional[np.ndarray]]:
    """({segment: wall mm} for AHA segments 1-16, the segment map) by the geometry module: JA2
    equal-thickness depth, JA3 segments (derived from ``labels`` unless given), and the per-segment
    wall of ``janusm.geometry.layers``. Empty if the AHA derivation fails."""
    lab = np.asarray(labels)
    dep = G.depth(lab, spacing=spacing, affine=affine)
    if segments is None:
        segments = G.aha17(lab, spacing=spacing, affine=affine).segments
    if segments is None:
        return {}, None
    sp = np.asarray(G._affine(lab.shape, spacing, affine)[1])
    reg = G.layers(dep, sp, segments).regions
    walls = {
        k: float(reg[k]["wall_mm"])
        for k in range(1, 17)
        if k in reg and reg[k]["n_voxels"] > MIN_SEGMENT_VOXELS
    }
    return walls, segments


def thickness_error(ref_walls: Dict[int, float], test_walls: Dict[int, float]) -> dict:
    """JA15's thickness summary: the median over shared segments 1-16 of |test - ref| (and of the
    signed difference), in mm."""
    keys = sorted(set(ref_walls) & set(test_walls) & set(range(1, 17)))
    if not keys:
        return {"median_abs_mm": float("nan"), "median_signed_mm": float("nan"), "n_segments": 0}
    d = np.array([test_walls[k] - ref_walls[k] for k in keys])
    return {
        "median_abs_mm": float(np.median(np.abs(d))),
        "median_signed_mm": float(np.median(d)),
        "n_segments": len(keys),
    }


def _kim(x: float) -> int:
    return int(np.searchsorted(KIM, x, side="right") - 1)


def _transmurality(scar, myo, seg, s) -> float:
    m = myo & (seg == s)
    n = int(m.sum())
    return float((scar & m).sum() / n) if n > MIN_SEGMENT_VOXELS else float("nan")


def sta(ref_labels, test_labels, ref_u, ref_segments, test_segments) -> float:
    """Segmental transmurality agreement: virtual subendocardial scars (reference depth < tau,
    tau in TAUS, segments 1-16) fixed in the image; the share whose Kim bin is the same in the
    reference and the test wall. NaN if no scar can be scored."""
    myo_r = np.asarray(ref_labels) == G.MYO
    myo_t = np.asarray(test_labels) == G.MYO
    agree = []
    for s in range(1, 17):
        for tau in TAUS:
            scar = myo_r & (ref_segments == s) & (np.nan_to_num(ref_u, nan=1.0) < tau)
            a = _transmurality(scar, myo_r, ref_segments, s)
            b = _transmurality(scar, myo_t, test_segments, s)
            if not (np.isnan(a) or np.isnan(b)):
                agree.append(_kim(a) == _kim(b))
    return float(np.mean(agree)) if agree else float("nan")


def _dice(a, b) -> float:
    s = int(a.sum()) + int(b.sum())
    return float(2 * (a & b).sum() / s) if s else float("nan")


def compare(
    ref_labels, test_labels, spacing=None, affine=None, *, with_sta: bool = True, roi=None
) -> dict:
    """Every JA15 measure between a reference and a test label map on the same grid (JA45).

    Per border (``endo``, ``epi``): ``assd_pp_*`` (JA39's scoring ASSD), ``assd_voxel_*``
    (reported beside it), ``bias_*`` (``signed_bias``, the guard's estimator, JA37), ``bias_pp_*``
    (JA37's transfer check) and ``mean_abs_d_*``.

    ``roi="ja37"`` builds JA37's band per border from the reference (``ja37_band``, JA61) and
    passes it to ``signed_bias``, ``signed_bias_pp`` and ``assd_pp``; the scorer uses it. A bool
    array (the grid's shape) is used as given for both borders. The voxel ASSD, mean |d|,
    thickness and STA always use the whole masks."""
    ref, test = np.asarray(ref_labels), np.asarray(test_labels)
    if ref.shape != test.shape:
        raise ValueError(f"label maps differ in shape: {ref.shape} vs {test.shape}")
    aff, sp = G._affine(ref.shape, spacing, affine)
    cav_r, sol_r = borders(ref)
    cav_t, sol_t = borders(test)
    if isinstance(roi, str) and roi != "ja37":
        raise ValueError(f"roi must be None, 'ja37' or a bool array, not {roi!r}")
    out = {"harness_version": HARNESS_VERSION, "geometry_version": G.GEOMETRY_VERSION}
    out["roi"] = "ja37" if isinstance(roi, str) else ("none" if roi is None else "array")
    for name, a, b in (("endo", cav_r, cav_t), ("epi", sol_r, sol_t)):
        band = ja37_band(ref, sp, name) if isinstance(roi, str) else roi
        out[f"bias_pp_{name}"], out[f"assd_pp_{name}"] = _pp(a, b, sp, band)
        out[f"assd_voxel_{name}"] = surface_assd(a, b, sp)
        out[f"bias_{name}"] = signed_bias(a, b, sp, roi=band)
        out[f"mean_abs_d_{name}"] = mean_abs_d(a, b, sp)
    walls_r, seg_r = segment_thickness(ref, affine=aff)
    walls_t, seg_t = segment_thickness(test, affine=aff)
    if seg_t is None and seg_r is not None:  # the test's AHA frame failed: keep the reference's
        walls_t, seg_t = segment_thickness(test, affine=aff, segments=seg_r * (test == G.MYO))
    th = thickness_error(walls_r, walls_t)
    out.update(
        thick_err_median_mm=th["median_abs_mm"],
        thick_bias_median_mm=th["median_signed_mm"],
        n_segments=th["n_segments"],
        dice_myo=_dice(ref == G.MYO, test == G.MYO),
        aha_failed=seg_t is None,
    )
    if with_sta and seg_r is not None and seg_t is not None:
        u_r = G.depth(ref, affine=aff).u
        out["sta"] = sta(ref, test, u_r, seg_r, seg_t)
    else:
        out["sta"] = float("nan")
    return out


def run(
    ref_labels,
    affine,
    *,
    sigma: float = 0.0,
    corr_mm: float = CORR_MM,
    bias_endo: float = 0.0,
    bias_epi: float = 0.0,
    rng=None,
    with_sta: bool = True,
) -> dict:
    """One harness row: perturb with the JA15 model (the same ``sigma`` on both borders), then
    measure. The nominal parameters are recorded beside what was realised (JA38): the row holds
    ``bias_{endo,epi}_nominal`` next to ``bias_{endo,epi}_realised`` (``signed_bias``) and
    ``bias_pp_*``, and is to be indexed by the realised values."""
    aff, sp = G._affine(np.shape(ref_labels), None, affine)
    test = perturb(
        ref_labels,
        sp,
        sigma_endo=sigma,
        sigma_epi=sigma,
        bias_endo=bias_endo,
        bias_epi=bias_epi,
        corr_mm=corr_mm,
        rng=rng,
    )
    row = compare(ref_labels, test, affine=aff, with_sta=with_sta)
    row.update(
        sigma_nominal=sigma,
        corr_mm=corr_mm,
        bias_endo_nominal=bias_endo,
        bias_epi_nominal=bias_epi,
        bias_endo_realised=row["bias_endo"],
        bias_epi_realised=row["bias_epi"],
    )
    return row


# ---------------------------------------------------------------------------------- phantom
PHANTOM_RC, PHANTOM_WALL, PHANTOM_CYL = 12.0, 8.0, 30.0  # mm
PHANTOM_RV_W = 8.0
PHANTOM_INSERTIONS = (120.0, 240.0)  # degrees, atan2(A, R)


def _capsule_sdf(rr, z, radius):
    """Exact signed distance to {rr < radius, z < 0}, where rr is the distance from the
    axis-and-cap skeleton (a cylinder above the cap centre, a sphere below)."""
    a = rr - radius
    out = np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(z, 0) ** 2)
    return np.where((a > 0) | (z > 0), out, np.maximum(a, z))


def _phantom_parts(
    spacing,
    endo_shift_mm,
    epi_shift_mm,
    origin_offset_mm,
    cavity_shift_mm,
    rc,
    wall,
    tilt_deg=0.0,
    closed=True,
):
    """(cavity, outer, la, rv, affine) of the phantom. ``closed``: cavity and outer are exact level
    sets of closed capsules (flat top at z = 0). Otherwise they are open upward and cut at the base
    plane z = 0, which the shifts do not move."""
    sp = _spacing(spacing)
    re = rc + wall
    half = re + abs(cavity_shift_mm) + PHANTOM_RV_W + 6.0
    depth_ = PHANTOM_CYL + re + 6.0
    t = np.radians(tilt_deg)
    grow = abs(np.sin(t)) * depth_
    lo = np.array([-half, -half - grow, -depth_ - abs(np.sin(t)) * half])
    hi = np.array([half, half + grow, 12.0 + abs(np.sin(t)) * half])
    n = tuple(int(v) for v in np.ceil((hi - lo) / sp))
    aff = np.diag([*sp, 1.0])
    aff[:3, 3] = lo + sp / 2
    off = np.asarray(origin_offset_mm, float)
    ax = [lo[d] + (np.arange(n[d]) + 0.5) * sp[d] - off[d] for d in range(3)]
    x, y, z = np.meshgrid(*ax, indexing="ij", sparse=True)
    if tilt_deg:  # the phantom's long axis turned about R, so the base plane is oblique to the grid
        y, z = np.cos(t) * y + np.sin(t) * z, -np.sin(t) * y + np.cos(t) * z

    def rr_of(xc):
        r = np.hypot(x - xc, y)
        return np.where(z >= -PHANTOM_CYL, r, np.sqrt(r**2 + (z + PHANTOM_CYL) ** 2)), r

    rr_c, _ = rr_of(cavity_shift_mm)
    rr_s, r_s = rr_of(0.0)
    if closed:
        cav = np.broadcast_to(_capsule_sdf(rr_c, z, rc) < endo_shift_mm, n)
        outer = np.broadcast_to(_capsule_sdf(rr_s, z, re) < epi_shift_mm, n)
    else:  # rr - radius is the exact signed distance of the upward-open shape
        cav = np.broadcast_to((rr_c - rc < endo_shift_mm) & (z < 0), n)
        outer = np.broadcast_to((rr_s - re < epi_shift_mm) & (z < 0), n)
    phi = np.degrees(np.arctan2(y, x)) % 360
    a0, a1 = PHANTOM_INSERTIONS
    la = np.broadcast_to((z >= 0) & (z < 6) & (r_s < re), n)
    rv = (z < 0) & (z >= -PHANTOM_CYL) & (r_s < re + PHANTOM_RV_W) & (phi >= a0) & (phi <= a1)
    return cav, outer, la, np.broadcast_to(rv, n), aff


def phantom(
    spacing: Sequence[float] = (GRID_MM,) * 3,
    *,
    endo_shift_mm: float = 0.0,
    epi_shift_mm: float = 0.0,
    origin_offset_mm: Sequence[float] = (0.0, 0.0, 0.0),
    cavity_shift_mm: float = 0.0,
    tilt_deg: float = 0.0,
    rc: float = PHANTOM_RC,
    wall: float = PHANTOM_WALL,
) -> Tuple[np.ndarray, np.ndarray]:
    """A synthetic LV (labels, affine): a cylinder with a hemispherical apex, long axis along -S
    (base superior at z = 0), anterior +A, the LA on the base and the RV over the septum between
    the insertions. The cavity axis may sit ``cavity_shift_mm`` along +R, so the wall varies, and
    the whole phantom may be turned ``tilt_deg`` about R, so its base plane is oblique to the grid.

    The borders are level sets of exact signed distances, so ``endo_shift_mm`` / ``epi_shift_mm``
    move each wall surface outward by exactly that much; the base plane stays at z = 0, where the
    cavity opens into the LA, as a read's mitral plane does. The grid does not depend on the
    shifts; ``origin_offset_mm`` moves the phantom against it by a sub-voxel amount. (JA16's check
    uses the closed surfaces, ``exact_shift_phantom``, which have no fixed plane.)"""
    cav, outer, la, rv, aff = _phantom_parts(
        spacing,
        endo_shift_mm,
        epi_shift_mm,
        origin_offset_mm,
        cavity_shift_mm,
        rc,
        wall,
        tilt_deg,
        closed=False,
    )
    lab = np.zeros(cav.shape, np.int16)
    lab[la] = G.LA
    lab[rv] = G.RV
    lab[outer | cav] = G.MYO
    lab[cav] = G.LV
    return lab, aff


def exact_shift_phantom(
    spacing: Sequence[float] = (GRID_MM,) * 3,
    *,
    endo_shift_mm: float = 0.0,
    epi_shift_mm: float = 0.0,
    origin_offset_mm: Sequence[float] = (0.0, 0.0, 0.0),
    cavity_shift_mm: float = 0.0,
    tilt_deg: float = 0.0,
    rc: float = PHANTOM_RC,
    wall: float = PHANTOM_WALL,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(cavity, outer, affine): the phantom's two borders as closed capsules, each an exact
    signed-distance level set, so ``endo_shift_mm`` / ``epi_shift_mm`` move the whole closed
    surface outward by exactly that much (JA38). This is the fixture for any test that needs a
    known shift; ``validate_bias_estimator`` uses it. The grid does not depend on the shifts, so
    two calls with the same ``spacing``, ``origin_offset_mm``, ``cavity_shift_mm`` and ``tilt_deg``
    are on the same grid. ``outer`` is the epicardial capsule itself (not united with the
    cavity), so each mask stays an exact level set; their flat tops share the plane z = 0."""
    cav, outer, _, _, aff = _phantom_parts(
        spacing,
        endo_shift_mm,
        epi_shift_mm,
        origin_offset_mm,
        cavity_shift_mm,
        rc,
        wall,
        tilt_deg,
        closed=True,
    )
    return np.ascontiguousarray(cav), np.ascontiguousarray(outer), aff


# ---------------------------------------------------------------------------------- JA16 check
OPEN_BASE_GRIDS = ((GRID_MM,) * 3, (0.4, 0.4, 0.5))  # JA61: two grids
OPEN_BASE_SHIFTS_MM = (0.3, 0.5)  # JA61: +-0.3 and +-0.5 mm


def _open_base_parts(spacing, endo, epi, off, cs, tilt):
    """(cavity, solid, labels, affine): ``exact_shift_phantom``'s borders cut by the fixed base
    plane z = 0, which the shifts do not move (JA61). The pool is open to label 0 at the base."""
    cav, outer, _, _, aff = _phantom_parts(
        spacing, endo, epi, off, cs, PHANTOM_RC, PHANTOM_WALL, tilt, closed=False
    )
    cav = np.ascontiguousarray(cav)
    sol = np.ascontiguousarray(outer | cav)
    lab = np.zeros(cav.shape, np.int16)
    lab[sol] = G.MYO
    lab[cav] = G.LV
    return cav, sol, lab, aff


def validate_bias_estimator(
    shift_mm: float = BIAS_CHECK_SHIFT_MM,
    tolerance_mm: float = BIAS_CHECK_TOLERANCE_MM,
    *,
    n_offsets: int = 3,
    shapes: Sequence[Tuple[float, float]] = ((0.0, 0.0), (2.3, 0.0), (2.3, 23.0)),
    seed: int = 20261030,
    spacing: Sequence[float] = (GRID_MM,) * 3,
    open_base: bool = False,
    grids: Optional[Sequence[Sequence[float]]] = None,
    shifts_mm: Optional[Sequence[float]] = None,
) -> dict:
    """JA16's check: does ``signed_bias`` recover a known shift, in each direction, on each
    border, to within ``tolerance_mm``?

    The truth is exact: the reference and the shifted phantom are voxelisations of exact signed
    distances offset by the shift on the same grid. It is repeated over ``n_offsets`` random
    sub-voxel positions of the phantom against the grid and over ``shapes``, each a (cavity shift,
    tilt degrees) pair: a uniform wall, a varying wall, and a varying wall whose base plane is
    oblique to the grid.

    ``open_base=False`` (JA16): closed capsules, whole masks, ``shift_mm`` on ``spacing``.
    ``open_base=True`` (JA61): the capsules cut by a fixed base plane, so the pool opens to label 0
    as a real mask does at the outflow; the estimate is taken in JA37's band (``ja37_band``) of
    the reference; two grids (``OPEN_BASE_GRIDS``) and +-0.3 / +-0.5 mm (``OPEN_BASE_SHIFTS_MM``)
    unless ``grids`` / ``shifts_mm`` say otherwise. The wall moves by exactly the shift; the cut
    does not move.

    Returns every reading, the worst error, the verdict and the guard this check supports
    (``BIAS_GUARD_TIGHT_MM`` if it passes, else ``BIAS_GUARD_FALLBACK_MM``). The guard in force
    is ``BIAS_GUARD_VALIDATED_MM``."""
    if grids is None:
        grids = OPEN_BASE_GRIDS if open_base else (tuple(spacing),)
    if shifts_mm is None:
        shifts_mm = OPEN_BASE_SHIFTS_MM if open_base else (shift_mm,)
    rng = np.random.default_rng(seed)
    rows = []
    for grid in grids:
        offsets = rng.uniform(0.0, float(np.max(grid)), size=(n_offsets, 3))
        for cs, tilt in shapes:
            for off in offsets:
                if open_base:
                    cav_r, sol_r, lab_r, aff = _open_base_parts(grid, 0.0, 0.0, off, cs, tilt)
                    sp = np.linalg.norm(aff[:3, :3], axis=0)
                    bands = {b: ja37_band(lab_r, sp, b) for b in ("endo", "epi")}
                else:
                    cav_r, sol_r, aff = exact_shift_phantom(
                        grid, origin_offset_mm=off, cavity_shift_mm=cs, tilt_deg=tilt
                    )
                    sp = np.linalg.norm(aff[:3, :3], axis=0)
                    bands = {"endo": None, "epi": None}
                for border in ("endo", "epi"):
                    for size in shifts_mm:
                        for sign in (+1.0, -1.0):
                            b = sign * size
                            sh = (b, 0.0) if border == "endo" else (0.0, b)
                            if open_base:
                                cav_t, sol_t, _, _ = _open_base_parts(grid, *sh, off, cs, tilt)
                            else:
                                cav_t, sol_t, _ = exact_shift_phantom(
                                    grid,
                                    endo_shift_mm=sh[0],
                                    epi_shift_mm=sh[1],
                                    origin_offset_mm=off,
                                    cavity_shift_mm=cs,
                                    tilt_deg=tilt,
                                )
                            a, t = (cav_r, cav_t) if border == "endo" else (sol_r, sol_t)
                            est = signed_bias(a, t, sp, roi=bands[border])
                            rows.append(
                                {
                                    "border": border,
                                    "true_mm": b,
                                    "estimate_mm": est,
                                    "error_mm": est - b,
                                    "grid_mm": [float(v) for v in grid],
                                    "cavity_shift_mm": float(cs),
                                    "tilt_deg": float(tilt),
                                    "origin_offset_mm": [float(v) for v in off],
                                }
                            )
    err = np.array([r["error_mm"] for r in rows])
    worst = float(np.max(np.abs(err)))
    passed = bool(worst <= tolerance_mm)
    by = {}
    for border in ("endo", "epi"):
        for sign, key in ((+1, "outward"), (-1, "inward")):
            sel = [r for r in rows if r["border"] == border and np.sign(r["true_mm"]) == sign]
            e = [r["estimate_mm"] for r in sel]
            by[f"{border}_{key}"] = {
                "mean_mm": float(np.mean(e)),
                "min_mm": float(np.min(e)),
                "max_mm": float(np.max(e)),
                "worst_abs_error_mm": float(max(abs(r["error_mm"]) for r in sel)),
            }
    return {
        "harness_version": HARNESS_VERSION,
        "open_base": bool(open_base),
        "shift_mm": shift_mm if not open_base else None,
        "shifts_mm": [float(v) for v in shifts_mm],
        "tolerance_mm": tolerance_mm,
        "worst_abs_error_mm": worst,
        "mean_error_mm": float(err.mean()),
        "passed": passed,
        "bias_guard_mm": BIAS_GUARD_TIGHT_MM if passed else BIAS_GUARD_FALLBACK_MM,
        "by_border": by,
        "rows": rows,
    }


# ---------------------------------------------------------------------------------- JA37 transfer
def transfer_check(
    rows, *, n_first: int = TRANSFER_N_FIRST, limit_mm: float = TRANSFER_LIMIT_MM
) -> dict:
    """JA37's transfer check (JA62, R4-S5) on ``compare(..., roi="ja37")`` rows in the decision
    list's order: the median |``bias_*`` - ``bias_pp_*``| per border over the first ``n_first``
    rows. Rows after the ``n_first``-th are ignored; fewer is a ``ValueError``, never a default,
    as is a missing or non-finite value among the first ``n_first``.

    Returns ``median_abs_diff_mm`` per border, ``passed`` (every border's median <= ``limit_mm``),
    ``bias_guard_mm`` (0.3 if passed, else 0.5), ``n_over_limit`` (rows where either border is
    over the limit; no ids) and ``bias_guard_applied_mm``, the larger of this check's guard and
    ``BIAS_GUARD_VALIDATED_MM`` (the open-base check's, JA61)."""
    rows = list(rows)
    if len(rows) < n_first:
        raise ValueError(f"the transfer check needs {n_first} rows, got {len(rows)}")
    first = rows[:n_first]
    diffs = {}
    for border in ("endo", "epi"):
        try:
            d = np.array(
                [abs(float(r[f"bias_{border}"]) - float(r[f"bias_pp_{border}"])) for r in first]
            )
        except KeyError as e:
            raise ValueError(f"a row lacks {e.args[0]}") from None
        if not np.isfinite(d).all():
            raise ValueError(f"non-finite bias_{border} or bias_pp_{border} among the first rows")
        diffs[border] = d
    med = {b: float(np.median(d)) for b, d in diffs.items()}
    passed = all(v <= limit_mm for v in med.values())
    guard = BIAS_GUARD_TIGHT_MM if passed else BIAS_GUARD_FALLBACK_MM
    over = (diffs["endo"] > limit_mm) | (diffs["epi"] > limit_mm)
    return {
        "harness_version": HARNESS_VERSION,
        "n_first": n_first,
        "limit_mm": limit_mm,
        "median_abs_diff_mm": med,
        "passed": bool(passed),
        "bias_guard_mm": guard,
        "n_over_limit": int(over.sum()),
        "bias_guard_applied_mm": max(guard, BIAS_GUARD_VALIDATED_MM),
    }
