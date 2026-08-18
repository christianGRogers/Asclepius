"""Self-test for the Slicer module, run inside Slicer's own Python.

The widget needs a running Slicer application, so this cannot live in the pytest
suite. Run it with::

    "C:\\...\\Slicer.exe" --no-splash --python-script tests\\slicer_selftest.py \\
        --run-dir C:\\segtrain\\runs\\Dataset710_Coronary__fold0

It exercises the parts that actually break: importing the stdlib-only event
reader out of ``src/``, folding a real event stream into run state, building the
MRML plot nodes, and importing a preview segmentation with named, coloured
segments. Exits non-zero on failure so it can gate a release.
"""

import os
import sys
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_DIR = os.path.join(REPO, "slicer", "SegmentatorTrainMonitor")


def _arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main():
    run_dir = _arg("--run-dir")
    failures = []

    def check(name, condition, detail=""):
        status = "PASS" if condition else "FAIL"
        print("  [{}] {}{}".format(status, name, (" -- " + detail) if detail else ""))
        if not condition:
            failures.append(name)

    print("Slicer self-test for SegmentatorTrainMonitor")
    print(f"  module dir: {MODULE_DIR}")

    if MODULE_DIR not in sys.path:
        sys.path.insert(0, MODULE_DIR)

    import slicer

    print("\n1. import")
    import SegmentatorTrainMonitor as mod

    check("module imports", True)
    check("segtrain.events importable from src/", mod._IMPORT_ERROR is None,
          mod._IMPORT_ERROR or "")

    print("\n2. helpers")
    colour = mod._colorForName("liver")
    check("colour is a valid rgb triple",
          len(colour) == 3 and all(0.0 <= c <= 1.0 for c in colour), str(colour))
    check("colour is stable for a name", mod._colorForName("liver") == colour)
    check("colours differ between structures",
          mod._colorForName("liver") != mod._colorForName("spleen"))

    from SegmentatorTrainMonitorLib import make_source

    check("local location -> local source", make_source(r"C:\runs\x").kind == "local")
    check("windows drive is not mistaken for a host",
          make_source(r"C:\segtrain\runs").kind == "local")
    check("user@host:/path -> ssh source",
          make_source("me@gpu:/data/runs/x").kind == "ssh")

    print("\n3. logic")
    logic = mod.SegmentatorTrainMonitorLogic()

    if not run_dir or not os.path.isdir(run_dir):
        print("  (skipped: pass --run-dir <a completed run> to exercise these)")
    else:
        check("connects to run directory", logic.connect(run_dir), logic.lastError or "")
        state = logic.state
        check("parsed epoch events", len(state.epochs) > 0,
              f"{len(state.epochs)} epochs")
        check("run metadata present", bool(state.meta.get("class_names")),
              "{} class names".format(len(state.meta.get("class_names") or [])))
        check("summary renders", bool(logic.summary()), logic.summary())

        logic.updatePlots()
        check("plot table built", logic._tableNode is not None)
        if logic._tableNode:
            rows = logic._tableNode.GetTable().GetNumberOfRows()
            check("plot table has a row per epoch", rows == len(state.epochs),
                  f"{rows} rows")
        check("chart has three series", len(logic._seriesNodes) == 3)

        scores = logic.latestClassScores()
        check("per-class scores available", len(scores) > 0,
              f"{len(scores)} structures")
        check("scores sorted weakest first",
              all(scores[i][1] <= scores[i + 1][1] for i in range(len(scores) - 1)))

        if state.previews:
            preview = state.previews[-1]
            ok = logic.loadPreview(preview, withReference=False)
            check("preview loads into the scene", ok, logic.lastError or "")
            if ok and logic._segmentationNode:
                seg = logic._segmentationNode.GetSegmentation()
                n = seg.GetNumberOfSegments()
                check("segments imported", n > 0, f"{n} segments")
                names = [seg.GetNthSegment(i).GetName() for i in range(min(n, 400))]
                known = set(state.meta.get("class_names") or [])
                named = [x for x in names if x in known]
                check("segments carry anatomical names", len(named) > 0,
                      "e.g. {}".format(", ".join(named[:4]) if named else "none"))
            # Reloading the same preview must be a no-op, or the 3D view would
            # reset its camera on every poll.
            check("re-loading the same preview is a no-op",
                  logic.loadPreview(preview, withReference=False))
        else:
            print("  (no previews in this run; skipping segmentation checks)")

    print("\n{}".format("FAILED: " + ", ".join(failures) if failures else "ALL CHECKS PASSED"))
    slicer.util.exit(1 if failures else 0)


try:
    main()
except Exception:
    traceback.print_exc()
    import slicer

    slicer.util.exit(2)
