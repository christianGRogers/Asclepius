"""India R5, item 2 of #223: the #219 engineer's band remedy, as a candidate amendment to JA61.

The shipped band (``harness.ja37_band``) leaves the cut myocardial base cap in the epicardial
band: it adjoins label 0 but is no LV-pool face, so its fixed area enters the denominator of
``signed_bias`` with no volume change. JA61's open-base check fails on the epicardium at
+-0.5 mm, and the guard is 0.5 mm. The remedy (#219, as #223 states it): also exclude <= 3 mm
of any pool or myocardium face that adjoins label 0.

Three bands, each scored on the same phantoms the shipped tests use:

* ``shipped``: ``harness.ja37_band`` as merged (the baseline; reproduces the FAIL).
* ``literal``: the remedy as worded. Every solid (pool or myocardium) face adjoining label 0 is
  excluded with its 3 mm. On a phantom, and on most of a real read, the whole epicardium adjoins
  label 0, so this is expected to empty the epicardial band.
* ``cap``: the remedy scoped to the cut cap. A solid face adjoining label 0 is a cap face only
  if it lies within ``CAP_REACH_MM`` of an open pool face and its outward normal is within
  ``CAP_ANGLE_DEG`` of that nearest open pool face's normal. No base plane and no extra label
  are needed. Its 3 mm is excluded as the remedy says.

Phantoms (synthetic only; no case is opened):

* E6-open: India's open-base phantom (the shipped ``india_open_base`` fixture: E6's ellipsoid
  cut at the base, two grids, three walls, both borders, +-0.3 / +-0.5 mm), truth = the mean
  normal displacement of the level set in each band.
* capsule: ``validate_bias_estimator(open_base=True)``'s cut capsule, 3 sub-voxel offsets, same
  grids, walls and shifts; truth = the shift (exact level sets).
* closed: E4's closed shell in a myocardial shell (radius 12 and 21 mm) and the closed capsule,
  both borders, which no remedy should move.
* label 4: ``harness.phantom`` (pool opens into the LA). The remedy should leave its band as is.

Pass, as JA61: |error| <= 0.05 mm on every row of a phantom set.

Run from the repo root:  python experiments/JanusM/India/r5/b1_band_remedy.py [--quick]
Writes ``b1_band_remedy.json`` beside this file.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
import time

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from janusm import geometry as G  # noqa: E402
from janusm import guard  # noqa: E402
from janusm import harness as H  # noqa: E402

spec = importlib.util.spec_from_file_location("th", ROOT / "tests" / "test_janusm_harness.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

CAP_REACH_MM = 20.0  # > any LV wall, so the whole width of a cut cap is reachable
CAP_ANGLE_DEG = 45.0
TOL = H.BIAS_CHECK_TOLERANCE_MM


# ------------------------------------------------------------------------------------ faces
def _faces(inside, outside):
    """Face centres (voxel index units, unpadded) and axis-sign between an ``inside`` voxel and a
    face-neighbour in ``outside`` (array edge counts as outside)."""
    a_in = np.pad(inside, 1)
    a_out = np.pad(outside, 1, constant_values=True)
    out = []
    for ax in range(3):
        for step in (1, -1):
            nb = np.roll(a_out, -step, axis=ax)
            idx = np.argwhere(a_in & nb).astype(float)
            idx[:, ax] += 0.5 * step
            out.append(idx - 1.0)
    return np.concatenate(out) if out else np.zeros((0, 3))


def _normals(mask, pts_idx):
    """Outward unit normals of ``mask`` at voxel-index points (gradient of the mask smoothed by
    one voxel, trilinear)."""
    f = ndi.gaussian_filter(np.pad(mask.astype(np.float32), 3), 1.0)
    g = np.stack(np.gradient(f), 0)
    c = (pts_idx + 3.0).T
    n = -np.stack([ndi.map_coordinates(g[k], c, order=1) for k in range(3)], 1)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


def _drop_near(band, centres_idx, sp, width):
    if not len(centres_idx):
        return band
    band = band.copy()
    cand = np.argwhere(band)
    d, _ = cKDTree(centres_idx * sp).query(cand * sp, distance_upper_bound=width + 1e-9)
    near = np.isfinite(d) & (d <= width)
    band[tuple(cand[near].T)] = False
    return band


def band_literal(lab, sp, border, width=H.JA37_BAND_MM):
    sp = np.asarray(sp, float)
    band = H.ja37_band(lab, sp, border, width)
    cav, sol = H.borders(lab)
    return _drop_near(band, _faces(sol, lab == 0), sp, width)


def cap_faces(lab, sp, reach=CAP_REACH_MM, angle=CAP_ANGLE_DEG):
    """Solid faces adjoining label 0 that are part of a cut cap: within ``reach`` of an open
    pool face, with an outward normal within ``angle`` of that pool face's normal."""
    sp = np.asarray(sp, float)
    cav, sol = H.borders(lab)
    bg = lab == 0
    pf = _faces(cav, bg)
    if not len(pf):
        return np.zeros((0, 3))
    sf = _faces(sol, bg)
    pn = _normals(cav, pf)
    sn = _normals(sol, sf)
    d, j = cKDTree(pf * sp).query(sf * sp, distance_upper_bound=reach)
    ok = np.isfinite(d)
    cosang = np.zeros(len(sf))
    cosang[ok] = (sn[ok] * pn[j[ok]]).sum(1)
    return sf[ok & (cosang >= np.cos(np.radians(angle)))]


