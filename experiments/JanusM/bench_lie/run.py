"""Shared synthetic-LIE benchmark: run every heart x condition through every JA29 registration stage and grade every
JA30 menu value on the scarred LIE and on its scar-free twin. Writes one JSON line per case (results.jsonl);
score.py turns them into the tables.

Images per case (same noise): the full LIE; its scar-free twin; and the LIE with blood set to remote.
Arms per case:
  oracle  the truth geometry on the LIE grid (isolates the rule's own error);
  R0      scanner coordinates (identity);
  rigid   Mattes MI rigid, heart-masked;
  affine  Mattes MI affine from rigid, heart-masked;
  rigid_m4  Mattes MI rigid with the mask dilated 4 mm instead of 10 mm (variant, not on the JA29 menu).
(The JA29 chain is assembled in score.py from these arms and the QC values.)

Usage: PYTHONPATH=src python experiments/JanusM/bench_lie/run.py <data_dir> [--hearts s0391,phantom] [--out f]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench  # noqa: E402
import menu  # noqa: E402
from fetch import hearts as heart_list  # noqa: E402  (guard runs on the whole list)

CONDS = [(b, c, m) for b in bench.BLOOD for c in bench.CNRS for m in bench.MOTIONS]


def _r(a, n=3):
    return [None if not np.isfinite(x) else round(float(x), n) for x in np.asarray(a, float)]


def _pack(g):
    return {k: _r(g[k]) for k in ("pk_share", "pg_share", "ev", "ed")} | {
        "remote": round(g["remote"], 1), "rsd": round(g["rsd"], 2), "qc": {k: round(v, 4) for k, v in g["qc"].items()}}


def one_heart(args):
    hid, data_dir = args
    t0 = time.time()
    h = bench.load_heart(hid, data_dir)
    if "skip" in h:
        return [{"heart": hid, "skip": h["skip"]}]
    geo = menu.fp_geometry(h)
    if geo is None:
        return [{"heart": hid, "skip": "AHA failed on the first-pass labels"}]
    rows = []
    for blood, cnr, motion in CONDS:
        seed = int(hashlib.sha256(f"bench-lie-r3:{hid}:{blood}:{cnr}:{motion}".encode()).hexdigest()[:8], 16)
        c = bench.make_case(h, blood, cnr, motion, seed)
        if "skip" in c:
            rows.append({"heart": hid, "blood": blood, "cnr": cnr, "motion": motion, "skip": c["skip"]})
            continue
        row = {"heart": hid, "blood": blood, "cnr": cnr, "motion": motion, "seed": seed,
               "truth_vol": _r(c["truth"]["vol"]), "truth_depth": _r(c["truth"]["depth"]),
               "T_nominal": c["truth"]["T_nominal"], "arms": {}}
        oracle = {"myo": c["lab_t"] == bench.G.MYO, "cav": c["lab_t"] == bench.G.LV, "seg": c["seg_t"],
                  "u": c["u_t"], "phi": c["phi_t"], "s": c["s_t"]}
        arms = [("oracle", None, oracle)]
        tx0 = menu.identity(geo)
        arms.append(("R0", tx0, None))
        rig = menu.register(c["lie"], c["fp"], geo, "rigid", seed=seed % 1000)
        arms.append(("rigid", rig, None))
        aff = menu.register(c["lie"], c["fp"], geo, "affine", init=rig, seed=seed % 1000)
        arms.append(("affine", aff, None))
        rig4 = menu.register(c["lie"], c["fp"], geo, "rigid", seed=seed % 1000, mask="mask4")
        arms.append(("rigid_m4", rig4, None))
        for name, tx, car in arms:
            ta = time.time()
            if car is None:
                car = menu.carry(geo, tx, c["lie"].shape)
            g = menu.grade(c["lie"], car)
            fixed = (g["remote"], g["rsd"], g["thr_k"])
            rec = {"scar": _pack(g),
                   # scar-free heart, graded as a real LGE-negative patient would be (own constants): Kilo 1b
                   "free_own": _pack(menu.grade(c["lie_free"], car)),
                   # scar removed, the scarred image's constants kept: calls made by spill or noise (reported)
                   "free_fixed": _pack(menu.grade(c["lie_free"], car, fixed)),
                   # blood set to remote, scar and constants kept: Golf's spill counterfactual (striking, 1a)
                   "noblood": _pack(menu.grade(c["lie_noblood"], car, fixed))}
            if tx is not None:
                rec["tre_mm"] = round(menu.tre(tx, c["tre_pts"]), 3)
            rec["sec"] = round(time.time() - ta, 1)
            row["arms"][name] = rec
        rows.append(row)
        print(hid, blood, cnr, motion, {k: v.get("tre_mm") for k, v in row["arms"].items()}, flush=True)
    print(hid, "done", round(time.time() - t0), "s", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--hearts")
    ap.add_argument("--out", default=str(HERE / "results.jsonl"))
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--resume", action="store_true", help="keep hearts already complete in --out; run the rest")
    a = ap.parse_args()
    ids = heart_list() + ["phantom"]                       # janusm.guard.refuse runs on the whole list here
    if a.hearts:
        ids = [i for i in a.hearts.split(",") if i in ids]
    done = set()
    if a.resume and Path(a.out).exists():
        rows = [json.loads(line) for line in open(a.out)]
        per = {}
        for r in rows:
            per.setdefault(r["heart"], []).append(r)
        done = {h for h, rr in per.items() if any("skip" in r and "blood" not in r for r in rr) or len(rr) >= len(CONDS)}
        with open(a.out, "w") as f:                        # drop partial hearts, keep complete ones
            for h in done:
                for r in per[h]:
                    f.write(json.dumps(r) + "\n")
        ids = [i for i in ids if i not in done]
    print(f"{len(ids)} hearts x {len(CONDS)} conditions ({len(done)} already complete)", flush=True)
    with Pool(a.procs) as p, open(a.out, "a" if a.resume else "w") as f:
        for rows in p.imap_unordered(one_heart, [(i, a.data_dir) for i in ids]):
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
