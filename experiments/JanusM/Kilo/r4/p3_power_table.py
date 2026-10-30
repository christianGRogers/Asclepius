"""Kilo R4 P3 (Janus-M Round 4, path jm/paired-scar, #251 item 3): JA57's planning table on the SHIPPED engine
(``janusm.scar.power`` / ``scoring``, PS3-S8-S10, SCAR_VERSION 1.1.0), with enough simulations that N is stable.

Cells: failure 0 / 2 / 5 %; clustering weak (tau 0.7) / strong (1.2); enrichment 50 / 70 %; infarct size Golf
(1 + Poisson(3), 4.0 scarred segments per scar patient) / Kilo (3.25 per scar patient, entered as Golf's cohort with
lam = 2.25, as ``seal_size`` does). Everything else is the engine's JA32 base (q 0.25, spec 0.98, bin_tau 1.0, Golf's
sensitivity by bin and bin shares), scored with JA55's split accounting and the yield bar.

Per cell and N on the grid 100-240 (step 20) the same simulated studies give
  - claim 1 power (presence: sensitivity, specificity, yield): what ``seal_size`` sizes on (JA57);
  - claim 2 power at anchor 0.70 (presence AND the Kim bin): the joint pass Juliet E9 and the ruling's planning
    figures used.
N is ``seal_size``'s rule: the first grid N from which power stays >= 0.80; seal = max(120; 270-segment N; N),
capped at 240. Two independent seeds of SIMS studies each: N is "stable" if both seeds give the same N.
Stability at 300 sims (what the #248 engineer ran) is shown on the headline cells by 10 seeds.

Reproductions (within Monte-Carlo error, z = difference / combined binomial SE):
  - Juliet E9 (``Juliet/r3/e9_itd_power.json``): every split row, claim 2 at anchor 0.70;
  - Golf E10 (``Golf/power_ja32.json``): ``segments_needed`` for both infarct sizes.

Simulation only: no image, case or identifier is read or written.
Usage: PYTHONPATH=src python experiments/JanusM/Kilo/r4/p3_power_table.py [--sims 2000] [--procs 3]
"""
from __future__ import annotations

import argparse
import json
import math
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from janusm.scar import SCAR_VERSION
from janusm.scar import power as P

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
GRID = (100, 120, 140, 160, 180, 200, 220, 240)
SIZES = {"golf": P.expected_scar_segments(1.0, 3.0), "kilo": P.kilo_segments_per_scar_patient()}
ANCHOR = 0.70
BOOT = 400


def cell_curve(args):
    p_fail, clus, enrich, size, n, sims, seed = args
    segs = SIZES[size]
    params = {**P.JA32_BASE, "lam": max(segs - 1.0, 0.0), "tau": P.CLUSTERING[clus], "enrich": enrich,
              "p_fail": p_fail}
    st = P.simulate_studies(P.golf_cohort, n, sims, BOOT, seed, itd_mode="split", **params)
    cp = P.claim_power(st, ANCHOR)
    return (p_fail, clus, enrich, size, n, seed), {"presence": cp["presence"], "kim_bin": cp["kim_bin"]}


def juliet_row(args):
    row, sims, seed = args
    params = {**P.JA32_BASE, "tau": row["tau"], "enrich": row["enrich"], "p_fail": row["p_fail"]}
    st = P.simulate_studies(P.golf_cohort, row["n"], sims, BOOT, seed, itd_mode="split", **params)
    return row, P.claim_power(st, ANCHOR)["kim_bin"]


def z(rec, rec_sims, now, sims):
    """Pooled two-proportion z (finite when either power is 0 or 1)."""
    pool = (rec * rec_sims + now * sims) / (rec_sims + sims)
    var = max(pool * (1 - pool), 1e-12)
    return (now - rec) / math.sqrt(var * (1 / rec_sims + 1 / sims))


def first_stay(curve, target=0.80):
    return P._first_n_staying_above({int(k): v for k, v in curve.items()}, target)


