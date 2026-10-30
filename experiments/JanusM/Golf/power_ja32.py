"""Golf R3 E10: the merged paired-seal power study at the JA32 bars (Round 2 paired-scar ruling, section 7 item 2).

One generative model that joins Golf R2 E6 (`cohort_power.py`: patient-clustered detection, patient-bootstrap lower
bounds) and Kilo R2 E6 (`Kilo/e6_power.py`: continuous transmurality, territory-contiguous infarcts, separate
detection and measurement), plus two LGE readers so that JA32's third bar is anchored the way JA32 says: to the
LGE inter-reader agreement measured on the 40 development patients, minus 0.10.

Per patient (all parameters are stated assumptions; the grid varies the uncertain ones):
  * A share `enrich` has a chronic ischaemic infarct in one territory (LAD 0.5, RCA 0.3, LCx 0.2; standard AHA map).
    Size: k = 1 + Binomial(n_territory - 1, 0.45) contiguous segments (Kilo), or k = 1 + Poisson(3) (Golf R2),
    capped at the 17 segments.  True transmurality T ~ Beta(1.6, 1.6), clipped to [0.02, 1] (Kilo).
  * Patient effect u ~ N(0, tau) on the logit, shared by misses and false calls (clustering; tau 0.4 weak,
    0.8 base, 1.2 strong).
  * CT detection: P(detect) = expit(a + b T - u); P(false call) = expit(c + u); a, b, c from Kilo E6, giving
    segment sensitivity about 0.86 and specificity 0.98 (Gatti 2025 pooled).  A `weak` pipeline lowers a by 0.8.
  * CT extent T' = T + N(0, 0.05) per patient + N(0, sd_s) per segment; a false call reads Beta(1, 6).
  * LGE: two readers, R_j = T + N(0, sd_r) per segment (sd_r 0.08 base: bin agreement about 0.69; 0.06 / 0.12), presence = truth (adjudicated, JA32).  The reference bin is
    the bin of the readers' mean (adjudication proxy).  Reader agreement A_rr = share of scarred segments where
    the two readers' Kim bins agree.
Study: development 40 patients (enrichment 0.65, >= 25 with MI on average) gives A_rr_dev; seal N patients.
JA32 endpoints on the seal, 95 % patient-bootstrap lower bounds, one look:
  sens >= 0.75; spec >= 0.93; transmurality agreement (CT bin == reference bin, scar-on-both) >= A_rr_dev - 0.10;
  if A_rr_dev < 0.60 the third endpoint is reported only (JA32) and counts as passed.
Variant (proposed amendment): the anchor taken from every patient's double LGE read (development + seal); reader
agreement involves no CT value, so this leaks nothing about the pipeline.
Also: how many patients give >= 270 ischaemic scarred segments (JA28) at 50 % and 70 % enrichment.

Usage: python power_ja32.py [--sims 400] [--boot 400] [--quick]     writes power_ja32.json (CPU, no images)
       python power_ja32.py --sweep --sims 1000 --boot 500             writes power_ja32_sweep.json
"""
import argparse, json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TERR = {"LAD": [0, 1, 6, 7, 12, 13, 16], "RCA": [2, 3, 8, 9, 14], "LCx": [4, 5, 10, 11, 15]}
TERR_P = np.array([0.5, 0.3, 0.2])
A, B, C = -0.2, 5.0, -4.3                 # Kilo E6 detection constants
EDGES = np.array([0.25, 0.50, 0.75])
BARS = {"sens": 0.75, "spec": 0.93, "margin": 0.10, "anchor_floor": 0.60}
DEV_N, DEV_ENRICH = 40, 0.65


def expit(x):
    return 1 / (1 + np.exp(-x))


def kbin(t, present):
    return np.where(present, np.digitize(np.clip(t, 1e-9, 1), EDGES) + 1, 0)


