"""Janus-M detectable depth (JA40): how deep a territory must thin before rule C flags it.

One procedure, fixed by JA40 (``vault/JanusM/Judgements/Round 3 - rest-ccta.md`` on
``jm/rest-ccta``): Hotel's E7 loop (``experiments/JanusM/Hotel/r3/e7_detectable.py``) on Lima's
simulation (``experiments/JanusM/Lima/calibrate_sim.py``). No image is opened; it is a simulation
of 16 segment thicknesses per heart.

**The population (Lima).** Per heart, segment thickness =
``median_mm * scale * phase * shape_s * exp(noise) * (1 - depth if thinned) + error``:

- ``scale``: lognormal patient size, CV 0.12;
- ``phase``: end-diastole 1.00, mid-diastole 1.14, systole 1.40, mixed 40 / 40 / 20 (JA40);
- ``shape``: the normal 16-segment pattern relative to the patient's median;
- ``noise``: normal segment-to-segment variation, SD ``cv_n``. JA40: the **plain SD** of thickness
  divided by shape (JM-0R's ``cv_n_shape_corrected_sd``), never India's robust log SD;
- a share ``PREVALENCE`` (0.1) of hearts have 2-4 contiguous thinned segments in one territory;
- ``error``: added measurement error, SD ``sig_m`` mm. JA40: 0 when ``cv_n`` was measured on the
  borders of the model that fills the table (it already holds that model's error).

**Rule C (Lima).** z = (thickness / patient median - population shape) / per-segment robust scale;
a segment is flagged below a cut set on a mirror null so that <= 5 % of null hearts have a flagged
territory (``calibrate_c``); a territory is flagged when two contiguous segments in it are.

**F1 floor (Hotel).** A territory flag shows only if the territory's shape-corrected mean thinning
against the patient's remote segments exceeds ``rc_terr_mm`` (1.0 mm until the reads exist, then
JA42's RC).

**The read-out (Hotel E7, JA40).** 4 replicate populations of 2000 per depth, depths 0.10-0.60 in
0.05 steps; the detectable depth is the smallest depth whose mean territory sensitivity is >= 0.80.
Being on the 0.05 grid, it is rounded **up** to 0.05. With the default ``seed`` the seeds are E7's,
so its primary rows (cv_n 0.088, Lima's shape and median) come back exactly: 0.30 at RC 0 and 0.35
at RC 1.0.
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence

import numpy as np

#: Bump on any change that can move a reported number.
CALIBRATE_VERSION = "1.0.0"

# AHA default territories and bullseye adjacency (Lima's calibrate_sim)
AHA = {"LAD": [1, 2, 7, 8, 13, 14, 17], "RCA": [3, 4, 9, 10, 15], "LCx": [5, 6, 11, 12, 16]}
RING = {
    1: [2, 6, 7], 2: [1, 3, 8], 3: [2, 4, 9], 4: [3, 5, 10], 5: [4, 6, 11], 6: [5, 1, 12],
    7: [8, 12, 1, 13], 8: [7, 9, 2, 13, 14], 9: [8, 10, 3, 14, 15], 10: [9, 11, 4, 15],
    11: [10, 12, 5, 15, 16], 12: [11, 7, 6, 16, 13], 13: [14, 16, 7, 8, 12], 14: [13, 15, 8, 9],
    15: [14, 16, 9, 10, 11], 16: [15, 13, 11, 12],
}  # fmt: skip
TERR16 = {t: [s for s in v if s <= 16] for t, v in AHA.items()}
TERRITORIES = list(TERR16)

#: Lima's self-test on 23 public hearts (1.5 mm model-made labels;
#: ``experiments/JanusM/Lima/local_check_summary.json``): the only measured inputs before JM-0R.
LIMA_SHAPE = (
    1.015, 1.288, 1.171, 0.971, 0.982, 1.120, 0.910, 1.121,
    1.276, 1.022, 0.916, 1.074, 0.777, 0.825, 0.756, 0.819,
)  # fmt: skip
LIMA_CV_N = 0.088
LIMA_MEDIAN_MM = 9.668

PHASES = {"ED": 1.00, "MD": 1.14, "SYS": 1.40}
PHASE_MIX = {"ED": 0.4, "MD": 0.4, "SYS": 0.2}  # JA40
SCALE_CV = 0.12
PREVALENCE = 0.1  # JA40
N_PER_POPULATION = 2000  # JA40
REPLICATES = 4  # JA40
DEPTHS = tuple(round(0.10 + 0.05 * i, 2) for i in range(11))  # 0.10 .. 0.60
SENSITIVITY_TARGET = 0.80
FALSE_FLAG_TARGET = 0.05  # rule C's mirror-null calibration
NULL_HEARTS = 20000
RC_TERR_PROVISIONAL_MM = 1.0  # JA40: the F1 floor until the reads exist
DEPTH_WARN = 0.40  # JA40: above this the page says so
DEFAULT_SEED = 31000  # Hotel E7's first seed: its primary rows reproduce exactly


# ---------------------------------------------------------------------------------- population
def population(
    n: int,
    prev: float,
    depth: float,
    cv_n: float,
    sig_m: float,
    phase_mix: Mapping[str, float],
    rng,
    *,
    shape: Sequence[float] = LIMA_SHAPE,
    median_mm: float = LIMA_MEDIAN_MM,
):
    """Lima's simulated population: (measured n x 16 mm, lesion n x 16, sick n, territory n,
    phase n). The draws are made in Lima's order, so a seed gives Lima's and Hotel's hearts."""
    shape = np.asarray(shape, float)
    scale = median_mm * np.exp(rng.normal(0, SCALE_CV, n))
    ph_names = rng.choice(list(PHASES), size=n, p=[phase_mix[k] for k in PHASES])
    ph = np.array([PHASES[k] for k in ph_names])
    true = scale[:, None] * ph[:, None] * shape[None, :] * np.exp(rng.normal(0, cv_n, (n, 16)))
    sick = rng.random(n) < prev
    lesion = np.zeros((n, 16), bool)
    terr = np.array([None] * n, object)
    for i in np.nonzero(sick)[0]:
        t = rng.choice(TERRITORIES)
        seed = rng.choice(TERR16[t])
        k = rng.integers(2, 5)
        segs = {seed}
        while len(segs) < min(k, len(TERR16[t])):
            nb = [x for s in segs for x in RING[s] if x in TERR16[t] and x not in segs]
            if not nb:
                break
            segs.add(rng.choice(nb))
        lesion[i, [s - 1 for s in segs]] = True
        terr[i] = t
    true = np.where(lesion, true * (1 - depth), true)
    meas = true + rng.normal(0, sig_m, (n, 16))
    return meas, lesion, sick, terr, ph_names