def band_cap(lab, sp, border, width=H.JA37_BAND_MM):
    sp = np.asarray(sp, float)
    band = H.ja37_band(lab, sp, border, width)
    return _drop_near(band, cap_faces(lab, sp), sp, width)


BANDS = {"shipped": lambda lab, sp, b: H.ja37_band(lab, sp, b), "literal": band_literal,
         "cap": band_cap}


def _est(ref, test, sp, band):
    if band is None or not band.any():
        return float("nan"), 0
    return H.signed_bias(ref, test, sp, roi=band), int(band.sum())


# ------------------------------------------------------------------------------------ phantoms
def run_e6(grids, walls, shifts):
    rows = []
    for sp in grids:
        for rot, rough in walls:
            Fc, Fs, base, _ = T._e6_phantom(sp, rot, rough)
            lab = T._e6_labels(Fc, Fs, base)
            for border, F in (("endo", Fc), ("epi", Fs)):
                ref = (F < 0) & (base < 0)
                bands = {k: f(lab, sp, border) for k, f in BANDS.items()}
                for s in shifts:
                    test = ((F - s) < 0) & (base < 0)
                    for k, band in bands.items():
                        est, nb = _est(ref, test, sp, band)
                        tb = T._e6_truth(F, s, sp, band)[0] if nb else float("nan")
                        rows.append(dict(phantom="E6-open", band=k, grid=list(sp), rot=rot,
                                         rough=rough, border=border, shift=s, band_voxels=nb,
                                         truth=tb, est=est, err=est - tb))
    return rows


def run_capsule(grids, shapes, shifts, n_offsets, seed=20261030):
    rows = []
    rng = np.random.default_rng(seed)  # the same draws as validate_bias_estimator
    for grid in grids:
        offsets = rng.uniform(0.0, float(np.max(grid)), size=(n_offsets, 3))
        for cs, tilt in shapes:
            for off in offsets:
                cav_r, sol_r, lab, aff = H._open_base_parts(grid, 0.0, 0.0, off, cs, tilt)
                sp = np.linalg.norm(aff[:3, :3], axis=0)
                for border in ("endo", "epi"):
                    bands = {k: f(lab, sp, border) for k, f in BANDS.items()}
                    for s in shifts:
                        sh = (s, 0.0) if border == "endo" else (0.0, s)
                        cav_t, sol_t, _, _ = H._open_base_parts(grid, *sh, off, cs, tilt)
                        a, t = (cav_r, cav_t) if border == "endo" else (sol_r, sol_t)
                        for k, band in bands.items():
                            est, nb = _est(a, t, sp, band)
                            rows.append(dict(phantom="capsule", band=k, grid=list(grid),
                                             cavity_shift=cs, tilt=tilt, border=border, shift=s,
                                             band_voxels=nb, truth=s, est=est, err=est - s))
    return rows


