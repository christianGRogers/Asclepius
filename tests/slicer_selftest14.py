"""SegQueue14 inside a real 3D Slicer: the D26 seed prefill and the overlap check.

    xvfb-run -a Slicer --no-splash --no-main-window --python-script tests/slicer_selftest14.py

What only Slicer can say: that one seed copied into all four class segments stays
four full, overlapping copies (one label volume imported into several target
segments fills only the first -- found in 5.8 while writing this), that trimming
one copy leaves the others whole, that a saved draft keeps them, that the classes
start hidden, that ``submit()`` refuses overlapping classes before any upload, and
that a trimmed case exports one class per voxel, and that the reviewer's
ImageCAS-X reference is shown in the four classes (#68).

With ``SEGQUEUE_SELFTEST_INSTALLED=<folder>`` it tests the module Slicer loaded
from that installed folder instead of the checkout.

The report goes to ``$SEGQUEUE_SELFTEST_OUT`` (default ``./selftest14.txt``); its
last line is ``RESULT PASS`` or ``RESULT FAIL``.
"""

import os
import sys
import tempfile
import time
import traceback

OUT = os.environ.get("SEGQUEUE_SELFTEST_OUT", os.path.abspath("selftest14.txt"))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_NAME = "~ vessel seed (not submitted)"
#: One tube per class, along k, at these (j, i) bands; together they are the seed.
TUBES = {"LM": (10, 13), "LAD": (20, 23), "LCx": (30, 33), "RCA": (40, 43)}
SHAPE = (40, 50, 60)
TUBE_VOXELS = 30 * 3 * 3

log = []
checks = []


def say(*parts):
    log.append(" ".join(str(p) for p in parts))


def check(name, passed, detail=""):
    checks.append(bool(passed))
    say("PASS" if passed else "FAIL", name, detail)


class _Assignment:
    def __init__(self, **fields):
        self.__dict__.update(fields)


class _NoUploadClient:
    def uploadFile(self, *args, **kwargs):
        raise AssertionError("uploaded although classes overlap")

    def submit(self, *args, **kwargs):
        raise AssertionError("submitted although classes overlap")


def _counts(slicer, labels, segmentationNode, volume, segmentId):
    return {spec.name: int((slicer.util.arrayFromSegmentBinaryLabelmap(
        segmentationNode, segmentId(spec.name), volume) > 0).sum())
        for spec in labels.segment_specs()}


