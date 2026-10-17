"""Round 8: pool Crucible two-reads seeds 1 and 2 case-paired (seed as a factor). Usage: python3 r8_pool_seeds.py [out.json]"""

import json

import numpy as np

R = "/home/user/Asclepius/trillium-results/"
S = [
    json.load(open(R + p + "/results/results.json"))
    for p in ["round5/crucible", "round6/crucible_seed2"]
]
arms = S[0]["arms"]
cases = [c["case"] for c in S[0]["cases"]]
assert cases == [c["case"] for c in S[1]["cases"]]
for a, b in zip(S[0]["cases"], S[1]["cases"]):
    assert a["inter_read"] == b["inter_read"]  # same reads, same test cases


def get(s, arm, kind, cls=None):
    out = []
    for c in S[s]["cases"]:
        r = c[arm]

        def v(k):
            return r[k]["tf1"] if cls is None else r[k]["per_class_tf1"].get(str(cls), np.nan)

        out.append(
            v("vs_T")
            if kind == "T"
            else (v("vs_A") + v("vs_B")) / 2
            if kind == "R"
            else v("vs_" + kind)
        )
    return np.array(out, float)


rng = np.random.default_rng(0)
B = 20000


def boot(d):
    d = d[np.isfinite(d)]
    i = rng.integers(0, len(d), (B, len(d)))
    return np.percentile(d[i].mean(1), [2.5, 97.5])


res = {}
print("== arm means per seed, between-seed SD (of the arm mean), per-case seed SD")
for kind in "TR":
    for arm in arms:
        x = [get(s, arm, kind) for s in (0, 1)]
        m = [float(np.mean(v)) for v in x]
        sd_between = abs(m[0] - m[1]) / np.sqrt(2)
        sd_case = float(np.std(x[0] - x[1], ddof=1) / np.sqrt(2))
        res[f"{arm}_{kind}"] = dict(
            seed1=m[0],
            seed2=m[1],
            pooled=float(np.mean(m)),
            sd_between_seed=sd_between,
            sd_per_case_seed=sd_case,
        )
        print(
            f"{kind} {arm:7s} s1 {m[0]:.4f} s2 {m[1]:.4f} pooled {np.mean(m):.4f} betweenSD {sd_between:.4f} per-case seed SD {sd_case:.4f}"
        )
print("== contrasts: per seed, pooled case-paired (seed as factor), interaction, seed-random CI")
contr = [
    ("both", "single"),
    ("a11", "single"),
    ("agree", "single"),
    ("union", "single"),
    ("oracle", "single"),
    ("a11", "both"),
    ("agree", "both"),
    ("union", "both"),
    ("oracle", "both"),
]
for kind in "TR":
    for x, y in contr:
        d = [get(s, x, kind) - get(s, y, kind) for s in (0, 1)]
        c = [float(np.mean(v)) for v in d]
        pooled = (d[0] + d[1]) / 2  # case-paired, seed effect averaged out (seed as fixed factor)
        lo, hi = boot(pooled)
        inter = d[1] - d[0]
        ilo, ihi = boot(inter)
        # seed as a random factor: add the between-seed variance of the contrast mean
        se_case = (hi - lo) / 3.92
        s2 = (c[0] - c[1]) ** 2 / 2
        se_r = np.sqrt(se_case**2 + s2 / 2)
        pm = float(pooled.mean())
        res[f"{x}-{y}_{kind}"] = dict(
            seed1=c[0],
            seed2=c[1],
            pooled=pm,
            ci_fixed=[float(lo), float(hi)],
            interaction=float(inter.mean()),
            ci_interaction=[float(ilo), float(ihi)],
            ci_random=[pm - 1.96 * se_r, pm + 1.96 * se_r],
            better_both=int(((d[0] > 0) & (d[1] > 0)).sum()),
        )
        print(
            f"{kind} {x}-{y:6s} s1 {c[0]:+.4f} s2 {c[1]:+.4f} | pooled {pm:+.4f} [{lo:+.4f},{hi:+.4f}] | seed-random [{pm - 1.96 * se_r:+.4f},{pm + 1.96 * se_r:+.4f}] | s2-s1 {inter.mean():+.4f} [{ilo:+.4f},{ihi:+.4f}]"
        )
print("== per-class a11-both and LM vs A/B per arm")
for s in (0, 1):
    for arm in arms:
        print(
            s + 1,
            arm,
            " ".join(f"{k}:LM {np.nanmean(get(s, arm, k, 1)):.3f}" for k in "TAB"),
            "LAD/LCx/RCA T",
            " ".join(f"{np.nanmean(get(s, arm, 'T', c)):.3f}" for c in (2, 3, 4)),
        )
for kind in "TR":
    for cls in (1, 2, 3, 4):
        d = [get(s, "a11", kind, cls) - get(s, "both", kind, cls) for s in (0, 1)]
        print(
            kind,
            "a11-both class",
            cls,
            " ".join(f"{np.nanmean(v):+.4f}" for v in d),
            "pooled %+.4f" % np.nanmean((d[0] + d[1]) / 2),
        )
import sys

if len(sys.argv) > 1:
    json.dump(res, open(sys.argv[1], "w"), indent=1)