def run_closed():
    rows = []
    sp = np.array([H.GRID_MM] * 3)
    for radius in (12.0, 21.0):  # E4's shells, as the shipped test builds them
        rng = np.random.default_rng(int(radius) + 1)
        n = int(2 * (radius + 9) / H.GRID_MM)
        ax = (np.arange(n) - n / 2) * H.GRID_MM
        X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij", sparse=True)
        c = rng.uniform(-H.GRID_MM / 2, H.GRID_MM / 2, 3)
        R = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
        lab = np.zeros(R.shape, np.int16)
        lab[R < radius + 5] = G.MYO
        lab[R < radius] = G.LV
        for border, r0 in (("endo", radius), ("epi", radius + 5)):
            ref = R < r0
            bands = {k: f(lab, sp, border) for k, f in BANDS.items()}
            for d in (-0.5, -0.3, 0.3, 0.5):
                for k, band in bands.items():
                    est, nb = _est(ref, R < r0 + d, sp, band)
                    rows.append(dict(phantom=f"E4-shell-r{int(radius)}", band=k, border=border,
                                     shift=d, band_voxels=nb, truth=d, est=est, err=est - d))
    return rows


def run_label4():
    """harness.phantom: the pool opens into the LA (label 4); no open pool face to label 0."""
    rows = []
    lab, aff = H.phantom()
    sp = np.linalg.norm(aff[:3, :3], axis=0)
    for border in ("endo", "epi"):
        b = {k: f(lab, sp, border) for k, f in BANDS.items()}
        rows.append(dict(phantom="label4", border=border,
                         identical_to_shipped={k: bool((v == b["shipped"]).all())
                                               for k, v in b.items()},
                         band_voxels={k: int(v.sum()) for k, v in b.items()}))
    return rows


def summarise(rows):
    out = {}
    for ph in sorted({r["phantom"] for r in rows}):
        for k in BANDS:
            sel = [r for r in rows if r["phantom"] == ph and r["band"] == k]
            if not sel:
                continue
            per = {}
            for border in ("endo", "epi"):
                for mag in sorted({abs(r["shift"]) for r in sel}):
                    s = [r for r in sel if r["border"] == border and abs(r["shift"]) == mag]
                    e = np.array([r["err"] for r in s])
                    per[f"{border}_{mag}"] = {
                        "n": len(s),
                        "n_empty_band": int(sum(r["band_voxels"] == 0 for r in s)),
                        "worst_abs_err": None if np.isnan(e).all() else
                        round(float(np.nanmax(np.abs(e))), 4),
                        "mean_err": None if np.isnan(e).all() else round(float(np.nanmean(e)), 4),
                    }
            e = np.array([r["err"] for r in sel])
            worst = float(np.max(np.abs(e))) if not np.isnan(e).any() else float("nan")
            out[f"{ph}/{k}"] = {
                "n": len(sel),
                "worst_abs_err": None if np.isnan(worst) else round(worst, 4),
                "any_empty_band": bool(np.isnan(e).any()),
                "passes_0.05": bool(not np.isnan(e).any() and worst <= TOL),
                "by": per,
            }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="one grid, one wall, one offset")
    a = ap.parse_args()
    guard.refuse([], what="India R5 b1 band remedy (synthetic phantoms; no case opened)")
    t0 = time.time()
    grids = [(0.5, 0.5, 0.5)] if a.quick else [(0.5, 0.5, 0.5), (0.4, 0.4, 0.5)]
    walls = [(None, False)] if a.quick else [(None, False), (23, False), (11, True)]
    shapes = ((0.0, 0.0),) if a.quick else ((0.0, 0.0), (2.3, 0.0), (2.3, 23.0))
    shifts = (-0.5, -0.3, 0.3, 0.5)
    rows = []
    rows += run_e6(grids, walls, shifts)
    print(f"E6-open done {time.time() - t0:.0f}s", flush=True)
    rows += run_capsule(grids, shapes, shifts, 1 if a.quick else 3)
    print(f"capsule done {time.time() - t0:.0f}s", flush=True)
    rows += run_closed()
    l4 = run_label4()
    summ = summarise(rows)
    out = {
        "harness_version": H.HARNESS_VERSION,
        "quick": a.quick,
        "cap_reach_mm": CAP_REACH_MM,
        "cap_angle_deg": CAP_ANGLE_DEG,
        "tolerance_mm": TOL,
        "summary": summ,
        "label4": l4,
        "rows": rows,
        "seconds": round(time.time() - t0),
    }
    name = "b1_band_remedy_quick.json" if a.quick else "b1_band_remedy.json"
    pathlib.Path(__file__).with_name(name).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: {kk: v[kk] for kk in ("n", "worst_abs_err", "any_empty_band",
                                               "passes_0.05")} for k, v in summ.items()},
                     indent=1))
    print(json.dumps(l4, indent=1))


if __name__ == "__main__":
    main()
