"""Self-test for the SegQueue module, run inside Slicer's own Python.

    "C:\\...\\Slicer.exe" --no-splash --no-main-window \\
        --python-script tests\\slicer_selftest.py --exit-after-startup

Exits non-zero on failure. Set ``SEGQUEUE_SELFTEST_OUT`` to also write the report
to a file: Slicer's stdout is noisy, and Slicer does not forward unknown
command-line flags through to the script, so an environment variable is the only
thing that reliably arrives.

**Why this exists.** ``SegQueue.py`` imports Qt, VTK and Slicer, so the pytest
suite cannot touch it, and the module's two hardest dependencies on Slicer are
both of a kind that fails *silently*:

* **Effect parameters are strings converted to enums by name.** Nothing
  validates them. ``Scissors`` shipped in 0.7.0 with ``Shape="FREE_FORM"``
  instead of ``"FreeForm"``; the effect mapped that to -1, built no drawing
  pipeline, and the trim tool activated but would not draw. No error anywhere.
* **Segment arithmetic goes through the Logical operators effect.** A wrong
  operation name or a stale modifier id does not raise -- it quietly produces
  the wrong voxels, which is a mislabelled artery nobody notices until the
  submission is scored.

So the checks here are the ones whose failure mode is silence. Anything that
raises an exception on its own is already covered by the annotator noticing.
"""

import os
import sys
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

    import slicer
    import vtk

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
    report.say("\n2. effects the module drives")
    available = list(editor.availableEffectNames())
    report.check("Scissors present", mod.SCISSORS_EFFECT in available)
    report.check("Logical operators present", "Logical operators" in available)
    report.check("{} present".format(mod.TUBE_EFFECT), mod.TUBE_EFFECT in available,
                 "" if mod.TUBE_EFFECT in available
                 else "install " + mod.TUBE_EXTENSION)

    # --------------------------------------------------- the scissors spelling
    #
    # Against the defaults Slicer itself writes, not against a second copy of
    # the same guess: activating Scissors on a virgin editor node makes the
    # effect store its own defaults, which are erase-inside and free-form -- the
    # exact configuration the trim tool wants. If Slicer ever renames these, the
    # module's constants stop matching and this fails instead of the tool
    # quietly refusing to draw.
    report.say("\n3. the trim tool's parameters are spelled the way Slicer spells them")
    virgin = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    probe = slicer.qMRMLSegmentEditorWidget()
    probe.setMRMLScene(slicer.mrmlScene)
    probe.setMRMLSegmentEditorNode(virgin)
    probe.setSegmentationNode(segmentation)
    probe.setSourceVolumeNode(volume)
    probe.setActiveEffectByName(mod.SCISSORS_EFFECT)

    defaultOperation = virgin.GetAttribute("Scissors.Operation")
    defaultShape = virgin.GetAttribute("Scissors.Shape")
    report.check("Operation matches Slicer's default",
                 mod.SCISSORS_OPERATION == defaultOperation,
                 "module {!r} vs Slicer {!r}".format(
                     mod.SCISSORS_OPERATION, defaultOperation))
    report.check("Shape matches Slicer's default",
                 mod.SCISSORS_SHAPE == defaultShape,
                 "module {!r} vs Slicer {!r}".format(
                     mod.SCISSORS_SHAPE, defaultShape))

    # ------------------------------------------------- the fill arithmetic
    #
    # The whole trimming workflow rests on this: a vessel is the mask minus
    # every other vessel. Done here with the same effect and the same operation
    # names the panel uses, on segments whose voxels are known exactly.
    report.say("\n4. filling a vessel from the unclaimed remainder")
    seg = segmentation.GetSegmentation()
    maskId = seg.AddEmptySegment("mask", "mask", [1.0, 1.0, 0.0])
    takenId = seg.AddEmptySegment("taken", "taken", [1.0, 0.0, 0.0])
    targetId = seg.AddEmptySegment("target", "target", [0.0, 1.0, 0.0])

    _paint(slicer, segmentation, volume, maskId, zrange=(2, 18))
    _paint(slicer, segmentation, volume, takenId, zrange=(2, 10))

    maskCount = _count(slicer, segmentation, maskId, volume)
    takenCount = _count(slicer, segmentation, takenId, volume)
    report.check("test masks are non-empty and nested",
                 maskCount > takenCount > 0,
                 "mask {} taken {}".format(maskCount, takenCount))

    _logical(editor, editorNode, "COPY", maskId, targetId)
    afterCopy = _count(slicer, segmentation, targetId, volume)
    report.check("COPY puts the whole mask in the target",
                 afterCopy == maskCount, "{} vs {}".format(afterCopy, maskCount))

    _logical(editor, editorNode, "SUBTRACT", takenId, targetId)
    afterSubtract = _count(slicer, segmentation, targetId, volume)
    report.check("SUBTRACT leaves exactly the remainder",
                 afterSubtract == maskCount - takenCount,
                 "{} vs {}".format(afterSubtract, maskCount - takenCount))
    report.check("the remainder is disjoint from what was already taken",
                 _overlap(slicer, segmentation, targetId, takenId, volume) == 0)

    return _finish(report)


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


def _logical(editor, editorNode, operation, modifierId, targetId):
    """The panel's ``_logicalOp``, in the smallest form that still tests it."""
    editorNode.SetSelectedSegmentID(targetId)
    editor.setActiveEffectByName("Logical operators")
    effect = editor.activeEffect()
    effect.setParameter("Operation", operation)
    if modifierId:
        effect.setParameter("ModifierSegmentID", modifierId)
    effect.setParameter("BypassMasking", "1")
    effect.self().onApply()


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
