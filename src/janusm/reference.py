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

**Reads** (:func:`read_agreement`): F1's RC per sign and territory by JA42, from the first 20
decision cases with two accepted reads, and κ and ICC(2,1) (reported, never gating; JA41) on the
40 decision cases. The builder never opens a decision case: it takes anonymous per-read feature
records (no id), produced by the decision-scoring path.

**Gate** (JA41): a sign flags only if its cut exists, its RC exists (F1) and, for thinning and
hypoattenuation, its detectable depth (JA40, at this population's cv_n and shape and the
measured RC) is <= 0.50. Fat: cut and RC.

**Pin.** :func:`load` refuses a config whose sha256 is not :data:`janusm.guard.REFERENCE_SHA256`.
Until the lead's run is committed that pin is None, and every load refuses.

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


def fat_territory_volume(feat: dict, fat_block: dict) -> Dict[str, Optional[float]]:
    """Core fat cluster volume (mm3) per AHA-default territory at the chosen (c, V): the sum of
    its clusters >= V. None if the config chose no grid cell."""
    c, v = fat_block.get("c_hu"), fat_block.get("v_mm3")
    if c is None:
        return {t: None for t in TERRITORIES}
    cl = (feat.get("fat_clusters_mm3") or {}).get(str(c), {})
    return {t: _r(sum(x for x in cl.get(t, []) if x >= v), 3) for t in TERRITORIES}


# --------------------------------------------------------------------------------------- per case
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


def sign_values(feat: dict, sign: str):
    """The 16-vector rule C runs on for a sign: wall thickness (mm) or relative subendo HU."""
    if sign == "thinning":
        return F.vector16(feat.get("wall_mm"))
    if sign == "hypoattenuation":
        return F.vector16(feat.get("rel_subendo_hu"))
    raise ValueError(sign)


