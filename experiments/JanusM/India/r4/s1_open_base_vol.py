"""India R4, S1 gap check: the guard's volume estimator (harness.signed_bias) on an OPEN wall.

Real LV masks are cut at the mitral/aortic base, like Hotel E6's phantom. JA37 says the bias is
taken in a band that excludes <= 3 mm from the LA and aorta; harness.signed_bias has no region
argument and uses the whole mask, whose area includes the fixed base cap. This measures the
whole-mask error near the 0.3 mm guard, beside pp with the test's ROI (6 mm off the base).
Synthetic phantoms only (the test's _e6_phantom); no case is opened.
Run from the repo root:  python experiments/JanusM/India/r4/s1_open_base_vol.py
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
            for shift in (-0.5, -0.3, 0.3, 0.5):
                test = ((F - shift) < 0) & (base < 0)
                tb, _ = T._e6_truth(F, shift, sp, roi)
                rows.append(dict(sp=list(sp), rot=rot, rough=rough, border=border, shift=shift,
                                 true_bias=round(tb, 4),
                                 vol_whole_err=round(H.signed_bias(ref, test, sp) - tb, 4),
                                 pp_roi_err=round(H.signed_bias_pp(ref, test, sp, roi) - tb, 4)))
summ = {}
for s in (-0.5, -0.3, 0.3, 0.5):
    r = [x for x in rows if x["shift"] == s]
    summ[str(s)] = {"vol_whole_err_worst": max((x["vol_whole_err"] for x in r), key=abs),
                    "vol_whole_err_mean": round(sum(x["vol_whole_err"] for x in r) / len(r), 4),
                    "pp_roi_err_worst": max((x["pp_roi_err"] for x in r), key=abs)}
out = {"harness_version": H.HARNESS_VERSION, "n": len(rows), "by_shift": summ, "rows": rows}
pathlib.Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=1))
print(json.dumps(summ, indent=1))
