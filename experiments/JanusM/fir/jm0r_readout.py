"""Job JM-0R (Janus-M Round 2, path jm/rest-ccta, JA23; issue #169): one guarded CPU read-out.

It replaces the three Round 2 add-ons (Hotel v2 §7 ``Hotel/r2/fir/halfmax_tpr_m0.py``, Lima
``Lima/fir/jm0b_readout.py``, India ``India/fir/jm0_addon.py``). Ruling:
``vault/JanusM/Judgements/Round 2 - rest-ccta.md``, JA23 (and JA15-JA20 for what is measured).

Inputs are Job JM-0's (Juliet v1 §7): the 40 ImageCAS-X *training* cases in ``m0_cases.txt``, their
``heartchambers_highres`` masks, their CT (``layout.json``) and their ImageCAS-X reference coronary
labels (collapsed to D25's four classes by ``trillium/icx4/lib/territory.py``).

Guard, before any image, mask, label or layout file is opened (fail closed: any error stops the
run):

1. the case list must equal the frozen JM-0 list, ``configs/janusm/sealed-r1.json`` key ``jm0``
   (read and hash-checked by ``janusm.sealed_r1``): same cases, no duplicates;
2. ``janusm.guard.refuse(cases, source="ImageCAS-X", purpose="any")``. JA23 writes
   ``purpose=JM-0``; the guard's ``any`` is that purpose: it refuses every coronary hold-out, the
   A14 sealed 100, the ImageCAS-X test split and val 80, and every Janus-M seal, extension and
   decision case, and allows only what is left, which includes the JM-0 list. ``seal_scoring`` and
   ``decision_scoring`` would each let one Janus-M list through, so they are never used here;
3. the ``splits.json`` on Fir must hash to the guard's pinned sha256, which is also the one
   ``sealed-r1.json`` records (JA6).

What it computes, one implementation per quantity (``janusm.geometry`` wherever it has one), on the
native grid:

* **Hotel:** half-maximum offsets of the endocardium and the free-wall epicardium; their 10-90 %
  edge widths; the blood, core-myocardium and fat plateaus; the pooled core-HU histogram; rest TPR
  per segment with guard bands of 0 mm, 1 mm and the JA17 adaptive band max(1 mm, endocardial
  FWHM), FWHM = 10-90 % width / 1.09.
* **Lima:** voxels per third and halves (JA2), AHA failures (JA3), wall thickness, the E3
  calibration inputs (``cv_n`` and segment shape: thickness relative to the patient's median),
  arc-proportional septal sectors, Euclidean vs geodesic territories (JA4), and the fat (c, V) grid
  (JA18) with Hotel's patient noise-aware cut as one more candidate.
* **India:** equal-thickness vs Laplace thirds agreement, the septal arc, and territory
  discordance with the AHA default map.

Sign conventions (mm). Each border has an axis s pointing into the labelled myocardium (endo:
negative in the LV pool; epi: negative in the fat), with the label's border at s = 0. A half-maximum
crossing at s = +x means the image edge lies x mm inside the labelled wall, i.e. the label puts the
border x mm too far toward the blood (endo) or the fat (epi). JA17's ±0.25 mm is symmetric.

Output (JA23: aggregates only): ``OUT/summary.json``, which is also the only thing printed on
stdout, holds quantiles, counts, shares and one pooled histogram: no case id, no per-case value, no
image, no path. ``OUT/cases.jsonl`` holds the per-case rows and **stays on Fir**. Progress lines
on stderr carry a counter only.

Commands for the lead (Fir, account def-aso22; after Job JM-0 has finished; CPU only, 0 GPU-h).
Nobody but the lead runs this on Fir::

    module load StdEnv/2023 python/3.11.5
    cd $SCRATCH/asclepius/repo && git fetch origin jm/rest-ccta && git checkout jm/rest-ccta \\
        && git pull --ff-only
    sbatch --account=def-aso22 --job-name=jm0r --cpus-per-task=8 --mem=48G --time=02:00:00 \\
        --output=$SCRATCH/janusm/jm0r-%j.log --wrap "source $HOME/icx4-tseg-venv/bin/activate && \\
        python experiments/JanusM/fir/jm0r_readout.py --cases $SCRATCH/janusm/m0_cases.txt \\
        --hc $SCRATCH/janusm/hc --layout $SCRATCH/icx4/layout.json --icx $SCRATCH/icx4/icx \\
        --splits $SCRATCH/icx4/splits.json --out $SCRATCH/janusm/jm0r --np 8"

    # when it ends: the guard line, then the aggregate JSON
    grep -m1 '^guard:' $SCRATCH/janusm/jm0r-*.log
    cat $SCRATCH/janusm/jm0r/summary.json

* The venv needs numpy, scipy and nibabel; ``totalsegmentator`` is optional (without it the
  published ``heartchambers_highres`` label order is used; check ``hc_label_ids`` in the summary).
* The first stderr line is ``guard: 40 cases ... 0 refused``. If it prints ``REFUSED`` instead, stop
  and send only that line back: nothing was opened.
* Send back on #142: ``summary.json`` only. ``cases.jsonl`` and the log stay on Fir.
* If memory runs out, re-run with ``--np 4 --mem=48G``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
for _p in (REPO / "src", REPO / "trillium/icx4/lib"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from janusm import geometry as G  # noqa: E402

SCRIPT_VERSION = "1"
ICX_SOURCE = "ImageCAS-X"
HC_FALLBACK = {1: "heart_myocardium", 2: "heart_atrium_left", 3: "heart_ventricle_left",
               4: "heart_atrium_right", 5: "heart_ventricle_right", 6: "aorta",
               7: "pulmonary_artery"}
SEPTAL = (2, 3, 8, 9, 14)
CROP_MM = 20.0                        # crop margin around the LV; vessel seeds come from this crop
PROFILE_BINS = np.arange(-4.0, 6.01, 0.25)
PROFILE_MIN_VOX = 50
HIST_EDGES = np.arange(-200, 301, 10)
TPR_MIN_VOX = 30
EDGE_TO_FWHM = 1.09                   # 10-90 % width / FWHM for a Gaussian edge (JA17)
EDGE_MAX_MM = 2.0                     # JA17: rest TPR is not computed above this edge
FAT_WINDOW = (-180.0, 0.0)            # JA18: Xu 2022's window
FAT_CUTS = (0, -30, -50, -100)        # JA18 c, HU
FAT_VOLS = (5, 20, 50)                # JA18 V, mm3
HOTEL_K, HOTEL_MIN_VOX = 3.5, 3       # Hotel v2 §5.6: median - 3.5 robust SD, 6-connected >= 3
CORE_SAMPLE = 20000                   # core HU kept per case for pooled quantiles (never written)


class Refused(RuntimeError):
    """The JM-0R guard refused the run. Nothing was opened."""


# --------------------------------------------------------------------------------------- guard
def guard_cases(cases_path, splits_path) -> list:
    """The JA23 guard. Returns the case list; raises :class:`Refused` on anything else.

    Reads only the case-list file, repository configs and the splits file: never an image."""
    try:
        guard = importlib.import_module("janusm.guard")
        sealed_r1 = importlib.import_module("janusm.sealed_r1")
    except Exception as e:  # noqa: BLE001 -- fail closed on any import problem
        raise Refused(f"janusm.guard unavailable ({type(e).__name__}); refusing") from e
    try:
        names = Path(cases_path).read_text().split()
        frozen = sealed_r1.load()
        if len(names) != len(set(names)):
            raise Refused(f"{len(names) - len(set(names))} duplicate case(s) in the case list")
        if set(names) != set(frozen.jm0):
            raise Refused(
                f"the case list is not the frozen JM-0 list ({sealed_r1.PATH} key jm0): "
                f"{len(set(names) - frozen.jm0)} extra, {len(frozen.jm0 - set(names))} missing")
        guard.refuse(names, what="JM-0R read-out (JA23)", source=ICX_SOURCE, purpose=guard.ANY)
        pinned = guard.PINNED[guard.SPLITS_RELPATH]
        recorded = json.loads((REPO / sealed_r1.PATH).read_text()).get("splits_sha256")
        if recorded != pinned:
            raise Refused(f"{sealed_r1.PATH} records a splits.json hash that is not the pinned one")
        got = hashlib.sha256(Path(splits_path).read_bytes()).hexdigest()
        if got != pinned:
            raise Refused(f"splits.json sha256 {got[:12]} is not the pinned {pinned[:12]} (JA6)")
    except Refused:
        raise
    except Exception as e:  # noqa: BLE001 -- HeldOutError, GuardInputError, I/O: all refuse
        first = str(e).splitlines()[0] if str(e) else ""
        raise Refused(f"{type(e).__name__}: {first}") from e
    return names


def provenance() -> dict:
    from janusm import guard, sealed_r1

    return {"script": "experiments/JanusM/fir/jm0r_readout.py", "script_version": SCRIPT_VERSION,
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "guard_version": guard.GUARD_VERSION, "guard_purpose": guard.ANY,
            "geometry_version": G.GEOMETRY_VERSION,
            "sealed_r1_sha256": sealed_r1.SEALED_R1_SHA256,
            "splits_sha256": guard.PINNED[guard.SPLITS_RELPATH]}


# --------------------------------------------------------------------------------------- loading
def hc_ids() -> dict:
    try:
        from totalsegmentator.map_to_binary import class_map

        return {v: k for k, v in class_map["heartchambers_highres"].items()}
    except Exception:  # noqa: BLE001
        return {v: k for k, v in HC_FALLBACK.items()}


def _largest(m):
    lab, n = ndi.label(m)
    if n <= 1:
        return m
    return lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)


def to_ja1(hc, ids):
    """``heartchambers_highres`` -> JA1 labels (1 myo, 2 LV, 3 RV, 4 LA), plus aorta and other."""
    myo = _largest(hc == ids["heart_myocardium"])
    lv = _largest(hc == ids["heart_ventricle_left"])
    lab = np.zeros(hc.shape, np.int16)
    lab[hc == ids["heart_atrium_left"]] = G.LA
    lab[hc == ids["heart_ventricle_right"]] = G.RV
    lab[myo] = G.MYO
    lab[lv] = G.LV
    aorta = hc == ids["aorta"]
    other = np.isin(hc, [ids[k] for k in ("heart_atrium_right", "pulmonary_artery") if k in ids])
    return lab, aorta, other


def crop(arrays, mask, affine, margin_mm=CROP_MM):
    aff = np.asarray(affine, float)
    sp = np.linalg.norm(aff[:3, :3], axis=0)
    idx = np.argwhere(mask)
    mg = np.ceil(margin_mm / sp).astype(int)
    lo = np.maximum(idx.min(0) - mg, 0)
    hi = np.minimum(idx.max(0) + mg + 1, mask.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    caff = aff.copy()
    caff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    return [None if a is None else a[sl] for a in arrays], caff


def icx_label_name(case: str) -> str:
    """ImageCAS-X c0002 is ImageCAS release id 3."""
    return f"{int(case[1:]) + 1}.coronary.nii.gz"


def load_case(case, hc_dir, ct_path, icx_dir, ids):
    """Open one case's mask, CT and coronary label. Only ever called after :func:`guard_cases`."""
    import nibabel as nib
    from territory import to_four

    hi = nib.as_closest_canonical(nib.load(str(Path(hc_dir) / f"{case}.nii.gz")))
    ci = nib.as_closest_canonical(nib.load(str(ct_path)))
    li = nib.as_closest_canonical(nib.load(str(Path(icx_dir) / icx_label_name(case))))
    for other in (ci, li):
        if other.shape != hi.shape or not np.allclose(other.affine, hi.affine, atol=1e-3):
            raise ValueError("grid mismatch")
    lab, aorta, other = to_ja1(np.asarray(hi.dataobj).astype(np.int16), ids)
    sp = np.asarray(hi.header.get_zooms()[:3], float)
    cor = to_four(np.asarray(li.dataobj).astype(np.int64), sp).astype(np.int16)
    ct = np.asarray(ci.dataobj, dtype=np.float32)
    (lab, ct, cor, aorta, other), aff = crop([lab, ct, cor, aorta, other],
                                             np.isin(lab, (G.MYO, G.LV)), hi.affine)
    return lab, ct, aff, cor, aorta, other


