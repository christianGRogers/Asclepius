"""The automatic check every submitted Janus-M read goes through: border protocol v1
(JA7, JA21, JA46; ``docs/JANUSM-READ-PROTOCOL.md`` section 4).

Two parts, both on the read's own grid (the CT's):

**Label conventions (JA1, JA46).** Values only 0-4, all four classes present; the LV
and RV pools touch over at most 0.5 % of the LV pool's surface (JA46 (b): the
membranous septum may let them meet); the LV and LA pools never share a face (the
mitral gap is 0 or 1); the LV pool reaches at most 3 mm above the mitral plane
(JA46 (a)); papillary muscles and trabeculae are in the LV pool, so the pool has no
enclosed holes; the myocardium is one piece.

**Hotel's half-maximum rule.** A border lies halfway between the plateaus on
either side of it. For each border the check measures the plateaus from the read's
own labels, then the median CT value as a function of signed distance to the read's
border, and finds where that profile crosses the half-way value. The crossing's
distance from the read's border is the border's **offset**, in the **canonical
sign** (JA44):

* ``offset > 0``: the region bounded by the border (the LV pool for the
  endocardium; pool + myocardium for the epicardium and the septal RV side)
  extends **beyond** the image half-maximum: the read spills past the edge;
* ``offset < 0``: the region stops short of the edge: the read is drawn too far in.

Three borders, each with its own pair of plateaus:

=================  =====================  ==========================  ============
border             inside / outside        plateaus                   region
=================  =====================  ==========================  ============
``endocardial``    LV pool / myocardium    LV blood, myocardium       class 2
``epicardial``     myocardium / outside    myocardium, epicardial fat class 1 vs 0
``septal_rv``      myocardium / RV pool    myocardium, RV blood       class 1 vs 3
=================  =====================  ==========================  ============

Each offset is measured over the whole border and in eight sectors (octants about
the LV pool's centre). JA46 (c): **the whole-border offset decides** (fails beyond
:attr:`CheckConfig.tolerance_mm`, 0.5 mm); an octant beyond
:attr:`CheckConfig.octant_warning_mm` (1.0 mm) is a warning only. Every border's
profile is kept in the report, so a returned read can show it to its reader.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage

from . import BORDER_PROTOCOL
from . import labels as L

#: What the sign of every offset in a report means (JA44).
OFFSET_SIGN = ("canonical: + = the region bounded by the border extends beyond the image "
               "half-maximum")


@dataclass
class CheckConfig:
    #: A border whose whole-border half-maximum offset exceeds this fails (JA21, JA46).
    tolerance_mm: float = 0.5
    #: An octant whose offset exceeds this is a warning, never a failure (JA46 (c)).
    octant_warning_mm: float = 1.0
    #: Half-width of the band either side of a border that the profile uses.
    band_mm: float = 3.0
    #: Width of one profile bin.
    bin_mm: float = 0.25
    #: Plateaus: blood from pool voxels at least this deep; myocardium from voxels at
    #: least ``myo_core_mm`` from any other class.
    blood_core_mm: float = 2.0
    myo_core_mm: float = 1.0
    #: Epicardial fat: background voxels this far outside the myocardium, in this HU
    #: window (JA11's verified -180..0 HU).
    fat_shell_mm: Tuple[float, float] = (1.0, 4.0)
    fat_window_hu: Tuple[float, float] = (-180.0, 0.0)
    #: Fewest voxels a plateau or a profile side needs; a sector with fewer is skipped.
    min_voxels: int = 50
    #: Label conventions.
    max_pool_contact_share: float = 0.005   # LV-pool faces touching the RV pool (JA46 (b))
    #: JA46 (a): the mitral plane is fitted to the label-2 voxels this close to label 4,
    #: and the LV pool may reach this far above it (towards the LA).
    mitral_gap_mm: float = 3.0
    max_pool_above_mitral_mm: float = 3.0
    #: Fewest points a mitral-plane fit uses.
    min_plane_points: int = 10
    max_pool_hole_share: float = 0.002      # enclosed non-pool voxels / LV pool volume
    max_myo_island_share: float = 0.02      # myocardium outside its largest piece
    #: Crop margin around the heart, beyond the band.
    margin_mm: float = 6.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BorderResult:
    name: str
    threshold_hu: Optional[float] = None
    offset_mm: Optional[float] = None
    sectors: Dict[str, Optional[float]] = field(default_factory=dict)
    voxels: int = 0
    skipped: str = ""
    #: The two plateaus (HU) the threshold lies between: inside, outside.
    plateaus_hu: List[Optional[float]] = field(default_factory=list)
    #: The whole-border profile: ``s_mm`` is the signed distance from the read's border
    #: (+ away from the region), ``hu`` the median CT value in that bin. The image edge
    #: is where ``hu`` crosses ``threshold_hu``, at ``s = -offset_mm``.
    profile: Dict[str, List[float]] = field(default_factory=dict)

    def worst_sector(self) -> Tuple[Optional[str], Optional[float]]:
        vals = [(k, v) for k, v in self.sectors.items() if v is not None]
        if not vals:
            return None, None
        return max(vals, key=lambda kv: abs(kv[1]))


@dataclass
class CheckReport:
    passed: bool
    errors: List[str]
    warnings: List[str]
    plateaus_hu: Dict[str, Optional[float]]
    borders: Dict[str, BorderResult]
    config: CheckConfig

    def summary(self) -> str:
        if self.passed:
            parts = [f"{b.name} {b.offset_mm:+.2f} mm" for b in self.borders.values()
                     if b.offset_mm is not None]
            return "Passed the Janus-M read check" + (f" ({', '.join(parts)})." if parts
                                                      else ".")
        return "Failed the Janus-M read check: " + " ".join(self.errors)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "plateausHU": dict(self.plateaus_hu),
            "borders": {k: asdict(v) for k, v in self.borders.items()},
            "config": self.config.to_dict(),
            "summary": self.summary(),
            "border_protocol": BORDER_PROTOCOL,
            "offsetSign": OFFSET_SIGN,
        }

    def offsets(self) -> Dict[str, Optional[float]]:
        """Whole-border offsets (mm, canonical sign), by border."""
        return {k: v.offset_mm for k, v in self.borders.items()}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=1, sort_keys=True)


# ------------------------------------------------------------------ helpers


def _edt(mask: np.ndarray, spacing) -> np.ndarray:
    """Distance (mm) from every voxel to the nearest voxel *of* ``mask``."""
    if not mask.any():
        return np.full(mask.shape, np.inf, dtype=np.float32)
    return ndimage.distance_transform_edt(~mask, sampling=spacing).astype(np.float32)


def _crop(read: np.ndarray, spacing, margin_mm: float):
    nz = np.nonzero(read)
    if not nz[0].size:
        return tuple(slice(0, s) for s in read.shape)
    out = []
    for axis, idx in enumerate(nz):
        pad = int(math.ceil(margin_mm / float(spacing[axis])))
        out.append(slice(max(0, int(idx.min()) - pad),
                         min(read.shape[axis], int(idx.max()) + 1 + pad)))
    return tuple(out)


def _median(values: np.ndarray, minimum: int) -> Optional[float]:
    if values.size < minimum:
        return None
    return float(np.median(values))


def _profile(s: np.ndarray, hu: np.ndarray, cfg: CheckConfig):
    """``(positions, median HU)`` of the binned profile, or None if too thin."""
    if s.size < 2 * cfg.min_voxels:
        return None
    nbins = int(round(2 * cfg.band_mm / cfg.bin_mm))
    idx = np.floor((s + cfg.band_mm) / cfg.bin_mm).astype(np.int64)
    keep = (idx >= 0) & (idx < nbins)
    idx, s, hu = idx[keep], s[keep], hu[keep]
    present = np.unique(idx)
    if present.size < 2:
        return None
    med = np.asarray(ndimage.median(hu, labels=idx + 1, index=present + 1), dtype=float)
    pos = np.asarray(ndimage.mean(s, labels=idx + 1, index=present + 1), dtype=float)
    return pos, med


def _crossing_of(pos: np.ndarray, med: np.ndarray, threshold: float) -> Optional[float]:
    """Where a profile crosses ``threshold``, nearest to the read's border (s = 0)."""
    diff = med - threshold
    best = None
    for i in range(len(pos) - 1):
        a, b = diff[i], diff[i + 1]
        if a == 0:
            x = pos[i]
        elif a * b < 0:
            x = pos[i] + (pos[i + 1] - pos[i]) * (a / (a - b))
        else:
            continue
        if best is None or abs(x) < abs(best):
            best = float(x)
    if best is None and diff[-1] == 0:
        best = float(pos[-1])
    return best


