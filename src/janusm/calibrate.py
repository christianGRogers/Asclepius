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

**The wall (JA60, Round 4).** The F1 floor is in mm, so the depth depends on the wall it is read
against. ``detectable_depth`` takes the measured median wall of the population whose table it
prints (``measured_median_mm``: JM-0R's ``thickness_median_mm`` in R9, the reference population's
``median_level`` in ``reference.gate``). ``population()`` multiplies its anchor by the patient
phase, so the anchor is ``measured / population_factor(phase_mix, shape, cv_n)``; the simulated
population's median wall then equals the measured one. With no wall the anchor is
``ED_MEDIAN_MM`` (5.7 mm). ``median_mm`` (an anchor, used as is) stays only for E7's regression
rows; passing both raises. 9.668 mm is never a plan input (JA60).

**The read-out (Hotel E7, JA40).** 4 replicate populations of 2000 per depth, depths 0.10-0.60 in
0.05 steps; the detectable depth is the smallest depth whose mean territory sensitivity is >= 0.80.
Being on the 0.05 grid, it is rounded **up** to 0.05. With the default ``seed`` the seeds are E7's,
so its primary rows (cv_n 0.088, Lima's shape, ``median_mm=9.668``) come back exactly: 0.30 at
RC 0 and 0.35 at RC 1.0. At the 5.7 mm default anchor the same inputs give 0.45, JA60's
provisional print.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

#: Bump on any change that can move a reported number.
CALIBRATE_VERSION = "1.1.1"

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
TNAMES = TERRITORIES  # the column order of ``territory_flags`` and ``f1_deviation``

#: Lima's self-test on 23 public hearts (1.5 mm model-made labels;
#: ``experiments/JanusM/Lima/local_check_summary.json``): the only measured inputs before JM-0R.
LIMA_SHAPE = (
    1.015, 1.288, 1.171, 0.971, 0.982, 1.120, 0.910, 1.121,
    1.276, 1.022, 0.916, 1.074, 0.777, 0.825, 0.756, 0.819,
)  # fmt: skip
LIMA_CV_N = 0.088
# Lima's self-test median wall. E7 passed it as an anchor (``median_mm``); kept only to reproduce
# E7's rows. Never a plan input (JA60): it fails R3's window and was phase-scaled twice.
LIMA_MEDIAN_MM = 9.668
ED_MEDIAN_MM = 5.7  # Lima's anchor (Chen 2025, CT end-diastole): the default anchor (JA60)

PHASES = {"ED": 1.00, "MD": 1.14, "SYS": 1.40}
PHASE_MIX = {"ED": 0.4, "MD": 0.4, "SYS": 0.2}  # JA40
MIXED = PHASE_MIX
SCALE_CV = 0.12
PREVALENCE = 0.1  # JA40
N_PER_POPULATION = 2000  # JA40
REPLICATES = 4  # JA40
DEPTHS = tuple(round(0.10 + 0.05 * i, 2) for i in range(11))  # 0.10 .. 0.60
SENSITIVITY_TARGET = 0.80
FALSE_FLAG_TARGET = 0.05  # rule C's mirror-null calibration
NULL_HEARTS = 20000
NULL_PATIENTS = NULL_HEARTS
RC_TERR_PROVISIONAL_MM = 1.0  # JA40: the F1 floor until the reads exist
DEPTH_WARN = 0.40  # JA40: above this the page says so
FACTOR_HEARTS = 200000  # JA60: population_factor's hearts (Lima G1, E6)
FACTOR_SEED = 7  # JA60: population_factor's fixed seed
E7_SEED = 31000  # Hotel E7's first seed: with it, E7's rows reproduce exactly
DEFAULT_SEED = E7_SEED


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
    median_mm: float = ED_MEDIAN_MM,
):
    """Lima's simulated population: (measured n x 16 mm, lesion n x 16, sick n, territory n,
    phase n). The draws are made in Lima's order, so a seed gives Lima's and Hotel's hearts.
    ``median_mm`` is the end-diastolic anchor (Lima's 5.7 mm by default); each heart's wall is
    also scaled by its phase, so the population's median wall is ``population_factor`` x it.
    ``phase_mix`` may be partial: an omitted phase is 0 (JA73); a bad mix raises ``ValueError``."""
    shape = np.asarray(shape, float)
    mix = dict(_phase_key(phase_mix))  # JA73: an omitted phase is 0
    scale = median_mm * np.exp(rng.normal(0, SCALE_CV, n))
    ph_names = rng.choice(list(PHASES), size=n, p=[mix[k] for k in PHASES])
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


