"""The Janus-M reference population and its pinned config (S6; Round 3 rest-ccta JA41, JA42, JA48).

Hotel v3 §4.1 (Issue A) as amended by JA48: one job, run once before any seal read, writes
``configs/janusm/reference-r1.json``, which holds every calibrated constant the table writer
(:mod:`janusm.report`) uses. The job is ``tools/janusm/build_reference.py``; this module holds
the computation, so it can be tested on synthetic populations.

**Cases.** ``splits.json`` train minus every Janus-M list in ``configs/janusm/sealed-r1.json``
(seal, seal extension, decision, JM-0), derived in code. Hotel v3 §4.1 says 420 (train minus the
seal 60, decision 40 and JM-0 40); the 60 seal-extension cases are inside those 420 and the JA12
guard refuses them under every purpose but seal scoring, so the population is **360**.
:func:`refuse_cases` runs before any file is opened: the JA12 guard (``purpose="any"``, which
refuses seal, extension and decision cases), an explicit JM-0 check (the guard ignores ``jm0``),
and equality with the derived list. The config stores the count and the sha256 of the sorted
list, never an id.

**Pooled** (:func:`pooled`): rule C shape and scale per segment, the mirror-null cut
(``calibrate_c``, 20 000 null patients, k 1.0-6.0 by 0.05, <= 5 % with a territory flag), for
thinning and hypoattenuation; the fat cut (JA43 R6 order); population percentiles; the composite
rate; the construct checks; and cv_n (JA40: plain SD of relative thickness / shape).

**Reads** (:func:`read_agreement`): F1's RC per sign and territory by JA42 as amended by JA63
(n = patients with a pair, each territory's own offset) and JA64 (a relative RC for the depth
signs when |Δ| grows with E_T; fat always on differences; one floor function,
:func:`rc_floor_mm`, for the gate and the report), from the first 20
decision cases with two accepted reads, and κ and ICC(2,1) (reported, never gating; JA41) on the
40 decision cases. The builder never opens a decision case: it takes anonymous per-read feature
records (no id), produced by the decision-scoring path.

**Gate** (JA41): a sign flags only if its cut exists, its RC exists (F1) and, for thinning and
hypoattenuation, its detectable depth (JA40, at this population's cv_n and shape and the
measured RC; JA60: simulated on the population's measured median, hypoattenuation with an
ED-only phase mix) is <= 0.50. Fat: cut and RC.

**Pin.** :func:`load` refuses a config whose sha256 is not :data:`janusm.guard.REFERENCE_SHA256`.
Until the lead's run is committed that pin is None, and every load refuses.

**Fall-backs** (JA75, Round 5): every read that fell back to the AHA default map is counted over
all reads the population uses, the RC's first 20 and κ / ICC's first 40, per use and in total
(:func:`fallback_counts`), in ``rc["aha_fallback"]`` and ``rc["decisions"]``.

The detectable depth and rule C come from S3 (``janusm.calibrate``, #194).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from janusm import calibrate
from janusm import features as F

REFERENCE_VERSION = 1
CONFIG_RELPATH = "configs/janusm/reference-r1.json"
SIGNS = ("thinning", "hypoattenuation", "fat")
DEPTH_SIGNS = ("thinning", "hypoattenuation")
TERRITORIES = F.TERRITORIES
LABEL = "this population, phase-uncertain"
NULL_TARGET = 0.05
DEPTH_GATE = 0.50                     # JA41
RC_CASES = 20                         # JA42: the first 20 decision cases with two reads
KAPPA_CASES = 40                      # JA41
KAPPA_MIN_FLAGGED = 5                 # JA41: κ "not estimable" below this
RC_PER_TERRITORY_MIN_N = 15           # JA42 step 3
OFFSET_FRACTION = 0.5                 # JA42 step 4
SPEARMAN_LOG = 0.4                    # JA42 step 4
COMPOSITE_RATE_MAX = 0.05
PCTL = tuple(range(0, 101))
SEED = 20261030
_ID = re.compile(r"(?<![A-Za-z0-9])(c\d{4}|s\d{4})(?![A-Za-z0-9])|__")


class ReferenceError(RuntimeError):
    """The reference config, its pin, or the builder's inputs are wrong. Never a pass."""


def _r(x, nd=4):
    if x is None:
        return None
    x = float(x)
    return None if not math.isfinite(x) else round(x, nd)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------------------- cases
def derive_cases(root=None) -> List[str]:
    """The reference population: splits.json train minus every Janus-M list, sorted."""
    from janusm import guard, sealed_r1

    root = Path(root) if root else guard.default_root()
    s = sealed_r1.load(root / sealed_r1.PATH)
    raw = (root / guard.SPLITS_RELPATH).read_bytes()
    if _sha(raw) != guard.PINNED[guard.SPLITS_RELPATH]:
        raise ReferenceError("splits.json is not the pinned one (JA6)")
    train = json.loads(raw)["train"]
    taken = set(s.seal) | set(s.decision) | set(s.jm0) | set(s.seal_extension)
    return sorted(c for c in train if c not in taken)