def territory_flags(flag) -> np.ndarray:
    """n x 16 segment flags -> n x 3 territory flags (LAD, RCA, LCx): two flagged, contiguous
    segments in the territory."""
    flag = np.asarray(flag, bool)
    out = np.zeros((flag.shape[0], 3), bool)
    for j, segs in enumerate(TERR16.values()):
        for s in segs:
            nbs = [x for x in RING[s] if x in segs]
            out[:, j] |= flag[:, s - 1] & flag[:, [x - 1 for x in nbs]].any(1)
    return out


def rule_c_scores(meas) -> np.ndarray:
    """Lima's rule C score per segment: (thickness / patient median - population shape) over a
    per-segment robust scale from the right half (which thinning cannot reach)."""
    rel = meas / np.median(meas, 1, keepdims=True)
    shape = np.median(rel, 0)  # learned from the unlabelled population itself
    z = rel - shape
    scale = np.array([1.4826 * np.median(np.abs(c[c >= 0])) for c in z.T])
    return z / scale


def calibrate_c(z, target: float = FALSE_FLAG_TARGET, rng=None):
    """(cut, k): the rule C cut so that <= ``target`` of null hearts have a flagged territory. The
    null is the mirror of the pooled scores' right half about their median; null hearts are
    ``NULL_HEARTS`` draws of 16 segments from it. No label is used."""
    rng = rng if rng is not None else np.random.default_rng(0)
    z = np.ravel(z)
    med = np.median(z)
    right = z[z >= med] - med
    pool = np.r_[med + right, med - right]
    null = rng.choice(pool, (NULL_HEARTS, 16))
    mad = 1.4826 * np.median(right)
    for k in np.arange(1.0, 6.01, 0.05):
        if territory_flags(null < med - k * mad).any(1).mean() <= target:
            return med - k * mad, float(k)
    return med - 6 * mad, 6.0


