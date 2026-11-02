"""SegQueue14 inside a real 3D Slicer: the D26 seed prefill, drafts, and the export.

    xvfb-run -a Slicer --no-splash --no-main-window --python-script tests/slicer_selftest14.py

What only Slicer can say: that one seed copied into all four class segments stays
four full, overlapping copies (one label volume imported into several target
segments fills only the first -- found in 5.8 while writing this), that trimming
one copy leaves the others whole, that a saved draft keeps them, that the classes
start hidden, that a draft saved with the copies still overlapping reopens with
every class readable (the false "empty" of #270), that overlapping classes and
an empty scene are uploaded rather than refused (#270), that the reviewer's
ImageCAS-X reference is shown in the four classes (#68), and D39 (#275): that an
untouched seeded case -- four identical full copies -- is submitted as four whole
classes (not as all RCA), reopens for a reviewer with all four whole and named,
and round-trips through a reviewer's revision the same way; and that a partly
trimmed case keeps every class's own voxels.

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


class _RecordingClient:
    """Takes uploads and hand-overs without a server, and remembers them.

    Each upload is read back as the server's scoring worker reads it (no Slicer):
    ``self.files`` holds ``{class name: voxels}`` per uploaded file, from the file.
    """

    def __init__(self):
        self.calls = []
        self.files = []
        self.formats = []
        self.kept = []

    def uploadFile(self, path, *args, **kwargs):
        self.calls.append(("upload", os.path.isfile(path)))
        from segqueue14 import labelfile

        if os.path.isfile(path):
            data = labelfile.read_class_stack(path)
            self.files.append(labelfile.voxel_counts(data["masks"], data["names"]))
            import shutil

            # Outside the case folder, which submit purges.
            keep = os.path.join(tempfile.mkdtemp(), "uploaded.seg.nrrd")

            shutil.copy(path, keep)
            self.kept.append(keep)
        return {"_id": "file"}

    def submit(self, assignmentId, meta, fileId, geometry=None, labelFormat=None):
        self.calls.append(("submit", dict(meta.voxel_counts)))
        self.formats.append(labelFormat)
        return {"submissionId": "s1"}

    def reviseSubmission(self, submissionId, meta, fileId, labelFormat=None):
        self.calls.append(("revise", dict(meta.voxel_counts)))
        self.formats.append(labelFormat)
        return {"submissionId": "s2"}


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

    # #270: the same draft reopened the way a resumed case is (through
    # _applyTemplate). Re-pinning label values used to leave LAD, LCx and RCA
    # unreadable here, so they exported as empty.
    resumed = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache"))
    resumed.project = logic.project
    resumed.volumeNode = volume
    resumed._loadOrCreateSegmentation({"workPath": draft})
    reread = _counts(slicer, labels, resumed.segmentationNode, volume, resumed.segmentIdFor)
    check("a resumed draft keeps every class readable", reread == copies, reread)
    slicer.mrmlScene.RemoveNode(resumed.segmentationNode)

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

    logic.client = _RecordingClient()
    logic.assignment = assignment
    logic._sessionStart = time.time()
    logic.reviseSubmission("s0")
    check("overlapping classes are uploaded, not refused (#270)",
          [c[0] for c in logic.client.calls] == ["upload", "revise"]
          and logic.client.calls[0][1], logic.client.calls)

    # D39 (#275): the untouched seeded case, submitted. The uploaded file holds all
    # four classes whole -- not the one class a label volume kept (all RCA) -- and
    # the counts say so.
    whole = {name: nSeed for name in TUBES}
    untouched = os.path.join(tmp, "untouched.seg.nrrd")
    counts, _source, _segmentation = logic.exportSubmission(untouched)
    from segqueue14 import labelfile

    stored = labelfile.read_class_stack(untouched)
    check("an untouched seeded case is saved as four whole classes (#275)",
          counts == whole and stored["names"] == labels.NAMES
          and all(np.array_equal(m, (seed > 0).astype(np.uint8)) for m in stored["masks"]),
          (counts, [int(m.sum()) for m in stored["masks"]]))
    check("the saved case is on the CT grid, not Slicer's cropped extent",
          stored["masks"].shape[1:] == SHAPE
          and tuple(round(v, 4) for v in stored["spacing"]) == (0.5, 0.5, 0.6),
          (stored["masks"].shape, stored["spacing"], stored["origin"]))

    # The reviewer opens it (onOpenReview: loadSegmentation, then applyProjectNames).
    review = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache"))
    review.project = logic.project
    review.volumeNode = volume
    review.segmentationNode = slicer.util.loadSegmentation(untouched)
    review.applyProjectNames()
    opened = _counts(slicer, labels, review.segmentationNode, volume, review.segmentIdFor)
    check("a reviewer opens all four classes whole (#275)", opened == whole, opened)
    review.showSubmissionIn3d()
    shownDisplay = review.segmentationNode.GetDisplayNode()
    check("and all four are shown", all(
        shownDisplay.GetSegmentVisibility(review.segmentIdFor(n)) for n in TUBES))

    # ... and saves it as their revision: the same four whole classes go back.
    review.client = _RecordingClient()
    review.reviseSubmission("s1")
    check("a revision round-trips the four whole classes (#275)",
          review.client.calls == [("upload", True), ("revise", whole)]
          and review.client.files == [whole]
          and review.client.formats == [labelfile.FORMAT_CLASS_STACK],
          (review.client.calls, review.client.files))
    slicer.mrmlScene.RemoveNode(review.segmentationNode)

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

    counts, _source, _segmentation = logic.exportSubmission(os.path.join(tmp, "out.seg.nrrd"))
    check("a trimmed case exports each class's own tube",
          counts == {name: TUBE_VOXELS for name in TUBES}, counts)

    # A partly trimmed case: LAD still holds the LCx tube. Every class keeps its own
    # voxels in the file -- LAD both tubes, LCx its tube -- nothing given to one class.
    lad[5:35, 30:33, 30:33] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(lad, logic.segmentationNode, segmentId, volume)
    partly = os.path.join(tmp, "partly.seg.nrrd")
    counts, _source, _segmentation = logic.exportSubmission(partly)
    stored = labelfile.read_class_stack(partly)
    byName = dict(zip(stored["names"], stored["masks"]))
    lo, hi = TUBES["LCx"]
    check("a partly trimmed case keeps every class's own voxels (#275)",
          counts == dict({name: TUBE_VOXELS for name in TUBES}, LAD=2 * TUBE_VOXELS)
          and int(byName["LAD"][5:35, lo:hi, lo:hi].sum()) == TUBE_VOXELS
          and int(byName["LCx"][5:35, lo:hi, lo:hi].sum()) == TUBE_VOXELS, counts)
    lad[5:35, 30:33, 30:33] = 0
    slicer.util.updateSegmentBinaryLabelmapFromArray(lad, logic.segmentationNode, segmentId, volume)

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

    # Without SetLabelValue in the import, a submission still has each class in its
    # own channel: exportSubmission reads the classes by name, in project order.
    logic.segmentationNode = fresh
    counts, _source, _segmentation = logic.exportSubmission(os.path.join(tmp, "pre.seg.nrrd"))
    stored = labelfile.read_class_stack(os.path.join(tmp, "pre.seg.nrrd"))
    byChannel = {}
    for name, mask in zip(stored["names"], stored["masks"]):
        byChannel[name] = [other for other, (lo, hi) in TUBES.items()
                           if mask[5:35, lo:hi, lo:hi].any()]
    check("an imported prelabel exports each class in its own channel",
          counts == {name: TUBE_VOXELS for name in TUBES}
          and byChannel == {name: [name] for name in TUBES},
          (counts, byChannel))

    # #270: an empty scene is submitted, as an all-background file on the CT grid.
    empty = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "empty")
    empty.CreateDefaultDisplayNodes()
    empty.SetReferenceImageGeometryParameterFromVolumeNode(volume)
    logic.segmentationNode = empty
    logic._applyTemplate()
    logic.client = _RecordingClient()
    logic.submit()
    check("an empty scene is uploaded and handed over (#270)",
          logic.client.calls == [("upload", True),
                                 ("submit", {name: 0 for name in TUBES})]
          and logic.client.formats == [labelfile.FORMAT_CLASS_STACK],
          logic.client.calls)

    # D39 (#275), end to end as an annotator does it: a fresh seeded case, prefilled,
    # touched by nobody, submitted. Last, because submit closes the case.
    ct2 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "ct2")
    slicer.util.updateVolumeFromArray(ct2, ct)
    ct2.CopyOrientation(volume)
    annotator = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache2"))
    annotator.project = logic.project
    annotator.volumeNode = ct2
    annotator._loadOrCreateSegmentation({})
    os.makedirs(annotator.cache.caseDir("a2"), exist_ok=True)
    seedNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "seed2")
    slicer.util.updateVolumeFromArray(seedNode, seed)
    seedNode.CopyOrientation(volume)
    seedPath2 = os.path.join(annotator.cache.caseDir("a2"), "seed.nii.gz")
    slicer.util.saveNode(seedNode, seedPath2)
    slicer.mrmlScene.RemoveNode(seedNode)
    annotator.seedSegmentId = annotator._importHelper(
        seedPath2, SEED_NAME, (0.95, 0.85, 0.2), 0.25)
    seeded = _Assignment(assignment_id="a2", case_name="seeded", attempt=1,
                         has_seed=True, has_prelabel=False)
    annotator._prefillClassesFromSeed(seeded)
    annotator.assignment = seeded
    annotator._sessionStart = time.time()
    annotator.client = _RecordingClient()
    annotator.submit()
    whole = {name: nSeed for name in TUBES}
    check("an untouched seeded case is submitted with every class whole (#275)",
          annotator.client.calls == [("upload", True), ("submit", whole)]
          and annotator.client.files == [whole]
          and annotator.client.formats == [labelfile.FORMAT_CLASS_STACK],
          (annotator.client.calls, annotator.client.files))
    reopened = slicer.util.loadSegmentation(annotator.client.kept[0])
    again = _counts(slicer, labels, reopened, volume,
                    lambda name: module._segmentIdIn(reopened, name))
    check("and reopens for a reviewer with all four whole (#275)", again == whole, again)


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
