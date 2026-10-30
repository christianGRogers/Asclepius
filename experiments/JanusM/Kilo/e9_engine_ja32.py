"""E9 (Kilo v3): two JA32 design questions, run on the merged engine (`janusm.scar.power`, `janusm.scar.scoring`).

Uses the shared engine's generators and harness unchanged; only the resolution of not-graded segments and the anchor
are varied here. Simulation only: no image, case or identifier.

A. When does the transmurality endpoint bind? The engine's default (Golf's bin-error rate q = 0.25, fixed anchors)
   reports that it never binds at anchors <= 0.8. E7 (Kilo's generator) found it binding at the extent error E5
   measured. Here the engine's own Golf cohort is run with q in {0.25, 0.35, 0.45, 0.55} (exact-bin agreement among
   scar-on-both segments is printed per row as median_point.tbin), at an anchor of 0.72 (E7's simulated two-reader agreement),
   (i) fixed and (ii) drawn per study from N(0.72, 0.05), the sampling spread E7 found for an anchor measured on the
   40 development patients (5th-95th percentile 0.63-0.80).

B. How registration failures are counted. JA29: a not-graded segment is a miss if LGE-positive and a false call if
   LGE-negative. The engine run on #182 shows that at 2-5 % whole-patient failure the specificity endpoint then fails
   at any N. Compared here, at p_fail in {0, 0.02, 0.05, 0.10}:
     ITD-worst   JA29 as written (the engine's `intention_to_diagnose`);
     ITD-nocall  a not-graded segment is "no scar called" (a miss if LGE-positive, correct if LGE-negative), which is
                 what the report actually says ("not graded" never reads as scar), plus a separate **yield endpoint**:
                 the not-graded patient share, upper 95 % bound (patient bootstrap) <= 0.10;
     graded-only the engine's graded-only analysis (reported, never deciding).

Usage: PYTHONPATH=src python e9_engine_ja32.py OUT_JSON [--sims 300] [--boot 300]
"""
import argparse, json, time

import numpy as np

from janusm.scar import power as P
from janusm.scar import scoring as S


def score_study(ref, ct, boot, rng, mode):
    ng = (ct == S.NOT_GRADED)
    if mode == "worst":
        st = S.patient_stats(ref, S.intention_to_diagnose(ref, ct))
    elif mode == "nocall":
        st = S.patient_stats(ref, np.where(ng, 0, ct))
    else:                                                   # graded only
        st = S.patient_stats(ref, np.where(ng, 0, ct), ~ng)
        keep = (~ng).any(1)
        st = st[keep]
    ci = S.cluster_bootstrap(st, boot, rng)
    pf = ng.all(1).astype(float)                            # patient not graded
    w = S.bootstrap_weights(len(pf), boot, rng)
    yield_hi = float(np.percentile(w @ pf / len(pf), 97.5))
    return ci, float(pf.mean()), yield_hi


def run(gen_params, n, sims, boot, seed, anchors, modes):
    rng = np.random.default_rng(seed)
    out = {m: {"sens": 0, "spec": 0, "tbin_fixed": 0, "tbin_noisy": 0, "joint_fixed": 0, "joint_noisy": 0,
               "yield": 0, "joint_nocall_yield": 0, "pt": []} for m in modes}
    for _ in range(sims):
        ref, ct = P.golf_cohort(rng, n, **gen_params)
        a_noisy = rng.normal(anchors, 0.05)
        for m in modes:
            ci, pfail, yhi = score_study(ref, ct, boot, rng, m)
            lo = {k: np.nan_to_num(ci[k]["lower"], nan=-np.inf) for k in ("sens", "spec", "tbin")}
            ps, pp = lo["sens"] >= S.SENS_BAR, lo["spec"] >= S.SPEC_BAR
            tf = lo["tbin"] >= anchors - S.TBIN_MARGIN
            tn = (lo["tbin"] >= a_noisy - S.TBIN_MARGIN) if a_noisy >= S.MIN_ANCHOR else True
            y = yhi <= 0.10
            o = out[m]
            o["sens"] += ps; o["spec"] += pp; o["tbin_fixed"] += tf; o["tbin_noisy"] += tn
            o["joint_fixed"] += ps and pp and tf; o["joint_noisy"] += ps and pp and tn
            o["yield"] += y; o["joint_nocall_yield"] += ps and pp and tf and y
            o["pt"].append([ci["sens"]["point"], ci["spec"]["point"], ci["tbin"]["point"]])
    res = {}
    for m, o in out.items():
        pt = np.nanmedian(np.array(o.pop("pt")), 0)
        res[m] = {k: round(v / sims, 3) for k, v in o.items()} | {
            "median_point": {"sens": round(float(pt[0]), 3), "spec": round(float(pt[1]), 3), "tbin": round(float(pt[2]), 3)}}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--sims", type=int, default=300); ap.add_argument("--boot", type=int, default=300)
    a = ap.parse_args()
    base = dict(enrich=0.5, lam=3.0, tau=0.7, bin_tau=0.0, p_fail=0.0)
    res = {"settings": vars(a) | {"base": base, "anchor": 0.72, "anchor_sd_noisy": 0.05,
                                  "bars": {"sens": S.SENS_BAR, "spec": S.SPEC_BAR, "margin": S.TBIN_MARGIN}},
           "A_transmurality": [], "B_failures": []}
    t0 = time.time()
    seed = 2026
    for q in (0.25, 0.35, 0.45, 0.55):
        for n in (120, 160, 240):
            seed += 1
            r = run(base | dict(q=q), n, a.sims, a.boot, seed, 0.72, ["worst"])["worst"]
            res["A_transmurality"].append({"q": q, "n": n, **r}); print("A", q, n, r, f"{time.time() - t0:.0f}s", flush=True)
            json.dump(res, open(a.out, "w"), indent=1)
    for enrich in (0.5, 0.7):
        for pf in (0.0, 0.02, 0.05, 0.10):
            for n in (120, 160, 240):
                seed += 1
                r = run(base | dict(enrich=enrich, q=0.25, p_fail=pf), n, a.sims, a.boot, seed, 0.72,
                        ["worst", "nocall", "graded"])
                res["B_failures"].append({"enrich": enrich, "p_fail": pf, "n": n, **r})
                print("B", enrich, pf, n, {m: (v["joint_fixed"], v["yield"]) for m, v in r.items()}, f"{time.time() - t0:.0f}s", flush=True)
                json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