# --------------------------------------------------------------------------------------- Hotel
def _profile(ct, sd):
    """Median HU per signed-distance bin (None where too few voxels)."""
    ok = np.isfinite(sd)
    v, s = ct[ok], sd[ok]
    k = np.digitize(s, PROFILE_BINS) - 1
    out = []
    for i in range(len(PROFILE_BINS) - 1):
        sel = v[k == i]
        out.append(float(np.median(sel)) if sel.size >= PROFILE_MIN_VOX else None)
    return out


def _crossing(prof, lo, hi, frac, near=0.0):
    """Where the profile crosses lo + frac * (hi - lo), nearest ``near`` (linear interpolation)."""
    level = lo + frac * (hi - lo)
    c = (PROFILE_BINS[:-1] + PROFILE_BINS[1:]) / 2
    v = np.array([np.nan if x is None else x for x in prof])
    ok = np.isfinite(v)
    c, v = c[ok], v[ok]
    hits = []
    for i in range(len(v) - 1):
        if (v[i] - level) * (v[i + 1] - level) <= 0 and v[i] != v[i + 1]:
            hits.append(float(c[i] + (level - v[i]) * (c[i + 1] - c[i]) / (v[i + 1] - v[i])))
    return min(hits, key=lambda x: abs(x - near)) if hits else None


