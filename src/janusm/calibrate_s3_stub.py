"""STUB for S3 (issue #194, ``janusm.calibrate``), used by S6/S7 until #194 merges.

S6 (``janusm.reference``, ``tools/janusm/build_reference.py``) and S7 (``janusm.report``) need
the detectable-depth function and rule C before S3 is on ``dev``. This module is a direct port
of the two committed sources, with no change to their logic:

* Lima's ``experiments/JanusM/Lima/calibrate_sim.py`` (branch ``jm/rest-ccta``): ``population``,
  ``territory_flags``, ``rule_c_scores``, ``calibrate_c``, unchanged except that the segment
  shape and the median thickness are arguments instead of module globals;
* Hotel's ``experiments/JanusM/Hotel/r3/e7_detectable.py``: ``f1_deviation`` and the replicate
  loop, as ``detectable_depth`` with S3's signature (Round 3 rest-ccta ruling, JA40 and §7 S3).

When #194 merges, ``janusm.reference`` and ``janusm.report`` switch their one import line
(``from janusm import calibrate_s3_stub as calibrate``) to ``janusm.calibrate`` and this file is
deleted. Nothing else imports it.

numpy only. No file, case or network access.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np

# AHA default map (Lima): segment 17 is never in rule C.
AHA = {"LAD": [1, 2, 7, 8, 13, 14, 17], "RCA": [3, 4, 9, 10, 15], "LCx": [5, 6, 11, 12, 16]}
#: Bullseye adjacency (rings of six, apical four), for "contiguous".
RING = {1: [2, 6, 7], 2: [1, 3, 8], 3: [2, 4, 9], 4: [3, 5, 10], 5: [4, 6, 11], 6: [5, 1, 12],
        7: [8, 12, 1, 13], 8: [7, 9, 2, 13, 14], 9: [8, 10, 3, 14, 15], 10: [9, 11, 4, 15],
        11: [10, 12, 5, 15, 16], 12: [11, 7, 6, 16, 13], 13: [14, 16, 7, 8, 12],
        14: [13, 15, 8, 9], 15: [14, 16, 9, 10, 11], 16: [15, 13, 11, 12]}
TERR16 = {t: [s for s in v if s <= 16] for t, v in AHA.items()}
#: Territory order of ``territory_flags`` columns (Lima's dict order).
TNAMES = list(TERR16)
#: Lima's self-test shape (23 public hearts, 1.5 mm model-made labels).
LIMA_SHAPE = np.array([1.015, 1.288, 1.171, 0.971, 0.982, 1.120, 0.910, 1.121, 1.276, 1.022,
                       0.916, 1.074, 0.777, 0.825, 0.756, 0.819])
PHASES = {"ED": 1.00, "MD": 1.14, "SYS": 1.40}
ED_MEDIAN_MM = 5.7
MIXED = {"ED": 0.4, "MD": 0.4, "SYS": 0.2}
#: JA40: depth grid (0.05 steps), replicates, population size, prevalence.
DEPTHS = tuple(round(x, 2) for x in np.arange(0.10, 0.601, 0.05))
REPS, N_POP, PREV = 4, 2000, 0.1
SENS_TARGET = 0.80
NULL_PATIENTS = 20000
K_GRID = np.arange(1.0, 6.01, 0.05)


def population(n, prev, depth, cv_n, sig_m, phase_mix, rng, shape=LIMA_SHAPE,
               median_mm=ED_MEDIAN_MM):
    """Lima's simulated population: (meas, lesion, sick, terr, phase names)."""
    shape = np.asarray(shape, float)
    scale = median_mm * np.exp(rng.normal(0, 0.12, n))
    ph_names = rng.choice(list(PHASES), size=n, p=[phase_mix[k] for k in PHASES])
    ph = np.array([PHASES[k] for k in ph_names])
    true = scale[:, None] * ph[:, None] * shape[None, :] * np.exp(rng.normal(0, cv_n, (n, 16)))
    sick = rng.random(n) < prev
    lesion = np.zeros((n, 16), bool)
    terr = np.array([None] * n, object)
    for i in np.nonzero(sick)[0]:
        t = rng.choice(list(TERR16))
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


def territory_flags(flag):
    """n x 16 bool -> n x 3 bool (LAD, RCA, LCx): >= 2 flagged, contiguous segments."""
    flag = np.atleast_2d(flag)
    out = np.zeros((flag.shape[0], 3), bool)
    for j, (_t, segs) in enumerate(TERR16.items()):
        for s in segs:
            nbs = [x for x in RING[s] if x in segs]
            out[:, j] |= flag[:, s - 1] & flag[:, [x - 1 for x in nbs]].any(1)
    return out


def rule_c_scores(meas):
    """Lima's rule C z: (thickness / patient median - shape) / per-segment right-half scale."""
    rel = meas / np.median(meas, 1, keepdims=True)
    shape = np.median(rel, 0)
    z = rel - shape
    scale = np.array([1.4826 * np.median(np.abs(c[c >= 0])) for c in z.T])
    return z / scale