def refuse_cases(cases: Iterable[str], root=None, splits_path=None) -> List[str]:
    """The S6 guard, before any file is opened (JA48 item 6). Raises on any seal, extension,
    decision or JM-0 case, on duplicates, and on any list other than :func:`derive_cases`'s.
    ``splits_path``: the operator's splits.json, which must hash to the guard's pin."""
    from janusm import guard, sealed_r1

    cases = [str(c) for c in cases]
    if len(cases) != len(set(cases)):
        raise ReferenceError(f"{len(cases) - len(set(cases))} duplicate case(s)")
    guard.refuse(cases, what="JA18 reference population (S6)", source=guard.ICX_SOURCE,
                 purpose=guard.ANY, root=root)
    jm0 = sealed_r1.load(Path(root or guard.default_root()) / sealed_r1.PATH).jm0
    hit = sorted(set(cases) & set(jm0))
    if hit:
        raise guard.HeldOutError(f"REFUSING JA18 reference population (S6): {len(hit)} JM-0 "
                                 "case(s) (sealed-r1.json jm0)")
    if splits_path is not None:
        got = _sha(Path(splits_path).read_bytes())
        if got != guard.PINNED[guard.SPLITS_RELPATH]:
            raise ReferenceError(f"splits.json sha256 {got[:12]} is not the pinned one (JA6)")
    want = derive_cases(root)
    if sorted(cases) != want:
        raise ReferenceError(f"the case list is not the derived reference population: "
                             f"{len(set(cases) - set(want))} extra, "
                             f"{len(set(want) - set(cases))} missing")
    return cases


def cases_sha256(cases: Iterable[str]) -> str:
    return _sha("\n".join(sorted(cases)).encode())


def assert_anonymous(obj, what="input") -> None:
    """Refuse anything that carries a case id or pool name (builder inputs and outputs)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert_anonymous(str(k), what)
            assert_anonymous(v, what)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            assert_anonymous(v, what)
    elif isinstance(obj, str) and _ID.search(obj):
        raise ReferenceError(f"{what} carries a case id or pool name ({obj[:40]!r}); refusing")


# --------------------------------------------------------------------------------------- rule C
def rule_c_fit(values: np.ndarray, seed: int) -> dict:
    """Rule C on an n x 16 matrix of positive per-segment values (thickness, or subendocardial
    HU): shape, scale, the mirror-null cut by ``calibrate_c``, and its null rate. ``z`` equals
    ``calibrate.rule_c_scores(values)``."""
    v = np.asarray(values, float)
    rel = v / np.median(v, 1, keepdims=True)
    shape = np.median(rel, 0)
    dz = rel - shape
    scale = np.array([1.4826 * np.median(np.abs(c[c >= 0])) for c in dz.T])
    z = dz / scale
    cut, k = calibrate.calibrate_c(z, target=NULL_TARGET, rng=np.random.default_rng(seed))
    # the same null calibrate_c drew (first draw of the same generator)
    zf = z.ravel()
    med = float(np.median(zf))
    right = zf[zf >= med] - med
    null = np.random.default_rng(seed).choice(np.r_[med + right, med - right],
                                              (calibrate.NULL_PATIENTS, 16))
    null_rate = float(calibrate.territory_flags(null < cut).any(1).mean())
    resid = rel / shape
    return {"shape": [_r(x) for x in shape], "scale": [_r(x) for x in scale],
            "median": _r(med), "mad": _r(1.4826 * np.median(right)), "k": _r(k),
            "cut": _r(cut), "null_rate": _r(null_rate),
            "null": {"patients": calibrate.NULL_PATIENTS, "seed": int(seed),
                     "target": NULL_TARGET},
            "cv_n": _r(float(np.std(resid))), "median_level": _r(float(np.median(v))),
            "_z": z}


def rule_c_z(rel16: np.ndarray, block: dict) -> np.ndarray:
    """One patient's rule C z from its 16 values and a config block (shape, scale)."""
    v = np.asarray(rel16, float)
    rel = v / np.median(v)
    return (rel - np.asarray(block["shape"], float)) / np.asarray(block["scale"], float)


def percentiles(columns: Dict[int, list]) -> Dict[str, list]:
    return {str(k): [_r(x) for x in np.percentile(np.asarray(v, float), PCTL)]
            for k, v in sorted(columns.items()) if len(v)}


def _gk(d: Optional[dict], k):
    """``d[k]`` for an int key that JSON may have turned into a string."""
    if not d:
        return None
    return d.get(k, d.get(str(k)))


def percentile_of(x, table: Sequence[float]) -> Optional[int]:
    """Population percentile (0-100) of ``x`` by linear interpolation of the 101-point table."""
    if x is None or not table:
        return None
    t = np.asarray(table, float)
    return int(round(float(np.interp(float(x), t, np.asarray(PCTL, float)))))


# --------------------------------------------------------------------------------------- fat
def fat_choice(grid_shares: Dict[str, float], hotel_share: Optional[float]) -> dict:
    """JA43 R6 / JA18: the least strict (c, V) with <= 5 % of hearts (c = 0, -30, -50, -100,
    then V = 5, 20, 50 within each c); else Hotel's patient rule if <= 5 %; else number only."""
    for c in F.FAT_CUTS:
        for v in F.FAT_VOLS:
            s = grid_shares.get(F.fat_key(c, v))
            if s is not None and s <= NULL_TARGET:
                return {"rule": "grid", "c_hu": c, "v_mm3": v, "null_rate": _r(s)}
    if hotel_share is not None and hotel_share <= NULL_TARGET:
        return {"rule": "patient_noise", "c_hu": None, "v_mm3": None,
                "null_rate": _r(hotel_share)}
    return {"rule": "none", "c_hu": None, "v_mm3": None, "null_rate": None}