def seal_of(n_power, enrich, size):
    n_seg = P.patients_for_scarred_segments(P.SEAL_SEGMENTS, enrich, SIZES[size])
    need = None if n_power is None else max(P.SEAL_FLOOR, n_seg, n_power)
    return {"n_power": n_power, "n_segments_270": n_seg, "seal": P.SEAL_CAP if need is None else min(need, P.SEAL_CAP),
            "capped": need is None or need > P.SEAL_CAP}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=2000)
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--out", default=str(HERE / "p3_power_table.json"))
    a = ap.parse_args()
    t0 = time.time()
    cells = [(pf, cl, en, sz) for pf in P.P_FAIL for cl in P.CLUSTERING for en in P.ENRICH for sz in SIZES]
    seeds = {"A": 251_000, "B": 251_500}
    jobs = [(*c, n, a.sims, seeds[s] + 10 * GRID.index(n) + 1000 * ci)
            for ci, c in enumerate(cells) for n in GRID for s in seeds]
    # 300-sim stability on the headline cells (weak clustering, 2 % failure, both enrichments, Golf size)
    head = [(0.02, "weak", en, "golf") for en in P.ENRICH]
    jobs300 = [(*c, n, 300, 900_000 + 37 * k + GRID.index(n)) for c in head for k in range(10) for n in GRID]
    jrec = json.loads((EXP / "Juliet/r3/e9_itd_power.json").read_text())
    jjobs = [(r, 1000, 700_000 + i) for i, r in enumerate(jrec["rows"])]
    with Pool(a.procs) as p:
        res = dict(p.map(cell_curve, jobs, chunksize=1))
        res300 = dict(p.map(cell_curve, jobs300, chunksize=1))
        jres = p.map(juliet_row, jjobs, chunksize=1)
    table = []
    for ci, (pf, cl, en, sz) in enumerate(cells):
        out = {"p_fail": pf, "clustering": cl, "enrich": en, "infarct_size": sz,
               "segs_per_scar_patient": round(SIZES[sz], 3)}
        for s, sd in seeds.items():
            cur = {claim: {n: res[(pf, cl, en, sz, n, sd + 10 * GRID.index(n) + 1000 * ci)][claim] for n in GRID}
                   for claim in ("presence", "kim_bin")}
            out[f"seed{s}"] = {"power_presence": cur["presence"], "power_claim2_anchor070": cur["kim_bin"],
                               "claim1": seal_of(first_stay(cur["presence"]), en, sz),
                               "claim1_and_2": seal_of(first_stay(cur["kim_bin"]), en, sz)}
        for k in ("claim1", "claim1_and_2"):
            out[f"stable_{k}"] = out["seedA"][k]["seal"] == out["seedB"][k]["seal"]
        table.append(out)
    stab = []
    for c in head:
        ns = []
        for k in range(10):
            cur = {n: res300[(*c, n, 900_000 + 37 * k + GRID.index(n))]["presence"] for n in GRID}
            ns.append(seal_of(first_stay(cur), c[2], c[3])["seal"])
        stab.append({"cell": dict(zip(("p_fail", "clustering", "enrich", "infarct_size"), c)), "sims": 300,
                     "seal_claim1_by_seed": ns})
    jout = [{"n": r["n"], "clustering": r["clustering"], "enrich": r["enrich"], "p_fail": r["p_fail"],
             "recorded": r["power_split"], "now": now, "z": round(z(r["power_split"], jrec["sims"], now, 1000), 2)}
            for r, now in jres]
    golf = json.loads((EXP / "Golf/power_ja32.json").read_text())["segments_needed"]

    def draw_kilo(rng):
        names = list(P.KILO_TERR)
        terr = P.KILO_TERR[names[rng.choice(3, p=[P.KILO_TERR_P[k] for k in names])]]
        return 1 + rng.binomial(len(terr) - 1, 0.45)

    def draw_golf(rng):
        return min(1 + rng.poisson(3.0), 17)

    gout = []
    for size, draw in (("kilo", draw_kilo), ("golf", draw_golf)):
        for en in P.ENRICH:
            mc = P.segments_needed_mc(np.random.default_rng(10), draw, en, sims=8000)
            gout.append({"infarct_size": size, "enrich": en, "recorded": golf[size][str(en)], "now": mc})
    out = {"engine": f"janusm.scar.power / scoring, SCAR_VERSION {SCAR_VERSION}", "sims": a.sims, "boot": BOOT,
           "grid": GRID, "anchor_claim2": ANCHOR, "seeds": seeds, "table": table, "stability_300": stab,
           "reproduce_juliet_e9": {"sims": 1000, "rows": jout,
                                   "max_abs_z": max(abs(r["z"]) for r in jout),
                                   "n_abs_z_over_2": sum(abs(r["z"]) > 2 for r in jout), "n": len(jout)},
           "reproduce_golf_e10": gout, "seconds": round(time.time() - t0)}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("stability_300", "seconds")}, indent=1))


if __name__ == "__main__":
    main()
