"""E6 (Kilo v2): how many paired CT + LGE patients a segment-level transmurality validation needs.

No image is read. A cohort of N patients is simulated, 17 AHA segments each, segments clustered in patients:
  * a share q of patients has a chronic infarct in one coronary territory (standard AHA map, Cerqueira 2002, as
    every Round 1 advocate used it, verified from secondary sources only, JA14); the rest have none;
  * an infarct covers k contiguous-territory segments, k ~ 1 + Binomial(n_territory - 1, 0.45);
  * true LGE transmurality T ~ Beta(1.6, 1.6) in (0, 1] for scarred segments, 0 elsewhere;
  * CT detection and measurement are separate steps:
      - a scarred segment is detected with probability logistic(a + b*T + u_patient), small scars being missed;
      - a scar-free segment is falsely called scar with probability logistic(c + u_patient);
      - u_patient ~ N(0, 0.8) makes errors cluster in patients (one patient's LIE scan is poor throughout);
      - a detected true scar is graded T' = T + b_patient + e_segment (b ~ N(0, sd_p = 0.05), a registration /
        protocol offset; e ~ N(0, sd_s), the transmurality measurement error); a false call has T' ~ Beta(1, 6).
    a, b and c are set so the segment sensitivity is about 0.86 and specificity about 0.98, the pooled LIE vs LGE
    values (Gatti 2025, 14 studies). sd_s is the free parameter that registration and border error (E5) set.
Agreement is scored on Kim bins (0; 1-25; 26-50; 51-75; 76-100 %): linear-weighted kappa, segment sensitivity and
specificity for scar presence, all with a 95 % patient (cluster) bootstrap CI (Dixon 2016: segments within a patient
are not independent).

Question answered: for each N, the CI half-widths, and the power to show
  (a) weighted kappa lower bound > 0.61 (Gerber 2006's segmental kappa for late-enhancement CT vs CE-MR),
  (b) sensitivity lower bound > 0.75, and
  (c) a transmurality-bin agreement (segments scar on both) known to +-0.10,
when the true CT error is sd_s (grid). Usage: python e6_power.py out.json [--sims 300 --boot 300]
"""
import argparse, json
import numpy as np

# Standard AHA 17-segment territory map (secondary sources only; JA14): LAD 1,2,7,8,13,14,17; RCA 3,4,9,10,15; LCx 5,6,11,12,16
TERR = {"LAD": [0, 1, 6, 7, 12, 13, 16], "RCA": [2, 3, 8, 9, 14], "LCX": [4, 5, 10, 11, 15]}
TERR_P = {"LAD": 0.5, "RCA": 0.3, "LCX": 0.2}
EDGES = np.array([0.0, 0.25, 0.50, 0.75])          # bin 0 = no scar; bins 1-4 = Kim quartiles


def bins(t, present):
    b = np.digitize(np.clip(t, 1e-9, 1.0), EDGES[1:]) + 1
    return np.where(present, b, 0)


def _logit_inv(x):
    return 1 / (1 + np.exp(-x))


DET_A, DET_B, FP_C, SD_U = -0.2, 5.0, -4.3, 0.8


def simulate(n, q, sd_s, sd_p, rng):
    T = np.zeros((n, 17))
    scarred = rng.random(n) < q
    names = list(TERR)
    for i in np.flatnonzero(scarred):
        terr = TERR[rng.choice(names, p=[TERR_P[k] for k in names])]
        k = 1 + rng.binomial(len(terr) - 1, 0.45)
        seg = rng.choice(terr, size=k, replace=False)
        T[i, seg] = rng.beta(1.6, 1.6, size=k).clip(0.02, 1.0)
    u = rng.normal(0, SD_U, (n, 1))
    pos = T > 0
    det = rng.random((n, 17)) < np.where(pos, _logit_inv(DET_A + DET_B * T + u), _logit_inv(FP_C + u))
    graded = T + rng.normal(0, sd_p, (n, 1)) + rng.normal(0, sd_s, (n, 17))
    graded = np.where(pos, graded, rng.beta(1, 6, (n, 17))).clip(0.01, 1.0)
    ref = bins(T, pos)
    ct = bins(graded, det)
    return ref, ct