def fat_territory_volume(feat: dict, fat_block: dict, source: str = "aha"):
    """Core fat cluster volume (mm3) per territory at the chosen (c, V): the sum of its clusters
    >= V. ``source``: the AHA default map (``"aha"``; rule C's fat flag, as calibrated) or the
    patient map (``"patient"``; fat's D, JA63 step 1). Returns ({territory: mm3 or None}, the map
    used); a patient request without patient clusters falls back to the AHA map and says so
    (``"aha_fallback"``). None everywhere if the config chose no grid cell."""
    c, v = fat_block.get("c_hu"), fat_block.get("v_mm3")
    used = "aha"
    if source == "patient":
        if feat.get("fat_clusters_mm3_patient"):
            used = "patient"
        else:
            used = "aha_fallback"
    if c is None:
        return {t: None for t in TERRITORIES}, used
    key = "fat_clusters_mm3_patient" if used == "patient" else "fat_clusters_mm3"
    cl = (feat.get(key) or {}).get(str(c), {})
    return {t: _r(sum(x for x in cl.get(t, []) if x >= v), 3) for t in TERRITORIES}, used


# --------------------------------------------------------------------------------------- per case
def _remote_level(values16, shape16, segs) -> float:
    """``f1_deviation``'s remote level: the median of the shape-corrected values outside the
    territory."""
    v, sh = np.asarray(values16, float), np.asarray(shape16, float)
    rem = [s for s in range(16) if s + 1 not in segs]
    return float(np.median(v[rem] / sh[rem]))


def territory_deviation(values16, shape16, terr_segments: Dict[str, Sequence[int]]) -> dict:
    """Hotel's shape-corrected deviation D per territory (``f1_deviation``) on the given map.
    Positive = lower than the patient's remote level predicts. None for an empty territory."""
    out = {}
    for t in TERRITORIES:
        segs = [s for s in terr_segments.get(t, []) if 1 <= s <= 16]
        if not segs or len(segs) == 16:
            out[t] = None
            continue
        d = calibrate.f1_deviation(np.asarray(values16, float)[None], shape16, {t: segs})
        out[t] = float(d[0, 0])
    return out


def territory_expected(values16, shape16, terr_segments: Dict[str, Sequence[int]]) -> dict:
    """JA64's E_T per territory: the remote level x the territory's mean shape, the term D is
    measured against in ``f1_deviation``. None for an empty territory."""
    out = {}
    sh = np.asarray(shape16, float)
    for t in TERRITORIES:
        segs = [s for s in terr_segments.get(t, []) if 1 <= s <= 16]
        if not segs or len(segs) == 16:
            out[t] = None
            continue
        out[t] = _remote_level(values16, sh, segs) * float(sh[[s - 1 for s in segs]].mean())
    return out


def population_expected(blk: dict) -> Dict[str, float]:
    """E_T for ``gate()`` (JA64): the population's median level x the territory's mean shape on
    the AHA default map."""
    sh = np.asarray(blk["shape"], float)
    lvl = float(blk["median_level"])
    return {t: lvl * float(sh[[s - 1 for s in calibrate.TERR16[t]]].mean()) for t in TERRITORIES}


def sign_values(feat: dict, sign: str):
    """The 16-vector rule C runs on for a sign: wall thickness (mm) or relative subendo HU."""
    if sign == "thinning":
        return F.vector16(feat.get("wall_mm"))
    if sign == "hypoattenuation":
        return F.vector16(feat.get("rel_subendo_hu"))
    raise ValueError(sign)


def case_state(feat: dict, cfg: dict, map_source: str = "patient") -> dict:
    """Per sign and territory: rule C territory flag (AHA default, as calibrated), D on
    ``map_source``'s map, E_T (depth signs; JA64) and the segment flags.

    JA63: a patient-map request that has no patient map (or, for fat, no patient-map clusters)
    falls back to the AHA default map; the sign's ``map`` and the case's ``map`` then read
    ``"aha_fallback"``, which callers count. Never silent."""
    out: dict = {}
    tmap = F.territory_segments(feat, map_source)
    used = map_source
    if not any(tmap.values()):
        tmap = F.territory_segments(feat, "aha")
        used = "aha_fallback" if map_source == "patient" else "aha"
    for sign in DEPTH_SIGNS:
        blk = cfg[sign]
        v = sign_values(feat, sign)
        if v is None or blk.get("cut") is None:
            out[sign] = None
            continue
        z = rule_c_z(v, blk)
        seg_flag = z < blk["cut"]
        tf = calibrate.territory_flags(seg_flag[None])[0]
        tflag = {t: bool(tf[calibrate.TNAMES.index(t)]) for t in TERRITORIES}
        shape = np.asarray(blk["shape"], float)
        out[sign] = {"z": z, "seg_flag": seg_flag, "territory_rule_c": tflag,
                     "D": territory_deviation(v, shape, tmap),
                     "E": territory_expected(v, shape, tmap), "map": used}
    fb = cfg["fat"]
    flag_vol, _ = fat_territory_volume(feat, fb, "aha")
    d_vol, fat_map = fat_territory_volume(feat, fb, "patient" if map_source == "patient"
                                          else "aha")
    out["fat"] = {"territory_rule_c": {t: (flag_vol[t] is not None and flag_vol[t] > 0)
                                       for t in TERRITORIES},
                  "D": d_vol, "E": None, "map": fat_map}
    maps = {x["map"] for x in out.values() if x is not None}
    out["map"] = "aha_fallback" if "aha_fallback" in maps else map_source
    return out