def case_state(feat: dict, cfg: dict, map_source: str = "patient") -> dict:
    """Per sign and territory: rule C territory flag (AHA default, as calibrated), D (on
    ``map_source``'s map, falling back to AHA default), and the segment flags."""
    out = {}
    tmap = F.territory_segments(feat, map_source)
    if not any(tmap.values()):
        tmap = F.territory_segments(feat, "aha")
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
        dev = territory_deviation(v, np.asarray(blk["shape"], float), tmap)
        out[sign] = {"z": z, "seg_flag": seg_flag, "territory_rule_c": tflag, "D": dev,
                     "level": float(np.median(v))}
    fb = cfg["fat"]
    vol = fat_territory_volume(feat, fb)
    out["fat"] = {"territory_rule_c": {t: (vol[t] is not None and vol[t] > 0)
                                       for t in TERRITORIES},
                  "D": vol}
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
def repeatability(d1, d2) -> dict:
    """F1's RC by JA42 steps 3-5. ``d1``, ``d2``: {territory: [D per case]} for the two reads
    (None where a case lacks the territory). Returns per-territory RC (the upper 95 % bound,
    plus offset when needed), the point estimates, n and every decision taken."""
    from scipy.stats import chi2, spearmanr

    def bound(sd, n):
        return sd * math.sqrt((n - 1) / chi2.ppf(0.025, n - 1))

    diffs, means = {}, {}
    for t in TERRITORIES:
        pairs = [(a, b) for a, b in zip(d1.get(t, []), d2.get(t, []))
                 if a is not None and b is not None]
        diffs[t] = np.array([a - b for a, b in pairs], float)
        means[t] = np.array([(a + b) / 2 for a, b in pairs], float)
    alld = np.concatenate([diffs[t] for t in TERRITORIES])
    allm = np.concatenate([means[t] for t in TERRITORIES])
    if len(alld) < 3:
        return {"status": "not_computed", "reason": f"{len(alld)} paired values"}
    decisions = []
    # log scale (India) if |Δ| grows with the level and every D is positive
    if np.ptp(allm) > 0 and np.ptp(np.abs(alld)) > 0:
        rho = float(spearmanr(np.abs(alld), allm).statistic)
    else:
        rho = float("nan")  # constant input: no trend to test
    log = bool(math.isfinite(rho) and rho > SPEARMAN_LOG)
    if log:
        pos = all((d1[t][i] or 0) > 0 and (d2[t][i] or 0) > 0
                  for t in TERRITORIES for i in range(len(d1.get(t, [])))
                  if d1[t][i] is not None and d2[t][i] is not None)
        if pos:
            for t in TERRITORIES:
                a = np.array([x for x, y in zip(d1[t], d2[t]) if x is not None and y is not None])
                b = np.array([y for x, y in zip(d1[t], d2[t]) if x is not None and y is not None])
                diffs[t] = np.log(a / b) if len(a) else np.zeros(0)
            alld = np.concatenate([diffs[t] for t in TERRITORIES])
            decisions.append(f"Spearman rho {rho:.3f} > {SPEARMAN_LOG}: RC on log ratios, "
                             "applied multiplicatively")
        else:
            log = False
            decisions.append(f"Spearman rho {rho:.3f} > {SPEARMAN_LOG}, but D is not positive "
                             "throughout: log ratios undefined, RC kept on differences")
    else:
        decisions.append(f"Spearman rho {rho:.3f} <= {SPEARMAN_LOG}: RC on differences")
    n_pool = len(alld)
    sd_pool = float(np.std(alld, ddof=1))
    pool_ub = bound(sd_pool, n_pool)
    out = {"scale": "log" if log else "difference", "spearman_rho": _r(rho),
           "pooled": {"sd": _r(sd_pool), "sd_upper95": _r(pool_ub), "n": n_pool}, "territory": {}}
    for t in TERRITORIES:
        dt = diffs[t]
        n_t = len(dt)
        sd_t = float(np.std(dt, ddof=1)) if n_t > 1 else float("nan")
        own = n_t >= RC_PER_TERRITORY_MIN_N
        use_own = own and math.isfinite(sd_t) and sd_t > pool_ub
        if not own:
            why = f"n_T {n_t} < {RC_PER_TERRITORY_MIN_N}: pooled"
        elif use_own:
            why = f"SD_T {sd_t:.4f} > pooled 95 % bound {pool_ub:.4f}: own"
        else:
            why = "SD_T within the pooled 95 % bound: pooled"
        sd, n, md = ((sd_t, n_t, float(dt.mean())) if use_own
                     else (sd_pool, n_pool, float(alld.mean())))
        rc_point = 1.96 * sd
        rc = 1.96 * bound(sd, n)
        if abs(md) > OFFSET_FRACTION * sd:
            rc += abs(md)
            why += f"; |mean diff| {abs(md):.4f} > {OFFSET_FRACTION} SD: added"
        out["territory"][t] = {"rc": _r(rc), "rc_point": _r(rc_point), "sd": _r(sd), "n": n,
                               "n_territory": n_t, "mean_diff": _r(md), "source":
                               "territory" if use_own else "pooled", "decision": why}
    out["decisions"] = decisions
    out["status"] = "computed"
    return out


def rc_abs(rc: dict, territory: str, level: float) -> float:
    """RC_T in the sign's own units. On the log scale (JA42 step 4, applied multiplicatively)
    it is (exp(RC) - 1) x the level it applies to."""
    v = float(rc["territory"][territory]["rc"])
    return (math.exp(v) - 1.0) * float(level) if rc.get("scale") == "log" else v


def cohen_kappa(a: Sequence[bool], b: Sequence[bool]) -> Optional[float]:
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = float(np.mean(a == b))
    pa, pb = a.mean(), b.mean()
    pe = float(pa * pb + (1 - pa) * (1 - pb))
    return None if pe >= 1 else (po - pe) / (1 - pe)


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


