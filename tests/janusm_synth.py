"""Synthetic inputs for the Janus-M S6 / S7 tests: feature records, read pairs and phantoms.

No case, no id, no file: populations come from Lima's simulator (via the S3 stub), phantoms from
``janusm.harness.phantom``.
"""

from __future__ import annotations

import numpy as np

from janusm import calibrate as C
from janusm import features as F
from janusm import geometry as G
from janusm import harness as H

MIX_ED = {"ED": 1.0, "MD": 0.0, "SYS": 0.0}


def feature_record(wall17, sub16, rng, *, fat_mm3=0.0, tpr=1.0):
    """One anonymous feature record shaped like :func:`janusm.features.case_features`'s."""
    wall = {k: float(wall17[k - 1]) for k in range(1, 18)}
    m = float(np.median(wall17[:16]))
    fat = {str(c): {t: [] for t in (*F.TERRITORIES, "none")} for c in F.FAT_CUTS}
    if fat_mm3:
        for c in F.FAT_CUTS:
            fat[str(c)]["LAD"] = [float(fat_mm3)]
    return {
        "frame": "ok", "orientation_ok": True, "aha_flagged": False,
        "wall_mm": wall, "rel_thickness": {k: wall[k] / m for k in range(1, 17)},
        "rel_subendo_hu": {k: float(sub16[k - 1]) for k in range(1, 17)},
        "rel_subepi_hu": {k: float(sub16[k - 1]) * 1.02 for k in range(1, 17)},
        "tpr": {k: float(tpr * np.exp(rng.normal(0, 0.03))) for k in range(1, 17)},
        "fat_grid": {F.fat_key(c, v): bool(fat_mm3 >= v) for c in F.FAT_CUTS for v in F.FAT_VOLS},
        "fat_hotel_any": bool(fat_mm3 > 0),
        "fat_clusters_mm3": fat,
        "fat_clusters_mm3_patient": fat,  # the patient map is the AHA map here
        "segment_territory": dict(G.AHA_STANDARD),
        "segment_territory_share": {k: 1.0 for k in range(1, 18)},
        "segment_territory_aha": dict(G.AHA_STANDARD),
    }


def population(n=400, *, seed=5, cv=0.06, shape=None, median_mm=6.0, hu_cv=0.05,
               fat_share=0.02):
    """n anonymous feature records: Lima-simulated thickness (no lesion), relative subendo HU
    around 1, and a small share of hearts with an LAD fat cluster."""
    rng = np.random.default_rng(seed)
    shape = C.LIMA_SHAPE if shape is None else np.asarray(shape, float)
    meas = C.population(n, 0.0, 0.0, cv, 0.0, MIX_ED, rng, shape=shape, median_mm=median_mm)[0]
    sub = np.exp(rng.normal(0, hu_cv, (n, 16)))
    apex = median_mm * np.exp(rng.normal(-0.2, 0.08, n))
    out = []
    for i in range(n):
        fat = 30.0 if rng.random() < fat_share else 0.0
        out.append(feature_record(np.r_[meas[i], apex[i]], sub[i], rng, fat_mm3=fat))
    return out


def reads(pop, n=40, *, seed=9, noise_mm=0.15, hu_noise=0.01):
    """Anonymous read pairs: each read is a population record plus independent read noise."""
    rng = np.random.default_rng(seed)
    out = []
    for f in pop[:n]:
        pair = {}
        for r in ("read_1", "read_2"):
            w = np.array([f["wall_mm"][k] for k in range(1, 18)]) + rng.normal(0, noise_mm, 17)
            s = np.array([f["rel_subendo_hu"][k] for k in range(1, 17)]) * \
                np.exp(rng.normal(0, hu_noise, 16))
            fat = (f["fat_clusters_mm3"]["0"]["LAD"] or [0.0])[0]
            pair[r] = feature_record(w, s, rng, fat_mm3=fat * float(np.exp(rng.normal(0, .1))))
        out.append(pair)
    return out


# --------------------------------------------------------------------------------- phantoms
SP = (0.7, 0.7, 0.7)
VESSELS = {G.LAD: 90.0, G.LCX: 330.0, G.RCA: 210.0}
HU = {0: -80.0, G.MYO: 110.0, G.LV: 420.0, G.RV: 380.0, G.LA: 400.0}