# --------------------------------------------------------------------------------------- pooled
def pooled(feats: List[dict], *, seed: int = SEED) -> dict:
    """Everything the population alone determines. ``feats``: :func:`features.case_features`
    outputs of the usable reference cases (no id)."""
    usable = [f for f in feats if f.get("frame") == "ok"]
    out: dict = {"n_usable": len(usable),
                 "excluded": {"frame_failed_or_error": sum(f.get("frame") != "ok" for f in feats)}}
    for i, sign in enumerate(DEPTH_SIGNS):
        rows = [sign_values(f, sign) for f in usable]
        keep = [r for r in rows if r is not None and np.all(np.asarray(r) > 0)]
        out["excluded"][f"{sign}_incomplete"] = len(rows) - len(keep)
        if len(keep) < 20:
            out[sign] = {"cut": None, "status": "number_only",
                         "reason": f"{len(keep)} complete cases"}
            continue
        fit = rule_c_fit(np.vstack(keep), seed + 1000 * (i + 1))
        fit.pop("_z")
        out[sign] = fit
    arc = [f.get("septal_arc") or {} for f in usable]
    out["septal_arc_percentiles"] = {
        q: percentiles({k: [v for v in (_gk(a.get(q), k) for a in arc) if v is not None]
                        for k in F.ARC_SEPTAL})
        for q in ("wall_mm", "rel_subendo_hu")}
    out["thinning_percentiles"] = percentiles(
        {k: [f["wall_mm"][k] for f in usable if k in f.get("wall_mm", {})] for k in range(1, 18)})
    out["hypoattenuation_percentiles"] = percentiles(
        {k: [f["rel_subendo_hu"][k] for f in usable if k in (f.get("rel_subendo_hu") or {})]
         for k in range(1, 17)})
    n = max(len(usable), 1)
    grid = {F.fat_key(c, v): _r(sum(bool(f.get("fat_grid", {}).get(F.fat_key(c, v)))
                                    for f in usable) / n)
            for c in F.FAT_CUTS for v in F.FAT_VOLS}
    hot = [f.get("fat_hotel_any") for f in usable if f.get("fat_hotel_any") is not None]
    hshare = _r(sum(hot) / len(hot)) if hot else None
    out["fat"] = {**fat_choice(grid, hshare), "grid": grid, "patient_noise_share": hshare}
    return out


def composite_and_construct(feats: List[dict], cfg: dict) -> dict:
    """The composite's population rate (Hotel v2 §4.3) and the construct checks (reported)."""
    usable = [f for f in feats if f.get("frame") == "ok"]
    comp = 0
    contig_num = contig_den = endo_num = endo_den = col_num = col_den = 0
    for f in usable:
        st = case_state(f, cfg, "aha")
        th, hy, fa = st.get("thinning"), st.get("hypoattenuation"), st["fat"]
        if th is None:
            continue
        for t in TERRITORIES:
            if th["territory_rule_c"][t]:
                col_den += 1
                sub = (hy is not None and hy["territory_rule_c"][t]) or fa["territory_rule_c"][t]
                col_num += bool(sub)
        if any(th["territory_rule_c"][t] and ((hy is not None and hy["territory_rule_c"][t])
                                              or fa["territory_rule_c"][t])
               for t in TERRITORIES):
            comp += 1
        fl = np.nonzero(th["seg_flag"])[0] + 1
        for s in fl:
            contig_den += 1
            contig_num += any(th["seg_flag"][x - 1] for x in calibrate.RING[int(s)])
        if hy is not None:
            sub = f.get("rel_subendo_hu") or {}
            epi = f.get("rel_subepi_hu") or {}
            for s in np.nonzero(hy["seg_flag"])[0] + 1:
                a, b = sub.get(int(s), sub.get(str(int(s)))), epi.get(int(s), epi.get(str(int(s))))
                if a is not None and b is not None:
                    endo_den += 1
                    endo_num += a < b
    n = max(len(usable), 1)
    rate = comp / n
    ratio = lambda a, b: _r(a / b) if b else None  # noqa: E731
    return {"composite": {"population_rate": _r(rate),
                          "needs_two_contiguous": bool(rate > COMPOSITE_RATE_MAX)},
            "construct_checks": {"contiguity": ratio(contig_num, contig_den),
                                 "endo_predominance": ratio(endo_num, endo_den),
                                 "colocation": ratio(col_num, col_den)}}


def rest_tpr_block(feats: List[dict], gate: str) -> dict:
    """JA17 / R5: the population median and robust scale of free-wall TPR, only if the gate
    passed. ``gate`` is the decision script's R5 verdict."""
    if gate not in ("pass", "fail", "not_evaluable"):
        raise ReferenceError(f"rest TPR gate must be pass, fail or not_evaluable, not {gate!r}")
    blk = {"gate": gate, "median": None, "z_scale": None}
    if gate != "pass":
        return blk
    septal = {2, 3, 8, 9, 14}
    v = [x for f in feats if f.get("frame") == "ok"
         for k, x in (f.get("tpr") or {}).items() if int(k) not in septal and x is not None]
    if len(v) < 20:
        return {**blk, "gate": "not_evaluable"}
    med = float(np.median(v))
    blk.update(median=_r(med), z_scale=_r(1.4826 * float(np.median(np.abs(np.asarray(v) - med)))))
    return blk


