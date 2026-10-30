"""India R4: CPU checks of the shipped JA42 RC (janusm.reference.repeatability, rc_abs).

Synthetic numbers only; no case, no image, no id. Three checks:
1. pooled n: the shipped pooled bound uses n = territory x case values (~60), JA42 says
   n = patients (20). Coverage of the true 1.96 sigma when the three territories of one
   patient share a reader-pair effect (rho = within-patient correlation of the differences).
2. the log branch: when does it fire for thinning D (a signed deviation) and for fat D
   (a volume), and what floor does rc_abs give at the levels report.py passes.
3. (e^RC - 1) vs (1 - e^-RC): how conservative the shipped conversion is.

    python experiments/JanusM/India/r4/s367_rc_checks.py   # writes s367_rc_checks.json beside it
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
from janusm import calibrate as C  # noqa: E402
from janusm import reference as R  # noqa: E402

OUT = Path(__file__).with_suffix(".json")
T = R.TERRITORIES


def coverage(rho, n_pat=20, sigma=0.3, reps=2000, seed=0):
    rng = np.random.default_rng(seed)
    true_rc = 1.96 * sigma
    hit_ship = hit_pat = 0
    ratio = []
    for _ in range(reps):
        a = rng.normal(0, sigma * math.sqrt(rho), n_pat)
        d1 = {t: list(a + rng.normal(0, sigma * math.sqrt(1 - rho), n_pat)) for t in T}
        d2 = {t: [0.0] * n_pat for t in T}
        rc = R.repeatability(d1, d2)
        if rc["territory"]["LAD"]["source"] != "pooled":
            continue
        ship = rc["territory"]["LAD"]["rc"] - (abs(rc["territory"]["LAD"]["mean_diff"])
                                               if "added" in rc["territory"]["LAD"]["decision"]
                                               else 0.0)
        sd = rc["pooled"]["sd"]
        from scipy.stats import chi2
        pat = 1.96 * sd * math.sqrt((n_pat - 1) / chi2.ppf(0.025, n_pat - 1))
        hit_ship += ship >= true_rc
        hit_pat += pat >= true_rc
        ratio.append(pat / ship)
    n = len(ratio)
    return {"rho": rho, "n_runs": n, "coverage_shipped_n_values": round(hit_ship / n, 3),
            "coverage_n_patients": round(hit_pat / n, 3),
            "bound_ratio_patients_over_shipped": round(float(np.median(ratio)), 3)}


def log_branch(seed=1, n=20):
    """Reads of one synthetic population whose thickness error is proportional to the wall."""
    rng = np.random.default_rng(seed)
    meas, *_ = C.population(n, 0.1, 0.3, 0.088, 0.0, C.PHASE_MIX, rng, median_mm=9.668)
    # read noise proportional to the level: 5 % multiplicative per segment
    r1 = meas * np.exp(rng.normal(0, 0.05, meas.shape))
    r2 = meas * np.exp(rng.normal(0, 0.05, meas.shape))
    shape = np.asarray(C.LIMA_SHAPE)
    D1, D2 = C.f1_deviation(r1, shape), C.f1_deviation(r2, shape)
    d1 = {t: list(D1[:, j]) for j, t in enumerate(C.TNAMES)}
    d2 = {t: list(D2[:, j]) for j, t in enumerate(C.TNAMES)}
    th = R.repeatability(d1, d2)
    lv = np.median(r1, 1)
    rel = np.concatenate([(D1[:, j] - D2[:, j]) / lv for j in range(3)])
    from scipy.stats import spearmanr
    rho_level = float(spearmanr(np.abs(np.concatenate([D1[:, j] - D2[:, j] for j in range(3)])),
                                np.tile(lv, 3)).statistic)
    share_pos = float(np.mean((D1 > 0) & (D2 > 0)))
    # fat-like: positive volumes, 25 % multiplicative read noise (the shipped log test's design)
    lvl = rng.uniform(5, 200, (n, 3))
    f1 = lvl * np.exp(rng.normal(0, 0.25, lvl.shape))
    f2 = lvl * np.exp(rng.normal(0, 0.25, lvl.shape))
    fr = R.repeatability({t: list(f1[:, j]) for j, t in enumerate(T)},
                         {t: list(f2[:, j]) for j, t in enumerate(T)})
    floor_report = R.rc_abs(fr, "LAD", 1.0)  # report.py passes level 1.0 for fat
    true_sd_at = {str(v): round(v * math.sqrt(2) * 0.25, 1) for v in (10, 50, 150)}
    return {
        "thinning": {"scale": th["scale"], "spearman_rho_vs_meanD": th["spearman_rho"],
                     "share_cases_with_D_positive_both_reads": round(share_pos, 3),
                     "decisions": th["decisions"],
                     "spearman_rho_absdiff_vs_patient_level": round(rho_level, 3),
                     "rc_on_D_over_level_point": round(1.96 * float(np.std(rel, ddof=1)), 4)},
        "fat": {"scale": fr["scale"], "rc_log": fr["territory"]["LAD"]["rc"],
                "rc_abs_as_report_calls_it_mm3": round(floor_report, 3),
                "true_sd_of_difference_mm3_at_level": true_sd_at},
    }


def conversion():
    rows = []
    for rc in (0.05, 0.1, 0.2, 0.3, 0.5):
        up, down = math.exp(rc) - 1, 1 - math.exp(-rc)
        rows.append({"rc_log": rc, "up_e^rc-1": round(up, 4), "down_1-e^-rc": round(down, 4),
                     "shipped_over_thinning_side": round(up / down, 4)})
    return rows


def main():
    out = {"pooled_n": [coverage(r) for r in (0.0, 0.5, 0.8)],
           "log_branch": log_branch(), "conversion": conversion()}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
