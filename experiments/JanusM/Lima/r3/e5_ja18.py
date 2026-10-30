"""E5 (Round 2 ruling §7 item 3): Lima's E3 re-run under the full JA18 thinning rule, with the measured `cv_n` and
segment shape, and the procedure that prints the page's detectable depth once Job JM-0R reports.

JA18's thinning flag = rule C (Lima E3: patient-relative, shape-corrected z; a territory flagged when >= 2 contiguous
segments fall below a cut set for <= 5 % of null patients)
  AND F1 (Hotel): the territory's mean thickness lies below the patient's remote median (segments outside the
      territory) by more than the repeatability coefficient of the territory mean, RC = 1.96 * sqrt(2) * s_w / sqrt(k)
      (Bland & Altman 1986; k segments, s_w the single-read segment SD);
  AND the kappa gate (India, Lima): read-to-read Cohen's kappa of territory flags >= 0.6 on the decision set
      (40 patients, two independent reads), else the sign is shown as a number only.

Simulated here (no image):
  1. patient false flags and territory sensitivity, with and without F1;
  2. P(kappa >= 0.6) on a 40-patient decision set, by decision-set infarct prevalence (0, 10, 30 %), against a
     prevalence-free alternative: ICC of the two reads' continuous territory deviations (Shrout & Fleiss 1979),
     P(ICC >= 0.75);
  3. the composite pattern's null rate (thinning AND fat-or-hypoattenuation in one territory, each sign calibrated to
     <= 5 % of null patients) against the correlation of the three signs' scores;
  4. `detectable_depth()`: the page line, from a JM-0R summary.json (cv_n, segment shape) and the decision set's
     measured segment-thickness error.

    python e5_ja18.py OUT_JSON [--summary JM0R_OR_LOCAL_SUMMARY_JSON] [--sig-m 0.5]
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import calibrate_sim as C  # noqa: E402  (Lima R2 E3: population, territory_flags, rule_c_scores, calibrate_c)

TERR = list(C.TERR16)
RC_FACTOR = 1.96 * np.sqrt(2)


def load_measured(summary_path):
    """cv_n and the 16-segment shape from a lima_geom summary (JM-0R, or local_check_summary.json)."""
    s = json.load(open(summary_path))
    shape = s["rel_thickness_by_segment_mean_sd"]
    return float(s["rel_thickness_shape_corrected_sd"]), np.array([shape[str(k)][0] for k in range(1, 17)])


def f1_pass(meas, sig_r):
    """n x 3: territory mean below the patient's remote median by more than RC of the territory mean (mm)."""
    out = np.zeros((meas.shape[0], 3), bool)
    for j, t in enumerate(TERR):
        idx = [s - 1 for s in C.TERR16[t]]
        rest = [i for i in range(16) if i not in idx]
        dev = meas[:, idx].mean(1) - np.median(meas[:, rest], 1)
        out[:, j] = dev < -RC_FACTOR * sig_r / np.sqrt(len(idx))
    return out


def ja18_flags(meas, cut, sig_r, use_f1=True):
    tf = C.territory_flags(C.rule_c_scores(meas) < cut)
    return tf & f1_pass(meas, sig_r) if use_f1 else tf


def kappa(a, b):
    a, b = a.ravel(), b.ravel()
    po = (a == b).mean()
    pa, pb = a.mean(), b.mean()
    pe = pa * pb + (1 - pa) * (1 - pb)
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def territory_dev(meas):
    """n x 3 territory deviation (mm): territory mean minus the patient's remote median (F1's quantity)."""
    out = np.zeros((meas.shape[0], 3))
    for j, t in enumerate(TERR):
        idx = [s - 1 for s in C.TERR16[t]]
        rest = [i for i in range(16) if i not in idx]
        out[:, j] = meas[:, idx].mean(1) - np.median(meas[:, rest], 1)
    return out


