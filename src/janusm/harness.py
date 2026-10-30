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

- ``surface_assd``: symmetric surface ASSD in mm between the two masks' surface voxels (Lima's and
  India's unit, which JA8 decides on).
- ``signed_bias``: mean signed normal displacement in mm, + outward. It is the volume change
  divided by the mean area of the two surfaces, the area taken from marching cubes on each mask
  smoothed by one voxel. For a uniform offset b of a smooth closed surface this is b to second
  order (the curvature terms cancel in the mean area). The Round 2 estimators sampled a voxel
  signed-distance map at surface voxels and read about 0.35-0.45 mm for a true 0.5 mm shift (Round
  2 judgement section 1.3); ``validate_bias_estimator`` is JA16's check of this one.
- ``segment_thickness`` / ``thickness_error``: the geometry module's wall thickness per AHA segment
  (``janusm.geometry.layers``: the median thickness of the segment's mid-wall voxels), and the
  error summarised as the **median over segments 1-16** (JA15).
- ``sta``: Kilo's segmental transmurality agreement (16 segments x 4 virtual subendocardial scars,
  Kim bins). Still reported (JA8, JA15).
- ``mean_abs_d``: Hotel's mean |d| (changed volume / mean area). Reported beside ASSD, never in its
  place (JA15).

**JA16.** The signed-bias guard is 0.3 mm only if the estimator recovers a known 0.5 mm shift, in
each direction and on each border, to within 0.05 mm here; otherwise it stays 0.5 mm.
``validate_bias_estimator`` runs that check on analytic phantoms whose true offset is exact, and
returns the guard it supports.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage as ndi
from skimage.measure import marching_cubes, mesh_surface_area

from janusm import geometry as G

#: Bump on any change that can move a reported number.
HARNESS_VERSION = "1.0.0"

GRID_MM = 0.5  # JA15: the native grid
CORR_MM = 8.0  # JA15: primary correlation length
CORR_SENSITIVITY_MM = (4.0, 16.0)

BIAS_CHECK_SHIFT_MM = 0.5  # JA16: the known shift the estimator must recover
BIAS_CHECK_TOLERANCE_MM = 0.05
BIAS_GUARD_VALIDATED_MM = 0.3
BIAS_GUARD_FALLBACK_MM = 0.5

TAUS = (0.15, 0.40, 0.65, 0.90)  # STA virtual-scar depths
KIM = np.array([0.0, 0.25, 0.50, 0.75, 1.0001])
MIN_SEGMENT_VOXELS = 50

_FACE = ndi.generate_binary_structure(3, 1)


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
def _surface(m: np.ndarray) -> np.ndarray:
    return m & ~ndi.binary_erosion(m, _FACE, border_value=0)


def surface_assd(a, b, spacing) -> float:
    """Symmetric surface ASSD (mm) between the surface voxels of two masks; NaN if one is empty."""
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    sp = _spacing(spacing)
    sa, sb = _surface(a), _surface(b)
    if not sa.any() or not sb.any():
        return float("nan")
    da = ndi.distance_transform_edt(~sb, sampling=sp)[sa]
    db = ndi.distance_transform_edt(~sa, sampling=sp)[sb]
    return float((da.sum() + db.sum()) / (da.size + db.size))


def surface_area(mask, spacing, smooth_vox: float = 1.0) -> float:
    """Surface area (mm^2) of a mask: marching cubes at 0.5 on the mask smoothed by a Gaussian of
    ``smooth_vox`` voxels, which removes most of the staircase's excess area."""
    m = np.asarray(mask, bool)
    sp = _spacing(spacing)
    if not m.any():
        return 0.0
    pad = int(np.ceil(4 * smooth_vox)) + 2
    nz = np.argwhere(m)
    box = tuple(slice(lo, hi + 1) for lo, hi in zip(nz.min(0), nz.max(0)))
    f = np.pad(m[box].astype(np.float32), pad)
    if smooth_vox > 0:
        f = ndi.gaussian_filter(f, smooth_vox)
    v, faces, _, _ = marching_cubes(f, 0.5, spacing=tuple(sp))
    return float(mesh_surface_area(v, faces))


def signed_bias(ref, test, spacing, smooth_vox: float = 1.0) -> float:
    """Mean signed displacement (mm, + = ``test`` lies outside ``ref``) of one border: the volume
    change over the mean area of the two surfaces. NaN if either mask is empty."""
    ref, test = np.asarray(ref, bool), np.asarray(test, bool)
    sp = _spacing(spacing)
    area = 0.5 * (surface_area(ref, sp, smooth_vox) + surface_area(test, sp, smooth_vox))
    if not ref.any() or not test.any() or area <= 0:
        return float("nan")
    dv = (int(test.sum()) - int(ref.sum())) * float(np.prod(sp))
    return float(dv / area)


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