def _edge(prof, outside, inside):
    """(half-maximum crossing, 10-90 % width) of a border between two plateaus."""
    if outside is None or inside is None or abs(inside - outside) < 30:
        return None, None
    half = _crossing(prof, outside, inside, 0.5)
    if half is None:
        return None, None
    c10 = _crossing(prof, outside, inside, 0.1, near=half)
    c90 = _crossing(prof, outside, inside, 0.9, near=half)
    return half, (None if c10 is None or c90 is None else abs(c90 - c10))


def _med(x, n=PROFILE_MIN_VOX):
    return float(np.median(x)) if x.size >= n else None


def tpr_segments(ct, myo, dep, seg, guard_mm):
    """Rest TPR per segment 1-16: mean HU of the inner third / the outer third (equal-thickness
    u), keeping voxels at least ``guard_mm`` from their border."""
    out = {}
    for k in range(1, 17):
        s = myo & (seg == k)
        inner = s & (dep.u < 1 / 3) & (dep.d_endo >= guard_mm)
        outer = s & (dep.u >= 2 / 3) & (dep.d_epi >= guard_mm)
        if inner.sum() >= TPR_MIN_VOX and outer.sum() >= TPR_MIN_VOX:
            o = float(ct[outer].mean())
            if o > 20:
                out[k] = float(ct[inner].mean()) / o
    return out


