"""Golf R4 E12 (#251 item 3): JA57's planning table, re-run on the shipped power engine with enough simulations that
N is stable.

Engine: `janusm.scar.power` / `scoring` as shipped (SCAR_VERSION 1.1.0), unchanged. Golf's cohort generator, JA55's
split accounting with the yield bar, JA56's two claims. Simulation only: no image, case or identifier.

Cells: failure 0 / 2 / 5 %; clustering weak (tau 0.7) / strong (1.2); enrichment 50 / 70 %; infarct size Golf's
(1 + Poisson(3), 16 segments: 3.99 scarred segments per scar patient) / Kilo's (3.25). Bin error 0.25 and Golf's
sensitivity by bin, as JA57's planning figures used (`JA32_BASE`).

For each cell, the power of
  claim 1 (presence: sensitivity, specificity, yield)  -- what `seal_size` sizes on by default (JA57);
  claim 2 jointly (presence and the Kim bin at anchor 0.70) -- what Juliet E9's "split" column and the ruling's
                                                             planning figures (~160 / ~200) were;
on N = 80 .. 320 (step 20), `SIMS` studies each. N80 is read two ways:
  grid   the smallest grid N from which power stays >= 0.80 (`seal_size`'s rule);
  fit    a logistic fit of pass/fail on N (all studies of the cell), solved for 0.80, with a 95 % interval from a
         parametric bootstrap of the fit -- stable where the grid rule flips between neighbouring N.
The JA57 seal is then max(120; N for 270 scarred segments; N80 of claim 1), capped at 240.

Reproductions (Monte-Carlo z against the committed record): Juliet E9's split cells (weak, 2 %, 50 % at N 200 and
70 % at 160) and Golf E10's segments-needed (Kilo and Golf infarct sizes).

Usage: PYTHONPATH=src python experiments/JanusM/Golf/r4/power_r4.py [--sims 1500] [--boot 400] [--out f] [--procs 1]
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
from janusm.scar import scoring as S

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
N_GRID = tuple(range(80, 321, 20))
ANCHOR = 0.70
SIZES = {"golf": P.expected_scar_segments(1.0, 3.0), "kilo": P.kilo_segments_per_scar_patient()}


def _draw_kilo_k(rng):
    terr = rng.choice(list(P.KILO_TERR), p=[P.KILO_TERR_P[t] for t in P.KILO_TERR])
    return 1 + rng.binomial(len(P.KILO_TERR[terr]) - 1, 0.45)


def _draw_golf_k(rng):
    return min(1 + rng.poisson(3.0), 17)


def fit_n80(ns, passed, target=0.80, reps=400, seed=0):
    """Logistic fit of pass ~ a + b * N (Newton), solved for `target`; parametric-bootstrap 95 % interval."""
    x = np.asarray(ns, float)
    y = np.asarray(passed, float)
    xs = (x - 200.0) / 100.0

    def fit(yy):
        b = np.zeros(2)
        X = np.c_[np.ones_like(xs), xs]
        for _ in range(50):
            p = 1 / (1 + np.exp(-(X @ b)))
            W = p * (1 - p) + 1e-9
            g = X.T @ (yy - p)
            H = X.T @ (X * W[:, None])
            step = np.linalg.solve(H + 1e-9 * np.eye(2), g)
            b += step
            if np.abs(step).max() < 1e-8:
                break
        return b, np.linalg.inv(H)

    b, cov = fit(y)
    lt = math.log(target / (1 - target))

    def solve(bb):
        if bb[1] <= 0:
            return float("inf")
        return 200.0 + 100.0 * (lt - bb[0]) / bb[1]

    rng = np.random.default_rng(seed)
    draws = rng.multivariate_normal(b, cov, reps)
    sol = np.array([solve(d) for d in draws])
    fin = sol[np.isfinite(sol)]
    lo, hi = (np.percentile(fin, [2.5, 97.5]) if fin.size > reps // 2 else (float("nan"), float("nan")))
    return {"n80": round(solve(b), 1), "n80_lo": round(float(lo), 1), "n80_hi": round(float(hi), 1),
            "coef": [round(float(v), 4) for v in b]}


def run_cell(args):
    cl, enrich, p_fail, size, sims, boot, seed = args
    m = SIZES[size]
    params = dict(lam=max(m - 1.0, 0.0), q=0.25, spec=0.98, bin_tau=1.0, tau=P.CLUSTERING[cl], enrich=enrich,
                  p_fail=p_fail, sens_by_bin=P.GOLF_SENS_BY_BIN, bin_w=P.GOLF_BIN_W)
    curve1, curve2, ns, pass1, pass2 = {}, {}, [], [], []
    tic = time.time()
    for i, n in enumerate(N_GRID):
        st = P.simulate_studies(P.golf_cohort, n, sims, boot, seed + i, itd_mode="split", **params)
        lo = {k: np.nan_to_num(st["lower"][k], nan=-np.inf) for k in ("sens", "spec", "tbin")}
        pres = (lo["sens"] >= S.SENS_BAR) & (lo["spec"] >= S.SPEC_BAR) & (np.asarray(st["yield_upper"]) <= S.YIELD_BAR)
        joint = pres & (lo["tbin"] >= S.bars(ANCHOR)["tbin"])
        curve1[n], curve2[n] = float(pres.mean()), float(joint.mean())
        ns += [n] * sims
        pass1 += pres.tolist()
        pass2 += joint.tolist()
    n_seg = P.patients_for_scarred_segments(P.SEAL_SEGMENTS, enrich, m)
    f1, f2 = fit_n80(ns, pass1, seed=seed), fit_n80(ns, pass2, seed=seed + 1)
    g1 = P._first_n_staying_above(curve1, 0.80)
    g2 = P._first_n_staying_above(curve2, 0.80)

    def seal(n80):
        if n80 is None or not np.isfinite(n80):
            return P.SEAL_CAP
        return int(min(max(P.SEAL_FLOOR, n_seg, int(math.ceil(n80))), P.SEAL_CAP))

    return {"clustering": cl, "tau": P.CLUSTERING[cl], "enrich": enrich, "p_fail": p_fail, "infarct_size": size,
            "segs_per_scar_patient": round(m, 3), "n_segments_270": n_seg,
            "power_claim1": {str(k): round(v, 4) for k, v in curve1.items()},
            "power_claim2_joint": {str(k): round(v, 4) for k, v in curve2.items()},
            "mc_se_at_0p8": round(math.sqrt(0.16 / sims), 4),
            "claim1": {"grid_n80": g1, **f1, "seal": seal(f1["n80"]), "seal_grid": seal(g1)},
            "claim2_joint": {"grid_n80": g2, **f2, "seal": seal(f2["n80"]), "seal_grid": seal(g2)},
            "sec": round(time.time() - tic)}


def reproductions(sims, boot):
    out = {}
    jul = json.loads((EXP / "Juliet/r3/e9_itd_power.json").read_text())
    for enrich, n in ((0.5, 200), (0.7, 160)):
        row = next(r for r in jul["rows"] if r["clustering"] == "weak" and r["enrich"] == enrich and r["n"] == n
                   and r["p_fail"] == 0.02)
        params = {**P.JA32_BASE, "tau": P.CLUSTERING["weak"], "enrich": enrich, "p_fail": 0.02}
        st = P.simulate_studies(P.golf_cohort, n, sims, boot, 7700 + n, itd_mode="split", **params)
        now = P.claim_power(st, jul["anchor"])["kim_bin"]
        rec = row["power_split"]
        se = math.sqrt(max(rec * (1 - rec), 0.25 / sims) * (1 / jul["sims"] + 1 / sims))
        out[f"juliet_e9_split_{enrich}_{n}"] = {"recorded": rec, "recorded_sims": jul["sims"], "now": round(now, 4),
                                                "sims": sims, "z": round((now - rec) / se, 2)}
    gol = json.loads((EXP / "Golf/power_ja32.json").read_text())["segments_needed"]
    for size, draw in (("kilo", _draw_kilo_k), ("golf", _draw_golf_k)):
        for enrich in (0.5, 0.7):
            mc = P.segments_needed_mc(np.random.default_rng(10), draw, enrich, sims=4000)
            rec = gol[size][str(enrich)]
            out[f"golf_e10_segments_{size}_{enrich}"] = {"recorded": rec, "now": mc}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=1500)
    ap.add_argument("--boot", type=int, default=400)
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--out", default=str(HERE / "power_r4.json"))
    a = ap.parse_args()
    cells = []
    k = 0
    for cl in P.CLUSTERING:
        for enrich in P.ENRICH:
            for p_fail in P.P_FAIL:
                for size in SIZES:
                    cells.append((cl, enrich, p_fail, size, a.sims, a.boot, 12000 + 100 * k))
                    k += 1
    rows = []
    with Pool(a.procs) as p:
        for r in p.imap_unordered(run_cell, cells):
            print(r["clustering"], r["enrich"], r["p_fail"], r["infarct_size"], "claim1", r["claim1"],
                  "joint", r["claim2_joint"], r["sec"], "s", flush=True)
            rows.append(r)
    rows.sort(key=lambda r: (r["clustering"], r["enrich"], r["p_fail"], r["infarct_size"]))
    res = {"scar_version": SCAR_VERSION, "engine": "janusm.scar.power.simulate_studies (golf_cohort, itd_mode=split)",
           "settings": {"sims": a.sims, "boot": a.boot, "n_grid": list(N_GRID), "anchor_claim2": ANCHOR,
                        "q": 0.25, "spec": 0.98, "bin_tau": 1.0, "sens_by_bin": P.GOLF_SENS_BY_BIN,
                        "bin_w": P.GOLF_BIN_W, "infarct_sizes": SIZES, "seal_floor": P.SEAL_FLOOR,
                        "seal_cap": P.SEAL_CAP, "segments": P.SEAL_SEGMENTS},
           "reproductions": reproductions(a.sims, a.boot), "cells": rows}
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
