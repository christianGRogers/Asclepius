"""Juliet R4 (#251 item 1): does score_v3's replay of the JA51 chain match `register_lie` run directly?

score_v3.py emulates the shipped chain on stages logged by run_v3.py. This re-runs the shipped
`janusm.scar.registration.register_lie` itself, end to end, on a sample of benchmark cases. The sample covers
the phantom and one public heart, all 8 motions, blood 'equal', CNR 5. Each run uses the same seed, mask and QC
cuts (score_v3.fit_cuts on results_v3), and the check compares the final stage, the stages run and the final TRE
with the replay.

Guard: fetch.hearts() on the whole list, and bench.load_heart per heart, before any file is opened.
Usage: OMP_NUM_THREADS=1 PYTHONPATH=src python experiments/JanusM/Juliet/r4/replay_check.py <data_dir> [hearts]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/bench_lie"))
sys.path.insert(0, str(HERE))
import bench  # noqa: E402
import score as S3  # noqa: E402
import score_v3_juliet as V3  # noqa: E402
import bench_r4  # noqa: E402,F401
from fetch import hearts as heart_list  # noqa: E402
from janusm.scar import registration as REG  # noqa: E402


def main():
    data = Path(sys.argv[1])
    want = sys.argv[2].split(",") if len(sys.argv) > 2 else ["phantom", "s0230"]
    ids = heart_list() + ["phantom"]                    # guard on the whole list
    rows, _ = V3.load(HERE / "results_v3_juliet.jsonl.gz")
    cuts = V3.fit_cuts(rows)
    by = {(r["heart"], r["blood"], r["motion"]): r for r in rows}
    out = []
    for hid in [h for h in want if h in ids]:
        h = bench.load_heart(hid, data)                 # guard again
        fp = REG.prepare_first_pass(h["ct"], h["lab"], bench.A_RAS)
        for m in V3.MOTIONS:
            r = by.get((hid, "equal", m))
            if r is None:
                continue
            c = bench_r4.make_case(h, "equal", 5, m, r["seed"])
            cut = cuts[(S3.half(hid), "equal")]
            reg = REG.register_lie(fp, c["lie"], bench.A_RAS, cut, seed=r["seed"] % 1000)
            x, x0 = c["tre_pts"]
            tre = float(np.linalg.norm(reg.final.transform.forward(x) - x0, axis=1).mean())
            final, run, ph = V3.replay(r, cut, "L")
            out.append({"heart": hid, "motion": m, "module_final": reg.final.name,
                        "module_stages": [s.name for s in reg.stages], "replay_final": final, "replay_stages": run,
                        "module_tre": round(tre, 3), "replay_tre": r["arms"][final]["tre_mm"],
                        "module_phase_flags": reg.phase.flags, "replay_phase_flags": ph["flags"],
                        "match": reg.final.name == final and [s.name for s in reg.stages] == run})
            print(out[-1], flush=True)
    res = {"n": len(out), "n_match": sum(o["match"] for o in out), "rows": out}
    (HERE / "replay_check.json").write_text(json.dumps(res, indent=1) + "\n")
    print(res["n"], res["n_match"])


if __name__ == "__main__":
    main()
