"""E5b (Kilo v2): a two-threshold scar rule from E5's saved per-segment shares (no image is re-read).

Presence from the specific rule (FWHM, GF, share >= 5 %); extent (Kim bin) from the accurate one (remote + 3 SD, G3).
A segment present on GF with a G3 share below 1-25 % is put in bin 1. Patient-bootstrap 95 % CIs (2000 draws).
Usage: python e5_hybrid.py results_e5_lie_registration.json OUT_JSON
"""
import json, sys
import numpy as np

KIM = np.array([0.25, 0.50, 0.75])


def kbin(f):
    return np.digitize(np.clip(f, 1e-9, 1), KIM) + 1


d = json.load(open(sys.argv[1]))
methods = list(d["summary"])
rules = {"G3": ("G3", "G3"), "GF": ("GF", "GF"), "G5": ("G5", "G5"), "hybrid_GFpresence_G3extent": ("GF", "G3")}
rng = np.random.default_rng(1)
out = {}
for m in methods:
    out[m] = {}
    for name, (pres_g, ext_g) in rules.items():
        per_case = []                     # (tp, fn, tn, fp, agree_scar, n_scar_both, err list) per case
        for c in d["cases"]:
            if "reps" not in c:
                continue
            acc = np.zeros(6); errs = []
            for r in c["reps"]:
                ref = np.array(r["ref_frac"]); rb = np.where(ref > 0, kbin(ref), 0)
                e = r["methods"][m]
                fp_ = np.array(e[pres_g]["frac"], float); fe = np.array(e[ext_g]["frac"], float)
                ok = ~np.isnan(fp_) & ~np.isnan(fe)
                pres = (fp_ >= 0.05) & ok
                cb = np.where(pres, np.maximum(kbin(np.nan_to_num(fe)), 1), 0)
                pos = (rb > 0) & ok
                both = pos & pres
                acc += [(pos & pres).sum(), (pos & ~pres).sum(), (~pos & ~pres & ok).sum(), (~pos & pres).sum(),
                        (cb[both] == rb[both]).sum(), both.sum()]
                errs += (np.nan_to_num(fe[both]) - ref[both]).tolist()
            per_case.append((acc, errs))
        A = np.array([a for a, _ in per_case])
        def st(a):
            s = a.sum(0)
            return np.array([s[0] / (s[0] + s[1]), s[2] / (s[2] + s[3]), s[4] / s[5]])
        est = st(A)
        bs = np.array([st(A[rng.integers(0, len(A), len(A))]) for _ in range(2000)])
        lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
        errs = sum((e for _, e in per_case), [])
        out[m][name] = {k: [round(float(est[i]), 3), round(float(lo[i]), 3), round(float(hi[i]), 3)]
                        for i, k in enumerate(("sens", "spec", "transmurality_agreement"))}
        out[m][name]["transmurality_error_mean_sd"] = [round(float(np.mean(errs)), 3), round(float(np.std(errs)), 3)]
json.dump({"n_cases": len(per_case), "rules": {k: list(v) for k, v in rules.items()}, "by_method": out},
          open(sys.argv[2], "w"), indent=1)
for m in ("oracle", "R0_none", "R1_rigid", "R3_rigid_heartmask"):
    for k, v in out[m].items():
        print(m, k, v)