def _phase_key(phase_mix: Mapping[str, float]) -> Tuple[Tuple[str, float], ...]:
    """The full mix, one (phase, share) per phase in ``PHASES`` order (JA73): an omitted phase is
    0. ``ValueError`` (never ``KeyError``) on an unknown phase, a negative or non-finite share, or
    shares that do not sum to 1."""
    try:
        keys = set(phase_mix)
        p = tuple((k, float(phase_mix.get(k, 0.0))) for k in PHASES)
    except (AttributeError, TypeError, ValueError) as e:
        raise ValueError(f"phase_mix must be a mapping of phase to share, got {phase_mix!r}") from e
    if keys - set(PHASES):
        raise ValueError(f"unknown phase in {dict(phase_mix)}; phases are {list(PHASES)}")
    if any((not np.isfinite(v)) or v < 0 for _, v in p) or not np.isclose(sum(v for _, v in p), 1):
        raise ValueError(f"phase_mix must be shares summing to 1, got {dict(phase_mix)}")
    return p


@lru_cache(maxsize=32)
def _population_factor(
    phase: Tuple[Tuple[str, float], ...], shape: Tuple[float, ...], cv_n: float
) -> float:
    rng = np.random.default_rng(FACTOR_SEED)
    meas, *_ = population(
        FACTOR_HEARTS, 0.0, 0.0, cv_n, 0.0, dict(phase), rng, shape=shape, median_mm=1.0
    )
    return float(np.median(np.median(meas, 1)))


def population_factor(
    phase_mix: Mapping[str, float] = PHASE_MIX,
    shape: Sequence[float] = LIMA_SHAPE,
    cv_n: float = LIMA_CV_N,
) -> float:
    """JA60: the simulated population's median wall (the median over hearts of each heart's
    median segment) divided by the anchor ``median_mm``. Deterministic: ``FACTOR_HEARTS``
    (200 000) infarct-free hearts, no added error, seed ``FACTOR_SEED`` (7). 1.109 at Lima's
    inputs (mixed phase, ``LIMA_SHAPE``, cv_n 0.088; Lima G1: 1.1087)."""
    shape_t = tuple(float(x) for x in np.asarray(shape, float).ravel())
    if len(shape_t) != 16:
        raise ValueError("shape must be 16 segment ratios")
    if not np.isfinite(cv_n) or cv_n < 0:
        raise ValueError(f"bad cv_n {cv_n}")
    return _population_factor(_phase_key(phase_mix), shape_t, float(cv_n))


def anchor_mm(
    measured_median_mm: float,
    phase_mix: Mapping[str, float] = PHASE_MIX,
    shape: Sequence[float] = LIMA_SHAPE,
    cv_n: float = LIMA_CV_N,
) -> float:
    """The end-diastolic anchor whose simulated population has ``measured_median_mm`` as its
    median wall (JA60): measured / ``population_factor``."""
    m = float(measured_median_mm)
    if not np.isfinite(m) or m <= 0:
        raise ValueError(f"measured_median_mm must be a positive wall in mm, got {m}")
    return m / population_factor(phase_mix, shape, cv_n)


def territory_flags(flag) -> np.ndarray:
    """n x 16 segment flags -> n x 3 territory flags (LAD, RCA, LCx): two flagged, contiguous
    segments in the territory."""
    flag = np.atleast_2d(np.asarray(flag, bool))
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