def _crossing(s: np.ndarray, hu: np.ndarray, threshold: float, cfg: CheckConfig,
              ) -> Optional[float]:
    """Where the median-HU-versus-signed-distance profile crosses ``threshold``,
    nearest to the read's border (s = 0). None if it never does within the band."""
    prof = _profile(s, hu, cfg)
    return None if prof is None else _crossing_of(prof[0], prof[1], threshold)


def _canonical(crossing: Optional[float]) -> Optional[float]:
    """A crossing at signed distance s (+ outside the region) is an image edge s mm
    beyond the read's border: the region stops short of it, offset -s (JA44)."""
    return None if crossing is None else 0.0 - float(crossing)


def _sector_ids(shape, spacing, centre) -> np.ndarray:
    """Octant (0..7) of every voxel about ``centre`` (physical axes)."""
    grids = np.indices(shape, dtype=np.float32)
    out = np.zeros(shape, dtype=np.uint8)
    for axis in range(3):
        out |= ((grids[axis] * spacing[axis] >= centre[axis]).astype(np.uint8) << axis)
    return out


def _border(name, inside, outside, others, ct, spacing, threshold, sectors, cfg,
            pair=(None, None)):
    """Signed-distance profile across the inside/outside border, whole and per sector."""
    result = BorderResult(name=name, plateaus_hu=[None if p is None else float(p)
                                                  for p in pair])
    if threshold is None:
        result.skipped = "a plateau could not be measured"
        return result
    result.threshold_hu = float(threshold)
    to_out = _edt(outside, spacing)
    to_in = _edt(inside, spacing)
    to_other = _edt(others, spacing)
    # Inside voxels facing the outside class (not another class), and outside voxels
    # facing the inside class, within the band.
    sel_in = inside & (to_out <= cfg.band_mm) & (to_out <= to_other)
    sel_out = outside & (to_in <= cfg.band_mm) & (to_in <= to_other)
    s = np.concatenate([-to_out[sel_in], to_in[sel_out]])
    hu = np.concatenate([ct[sel_in], ct[sel_out]]).astype(np.float32)
    sec = np.concatenate([sectors[sel_in], sectors[sel_out]])
    result.voxels = int(s.size)
    prof = _profile(s, hu, cfg)
    if prof is not None:
        result.profile = {"s_mm": [round(float(x), 3) for x in prof[0]],
                          "hu": [round(float(y), 1) for y in prof[1]]}
        result.offset_mm = _canonical(_crossing_of(prof[0], prof[1], threshold))
    for k in range(8):
        m = sec == k
        n_in = int(np.count_nonzero(m[: int(sel_in.sum())]))
        n_out = int(np.count_nonzero(m)) - n_in
        if n_in < cfg.min_voxels or n_out < cfg.min_voxels:
            continue
        result.sectors[f"octant{k}"] = _canonical(_crossing(s[m], hu[m], threshold, cfg))
    return result


