"""One power script for the JA32 endpoints (Round 2 paired-scar ruling, JA28, JA32; JA35 item 4).

Ruling: ``vault/JanusM/Judgements/Round 2 - paired-scar.md``. It replaces the three Round 2 scripts,
``experiments/JanusM/{Golf,Kilo,Juliet}/...power.py``, which stay as the record:

* the cohort is Golf's patient-clustered study (:func:`golf_cohort`): a share ``enrich`` of
  patients has K ~ 1 + Poisson(lam) contiguous scarred segments, detected with a per-bin
  sensitivity, scar-free segments falsely called with 1 - spec, and a patient random effect (logit
  SD ``tau``) on both;
* the endpoints are JA32's: segment sensitivity >= 0.75, specificity >= 0.93, and Kilo's
  transmurality agreement (exact Kim bin among segments scar on both) >= the LGE inter-reader
  anchor - 0.10, all on the 95 % patient-bootstrap lower bound, one look; kappa is reported only;
* every simulated study is scored by :mod:`janusm.scar.scoring`, the harness the seal will be
  scored by, including intention-to-diagnose: a patient whose registration fails (probability
  ``p_fail``) has every segment counted wrong (JA29).

Two additions to Golf's model, both off when reproducing Golf (``bin_tau=0, p_fail=0``):

* ``bin_tau``: the patient effect also moves the bin-error rate, logit(q_i) = logit(q) + bin_tau *
  b_i, so a poor scan grades worse as well as detecting worse (Kilo's per-patient grading offset,
  in Golf's terms);
* ``p_fail``: the intention-to-diagnose registration failure rate.

**Reproduction.** :func:`kilo_cohort` and :func:`juliet_cohort` port Kilo's and Juliet's
generators, and :data:`ROUND2_RECORD` holds the Round 2 numbers each script committed.
``tests/test_janusm_scar_power.py`` re-runs every recorded cell through this one engine and checks
it within Monte-Carlo error.

**Seal size** (:func:`seal_size`): the smallest N at >= 80 % power for all deciding JA32 endpoints
jointly (JA28), then JA28's floor: >= 120 patients and >= 270 scarred segments, whichever needs
more.

Usage::

    python -m janusm.scar.power --out ja32_power.json [--sims 400 --boot 400]

Simulation only: no image, case or identifier is read or written.
"""

from __future__ import annotations

import argparse
import json
import math
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from janusm.scar import scoring as S

# -------------------------------------------------------------------------------------------------
# Cohort generators. Each returns (ref, ct): (N, segments) Kim bins; ct may hold S.NOT_GRADED.

GOLF_SENS_BY_BIN = (0.70, 0.88, 0.93, 0.97)
GOLF_BIN_W = (0.30, 0.25, 0.25, 0.20)


def _logit(p):
    return np.log(p / (1 - p))


def _expit(x):
    return 1 / (1 + np.exp(-x))


def golf_cohort(
    rng: np.random.Generator,
    n: int,
    enrich: float = 0.5,
    lam: float = 3.0,
    tau: float = 0.7,
    q: float = 0.25,
    spec: float = 0.98,
    sens_by_bin: Sequence[float] = GOLF_SENS_BY_BIN,
    bin_w: Sequence[float] = GOLF_BIN_W,
    segments: int = 16,
    bin_tau: float = 0.0,
    p_fail: float = 0.0,
):
    """Golf R2 E6's cohort (``Golf/cohort_power.py``), vectorised, plus ``bin_tau``, ``p_fail``."""
    ref = np.zeros((n, segments), int)
    b = rng.normal(0, tau, (n, 1))
    for i in np.flatnonzero(rng.random(n) < enrich):
        k = min(1 + rng.poisson(lam), segments)
        idx = (rng.integers(segments) + np.arange(k)) % segments
        ref[i, idx] = rng.choice([1, 2, 3, 4], size=k, p=list(bin_w))
    shape = (n, segments)
    sens = np.clip(np.array((0.0,) + tuple(sens_by_bin))[ref], 1e-9, 1 - 1e-9)
    false_call = rng.random(shape) < _expit(_logit(1 - spec) + b)
    false_bin = np.where(rng.random(shape) < 0.7, 1, 2)
    detected = rng.random(shape) < _expit(_logit(sens) - b)
    qi = _expit(_logit(q) + bin_tau * b) if 0 < q < 1 else np.full((n, 1), q)
    off = rng.random(shape) < qi
    step = np.where(rng.random(shape) < 0.5, -1, 1)
    graded = np.where(off, np.clip(ref + step, 1, 4), ref)
    ct = np.where(ref == 0, np.where(false_call, false_bin, 0), np.where(detected, graded, 0))
    if p_fail > 0:
        ct[rng.random(n) < p_fail] = S.NOT_GRADED
    return ref, ct