def f1_deviation(meas, shape) -> np.ndarray:
    """Hotel's F1 deviation, n x 3 (mm, + = thinner than expected): each territory's mean
    shape-corrected thinning against the patient's remote level (the median of the segments
    outside it, shape-corrected)."""
    meas = np.asarray(meas, float)
    shape = np.asarray(shape, float)
    out = np.zeros((meas.shape[0], 3))
    for j, t in enumerate(TERRITORIES):
        segs = [s - 1 for s in TERR16[t]]
        rem = [s for s in range(16) if s not in segs]
        level = np.median(meas[:, rem] / shape[rem], 1)
        out[:, j] = (level[:, None] * shape[segs] - meas[:, segs]).mean(1)
    return out


def simulate(
    depth: float,
    cv_n: float,
    shape: Sequence[float],
    rcs: Sequence[float],
    seed: int,
    *,
    sig_m: float = 0.0,
    median_mm: float = LIMA_MEDIAN_MM,
    prev: float = PREVALENCE,
    phase_mix: Mapping[str, float] = PHASE_MIX,
    n: int = N_PER_POPULATION,
) -> dict:
    """One population (Hotel E7's ``one``): {"k_mad": k, rc: {"false_flag", "sens"}} for each F1
    floor in ``rcs``. ``false_flag`` is the share of infarct-free hearts with any shown flag;
    ``sens`` the share of infarcted hearts whose infarct territory shows a flag."""
    shape = np.asarray(shape, float)
    rng = np.random.default_rng(seed)
    meas, _, sick, terr, _ = population(
        n, prev, depth, cv_n, sig_m, phase_mix, rng, shape=shape, median_mm=median_mm
    )
    z = rule_c_scores(meas)
    cut, k = calibrate_c(z, rng=np.random.default_rng(seed + 1))
    tf = territory_flags(z < cut)
    dev = f1_deviation(meas, shape)
    sick_idx = np.nonzero(sick)[0]
    out: dict = {"k_mad": k}
    for rc in rcs:
        f = tf & (dev > rc)
        hit = np.array([f[i, TERRITORIES.index(terr[i])] for i in sick_idx])
        out[float(rc)] = {
            "false_flag": float(f.any(1)[~sick].mean()),
            "sens": float(hit.mean()) if len(hit) else float("nan"),
        }
    return out


# ---------------------------------------------------------------------------------- read-out
def _check_inputs(cv_n, shape, rcs, sig_m):
    shape = np.asarray(shape, float)
    if shape.shape != (16,) or not np.all(np.isfinite(shape)) or (shape <= 0).any():
        raise ValueError("shape must be 16 positive segment ratios (segments 1-16)")
    if not np.isfinite(cv_n) or cv_n < 0:
        raise ValueError(f"bad cv_n {cv_n}")
    if sig_m < 0 or any((not np.isfinite(r)) or r < 0 for r in rcs):
        raise ValueError("sig_m and rc_terr_mm must be >= 0")
    if cv_n == 0 and sig_m == 0:
        raise ValueError(
            "cv_n and sig_m are both 0: the population has no normal variation, so rule C has "
            "no scale and the detectable depth is undefined"
        )
    return shape