def f1_deviation(
    meas, shape, territories: Optional[Mapping[str, Sequence[int]]] = None
) -> np.ndarray:
    """Hotel's F1 deviation, n x territories (mm, + = thinner than expected): each territory's
    mean shape-corrected thinning against the patient's remote level (the median of the segments
    outside it, shape-corrected). ``territories`` ({name: 1-based segments}) defaults to the AHA
    map, in ``TNAMES`` order."""
    meas = np.atleast_2d(np.asarray(meas, float))
    shape = np.asarray(shape, float)
    terrs = TERR16 if territories is None else territories
    out = np.zeros((meas.shape[0], len(terrs)))
    for j, segs1 in enumerate(terrs.values()):
        segs = [s - 1 for s in segs1]
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
    median_mm: float = ED_MEDIAN_MM,
    prev: float = PREVALENCE,
    phase_mix: Mapping[str, float] = PHASE_MIX,
    n: int = N_PER_POPULATION,
) -> dict:
    """One population (Hotel E7's ``one``): {"k_mad": k, rc: {"false_flag", "sens"}} for each F1
    floor in ``rcs``. ``false_flag`` is the share of infarct-free hearts with any shown flag;
    ``sens`` the share of infarcted hearts whose infarct territory shows a flag. ``median_mm`` is
    ``population``'s anchor (``detectable_depth`` converts a measured wall to it, JA60)."""
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


def _anchor(measured_median_mm, median_mm, phase_mix, shape, cv_n):
    """(anchor, factor, source) per JA60."""
    if measured_median_mm is not None and median_mm is not None:
        raise ValueError(
            "pass measured_median_mm (the measured wall) or median_mm (an anchor, E7's "
            "regression rows only), not both"
        )
    if measured_median_mm is not None:
        factor = population_factor(phase_mix, shape, cv_n)
        return anchor_mm(measured_median_mm, phase_mix, shape, cv_n), factor, "measured"
    if median_mm is not None:
        m = float(median_mm)
        if not np.isfinite(m) or m <= 0:
            raise ValueError(f"median_mm must be a positive anchor in mm, got {median_mm}")
        return m, None, "median_mm"
    return ED_MEDIAN_MM, None, "ed_default"