def icc(a, b):
    """ICC(2,1)-style agreement of two reads' continuous territory deviations (Shrout & Fleiss absolute agreement,
    two raters), over every patient x territory."""
    x = np.stack([a.ravel(), b.ravel()], 1)
    n, k = x.shape
    gm = x.mean()
    msr = k * ((x.mean(1) - gm) ** 2).sum() / (n - 1)
    msc = n * ((x.mean(0) - gm) ** 2).sum() / (k - 1)
    sse = ((x - x.mean(1, keepdims=True) - x.mean(0, keepdims=True) + gm) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    return float((msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n))


def one_condition(cv_n, sig_m, depth, prev_ref, prev_dec, rng, n_ref=2000, n_kappa=400):
    mix = {"ED": 0.4, "MD": 0.4, "SYS": 0.2}
    meas, lesion, sick, terr, ph = C.population(n_ref, prev_ref, depth, cv_n, sig_m, mix, rng)
    cut, k = C.calibrate_c(C.rule_c_scores(meas))
    res = {}
    for name, f1 in (("rule_c", False), ("rule_c_f1", True)):
        tf = ja18_flags(meas, cut, sig_m, f1)
        hit = np.array([tf[i, TERR.index(terr[i])] for i in np.nonzero(sick)[0]])
        res[name] = {"patient_false_flag": round(float(tf.any(1)[~sick].mean()), 3),
                     "territory_sensitivity": round(float(hit.mean()), 3) if len(hit) else None}
    # kappa on a 40-patient decision set: two independent reads of the same true walls
    kap, iccs = [], []
    for _ in range(n_kappa):
        true, _, _, _, _ = C.population(40, prev_dec, depth, cv_n, 0.0, mix, rng)
        A = true + rng.normal(0, sig_m, true.shape)
        B = true + rng.normal(0, sig_m, true.shape)
        fa, fb = ja18_flags(A, cut, sig_m), ja18_flags(B, cut, sig_m)
        kap.append(kappa(fa, fb) if (fa.any() or fb.any()) else float("nan"))
        iccs.append(icc(territory_dev(A), territory_dev(B)))
    kap = np.array(kap)
    res["icc_median"] = round(float(np.median(iccs)), 3)
    res["p_icc_ge_0p75"] = round(float(np.mean(np.array(iccs) >= 0.75)), 3)
    res["kappa_median"] = round(float(np.nanmedian(kap)), 3) if np.isfinite(kap).any() else None
    res["p_kappa_ge_0p6"] = round(float(np.mean(np.nan_to_num(kap, nan=-1) >= 0.6)), 3)
    res["p_no_flag_in_decision_set"] = round(float(np.isnan(kap).mean()), 3)
    return res, cut


def composite_null(rho, rng, n=20000):
    """Null patients with three correlated per-segment scores (thinning, fat, hypoattenuation). Each sign is
    calibrated alone to <= 5 % of patients with any territory flag; the composite is thinning AND (fat OR hypo) in
    the same territory. Returns each sign's and the composite's patient rate."""
    cov = np.full((3, 3), rho) + (1 - rho) * np.eye(3)
    z = rng.multivariate_normal(np.zeros(3), cov, size=(n, 16))  # n x 16 x 3
    flags = []
    for s in range(3):
        cut = None
        for kk in np.arange(1.0, 6.01, 0.02):
            if C.territory_flags(z[:, :, s] < -kk).any(1).mean() <= 0.05:
                cut = -kk
                break
        flags.append(C.territory_flags(z[:, :, s] < cut))
    comp = flags[0] & (flags[1] | flags[2])
    any_sign = flags[0] | flags[1] | flags[2]
    return {"rho": rho, "each_sign": [round(float(f.any(1).mean()), 4) for f in flags],
            "any_sign": round(float(any_sign.any(1).mean()), 4), "composite": round(float(comp.any(1).mean()), 4)}


def detectable_depth(cv_n, shape, sig_m, rng, target=0.8):
    """The page line: the smallest relative thinning (5 % steps) flagged with >= 80 % probability under JA18 (rule C
    + F1), mixed phase, 10 % prevalence. Never called a sensitivity."""
    C.SHAPE = shape
    for depth in np.arange(0.15, 0.651, 0.05):
        meas, lesion, sick, terr, ph = C.population(4000, 0.1, depth, cv_n, sig_m, {"ED": .4, "MD": .4, "SYS": .2}, rng)
        cut, _ = C.calibrate_c(C.rule_c_scores(meas))
        tf = ja18_flags(meas, cut, sig_m)
        hit = np.mean([tf[i, TERR.index(terr[i])] for i in np.nonzero(sick)[0]])
        if hit >= target:
            return round(float(depth), 2)
    return None


def page_line(depth, sig_m):
    d = f"{int(round(depth * 100))} %" if depth else "more than 65 %"
    return (f"Thinning flags in this population find a territory thinned by {d} or more with 80 % probability "
            f"(simulated; segment-thickness error {sig_m} mm; this is not a sensitivity for scar).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--summary", default=os.path.join(os.path.dirname(HERE), "local_check_summary.json"))
    ap.add_argument("--sig-m", type=float, default=0.5)
    a = ap.parse_args()
    rng = np.random.default_rng(20261030)
    cv_meas, shape = load_measured(a.summary)
    C.SHAPE = shape
    grid = []
    for cv_n in sorted({0.06, round(cv_meas, 3), 0.15}):
        for sig_m in (0.25, 0.5, 1.0):
            for depth in (0.3, 0.4, 0.5):
                for prev_dec in (0.0, 0.1, 0.3):
                    r, _ = one_condition(cv_n, sig_m, depth, 0.1, prev_dec, rng)
                    grid.append(dict(cv_n=cv_n, sig_m=sig_m, depth=depth, prev_decision=prev_dec, **r))
                    print(cv_n, sig_m, depth, prev_dec, r, flush=True)
    comp = [composite_null(rho, rng) for rho in (0.0, 0.3, 0.6, 0.9)]
    dd = {str(s): detectable_depth(cv_meas, shape, s, rng) for s in (0.25, 0.5, 1.0)}
    out = {"inputs": {"summary": os.path.relpath(a.summary, HERE), "cv_n_measured": cv_meas,
                      "shape": shape.round(3).tolist()},
           "grid": grid, "composite_null": comp, "detectable_depth_by_sig_m": dd,
           "page_line": page_line(dd[str(a.sig_m)], a.sig_m)}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("composite_null", "detectable_depth_by_sig_m", "page_line")}, indent=1))


if __name__ == "__main__":
    main()
