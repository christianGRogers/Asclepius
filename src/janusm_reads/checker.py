"""The automatic check every submitted Janus-M read goes through (JA7).

Two parts, both on the read's own grid (the CT's):

**Label conventions (JA1).** Values only 0-4, all four classes present; the LV and
RV pools never touch (the septum is myocardium); papillary muscles and trabeculae
are in the LV pool, so the pool has no enclosed holes; the myocardium is one piece.

**Hotel's half-maximum rule.** A border lies halfway between the plateaus on
either side of it. For each border the check measures the plateaus from the read's
own labels, then the CT profile across the read's border as a function of signed
distance to it, and finds where that profile crosses the half-way value. That
crossing's distance from the read's border is the border's **offset**:

* ``offset > 0``: the image border lies *outside* the read's region (the read is
  drawn too far in);
* ``offset < 0``: the read's region spills past the image border.

Three borders, each with its own pair of plateaus:

=================  =====================  ==========================  ============
border             inside / outside        plateaus                   region
=================  =====================  ==========================  ============
``endocardial``    LV pool / myocardium    LV blood, myocardium       class 2
``epicardial``     myocardium / outside    myocardium, epicardial fat class 1 vs 0
``septal_rv``      myocardium / RV pool    myocardium, RV blood       class 1 vs 3
=================  =====================  ==========================  ============

Each offset is measured over the whole border and in eight sectors (octants about
the LV pool's centre), so a local error is caught as well as a global bias. A read
fails when any offset is beyond :attr:`CheckConfig.tolerance_mm`.

The tolerance, the bands and the fat window are **placeholders until Round 2**
(``docs/JANUSM-READ-PROTOCOL.md`` §6); they live in :class:`CheckConfig` so they
change in one place.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage

from . import labels as L


@dataclass
class CheckConfig:
    #: A border whose half-maximum offset (whole border or one sector) exceeds this
    #: fails. Placeholder (Round 2); JA8's bias guard is 0.5 mm on the *model*.
    tolerance_mm: float = 1.0
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
    max_pool_contact_share: float = 0.005   # LV-pool faces touching the RV pool
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
        }

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


def _crossing(s: np.ndarray, hu: np.ndarray, threshold: float, cfg: CheckConfig,
              ) -> Optional[float]:
    """Where the median-HU-versus-signed-distance profile crosses ``threshold``,
    nearest to the read's border (s = 0). None if it never does within the band."""
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


def _sector_ids(shape, spacing, centre) -> np.ndarray:
    """Octant (0..7) of every voxel about ``centre`` (physical axes)."""
    grids = np.indices(shape, dtype=np.float32)
    out = np.zeros(shape, dtype=np.uint8)
    for axis in range(3):
        out |= ((grids[axis] * spacing[axis] >= centre[axis]).astype(np.uint8) << axis)
    return out


def _border(name, inside, outside, others, ct, spacing, threshold, sectors, cfg):
    """Signed-distance profile across the inside/outside border, whole and per sector."""
    result = BorderResult(name=name)
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
    result.offset_mm = _crossing(s, hu, threshold, cfg)
    for k in range(8):
        m = sec == k
        n_in = int(np.count_nonzero(m[: int(sel_in.sum())]))
        n_out = int(np.count_nonzero(m)) - n_in
        if n_in < cfg.min_voxels or n_out < cfg.min_voxels:
            continue
        result.sectors[f"octant{k}"] = _crossing(s[m], hu[m], threshold, cfg)
    return result


# --------------------------------------------------------------- the checks


def check_conventions(read: np.ndarray, spacing, cfg: Optional[CheckConfig] = None,
                      ) -> Tuple[List[str], List[str]]:
    """JA1 label conventions. Returns ``(errors, warnings)``."""
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


def _half(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else 0.5 * (a + b)


def check_read(read: np.ndarray, ct: np.ndarray, spacing: Sequence[float],
               cfg: Optional[CheckConfig] = None) -> CheckReport:
    """Check one read against the half-maximum rule and the JA1 conventions.

    ``read`` and ``ct`` are on the same grid; ``spacing`` is in mm, in array axis
    order; ``ct`` is in HU.
    """
    cfg = cfg or CheckConfig()
    if read.shape != ct.shape:
        raise ValueError(f"read {read.shape} and CT {ct.shape} are not on one grid")
    spacing = tuple(float(s) for s in spacing)
    box = _crop(read, spacing, cfg.band_mm + cfg.margin_mm)
    read = np.asarray(read[box]).astype(np.int16)
    ct = np.asarray(ct[box]).astype(np.float32)

    errors, warnings = check_conventions(read, spacing, cfg)
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
            ("endocardial", pool, myo, bg | rv | la, _half(pl["lv_blood"], pl["myocardium"])),
            ("epicardial", myo, bg, pool | rv | la, _half(pl["myocardium"],
                                                          pl["epicardial_fat"])),
            ("septal_rv", myo, rv, pool | bg | la, _half(pl["myocardium"], pl["rv_blood"])),
        ]
        for name, inside, outside, others, threshold in specs:
            b = _border(name, inside, outside, others, ct, spacing, threshold, sectors, cfg)
            borders[name] = b
            if b.skipped:
                warnings.append(f"The {name} border was not checked: {b.skipped}.")
                continue
            if b.offset_mm is None:
                errors.append(f"The {name} border has no half-maximum crossing within "
                              f"±{cfg.band_mm:g} mm of the read's border.")
                continue
            if abs(b.offset_mm) > cfg.tolerance_mm:
                side = "inside" if b.offset_mm > 0 else "outside"
                errors.append(f"The {name} border is {abs(b.offset_mm):.1f} mm {side} the "
                              f"half-maximum edge (tolerance {cfg.tolerance_mm:g} mm).")
                continue
            sector, worst = b.worst_sector()
            if worst is not None and abs(worst) > cfg.tolerance_mm:
                side = "inside" if worst > 0 else "outside"
                errors.append(f"Part of the {name} border ({sector}) is {abs(worst):.1f} mm "
                              f"{side} the half-maximum edge (tolerance "
                              f"{cfg.tolerance_mm:g} mm).")
    return CheckReport(passed=not errors, errors=errors, warnings=warnings,
                       plateaus_hu=pl, borders=borders, config=cfg)


def check_files(read_path, ct_path, cfg: Optional[CheckConfig] = None) -> CheckReport:
    """:func:`check_read` on two NIfTI files, which must share one grid."""
    import nibabel as nib

    ri, ci = nib.load(str(read_path)), nib.load(str(ct_path))
    if ri.shape[:3] != ci.shape[:3] or not np.allclose(ri.affine, ci.affine, atol=1e-3):
        raise ValueError(f"{read_path} is not on the CT's grid ({ri.shape} vs {ci.shape})")
    read = np.asarray(ri.dataobj).astype(np.int16)
    ct = np.asarray(ci.dataobj, dtype=np.float32)
    spacing = ci.header.get_zooms()[:3]
    return check_read(read, ct, spacing, cfg)


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Check a Janus-M read (JA7).")
    p.add_argument("read")
    p.add_argument("ct")
    p.add_argument("--tolerance-mm", type=float, default=CheckConfig.tolerance_mm)
    args = p.parse_args(argv)
    report = check_files(args.read, args.ct, CheckConfig(tolerance_mm=args.tolerance_mm))
    print(report.to_json())
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
