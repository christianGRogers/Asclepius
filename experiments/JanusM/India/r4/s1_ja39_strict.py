"""India R4, item 6 note 1: the shipped pp ASSD / pp bias errors on the shipped E6 test conditions,
compared with JA39's tolerances strictly and at two decimals (as the shipped test does).

Synthetic phantoms only (the test's own _e6_phantom); no case is opened. CPU, ~1 min.
Run from the repo root:  python experiments/JanusM/India/r4/s1_ja39_strict.py
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("th", ROOT / "tests" / "test_janusm_harness.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
H = T.H

rows = []
for sp in [(0.5, 0.5, 0.5), (0.4, 0.4, 0.5)]:
    for rot, rough in [(None, False), (23, False), (11, True)]:
        Fc, Fs, base, roi = T._e6_phantom(sp, rot, rough)
        for border, F in (("endo", Fc), ("epi", Fs)):
            ref = (F < 0) & (base < 0)
            for shift in (-1.0, -0.5, -0.25, 0.25, 0.5, 1.0):
                test = ((F - shift) < 0) & (base < 0)
                tb, ta = T._e6_truth(F, shift, sp, roi)
                eb = H.signed_bias_pp(ref, test, sp, roi) - tb
                ea = H.assd_pp(ref, test, sp, roi) - ta
                tol = T._ja39_tolerance(shift)
                rows.append(dict(sp=list(sp), rot=rot, rough=rough, border=border, shift=shift,
                                 tol=tol, err_assd=round(float(ea), 5), err_bias=round(float(eb), 5),
                                 strict_fail=bool(max(abs(ea), abs(eb)) > tol),
                                 rounded_fail=bool(round(max(abs(ea), abs(eb)), 2) > tol)))
half = [r for r in rows if abs(r["shift"]) <= 0.5]
out = {
    "harness_version": H.HARNESS_VERSION,
    "n_conditions": len(rows),
    "worst_abs_err_upto_0p5": max(max(abs(r["err_assd"]), abs(r["err_bias"])) for r in half),
    "worst_abs_err_at_1p0": max(max(abs(r["err_assd"]), abs(r["err_bias"]))
                                for r in rows if abs(r["shift"]) == 1.0),
    "strict_failures": [r for r in rows if r["strict_fail"]],
    "rounded_failures": [r for r in rows if r["rounded_fail"]],
    "rows": rows,
}
p = pathlib.Path(__file__).with_suffix(".json")
p.write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