def detectable_depths(
    cv_n: float,
    shape: Sequence[float],
    rc_terr_mm: Sequence[float],
    *,
    sig_m: float = 0.0,
    seed: int,
    measured_median_mm: Optional[float] = None,
    median_mm: Optional[float] = None,
    phase_mix: Mapping[str, float] = PHASE_MIX,
) -> Dict[float, dict]:
    """``detectable_depth`` for several F1 floors on the same populations (as E7 swept them):
    {rc: result}. Each population is simulated once and read at every floor."""
    rcs = [float(r) for r in np.atleast_1d(rc_terr_mm)]
    shape = _check_inputs(cv_n, shape, rcs, sig_m)
    phase_mix = dict(_phase_key(phase_mix))  # JA73: normalised once; the full mix is passed on
    anchor, factor, source = _anchor(measured_median_mm, median_mm, phase_mix, shape, cv_n)
    rows = []
    s = seed
    for depth in DEPTHS:
        reps = []
        for _ in range(REPLICATES):
            s += 2  # E7's seed sequence: population seed s, null seed s + 1
            reps.append(
                simulate(
                    depth,
                    cv_n,
                    shape,
                    rcs,
                    s,
                    sig_m=sig_m,
                    median_mm=anchor,
                    phase_mix=phase_mix,
                )
            )
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
            "exceeds": None if first else DEPTHS[-1],
            "sens_range": [min(first["sens"]), max(first["sens"])] if first else None,
            "false_flag": max(max(t["false_flag"]) for t in table),
            "inputs": {
                "cv_n": float(cv_n),
                "shape": [float(x) for x in shape],
                "rc_terr_mm": rc,
                "sig_m": float(sig_m),
                "measured_median_mm": (
                    None if measured_median_mm is None else float(measured_median_mm)
                ),
                "median_mm": None if median_mm is None else float(median_mm),
                "anchor_mm": float(anchor),
                "anchor_source": source,
                "population_factor": factor,
                "phase_mix": dict(phase_mix),
                "seed": int(seed),
            },
            "design": {
                "phase_mix": dict(phase_mix),
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
    seed: int,
    measured_median_mm: Optional[float] = None,
    median_mm: Optional[float] = None,
    phase_mix: Mapping[str, float] = PHASE_MIX,
) -> dict:
    """JA40's detectable depth: the smallest relative thinning (0.10-0.60, 0.05 steps, so rounded
    up to 0.05) whose mean territory sensitivity over 4 populations of 2000 is >= 0.80.

    Returns ``depth`` (None if 0.60 is not enough; ``exceeds`` then names 0.60),
    ``sens_range`` (the replicates' min and max at that depth), ``false_flag`` (the largest
    share of infarct-free hearts with a shown flag over every depth and replicate), the inputs,
    the design and the per-depth table.

    ``cv_n`` is the plain SD of thickness / shape; ``shape`` the 16 segment ratios;
    ``rc_terr_mm`` the F1 floor; ``sig_m`` the error to add (0 when ``cv_n`` was measured on the
    borders of the model that fills the table, JA40); ``seed`` the first seed (``E7_SEED``
    reproduces E7).

    The wall (JA60): ``measured_median_mm`` is the measured median wall of the population whose
    table this depth is printed for; the anchor is it / ``population_factor(phase_mix, shape,
    cv_n)``. ``median_mm`` is an anchor used as is, for E7's regression rows only. Passing both
    raises; with neither the anchor is ``ED_MEDIAN_MM`` (5.7 mm). ``phase_mix`` is the
    population's phase mix (JA40's mix by default; ``{"ED": 1.0}`` for hypoattenuation, which
    phase does not scale); it may be partial, an omitted phase being 0 (JA73), and ``inputs``
    records the full mix. ``inputs`` records the measured wall, the anchor and the factor."""
    return detectable_depths(
        cv_n,
        shape,
        [rc_terr_mm],
        sig_m=sig_m,
        seed=seed,
        measured_median_mm=measured_median_mm,
        median_mm=median_mm,
        phase_mix=phase_mix,
    )[float(rc_terr_mm)]


_SUBJECT = {
    "thinning": (
        "Thinning",
        "its wall is thinner than the patient's other walls",
        "a territory thinned by",
        "Thinner changes are usually not flagged.",
    ),
    "hypoattenuation": (
        "Hypoattenuation",
        "its subendocardial attenuation is lower than the patient's other walls",
        "a territory with a relative subendocardial deficit of",
        "Smaller changes are usually not flagged.",
    ),
}


def page_line(result: dict | float | None, sign: str = "thinning") -> str:
    """The page's sentence for a depth sign (Hotel E7, adopted by JA40), with the depth filled in.

    ``result`` is ``detectable_depth``'s dict, or the depth itself (None: not reached by 0.60).
    ``sign`` is ``thinning`` (Hotel's sentence) or ``hypoattenuation`` (the same sentence for
    the relative subendocardial deficit, S7). Above 0.40 the sentence says so (JA40); no
    threshold is loosened."""
    name, what, how, smaller = _SUBJECT[sign]
    depth: Optional[float] = result.get("depth") if isinstance(result, dict) else result
    head = (
        f"{name}: a territory is flagged only when {what} by more than this population's "
        "normal variation allows."
    )
    tail = "This is not a sensitivity for scar, which this table cannot measure."
    if depth is None:
        top = int(round(100 * DEPTHS[-1]))
        mid = (
            f"In simulation, no change up to {top} % is flagged in ≥ 80 % of cases; this sign is "
            "shown as numbers only."
        )
        return f"{head} {mid} {tail}"
    pct = int(round(100 * float(depth)))
    mid = f"In simulation, {how} ≥ {pct} % is flagged in ≥ 80 % of cases. {smaller}"
    line = f"{head} {mid} {tail}"
    if depth > DEPTH_WARN + 1e-9:
        line += (
            f" This depth is above {int(round(100 * DEPTH_WARN))} %: only large changes can be "
            "flagged, and the flag's thresholds are not loosened to see more."
        )
    return line
