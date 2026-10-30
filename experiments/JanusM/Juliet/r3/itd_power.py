"""Juliet R3 E9 (Janus-M Round 3, path jm/paired-scar, ruling section 7 item 2): the merged JA32 power script
(#182, PR #187, `janusm.scar.power` / `janusm.scar.scoring`) re-run at the JA32 bars, and one question it raises:
how a not-graded patient (registration failed twice, JA29) is counted.

Simulation only (Golf's cohort as ported in #187; no image, case or id). Run from a checkout that has
`src/janusm/scar/` (PR #187's head until it merges):  PYTHONPATH=<that>/src python itd_power.py

Two accountings of a not-graded patient, same cohorts, same bootstrap draws:
  segment (JA29 as written, #187): every LGE-positive segment is a miss, every LGE-negative segment a false call;
  split   (proposed): every LGE-positive segment is a miss (sensitivity is still charged in full), LGE-negative
          segments leave the specificity denominator, and the not-graded patient rate is its own bar: the exact
          (Clopper-Pearson) upper 95 % bound <= 0.10, the rate at which JA29 already stops seal grading.
Bars otherwise JA32: sensitivity >= 0.75, specificity >= 0.93, transmurality >= anchor - 0.10 (anchor 0.70), lower
bounds of the patient-cluster bootstrap. Joint power = the share of simulated studies passing every deciding bar.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import beta

from janusm.scar import power as P
from janusm.scar import scoring as S

HERE = Path(__file__).resolve().parent
OUT = HERE / "e9_itd_power.json"
N_GRID = (120, 160, 200, 240, 320)
P_FAIL = (0.0, 0.02, 0.05, 0.10)
ANCHOR = 0.70
NG_BAR = 0.10


def run(n, tau, enrich, p_fail, sims, boot, seed):
    rng = np.random.default_rng(seed)
    bars = S.bars(ANCHOR)
    hit = {"segment": 0, "split": 0}
    spec_pt = {"segment": [], "split": []}
    ngfail = 0
    for _ in range(sims):
        ref, ct = P.golf_cohort(rng, n, **{**P.JA32_BASE, "tau": tau, "enrich": enrich, "p_fail": p_fail})
        ng = (ct == S.NOT_GRADED).all(1)
        w = S.bootstrap_weights(n, boot, rng)                      # the same replicates for both accountings
        for rule in ("segment", "split"):
            if rule == "segment":
                stats = S.patient_stats(ref, S.intention_to_diagnose(ref, ct))
            else:
                ct2 = np.where(ct == S.NOT_GRADED, 0, ct)              # positives -> miss
                mask = ~((ct == S.NOT_GRADED) & (ref == 0))            # negatives of a not-graded patient leave
                stats = S.patient_stats(ref, ct2, mask)
            point = S.endpoints(stats.sum(0))
            b = S.endpoints(w @ stats)
            lo = {k: np.nanpercentile(b[k], 2.5) for k in ("sens", "spec", "tbin")}
            ok = all(lo[k] >= v for k, v in bars.items() if v is not None)
            if rule == "split":
                k_ng = int(ng.sum())
                ub = 1.0 if k_ng == n else float(beta.ppf(0.95, k_ng + 1, n - k_ng))
                ok = ok and ub <= NG_BAR
                ngfail += ub > NG_BAR
            hit[rule] += ok
            spec_pt[rule].append(float(point["spec"]))
    return {"n": n, "tau": tau, "enrich": enrich, "p_fail": p_fail,
            "power_segment": round(hit["segment"] / sims, 3), "power_split": round(hit["split"] / sims, 3),
            "spec_point_segment": round(float(np.median(spec_pt["segment"])), 4),
            "spec_point_split": round(float(np.median(spec_pt["split"])), 4),
            "split_ng_bar_failed": round(ngfail / sims, 3)}


def main(sims=200, boot=200):
    rows, cell = [], 0
    for cl, tau in P.CLUSTERING.items():
        for enrich in P.ENRICH:
            for p_fail in P_FAIL:
                for n in N_GRID:
                    r = run(n, tau, enrich, p_fail, sims, boot, 9000 + cell)
                    r["clustering"] = cl
                    rows.append(r)
                    cell += 1
                    print(r, flush=True)
    OUT.write_text(json.dumps({"engine": "janusm.scar.power/scoring at PR #187 head f5d2b56", "sims": sims,
                               "boot": boot, "anchor": ANCHOR, "ng_bar": NG_BAR, "rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