def run():
    import numpy as np

    import slicer

    installed = os.environ.get("SEGQUEUE_SELFTEST_INSTALLED")
    if installed:
        # The module as an annotator has it: the copy Slicer loaded at startup
        # from an install (#97), not the checkout.
        import SegQueue14 as module

        where = os.path.dirname(os.path.abspath(module.__file__))
        check("testing the installed module", os.path.normcase(where)
              == os.path.normcase(os.path.abspath(installed)), where)
    else:
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
        import SegQueue14 as module

    from segqueue.protocol import ProjectConfig
    from segqueue14 import labels

    tmp = tempfile.mkdtemp()
    logic = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache"))
    logic.project = ProjectConfig(name="selftest", instructions=labels.INSTRUCTIONS,
                                  segments=labels.segment_specs())

    seed = np.zeros(SHAPE, np.uint8)
    for lo, hi in TUBES.values():
        seed[5:35, lo:hi, lo:hi] = 1
    ct = np.where(seed > 0, 400, -100).astype(np.int16)
    volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "ct")
    slicer.util.updateVolumeFromArray(volume, ct)
    volume.SetSpacing(0.5, 0.5, 0.6)
    volume.SetOrigin(10, -20, 30)
    logic.volumeNode = volume
    logic._loadOrCreateSegmentation({})

    # The seed file as _loadHelpers would have cached and imported it.
    seedNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "seed")
    slicer.util.updateVolumeFromArray(seedNode, seed)
    seedNode.CopyOrientation(volume)
    os.makedirs(logic.cache.caseDir("a1"), exist_ok=True)
    seedPath = os.path.join(logic.cache.caseDir("a1"), "seed.nii.gz")
    slicer.util.saveNode(seedNode, seedPath)
    slicer.mrmlScene.RemoveNode(seedNode)
    logic.seedSegmentId = logic._importHelper(seedPath, SEED_NAME, (0.95, 0.85, 0.2), 0.25)

    assignment = _Assignment(assignment_id="a1", case_name="selftest", attempt=1,
                             has_seed=True, has_prelabel=False)
    filled = logic._prefillClassesFromSeed(assignment)
    nSeed = int(seed.sum())
    copies = _counts(slicer, labels, logic.segmentationNode, volume, logic.segmentIdFor)
    check("every class starts as the whole seed", filled == 4 and all(
        n == nSeed for n in copies.values()), copies)

    draft = os.path.join(tmp, "draft.seg.nrrd")
    slicer.util.saveNode(logic.segmentationNode, draft)
    reopened = slicer.util.loadSegmentation(draft)
    again = _counts(slicer, labels, reopened, volume,
                    lambda name: module._segmentIdIn(reopened, name))
    slicer.mrmlScene.RemoveNode(reopened)
    check("a saved draft keeps the four copies", again == copies, again)

    logic.setClassesVisible(False)
    display = logic.segmentationNode.GetDisplayNode()
    hidden = [not display.GetSegmentVisibility(logic.segmentIdFor(s.name))
              for s in labels.segment_specs()]
    check("the classes start hidden", all(hidden), hidden)
    check("the seed helper stays visible",
          display.GetSegmentVisibility(logic.seedSegmentId))

    overlaps = logic.classOverlaps()
    check("untrimmed copies overlap pairwise", len(overlaps) == 6 and all(
        n == nSeed for _, _, n in overlaps), overlaps)

    logic.client = _NoUploadClient()
    logic.assignment = assignment
    logic._sessionStart = time.time()
    try:
        logic.submit()
        refusal = ""
    except module.SegQueueError as exc:
        refusal = str(exc)
    check("submit refuses overlapping classes before any upload", "share" in refusal,
          refusal[:80])

    for name, (lo, hi) in TUBES.items():
        segmentId = logic.segmentIdFor(name)
        array = slicer.util.arrayFromSegmentBinaryLabelmap(
            logic.segmentationNode, segmentId, volume).copy()
        keep = np.zeros_like(array)
        keep[5:35, lo:hi, lo:hi] = 1
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            array * keep, logic.segmentationNode, segmentId, volume)
    check("trimmed classes do not overlap", logic.classOverlaps() == [])

    segmentId = logic.segmentIdFor("LAD")
    lad = slicer.util.arrayFromSegmentBinaryLabelmap(
        logic.segmentationNode, segmentId, volume).copy()
    lad[5:35, 30:33, 30:33] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(lad, logic.segmentationNode, segmentId, volume)
    partial = logic.classOverlaps()
    check("a class left over another is named", partial == [("LAD", "LCx", TUBE_VOXELS)], partial)
    lad[5:35, 30:33, 30:33] = 0
    slicer.util.updateSegmentBinaryLabelmapFromArray(lad, logic.segmentationNode, segmentId, volume)

    counts, _source, _segmentation = logic.exportLabelmap(os.path.join(tmp, "out.seg.nrrd"))
    check("the export has one class per voxel",
          counts == {name: TUBE_VOXELS for name in TUBES}, counts)

    # #68: the reviewer's ImageCAS-X reference is in ImageCAS-X's 14 values. The
    # LAD tube is drawn as D1 (4), the RCA as 9, and an "Other" (14) stub sits at
    # the end of the LAD; collapsed, they show as LAD, RCA and LAD (D25).
    icx = np.zeros(SHAPE, np.uint8)
    for name, value in (("LM", 1), ("LAD", 4), ("LCx", 3), ("RCA", 9)):
        lo, hi = TUBES[name]
        icx[5:35, lo:hi, lo:hi] = value
    lo, hi = TUBES["LAD"]
    icx[35:37, lo:hi, lo:hi] = labels.ICX_OTHER
    refNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "reference")
    slicer.util.updateVolumeFromArray(refNode, icx)
    refNode.CopyOrientation(volume)
    refPath = os.path.join(tmp, "case_reference.nii.gz")
    slicer.util.saveNode(refNode, refPath)
    slicer.mrmlScene.RemoveNode(refNode)
    shown = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "reference")
    shown.CreateDefaultDisplayNodes()
    shown.SetReferenceImageGeometryParameterFromVolumeNode(volume)
    logic.importLabelsIntoProject(refPath, segmentationNode=shown, icx14=True)
    ref = _counts(slicer, labels, shown, volume, lambda name: module._segmentIdIn(shown, name))
    stub = 2 * (hi - lo) * (hi - lo)
    check("the ImageCAS-X reference shows in the four classes (D1 as LAD, RCA as RCA)",
          ref == {"LM": TUBE_VOXELS, "LAD": TUBE_VOXELS + stub, "LCx": TUBE_VOXELS,
                  "RCA": TUBE_VOXELS}, ref)

    # The same import by value (a prelabel, in the four): every class, not only the
    # first -- into a fresh node, and again into the classes it now has (a case's
    # project segments exist before its prelabel is imported).
    four = np.zeros(SHAPE, np.uint8)
    for name, (lo, hi) in TUBES.items():
        four[5:35, lo:hi, lo:hi] = labels.LABEL_VALUES[name]
    fourNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "four")
    slicer.util.updateVolumeFromArray(fourNode, four)
    fourNode.CopyOrientation(volume)
    fourPath = os.path.join(tmp, "prelabel.nii.gz")
    slicer.util.saveNode(fourNode, fourPath)
    slicer.mrmlScene.RemoveNode(fourNode)
    fresh = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "prelabel")
    fresh.CreateDefaultDisplayNodes()
    fresh.SetReferenceImageGeometryParameterFromVolumeNode(volume)
    filled = logic.importLabelsIntoProject(fourPath, segmentationNode=fresh)
    got = _counts(slicer, labels, fresh, volume, lambda name: module._segmentIdIn(fresh, name))
    check("a four-class volume imports into every class", filled == 4 and got == {
        name: TUBE_VOXELS for name in TUBES}, got)
    for spec in labels.segment_specs():
        segment = fresh.GetSegmentation().GetSegment(module._segmentIdIn(fresh, spec.name))
        segment.SetLabelValue(int(spec.label))  # as _applyTemplate leaves them
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            np.zeros(SHAPE, np.uint8), fresh, module._segmentIdIn(fresh, spec.name), volume)
    filled = logic.importLabelsIntoProject(fourPath, segmentationNode=fresh)
    got = _counts(slicer, labels, fresh, volume, lambda name: module._segmentIdIn(fresh, name))
    check("and into existing classes", filled == 4 and got == {
        name: TUBE_VOXELS for name in TUBES}, got)

    # Without SetLabelValue in the import, a submission still carries the project's
    # values: exportLabelmap numbers the classes by project order (1 LM ... 4 RCA).
    logic.segmentationNode = fresh
    counts, _source, _segmentation = logic.exportLabelmap(os.path.join(tmp, "pre.seg.nrrd"))
    exported = slicer.util.loadLabelVolume(os.path.join(tmp, "pre.seg.nrrd"))
    array = slicer.util.arrayFromVolume(exported)
    slicer.mrmlScene.RemoveNode(exported)
    byValue = {}
    for name, (lo, hi) in TUBES.items():
        found = np.unique(array[5:35, lo:hi, lo:hi])
        byValue[name] = [int(v) for v in found]
    check("an imported prelabel exports under the project's label values",
          counts == {name: TUBE_VOXELS for name in TUBES}
          and byValue == {name: [labels.LABEL_VALUES[name]] for name in TUBES},
          (counts, byValue))


try:
    run()
except Exception:
    say("EXCEPTION", traceback.format_exc())
    checks.append(False)

passed = bool(checks) and all(checks)
say("RESULT", "PASS" if passed else "FAIL")
with open(OUT, "w") as handle:
    handle.write("\n".join(log) + "\n")

import slicer  # noqa: E402  (only importable inside Slicer)

slicer.app.exit(0 if passed else 1)