def simulate(n, enrich, tau, sd_s, sd_r, size, weak, rng):
    T = np.zeros((n, 17))
    names = list(TERR)
    for i in np.flatnonzero(rng.random(n) < enrich):
        terr = TERR[names[rng.choice(3, p=TERR_P)]]
        if size == "kilo":
            k = 1 + rng.binomial(len(terr) - 1, 0.45)
            seg = rng.choice(terr, size=k, replace=False)
        else:                                       # golf: 1 + Poisson(3), contiguous from a territory segment
            k = min(1 + rng.poisson(3.0), 17)
            start = rng.choice(terr)
            seg = (start + np.arange(k)) % 17
        T[i, seg] = rng.beta(1.6, 1.6, size=len(seg)).clip(0.02, 1.0)
    pos = T > 0
    u = rng.normal(0, tau, (n, 1))
    a = A - (0.8 if weak else 0.0)
    det = rng.random((n, 17)) < np.where(pos, expit(a + B * T - u), expit(C + u))
    tct = T + rng.normal(0, 0.05, (n, 1)) + rng.normal(0, sd_s, (n, 17))
    tct = np.where(pos, tct, rng.beta(1, 6, (n, 17))).clip(0.01, 1.0)
    r1 = T + rng.normal(0, sd_r, (n, 17))
    r2 = T + rng.normal(0, sd_r, (n, 17))
    ref = kbin((r1 + r2) / 2, pos)
    return pos, det, kbin(tct, det), ref, kbin(r1, pos), kbin(r2, pos)


def per_patient(pos, det, ct, ref):
    both = pos & det
    return np.stack([(pos & det).sum(1), pos.sum(1), (~pos & ~det).sum(1), (~pos).sum(1),
                     (both & (ct == ref)).sum(1), both.sum(1)], 1).astype(float)


def lower_bounds(S, boot, rng):
    n = S.shape[0]
    W = rng.multinomial(n, np.ones(n) / n, size=boot).astype(float)
    Z = W @ S
    sens = Z[:, 0] / np.maximum(Z[:, 1], 1)
    spec = Z[:, 2] / np.maximum(Z[:, 3], 1)
    tagr = Z[:, 4] / np.maximum(Z[:, 5], 1)
    tot = S.sum(0)
    return ({"sens": np.percentile(sens, 2.5), "spec": np.percentile(spec, 2.5), "tagr": np.percentile(tagr, 2.5)},
            {"sens": tot[0] / max(tot[1], 1), "spec": tot[2] / tot[3], "tagr": tot[4] / max(tot[5], 1)})


def study(n, enrich, tau, sd_s, sd_r, size, weak, boot, rng):
    pos0, _, _, _, r1, r2 = simulate(DEV_N, DEV_ENRICH, tau, sd_s, sd_r, size, weak, rng)
    agree0, nsc0 = (r1[pos0] == r2[pos0]).sum(), pos0.sum()
    a_rr = float(agree0 / max(nsc0, 1))
    pos, det, ct, ref, s1, s2 = simulate(n, enrich, tau, sd_s, sd_r, size, weak, rng)
    # variant: the anchor from every patient's double read (development + seal); it uses no CT value
    a_all = float((agree0 + (s1[pos] == s2[pos]).sum()) / max(nsc0 + pos.sum(), 1))
    lb, pt = lower_bounds(per_patient(pos, det, ct, ref), boot, rng)
    anchored = a_rr >= BARS["anchor_floor"]
    ok = {"sens": lb["sens"] >= BARS["sens"], "spec": lb["spec"] >= BARS["spec"],
          "tagr": (lb["tagr"] >= a_rr - BARS["margin"]) if anchored else True}
    alt = (lb["tagr"] >= a_all - BARS["margin"]) if a_all >= BARS["anchor_floor"] else True
    return ok, pt, a_rr, anchored, int(pos.sum()), alt, a_all >= BARS["anchor_floor"]


def power(n, enrich, tau, sd_s, sd_r, size, weak, sims, boot, seed):
    rng = np.random.default_rng(seed)
    acc = {"sens": 0, "spec": 0, "tagr": 0, "all": 0, "anchored": 0, "tagr_anchor_all": 0, "all_anchor_all": 0,
           "anchored_all": 0}
    pts, arr, nsc = [], [], []
    for _ in range(sims):
        ok, pt, a_rr, anch, ns, alt, anch_all = study(n, enrich, tau, sd_s, sd_r, size, weak, boot, rng)
        for k in ok:
            acc[k] += ok[k]
        acc["all"] += all(ok.values()); acc["anchored"] += anch
        acc["tagr_anchor_all"] += alt; acc["anchored_all"] += anch_all
        acc["all_anchor_all"] += ok["sens"] and ok["spec"] and alt
        pts.append(pt); arr.append(a_rr); nsc.append(ns)
    return {"N": n, "enrich": enrich, "tau": tau, "sd_s": sd_s, "sd_r": sd_r, "size": size, "weak": weak,
            "power": {k: round(v / sims, 3) for k, v in acc.items()},
            "point_median": {k: round(float(np.median([p[k] for p in pts])), 3) for k in pts[0]},
            "a_rr_dev_median": round(float(np.nanmedian(arr)), 3),
            "scarred_segments_median": int(np.median(nsc))}


