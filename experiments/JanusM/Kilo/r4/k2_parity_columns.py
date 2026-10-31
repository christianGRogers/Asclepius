"""Kilo R4 K2 (#251 item 1): why module_parity.json fails on real hearts, and the fix to specify.

module_parity.py (shipped PS3-S7 script, run unchanged) finds E-V and P-G agreeing with the benchmark everywhere but
E-D differing. The shipped Scar-0 counts a depth column only if it spans >= 6 of its 10 depth bins
(``scar0.JA30Constants.column_min_bins = 6``); the benchmark that decided the menu (``bench.depth_extent``) counts
columns spanning >= 4. This re-runs the same parity on the same cases with the module's constant set to 4 *in this
process only* (src/ is not changed). If parity then passes, the constant is the whole difference.

Guard first: fetch.hearts() runs janusm.guard.refuse on the whole list; bench.load_heart again per heart.
Usage: PYTHONPATH=src python experiments/JanusM/Kilo/r4/k2_parity_columns.py <data_dir>
"""
import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/bench_lie"))
import bench  # noqa: E402
import module_parity as MP  # noqa: E402
from fetch import hearts  # noqa: E402
from janusm.scar import scar0 as S  # noqa: E402


def main(data_dir):
    ids = hearts()                                            # guard on the whole list, first
    S.JA30 = dataclasses.replace(S.JA30, column_min_bins=4)   # this process only
    S.scar0.__defaults__ = tuple(S.JA30 if isinstance(d, S.JA30Constants) else d
                                 for d in (S.scar0.__defaults__ or ()))
    if S.scar0.__kwdefaults__:
        S.scar0.__kwdefaults__ = {k: (S.JA30 if isinstance(v, S.JA30Constants) else v)
                                  for k, v in S.scar0.__kwdefaults__.items()}
    rows = []
    for hid in ids:
        h = bench.load_heart(hid, Path(data_dir))             # guard again
        if "skip" in h:
            rows.append({"heart": hid, "skip": h["skip"]})
            continue
        rows += MP.parity(h)
        print(hid, [r.get("pass") for r in rows if r["heart"] == hid], flush=True)
    out = {"what": "module_parity with scar0 column_min_bins = 4 (the benchmark's), this process only",
           "summary": MP.summary(rows), "cases": rows}
    (HERE / "k2_parity_columns4.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