# --------------------------------------------------------------------------------------- reads
def _chi2_factor(n: int) -> float:
    """sqrt((n - 1) / chi2_0.025,n-1): the upper 95 % bound of an SD over its estimate."""
    from scipy.stats import chi2

    return math.sqrt((n - 1) / chi2.ppf(0.025, n - 1))


def _spearman(x, y) -> float:
    from scipy.stats import spearmanr

    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")  # constant input: no trend to test
    return float(spearmanr(x, y).statistic)


def repeatability(d1, d2, e1=None, e2=None, *, cases=None) -> dict:
    """F1's RC by JA42 steps 3-5 as amended by JA63 and JA64.

    ``d1``, ``d2``: {territory: [D per position]} for the two reads, None where a case lacks the
    territory. ``e1``, ``e2``: the same for E_T (JA64; depth signs), or None (fat: always on
    differences). ``cases``: the case index of each position (default: the position), so that n
    counts **patients** with at least one pair, never values (JA63).

    Step 3: the pooled SD is over every value; its 95 % bound and the switch to a territory's own
    SD (n_T >= 15 patients and SD_T above the pooled bound) use n = patients. Step 4a: each
    territory's **own** mean difference is added when larger than 0.5 x the SD it uses. Step 4b
    (JA64): if Spearman rho(|Δ_T|, mean of the two reads' E_T) > 0.4 and E_T > 0 for every pair,
    the RC is on Δ_T / Ē_T (``scale`` ``"relative"``, applied as RC x E by
    :func:`rc_floor_mm`); otherwise on differences, with the decision recorded."""
    npos = max([len(d1.get(t, [])) for t in TERRITORIES] + [0])
    cases = list(range(npos)) if cases is None else list(cases)
    rows = {}
    for t in TERRITORIES:
        a_, b_ = d1.get(t, []), d2.get(t, [])
        ea = (e1 or {}).get(t) or [None] * len(a_)
        eb = (e2 or {}).get(t) or [None] * len(b_)
        rows[t] = [(cases[i], a_[i], b_[i], ea[i], eb[i]) for i in range(min(len(a_), len(b_)))
                   if a_[i] is not None and b_[i] is not None]
    allrows = [r for t in TERRITORIES for r in rows[t]]
    n_values = len(allrows)
    n_patients = len({r[0] for r in allrows})
    if n_values < 3 or n_patients < 2:
        return {"status": "not_computed",
                "reason": f"{n_values} paired values on {n_patients} patients",
                "n_patients": n_patients, "n_values": n_values}
    decisions = []
    delta = {t: np.array([a - b for _, a, b, _, _ in rows[t]], float) for t in TERRITORIES}
    alld = np.concatenate([delta[t] for t in TERRITORIES])
    relative, rho = False, None
    if e1 is None or e2 is None:
        decisions.append("fat: RC on differences, in mm³ (JA64)")
    else:
        ebar = np.array([(ea + eb) / 2 if ea is not None and eb is not None else np.nan
                         for t in TERRITORIES for _, _, _, ea, eb in rows[t]], float)
        ok = np.isfinite(ebar)
        rho = _spearman(np.abs(alld[ok]), ebar[ok])
        if not (math.isfinite(rho) and rho > SPEARMAN_LOG):
            decisions.append(f"Spearman rho(|Δ|, E) {rho:.3f} <= {SPEARMAN_LOG}: "
                             "RC on differences")
        elif not all(ea is not None and eb is not None and ea > 0 and eb > 0
                     for _, _, _, ea, eb in allrows):
            decisions.append(f"Spearman rho(|Δ|, E) {rho:.3f} > {SPEARMAN_LOG}, but E_T <= 0 (or "
                             "missing) for a pair: RC kept on differences (JA64)")
        else:
            relative = True
            for t in TERRITORIES:
                delta[t] = np.array([(a - b) / ((ea + eb) / 2) for _, a, b, ea, eb in rows[t]],
                                    float)
            alld = np.concatenate([delta[t] for t in TERRITORIES])
            decisions.append(f"Spearman rho(|Δ|, E) {rho:.3f} > {SPEARMAN_LOG} and E_T > 0 "
                             "for every pair: RC on Δ / Ē, applied as RC x E_T (JA64)")
    sd_pool = float(np.std(alld, ddof=1))
    pool_ub = sd_pool * _chi2_factor(n_patients)
    out = {"scale": "relative" if relative else "difference", "spearman_rho": _r(rho),
           "n_patients": n_patients, "n_values": n_values,
           "pooled": {"sd": _r(sd_pool), "sd_upper95": _r(pool_ub), "n_patients": n_patients,
                      "n_values": n_values, "mean_diff": _r(float(alld.mean()))},
           "territory": {}}
    for t in TERRITORIES:
        dt = delta[t]
        n_t = len({r[0] for r in rows[t]})
        sd_t = float(np.std(dt, ddof=1)) if len(dt) > 1 else float("nan")
        own = n_t >= RC_PER_TERRITORY_MIN_N
        use_own = own and math.isfinite(sd_t) and sd_t > pool_ub
        if not own:
            why = f"n_T {n_t} < {RC_PER_TERRITORY_MIN_N} patients: pooled"
        elif use_own:
            why = f"SD_T {sd_t:.4f} > pooled 95 % bound {pool_ub:.4f}: own"
        else:
            why = "SD_T within the pooled 95 % bound: pooled"
        sd, n = (sd_t, n_t) if use_own else (sd_pool, n_patients)
        md = float(dt.mean()) if len(dt) else 0.0  # step 4a: the territory's own mean (JA63)
        rc_point = 1.96 * sd
        rc = 1.96 * sd * _chi2_factor(n)
        if abs(md) > OFFSET_FRACTION * sd:
            rc += abs(md)
            why += f"; |own mean diff| {abs(md):.4f} > {OFFSET_FRACTION} SD: added"
        out["territory"][t] = {"rc": _r(rc), "rc_point": _r(rc_point), "sd": _r(sd), "n": n,
                               "n_territory": n_t, "n_values": len(dt), "mean_diff": _r(md),
                               "source": "territory" if use_own else "pooled", "decision": why}
    out["decisions"] = decisions
    out["status"] = "computed"
    return out


