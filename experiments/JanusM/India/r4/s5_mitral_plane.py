"""India R4, S5 check: what the shipped JA46 (a) mitral-plane check catches.

Synthetic phantom only (janusm_reads.phantom); no case, no image is opened.
Question: a read whose LV pool reaches h mm into the LA, keeping a myocardium rim so
no 2-4 face is made (the shipped test's construction), on
  (seeded) the plane fitted to the seed (= truth), and
  (blank)  no seed: the plane fitted to the read's own gap,
plus: the margin an exact read already uses, and an overreach just outside the
plane's footprint.
Run: python experiments/JanusM/India/r4/s5_mitral_plane.py  -> s5_mitral_plane.json
"""
import json
import pathlib

import numpy as np
from scipy import ndimage

from janusm_reads import checker, phantom
from janusm_reads import labels as L


def geometry(truth, spacing, plane):
    centre, normal, radius, _ = plane
    pts = np.indices(truth.shape).reshape(3, -1).T * np.asarray(spacing)
    rel = pts - centre
    h = rel @ normal
    inpl = np.sqrt(np.maximum(0, (rel ** 2).sum(1) - h ** 2))
    return h.reshape(truth.shape), inpl.reshape(truth.shape)


def overreach(truth, spacing, plane, height_mm, r_lo=0.0, r_hi=None):
    h, inpl = geometry(truth, spacing, plane)
    radius = plane[2]
    r_hi = radius if r_hi is None else r_hi
    pool = truth == L.LV_POOL
    extra = (h > 0) & (h <= height_mm) & (inpl >= r_lo) & (inpl <= r_hi) & ~pool
    # only grow into what is myocardium or LA (stay inside the heart)
    extra &= np.isin(truth, (L.LV_MYO, L.LA_POOL))
    read = truth.copy()
    read[extra] = L.LV_POOL
    rim = ndimage.binary_dilation(read == L.LV_POOL) & (read == L.LA_POOL)
    read[rim] = L.LV_MYO
    return read, int(extra.sum())


def run_one(read, spacing, seed):
    errors, warnings = checker.check_conventions(read, spacing, seed=seed)
    plane = checker.mitral_plane(read, spacing, seed=seed)
    above = None if plane is None else checker.pool_above_mitral_mm(read, spacing, plane)
    return {"plane_source": None if plane is None else plane[3],
            "plane_radius_mm": None if plane is None else round(plane[2], 2),
            "pool_above_mm": None if above is None else round(above, 2),
            "face_error": any("share a face" in e for e in errors),
            "plane_error": any("above the mitral plane" in e for e in errors)}


def main():
    truth, spacing = phantom.heart(mitral_gap_mm=2.0)
    seed_plane = checker.mitral_plane(truth, spacing, seed=truth)
    out = {"phantom": "janusm_reads.phantom.heart(mitral_gap_mm=2.0), 0.5 mm",
           "limit_mm": checker.CheckConfig().max_pool_above_mitral_mm,
           "exact_read": {"seeded": run_one(truth, spacing, truth),
                          "blank": run_one(truth, spacing, None)},
           "overreach_inside_footprint": [], "overreach_outside_footprint": []}
    for hmm in (2.0, 4.0, 6.0, 10.0):
        read, n = overreach(truth, spacing, seed_plane, hmm)
        out["overreach_inside_footprint"].append(
            {"height_mm": hmm, "voxels_added": n,
             "seeded": run_one(read, spacing, truth), "blank": run_one(read, spacing, None)})
    r = seed_plane[2]
    for hmm in (6.0, 10.0):
        read, n = overreach(truth, spacing, seed_plane, hmm, r_lo=r + 0.5, r_hi=r + 6.0)
        out["overreach_outside_footprint"].append(
            {"height_mm": hmm, "ring_mm": [round(r + 0.5, 2), round(r + 6.0, 2)],
             "voxels_added": n, "seeded": run_one(read, spacing, truth),
             "blank": run_one(read, spacing, None)})
    path = pathlib.Path(__file__).with_suffix(".json")
    path.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
