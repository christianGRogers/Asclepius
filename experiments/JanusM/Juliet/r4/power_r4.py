"""Juliet R4 E11 (Janus-M Round 4, path jm/paired-scar, #251 item 3): JA57's planning table, on the shipped engine.

Engine: `janusm.scar.power` / `janusm.scar.scoring` as shipped on jm/paired-scar (#248, SCAR_VERSION 1.1.0), used
unchanged: `simulate_studies(golf_cohort, ..., itd_mode="split")` (JA55's split accounting and yield bar) and
`claim_power` (JA56's two ordered claims). The cohort parameters are `seal_size`'s: Golf's cohort, K = 1 +
Poisson(mean - 1), q = 0.25, spec 0.98, Golf's sensitivity by bin and bin shares, bin_tau 1.0.

Grid (#251 item 3): failure 0 / 2 / 5 %; clustering weak (tau 0.7) / strong (1.2); enrichment 50 / 70 %; infarct
size Golf (1 + Poisson(3): 4.0 scarred segments per scar patient) / Kilo (one territory, 1 + Bin(n - 1, 0.45): 3.25);
N 100-320 in steps of 20. Per N: SIMS studies (two independent halves, so N's stability is visible), BOOT
bootstrap replicates each.

Per cell it reports:
  - claim-1 (presence) power, and claim-1-then-2 power (Kim bin at anchors 0.60 / 0.70 / 0.80), per N;
  - N_presence: the first N from which presence power stays >= 0.80 (the JA57 rule), pooled and per half;
  - N_270: patients for >= 270 scarred segments (seal_size's formula);
  - seal_JA57 = min(max(120, N_270, N_presence), 240);
  - N_joint07: the same with claim 2 at anchor 0.70 in the target too (what Juliet E9's "split" column measured).

Reproductions (#251 item 3):
  - Juliet E9 (`Juliet/r3/e9_itd_power.json`, 400 studies): its `power_split` is the joint pass of sensitivity,
    specificity and the Kim bin at anchor 0.70 plus yield, i.e. claim_power(...)["kim_bin"] at 0.70. Every E9
    row with Golf's infarct size is compared with this grid's cell at the same N (z on the two binomial SEs);
  - E9's `power_segment` (JA29 worst case) at 2 % failure, weak clustering, N 200 and 320: re-run in "worst" mode;
  - Golf E10 (`Golf/power_ja32.json` `segments_needed`): `segments_needed_mc` with Kilo's and Golf's draws.

Simulation only: no image, case or identifier. Usage:
  PYTHONPATH=src python experiments/JanusM/Juliet/r4/power_r4.py [--sims 2000 --boot 400 --procs 1]
"""
from __future__ import annotations

import argparse
import json
import math
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from janusm.scar import power as P  # noqa: E402
from janusm.scar import scoring as S  # noqa: E402

N_GRID = tuple(range(100, 321, 20))
INFARCT = {"golf": P.expected_scar_segments(1.0, 3.0), "kilo": P.kilo_segments_per_scar_patient()}
ANCHORS = (0.60, 0.70, 0.80)


def cell_params(infarct, tau, enrich, p_fail):
    m = INFARCT[infarct]
    return dict(enrich=enrich, lam=max(m - 1.0, 0.0), tau=tau, q=0.25, spec=0.98,
                sens_by_bin=tuple(P.GOLF_SENS_BY_BIN), bin_w=tuple(P.GOLF_BIN_W), bin_tau=1.0, p_fail=p_fail)


def seed_of(*key):
    import hashlib
    return int(hashlib.sha256(("juliet-r4-e11:" + ":".join(map(str, key))).encode()).hexdigest()[:8], 16)


def run_point(args):
    infarct, cl, enrich, p_fail, n, sims, boot = args
    params = cell_params(infarct, P.CLUSTERING[cl], enrich, p_fail)
    out = {"infarct": infarct, "clustering": cl, "enrich": enrich, "p_fail": p_fail, "n": n, "halves": []}
    for h in (0, 1):
        st = P.simulate_studies(P.golf_cohort, n, sims // 2, boot, seed_of(infarct, cl, enrich, p_fail, n, h),
                                itd_mode="split", **params)
        rec = {"presence": P.claim_power(st, None)["presence"]}
        for a in ANCHORS:
            rec[f"kim_{a:.2f}"] = P.claim_power(st, a)["kim_bin"]
        rec["tbin_point_median"] = float(np.nanmedian(st["point"]["tbin"]))
        out["halves"].append(rec)
    for k in out["halves"][0]:
        out[k] = float(np.mean([x[k] for x in out["halves"]]))
    return out


def first_n(curve, target=0.80):
    return P._first_n_staying_above(curve, target)


def summarise_cell(points, infarct, enrich):
    m = INFARCT[infarct]
    n270 = P.patients_for_scarred_segments(P.SEAL_SEGMENTS, enrich, m)
    res = {"n_segments_270": n270}
    for key in ("presence", "kim_0.70"):
        pooled = first_n({p["n"]: p[key] for p in points})
        halves = [first_n({p["n"]: p["halves"][h][key] for p in points}) for h in (0, 1)]
        res[f"n_{key}"] = pooled
        res[f"n_{key}_halves"] = halves
    def seal(n_pow):
        need = None if n_pow is None else max(P.SEAL_FLOOR, n270, n_pow)
        return P.SEAL_CAP if need is None or need > P.SEAL_CAP else need
    res["seal_JA57"] = seal(res["n_presence"])
    res["seal_JA57_halves"] = [seal(x) for x in res["n_presence_halves"]]
    res["seal_with_claim2_at_0.70"] = seal(res["n_kim_0.70"] if res["n_presence"] is not None else None) \
        if res["n_kim_0.70"] is not None else P.SEAL_CAP
    res["n_required_uncapped_presence"] = None if res["n_presence"] is None else max(P.SEAL_FLOOR, n270,
                                                                                      res["n_presence"])
    return res