def rc_floor_mm(rc: dict, territory: str, e: Optional[float]) -> Optional[float]:
    """F1's floor for one territory in the sign's own units (JA64): the RC itself on
    differences, RC_rel x E on the relative scale. ``gate()`` passes the population's E_T, the
    report the patient's. None when the RC is relative and E is missing or not positive (no
    floor, so no flag)."""
    v = float(rc["territory"][territory]["rc"])
    if rc.get("scale") != "relative":
        return v
    if e is None or not math.isfinite(float(e)) or float(e) <= 0:
        return None
    return v * float(e)


def cohen_kappa(a: Sequence[bool], b: Sequence[bool]) -> Optional[float]:
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = float(np.mean(a == b))
    pa, pb = a.mean(), b.mean()
    pe = float(pa * pb + (1 - pa) * (1 - pb))
    return None if pe >= 1 else (po - pe) / (1 - pe)


def kappa_status(fa: Sequence[bool], fb: Sequence[bool]):
    """(κ, status) for JA41: "not estimable" below :data:`KAPPA_MIN_FLAGGED` flagged units in
    either read, or when chance agreement is 1 (κ is 0 / 0)."""
    if not len(fa):
        return None, "no units"
    if min(sum(fa), sum(fb)) < KAPPA_MIN_FLAGGED:
        return None, (f"not estimable: a read has < {KAPPA_MIN_FLAGGED} flagged units "
                      f"({sum(fa)}, {sum(fb)})")
    k = cohen_kappa(fa, fb)
    if k is None:
        return None, "not estimable: chance agreement pe = 1"
    return k, "estimated"


