"""Turning the extended classes on, timed on a realistic seeded case (D52).

    BENCH_MODULE=<folder holding SegQueue14.py> BENCH_SURFACES=0|1 \\
    BENCH_OUT=bench.json xvfb-run -a Slicer --no-splash --no-main-window \\
        --python-script tests/slicer_bench_extended14.py

Not a test: it measures, it does not pass or fail, and pytest does not collect it.
One Slicer process per run, so the peak memory it reports is that run's.

The case: a 512 x 512 x 300 CT (0.4 x 0.4 x 0.6 mm) and a vessel seed of a few
hundred thousand voxels -- four vessels and 14 branches drawn as tubes. It opens as
an own seeded case does (the four filled from the seed, D26), with or without the
classes shown in 3D (``BENCH_SURFACES``). Then:

* **toggle on** -- what the panel's "Extended classes" toggle calls. 0.25.3 adds the
  17 and fills each from the seed (``addExtendedClasses(fromSeed=True)``); 0.25.4
  adds them empty (D52).
* **first selection of a branch** -- 0.25.4: ``seedOnFirstSelection`` (the copy of
  the seed made then) and showing it, as the panel does on a selection. 0.25.3 only
  showed it: its copy was made at toggle-on.
* the segmentation's labelmap layers and their voxels, after each step, and the
  process's resident and peak memory (``/proc/self/status``).

``BENCH_MODULE`` picks the module version: the checkout's ``slicer/SegQueue14`` by
default, or an older one, e.g. from ``git archive <rev> slicer/SegQueue14 src``.
"""

import json
import os
import sys
import time
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_DIR = os.environ.get("BENCH_MODULE") or os.path.join(REPO, "slicer", "SegQueue14")
SRC = os.environ.get("BENCH_SRC") or os.path.join(REPO, "src")
SURFACES = os.environ.get("BENCH_SURFACES", "0") == "1"
OUT = os.environ.get("BENCH_OUT", os.path.abspath("bench_extended14.json"))

SHAPE = (300, 512, 512)                # k, j, i
SPACING = (0.4, 0.4, 0.6)              # i, j, k in mm
RADIUS = 6                             # voxels: 2.4 mm in-plane


def memory():
    """``{"rss_mb", "peak_mb"}`` of this process, from /proc (Linux)."""
    found = {}
    try:
        with open("/proc/self/status") as handle:
            for line in handle:
                if line.startswith(("VmRSS:", "VmHWM:")):
                    key = "rss_mb" if line.startswith("VmRSS") else "peak_mb"
                    found[key] = round(int(line.split()[1]) / 1024.0, 1)
    except OSError:
        pass
    return found


def tube(np, seed, start, end):
    """A solid tube from ``start`` to ``end`` (k, j, i), ``RADIUS`` across."""
    start, end = np.array(start, float), np.array(end, float)
    steps = int(np.linalg.norm(end - start)) + 1
    r = RADIUS
    for t in np.linspace(0.0, 1.0, steps):
        k, j, i = (start + t * (end - start)).round().astype(int)
        k0, k1 = max(k - r, 0), min(k + r + 1, SHAPE[0])
        j0, j1 = max(j - r, 0), min(j + r + 1, SHAPE[1])
        i0, i1 = max(i - r, 0), min(i + r + 1, SHAPE[2])
        kk, jj, ii = np.ogrid[k0:k1, j0:j1, i0:i1]
        ball = (kk - k) ** 2 + (jj - j) ** 2 + (ii - i) ** 2 <= r * r
        seed[k0:k1, j0:j1, i0:i1] |= ball.astype(np.uint8)


def make_seed(np):
    """Four vessels from near the aortic root, and 14 branches off them."""
    seed = np.zeros(SHAPE, np.uint8)
    rng = np.random.RandomState(52)
    root = np.array([200, 256, 256])
    ends = {"LM": [190, 236, 300], "LAD": [60, 170, 360], "LCx": [90, 330, 360],
            "RCA": [40, 300, 150]}
    lm_end = np.array(ends["LM"])
    tube(np, seed, root, lm_end)
    for name in ("LAD", "LCx"):
        tube(np, seed, lm_end, ends[name])
    tube(np, seed, root, ends["RCA"])
    parents = ["LAD"] * 6 + ["LCx"] * 3 + ["RCA"] * 5
    for parent in parents:
        a = lm_end if parent != "RCA" else root
        b = np.array(ends[parent])
        start = a + rng.uniform(0.25, 0.85) * (b - a)
        end = start + rng.uniform(-90, 90, 3) * np.array([0.6, 1.0, 1.0])
        end = np.clip(end, [5, 5, 5], np.array(SHAPE) - 6)
        tube(np, seed, start, end)
    return seed