def detectable_depths(
    cv_n: float,
    shape: Sequence[float],
    rc_terr_mm: Sequence[float],
    *,
    sig_m: float = 0.0,
    seed: int = DEFAULT_SEED,
    median_mm: float = LIMA_MEDIAN_MM,
) -> Dict[float, dict]:
    """``detectable_depth`` for several F1 floors on the same populations (as E7 swept them):
    {rc: result}. Each population is simulated once and read at every floor."""
    rcs = [float(r) for r in np.atleast_1d(rc_terr_mm)]
    shape = _check_inputs(cv_n, shape, rcs, sig_m)
    rows = []
    s = seed
    for depth in DEPTHS:
        reps = []
        for _ in range(REPLICATES):
            s += 2  # E7's seed sequence: population seed s, null seed s + 1
            reps.append(simulate(depth, cv_n, shape, rcs, s, sig_m=sig_m, median_mm=median_mm))
        rows.append((depth, reps))
    out = {}
    for rc in rcs:
        table = [
            {
                "depth": depth,
                "sens": [r[rc]["sens"] for r in reps],
                "false_flag": [r[rc]["false_flag"] for r in reps],
                "k_mad": [r["k_mad"] for r in reps],
            }
            for depth, reps in rows
        ]
        hit = [t for t in table if np.mean(t["sens"]) >= SENSITIVITY_TARGET]
        first = hit[0] if hit else None
        out[rc] = {
            "depth": first["depth"] if first else None,  # None: not reached by 0.60
            "sens_range": [min(first["sens"]), max(first["sens"])] if first else None,
            "false_flag": max(max(t["false_flag"]) for t in table),
            "inputs": {
                "cv_n": float(cv_n),
                "shape": [float(x) for x in shape],
                "rc_terr_mm": rc,
                "sig_m": float(sig_m),
                "median_mm": float(median_mm),
                "seed": int(seed),
            },
            "design": {
                "phase_mix": dict(PHASE_MIX),
                "prevalence": PREVALENCE,
                "n_per_population": N_PER_POPULATION,
                "replicates": REPLICATES,
                "depths": list(DEPTHS),
                "sensitivity_target": SENSITIVITY_TARGET,
            },
            "table": table,
            "calibrate_version": CALIBRATE_VERSION,
        }
    return out


def detectable_depth(
    cv_n: float,
    shape: Sequence[float],
    rc_terr_mm: float,
    *,
    sig_m: float = 0.0,
    seed: int = DEFAULT_SEED,
    median_mm: float = LIMA_MEDIAN_MM,
) -> dict:
    """JA40's detectable depth: the smallest relative thinning (0.10-0.60, 0.05 steps, so rounded
    up to 0.05) whose mean territory sensitivity over 4 populations of 2000 is >= 0.80.

    Returns ``depth`` (None if 0.60 is not enough), ``sens_range`` (the replicates' min and max at
    that depth), ``false_flag`` (the largest share of infarct-free hearts with a shown flag over
    every depth and replicate), the inputs, the design and the per-depth table.

    ``cv_n`` is the plain SD of thickness / shape; ``shape`` the 16 segment ratios;
    ``rc_terr_mm`` the F1 floor; ``sig_m`` the error to add (0 when ``cv_n`` was measured on the
    borders of the model that fills the table, JA40); ``median_mm`` the population's median wall."""
    return detectable_depths(
        cv_n, shape, [rc_terr_mm], sig_m=sig_m, seed=seed, median_mm=median_mm
    )[float(rc_terr_mm)]


def page_line(result: dict | float | None) -> str:
    """The page's thinning sentence (Hotel E7, adopted by JA40), with the depth filled in.

    ``result`` is ``detectable_depth``'s dict, or the depth itself (None: not reached by 0.60).
    Above 0.40 the sentence says so (JA40); no threshold is loosened."""
    depth: Optional[float] = result.get("depth") if isinstance(result, dict) else result
    head = (
        "Thinning: a territory is flagged only when its wall is thinner than the patient's other "
        "walls by more than this population's normal variation allows."
    )
    tail = (
        "Thinner changes are usually not flagged. This is not a sensitivity for scar, which this "
        "table cannot measure."
    )
    if depth is None:
        top = int(round(100 * DEPTHS[-1]))
        mid = (
            f"In simulation, no territory thinned by up to {top} % is flagged in >= 80 % of cases."
        )
        return f"{head} {mid} {tail}"
    pct = int(round(100 * float(depth)))
    mid = f"In simulation, a territory thinned by >= {pct} % is flagged in >= 80 % of cases."
    line = f"{head} {mid} {tail}"
    if depth > DEPTH_WARN + 1e-9:
        line += (
            f" This depth is above {int(round(100 * DEPTH_WARN))} %: moderate thinning is not "
            "seen, and the flag's thresholds are not loosened to see it."
        )
    return line
