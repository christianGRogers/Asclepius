"""Lima R5 E1: the #219 engineer's remedy for R4-S4's open-base failure (issue #223 item 2).

The shipped band (``janusm.harness.ja37_band``) drops voxels within 3 mm of label 4 and of any
LV-pool face adjoining label 0. On a cut mask the myocardial base cap also adjoins label 0, stays
in the epicardial band, and adds area with no volume change. The remedy: also drop voxels within
3 mm of any pool **or myocardium** face adjoining label 0.

This script measures four bands, none of them shipped code (the shipped band is called, not
changed; the variants live here):

- ``shipped``: ``H.ja37_band`` as merged in #219.
- ``literal``: the remedy as worded: 3 mm around every solid (pool | myocardium) face adjoining 0.
- ``cap_plane``: a narrow reading: fit a plane to the open pool faces' centres, and drop 3 mm
  around the solid faces adjoining 0 that lie within one voxel of that plane (the cut cap only).
- ``slab``: the shipped band, less every voxel within 3 mm of that plane or beyond it.

Each runs on the same phantoms as #219:

1. India's open-base E6 phantom (``tests/test_janusm_harness.py``'s ``india_open_base`` fixture,
   its helpers imported unchanged): two grids, three walls, both borders, +-0.3 / +-0.5 mm, truth =
   the mean normal displacement in the band.
2. ``validate_bias_estimator(open_base=True)`` with its default three offsets (the band is swapped
   by patching ``H.ja37_band`` for the call and restored after).
3. Controls: E4's closed shells (both borders), and ``H.phantom()``'s LA-capped heart (how much of
   the epicardial band each variant keeps).

Phantoms only; no case is opened.

    python experiments/JanusM/Lima/r5/e1_open_base_remedy.py experiments/JanusM/Lima/r5/e1_open_base_remedy.json
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from janusm import geometry as G  # noqa: E402
from janusm import guard  # noqa: E402
from janusm import harness as H  # noqa: E402

spec = importlib.util.spec_from_file_location("th", REPO / "tests" / "test_janusm_harness.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

W = H.JA37_BAND_MM
TOL = H.BIAS_CHECK_TOLERANCE_MM


def face_centres(mask, bg, sp):
    """Centres (mm) of the faces between a ``mask`` voxel and a face neighbour in ``bg``
    (the array's edge counts as ``bg``), as ``ja37_band`` computes them for the pool."""
    m = np.pad(mask, 1)
    b = np.pad(bg, 1, constant_values=True)
    out = []
    for a in range(3):
        for step in (1, -1):
            idx = np.argwhere(m & np.roll(b, -step, axis=a)).astype(float)
            idx[:, a] += 0.5 * step
            out.append(idx)
    c = np.concatenate(out)
    return (c - 1.0) * sp


def drop_near(band, centres, sp, width=W):
    band = band.copy()
    if not len(centres):
        return band
    cand = np.argwhere(band)
    if not len(cand):
        return band
    d, _ = cKDTree(centres).query(cand * sp, distance_upper_bound=width + 1e-9)
    near = np.isfinite(d) & (d <= width)
    band[tuple(cand[near].T)] = False
    return band


def opening_plane(lab, sp):
    """(point, unit normal pointing out of the pool) of the least-squares plane through the open
    pool faces, or None if the pool has none."""
    cav, _ = H.borders(lab)
    c = face_centres(cav, lab == 0, sp)
    if len(c) < 3:
        return None
    p0 = c.mean(0)
    n = np.linalg.svd(c - p0)[2][-1]
    pool_c = np.argwhere(cav).mean(0) * sp
    if np.dot(pool_c - p0, n) > 0:
        n = -n
    return p0, n


def band_variant(lab, sp, border, which):
    lab = np.asarray(lab)
    sp = np.asarray(sp, float)
    band = H.ja37_band(lab, sp, border)
    if which == "shipped":
        return band
    cav, sol = H.borders(lab)
    bg = lab == 0
    if which == "literal":
        return drop_near(band, face_centres(sol, bg, sp), sp)
    pl = opening_plane(lab, sp)
    if pl is None:
        return band
    p0, n = pl
    if which == "cap_plane":
        c = face_centres(sol, bg, sp)
        on = np.abs((c - p0) @ n) <= float(sp.max())
        return drop_near(band, c[on], sp)
    if which == "slab":
        ijk = np.argwhere(band)
        h = (ijk * sp - p0) @ n  # + = beyond the opening
        band[tuple(ijk[h > -W].T)] = False
        return band
    raise ValueError(which)


VARIANTS = ("shipped", "literal", "cap_plane", "slab")


def india(variants):
    rows = []
    for sp in [(0.5, 0.5, 0.5), (0.4, 0.4, 0.5)]:
        spa = np.asarray(sp)
        for rot, rough in [(None, False), (23, False), (11, True)]:
            Fc, Fs, base, _ = T._e6_phantom(sp, rot, rough)
            lab = T._e6_labels(Fc, Fs, base)
            for border, F in (("endo", Fc), ("epi", Fs)):
                ref = (F < 0) & (base < 0)
                full = ref.sum()
                bands = {v: band_variant(lab, spa, border, v) for v in variants}
                surf = np.abs(H.corrected_sdf(ref, spa)) <= 0.5 * spa.max()
                for shift in (-0.5, -0.3, 0.3, 0.5):
                    test = ((F - shift) < 0) & (base < 0)
                    for v, band in bands.items():
                        kept = int((band & surf).sum())
                        if not band.any() or kept == 0:
                            rows.append(dict(phantom="india", grid=sp, wall=[rot, rough],
                                             border=border, shift=shift, variant=v,
                                             err=None, kept_surface_vox=0))
                            continue
                        tb, _ = T._e6_truth(F, shift, spa, band)
                        est = H.signed_bias(ref, test, spa, roi=band)
                        rows.append(dict(phantom="india", grid=sp, wall=[rot, rough],
                                         border=border, shift=shift, variant=v,
                                         err=float(est - tb), kept_surface_vox=kept))
                del full
    return rows


def validate(variant):
    orig = H.ja37_band
    try:
        H.ja37_band = lambda lab, sp, b, width_mm=W: band_variant(lab, sp, b, variant)
        r = H.validate_bias_estimator(open_base=True)  # default n_offsets=3
    finally:
        H.ja37_band = orig
    return r


def e4(variants):
    out = []
    for radius in (12.0, 21.0):
        rng = np.random.default_rng(int(radius) + 1)
        n = int(2 * (radius + 9) / H.GRID_MM)
        ax = (np.arange(n) - n / 2) * H.GRID_MM
        X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij", sparse=True)
        c = rng.uniform(-H.GRID_MM / 2, H.GRID_MM / 2, 3)
        R = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
        lab = np.zeros(R.shape, np.int16)
        lab[R < radius + 5] = G.MYO
        lab[R < radius] = G.LV
        sp = np.asarray(T.SP, float)
        for border, r0 in (("endo", radius), ("epi", radius + 5)):
            for v in variants:
                band = band_variant(lab, sp, border, v)
                errs = []
                for d in (-0.5, -0.3, 0.3, 0.5):
                    est = H.signed_bias(R < r0, R < r0 + d, sp, roi=band) if band.any() else None
                    errs.append(None if est is None or not np.isfinite(est) else float(est - d))
                out.append(dict(radius=radius, border=border, variant=v,
                                band_vox=int(band.sum()), err=errs))
    return out


def la_heart(variants):
    lab, _ = H.phantom()
    sp = np.asarray(T.SP, float)
    out = []
    for border in ("endo", "epi"):
        base = int(band_variant(lab, sp, border, "shipped").sum())
        for v in variants:
            k = int(band_variant(lab, sp, border, v).sum())
            out.append(dict(border=border, variant=v, band_vox=k,
                            share_of_shipped=k / base if base else None))
    return out


def summarise(rows):
    s = {}
    for v in VARIANTS:
        for b in ("endo", "epi"):
            sel = [r for r in rows if r["variant"] == v and r["border"] == b]
            e = [abs(r["err"]) for r in sel if r["err"] is not None]
            s[f"{v}/{b}"] = dict(
                n=len(sel), n_empty=sum(r["err"] is None for r in sel),
                worst_abs_err=max(e) if e else None,
                pass_005=bool(e) and len(e) == len(sel) and max(e) <= TOL)
    return s


def main(out):
    guard.refuse([], what="Lima R5 E1 (phantoms; no case is opened)")
    t0 = time.time()
    res = {"harness_version": H.HARNESS_VERSION, "tolerance_mm": TOL, "band_mm": W}
    rows = india(VARIANTS)
    res["india_open_base"] = {"summary": summarise(rows), "rows": rows}
    print("india", json.dumps(res["india_open_base"]["summary"], indent=1), flush=True)
    res["validate_open_base"] = {}
    for v in VARIANTS:
        r = validate(v)
        res["validate_open_base"][v] = {k: r[k] for k in
                                        ("worst_abs_error_mm", "mean_error_mm", "passed",
                                         "bias_guard_mm", "by_border")}
        res["validate_open_base"][v]["n_rows"] = len(r["rows"])
        res["validate_open_base"][v]["n_nan"] = int(sum(not np.isfinite(x["estimate_mm"])
                                                        for x in r["rows"]))
        print("validate", v, r["worst_abs_error_mm"], r["passed"], flush=True)
    res["e4_closed_shells"] = e4(VARIANTS)
    res["la_capped_heart"] = la_heart(VARIANTS)
    res["seconds"] = round(time.time() - t0, 1)
    Path(out).write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({"e4": res["e4_closed_shells"], "la": res["la_capped_heart"]}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