# --------------------------------------------------------------- the checks


def _physical(mask: np.ndarray, spacing) -> np.ndarray:
    """``(n, 3)`` physical coordinates (mm, array axis order) of a mask's voxels."""
    return np.argwhere(mask).astype(np.float64) * np.asarray(spacing, dtype=np.float64)


def _face_neighbours(mask: np.ndarray, other: np.ndarray) -> np.ndarray:
    """Voxels of ``mask`` sharing a face with a voxel of ``other``."""
    six = ndimage.generate_binary_structure(3, 1)
    return mask & ndimage.binary_dilation(other, six)


def mitral_plane(read: np.ndarray, spacing, cfg: Optional[CheckConfig] = None,
                 seed: Optional[np.ndarray] = None,
                 hinge_points_mm: Optional[Sequence[Sequence[float]]] = None):
    """The JA46 (a) mitral plane: ``(centre, unit normal towards the LA, radius, source)``,
    or None when there is nothing to fit it to.

    Fitted by least squares (SVD) to, in order of preference:

    1. ``seed``: its 2-4 interface (LV-pool voxels sharing a face with the LA), or,
       if the seed has a mitral gap, its label-2 voxels within ``mitral_gap_mm`` of 4;
    2. the read's label-2 voxels within ``mitral_gap_mm`` of label 4 (blank cases);
    3. ``hinge_points_mm``: annular hinge points (mm, array axis order).

    ``radius`` is the largest in-plane distance of a fitted point from the centre: the
    check looks above the plane only over that footprint (plus the gap), so the LV
    outflow under the aortic valve is not measured against the mitral plane.
    """
    cfg = cfg or CheckConfig()
    la = read == L.LA_POOL
    sources = []
    if seed is not None:
        s_pool, s_la = seed == L.LV_POOL, seed == L.LA_POOL
        if s_pool.any() and s_la.any():
            face = _face_neighbours(s_pool, s_la)
            if face.sum() < cfg.min_plane_points:
                face = s_pool & (_edt(s_la, spacing) <= cfg.mitral_gap_mm)
            sources.append(("seed", _physical(face, spacing)))
    if la.any():
        gap = (read == L.LV_POOL) & (_edt(la, spacing) <= cfg.mitral_gap_mm)
        sources.append(("read", _physical(gap, spacing)))
    if hinge_points_mm is not None and len(hinge_points_mm):
        sources.append(("hinge points", np.asarray(hinge_points_mm, dtype=np.float64)))
    for source, pts in sources:
        need = 3 if source == "hinge points" else cfg.min_plane_points
        if len(pts) < need:
            continue
        centre = pts.mean(axis=0)
        _, sv, vt = np.linalg.svd(pts - centre, full_matrices=False)
        if sv.size < 2 or sv[1] <= 1e-6 * max(1.0, sv[0]):
            continue                          # collinear: no plane
        normal = vt[-1]
        if la.any() and float((_physical(la, spacing).mean(axis=0) - centre) @ normal) < 0:
            normal = -normal
        rel = pts - centre
        inplane = rel - np.outer(rel @ normal, normal)
        radius = float(np.sqrt((inplane ** 2).sum(axis=1)).max())
        return centre, normal, radius, source
    return None


