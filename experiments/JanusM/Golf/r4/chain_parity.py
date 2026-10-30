"""Golf R4 (#251 item 1, pre-registered parity check): does score_v3's assembled chain equal the shipped
`register_lie` run end to end?

For a few benchmark cases (the phantom and two hearts; motions rigid, aniso, phase_neg; CNR 5; blood equal), this
runs `janusm.scar.registration.register_lie` with the same QC cuts score_v3 uses for that case (v3 half split), and
compares its final stage and its TRE with the stage score_v3 assembled from results_v3 (rule `literal`).

Guard first: the heart list goes through janusm.guard.refuse (fetch.hearts), and again per heart (bench.load_heart).
Writes chain_parity.json (summary numbers only).

Usage: PYTHONPATH=src python experiments/JanusM/Golf/r4/chain_parity.py <data_dir> [--hearts a,b]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BL = ROOT / "experiments/JanusM/bench_lie"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(BL))
import bench  # noqa: E402
import menu  # noqa: E402
import score_v3  # noqa: E402
from fetch import hearts as heart_list  # noqa: E402
from janusm.scar import registration as R  # noqa: E402
from run_v3 import to_sitk  # noqa: E402
from score import half, load  # noqa: E402

CONDS = [("equal", 5, m) for m in ("rigid", "aniso", "phase_neg")]
STAGE = {"R0": "R0", "rigid": "rigid4", "affine": "affine4", "rigid10": "rigid10"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--hearts", default="phantom")
    a = ap.parse_args()
    ids = heart_list() + ["phantom"]                     # guard on the whole list first
    rows, _ = load(BL / "results_v3.jsonl")
    cuts = score_v3.fit_cuts(rows)
    by = {(r["heart"], r["blood"], r["cnr"], r["motion"]): r for r in rows}
    out = []
    for hid in [h for h in a.hearts.split(",") if h in ids]:
        h = bench.load_heart(hid, Path(a.data_dir))     # guard again, per heart
        if "skip" in h:
            continue
        fp = R.prepare_first_pass(h["ct"], h["lab"], bench.A_RAS, case_id=None if hid == "phantom" else hid)
        for blood, cnr, motion in CONDS:
            r = by.get((hid, blood, cnr, motion))
            if r is None:
                continue
            seed = int(hashlib.sha256(f"bench-lie-r3:{hid}:{blood}:{cnr}:{motion}".encode()).hexdigest()[:8], 16)
            c = bench.make_case(h, blood, cnr, motion, seed)
            q = cuts[(half(hid), blood, cnr)]
            reg = R.register_lie(fp, c["lie"], bench.A_RAS, q, seed=seed % 1000,
                                 case_id=None if hid == "phantom" else hid)
            assembled = score_v3.chain(r, q, "literal")
            shipped = STAGE[reg.final.name]
            tre = menu.tre(to_sitk(reg.final.transform), c["tre_pts"])
            out.append({"heart": hid, "blood": blood, "cnr": cnr, "motion": motion,
                        "register_lie_final": shipped, "assembled_final": assembled, "match": shipped == assembled,
                        "register_lie_tre_mm": round(tre, 3), "assembled_tre_mm": r["arms"][assembled]["tre_mm"],
                        "stages_run": [s.name for s in reg.stages],
                        "phase_flags": reg.phase.flags if reg.phase else None})
            print(out[-1], flush=True)
    res = {"n": len(out), "n_match": sum(o["match"] for o in out),
           "max_abs_tre_diff_mm_when_match": max([abs(o["register_lie_tre_mm"] - o["assembled_tre_mm"])
                                                  for o in out if o["match"]] or [None]) if out else None,
           "cases": out}
    (HERE / "chain_parity.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
