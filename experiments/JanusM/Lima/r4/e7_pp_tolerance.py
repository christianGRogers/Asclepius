"""Lima R4 E7: how close the shipped pp estimators come to JA39's 0.03 / 0.07 mm (issue #205 item 6).

Runs the same 2 grids x 3 walls x 2 borders x 6 shifts as
``tests/test_janusm_harness.py::test_e6_pp_within_ja39_tolerances`` (its phantom and truth
helpers are imported from the test file, unchanged) and records the raw errors, so the effect of
the test's two-decimal rounding can be read off. Phantoms only; no case is opened.

    python experiments/JanusM/Lima/r4/e7_pp_tolerance.py OUT.json
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from janusm import guard  # noqa: E402
from janusm import harness as H  # noqa: E402

spec = importlib.util.spec_from_file_location("th", REPO / "tests" / "test_janusm_harness.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def main(out):
    guard.refuse([], what="Lima R4 E7 (phantoms; no case is opened)")
    rows = []
    for sp in [(0.5, 0.5, 0.5), (0.4, 0.4, 0.5)]:
        for rot, rough in [(None, False), (23, False), (11, True)]:
            Fc, Fs, base, roi = T._e6_phantom(sp, rot, rough)
            for border, F in (("endo", Fc), ("epi", Fs)):
                ref = (F < 0) & (base < 0)
                for shift in (-1.0, -0.5, -0.25, 0.25, 0.5, 1.0):
                    test = ((F - shift) < 0) & (base < 0)
                    tb, ta = T._e6_truth(F, shift, sp, roi)
                    rows.append({"grid": sp, "rot": rot, "rough": rough, "border": border,
                                 "shift": shift, "tol": T._ja39_tolerance(shift),
                                 "err_assd": abs(H.assd_pp(ref, test, sp, roi) - ta),
                                 "err_bias": abs(H.signed_bias_pp(ref, test, sp, roi) - tb)})
    for key in ("err_assd", "err_bias"):
        for tol in (0.03, 0.07):
            sub = [r for r in rows if r["tol"] == tol]
            worst = max(sub, key=lambda r: r[key])
            print(key, "tol", tol, "worst", round(worst[key], 4), "strict fails",
                  sum(r[key] > tol for r in sub), "of", len(sub), worst["grid"], worst["rot"],
                  worst["rough"], worst["border"], worst["shift"])
    Path(out).write_text(json.dumps({"experiment": "Lima R4 E7",
                                     "harness_version": H.HARNESS_VERSION, "rows": rows},
                                    indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(HERE / "e7_pp_tolerance.json"))
