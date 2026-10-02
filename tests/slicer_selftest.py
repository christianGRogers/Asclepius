"""Self-test for the SegQueue module, run inside Slicer's own Python.

    "C:\\...\\Slicer.exe" --no-splash --no-main-window \\
        --python-script tests\\slicer_selftest.py --exit-after-startup

Exits non-zero on failure. Set ``SEGQUEUE_SELFTEST_OUT`` to also write the report
to a file: Slicer's stdout is noisy, and Slicer does not forward unknown
command-line flags through to the script, so an environment variable is the only
thing that reliably arrives.

**Why this exists.** ``SegQueue.py`` imports Qt, VTK and Slicer, so the pytest
suite cannot touch it, and what the module asks of Slicer is mostly of a kind
that fails *silently*:

* **One mask written into four segments.** Every branch starts as a copy of the
  coronary mask, which means four segments covering the same voxels. A
  segmentation stores that by splitting them across labelmap *layers*, and a
  write that landed in the shared layer instead would erase the segments beside
  it -- leaving three empty branches and no error anywhere.
* **The export flattens those layers into one label per voxel.** So the overlap
  the new start creates has to be measured before the export, and the two numbers
  have to be counted on the same grid, or the check either misses a mislabelled
  artery or invents one.
* **The 3D camera keeps the last case's framing.** Nothing raises; the surface is
  simply off screen. The calls that reframe it are guarded against
  ``AttributeError``, which makes a rename in Slicer silent too.

So the checks here are the ones whose failure mode is silence. Anything that
raises an exception on its own is already covered by the annotator noticing.
"""

import os
import sys
import tempfile
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_DIR = os.path.join(REPO, "slicer", "SegQueue")