def layers(segmentation_node):
    """``(layer count, voxels held across the layers)`` of the segmentation: the
    labelmap layers' image extents, which is what their memory and the 2D views'
    per-layer reslicing scale with."""
    segmentation = segmentation_node.GetSegmentation()
    count = segmentation.GetNumberOfLayers()
    voxels = 0
    for index in range(count):
        image = segmentation.GetLayerDataObject(index)
        if image is not None and hasattr(image, "GetNumberOfPoints"):
            voxels += int(image.GetNumberOfPoints())
    return count, voxels


def main():
    import numpy as np

    import slicer

    sys.path.insert(0, SRC)
    sys.path.insert(0, MODULE_DIR)
    import SegQueue14 as module

    from segqueue.protocol import ProjectConfig
    from segqueue14 import labels

    result = {"slicer": slicer.app.applicationVersion, "module": module.__version__,
              "surfaces": SURFACES, "shape": SHAPE}
    seed = make_seed(np)
    result["seed_voxels"] = int(seed.sum())

    volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "bench-ct")
    slicer.util.updateVolumeFromArray(volume, np.where(seed > 0, 400, -100).astype(np.int16))
    volume.SetSpacing(*SPACING)
    cache = os.path.join(os.path.dirname(OUT), "bench-cache")
    logic = module.SegQueue14Logic(cacheRoot=cache)
    logic.project = ProjectConfig(name="bench", instructions=labels.INSTRUCTIONS,
                                  segments=labels.segment_specs())
    logic.extendedClasses = False
    logic.volumeNode = volume

    class Assignment:
        assignment_id = case_name = "bench"
        attempt = 1
        has_seed, has_prelabel = True, False

    logic.assignment = Assignment()
    logic._loadOrCreateSegmentation({})
    os.makedirs(logic.cache.caseDir("bench"), exist_ok=True)
    seedNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "bench-seed")
    slicer.util.updateVolumeFromArray(seedNode, seed)
    seedNode.CopyOrientation(volume)
    seedPath = os.path.join(logic.cache.caseDir("bench"), "seed.nii.gz")
    slicer.util.saveNode(seedNode, seedPath)
    slicer.mrmlScene.RemoveNode(seedNode)
    logic.seedSegmentId = logic._importHelper(seedPath, "~ vessel seed (not submitted)",
                                              (0.95, 0.85, 0.2), 0.25)
    logic._prefillClassesFromSeed(logic.assignment)
    logic.setClassesVisible(False)
    if SURFACES:
        logic.showPrelabelIn3d()
    node = logic.segmentationNode
    result["opened"] = dict(zip(("layers", "layer_voxels"), layers(node)), **memory())

    # Toggle on, as the panel's toggle does it in each version.
    newApi = hasattr(logic, "seedOnFirstSelection")
    logic.extendedClasses = True
    started = time.perf_counter()
    if newApi:
        logic.addExtendedClasses()
    else:
        logic.addExtendedClasses(fromSeed=True)
    slicer.app.processEvents()
    toggle = time.perf_counter() - started
    seeded = sum(1 for n in labels.EXTRA_NAMES if module._segmentHasContent(node, n))
    result["toggle_on"] = dict(zip(("layers", "layer_voxels"), layers(node)),
                               seconds=round(toggle, 3), classes_with_seed_voxels=seeded,
                               surfaces_after=bool(node.GetSegmentation()
                                                   .ContainsRepresentation("Closed surface")),
                               **memory())

    # The first selection of a branch: its seed copy (0.25.4), then shown.
    segmentId = logic.segmentIdFor("D1")
    started = time.perf_counter()
    filled = logic.seedOnFirstSelection(segmentId) if newApi else False
    node.GetDisplayNode().SetSegmentVisibility(segmentId, True)
    slicer.app.processEvents()
    first = time.perf_counter() - started
    seeded = sum(1 for n in labels.EXTRA_NAMES if module._segmentHasContent(node, n))
    result["first_selection"] = dict(
        zip(("layers", "layer_voxels"), layers(node)), seconds=round(first, 3),
        filled=bool(filled), classes_with_seed_voxels=seeded,
        d1_voxels=int(np.count_nonzero(slicer.util.arrayFromSegmentBinaryLabelmap(
            node, segmentId, volume))),
        **memory())
    return result


try:
    report = main()
except Exception:
    report = {"error": traceback.format_exc()}
with open(OUT, "w") as handle:
    json.dump(report, handle, indent=1)

import slicer  # noqa: E402  (only importable inside Slicer)

slicer.app.exit(0 if "error" not in report else 1)