def calibrate_c(z, target=0.05, rng=None):
    """Lima's mirror-null cut: (cut, k) so that <= ``target`` of 20 000 null patients have any
    flagged territory."""
    rng = rng or np.random.default_rng(0)
    z = np.asarray(z).ravel()
    med = np.median(z)
    right = z[z >= med] - med
    pool = np.r_[med + right, med - right]
    null = rng.choice(pool, (NULL_PATIENTS, 16))
    mad = 1.4826 * np.median(right)
    for k in K_GRID:
        if territory_flags(null < med - k * mad).any(1).mean() <= target:
            return med - k * mad, float(k)
    return med - 6 * mad, 6.0


def f1_deviation(meas, shape, territories: Optional[Dict[str, Sequence[int]]] = None):
    """Hotel's F1 deviation, per patient x territory (``TNAMES`` order unless ``territories``
    is given): shape-corrected mean thinning of the territory against the patient's remote
    segments. Positive = thinner than expected. Segments are 1-based."""
    meas = np.atleast_2d(np.asarray(meas, float))
    shape = np.asarray(shape, float)
    terrs = territories if territories is not None else TERR16
    out = np.zeros((meas.shape[0], len(terrs)))
    for j, segs1 in enumerate(terrs.values()):
        segs = [s - 1 for s in segs1]
        rem = [s for s in range(16) if s not in segs]
        level = np.median(meas[:, rem] / shape[rem], 1)
        exp = level[:, None] * shape[segs]
        out[:, j] = (exp - meas[:, segs]).mean(1)
    return out


def _one(depth, cv_n, sig_m, rc, seed, shape, median_mm, mix, prev, n):
    rng = np.random.default_rng(seed)
    meas, _lesion, sick, terr, _ph = population(n, prev, depth, cv_n, sig_m, mix, rng,
                                                shape=shape, median_mm=median_mm)
    z = rule_c_scores(meas)
    cut, _k = calibrate_c(z, rng=np.random.default_rng(seed + 1))
    f = territory_flags(z < cut) & (f1_deviation(meas, shape) > rc)
    sick_idx = np.nonzero(sick)[0]
    hit = np.array([f[i, TNAMES.index(terr[i])] for i in sick_idx])
    return float(hit.mean()) if len(hit) else float("nan"), float(f.any(1)[~sick].mean())


def detectable_depth(cv_n, shape, rc_terr_mm, *, sig_m=0.0, seed, median_mm=ED_MEDIAN_MM,
                     mix=None, prev=PREV, reps=REPS, n=N_POP, depths=DEPTHS) -> dict:
    """JA40: the smallest relative thinning (0.05 grid, so already rounded up) whose mean
    territory sensitivity over ``reps`` populations is >= 0.80, under rule C and the F1 floor
    ``rc_terr_mm``. Returns ``{depth, sens_range, false_flag}``; ``depth`` is None when no
    grid depth reaches 0.80 (``exceeds`` then names the largest depth tried)."""
    mix = mix or MIXED
    shape = np.asarray(shape, float)
    s = int(seed)
    worst_ff = 0.0
    for dep in depths:
        rr = []
        for _ in range(reps):
            s += 2
            rr.append(_one(float(dep), float(cv_n), float(sig_m), float(rc_terr_mm), s, shape,
                           float(median_mm), mix, prev, n))
        sens = [x[0] for x in rr]
        worst_ff = max(worst_ff, max(x[1] for x in rr))
        if np.mean(sens) >= SENS_TARGET:
            return {"depth": float(dep), "sens_range": [round(min(sens), 4), round(max(sens), 4)],
                    "false_flag": round(worst_ff, 4)}
    return {"depth": None, "exceeds": float(depths[-1]), "sens_range": None,
            "false_flag": round(worst_ff, 4)}


_SUBJECT = {
    "thinning": ("Thinning", "its wall is thinner than the patient's other walls",
                 "a territory thinned by"),
    "hypoattenuation": ("Hypoattenuation",
                        "its subendocardial attenuation is lower than the patient's other walls",
                        "a territory with a relative subendocardial deficit of"),
}


def page_line(depth, sign: str = "thinning") -> str:
    """The page sentence (Hotel E7, JA40), with the depth filled in."""
    name, what, how = _SUBJECT[sign]
    head = (f"{name}: a territory is flagged only when {what} by more than this population's "
            "normal variation allows. ")
    if depth is None:
        return head + ("In simulation, no change up to 60 % is flagged in 80 % of cases; this sign "
                       "is shown as numbers only. This is not a sensitivity for scar, which this "
                       "table cannot measure.")
    pct = int(round(float(depth) * 100))
    line = head + (f"In simulation, {how} ≥ {pct} % is flagged in ≥ 80 % of cases. "
                   "Thinner changes are usually not flagged." if sign == "thinning" else
                   f"In simulation, {how} ≥ {pct} % is flagged in ≥ 80 % of cases. "
                   "Smaller changes are usually not flagged.")
    if depth > 0.40:
        line += " At this population's variation only large changes can be flagged."
    return line + " This is not a sensitivity for scar, which this table cannot measure."