def _load_working_copy():
    """Import this repository's SegQueue.py under its own name, by path."""
    import importlib.util

    path = os.path.join(MODULE_DIR, "SegQueue.py")
    spec = importlib.util.spec_from_file_location("SegQueueWorkingCopy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Report(object):
    def __init__(self):
        self.lines = []
        self.failures = []

    def check(self, name, condition, detail=""):
        status = "PASS" if condition else "FAIL"
        self.say("  [{}] {}{}".format(status, name, (" -- " + detail) if detail else ""))
        if not condition:
            self.failures.append(name)

    def say(self, text=""):
        print(text)
        self.lines.append(text)


def main():
    report = Report()
    report.say("SegQueue self-test")
    report.say("  module dir: " + MODULE_DIR)

    if MODULE_DIR not in sys.path:
        sys.path.insert(0, MODULE_DIR)

    import vtk

    import slicer

    # ---------------------------------------------------------------- import
    #
    # By path, and never by ``import SegQueue``. When the extension is also
    # *installed* -- which it is on any machine where somebody has tried a
    # release -- Slicer has already imported that copy by the time this script
    # runs, so a plain import quietly hands back the installed module and the
    # whole self-test reports on a file nobody is editing. That happened on this
    # script's first run, against an installed build carrying the very bug the
    # working copy had just fixed.
    report.say("\n1. import")
    try:
        mod = _load_working_copy()
        report.check("module imports", True)
    except Exception:
        report.say(traceback.format_exc())
        report.check("module imports", False)
        return _finish(report)

    report.say("     loaded: " + getattr(mod, "__file__", "?"))
    report.check("it is the working copy, not an installed build",
                 os.path.abspath(getattr(mod, "__file__", "")).startswith(
                     os.path.abspath(REPO)),
                 getattr(mod, "__file__", "?"))

    report.check("segqueue package found", mod._IMPORT_ERROR is None,
                 mod._IMPORT_ERROR or "")
    report.check("version is set", bool(getattr(mod, "__version__", "")),
                 getattr(mod, "__version__", ""))

    # ------------------------------------------------------ a scene to work in
    volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "v")
    image = vtk.vtkImageData()
    image.SetDimensions(20, 20, 20)
    image.AllocateScalars(vtk.VTK_SHORT, 1)
    image.GetPointData().GetScalars().Fill(0)
    volume.SetAndObserveImageData(image)

    segmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "s")
    segmentation.CreateDefaultDisplayNodes()
    segmentation.SetReferenceImageGeometryParameterFromVolumeNode(volume)

    editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    editor = slicer.qMRMLSegmentEditorWidget()
    editor.setMRMLScene(slicer.mrmlScene)
    editor.setMRMLSegmentEditorNode(editorNode)
    editor.setSegmentationNode(segmentation)
    editor.setSourceVolumeNode(volume)

    # ------------------------------------------------------------- the tools
    #
    # Trimming is done with Scissors from the Segment Editor itself now, so what
    # matters is that the effect the workflow depends on is in the build at all.
    # The panel no longer configures it -- the annotator picks it up in the editor,
    # which is also where its own defaults come from.
    report.say('\n2. the effects the workflow needs')
    available = list(editor.availableEffectNames())
    report.check("Scissors present", "Scissors" in available,
                 "" if "Scissors" in available else "core Slicer effect is missing")
    report.check("Logical operators present", "Logical operators" in available)

    # -------------------------------------------- the calls that centre 3D
    #
    # ``centre3d`` swallows AttributeError, because a Slicer that spells these
    # differently must not cost an annotator a case over a camera. That makes a
    # rename silent in exactly the way this file exists to catch: the 3D view
    # stays pointed wherever the previous case left it, the mask renders off
    # screen, and the module looks like it never built one. Checked on a view
    # constructed here rather than on the layout manager's, because this runs
    # under --no-main-window and there is no layout to ask.
    report.say('\n3. the 3D view exposes the calls that frame it')
    try:
        view = slicer.qMRMLThreeDView()
    except Exception:
        report.say(traceback.format_exc())
        report.check("a 3D view can be constructed", False)
    else:
        for call in ("forceRender", "resetFocalPoint", "resetCamera"):
            report.check("qMRMLThreeDView.{}() exists".format(call),
                         callable(getattr(view, call, None)))

    # ------------------------------------------- starting the branches from the mask
    report.say('\n4. starting the branches from the mask, and the overlap it makes possible')
    try:
        _branch_flow(report, mod, slicer, volume)
    except Exception:
        report.say(traceback.format_exc())
        report.check("the branch flow runs", False)

    # ------------------------------------------- what a reviewer opens into
    report.say('\n5. what a reviewer opens into')
    try:
        _review_view(report, mod, slicer, volume)
    except Exception:
        report.say(traceback.format_exc())
        report.check("the review view runs", False)

    return _finish(report)


def _review_view(report, mod, slicer, volume):
    """A submission has to arrive visible, in 3D, and in frame.

    The reviewer's complaint was that it did not: the segments were loaded and
    the 3D view was empty. Two separate causes, both only visible in Slicer --
    a loaded segmentation can carry its segments hidden, and ``centre3d`` fits
    the camera to the actors in the renderer, so centring before the surface
    exists frames nothing at all.
    """
    import math

    segmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "sub")
    segmentation.CreateDefaultDisplayNodes()
    segmentation.SetReferenceImageGeometryParameterFromVolumeNode(volume)

    logic = mod.SegQueueLogic(cacheRoot=tempfile.mkdtemp(prefix="segqueue-review-"))
    logic.volumeNode = volume
    logic.segmentationNode = segmentation

    ids = []
    for name, zrange in (("lad", (2, 8)), ("lcx", (8, 13)), ("rca", (13, 18))):
        segmentId = segmentation.GetSegmentation().AddEmptySegment(name, name, [1, 0, 0])
        _paint(slicer, segmentation, volume, segmentId, zrange=zrange)
        ids.append(segmentId)

    display = segmentation.GetDisplayNode()
    for segmentId in ids:
        display.SetSegmentVisibility(segmentId, False)
    report.check("a submission can arrive with every segment hidden",
                 not any(display.GetSegmentVisibility(s) for s in ids))

    shown = logic.showSubmissionIn3d()
    report.check("opening it shows every segment", shown == len(ids),
                 "{} of {}".format(shown, len(ids)))
    report.check("and they are visible in the segment list",
                 all(display.GetSegmentVisibility(s) for s in ids))

    name = slicer.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
    report.check("the 3D surface is built, not waited for",
                 segmentation.GetSegmentation().ContainsRepresentation(name))

    camera = slicer.util.getNode("vtkMRMLCameraNode*")
    if camera is None:
        report.say("  [SKIP] no camera in this session (--no-main-window)")
        return
    centre = segmentation.GetSegmentCenterRAS(ids[1])
    camera.SetFocalPoint(-900.0, 900.0, -900.0)
    camera.SetPosition(-900.0, 900.0, -400.0)
    before = math.dist(camera.GetFocalPoint(), centre)
    logic.centre3d()
    after = math.dist(camera.GetFocalPoint(), centre)
    report.check("and the 3D view is framed on it",
                 after < 25.0 < before,
                 "{:.0f} mm -> {:.0f} mm".format(before, after))


