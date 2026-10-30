"""India Round 2, E8: the seal re-powering rule (ruling §6 item 5, JA6/JA8), as code fixed before any read exists.

Input (later, from the first 20 double-read decision cases): per patient and per border, d = (model-vs-read ASSD)
- (read-vs-read ASSD), averaged over the two reads, for Janus-M 0. The rule:
  1. margin M (per border) = 0.25 mm, unless the median read-vs-read ASSD on those 20 exceeds 0.5 mm; then
     M = min(0.5 x that median, 0.40 mm). Thickness margin = 0.5 mm, unless the median per-segment read-vs-read
     thickness difference exceeds 1.0 mm; then 0.5 x that median, capped at 0.8 mm. Set once; never revised.
  2. seal size n = the smallest of 60, 80, 100, 120 (the pre-registered extension) at which a patient bootstrap
     of the upper 95 % bound of mean d is <= M with probability >= 0.80, resampling the 20 observed d values
     (both borders must pass). If none reaches 0.80, n = 120 and the plan records that acceptance is unlikely.
  3. the seal never shrinks below 60.

Without reads it prints the table of n against the per-patient SD of d and the true mean, for the plan.

    python e8_repower.py                       # table (plan)
    python e8_repower.py decision20.json       # the rule, on {"endo": [...20], "epi": [...20], "rr_endo": [...],
                                               #   "rr_epi": [...], "rr_thick": [...]}
"""
import json, sys
import numpy as np

SIZES = (60, 80, 100, 120)


def p_pass(d, n, M, sims=2000, boots=400, rng=None):
    rng = rng or np.random.default_rng(0)
    d = np.asarray(d, float)
    ok = 0
    for _ in range(sims):
        s = rng.choice(d, n, replace=True)
        bm = rng.choice(s, (boots, n), replace=True).mean(1)
        ok += np.percentile(bm, 97.5) <= M
    return ok / sims


def margin(rr):
    m = float(np.median(rr))
    return 0.25 if m <= 0.5 else min(0.5 * m, 0.40)


def rule(x):
    out = {}
    for b in ("endo", "epi"):
        M = margin(x[f"rr_{b}"])
        p = {n: p_pass(x[b], n, M) for n in SIZES}
        out[b] = dict(margin_mm=M, power=p)
    nmin = next((n for n in SIZES if all(out[b]["power"][n] >= 0.8 for b in ("endo", "epi"))), None)
    rt = float(np.median(x["rr_thick"]))
    out["thickness_margin_mm"] = 0.5 if rt <= 1.0 else min(0.5 * rt, 0.8)
    out["seal_n"] = nmin or 120
    out["acceptance_unlikely"] = nmin is None
    return out


def table():
    rng = np.random.default_rng(1)
    rows = []
    for sd in (0.15, 0.25, 0.35):
        for mu in (0.0, 0.10, 0.15):
            d = rng.normal(mu, sd, 20)                  # a plausible 20-case observation
            d = d - d.mean() + mu                       # centred on the stated true mean
            rows.append(dict(sd=sd, true_mean=mu, power={n: round(p_pass(d, n, 0.25, 600, 300, rng), 2) for n in SIZES}))
    return rows


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(rule(json.load(open(sys.argv[1]))), indent=1))
    else:
        r = table()
        json.dump(r, open(__file__.replace("e8_repower.py", "results/e8_repower_table.json"), "w"), indent=1)
        for x in r:
            print(x)