# --------------------------------------------------------------------------------------- sectors
def _theta(labels, aff, aha):
    """The JA3 angle of every myocardial voxel (0 at the anterior insertion, + into the septum),
    recomputed exactly as ``janusm.geometry.aha17`` does with its defaults."""
    myo, lv, rv, la = (labels == c for c in (G.MYO, G.LV, G.RV, G.LA))
    face = ndi.generate_binary_structure(3, 1)
    world = lambda ijk: ijk @ aff[:3, :3].T + aff[:3, 3]  # noqa: E731
    base = world(np.argwhere(lv & ndi.binary_dilation(la, face))).mean(0)
    pidx = np.argwhere(myo)
    p = world(pidx)
    dist = np.linalg.norm(p - base, axis=1)
    apex = p[dist >= dist.max() - 3.0].mean(0)
    axis = (apex - base) / np.linalg.norm(apex - base)
    s = (p - base) @ axis
    cav = float(((world(np.argwhere(lv)) - base) @ axis).max())
    helper = np.eye(3)[int(np.argmin(np.abs(axis)))]
    e1 = helper - (helper @ axis) * axis
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    rel = p - base
    ang = np.degrees(np.arctan2(rel @ e2, rel @ e1)) % 360.0
    contact = ndi.binary_dilation(rv, face)[myo] & (s >= 0) & (s <= 2 / 3 * cav)
    h = np.sort(ang[contact])
    gaps = np.diff(np.concatenate([h, h[:1] + 360.0]))
    g = int(np.argmax(gaps))
    start, end = float(h[(g + 1) % len(h)]), float(h[g])

    def direction(deg):
        r = np.radians(deg)
        return np.cos(r) * e1 + np.sin(r) * e2

    ant = np.array([0.0, 1.0, 1.0]) / np.sqrt(2)
    ref, sign = (start, 1.0) if direction(start) @ ant >= direction(end) @ ant else (end, -1.0)
    return pidx, (sign * (ang - ref)) % 360.0


