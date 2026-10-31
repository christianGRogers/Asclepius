"""Golf R4 E12b (#251 item 3): what development failure rate a seal of 160 / 200 / 240 tolerates.

Same engine and settings as power_r4.py (golf_cohort, JA55 split, claim 1), at 70 % enrichment (JA57's target) and
50 %, both clusterings and both infarct sizes, failure 0.5-4 %. 1000 studies a cell. Simulation only.

Usage: PYTHONPATH=src python experiments/JanusM/Golf/r4/power_fail_tolerance.py
"""
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from janusm.scar import power as P
from janusm.scar import scoring as S

HERE = Path(__file__).resolve().parent
SIZES = {"golf": P.expected_scar_segments(1.0, 3.0), "kilo": P.kilo_segments_per_scar_patient()}
P_FAIL = (0.005, 0.01, 0.015, 0.02, 0.03, 0.04)
NS = (160, 200, 240)
SIMS, BOOT = 1000, 400


def cell(args):
    cl, enrich, size, pf, n, seed = args
    m = SIZES[size]
    params = dict(lam=m - 1.0, q=0.25, spec=0.98, bin_tau=1.0, tau=P.CLUSTERING[cl], enrich=enrich, p_fail=pf)
    st = P.simulate_studies(P.golf_cohort, n, SIMS, BOOT, seed, itd_mode="split", **params)
    lo = {k: np.nan_to_num(st["lower"][k], nan=-np.inf) for k in ("sens", "spec")}
    pres = (lo["sens"] >= S.SENS_BAR) & (lo["spec"] >= S.SPEC_BAR) & (st["yield_upper"] <= S.YIELD_BAR)
    return {"clustering": cl, "enrich": enrich, "infarct_size": size, "p_fail": pf, "n": n,
            "power_claim1": round(float(pres.mean()), 4),
            "power_sens_only": round(float((lo["sens"] >= S.SENS_BAR).mean()), 4),
            "sens_point_median": round(float(np.nanmedian(st["point"]["sens"])), 4)}


if __name__ == "__main__":
    jobs, k = [], 0
    for cl in P.CLUSTERING:
        for enrich in (0.5, 0.7):
            for size in SIZES:
                for pf in P_FAIL:
                    for n in NS:
                        jobs.append((cl, enrich, size, pf, n, 31000 + k))
                        k += 1
    with Pool(2) as p:
        rows = p.map(cell, jobs)
    (HERE / "power_fail_tolerance.json").write_text(json.dumps(
        {"sims": SIMS, "boot": BOOT, "settings": "golf_cohort, q 0.25, spec 0.98, bin_tau 1.0, split", "rows": rows},
        indent=1) + "\n")
    for r in rows:
        print(r)