def icc_2_1(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    """Shrout & Fleiss (1979) ICC(2,1): two-way random, absolute agreement, single rater."""
    m = np.column_stack([np.asarray(x, float), np.asarray(y, float)])
    n, k = m.shape
    if n < 3:
        return None
    gm = m.mean()
    msr = k * ((m.mean(1) - gm) ** 2).sum() / (n - 1)
    msc = n * ((m.mean(0) - gm) ** 2).sum() / (k - 1)
    sse = ((m - m.mean(1, keepdims=True) - m.mean(0, keepdims=True) + gm) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    den = msr + (k - 1) * mse + k * (msc - mse) / n
    return None if den == 0 else float((msr - mse) / den)


def fallback_counts(states, sign: str, rc_idx: Sequence[int], k_idx: Sequence[int]) -> dict:
    """JA75: AHA fall-backs over every read the population uses, per use and in total.

    ``states``: (read 1, read 2) :func:`case_state` pairs in draw order; ``rc_idx`` and
    ``k_idx``: the entries the RC (first 20) and κ / ICC (first 40) use for ``sign``. Returns
    ``{"rc" | "kappa_icc" | "total": {"fell": n, "reads": n}}``; ``total`` is over the union, so
    a read both uses share is counted once."""
    def count(idx):
        idx = sorted(set(idx))
        fell = sum(states[i][r][sign]["map"] == "aha_fallback" for i in idx for r in (0, 1))
        return {"fell": int(fell), "reads": 2 * len(idx)}

    return {"rc": count(rc_idx), "kappa_icc": count(k_idx),
            "total": count(list(rc_idx) + list(k_idx))}


def fallback_decision(fb: dict) -> str:
    """The ``rc["decisions"]`` line for :func:`fallback_counts` (JA63's "never silent")."""
    part = lambda k: f"{fb[k]['fell']} of {fb[k]['reads']}"  # noqa: E731
    return (f"AHA default-map fall-backs (JA63, JA75): RC {part('rc')} reads, "
            f"κ / ICC {part('kappa_icc')} reads, total {part('total')} reads")


def read_agreement(reads: List[dict], cfg: dict) -> dict:
    """RC (first 20 entries) and κ / ICC (first 40) per sign from anonymous read pairs.

    ``reads``: decision cases in draw order, each ``{"read_1": features, "read_2": features}``
    (outputs of :func:`features.case_features` on the two accepted reads, no id). D and E_T use
    the patient-specific map of each read (JA42 step 1, JA63); rule C flags use the AHA default
    map. Every read that fell back to the AHA map is counted in ``rc["decisions"]`` and
    ``rc["aha_fallback"]``, per use (RC, κ / ICC) and in total (JA63, JA75)."""
    assert_anonymous(reads, "the read records")
    out: Dict[str, dict] = {}
    states = [(case_state(r["read_1"], cfg), case_state(r["read_2"], cfg)) for r in reads]
    for sign in SIGNS:
        rc_rows = [(i, a[sign], b[sign]) for i, (a, b) in enumerate(states[:RC_CASES])
                   if a.get(sign) is not None and b.get(sign) is not None]
        d1 = {t: [a["D"][t] for _, a, _ in rc_rows] for t in TERRITORIES}
        d2 = {t: [b["D"][t] for _, _, b in rc_rows] for t in TERRITORIES}
        if sign in DEPTH_SIGNS:
            e1 = {t: [a["E"][t] for _, a, _ in rc_rows] for t in TERRITORIES}
            e2 = {t: [b["E"][t] for _, _, b in rc_rows] for t in TERRITORIES}
        else:
            e1 = e2 = None
        rc = repeatability(d1, d2, e1, e2, cases=[i for i, _, _ in rc_rows])
        rc["n_cases"] = len(rc_rows)
        k_idx = [i for i, (a, b) in enumerate(states[:KAPPA_CASES])
                 if a.get(sign) is not None and b.get(sign) is not None]
        k_rows = [(states[i][0][sign], states[i][1][sign]) for i in k_idx]
        fb = fallback_counts(states, sign, [i for i, _, _ in rc_rows], k_idx)
        rc["aha_fallback"] = fb
        rc["aha_fallback_reads"] = fb["total"]["fell"]
        rc.setdefault("decisions", []).append(fallback_decision(fb))
        fa = [a["territory_rule_c"][t] for a, _ in k_rows for t in TERRITORIES]
        fb = [b["territory_rule_c"][t] for _, b in k_rows for t in TERRITORIES]
        kap, kn = kappa_status(fa, fb)
        xs = [(a["D"][t], b["D"][t]) for a, b in k_rows for t in TERRITORIES
              if a["D"][t] is not None and b["D"][t] is not None]
        icc = icc_2_1([p[0] for p in xs], [p[1] for p in xs]) if xs else None
        out[sign] = {"rc": rc, "kappa": _r(kap), "kappa_status": kn, "icc": _r(icc),
                     "n_units": len(fa)}
    return out


# --------------------------------------------------------------------------------------- gate
#: JA60: hypoattenuation is a relative HU level, which phase does not scale.
HYPO_PHASE_MIX = {"ED": 1.0, "MD": 0.0, "SYS": 0.0}  # every phase named: S3's sampler needs them


def s3_wall_kwargs(sign: str, blk: dict) -> dict:
    """The wall input ``gate()`` gives S3 (JA60, R4-S10): ``measured_median_mm`` = this
    population's median level and, for hypoattenuation (a relative HU level, which phase does
    not scale), ``phase_mix={"ED": 1.0}``. Never ``median_mm``, which is E7's only."""
    kw = {"measured_median_mm": float(blk["median_level"])}
    if sign == "hypoattenuation":
        kw["phase_mix"] = dict(HYPO_PHASE_MIX)
    return kw


def gate(sign: str, cfg: dict, agreement: dict, *, seed: int = SEED, sig_m: float = 0.0) -> dict:
    """JA41 for one sign. Depth (thinning, hypoattenuation) at the population's cv_n and shape,
    the conservative floor (the largest territory floor, at the population's E_T; JA64) and the
    population's measured median level (JA60)."""
    blk = cfg[sign]
    ag = agreement.get(sign) or {}
    rc = ag.get("rc") or {}
    has_rc = rc.get("status") == "computed"
    g = {"kappa": ag.get("kappa"), "kappa_status": ag.get("kappa_status"), "icc": ag.get("icc"),
         "depth": None, "rc_terr_for_depth": None}
    if sign == "fat":
        has_cut = blk.get("rule") in ("grid", "patient_noise")
        g["pass"] = bool(has_cut and has_rc)
        g["why"] = ("fat: cut and F1 (JA41; no depth gate)" if g["pass"] else
                    "fat: no cut" if not has_cut else "fat: no RC (F1)")
        return g
    if blk.get("cut") is None or not has_rc:
        g["pass"] = False
        g["why"] = "no cut" if blk.get("cut") is None else "no RC (F1)"
        return g
    e = population_expected(blk)
    floors = {t: rc_floor_mm(rc, t, e[t]) for t in TERRITORIES}
    if any(v is None for v in floors.values()):
        g["pass"] = False
        g["why"] = "no F1 floor: the population's E_T is not positive"
        return g
    rc_mm = max(floors.values())
    kw = s3_wall_kwargs(sign, blk)
    dd = calibrate.detectable_depth(blk["cv_n"], np.asarray(blk["shape"], float), rc_mm,
                                    sig_m=sig_m, seed=seed, **kw)
    g.update(depth=dd["depth"], sens_range=dd["sens_range"], false_flag=dd["false_flag"],
             rc_terr_for_depth=_r(rc_mm), depth_seed=int(seed),
             floor_mm={t: _r(v) for t, v in floors.items()},
             expected={t: _r(v) for t, v in e.items()},
             s3_wall_input={k: v for k, v in kw.items()})
    g["pass"] = bool(dd["depth"] is not None and dd["depth"] <= DEPTH_GATE + 1e-9)
    g["why"] = (f"depth {dd['depth']} <= {DEPTH_GATE}" if g["pass"] else
                f"depth {dd['depth'] if dd['depth'] is not None else '> 0.60'} > {DEPTH_GATE}")
    return g


# --------------------------------------------------------------------------------------- config
def build_config(feats: List[dict], reads: List[dict], *, cases_sha: str, n_cases: int,
                 rest_tpr_gate: str, septal_arc_column: bool, halves_note: bool,
                 geodesic_shared: bool = False, model: str, guard_mm: float,
                 seed: int = SEED) -> dict:
    """The whole config, from anonymous features. Deterministic for fixed inputs and seed."""
    from janusm import geometry, guard

    assert_anonymous(feats, "the population features")
    cfg = pooled(feats, seed=seed)
    cfg.update(composite_and_construct(feats, cfg))
    ag = read_agreement(reads, cfg)
    gates = {s: gate(s, cfg, ag, seed=seed + 7 * (i + 1)) for i, s in enumerate(SIGNS)}
    for s in SIGNS:
        cfg[s]["status"] = "flag" if gates[s]["pass"] else "number_only"
        rc = ag[s]["rc"]
        cfg[s]["rc_terr"] = ({t: rc["territory"][t]["rc"] for t in TERRITORIES}
                             if rc.get("status") == "computed" else None)
        cfg[s]["rc_scale"] = rc.get("scale")
    th = cfg["thinning"]
    out = {
        "version": REFERENCE_VERSION,
        "what": "Janus-M reference population config (S6; JA41, JA42, JA48). Produced once, "
                "before any seal read; never refitted on seal cases.",
        "geometry_version": geometry.GEOMETRY_VERSION, "guard_version": guard.GUARD_VERSION,
        "features_version": F.FEATURES_VERSION, "calibrate": calibrate.__name__,
        "calibrate_version": calibrate.CALIBRATE_VERSION,
        "model": model, "guard_mm": float(guard_mm),
        "cases_sha256": cases_sha, "splits_sha256_prefix": guard.PINNED[guard.SPLITS_RELPATH][:12],
        "n_cases": int(n_cases), "n_usable": cfg.pop("n_usable"), "excluded": cfg.pop("excluded"),
        "label": LABEL, "seed": int(seed),
        "thinning": cfg["thinning"], "hypoattenuation": cfg["hypoattenuation"], "fat": cfg["fat"],
        "percentiles": {"thickness_mm": cfg.pop("thinning_percentiles"),
                        "rel_subendo_hu": cfg.pop("hypoattenuation_percentiles"),
                        "septal_arc": cfg.pop("septal_arc_percentiles")},
        "gate": gates, "rc": {s: ag[s]["rc"] for s in SIGNS},
        "rest_tpr": rest_tpr_block(feats, rest_tpr_gate),
        "composite": cfg["composite"], "construct_checks": cfg["construct_checks"],
        "detectable_depth": {"value": gates["thinning"]["depth"], "cv_n": th.get("cv_n"),
                             "rc_terr_mm": gates["thinning"]["rc_terr_for_depth"]},
        "page_line": {s: calibrate.page_line(gates[s]["depth"], s) for s in DEPTH_SIGNS},
        "table": {"septal_arc_column": bool(septal_arc_column), "halves_note": bool(halves_note),
                  "geodesic_shared": bool(geodesic_shared)},
    }
    assert_anonymous(out, "the config")
    return out


def dumps(cfg: dict) -> str:
    """Canonical bytes: sorted keys, one space indent, trailing newline."""
    return json.dumps(cfg, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


# --------------------------------------------------------------------------------------- pin
@dataclass(frozen=True)
class Reference:
    """A loaded, pin-checked config."""

    data: dict
    sha256: str
    path: str


def load(path=None, *, root=None) -> Reference:
    """Load the config and check it against :data:`janusm.guard.REFERENCE_SHA256`. A missing
    pin, a missing file or a changed file is refused."""
    from janusm import guard

    root = Path(root) if root else guard.default_root()
    p = Path(path) if path else root / CONFIG_RELPATH
    pin = guard.REFERENCE_SHA256
    if pin is None:
        raise ReferenceError(f"{CONFIG_RELPATH} is not pinned yet (janusm.guard.REFERENCE_SHA256 "
                             "is None); the table cannot run before the lead's reference run")
    if not p.is_file():
        raise ReferenceError(f"{p}: reference config not found")
    raw = p.read_bytes()
    got = _sha(raw)
    if got != pin:
        raise ReferenceError(f"{p}: sha256 {got} is not the pinned {pin}; a reference change is "
                             "an explicit PR to the file and janusm.guard.REFERENCE_SHA256")
    data = json.loads(raw)
    if data.get("version") != REFERENCE_VERSION:
        raise ReferenceError(f"{p}: version {data.get('version')} is not {REFERENCE_VERSION}")
    return Reference(data=data, sha256=got, path=str(p))