def z(rec, rs, now, ns):
    var = max(rec * (1 - rec), 0.25 / ns)
    return (now - rec) / math.sqrt(var * (1 / rs + 1 / ns))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=2000)
    ap.add_argument("--boot", type=int, default=400)
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--out", default=str(HERE / "e11_power_r4.json"))
    a = ap.parse_args()
    cells = [(i, c, e, f) for i in INFARCT for c in P.CLUSTERING for e in P.ENRICH for f in P.P_FAIL]
    jobs = [(i, c, e, f, n, a.sims, a.boot) for (i, c, e, f) in cells for n in N_GRID]
    part = Path(str(a.out) + ".part.jsonl")
    done = {}
    if part.exists():
        for line in open(part):
            r = json.loads(line)
            done[(r["infarct"], r["clustering"], r["enrich"], r["p_fail"], r["n"])] = r
    todo = [j for j in jobs if tuple(j[:5]) not in done]
    print(f"{len(jobs)} points, {len(todo)} to run", flush=True)
    with Pool(a.procs) as p, open(part, "a") as f:
        for r in p.imap_unordered(run_point, todo):
            done[(r["infarct"], r["clustering"], r["enrich"], r["p_fail"], r["n"])] = r
            f.write(json.dumps(r) + "\n")
            f.flush()
            print(r["infarct"], r["clustering"], r["enrich"], r["p_fail"], r["n"],
                  round(r["presence"], 3), round(r["kim_0.70"], 3), flush=True)
    table = []
    for (i, c, e, fl) in cells:
        pts = sorted([done[(i, c, e, fl, n)] for n in N_GRID], key=lambda r: r["n"])
        table.append({"infarct": i, "segs_per_scar_patient": INFARCT[i], "clustering": c, "tau": P.CLUSTERING[c],
                      "enrich": e, "p_fail": fl, **summarise_cell(pts, i, e),
                      "power_presence": {str(p["n"]): round(p["presence"], 4) for p in pts},
                      "power_kim_0.70": {str(p["n"]): round(p["kim_0.70"], 4) for p in pts}})
    # reproductions
    e9 = json.loads((ROOT / "experiments/JanusM/Juliet/r3/e9_itd_power.json").read_text())
    rep9 = []
    for r in e9["rows"]:
        key = ("golf", r["clustering"], r["enrich"], r["p_fail"], r["n"])
        if key not in done:
            continue
        now = done[key]["kim_0.70"]
        rep9.append({"clustering": r["clustering"], "enrich": r["enrich"], "p_fail": r["p_fail"], "n": r["n"],
                     "recorded_power_split": r["power_split"], "now": round(now, 4),
                     "z": round(z(r["power_split"], e9["sims"], now, a.sims), 2)})
    worst = []
    for n in (200, 320):
        rec = next(r for r in e9["rows"] if r["clustering"] == "weak" and r["enrich"] == 0.5 and r["p_fail"] == 0.02
                   and r["n"] == n)
        nw = min(1000, a.sims)
        st = P.simulate_studies(P.golf_cohort, n, nw, a.boot, seed_of("worst", n), itd_mode="worst",
                                **cell_params("golf", 0.7, 0.5, 0.02))
        now = P.power_from(st, S.bars(0.70))["power_all"]
        worst.append({"n": n, "recorded_power_segment": rec["power_segment"], "now": round(now, 4),
                      "sims": nw, "z": round(z(rec["power_segment"], e9["sims"], now, nw), 2)})
    g10 = json.loads((ROOT / "experiments/JanusM/Golf/power_ja32.json").read_text())["segments_needed"]

    def draw_kilo(rng):
        names = list(P.KILO_TERR)
        terr = P.KILO_TERR[rng.choice(names, p=[P.KILO_TERR_P[k] for k in names])]
        return 1 + rng.binomial(len(terr) - 1, 0.45)

    def draw_golf(rng):
        return min(1 + rng.poisson(3.0), 17)

    rep10 = {}
    for size, draw in (("kilo", draw_kilo), ("golf", draw_golf)):
        for e in (0.5, 0.7):
            mc = P.segments_needed_mc(np.random.default_rng(seed_of("e10", size, e)), draw, e, sims=min(4000, 2 * a.sims))
            rep10[f"{size}|{e}"] = {"recorded": g10[size][str(e)], "now": mc,
                                    "analytic_mean_formula": P.patients_for_scarred_segments(
                                        270, e, INFARCT[size] if size == "kilo" else 4.0)}
    out = {"engine": "janusm.scar.power / scoring on jm/paired-scar (SCAR_VERSION 1.1.0), unchanged",
           "sims_per_point": a.sims, "boot": a.boot, "n_grid": list(N_GRID), "infarct_segs_per_scar_patient": INFARCT,
           "target": 0.80, "cap": P.SEAL_CAP, "floor": P.SEAL_FLOOR, "table": table,
           "reproduce_juliet_e9_split": rep9, "reproduce_juliet_e9_segment_worst": worst,
           "reproduce_golf_e10_segments_needed": rep10,
           "max_abs_z_e9_split": max(abs(r["z"]) for r in rep9) if rep9 else None}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for t in table:
        print(t["infarct"], t["clustering"], t["enrich"], t["p_fail"], "N_pres", t["n_presence"],
              t["n_presence_halves"], "N270", t["n_segments_270"], "seal", t["seal_JA57"], "N_joint.70",
              t["n_kim_0.70"])


if __name__ == "__main__":
    main()