# Kilo v2 E6 (``Kilo/e6_power.py``): standard AHA map, 0-based, and its calibrated constants.
KILO_TERR = {"LAD": [0, 1, 6, 7, 12, 13, 16], "RCA": [2, 3, 8, 9, 14], "LCX": [4, 5, 10, 11, 15]}
KILO_TERR_P = {"LAD": 0.5, "RCA": 0.3, "LCX": 0.2}
KILO_DET_A, KILO_DET_B, KILO_FP_C, KILO_SD_U = -0.2, 5.0, -4.3, 0.8
KILO_EDGES = np.array([0.25, 0.50, 0.75])


def _kilo_bins(t, present):
    return np.where(present, np.digitize(np.clip(t, 1e-9, 1.0), KILO_EDGES) + 1, 0)


def kilo_cohort(
    rng: np.random.Generator, n: int, q: float = 0.7, sd_s: float = 0.13, sd_p: float = 0.05
):
    """Kilo R2 E6's cohort: continuous LGE transmurality, detection rising with it, 17 segments."""
    t = np.zeros((n, 17))
    names = list(KILO_TERR)
    for i in np.flatnonzero(rng.random(n) < q):
        terr = KILO_TERR[rng.choice(names, p=[KILO_TERR_P[k] for k in names])]
        k = 1 + rng.binomial(len(terr) - 1, 0.45)
        seg = rng.choice(terr, size=k, replace=False)
        t[i, seg] = rng.beta(1.6, 1.6, size=k).clip(0.02, 1.0)
    u = rng.normal(0, KILO_SD_U, (n, 1))
    pos = t > 0
    p_call = np.where(pos, _expit(KILO_DET_A + KILO_DET_B * t + u), _expit(KILO_FP_C + u))
    det = rng.random((n, 17)) < p_call
    graded = t + rng.normal(0, sd_p, (n, 1)) + rng.normal(0, sd_s, (n, 17))
    graded = np.where(pos, graded, rng.beta(1, 6, (n, 17))).clip(0.01, 1.0)
    return _kilo_bins(t, pos), _kilo_bins(graded, det)


# Juliet v2 E5 (``Juliet/cohort_power.py``): 1-based AHA map, as Juliet wrote it.
JULIET_TERR = {"LAD": [1, 2, 7, 8, 13, 14, 17], "RCA": [3, 4, 9, 10, 15], "LCx": [5, 6, 11, 12, 16]}
JULIET_BIN_W = (0.30, 0.25, 0.20, 0.25)
JULIET_SCEN = {
    "published": {"sens": 0.86, "spec": 0.98, "p_bin": 0.65},
    "weak": {"sens": 0.72, "spec": 0.95, "p_bin": 0.45},
}


def juliet_cohort(
    rng: np.random.Generator,
    n: int,
    f_mi: float = 0.5,
    sens: float = 0.86,
    spec: float = 0.98,
    p_bin: float = 0.65,
):
    """Juliet R2 E5's cohort: one territorial patch, 10 % unrecognised scar, one patient effect."""
    ref = np.zeros((n, 17), int)
    ct = np.zeros((n, 17), int)
    names = list(JULIET_TERR)
    for i in range(n):
        if rng.random() < f_mi:
            k = rng.integers(2, 8)
        elif rng.random() < 0.10:
            k = rng.integers(2, 4)
        else:
            k = 0
        if k:
            segs = JULIET_TERR[rng.choice(names)]
            k = min(k, len(segs))
            start = rng.integers(len(segs))
            for s in [segs[(start + j) % len(segs)] for j in range(k)]:
                ref[i, s - 1] = rng.choice(4, p=list(JULIET_BIN_W)) + 1
        z = rng.normal()
        se, sp = _expit(_logit(sens) + 0.8 * z), _expit(_logit(spec) + 0.8 * z)
        for j, t in enumerate(ref[i]):
            if t:
                if rng.random() < se:
                    v = rng.random()
                    if v < p_bin:
                        ct[i, j] = t
                    else:
                        step = 1 if v < p_bin + 0.8 * (1 - p_bin) else 2
                        ct[i, j] = int(np.clip(t + step * rng.choice([-1, 1]), 1, 4))
            elif rng.random() > sp:
                ct[i, j] = 1 if rng.random() < 0.8 else 2
    return ref, ct


