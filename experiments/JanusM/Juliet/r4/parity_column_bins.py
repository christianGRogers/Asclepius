"""Juliet R4 (#251 item 1, PS3-S7): why `module_parity.py` fails on real hearts, and what fixes it.

`bench_lie/module_parity.py` (shipped scar0, SCAR_VERSION 1.1.0) disagrees with the benchmark's `menu.grade` on most
real hearts; it passes on the phantom, which is what CI tests. E-V and P-G agree within 0.001; only E-D differs.
The cause is one constant: an E-D column counts in the module only if it spans >= 6 depth bins
(`JA30Constants.column_min_bins = 6`), and in the benchmark, which decided the menu (JA54), if it spans >= 4
(`bench.depth_extent`, `ccnt >= 4`).

This re-runs module_parity's own `parity()` on every guard-allowed heart twice: once with the module as shipped,
and once with `column_min_bins = 4` passed in as the `constants` argument (an experiment-side override; nothing
under src/ changes). It writes the summary per variant.

Guard: fetch.hearts() on the whole list, and bench.load_heart per heart.
Usage: OMP_NUM_THREADS=1 PYTHONPATH=src python experiments/JanusM/Juliet/r4/parity_column_bins.py <data_dir>
"""
from __future__ import annotations

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
from fetch import hearts as heart_list  # noqa: E402
from janusm.scar import scar0 as S  # noqa: E402

SHIPPED = S.scar0


def with_min_bins(n):
    def f(lie, car, **kw):
        kw.setdefault("constants", dataclasses.replace(S.JA30Constants(), column_min_bins=n))
        return SHIPPED(lie, car, **kw)
    return f


def main():
    data = Path(sys.argv[1])
    ids = heart_list()                                   # guard on the whole list
    out = {}
    for name, fn in (("shipped_min_bins_6", SHIPPED), ("min_bins_4", with_min_bins(4))):
        S.scar0 = fn
        rows = []
        for hid in ids:
            h = bench.load_heart(hid, data)              # guard again
            if "skip" in h:
                rows.append({"heart": hid, "skip": h["skip"]})
                continue
            rows += MP.parity(h)
        s = MP.summary(rows)
        s["hearts_all_pass"] = sum(all(r["pass"] for r in rows if r.get("heart") == hid and "pass" in r)
                                   for hid in {r["heart"] for r in rows if "pass" in r})
        s["n_hearts"] = len({r["heart"] for r in rows if "pass" in r})
        out[name] = s
        print(name, json.dumps(s), flush=True)
    S.scar0 = SHIPPED
    (HERE / "parity_column_bins.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