def pool_above_mitral_mm(read: np.ndarray, spacing, plane) -> float:
    """How far (mm) the LV pool reaches above the mitral plane, over its footprint."""
    centre, normal, radius, _ = plane
    pts = _physical(read == L.LV_POOL, spacing)
    if not len(pts):
        return 0.0
    rel = pts - centre
    height = rel @ normal
    inplane = np.sqrt(np.maximum(0.0, (rel ** 2).sum(axis=1) - height ** 2))
    near = inplane <= radius
    return float(max(0.0, height[near].max())) if near.any() else 0.0


def check_conventions(read: np.ndarray, spacing, cfg: Optional[CheckConfig] = None,
                      seed: Optional[np.ndarray] = None,
                      hinge_points_mm: Optional[Sequence[Sequence[float]]] = None,
                      ) -> Tuple[List[str], List[str]]:
    """JA1 / JA46 label conventions. Returns ``(errors, warnings)``.

    ``seed`` (on the read's grid) is the case's seed, from which the mitral plane is
    fitted on seeded cases; on blank cases it is fitted to the read (JA46 (a)).
    """
    cfg = cfg or CheckConfig()
    errors, warnings = [], []
    values, counts = np.unique(read, return_counts=True)
    bad = L.invalid_values(values.tolist())
    if bad:
        errors.append(f"Label values {bad} are not Janus-M classes (0-4).")
    missing = L.missing_required({int(v): int(c) for v, c in zip(values, counts)})
    if missing:
        errors.append(L.missing_message(missing))
    if L.LV_POOL in missing or L.LV_MYO in missing:
        return errors, warnings

    pool = read == L.LV_POOL
    myo = read == L.LV_MYO
    six = ndimage.generate_binary_structure(3, 1)

    # LV pool against RV pool: the septum must separate them.
    if L.RV_POOL not in missing:
        rv = read == L.RV_POOL
        surface = pool & ~ndimage.binary_erosion(pool, six, border_value=0)
        touching = surface & ndimage.binary_dilation(rv, six)
        share = touching.sum() / max(1, surface.sum())
        if share > cfg.max_pool_contact_share:
            errors.append(f"The LV and RV blood pools touch over {share:.1%} of the LV "
                          "pool's surface: the septum must be labelled myocardium (1).")

    # JA46 (a): the LV and LA pools never share a face; the mitral gap is 0 or 1.
    if L.LA_POOL not in missing:
        la = read == L.LA_POOL
        faces = int(_face_neighbours(pool, la).sum())
        if faces:
            errors.append(f"The LV and LA blood pools share a face at {faces} voxels: "
                          "leave the mitral gap as background (0) or myocardium (1).")
        plane = mitral_plane(read, spacing, cfg, seed=seed, hinge_points_mm=hinge_points_mm)
        if plane is None:
            warnings.append("The mitral plane could not be fitted (no mitral gap in the "
                            "seed or the read, and no hinge points): the LV pool's basal "
                            "limit was not checked.")
        else:
            above = pool_above_mitral_mm(read, spacing, plane)
            if above > cfg.max_pool_above_mitral_mm:
                errors.append(f"The LV blood pool reaches {above:.1f} mm above the mitral "
                              f"plane (fitted to the {plane[3]}; limit "
                              f"{cfg.max_pool_above_mitral_mm:g} mm): end the pool at the "
                              "mitral annulus.")

    # Papillary muscles and trabeculae belong in the LV pool (JA1): no enclosed holes.
    filled = ndimage.binary_fill_holes(pool)
    holes = filled & ~pool
    share = holes.sum() / max(1, pool.sum())
    if share > cfg.max_pool_hole_share:
        errors.append(f"The LV blood pool has enclosed holes ({share:.1%} of its volume): "
                      "papillary muscles and trabeculae are part of the pool (2), not "
                      "myocardium or background.")

    # The myocardium is one piece.
    lab, n = ndimage.label(myo, structure=np.ones((3, 3, 3)))
    if n > 1:
        sizes = np.bincount(lab.ravel())[1:]
        share = 1.0 - sizes.max() / sizes.sum()
        if share > cfg.max_myo_island_share:
            errors.append(f"The LV myocardium is in {n} pieces ({share:.1%} outside the "
                          "largest): label the compact wall only, as one shell.")
        else:
            warnings.append(f"The LV myocardium has {n - 1} small loose piece(s).")

    # Open wall: warn, since the aortic outflow legitimately opens to background.
    surface = pool & ~ndimage.binary_erosion(pool, six, border_value=0)
    open_share = (surface & ndimage.binary_dilation(read == L.BACKGROUND, six)).sum() / max(
        1, surface.sum())
    if open_share > 0.25:
        warnings.append(f"{open_share:.0%} of the LV pool's surface faces background; "
                        "check the wall is complete away from the valve planes.")
    return errors, warnings