GENERATORS: Dict[str, Callable] = {
    "golf": golf_cohort,
    "kilo": kilo_cohort,
    "juliet": juliet_cohort,
}

# -------------------------------------------------------------------------------------------------
# The engine


def simulate_studies(
    generator: Callable, n: int, sims: int, boot: int, seed: int, **params
) -> Dict:
    """Simulate ``sims`` studies of ``n`` patients; score each with the harness's cluster bootstrap.

    Returns per-study arrays: ``lower``, ``upper`` and ``point`` per endpoint, and
    ``scar_segments``.
    """
    rng = np.random.default_rng(seed)
    lower = {k: np.empty(sims) for k in S.ENDPOINTS}
    upper = {k: np.empty(sims) for k in S.ENDPOINTS}
    point = {k: np.empty(sims) for k in S.ENDPOINTS}
    scar = np.empty(sims)
    for r in range(sims):
        ref, ct = generator(rng, n, **params)
        stats = S.patient_stats(ref, S.intention_to_diagnose(ref, ct))
        ci = S.cluster_bootstrap(stats, boot, rng)
        for k in S.ENDPOINTS:
            lower[k][r], upper[k][r], point[k][r] = ci[k]["lower"], ci[k]["upper"], ci[k]["point"]
        scar[r] = (ref > 0).sum()
    return {"lower": lower, "upper": upper, "point": point, "scar_segments": scar}


def power_from(studies: Mapping, bars: Mapping[str, Optional[float]]) -> Dict:
    """Per-endpoint and joint power: the share of studies whose lower bounds clear each bar."""
    deciding = {k: b for k, b in bars.items() if b is not None}
    hit = {k: np.nan_to_num(studies["lower"][k], nan=-np.inf) >= b for k, b in deciding.items()}
    joint = np.logical_and.reduce(list(hit.values())) if hit else None
    return {
        "bars_lower95": dict(bars),
        "power": {k: float(v.mean()) for k, v in hit.items()},
        "power_all": float(joint.mean()) if hit else float("nan"),
    }


def summarise(studies: Mapping) -> Dict:
    """Median point estimates and CI half-widths, and the mean scarred segments per study."""
    half = {
        k: float(np.nanmedian((studies["upper"][k] - studies["lower"][k]) / 2)) for k in S.ENDPOINTS
    }
    return {
        "point_median": {k: float(np.nanmedian(v)) for k, v in studies["point"].items()},
        "ci_halfwidth_median": half,
        "mean_scar_segments": float(studies["scar_segments"].mean()),
    }


def expected_scar_segments(enrich: float, lam: float, segments: int = 16) -> float:
    """Expected scarred segments per Golf patient: enrich * E[min(1 + Poisson(lam), S)]."""
    ks = np.arange(segments)  # Poisson values 0 .. S-1; anything larger is capped at S
    if lam > 0:
        pmf = np.exp(-lam + ks * math.log(lam) - np.array([math.lgamma(k + 1) for k in ks]))
    else:
        pmf = np.r_[1.0, np.zeros(segments - 1)]
    e_k = float(((ks + 1) * pmf).sum() + segments * (1 - pmf.sum()))
    return enrich * e_k


def patients_for_segments(n_segments: int, enrich: float, lam: float, segments: int = 16) -> int:
    """Patients needed for an expected ``n_segments`` scarred segments (JA28's >= 270)."""
    return int(math.ceil(n_segments / expected_scar_segments(enrich, lam, segments)))


