"""E11 (Round 5, #223 item 2): the #219 engineer's remedy for R4-S4's failed open-base check.

The remedy, as #223 states it: besides JA61's exclusions (<= 3 mm of label 4, <= 3 mm of an LV-pool
face adjoining label 0), "also exclude <= 3 mm of any pool or myocardium face that adjoins label 0,
because the cut basal cap adds area with no volume change".

Every band variant is built here; shipped code (``janusm.harness``) is only called, never changed.

Variants (each = the shipped ``harness.ja37_band`` minus a further exclusion):
- ``shipped``: JA61 as built (#219).
- ``literal``: minus <= 3 mm of every solid (pool or myocardium) face adjoining label 0. The
  label set has no aorta, RA or pericardium (``geometry``: 0 MYO LV RV LA), so the free
  epicardial wall adjoins label 0 everywhere it does not touch the RV or LA.
- ``rim15``: minus <= 3 mm of the solid faces adjoining label 0 that lie within 15 mm (>= any LV
  wall) of an open pool face: the cap and the wall just under it, not the whole epicardium.
- ``plane``: minus <= 3 mm of the solid faces adjoining label 0 that lie within 1 mm of the plane
  fitted (least squares) to the open pool faces: the cap only.

Phantoms (synthetic only; no case is opened):
- A. India's open-base E6 phantom (the fixture of
  ``test_open_base_india_phantom_with_the_band``): two grids, three walls, both borders,
  +-0.3 / +-0.5 mm; truth = mean normal displacement in the band.
- B. ``validate_bias_estimator(open_base=True)``'s cut capsule (``harness._open_base_parts``), three
  offsets, three shapes, two grids; truth = the shift.
- C. A read-like phantom: ``harness.phantom()`` (LA over the base, RV over the septum) with the LA
  removed over a 60 degree sector, so the base is open to label 0 there as at the outflow; tilt 0
  and 23 degrees; truth = the shift. Also reports how much of each border's band each variant keeps.

    python experiments/JanusM/Hotel/r5/e11_open_base_remedy.py OUT_JSON [--quick]
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from janusm import geometry as G
from janusm import harness as H
from janusm.guard import refuse

refuse([], what="E11 (synthetic phantoms; no case)")

W = H.JA37_BAND_MM
SHIFTS = (-0.5, -0.3, 0.3, 0.5)
TOL = H.BIAS_CHECK_TOLERANCE_MM


# ------------------------------------------------------------------ face centres and band variants
def faces_to_zero(mask, lab):
    """Centres (mm, voxel-index frame x spacing) and axis of every face between a ``mask`` voxel and
    label 0 (the array's edge counts as label 0, as in ``ja37_band``)."""
    m = np.pad(np.asarray(mask, bool), 1)
    bg = np.pad(np.asarray(lab) == 0, 1, constant_values=True)
    out = []
    for a in range(3):
        for step in (1, -1):
            idx = np.argwhere(m & np.roll(bg, -step, axis=a)).astype(float)
            idx[:, a] += 0.5 * step
            out.append(idx - 1.0)
    return np.concatenate(out)


def minus_near(band, centres_mm, sp, width=W):
    band = band.copy()
    if len(centres_mm) == 0:
        return band
    cand = np.argwhere(band)
    d, _ = cKDTree(centres_mm).query(cand * sp, distance_upper_bound=width + 1e-9)
    near = np.isfinite(d) & (d <= width)
    band[tuple(cand[near].T)] = False
    return band


def bands(lab, sp, border):
    sp = np.asarray(sp, float)
    cav, sol = H.borders(lab)
    base = H.ja37_band(lab, sp, border)
    pool_open = faces_to_zero(cav, lab) * sp
    solid_open = faces_to_zero(sol, lab) * sp
    out = {"shipped": base, "literal": minus_near(base, solid_open, sp)}
    if len(pool_open):
        d, _ = cKDTree(pool_open).query(solid_open, distance_upper_bound=15.0 + 1e-9)
        out["rim15"] = minus_near(base, solid_open[np.isfinite(d)], sp)
        c = pool_open.mean(0)
        n = np.linalg.svd(pool_open - c, full_matrices=False)[2][-1]
        cap = solid_open[np.abs((solid_open - c) @ n) <= 1.0]
        out["plane"] = minus_near(base, cap, sp)
    else:  # nothing is open: the remedies other than ``literal`` change nothing
        out["rim15"] = out["plane"] = base
    return out


def est(ref, test, sp, band):
    return H.signed_bias(ref, test, sp, roi=band) if band.any() else float("nan")


# ------------------------------------------------------------------ A: India's open-base E6 phantom
E6_BOX = np.array([84.0, 84.0, 76.0])


def e6_phantom(sp, rot_seed, rough):
    """Copied from ``tests/test_janusm_harness.py::_e6_phantom`` (Hotel E6)."""
    sp = np.asarray(sp, float)
    n = np.ceil(E6_BOX / sp).astype(int)
    X = [(np.arange(k) + 0.5) * s - b / 2 for k, s, b in zip(n, sp, E6_BOX)]
    P = np.stack(np.meshgrid(*X, indexing="ij"), -1).reshape(-1, 3)
    R = Rotation.random(random_state=rot_seed).as_matrix() if rot_seed is not None else np.eye(3)
    Q = P @ R
    qx, qy, zz = Q[:, 0], Q[:, 1], 30.0 - Q[:, 2]

    def ell(x0, a, c):
        q = ((qx - x0) / a) ** 2 + (qy / a) ** 2 + (zz / c) ** 2
        g = 2 * np.sqrt(((qx - x0) / a**2) ** 2 + (qy / a**2) ** 2 + (zz / c**2) ** 2)
        return (q - 1) / np.maximum(g, 1e-9)

    Fs, Fc = ell(0.0, 32.0, 56.0).reshape(n), ell(4.0, 22.0, 48.0).reshape(n)
    if rough:
        rng = np.random.default_rng(1000 + (rot_seed or 0))
        for F in (Fs, Fc):
            f = ndi.gaussian_filter(rng.standard_normal(n), 3.0 / sp)
            F += 0.6 * f / f.std()
    base = (-zz).reshape(n)
    return Fc.astype(np.float32), Fs.astype(np.float32), base


def e6_truth(F, s, sp, roi):
    """Copied from ``tests/test_janusm_harness.py::_e6_truth``."""
    band = (np.abs(F) < 0.5 * float(np.min(sp))) & roi
    gm = np.sqrt(sum(g * g for g in np.gradient(F, *sp)))[band]
    return float((s / np.maximum(gm, 1e-6)).mean())


def run_a(grids):
    rows = []
    for sp in grids:
        for rot, rough in [(None, False), (23, False), (11, True)]:
            Fc, Fs, base = e6_phantom(sp, rot, rough)
            cav, sol = (Fc < 0) & (base < 0), (Fs < 0) & (base < 0)
            lab = np.zeros(cav.shape, np.int16)
            lab[sol | cav] = G.MYO
            lab[cav] = G.LV
            for border, F in (("endo", Fc), ("epi", Fs)):
                ref = (F < 0) & (base < 0)
                bs = bands(lab, sp, border)
                for shift in SHIFTS:
                    test = ((F - shift) < 0) & (base < 0)
                    for v, b in bs.items():
                        e = est(ref, test, sp, b)
                        t = e6_truth(F, shift, sp, b) if b.any() else float("nan")
                        rows.append(
                            dict(
                                phantom="A",
                                grid=list(sp),
                                wall=f"{rot}/{rough}",
                                border=border,
                                shift=shift,
                                variant=v,
                                band_vox=int(b.sum()),
                                err=e - t,
                            )
                        )
    return rows


# ------------------------------------------------------------------ B: the cut capsule
def run_b(grids, n_offsets):
    rng = np.random.default_rng(20261030)
    rows = []
    for grid in grids:
        offs = rng.uniform(0.0, float(np.max(grid)), size=(n_offsets, 3))
        for cs, tilt in ((0.0, 0.0), (2.3, 0.0), (2.3, 23.0)):
            for off in offs:
                cav_r, sol_r, lab_r, aff = H._open_base_parts(grid, 0.0, 0.0, off, cs, tilt)
                sp = np.linalg.norm(aff[:3, :3], axis=0)
                for border in ("endo", "epi"):
                    bs = bands(lab_r, sp, border)
                    for shift in SHIFTS:
                        sh = (shift, 0.0) if border == "endo" else (0.0, shift)
                        cav_t, sol_t, _, _ = H._open_base_parts(grid, *sh, off, cs, tilt)
                        a, t = (cav_r, cav_t) if border == "endo" else (sol_r, sol_t)
                        for v, b in bs.items():
                            rows.append(
                                dict(
                                    phantom="B",
                                    grid=list(grid),
                                    wall=f"{cs}/{tilt}",
                                    border=border,
                                    shift=shift,
                                    variant=v,
                                    band_vox=int(b.sum()),
                                    err=est(a, t, sp, b) - shift,
                                )
                            )
    return rows


# ---------------------------------------------------- C: read-like, LA over most of the base
def open_sector(lab, aff, tilt):
    """Remove the LA over phi in [20, 80] degrees, so the base is open to label 0 there."""
    sp = np.linalg.norm(aff[:3, :3], axis=0)
    idx = np.indices(lab.shape).reshape(3, -1).T * sp + aff[:3, 3]
    x, y, z = idx.T
    t = np.radians(tilt)
    y = np.cos(t) * y + np.sin(t) * z
    phi = (np.degrees(np.arctan2(y, x)) % 360).reshape(lab.shape)
    out = lab.copy()
    out[(lab == G.LA) & (phi >= 20) & (phi <= 80)] = 0
    return out


def run_c():
    rows = []
    sp = np.full(3, H.GRID_MM)
    for tilt in (0.0, 23.0):
        lab0, aff = H.phantom(tilt_deg=tilt, cavity_shift_mm=2.3)
        lab = open_sector(lab0, aff, tilt)
        cav_r, sol_r = H.borders(lab)
        for border in ("endo", "epi"):
            bs = bands(lab, sp, border)
            for shift in SHIFTS:
                kw = {"endo_shift_mm": shift} if border == "endo" else {"epi_shift_mm": shift}
                labt = open_sector(
                    H.phantom(tilt_deg=tilt, cavity_shift_mm=2.3, **kw)[0], aff, tilt
                )
                cav_t, sol_t = H.borders(labt)
                a, t = (cav_r, cav_t) if border == "endo" else (sol_r, sol_t)
                for v, b in bs.items():
                    rows.append(
                        dict(
                            phantom="C",
                            grid=list(sp),
                            wall=f"2.3/{tilt}",
                            border=border,
                            shift=shift,
                            variant=v,
                            band_vox=int(b.sum()),
                            err=est(a, t, sp, b) - shift,
                        )
                    )
    return rows


def summarise(rows):
    out = {}
    for ph in sorted({r["phantom"] for r in rows}):
        for v in ("shipped", "literal", "rim15", "plane"):
            for border in ("endo", "epi"):
                sel = [
                    r
                    for r in rows
                    if r["phantom"] == ph and r["variant"] == v and r["border"] == border
                ]
                errs = np.array([r["err"] for r in sel])
                fin = errs[np.isfinite(errs)]
                key = f"{ph}/{v}/{border}"
                out[key] = {
                    "n": len(sel),
                    "n_empty_band": int((~np.isfinite(errs)).sum()),
                    "worst_abs_err_mm": float(np.abs(fin).max()) if len(fin) else None,
                    "mean_err_mm": float(fin.mean()) if len(fin) else None,
                    "min_band_vox": int(min(r["band_vox"] for r in sel)),
                    "pass_0_05": bool(len(fin) == len(sel) and np.abs(fin).max() <= TOL),
                }
    return out


def main(argv):
    out = argv[0]
    quick = "--quick" in argv
    t0 = time.time()
    grids = [(0.5, 0.5, 0.5)] if quick else [(0.5, 0.5, 0.5), (0.4, 0.4, 0.5)]
    rows = run_c() + run_b(grids, 1 if quick else 3) + run_a(grids)
    res = {
        "experiment": "E11",
        "issue": "#223 item 2",
        "harness_version": H.HARNESS_VERSION,
        "tolerance_mm": TOL,
        "quick": quick,
        "seconds": round(time.time() - t0, 1),
        "summary": summarise(rows),
        "rows": rows,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    for k, v in res["summary"].items():
        print(k, v)


if __name__ == "__main__":
    main(sys.argv[1:])