def plateaus(read: np.ndarray, ct: np.ndarray, spacing, cfg: CheckConfig,
             ) -> Dict[str, Optional[float]]:
    """Median HU of LV blood, RV blood, myocardium and epicardial fat, from the read."""
    out: Dict[str, Optional[float]] = {}
    for key, value in (("lv_blood", L.LV_POOL), ("rv_blood", L.RV_POOL)):
        mask = read == value
        deep = mask & (_edt(~mask, spacing) >= cfg.blood_core_mm)
        out[key] = _median(ct[deep], cfg.min_voxels)
    myo = read == L.LV_MYO
    core = myo & (_edt(~myo, spacing) >= cfg.myo_core_mm)
    out["myocardium"] = _median(ct[core], cfg.min_voxels)
    to_myo = _edt(myo, spacing)
    lo, hi = cfg.fat_window_hu
    near, far = cfg.fat_shell_mm
    fat = ((read == L.BACKGROUND) & (to_myo >= near) & (to_myo <= far)
           & (ct >= lo) & (ct <= hi))
    out["epicardial_fat"] = _median(ct[fat], cfg.min_voxels)
    return out


def _side(offset: float) -> str:
    """Canonical sign in words: + spills past the edge, - stops short of it."""
    return "past" if offset > 0 else "short of"