def seal_size(
    power_by_n: Mapping[int, float],
    enrich: float,
    lam: float,
    target: float = 0.80,
    min_patients: int = 120,
    min_segments: int = 270,
) -> Dict[str, Optional[int]]:
    """JA28's seal size from a joint-power curve: max(power-N, 120, the >= 270-segment N).

    ``power-N`` is the smallest N in the grid from which joint power stays >= ``target``; None if
    the grid never gets there, and then the seal size is None too (no N in the grid suffices).
    """
    ns = sorted(power_by_n)
    n_power = None
    for i, n in enumerate(ns):
        if all(power_by_n[m] >= target for m in ns[i:]):
            n_power = n
            break
    n_seg = patients_for_segments(min_segments, enrich, lam)
    seal = None if n_power is None else max(n_power, min_patients, n_seg)
    return {"n_power": n_power, "n_segments_270": n_seg, "n_floor": min_patients, "seal": seal}


# -------------------------------------------------------------------------------------------------
# What Round 2 recorded, for the reproduction check. Each cell names the script, its parameters,
# the bars that script used and the joint pass rate it committed (``power``, from ``sims`` studies).

GOLF_BARS = {"sens": 0.75, "spec": 0.93, "kappa_linear": 0.60}
KILO_BARS = {"sens": 0.75}
JULIET_BARS = {"kappa_quadratic": 0.60, "sens": 0.70, "spec": 0.90}
_GOLF_BASE = {"enrich": 0.5, "lam": 3.0, "tau": 0.7, "q": 0.25}

ROUND2_RECORD: List[Dict] = [
    # Golf/cohort_power.json (sims 400, boot 400): the base, the clustering stress, 30 % enrichment
    {"script": "golf", "n": 80, "params": _GOLF_BASE, "bars": GOLF_BARS, "power": 0.80,
     "sims": 400},
    {"script": "golf", "n": 120, "params": _GOLF_BASE, "bars": GOLF_BARS, "power": 0.8875,
     "sims": 400},
    {"script": "golf", "n": 120, "params": {**_GOLF_BASE, "tau": 1.2}, "bars": GOLF_BARS,
     "power": 0.57, "sims": 400},
    {"script": "golf", "n": 120, "params": {**_GOLF_BASE, "enrich": 0.3}, "bars": GOLF_BARS,
     "power": 0.7825, "sims": 400},
    # Kilo/results_e6_power.json (sims 200, boot 200): P(sens lb > 0.75) at sd_s 0.13
    {"script": "kilo", "n": 60, "params": {"q": 0.7, "sd_s": 0.13}, "bars": KILO_BARS,
     "power": 0.72, "sims": 200},
    {"script": "kilo", "n": 120, "params": {"q": 0.7, "sd_s": 0.13}, "bars": KILO_BARS,
     "power": 0.95, "sims": 200},
    # Juliet/e5_cohort_power.json (300 cohorts, B 400): the published and the weak pipeline
    {"script": "juliet", "n": 60, "params": {"f_mi": 0.5, **JULIET_SCEN["published"]},
     "bars": JULIET_BARS, "power": 0.927, "sims": 300},
    {"script": "juliet", "n": 120, "params": {"f_mi": 0.5, **JULIET_SCEN["weak"]},
     "bars": JULIET_BARS, "power": 0.03, "sims": 300},
]  # fmt: skip
# Kilo/results_e6_power.json "calibration": transmurality agreement of a 20 000-patient cohort
KILO_TBIN_RECORD = {0.08: 0.734, 0.13: 0.63, 0.20: 0.52}


def reproduce(sims: int, boot: int, seed: int = 182) -> List[Dict]:
    """Re-run every :data:`ROUND2_RECORD` cell through this engine; report it beside the record."""
    out = []
    for i, cell in enumerate(ROUND2_RECORD):
        gen = GENERATORS[cell["script"]]
        st = simulate_studies(gen, cell["n"], sims, boot, seed + i, **cell["params"])
        p = power_from(st, cell["bars"])["power_all"]
        rec = cell["power"]
        var = max(rec * (1 - rec), 0.25 / sims)  # floor keeps z finite for a recorded 0 or 1
        se = math.sqrt(var * (1 / cell["sims"] + 1 / sims))
        out.append(
            {
                **{k: cell[k] for k in ("script", "n", "params", "bars")},
                "recorded": rec,
                "reproduced": p,
                "mc_se": se,
                "z": (p - rec) / se,
            }
        )
    return out


