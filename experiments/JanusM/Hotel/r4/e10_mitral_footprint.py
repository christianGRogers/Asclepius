"""E10 (Round 4, #205 items 1 and 5): the JA46 (a) mitral-plane check on the queue's synthetic phantom.

Synthetic only (``janusm_reads.phantom.heart``): no case is opened. ``janusm.guard.refuse([])`` is
called first by rule; it names nothing.

A: LV-pool voxels 4-8 mm above the fitted plane, just outside the fit's footprint (radius of the fitted
points), under the LA. B: a 5 mm intrusion inside the footprint, on a seeded read (plane from the seed)
and on a blank read (plane refitted to the read itself).

    python experiments/JanusM/Hotel/r4/e10_mitral_footprint.py OUT_JSON
"""
import json
import sys

import numpy as np
from scipy import ndimage

from janusm.guard import refuse
from janusm_reads import checker, phantom
from janusm_reads import labels as L

refuse([], what="E10 (synthetic phantom; no case)")
truth, sp = phantom.heart(mitral_gap_mm=2.0)
centre, normal, radius, src = checker.mitral_plane(truth, sp, seed=truth)
pts = np.indices(truth.shape).reshape(3, -1).T * np.asarray(sp)
rel = pts - centre
h = (rel @ normal).reshape(truth.shape)
ip = np.sqrt(np.maximum(0, (rel ** 2).sum(1) - (rel @ normal) ** 2)).reshape(truth.shape)
pool = truth == L.LV_POOL
rows = []


def probe(mask, name, seed):
    read = truth.copy()
    read[mask] = L.LV_POOL
    rim = ndimage.binary_dilation(read == L.LV_POOL) & (read == L.LA_POOL)
    read[rim] = L.LV_MYO
    errors, _ = checker.check_conventions(read, sp, seed=seed)
    pl = checker.mitral_plane(read, sp, seed=seed)
    rows.append({"probe": name, "voxels_added": int(mask.sum()),
                 "reported_above_mm": round(checker.pool_above_mitral_mm(read, sp, pl), 2),
                 "true_max_above_mm": round(float(h[read == L.LV_POOL].max()), 2),
                 "mitral_error": any("mitral" in e for e in errors)})
    print(rows[-1])


cand = (h > 4) & (h <= 8) & (ip > radius) & (ip <= radius + 4) & (truth != L.LA_POOL)
probe(cand, "A outside footprint, seeded", truth)
probe(cand, "A outside footprint, blank", None)
inside = (h > 0) & (h <= 5) & (ip <= radius) & ~pool
probe(inside, "B inside footprint, seeded", truth)
probe(inside, "B inside footprint, blank (read-fitted)", None)
doc = {"spacing": list(map(float, sp)), "fit_radius_mm": round(radius, 2), "plane_source": src,
       "la_inplane_max_mm": round(float(ip[truth == L.LA_POOL].max()), 2), "rows": rows}
open(sys.argv[1], "w").write(json.dumps(doc, indent=1) + "\n")