def compare(ref_labels, test_labels, spacing=None, affine=None, *, with_sta: bool = True) -> dict:
    """Every JA15 measure between a reference and a test label map on the same grid."""
    ref, test = np.asarray(ref_labels), np.asarray(test_labels)
    if ref.shape != test.shape:
        raise ValueError(f"label maps differ in shape: {ref.shape} vs {test.shape}")
    aff, sp = G._affine(ref.shape, spacing, affine)
    cav_r, sol_r = borders(ref)
    cav_t, sol_t = borders(test)
    out = {"harness_version": HARNESS_VERSION, "geometry_version": G.GEOMETRY_VERSION}
    for name, a, b in (("endo", cav_r, cav_t), ("epi", sol_r, sol_t)):
        out[f"assd_{name}"] = surface_assd(a, b, sp)
        out[f"bias_{name}"] = signed_bias(a, b, sp)
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
    measure. The nominal parameters are recorded beside what was realised."""
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
        sigma_nominal=sigma, corr_mm=corr_mm, bias_endo_nominal=bias_endo, bias_epi_nominal=bias_epi
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
    uses the closed surfaces themselves, which have no fixed plane.)"""
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


# ---------------------------------------------------------------------------------- JA16 check
def validate_bias_estimator(
    shift_mm: float = BIAS_CHECK_SHIFT_MM,
    tolerance_mm: float = BIAS_CHECK_TOLERANCE_MM,
    *,
    n_offsets: int = 3,
    shapes: Sequence[Tuple[float, float]] = ((0.0, 0.0), (2.3, 0.0), (2.3, 23.0)),
    seed: int = 20261030,
    spacing: Sequence[float] = (GRID_MM,) * 3,
) -> dict:
    """JA16's check: does ``signed_bias`` recover a known ``shift_mm``, in each direction, on each
    border, to within ``tolerance_mm``?

    The truth is exact: the reference and the shifted phantom are voxelisations of exact signed
    distances offset by ``shift_mm`` on the same grid. It is repeated over ``n_offsets`` random
    sub-voxel positions of the phantom against the grid and over ``shapes``, each a (cavity shift,
    tilt degrees) pair: a uniform wall, a varying wall, and a varying wall whose base plane is
    oblique to the grid. Returns every reading, the worst error, the verdict and the
    guard it supports (0.3 mm if it passes, else 0.5 mm)."""
    rng = np.random.default_rng(seed)
    offsets = rng.uniform(0.0, float(np.max(spacing)), size=(n_offsets, 3))
    rows = []
    for cs, tilt in shapes:
        for off in offsets:
            cav_r, out_r, _, _, aff = _phantom_parts(
                spacing, 0.0, 0.0, off, cs, PHANTOM_RC, PHANTOM_WALL, tilt
            )
            sp = np.linalg.norm(aff[:3, :3], axis=0)
            for border in ("endo", "epi"):
                for sign in (+1.0, -1.0):
                    b = sign * shift_mm
                    shifts = (b, 0.0) if border == "endo" else (0.0, b)
                    cav_t, out_t, *_ = _phantom_parts(
                        spacing, *shifts, off, cs, PHANTOM_RC, PHANTOM_WALL, tilt
                    )
                    a, t = (cav_r, cav_t) if border == "endo" else (out_r, out_t)
                    est = signed_bias(a, t, sp)
                    rows.append(
                        {
                            "border": border,
                            "true_mm": b,
                            "estimate_mm": est,
                            "error_mm": est - b,
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
            e = [
                r["estimate_mm"]
                for r in rows
                if r["border"] == border and np.sign(r["true_mm"]) == sign
            ]
            by[f"{border}_{key}"] = {
                "mean_mm": float(np.mean(e)),
                "min_mm": float(np.min(e)),
                "max_mm": float(np.max(e)),
            }
    return {
        "harness_version": HARNESS_VERSION,
        "shift_mm": shift_mm,
        "tolerance_mm": tolerance_mm,
        "worst_abs_error_mm": worst,
        "mean_error_mm": float(err.mean()),
        "passed": passed,
        "bias_guard_mm": BIAS_GUARD_VALIDATED_MM if passed else BIAS_GUARD_FALLBACK_MM,
        "by_border": by,
        "rows": rows,
    }