def arc_segments(labels, aff, aha):
    """Septal sectors proportional to the measured septal arc in the basal and mid rings (JA20:
    the two septal segments of each ring); the apical ring and 17 stay as JA3 cuts them. Returns
    (segments, agreement of the recomputed fixed sectors with JA3's), or (None, None)."""
    pidx, theta = _theta(labels, aff, aha)
    fixed = aha.segments[tuple(pidx.T)]
    six = np.array([2, 3, 4, 5, 6, 1])
    ring = np.isin(fixed, (1, 2, 3, 4, 5, 6)) | np.isin(fixed, (7, 8, 9, 10, 11, 12))
    if not ring.any():
        return None, None
    recomputed = six[(theta // 60).astype(int) % 6] + np.where(fixed > 6, 6, 0)
    agree = float(np.mean(recomputed[ring] == fixed[ring]))
    arc = float(np.clip(aha.septal_arc_deg, 60.0, 240.0))
    rest = (360.0 - arc) / 4
    edges = [arc / 2, arc, arc + rest, arc + 2 * rest, arc + 3 * rest]
    k = np.searchsorted(edges, theta, side="right")
    new = six[np.clip(k, 0, 5)] + np.where(fixed > 6, 6, 0)
    seg = aha.segments.copy()
    seg[tuple(pidx[ring].T)] = new[ring]
    return seg, agree


_STD_CODE = np.zeros(18, np.uint8)
for _k, _v in G.AHA_STANDARD.items():
    _STD_CODE[_k] = {"LAD": 1, "LCx": 2, "RCA": 3}[_v]


def _std_terr(seg):
    """The AHA default territory (coded 1-3) of each segment label."""
    return _STD_CODE[np.clip(seg, 0, 17)]


# --------------------------------------------------------------------------------------- fat
def fat_grid(ct, core, vox_mm3):
    """JA18 (c, V) grid: does any 26-connected cluster of core voxels in -180 HU..c reach V mm3?"""
    out = {}
    lo = FAT_WINDOW[0]
    for c in FAT_CUTS:
        lab, n = ndi.label(core & (ct >= lo) & (ct < c), structure=np.ones((3, 3, 3)))
        sizes = np.bincount(lab.ravel())[1:] * vox_mm3 if n else np.zeros(0)
        for v in FAT_VOLS:
            out[f"{c}_{v}"] = bool((sizes >= v).any())
    return out


def hotel_fat(ct, core):
    """Hotel v2 §5.6: core voxels below min(0, median - 3.5 x robust SD) and >= -180 HU, in a
    6-connected cluster of >= 3 voxels. Returns (any cluster, the cut in HU)."""
    v = ct[core]
    if v.size < PROFILE_MIN_VOX:
        return None, None
    med = float(np.median(v))
    sd = 1.4826 * float(np.median(np.abs(v - med)))
    cut = min(FAT_WINDOW[1], med - HOTEL_K * sd)
    lab, n = ndi.label(core & (ct >= FAT_WINDOW[0]) & (ct < cut))
    any_ = bool(n and (np.bincount(lab.ravel())[1:] >= HOTEL_MIN_VOX).any())
    return any_, cut


# --------------------------------------------------------------------------------------- one case
def measure(labels, ct, affine, cor=None, aorta=None, other=None, seed=0) -> dict:
    """Every JM-0R quantity for one case on its native grid. Numbers only; no id, no path.

    ``labels`` is a JA1 map, ``ct`` HU on the same grid, ``cor`` D25 coronary classes or None;
    ``aorta`` and ``other`` (RA, pulmonary artery) are excluded from the free-wall epicardium."""
    aff = np.asarray(affine, float)
    sp = np.linalg.norm(aff[:3, :3], axis=0)
    h = 0.5 * float(sp.mean())
    vox_ml = float(np.prod(sp)) / 1000.0
    labels = np.asarray(labels).astype(np.int16)
    ct = np.asarray(ct, np.float32)
    zero = np.zeros(labels.shape, bool)
    aorta = zero if aorta is None else np.asarray(aorta, bool)
    other = zero if other is None else np.asarray(other, bool)
    has_vessels = cor is not None and np.isin(cor, (G.LAD, G.LCX, G.RCA)).sum() >= 50
    geo = G.analyse(labels, affine=aff, coronary=cor if has_vessels else None)
    dep, aha = geo.depth, geo.aha
    myo, lv = labels == G.MYO, labels == G.LV
    solid = myo | lv
    r = {"spacing_mm": [round(float(x), 3) for x in sp], "has_coronary": bool(has_vessels),
         "aha_flagged": bool(aha.flagged),
         "aha_flags": [f.split(":")[0] for f in aha.flags]}

    # ---- Hotel: plateaus, half-maximum offsets, edge widths
    d_lv_in = ndi.distance_transform_edt(lv, sampling=sp) - h
    d_out = ndi.distance_transform_edt(~solid, sampling=sp) - h
    near_other = ndi.distance_transform_edt(~(labels == G.RV) & ~(labels == G.LA) & ~aorta
                                            & ~other, sampling=sp) < 2.0
    core1 = myo & (dep.d_endo >= 1.0) & (dep.d_epi >= 1.0)
    blood = _med(ct[lv & (d_lv_in >= 3.0)])
    myo_core = _med(ct[core1])
    fat_v = ct[~solid & ~near_other & (d_out > 1.5) & (d_out < 4.5)]
    fat = _med(fat_v[(fat_v > -250) & (fat_v < -30)])
    r["plateau_blood_hu"], r["plateau_myocore_hu"], r["plateau_fat_hu"] = blood, myo_core, fat
    sd_endo = np.where(lv, -d_lv_in, np.where(myo, dep.d_endo, np.nan))
    sd_epi = np.where(myo & ~near_other, dep.d_epi,
                      np.where(~solid & ~near_other & (d_out < 6.0), -d_out, np.nan))
    r["endo_halfmax_mm"], r["endo_10_90_mm"] = _edge(_profile(ct, sd_endo), blood, myo_core)
    r["epi_halfmax_mm"], r["epi_10_90_mm"] = _edge(_profile(ct, sd_epi), fat, myo_core)
    e = r["endo_10_90_mm"]
    fwhm = None if e is None else e / EDGE_TO_FWHM
    adaptive = None if fwhm is None or e > EDGE_MAX_MM else max(1.0, fwhm)
    r["endo_fwhm_mm"], r["guard_adaptive_mm"] = fwhm, adaptive

    # ---- Hotel: core HU (>= 1 mm from both borders)
    v = ct[core1]
    r["core1_hist"] = np.histogram(v, bins=HIST_EDGES)[0].tolist()
    r["core1_below_above"] = [int((v < HIST_EDGES[0]).sum()), int((v >= HIST_EDGES[-1]).sum())]
    r["core1_frac_fat_window"] = float(((v >= FAT_WINDOW[0]) & (v <= FAT_WINDOW[1])).mean()) \
        if v.size else None
    rng = np.random.default_rng(seed)
    r["_core_sample"] = (rng.choice(v, CORE_SAMPLE, replace=False) if v.size > CORE_SAMPLE
                         else v).tolist()

    # ---- Lima: thickness, voxels per third, halves
    regs = {k: geo.layers.regions[k] for k in range(1, 17) if k in geo.layers.regions}
    wall = {k: g["wall_mm"] for k, g in regs.items()}
    r["seg_wall_mm"] = wall
    r["seg_vox_per_third"] = {k: g["vox_per_third"] for k, g in regs.items()}
    r["seg_halves"] = [k for k, g in regs.items() if g["scheme"] == "halves"]
    r["n_segments"] = len(regs)
    r["median_thickness_mm"] = float(np.median(list(wall.values()))) if wall else None
    r["whole_scheme"] = geo.layers.regions[0]["scheme"]

    seg = aha.segments
    if seg is None:
        r["frame"] = "aha_failed"
        return r
    r["frame"] = "ok"
    r["septal_arc_deg"] = aha.septal_arc_deg

    # ---- Hotel: rest TPR, guards 0, 1 mm and JA17 adaptive
    r["tpr"] = {"0": tpr_segments(ct, myo, dep, seg, 0.0),
                "1": tpr_segments(ct, myo, dep, seg, 1.0),
                "adaptive": tpr_segments(ct, myo, dep, seg, adaptive) if adaptive else None}

    # ---- Lima E3 inputs: thickness and guarded subendocardial HU, relative to the patient
    gcore = adaptive if adaptive else 1.0
    r["guard_core_mm"], r["guard_core_is_adaptive"] = gcore, adaptive is not None
    if wall:
        m = float(np.median(list(wall.values())))
        r["rel_thickness"] = {k: w / m for k, w in wall.items()}
    sub = {}
    for k in range(1, 17):
        s = myo & (seg == k) & (dep.u < 1 / 3) & (dep.d_endo >= gcore)
        if s.sum() >= TPR_MIN_VOX:
            sub[k] = float(ct[s].mean())
    if sub:
        ms = float(np.median(list(sub.values())))
        r["rel_subendo_hu"] = {k: x / ms for k, x in sub.items()} if ms else None

    # ---- JA18: fat grid and Hotel's candidate, core >= the JA17 guard from both borders
    core = myo & (dep.d_endo >= gcore) & (dep.d_epi >= gcore)
    r["fat_grid"] = fat_grid(ct, core, vox_ml * 1000.0)
    r["fat_hotel_any"], r["fat_hotel_cut_hu"] = hotel_fat(ct, core)

    # ---- India: equal-thickness vs Laplace thirds
    lap = G.depth(labels, affine=aff, method="laplace")
    t_et = 1 + np.minimum((dep.u[myo] * 3).astype(int), 2)
    t_lp = 1 + np.minimum((lap.u[myo] * 3).astype(int), 2)
    r["thirds_agree_et_laplace"] = float(np.mean(t_et == t_lp))

    # ---- Lima / India: arc-proportional septal sectors
    has_seg = myo & (seg > 0)
    arc, agree = arc_segments(labels, aff, aha)
    r["arc_frame_agreement"] = agree
    if arc is not None and agree >= 0.995:
        changed = has_seg & (arc != seg)
        r["arc_changed_ml"] = float(changed.sum() * vox_ml)
        r["seg_ml"] = float(has_seg.sum() * vox_ml)
        r["arc_terr_changed_ml"] = float(
            (_std_terr(arc[has_seg]) != _std_terr(seg[has_seg])).sum() * vox_ml)
    else:
        arc = None

    # ---- territories: Euclidean (JA4) vs geodesic, discordance with the AHA default
    te = geo.territories
    if te is not None:
        tg = G.territories(labels, cor, affine=aff, segments=seg, method="geodesic")
        r["terr_n_segments"] = len(te.segments)
        r["terr_discordant_euclid"] = sum(not s["concordant"] for s in te.segments.values())
        r["terr_discordant_geodesic"] = sum(not s["concordant"] for s in tg.segments.values())
        r["terr_n_segments_geodesic"] = len(tg.segments)
        r["terr_segments_changed"] = sum(
            tg.segments.get(k, {}).get("territory") != s["territory"]
            for k, s in te.segments.items())
        r["terr_voxel_disagree"] = float(np.mean(te.label[myo] != tg.label[myo]))
        r["terr_shared_segments"] = sum(s["majority_share"] < 0.6 for s in te.segments.values())
        r["mass_share_euclid"] = te.share
        if arc is not None:
            ta = G.territories(labels, cor, affine=aff, segments=arc, method="euclidean")
            r["terr_discordant_euclid_arc"] = sum(
                not s["concordant"] for s in ta.segments.values())
            r["terr_n_segments_arc"] = len(ta.segments)
    return r


# --------------------------------------------------------------------------------------- aggregate
def q(values, ps=(10, 25, 50, 75, 90)):
    v = [float(x) for x in values if x is not None and np.isfinite(x)]
    if not v:
        return {"n": 0}
    return {**{f"p{p}": round(float(np.percentile(v, p)), 3) for p in ps}, "n": len(v)}


def _share(flags):
    flags = [bool(f) for f in flags if f is not None]
    return {"share": round(float(np.mean(flags)), 3), "n": len(flags)} if flags else {"n": 0}


def _ratio(num, den):
    return round(float(num) / den, 4) if den else None


def aggregate(rows) -> dict:
    """Aggregates only (JA23): quantiles, counts, shares and a pooled histogram. No case id, no
    per-case value: every list here is a distribution summary or a fixed grid."""
    fails = [r for r in rows if "error" in r]
    ok = [r for r in rows if "error" not in r]
    fr = [r for r in ok if r.get("frame") == "ok"]
    s = {"n_cases": len(rows), "n_measured": len(ok), "n_frame_ok": len(fr),
         "failures_by_type": dict(Counter(r["error"] for r in fails)),
         "spacing_inplane_mm": q([r["spacing_mm"][0] for r in ok]),
         "spacing_z_mm": q([r["spacing_mm"][2] for r in ok]),
         "has_coronary": sum(r["has_coronary"] for r in ok)}

    # Hotel
    hot = {k: q([r.get(k) for r in ok]) for k in (
        "endo_halfmax_mm", "epi_halfmax_mm", "endo_10_90_mm", "epi_10_90_mm", "endo_fwhm_mm",
        "guard_adaptive_mm", "plateau_blood_hu", "plateau_myocore_hu", "plateau_fat_hu",
        "core1_frac_fat_window")}
    hot["n_edge_over_2mm"] = sum((r.get("endo_10_90_mm") or 0) > EDGE_MAX_MM for r in ok)
    hot["core1_hist_edges_hu"] = HIST_EDGES.tolist()
    hot["core1_hist_pooled"] = (np.sum([r["core1_hist"] for r in ok], axis=0).tolist()
                                if ok else None)
    hot["core1_below_above_pooled"] = (np.sum([r["core1_below_above"] for r in ok], 0).tolist()
                                       if ok else None)
    core = np.concatenate([np.asarray(r["_core_sample"], float) for r in ok
                           if r.get("_core_sample")] or [np.zeros(0)])
    hot["core_sample_pooled_quantiles_hu"] = (
        {f"p{p}": round(float(np.percentile(core, p)), 1) for p in (0.1, 0.5, 1, 5, 50)}
        if core.size else None)
    tpr = {}
    for g in ("0", "1", "adaptive"):
        have = [r for r in fr if r["tpr"].get(g)]
        free = [x for r in have for k, x in r["tpr"][g].items() if int(k) not in SEPTAL]
        sept = [x for r in have for k, x in r["tpr"][g].items() if int(k) in SEPTAL]
        pat = [float(np.median([x for k, x in r["tpr"][g].items() if int(k) not in SEPTAL]))
               for r in have if any(int(k) not in SEPTAL for k in r["tpr"][g])]
        tpr[g] = {"n_cases": len(have), "free_wall_segments": q(free), "septal_segments": q(sept),
                  "patient_median_free_wall": q(pat),
                  "share_free_wall_below_0p99": _ratio(sum(x < 0.99 for x in free), len(free)),
                  "share_free_wall_in_0p99_1p25": _ratio(
                      sum(0.99 <= x <= 1.25 for x in free), len(free))}
    hot["tpr_by_guard"] = tpr
    s["hotel"] = hot

    # JA17 gate (all three, or rest TPR stays in the research export)
    e_w = hot["endo_10_90_mm"].get("p50")
    e_o = hot["endo_halfmax_mm"].get("p50")
    t_m = tpr["adaptive"]["free_wall_segments"].get("p50")
    c1 = None if e_w is None else e_w <= 1.5
    c2 = None if e_o is None else abs(e_o) <= 0.25
    c3 = None if t_m is None else 0.99 <= t_m <= 1.15
    s["ja17_rest_tpr_gate"] = {
        "edge_10_90_median_le_1p5mm": c1, "endo_halfmax_median_within_0p25mm": c2,
        "adaptive_guard_free_wall_tpr_median_in_0p99_1p15": c3,
        "passes": None if None in (c1, c2, c3) else bool(c1 and c2 and c3),
        "edge_median_over_2mm_not_computed": None if e_w is None else e_w > EDGE_MAX_MM}

    # Lima
    lim = {"median_thickness_mm": q([r.get("median_thickness_mm") for r in ok]),
           "seg_wall_mm": q([x for r in ok for x in r["seg_wall_mm"].values()]),
           "seg_vox_per_third": q([x for r in ok for x in r["seg_vox_per_third"].values()],
                                  (5, 10, 50, 90)),
           "share_segments_halves": _ratio(sum(len(r["seg_halves"]) for r in ok),
                                           sum(r["n_segments"] for r in ok)),
           "cases_with_any_halves": sum(bool(r["seg_halves"]) for r in ok),
           "aha_flagged_cases": sum(r["aha_flagged"] for r in ok),
           "aha_flags_by_kind": dict(Counter(f for r in ok for f in r["aha_flags"])),
           "thickness_definition_check_median_within_1p5mm_of_5p7_6p5": None}
    mt = lim["median_thickness_mm"].get("p50")
    if mt is not None:
        lim["thickness_definition_check_median_within_1p5mm_of_5p7_6p5"] = 4.2 <= mt <= 8.0
    rel = {k: [r["rel_thickness"][k] for r in fr if k in r.get("rel_thickness", {})]
           for k in range(1, 17)}
    shape = {k: float(np.mean(v)) for k, v in rel.items() if len(v) > 2}
    lim["rel_thickness_segment_shape_mean_sd"] = {
        str(k): [round(shape[k], 3), round(float(np.std(rel[k])), 3)] for k in shape}
    lim["rel_thickness_within_case_sd"] = q(
        [float(np.std(list(r["rel_thickness"].values()))) for r in fr if r.get("rel_thickness")])
    resid = [r["rel_thickness"][k] / shape[k] for r in fr for k in r.get("rel_thickness", {})
             if k in shape]
    lim["cv_n_shape_corrected_sd"] = round(float(np.std(resid)), 4) if resid else None
    rh = [x for r in fr for x in (r.get("rel_subendo_hu") or {}).values()]
    lim["rel_subendo_hu_sd"] = round(float(np.std(rh)), 4) if rh else None
    lim["guard_core_adaptive_cases"] = sum(r.get("guard_core_is_adaptive", False) for r in fr)
    grid = {}
    for c in FAT_CUTS:
        for v in FAT_VOLS:
            grid[f"c{c}_V{v}"] = _share([r["fat_grid"][f"{c}_{v}"] for r in fr])
    lim["fat_grid_share_hearts_with_cluster"] = grid
    lim["fat_grid_le_5pct_hearts"] = [k for k, x in grid.items()
                                      if x.get("n") and x["share"] <= 0.05]
    lim["fat_hotel_candidate_share_hearts"] = _share([r.get("fat_hotel_any") for r in fr])
    lim["fat_hotel_cut_hu"] = q([r.get("fat_hotel_cut_hu") for r in fr])
    arc = [r for r in fr if "arc_changed_ml" in r]
    seg_ml = sum(r["seg_ml"] for r in arc)
    lim["arc_sectors"] = {
        "n_cases": len(arc), "n_frame_check_failed": len(fr) - len(arc),
        "share_mass_changing_segment_pooled": _ratio(sum(r["arc_changed_ml"] for r in arc),
                                                     seg_ml),
        "share_mass_changing_segment_case": q([r["arc_changed_ml"] / r["seg_ml"] for r in arc]),
        "share_mass_changing_aha_territory_pooled": _ratio(
            sum(r["arc_terr_changed_ml"] for r in arc), seg_ml)}
    sh = lim["arc_sectors"]["share_mass_changing_segment_pooled"]
    lim["ja20_septal_arc_column_kept"] = None if sh is None else sh >= 0.10
    t = [r for r in fr if "terr_n_segments" in r]
    n_eu = sum(r["terr_n_segments"] for r in t)
    n_ge = sum(r["terr_n_segments_geodesic"] for r in t)
    n_ar = sum(r.get("terr_n_segments_arc", 0) for r in t)
    lim["territories"] = {
        "n_cases": len(t),
        "voxel_disagree_euclid_geodesic": q([r["terr_voxel_disagree"] for r in t]),
        "share_segments_majority_changes_euclid_geodesic": _ratio(
            sum(r["terr_segments_changed"] for r in t), n_eu),
        "share_segments_shared_lt_0p6": _ratio(sum(r["terr_shared_segments"] for r in t), n_eu),
        "mass_share_euclid": {k: q([r["mass_share_euclid"][k] for r in t])
                              for k in ("LAD", "LCx", "RCA")}}
    ch = lim["territories"]["share_segments_majority_changes_euclid_geodesic"]
    lim["ja20_geodesic_round3_rules"] = None if ch is None else ch >= 0.10
    s["lima"] = lim

    # India
    s["india"] = {
        "thirds_agree_et_laplace": q([r.get("thirds_agree_et_laplace") for r in fr]),
        "septal_arc_deg": q([r.get("septal_arc_deg") for r in fr]),
        "discordant_with_aha_default": {
            "euclid": _ratio(sum(r["terr_discordant_euclid"] for r in t), n_eu),
            "geodesic": _ratio(sum(r["terr_discordant_geodesic"] for r in t), n_ge),
            "euclid_arc_sectors": _ratio(
                sum(r.get("terr_discordant_euclid_arc", 0) for r in t), n_ar),
            "patients_with_any_discordant_euclid": _share(
                [r["terr_discordant_euclid"] > 0 for r in t])}}
    return s


# --------------------------------------------------------------------------------------- run
def _one(job):
    case, hc_dir, ct_path, icx_dir, ids = job
    t0 = time.time()
    try:
        lab, ct, aff, cor, aorta, other = load_case(case, hc_dir, ct_path, icx_dir, ids)
        r = measure(lab, ct, aff, cor, aorta, other, seed=int(hashlib.sha256(
            case.encode()).hexdigest()[:8], 16))
    except Exception as e:  # noqa: BLE001 -- the type only: a message can carry a path
        r = {"error": type(e).__name__}
    r["seconds"] = round(time.time() - t0, 1)
    return r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for k in ("cases", "hc", "layout", "icx", "splits", "out"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--np", type=int, default=8)
    a = ap.parse_args(argv)
    try:
        cases = guard_cases(a.cases, a.splits)  # before any image, mask, label or layout
    except Refused as e:
        print(f"REFUSED: {e}. Nothing was opened.", file=sys.stderr, flush=True)
        return 3
    print(f"guard: {len(cases)} cases, all the frozen JM-0 list, 0 refused "
          f"(janusm.guard purpose=any; splits.json hash ok)", file=sys.stderr, flush=True)
    layout = json.loads(Path(a.layout).read_text())["cases"]
    ids = hc_ids()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(c, a.hc, layout[c]["ct"], a.icx, ids) for c in cases]
    rows = []
    if a.np > 1:
        from multiprocessing import Pool

        pool = Pool(a.np)
        it = pool.imap(_one, jobs)
    else:
        pool, it = None, map(_one, jobs)
    try:
        with open(out / "cases.jsonl", "w") as fh:  # per-case rows: stay on Fir
            for i, (c, r) in enumerate(zip(cases, it), 1):
                fh.write(json.dumps({"id": c, **{k: x for k, x in r.items()
                                                 if not k.startswith("_")}}) + "\n")
                rows.append(r)
                print(f"case {i}/{len(cases)} {'fail' if 'error' in r else 'ok'} "
                      f"{r['seconds']}s", file=sys.stderr, flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    summary = {"provenance": provenance(), "hc_label_ids": ids, **aggregate(rows)}
    text = json.dumps(summary, indent=1)
    (out / "summary.json").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