def read_agreement(reads: List[dict], cfg: dict) -> dict:
    """RC (first 20 entries) and κ / ICC (first 40) per sign from anonymous read pairs.

    ``reads``: decision cases in draw order, each ``{"read_1": features, "read_2": features}``
    (outputs of :func:`features.case_features` on the two accepted reads, no id). D uses the
    patient-specific map of each read (JA42 step 1); rule C flags use the AHA default map."""
    assert_anonymous(reads, "the read records")
    out: Dict[str, dict] = {}
    states = [(case_state(r["read_1"], cfg), case_state(r["read_2"], cfg)) for r in reads]
    for sign in SIGNS:
        rc_rows = [(a[sign], b[sign]) for a, b in states[:RC_CASES]
                   if a.get(sign) is not None and b.get(sign) is not None]
        d1 = {t: [a["D"][t] for a, _ in rc_rows] for t in TERRITORIES}
        d2 = {t: [b["D"][t] for _, b in rc_rows] for t in TERRITORIES}
        rc = repeatability(d1, d2)
        rc["n_cases"] = len(rc_rows)
        k_rows = [(a[sign], b[sign]) for a, b in states[:KAPPA_CASES]
                  if a.get(sign) is not None and b.get(sign) is not None]
        fa = [a["territory_rule_c"][t] for a, _ in k_rows for t in TERRITORIES]
        fb = [b["territory_rule_c"][t] for _, b in k_rows for t in TERRITORIES]
        if not fa:
            kap, kn = None, "no units"
        elif min(sum(fa), sum(fb)) < KAPPA_MIN_FLAGGED:
            kap, kn = None, (f"not estimable: a read has < {KAPPA_MIN_FLAGGED} flagged units "
                             f"({sum(fa)}, {sum(fb)})")
        else:
            kap, kn = cohen_kappa(fa, fb), "estimated"
        xs = [(a["D"][t], b["D"][t]) for a, b in k_rows for t in TERRITORIES
              if a["D"][t] is not None and b["D"][t] is not None]
        icc = icc_2_1([p[0] for p in xs], [p[1] for p in xs]) if xs else None
        out[sign] = {"rc": rc, "kappa": _r(kap), "kappa_status": kn, "icc": _r(icc),
                     "n_units": len(fa)}
    return out


# --------------------------------------------------------------------------------------- gate
def gate(sign: str, cfg: dict, agreement: dict, *, seed: int = SEED, sig_m: float = 0.0) -> dict:
    """JA41 for one sign. Depth (thinning, hypoattenuation) at the population's cv_n and shape,
    the conservative RC (the largest territory RC) and the population's median level."""
    blk = cfg[sign]
    ag = agreement.get(sign) or {}
    rc = ag.get("rc") or {}
    has_rc = rc.get("status") == "computed"
    g = {"kappa": ag.get("kappa"), "kappa_status": ag.get("kappa_status"), "icc": ag.get("icc"),
         "depth": None, "rc_terr_for_depth": None}
    if sign == "fat":
        has_cut = blk.get("rule") in ("grid", "patient_noise")
        g["pass"] = bool(has_cut and has_rc)
        g["why"] = "fat: cut and F1 (JA41; no depth gate)"
        return g
    if blk.get("cut") is None or not has_rc:
        g["pass"] = False
        g["why"] = "no cut" if blk.get("cut") is None else "no RC (F1)"
        return g
    rc_mm = max(rc_abs(rc, t, blk["median_level"]) for t in TERRITORIES)
    dd = calibrate.detectable_depth(blk["cv_n"], np.asarray(blk["shape"], float), rc_mm,
                                    sig_m=sig_m, seed=seed, median_mm=blk["median_level"])
    g.update(depth=dd["depth"], sens_range=dd["sens_range"], false_flag=dd["false_flag"],
             rc_terr_for_depth=_r(rc_mm), depth_seed=int(seed))
    g["pass"] = bool(dd["depth"] is not None and dd["depth"] <= DEPTH_GATE)
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
        "model": model, "guard_mm": float(guard_mm),
        "cases_sha256": cases_sha, "splits_sha256_prefix": guard.PINNED[guard.SPLITS_RELPATH][:12],
        "n_cases": int(n_cases), "n_usable": cfg.pop("n_usable"), "excluded": cfg.pop("excluded"),
        "label": LABEL, "seed": int(seed),
        "thinning": cfg["thinning"], "hypoattenuation": cfg["hypoattenuation"], "fat": cfg["fat"],
        "percentiles": {"thickness_mm": cfg.pop("thinning_percentiles"),
                        "rel_subendo_hu": cfg.pop("hypoattenuation_percentiles")},
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