def _world(lab, aff):
    idx = np.indices(lab.shape).reshape(3, -1).T
    w = (idx @ aff[:3, :3].T + aff[:3, 3]).reshape(*lab.shape, 3)
    return w[..., 0], w[..., 1], w[..., 2]


def coronary(lab, aff, vessels=None):
    x, y, z = _world(lab, aff)
    re = H.PHANTOM_RC + H.PHANTOM_WALL
    cor = np.zeros(lab.shape, np.int16)
    for cls, ang in (VESSELS if vessels is None else vessels).items():
        cx, cy = (re + 1.5) * np.cos(np.radians(ang)), (re + 1.5) * np.sin(np.radians(ang))
        tube = (np.hypot(x - cx, y - cy) < 1.0) & (z < 0) & (z > -H.PHANTOM_CYL)
        cor[tube & ((lab == 0) | (lab == G.RV))] = cls
    return cor


def ct_of(lab):
    ct = np.zeros(lab.shape, np.float32)
    for v, hu in HU.items():
        ct[lab == v] = hu
    return ct


THINNED = (1, 7, 13)  # anterior LAD segments, contiguous on the bullseye


def heart(*, thin: float = 0.0, subendo_hu: float = None, segs=THINNED):
    """(labels, ct, affine, coronary). ``thin``: relative thinning of ``segs`` (the outer part
    of the wall becomes background); ``subendo_hu``: HU of their inner third."""
    lab, aff = H.phantom(SP)
    if thin or subendo_hu is not None:
        geo = G.analyse(lab, affine=aff)
        sel = np.isin(geo.aha.segments, segs) & (lab == G.MYO)
        if thin:
            lab = lab.copy()
            lab[sel & (geo.depth.u > 1.0 - thin)] = 0
    ct = ct_of(lab)
    if subendo_hu is not None:
        geo = G.analyse(lab, affine=aff)
        sel = np.isin(geo.aha.segments, segs) & (lab == G.MYO) & (geo.depth.u < 1 / 3)
        ct[sel] = subendo_hu
    return lab, ct, aff, coronary(lab, aff)


# ------------------------------------------------------------------- R8 (R5-S6 S12) and S9
#: Vessels centred on segment pairs (LAD over 6 and 1, RCA over 2 and 3, LCx over 4 and 5), so
#: every basal and mid segment has a clear majority on both maps.
ALIGNED = {G.LAD: 62.0, G.LCX: 302.0, G.RCA: 182.0}
#: The cavity branch: an LCx arc 0.8 mm inside the anterior endocardium (r 11.3 mm), 92 +/- 15°,
#: z -10 .. -5 mm (segment 1's middle). Nearest in a straight line for most of segment 1, but it
#: touches no epicardial myocardium within 5 mm, so the geodesic map never seeds from it.
BRANCH = {"cls": G.LCX, "r_mm": 11.3, "angle": 92.0, "half_deg": 15.0, "z_mm": (-10.0, -5.0)}


def heart_r8(*, branch: bool = True, fat_mm: float = 0.0):
    """(labels, ct, affine, coronary) for R8: the normal phantom with :data:`ALIGNED` vessels
    and, with ``branch``, :data:`BRANCH` in the cavity. The real Euclidean majority of segment
    1 is then LCx (share ~0.8) while the geodesic one stays LAD; no other segment differs.
    ``fat_mm``: radius of a -60 HU ball in segment 1's mid-wall core (92°, r 16 mm, z -7 mm)."""
    lab, aff = H.phantom(SP)
    cor = coronary(lab, aff, ALIGNED)
    x, y, z = _world(lab, aff)
    r, ph = np.hypot(x, y), np.degrees(np.arctan2(y, x)) % 360
    if branch:
        b = BRANCH
        sel = ((np.abs(r - b["r_mm"]) < 0.5) & (np.abs(ph - b["angle"]) < b["half_deg"])
               & (z > b["z_mm"][0]) & (z < b["z_mm"][1]) & (lab == G.LV))
        cor[sel] = b["cls"]
    ct = ct_of(lab)
    if fat_mm:
        cx, cy = 16.0 * np.cos(np.radians(92.0)), 16.0 * np.sin(np.radians(92.0))
        ct[(np.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z + 7.0) ** 2) <= fat_mm)
           & (lab == G.MYO)] = -60.0
    return lab, ct, aff, cor