def _half(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else 0.5 * (a + b)


def check_read(read: np.ndarray, ct: np.ndarray, spacing: Sequence[float],
               cfg: Optional[CheckConfig] = None, seed: Optional[np.ndarray] = None,
               hinge_points_mm: Optional[Sequence[Sequence[float]]] = None) -> CheckReport:
    """Check one read against the half-maximum rule and the JA1 / JA46 conventions.

    ``read``, ``ct`` and ``seed`` (optional) are on the same grid; ``spacing`` is in
    mm, in array axis order; ``ct`` is in HU. ``hinge_points_mm`` are in mm in array
    axis order, relative to the uncropped array's first voxel.
    """
    cfg = cfg or CheckConfig()
    if read.shape != ct.shape:
        raise ValueError(f"read {read.shape} and CT {ct.shape} are not on one grid")
    spacing = tuple(float(s) for s in spacing)
    box = _crop(read, spacing, cfg.band_mm + cfg.margin_mm)
    if seed is not None and seed.shape != read.shape:
        raise ValueError(f"seed {seed.shape} and read {read.shape} are not on one grid")
    read = np.asarray(read[box]).astype(np.int16)
    ct = np.asarray(ct[box]).astype(np.float32)
    if seed is not None:
        seed = np.asarray(seed[box]).astype(np.int16)
    if hinge_points_mm is not None and len(hinge_points_mm):
        shift = np.array([sl.start * float(sp) for sl, sp in zip(box, spacing)])
        hinge_points_mm = np.asarray(hinge_points_mm, dtype=np.float64) - shift

    errors, warnings = check_conventions(read, spacing, cfg, seed=seed,
                                         hinge_points_mm=hinge_points_mm)
    pl: Dict[str, Optional[float]] = {}
    borders: Dict[str, BorderResult] = {}
    if not any(e.startswith(("Label values", "These Janus-M")) for e in errors):
        pl = plateaus(read, ct, spacing, cfg)
        pool = read == L.LV_POOL
        centre = (np.array(ndimage.center_of_mass(pool)) * np.array(spacing)).tolist()
        sectors = _sector_ids(read.shape, spacing, centre)
        myo = read == L.LV_MYO
        bg = read == L.BACKGROUND
        rv = read == L.RV_POOL
        la = read == L.LA_POOL
        specs = [
            ("endocardial", pool, myo, bg | rv | la, ("lv_blood", "myocardium")),
            ("epicardial", myo, bg, pool | rv | la, ("myocardium", "epicardial_fat")),
            ("septal_rv", myo, rv, pool | bg | la, ("myocardium", "rv_blood")),
        ]
        for name, inside, outside, others, keys in specs:
            pair = (pl[keys[0]], pl[keys[1]])
            b = _border(name, inside, outside, others, ct, spacing, _half(*pair), sectors,
                        cfg, pair=pair)
            borders[name] = b
            if b.skipped:
                warnings.append(f"The {name} border was not checked: {b.skipped}.")
                continue
            if b.offset_mm is None:
                errors.append(f"The {name} border has no half-maximum crossing within "
                              f"±{cfg.band_mm:g} mm of the read's border.")
                continue
            if abs(b.offset_mm) > cfg.tolerance_mm:
                errors.append(f"The {name} border is {abs(b.offset_mm):.2f} mm "
                              f"{_side(b.offset_mm)} the half-maximum edge (median over the "
                              f"border; tolerance {cfg.tolerance_mm:g} mm).")
            # JA46 (c): octants warn, never fail.
            for sector, value in sorted(b.sectors.items()):
                if value is not None and abs(value) > cfg.octant_warning_mm:
                    warnings.append(f"Part of the {name} border ({sector}) is "
                                    f"{abs(value):.1f} mm {_side(value)} the half-maximum "
                                    f"edge (warning above {cfg.octant_warning_mm:g} mm).")
    return CheckReport(passed=not errors, errors=errors, warnings=warnings,
                       plateaus_hu=pl, borders=borders, config=cfg)


def check_files(read_path, ct_path, cfg: Optional[CheckConfig] = None,
                seed_path=None) -> CheckReport:
    """:func:`check_read` on NIfTI files (read, CT and optionally the seed), which must
    share one grid."""
    import nibabel as nib

    ci = nib.load(str(ct_path))

    def on_grid(path):
        img = nib.load(str(path))
        if img.shape[:3] != ci.shape[:3] or not np.allclose(img.affine, ci.affine, atol=1e-3):
            raise ValueError(f"{path} is not on the CT's grid ({img.shape} vs {ci.shape})")
        return np.asarray(img.dataobj).astype(np.int16)

    read = on_grid(read_path)
    seed = on_grid(seed_path) if seed_path else None
    ct = np.asarray(ci.dataobj, dtype=np.float32)
    spacing = ci.header.get_zooms()[:3]
    return check_read(read, ct, spacing, cfg, seed=seed)


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Check a Janus-M read (border protocol v1).")
    p.add_argument("read")
    p.add_argument("ct")
    p.add_argument("--seed", help="the case's seed (the mitral plane is fitted to it)")
    p.add_argument("--tolerance-mm", type=float, default=CheckConfig.tolerance_mm)
    args = p.parse_args(argv)
    report = check_files(args.read, args.ct, CheckConfig(tolerance_mm=args.tolerance_mm),
                         seed_path=args.seed)
    print(report.to_json())
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