def _branch_flow(report, mod, slicer, volume):
    """Open a seeded case, check what the annotator lands in, then trim it.

    Driven through the logic's own methods on a hand-built scene, because
    ``openCase`` wants a server and a 400 MB download and none of what is being
    checked here is about either. What *is* being checked can only be checked in
    Slicer: whether writing one mask into four segments leaves four segments each
    holding that mask, which is a question about how a segmentation stores
    overlapping labelmaps in layers, and whether the export then flattens them in
    the way the overlap check assumes.
    """
    from segqueue import protocol

    segmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "branch")
    segmentation.CreateDefaultDisplayNodes()
    segmentation.SetReferenceImageGeometryParameterFromVolumeNode(volume)

    logic = mod.SegQueueLogic(cacheRoot=tempfile.mkdtemp(prefix="segqueue-selftest-"))
    logic.volumeNode = volume
    logic.segmentationNode = segmentation
    logic.resumedDraft = False
    logic.project = protocol.ProjectConfig(segments=[
        protocol.SegmentSpec(name="lad", label=1, color=(1.0, 0.0, 0.0)),
        protocol.SegmentSpec(name="lcx", label=2, color=(0.0, 1.0, 0.0)),
        protocol.SegmentSpec(name="rca", label=3, color=(0.0, 0.0, 1.0)),
    ])
    names = [spec.name for spec in logic.project.segments]

    # The project's segments first, then the helper -- the order
    # ``_loadOrCreateSegmentation`` uses, and not an arbitrary one. ``_applyTemplate``
    # pins each segment's label value to the protocol's, and segments in one
    # segmentation can share a labelmap layer, so a helper painted *before* the
    # template holds label 1 and the first branch's ``SetLabelValue(1)`` then aims
    # at the same voxels: the branch reads back as the whole mask before anything
    # has copied it there. Written down because this test made exactly that
    # mistake and reported failures the module was not responsible for.
    logic._applyTemplate()
    ids = {name: logic.segmentIdFor(name) for name in names}
    report.check("the template created the project's segments",
                 all(ids.values()), repr(ids))

    seg = segmentation.GetSegmentation()
    seedId = seg.AddEmptySegment(protocol.SEED_SEGMENT_NAME,
                                 protocol.SEED_SEGMENT_NAME, [0.95, 0.95, 0.35])
    logic.seedSegmentId = seedId
    _paint(slicer, segmentation, volume, seedId, zrange=(2, 18))
    maskCount = _count(slicer, segmentation, seedId, volume)
    report.check("the mask is non-empty and the branches are not it",
                 maskCount > 0
                 and all(_count(slicer, segmentation, ids[n], volume) == 0
                         for n in names),
                 "mask {}".format(maskCount))

    # -- what the annotator lands in
    started = logic._startBranchesFromSeed()
    report.check("every branch was started", started == len(names),
                 "{} of {}".format(started, len(names)))

    drawn = logic.drawnCounts()
    report.check("every branch now holds the whole mask",
                 all(drawn.get(n) == maskCount for n in names),
                 " ".join("{} {}".format(n, drawn.get(n)) for n in names))
    report.check("and the mask itself is untouched",
                 _count(slicer, segmentation, seedId, volume) == maskCount)

    display = segmentation.GetDisplayNode()
    report.check("every branch is hidden",
                 all(not display.GetSegmentVisibility(ids[n]) for n in names))
    report.check("and the mask is not",
                 bool(display.GetSegmentVisibility(seedId)))

    # -- the overlap the new start makes possible, measured the way submit does
    exported, drawnBefore = _export_counts(report, mod, slicer, logic, names)
    lost = {n: drawnBefore.get(n, 0) - exported.get(n, 0) for n in names}
    report.check("three identical branches lose voxels on export",
                 any(v > 0 for v in lost.values()),
                 " ".join("{} -{}".format(n, lost[n]) for n in names))
    report.check("and one of them survives whole, because a voxel gets one label",
                 sum(exported.values()) == maskCount,
                 "{} vs {}".format(sum(exported.values()), maskCount))

    # -- trimmed apart, the two measures agree again
    _paint(slicer, segmentation, volume, ids["lad"], zrange=(2, 8))
    _paint(slicer, segmentation, volume, ids["lcx"], zrange=(8, 13))
    _paint(slicer, segmentation, volume, ids["rca"], zrange=(13, 18))

    exported, drawnAfter = _export_counts(report, mod, slicer, logic, names)
    report.check("trimmed apart, nothing is lost on export",
                 all(drawnAfter.get(n) == exported.get(n) for n in names),
                 " ".join("{} {}/{}".format(n, drawnAfter.get(n), exported.get(n))
                          for n in names))
    report.check("and the three branches add back up to the mask",
                 sum(exported.values()) == maskCount,
                 "{} vs {}".format(sum(exported.values()), maskCount))
    report.check("no two branches share a voxel",
                 _overlap(slicer, segmentation, ids["lad"], ids["lcx"], volume) == 0
                 and _overlap(slicer, segmentation, ids["lcx"], ids["rca"], volume) == 0
                 and _overlap(slicer, segmentation, ids["lad"], ids["rca"], volume) == 0)

    # -- a reopened draft keeps the annotator's trimming
    logic.resumedDraft = True
    report.check("a resumed draft is not restarted from the mask",
                 logic._startBranchesFromSeed() == 0)
    report.check("and still holds what was trimmed",
                 logic.drawnCounts() == drawnAfter)