def segments_needed(size, rng, sims=4000):
    """Patients needed for >= 270 scarred segments (JA28): median and 90th-percentile N, at 50 % and 70 %."""
    out = {}
    for enrich in (0.5, 0.7):
        need = []
        for _ in range(sims):
            tot, n = 0, 0
            while tot < 270:
                n += 1
                if rng.random() < enrich:
                    if size == "kilo":
                        terr = TERR[list(TERR)[rng.choice(3, p=TERR_P)]]
                        tot += 1 + rng.binomial(len(terr) - 1, 0.45)
                    else:
                        tot += min(1 + rng.poisson(3.0), 17)
            need.append(n)
        out[str(enrich)] = {"median": int(np.median(need)), "p90": int(np.percentile(need, 90))}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=400)
    ap.add_argument("--boot", type=int, default=400)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--sweep", action="store_true", help="CT extent error x reader error at N 120 / 160")
    a = ap.parse_args()
    if a.sweep:
        rows = []
        for i, (n, sd_r, sd_s) in enumerate((n, r, s_) for n in (120, 160) for r in (0.06, 0.08, 0.12)
                                            for s_ in (0.04, 0.06, 0.08, 0.10, 0.13)):
            r = power(n, 0.5, 0.8, sd_s, sd_r, "kilo", False, a.sims, a.boot, 9000 + i)
            rows.append(r); print(r, flush=True)
        (HERE / "power_ja32_sweep.json").write_text(json.dumps({"sims": a.sims, "boot": a.boot, "rows": rows}, indent=1) + "\n")
        raise SystemExit
    rng = np.random.default_rng(20261031)
    res = {"assumptions": {"detection_abc": [A, B, C], "bars": BARS, "dev": [DEV_N, DEV_ENRICH],
                           "sims": a.sims, "boot": a.boot},
           "segments_needed": {s: segments_needed(s, rng) for s in ("kilo", "golf")}, "calibration": {}, "grid": []}
    print(res["segments_needed"], flush=True)
    # calibration: one very large cohort per reader / CT error
    for sd_r in (0.06, 0.08, 0.12):
        for sd_s in (0.08, 0.13, 0.20):
            pos, det, ct, ref, r1, r2 = simulate(20000, 0.6, 0.8, sd_s, sd_r, "kilo", False, rng)
            both = pos & det
            res["calibration"][f"sd_r={sd_r},sd_s={sd_s}"] = {
                "sens": round(float(det[pos].mean()), 3), "spec": round(float((~det[~pos]).mean()), 3),
                "tagr_ct_vs_ref": round(float((ct[both] == ref[both]).mean()), 3),
                "a_rr": round(float((r1[pos] == r2[pos]).mean()), 3)}
    print(res["calibration"], flush=True)
    Ns = (80, 100, 120, 160) if a.quick else (60, 80, 100, 120, 135, 160, 200)
    grid = []
    for tau in (0.4, 0.8, 1.2):
        for enrich in (0.5, 0.7):
            for n in Ns:
                grid.append(dict(n=n, enrich=enrich, tau=tau, sd_s=0.13, sd_r=0.08, size="kilo", weak=False))
    for sd_s in (0.08, 0.20):
        for n in Ns:
            grid.append(dict(n=n, enrich=0.5, tau=0.8, sd_s=sd_s, sd_r=0.08, size="kilo", weak=False))
    for sd_r in (0.06, 0.12):
        for n in Ns:
            grid.append(dict(n=n, enrich=0.5, tau=0.8, sd_s=0.13, sd_r=sd_r, size="kilo", weak=False))
    for n in Ns:
        grid.append(dict(n=n, enrich=0.5, tau=0.8, sd_s=0.13, sd_r=0.08, size="golf", weak=False))
        grid.append(dict(n=n, enrich=0.5, tau=0.8, sd_s=0.13, sd_r=0.08, size="kilo", weak=True))
    for i, g in enumerate(grid):
        r = power(**g, sims=a.sims, boot=a.boot, seed=5000 + i)
        res["grid"].append(r)
        print(r, flush=True)
    (HERE / "power_ja32.json").write_text(json.dumps(res, indent=1) + "\n")