def wkappa(a, b, k=5):
    m = np.zeros((k, k)); np.add.at(m, (a, b), 1); m /= m.sum()
    w = 1 - np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    po = (w * m).sum(); pe = (w * np.outer(m.sum(1), m.sum(0))).sum()
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def stats(ref, ct):
    r, c = ref.ravel(), ct.ravel()
    pos = r > 0
    sens = (c[pos] > 0).mean() if pos.any() else np.nan
    spec = (c[~pos] == 0).mean()
    both = pos & (c > 0)
    tbin = (r[both] == c[both]).mean() if both.any() else np.nan   # transmurality bin agreement, scar on both
    return wkappa(r, c), sens, spec, tbin


def boot_ci(ref, ct, nb, rng):
    n = ref.shape[0]
    out = np.array([stats(ref[idx], ct[idx]) for idx in rng.integers(0, n, (nb, n))])
    return np.nanpercentile(out, [2.5, 97.5], axis=0)


def icc_binary(ct_pos):
    """One-way ANOVA ICC of the per-segment CT-positive indicator within patients."""
    n, m = ct_pos.shape
    gm = ct_pos.mean(); pm = ct_pos.mean(1)
    msb = m * ((pm - gm) ** 2).sum() / (n - 1)
    msw = ((ct_pos - pm[:, None]) ** 2).sum() / (n * (m - 1))
    return (msb - msw) / (msb + (m - 1) * msw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--sims", type=int, default=300); ap.add_argument("--boot", type=int, default=300)
    ap.add_argument("--q", type=float, default=0.7); ap.add_argument("--seed", type=int, default=20261030)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    sd_p = 0.05
    res = {"settings": vars(a) | {"sd_p": sd_p, "det_a": DET_A, "det_b": DET_B, "fp_c": FP_C, "sd_u": SD_U}, "calibration": {}, "grid": []}
    # calibration: one very large cohort per sd_s
    for sd_s in (0.08, 0.13, 0.20):
        ref, ct = simulate(20000, a.q, sd_s, sd_p, rng)
        k, se, sp, tb = stats(ref, ct)
        res["calibration"][str(sd_s)] = {"wkappa": round(float(k), 3), "sens": round(float(se), 3), "spec": round(float(sp), 3),
                                         "tbin_agreement_scarred": round(float(tb), 3),
                                         "exact_bin_agreement": round(float((ref == ct).mean()), 3),
                                         "scar_segment_share": round(float((ref > 0).mean()), 3),
                                         "icc_ct_positive": round(float(icc_binary((ct > 0).astype(float))), 3)}
        print("calibration", sd_s, res["calibration"][str(sd_s)], flush=True)
    for sd_s in (0.08, 0.13, 0.20):
        for n in (20, 40, 60, 80, 120, 160, 240):
            hw, pk, ps, pt, kap, nsc = [], 0, 0, 0, [], []
            for _ in range(a.sims):
                ref, ct = simulate(n, a.q, sd_s, sd_p, rng)
                lo, hi = boot_ci(ref, ct, a.boot, rng)
                k = stats(ref, ct)[0]; kap.append(k); nsc.append((ref > 0).sum())
                hw.append((hi - lo) / 2)
                pk += lo[0] > 0.61; ps += lo[1] > 0.75; pt += (hi[3] - lo[3]) / 2 <= 0.10
            hw = np.nanmean(np.array(hw), axis=0)
            row = {"sd_s": sd_s, "n_patients": n, "mean_wkappa": round(float(np.nanmean(kap)), 3),
                   "mean_scar_segments": round(float(np.mean(nsc)), 1),
                   "ci_halfwidth": {"wkappa": round(float(hw[0]), 3), "sens": round(float(hw[1]), 3),
                                    "spec": round(float(hw[2]), 3), "tbin_scarred": round(float(hw[3]), 3)},
                   "power_wkappa_lb_gt_0.61": round(pk / a.sims, 3), "power_sens_lb_gt_0.75": round(ps / a.sims, 3),
                   "p_tbin_halfwidth_le_0.10": round(pt / a.sims, 3)}
            res["grid"].append(row); print(row, flush=True)
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