# -------------------------------------------------------------------------------------------------
# The JA32 study

JA32_BASE = {"lam": 3.0, "q": 0.25, "spec": 0.98, "bin_tau": 1.0}
# patient logit SD: Golf's base (Kilo and Juliet used 0.8) and Golf's stress
CLUSTERING = {"weak": 0.7, "strong": 1.2}
ENRICH = (0.5, 0.7)
P_FAIL = (0.0, 0.02, 0.05)  # JA29 intention-to-diagnose: whole-patient registration failure
ANCHORS = (0.60, 0.70, 0.80)  # development LGE inter-reader agreement; none is sourced yet
N_GRID = (60, 80, 100, 120, 140, 160, 180, 200, 240, 280, 320)


def ja32_study(
    sims: int,
    boot: int,
    seed: int = 32,
    n_grid: Iterable[int] = N_GRID,
    anchors: Iterable[float] = ANCHORS,
    log: Optional[Callable] = None,
) -> Dict:
    """Power and seal size at the JA32 bars over clustering, enrichment, failure rate and anchor.

    The anchor ``None`` row is the case JA32 provides for an anchor < 0.60: transmurality reported
    only, presence decides.
    """
    levels = list(anchors) + [None]
    n_grid = list(n_grid)
    rows, seals = [], []
    cell = 0
    for cl, tau in CLUSTERING.items():
        for enrich in ENRICH:
            for p_fail in P_FAIL:
                where = {"clustering": cl, "tau": tau, "enrich": enrich, "p_fail": p_fail}
                curves = {a: {} for a in levels}
                for n in n_grid:
                    params = {**JA32_BASE, "tau": tau, "enrich": enrich, "p_fail": p_fail}
                    st = simulate_studies(golf_cohort, n, sims, boot, seed + cell, **params)
                    cell += 1
                    summ = summarise(st)
                    for a in levels:
                        pw = power_from(st, S.bars(a))
                        curves[a][n] = pw["power_all"]
                        rows.append({**where, "anchor": a, "n": n, **pw, **summ})
                    if log:
                        tb = summ["point_median"]["tbin"]
                        pws = " ".join(f"P[{a}]={curves[a][n]:.3f}" for a in levels)
                        log(f"{cl} enrich={enrich} p_fail={p_fail} n={n} tbin={tb:.3f} {pws}")
                for a in levels:
                    size = seal_size(curves[a], enrich, JA32_BASE["lam"])
                    seals.append({**where, "anchor": a, **size})
    return {
        "assumptions": {
            "cohort": "golf",
            **JA32_BASE,
            "sens_by_bin": GOLF_SENS_BY_BIN,
            "bin_weights_1_4": GOLF_BIN_W,
            "segments": 16,
            "clustering_tau": CLUSTERING,
            "enrich": ENRICH,
            "p_fail": P_FAIL,
            "anchors": list(anchors),
            "bars": {
                "sens": S.SENS_BAR,
                "spec": S.SPEC_BAR,
                "tbin": f"anchor - {S.TBIN_MARGIN}; reported only if anchor < {S.MIN_ANCHOR}",
            },
            "anchor_none": "anchor < 0.60: transmurality reported only, presence decides",
            "power_target_joint": 0.80,
            "sims": sims,
            "boot": boot,
            "seed": seed,
        },
        "patients_for_270_segments": {
            str(e): patients_for_segments(270, e, JA32_BASE["lam"]) for e in ENRICH
        },
        "grid": rows,
        "seal_size": seals,
    }


def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="One power script for the JA32 endpoints (JA35 4).")
    ap.add_argument("--out", required=True, help="JSON output path")
    ap.add_argument("--sims", type=int, default=400)
    ap.add_argument("--boot", type=int, default=400)
    ap.add_argument("--seed", type=int, default=32)
    a = ap.parse_args(argv)
    res = {"reproduction": reproduce(a.sims, a.boot)}
    for r in res["reproduction"]:
        print(
            f"reproduce {r['script']} n={r['n']}: recorded {r['recorded']:.3f}, "
            f"now {r['reproduced']:.3f} (z {r['z']:+.2f})",
            flush=True,
        )
    res.update(ja32_study(a.sims, a.boot, a.seed, log=lambda s: print(s, flush=True)))
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
