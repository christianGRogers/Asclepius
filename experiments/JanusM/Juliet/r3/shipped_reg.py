"""Juliet R3 E10 (Janus-M Round 3, path jm/paired-scar, ruling section 7 items 1 and 5): does the *shipped* JA29
registration module (`janusm.scar.registration`, #181/#188) show the static-chest pull the shared benchmark found
with its SimpleITK reference, and does a 4 mm metric mask remove it?

Cases: the shared LIE benchmark's generator (`experiments/JanusM/bench_lie/bench.py`), every usable heart, blood
'equal', CNR 5 and 3, motions 'rigid' (the heart moves 4 mm / 2 deg against the static chest) and 'none'.
Each heart goes through janusm.guard.refuse first (in bench.load_heart).

Arms, both through `register_lie` exactly as shipped (Mattes MI, Powell, 2 levels, 30k samples):
  mask10  MASK_DILATION_MM = 10 (JA29 as written);
  mask4   MASK_DILATION_MM = 4 (the module constant set before prepare_first_pass).
QC cuts are set so R0 always fails (the chain always registers), so the rigid and affine stages are measured on
every case. Residual (TRE) = mean distance over the truth wall between the module's transform and the true map.

Usage: PYTHONPATH=src python experiments/JanusM/Juliet/r3/shipped_reg.py <ts_dir> [--procs 4]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/bench_lie"))
import bench  # noqa: E402
from fetch import hearts as heart_list  # noqa: E402
from janusm.scar import registration as REG  # noqa: E402

FORCE = REG.QCCuts(max_fatlike=-1.0, max_bloodlike=-1.0, max_brighter_than_blood=-1.0)
CONDS = [("equal", 5, "rigid"), ("equal", 3, "rigid"), ("equal", 5, "none")]


def one(args):
    hid, data = args
    h = bench.load_heart(hid, data)
    if "skip" in h:
        return [{"heart": hid, "skip": h["skip"]}]
    rows = []
    for blood, cnr, motion in CONDS:
        import hashlib
        seed = int(hashlib.sha256(f"bench-lie-r3:{hid}:{blood}:{cnr}:{motion}".encode()).hexdigest()[:8], 16)
        c = bench.make_case(h, blood, cnr, motion, seed)
        if "skip" in c:
            continue
        x, x0 = c["tre_pts"]
        row = {"heart": hid, "blood": blood, "cnr": cnr, "motion": motion}
        for name, mm in (("mask10", 10.0), ("mask4", 4.0)):
            REG.MASK_DILATION_MM = mm
            t0 = time.time()
            fp = REG.prepare_first_pass(c["fp"], c["lab_fp"], bench.A_RAS)
            r = REG.register_lie(fp, c["lie"], bench.A_RAS, FORCE, seed=seed % 1000)
            for st in r.stages:
                row[f"{name}_{st.name}_tre"] = round(float(np.linalg.norm(st.transform.forward(x) - x0, axis=1).mean()), 3)
            row[f"{name}_final"] = r.final.name
            row[f"{name}_sec"] = round(time.time() - t0, 1)
        rows.append(row)
        print(row, flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--resume-log", help="a previous run's stdout: its printed rows are kept, their hearts skipped")
    a = ap.parse_args()
    ids = heart_list() + ["phantom"]                       # guard on the whole list
    prev = []
    if a.resume_log:
        import ast
        prev = [ast.literal_eval(line) for line in open(a.resume_log) if line.startswith("{'heart'")]
        per = {}
        for r in prev:
            per.setdefault(r["heart"], []).append(r)
        full = {h for h, rr in per.items() if len(rr) >= len(CONDS)}
        prev = [r for r in prev if r["heart"] in full]
        ids = [i for i in ids if i not in full]
        print(f"resume: {len(full)} hearts kept from the log", flush=True)
    with Pool(a.procs) as p:
        rows = prev + [r for rs in p.imap_unordered(one, [(i, a.data) for i in ids]) for r in rs]
    out = {"module": "janusm.scar.registration at jm/paired-scar 1524550", "conds": CONDS, "rows": rows}
    summ = {}
    for blood, cnr, motion in CONDS:
        rr = [r for r in rows if r.get("motion") == motion and r.get("cnr") == cnr]
        for k in ("mask10_rigid_tre", "mask10_affine_tre", "mask4_rigid_tre", "mask4_affine_tre"):
            v = [r[k] for r in rr if k in r]
            if v:
                summ[f"{motion}|cnr{cnr}|{k}"] = {"median": round(float(np.median(v)), 3),
                                                   "p90": round(float(np.percentile(v, 90)), 3), "n": len(v)}
    out["summary"] = summ
    (HERE / "e10_shipped_registration.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
