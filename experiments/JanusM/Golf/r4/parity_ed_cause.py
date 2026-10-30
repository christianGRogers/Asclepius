"""Golf R4: why module_parity.json fails on E-D. Re-runs bench_lie/module_parity.parity on the given hearts with the
module's E-D column minimum set to the benchmark's (4 depth bins instead of JA30Constants.column_min_bins = 6).
Diagnostic only (nothing in src/ changes): the constant is passed through scar0's `constants` argument.
Guard first (fetch.hearts on the whole list; bench.load_heart per heart). Writes parity_ed_cause.json.

Usage: PYTHONPATH=src python experiments/JanusM/Golf/r4/parity_ed_cause.py <data_dir> --hearts a,b
"""
import argparse
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
from janusm.scar import PASSED  # noqa: E402
from janusm.scar import scar0 as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("data_dir")
ap.add_argument("--hearts", required=True)
a = ap.parse_args()
ids = heart_list()
out = {}
for min_bins in (S.JA30.column_min_bins, 4):
    c = dataclasses.replace(S.JA30, column_min_bins=min_bins)

    def module_values(lie, car, c=c):
        res = S.scar0(lie, car, status=PASSED, constants=c)
        import numpy as np
        v = {k: np.full(17, np.nan) for k in MP.KEYS}
        for s, row in res.segments.items():
            if row["graded"]:
                v["ev"][s - 1], v["ed"][s - 1], v["pg_share"][s - 1] = row["share_ev"], row["extent_ed"], row["share_pg"]
        return v

    MP.module_values = module_values
    rows = []
    for hid in [h for h in a.hearts.split(",") if h in ids]:
        h = bench.load_heart(hid, Path(a.data_dir))
        if "skip" not in h:
            rows += MP.parity(h)
    out[f"column_min_bins={min_bins}"] = MP.summary(rows)
    print(min_bins, out[f"column_min_bins={min_bins}"], flush=True)
(HERE / "parity_ed_cause.json").write_text(json.dumps(out, indent=1) + "\n")
