"""Per-case quantities for the Janus-M reference population (S6) and table writer (S7).

One implementation of every per-case number that ``janusm.reference`` pools and ``janusm.report``
prints, so the population and the page can never measure a case differently (JA48). Geometry
(depth, layers, AHA 17, territories) comes from :mod:`janusm.geometry` only. The HU quantities
follow JM-0R (``experiments/JanusM/fir/jm0r_readout.py``) definition for definition, at a fixed
core guard ``guard_mm`` that the reference config records and the report reuses:

* guarded subendocardial HU: mean HU of segment voxels with u < 1/3 and >= ``guard_mm`` from the
  endocardium (>= 30 voxels), divided by the patient's median over segments 1-16;
* core: myocardium >= ``guard_mm`` from both borders;
* fat (JA18): 26-connected core clusters within -180 HU .. c; the (c, V) grid; Hotel's
  noise-aware patient rule;
* rest TPR (JA17): inner-third / outer-third mean HU per segment at ``guard_mm``.

Added for the table: the subepicardial HU (for the endocardial-predominance construct check),
fat cluster volume per territory, and territory masses at 1.05 g/ml.

Round 4 (``jm/rest-ccta`` JA63, JA43 R8, JA69 (a)):

* fat clusters per **patient-map** territory as well as per AHA-default territory
  (``fat_clusters_mm3_patient``; fat's D uses them, rule C's fat flag stays on the AHA map);
* the **geodesic** segment majority beside the Euclidean one (``segment_territory_geodesic``),
  for R8's "shared";
* the **arc-proportional** septal values (``septal_arc``): wall and relative subendocardial HU of
  segments 2, 3, 8 and 9 on :func:`janusm.geometry.arc_segments`'s sectors, None below JM-0R's
  0.995 frame-agreement guard.

No file access, no case id: arrays in, numbers out. Callers run the JA12 guard first.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
from scipy import ndimage as ndi

from janusm import geometry as G

FEATURES_VERSION = "1.1.0"
TERRITORIES = ("LAD", "LCx", "RCA")
SEGMENTS16 = tuple(range(1, 17))
ARC_SEPTAL = G.ARC_SEPTAL            # JA69 (a): segments 2, 3, 8, 9
MYO_DENSITY_G_PER_ML = 1.05
MIN_VOX = 30                          # JM-0R TPR_MIN_VOX
FAT_WINDOW = (-180.0, 0.0)            # JA18
FAT_CUTS = (0, -30, -50, -100)        # JA18 c, HU (least strict first)
FAT_VOLS = (5, 20, 50)                # JA18 V, mm3 (least strict first)
HOTEL_K, HOTEL_MIN_VOX = 3.5, 3       # Hotel v2 §5.6
DEFAULT_GUARD_MM = 1.0
SHARED_BELOW = 0.6                    # JA19: "shared" if the majority share is < 0.6
_STD = {k: v for k, v in G.AHA_STANDARD.items()}


def _r(x, nd=4):
    return None if x is None else round(float(x), nd)


def fat_key(c, v) -> str:
    return f"{int(c)}_{int(v)}"


def _clusters(mask, structure):
    lab, n = ndi.label(mask, structure=structure)
    return lab, n


def fat_cluster_volumes(ct, core, segments, vox_mm3, c, seg_territory=None):
    """26-connected core clusters within -180 HU .. ``c``. Returns (per territory, the volume
    (mm3) of every cluster whose majority of voxels lies in it, clusters on segment 0 under
    ``"none"``; per V in :data:`FAT_VOLS`, the fat volume (mm3) per segment 1-17 that belongs to
    clusters >= V). Territories are the AHA default map's, or ``seg_territory``'s ({segment:
    territory}, the patient map; a segment it lacks counts as ``"none"``)."""
    lab, n = _clusters(core & (ct >= FAT_WINDOW[0]) & (ct < c), np.ones((3, 3, 3)))
    out: Dict[str, list] = {t: [] for t in (*TERRITORIES, "none")}
    per_seg = {str(v): {} for v in FAT_VOLS}
    if not n:
        return out, per_seg
    sizes = np.bincount(lab.ravel())[1:]
    big_mm3 = np.r_[0.0, sizes * vox_mm3]
    for v in FAT_VOLS:
        m = big_mm3[lab] >= v
        cnt = np.bincount(np.clip(segments[m], 0, 17), minlength=18)
        per_seg[str(v)] = {k: round(float(cnt[k] * vox_mm3), 3) for k in range(1, 18) if cnt[k]}
    # majority segment of each cluster -> its AHA-default territory
    terr_code = np.zeros(18, np.int64)
    for k, t in (_STD if seg_territory is None else seg_territory).items():
        if t in TERRITORIES and 1 <= int(k) <= 17:
            terr_code[int(k)] = 1 + TERRITORIES.index(t)
    tl = terr_code[np.clip(segments, 0, 17)]
    sel = lab > 0
    counts = np.zeros((n + 1, 4), np.int64)
    np.add.at(counts, (lab[sel], tl[sel]), 1)
    for i in range(1, n + 1):
        j = int(np.argmax(counts[i]))
        out[TERRITORIES[j - 1] if j else "none"].append(round(float(sizes[i - 1] * vox_mm3), 3))
    return {k: sorted(v, reverse=True) for k, v in out.items()}, per_seg


def hotel_fat(ct, core):
    """Hotel v2 §5.6 patient rule: (any cluster, cut HU), as JM-0R computes it."""
    v = ct[core]
    if v.size < 50:
        return None, None
    med = float(np.median(v))
    sd = 1.4826 * float(np.median(np.abs(v - med)))
    cut = min(FAT_WINDOW[1], med - HOTEL_K * sd)
    lab, n = ndi.label(core & (ct >= FAT_WINDOW[0]) & (ct < cut))
    return bool(n and (np.bincount(lab.ravel())[1:] >= HOTEL_MIN_VOX).any()), cut


def _mid_wall_mm(dep, sel) -> Optional[float]:
    """A region's wall as :func:`janusm.geometry.layers` measures it: the median thickness of its
    mid-wall voxels (|u - 1/2| < 1/6), else of all its voxels."""
    if not sel.any():
        return None
    mid = sel & (np.abs(dep.u - 0.5) < 1 / 6)
    return float(np.median(dep.thickness[mid] if mid.any() else dep.thickness[sel]))


def septal_arc_values(labels, ct, affine, geo, sub_median: Optional[float], *,
                      guard_mm: float = DEFAULT_GUARD_MM, arc_deg: Optional[float] = None) -> dict:
    """JA69 (a): the wall (mm) and relative subendocardial HU (the case's fixed-sector median as
    the divisor) of segments 2, 3, 8 and 9 on the arc-proportional sectors. Values are None when
    the recomputed frame agrees with JA3's on < 0.995 of the ring voxels (JM-0R's guard).
    ``arc_deg`` overrides the measured arc (tests)."""
    seg, agree = G.arc_segments(labels, affine, geo.aha, arc_deg=arc_deg)
    out = {"agreement": _r(agree), "wall_mm": {k: None for k in G.ARC_SEPTAL},
           "rel_subendo_hu": {k: None for k in G.ARC_SEPTAL}}
    if seg is None or agree is None or agree < G.ARC_AGREEMENT_MIN:
        out["note"] = "frame agreement below 0.995: not computed"
        return out
    dep = geo.depth
    myo = np.asarray(labels) == G.MYO
    for k in G.ARC_SEPTAL:
        s = myo & (seg == k)
        out["wall_mm"][k] = _r(_mid_wall_mm(dep, s))
        a = s & (dep.u < 1 / 3) & (dep.d_endo >= guard_mm)
        if sub_median and a.sum() >= MIN_VOX:
            out["rel_subendo_hu"][k] = _r(float(ct[a].mean()) / sub_median)
    return out


def case_features(labels, ct, affine, coronary=None, *, guard_mm: float = DEFAULT_GUARD_MM,
                  depth_method: str = "equal_thickness") -> dict:
    """Every per-case number the reference population and the table use. JSON-ready.

    ``labels``: JA1 map; ``ct``: HU on the same grid; ``coronary``: D25 classes or None (no
    patient-specific territory then)."""
    aff = np.asarray(affine, float)
    sp = np.linalg.norm(aff[:3, :3], axis=0)
    vox_ml = float(np.prod(sp)) / 1000.0
    labels = np.asarray(labels).astype(np.int16)
    ct = np.asarray(ct, np.float32)
    has_cor = coronary is not None and np.isin(coronary, (G.LAD, G.LCX, G.RCA)).any()
    geo = G.analyse(labels, affine=aff, coronary=coronary if has_cor else None,
                    depth_method=depth_method)
    dep, aha = geo.depth, geo.aha
    myo = labels == G.MYO
    f: dict = {
        "features_version": FEATURES_VERSION, "geometry_version": G.GEOMETRY_VERSION,
        "guard_mm": float(guard_mm), "spacing_mm": [_r(x, 3) for x in sp],
        "aha_flagged": bool(aha.flagged), "aha_flags": [x.split(":")[0] for x in aha.flags],
        "orientation_ok": bool(aha.orientation.get("ok", False)) if aha.orientation else False,
        "septal_arc_deg": _r(aha.septal_arc_deg, 1),
    }
    regs = geo.layers.regions
    f["wall_mm"] = {k: _r(regs[k]["wall_mm"]) for k in range(1, 18) if k in regs}
    f["layer_scheme"] = {k: regs[k]["scheme"] for k in range(1, 18) if k in regs}
    seg = aha.segments
    if seg is None:
        f["frame"] = "aha_failed"
        return f
    f["frame"] = "ok"
    w16 = [f["wall_mm"][k] for k in SEGMENTS16 if k in f["wall_mm"]]
    if w16:
        m = float(np.median(w16))
        f["median_wall_mm"] = _r(m)
        f["rel_thickness"] = {k: _r(f["wall_mm"][k] / m) for k in SEGMENTS16
                              if k in f["wall_mm"]}

    sub, epi = {}, {}
    ms = None
    for k in SEGMENTS16:
        s = myo & (seg == k)
        a = s & (dep.u < 1 / 3) & (dep.d_endo >= guard_mm)
        b = s & (dep.u >= 2 / 3) & (dep.d_epi >= guard_mm)
        if a.sum() >= MIN_VOX:
            sub[k] = float(ct[a].mean())
        if b.sum() >= MIN_VOX:
            epi[k] = float(ct[b].mean())
    if sub:
        ms = float(np.median(list(sub.values())))
        if ms:
            f["rel_subendo_hu"] = {k: _r(x / ms) for k, x in sub.items()}
            f["rel_subepi_hu"] = {k: _r(x / ms) for k, x in epi.items()}
    f["tpr"] = {k: _r(sub[k] / epi[k]) for k in sub if k in epi and epi[k] > 20}
    f["septal_arc"] = septal_arc_values(labels, ct, aff, geo, ms or None, guard_mm=guard_mm)

    core = myo & (dep.d_endo >= guard_mm) & (dep.d_epi >= guard_mm)
    vox_mm3 = vox_ml * 1000.0
    fat, fat_seg = {}, {}
    for c in FAT_CUTS:
        fat[str(c)], fat_seg[str(c)] = fat_cluster_volumes(ct, core, seg, vox_mm3, c)
    f["fat_clusters_mm3"] = fat
    f["fat_segment_mm3"] = fat_seg
    te = geo.territories
    if te is not None:
        pmap = {k: v["territory"] for k, v in te.segments.items()}
        f["fat_clusters_mm3_patient"] = {
            str(c): fat_cluster_volumes(ct, core, seg, vox_mm3, c, pmap)[0] for c in FAT_CUTS}
    f["fat_grid"] = {fat_key(c, v): any(x >= v for t in fat[str(c)].values() for x in t)
                     for c in FAT_CUTS for v in FAT_VOLS}
    f["fat_hotel_any"], cut = hotel_fat(ct, core)
    f["fat_hotel_cut_hu"] = _r(cut, 1)

    f["segment_territory_aha"] = {k: _STD[k] for k in range(1, 18)}
    f["mass_g_aha"] = {t: _r(sum(int((myo & (seg == k)).sum()) for k in range(1, 18)
                                 if _STD[k] == t) * vox_ml * MYO_DENSITY_G_PER_ML, 2)
                       for t in TERRITORIES}
    if te is not None:
        f["segment_territory"] = {k: v["territory"] for k, v in te.segments.items()}
        f["segment_territory_share"] = {k: v["majority_share"] for k, v in te.segments.items()}
        lab_t = te.label[myo]
        f["mass_g"] = {G.TERRITORY_NAMES[c]: _r((lab_t == c).sum() * vox_ml
                                                * MYO_DENSITY_G_PER_ML, 2)
                       for c in (G.LAD, G.LCX, G.RCA)}
        f["mass_share"] = dict(te.share)
        geo_t = G.territories(labels, coronary, affine=aff, segments=seg, method="geodesic")
        f["segment_territory_geodesic"] = {k: v["territory"] for k, v in geo_t.segments.items()}
    f["halves_segments"] = sorted(k for k, s in f["layer_scheme"].items() if s == "halves")
    return f


def territory_segments(feat: dict, source: str = "patient") -> Dict[str, list]:
    """{territory: [segments 1-16]} on the patient-specific map (``"patient"``), falling back to
    nothing, or the AHA default map (``"aha"``)."""
    key = "segment_territory" if source == "patient" else "segment_territory_aha"
    m = feat.get(key) or {}
    return {t: sorted(int(k) for k, v in m.items() if v == t and int(k) <= 16)
            for t in TERRITORIES}


def vector16(d: Optional[dict]) -> Optional[np.ndarray]:
    """A {segment: value} dict as a 16-vector, or None if any of 1-16 is missing."""
    if not d:
        return None
    try:
        return np.array([float(d[k] if k in d else d[str(k)]) for k in SEGMENTS16])
    except (KeyError, TypeError, ValueError):
        return None