def _export_counts(report, mod, slicer, logic, names):
    """``(exported, drawn)`` counts, measured the way pressing Check measures them."""
    directory = tempfile.mkdtemp(prefix="segqueue-export-")
    path = os.path.join(directory, "check.seg.nrrd")
    drawn = logic.drawnCounts()
    counts, _source, _seg = logic.exportLabelmap(path)
    try:
        os.unlink(path)
    except OSError:
        pass
    return counts, drawn


def _paint(slicer, segmentationNode, volumeNode, segmentId, zrange):
    """Fill a slab of the segment, by writing its labelmap directly."""
    array = slicer.util.arrayFromSegmentBinaryLabelmap(
        segmentationNode, segmentId, volumeNode)
    array[:] = 0
    array[zrange[0]:zrange[1], 5:15, 5:15] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(
        array, segmentationNode, segmentId, volumeNode)


def _count(slicer, segmentationNode, segmentId, volumeNode):
    array = slicer.util.arrayFromSegmentBinaryLabelmap(
        segmentationNode, segmentId, volumeNode)
    return int((array > 0).sum()) if array is not None else 0


def _overlap(slicer, segmentationNode, a, b, volumeNode):
    first = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, a, volumeNode)
    second = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, b, volumeNode)
    return int(((first > 0) & (second > 0)).sum())


def _finish(report):
    out = os.environ.get("SEGQUEUE_SELFTEST_OUT")
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            handle.write("\n".join(report.lines))
    if report.failures:
        report.say("\nFAILED: " + ", ".join(report.failures))
        return 1
    report.say("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        print(traceback.format_exc())
    # Slicer swallows a bare sys.exit from a --python-script, so the status has
    # to go through the application object for a CI step to see it.
    try:
        import slicer
        slicer.util.exit(code)
    except Exception:
        sys.exit(code)
