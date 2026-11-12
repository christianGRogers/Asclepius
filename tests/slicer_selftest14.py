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
and round-trips through a reviewer's revision the same way; that a partly
trimmed case keeps every class's own voxels; and (#315) that a case reopened for
the annotator's own revision opens from their submitted read with every class intact.

D44 (#280), the optional extended classes (``run_extended``): a seeded case opens
with the four vessels as before; turning "Extended classes" on adds the 17 empty,
with their pinned label values, grouped under their parents; a branch moved from
LAD into D1 and a painted plaque are submitted, opened by a reviewer and revised
with all 21 classes whole; a 0.17.x four-class draft reopens intact (with the 17
empty extras when the toggle is on); and turning the toggle off removes only the
empty extended classes.

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

    # #315: a case reopened for the annotator's own revision opens from what she
    # submitted -- here the partly trimmed read, LAD still over the LCx tube --
    # with every class as it was, overlap included, and no seed laid over it.
    import shutil

    class _OwnClient:
        def __init__(self, path):
            self.path, self.asked = path, []

        def downloadAsset(self, caseId, kind, stem, progress=None):
            self.asked.append(kind)
            shutil.copy(self.path, stem + ".seg.nrrd")
            return stem + ".seg.nrrd"

    ct3 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "ct3")
    slicer.util.updateVolumeFromArray(ct3, ct)
    ct3.CopyOrientation(volume)
    mine = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache3"))
    mine.project = logic.project
    mine.volumeNode = ct3
    mine.client = _OwnClient(partly)
    own = _Assignment(assignment_id="a3", case_id="c3", case_name="reopened", attempt=2,
                      state="assigned", checksum="", size_bytes=0, has_seed=True,
                      has_prelabel=False, start_from_own=True)
    manifest = mine._startFromOwn(own, mine.cache.open(own))
    mine._loadOrCreateSegmentation(manifest)
    mine.assignment = own
    got = _counts(slicer, labels, mine.segmentationNode, ct3, mine.segmentIdFor)
    asSubmitted = dict({name: TUBE_VOXELS for name in TUBES}, LAD=2 * TUBE_VOXELS)
    check("a reopened case opens from her own read, every class intact (#315)",
          mine.client.asked == ["own"] and mine.resumedDraft and got == asSubmitted,
          (mine.client.asked, got))
    counts, _source, _segmentation = mine.exportSubmission(os.path.join(tmp, "again.seg.nrrd"))
    check("  and kept as it is, it saves back the same classes (D38)",
          counts == asSubmitted, counts)
    slicer.mrmlScene.RemoveNode(mine.segmentationNode)


def _countsOf(slicer, node, volume, names, segmentIdIn):
    """``{name: voxels}`` of ``names`` in ``node``; None for a class it does not have."""
    out = {}
    for name in names:
        segmentId = segmentIdIn(node, name)
        out[name] = None if not segmentId else int((slicer.util.arrayFromSegmentBinaryLabelmap(
            node, segmentId, volume) > 0).sum())
    return out


def _seededCase(slicer, np, module, labels, tmp, name, seed, extended):
    """A fresh seeded case opened as ``openCase`` does, with the toggle as given."""
    from segqueue.protocol import ProjectConfig

    ct = np.where(seed > 0, 400, -100).astype(np.int16)
    volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", name)
    slicer.util.updateVolumeFromArray(volume, ct)
    volume.SetSpacing(0.5, 0.5, 0.6)
    volume.SetOrigin(10, -20, 30)
    logic = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache-" + name))
    logic.project = ProjectConfig(name="selftest", instructions=labels.INSTRUCTIONS,
                                  segments=labels.segment_specs())
    logic.extendedClasses = extended
    logic.volumeNode = volume
    logic._loadOrCreateSegmentation({})
    os.makedirs(logic.cache.caseDir(name), exist_ok=True)
    seedNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", name + "-seed")
    slicer.util.updateVolumeFromArray(seedNode, seed)
    seedNode.CopyOrientation(volume)
    seedPath = os.path.join(logic.cache.caseDir(name), "seed.nii.gz")
    slicer.util.saveNode(seedNode, seedPath)
    slicer.mrmlScene.RemoveNode(seedNode)
    logic.seedSegmentId = logic._importHelper(seedPath, SEED_NAME, (0.95, 0.85, 0.2), 0.25)
    assignment = _Assignment(assignment_id=name, case_name=name, attempt=1,
                             has_seed=True, has_prelabel=False)
    logic._prefillClassesFromSeed(assignment)
    logic.assignment = assignment
    logic._sessionStart = time.time()
    return logic, volume


def _trim(slicer, np, logic, volume):
    """Cut every vessel class down to its own tube."""
    for name, (lo, hi) in TUBES.items():
        segmentId = logic.segmentIdFor(name)
        array = slicer.util.arrayFromSegmentBinaryLabelmap(
            logic.segmentationNode, segmentId, volume).copy()
        keep = np.zeros_like(array)
        keep[5:35, lo:hi, lo:hi] = 1
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            array * keep, logic.segmentationNode, segmentId, volume)


def run_extended():
    import numpy as np

    import slicer

    if not os.environ.get("SEGQUEUE_SELFTEST_INSTALLED"):
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
    import SegQueue14 as module

    from segqueue14 import labelfile, labels

    say("--- D44: extended classes")
    tmp = tempfile.mkdtemp()
    seed = np.zeros(SHAPE, np.uint8)
    for lo, hi in TUBES.values():
        seed[5:35, lo:hi, lo:hi] = 1
    nSeed = int(seed.sum())
    segIn = module._segmentIdIn

    # 1. Toggle off (the default): a seeded case opens with the four vessels, as now.
    four, volume = _seededCase(slicer, np, module, labels, tmp, "four", seed, False)
    names = [four.segmentationNode.GetSegmentation().GetNthSegment(i).GetName()
             for i in range(four.segmentationNode.GetSegmentation().GetNumberOfSegments())]
    check("with the toggle off a seeded case opens with the four vessels",
          sorted(n for n in names if n != SEED_NAME) == sorted(labels.NAMES)
          and _countsOf(slicer, four.segmentationNode, volume, labels.NAMES, segIn)
          == {n: nSeed for n in labels.NAMES}, names)
    four.client = _RecordingClient()
    path = os.path.join(tmp, "four.seg.nrrd")
    four.exportSubmission(path)
    check("and is submitted as a plain four-class read",
          labelfile.read_class_stack(path)["names"] == labels.NAMES)

    # A 0.17.x draft: four trimmed classes, saved, as 0.17.x autosaves it.
    _trim(slicer, np, four, volume)
    draft = os.path.join(tmp, "draft-0.17.seg.nrrd")
    slicer.util.saveNode(four.segmentationNode, draft)
    tubes = {n: TUBE_VOXELS for n in labels.NAMES}

    # 2. The toggle on adds the 17, empty, with their pinned values, under their parents.
    four.extendedClasses = True
    added = four.addExtendedClasses()
    node = four.segmentationNode
    extras = _countsOf(slicer, node, volume, labels.EXTRA_NAMES, segIn)
    check("turning the toggle on adds the 17 extended classes, empty",
          added == 17 and extras == {n: 0 for n in labels.EXTRA_NAMES}, (added, extras))
    values = {n: module._labelValueOf(node.GetSegmentation().GetSegment(segIn(node, n)),
                                      segIn(node, n)) for n in labels.EXTRA_NAMES}
    check("each with its pinned label value",
          values == {n: labels.ALL_LABEL_VALUES[n] for n in labels.EXTRA_NAMES}, values)
    segmentation = node.GetSegmentation()
    order = [segmentation.GetNthSegment(i).GetName()
             for i in range(segmentation.GetNumberOfSegments())]
    check("grouped by parent in the segment list",
          order[:21] == labels.DISPLAY_ORDER, order)
    check("and the four are untouched",
          _countsOf(slicer, node, volume, labels.NAMES, segIn) == tubes)
    check("adding them again adds nothing", four.addExtendedClasses() == 0)
    check("a group hides and shows", four.setGroupVisible(labels.GROUP_LAD, False) == 6
          and not node.GetDisplayNode().GetSegmentVisibility(segIn(node, "D1")))
    four.setGroupVisible(labels.GROUP_LAD, True)

    # 3. A branch moved out of LAD into D1, and a plaque painted on the RCA.
    lo, hi = TUBES["LAD"]
    lad = slicer.util.arrayFromSegmentBinaryLabelmap(node, segIn(node, "LAD"), volume).copy()
    d1 = np.zeros_like(lad)
    d1[5:15, lo:hi, lo:hi] = lad[5:15, lo:hi, lo:hi]
    lad[5:15, lo:hi, lo:hi] = 0
    slicer.util.updateSegmentBinaryLabelmapFromArray(lad, node, segIn(node, "LAD"), volume)
    slicer.util.updateSegmentBinaryLabelmapFromArray(d1, node, segIn(node, "D1"), volume)
    lo, hi = TUBES["RCA"]
    plaque = np.zeros_like(lad)
    plaque[20:24, lo:hi, lo:hi] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(
        plaque, node, segIn(node, "Calcified plaque"), volume)
    want = dict({n: 0 for n in labels.ALL_NAMES}, **tubes)
    want.update({"LAD": TUBE_VOXELS - 90, "D1": 90, "Calcified plaque": 36})
    check("a branch moved from LAD to D1 and a plaque painted",
          _countsOf(slicer, node, volume, labels.ALL_NAMES, segIn) == want,
          _countsOf(slicer, node, volume, labels.ALL_NAMES, segIn))

    # 4. Submit, reviewer open, revise: all 21 classes whole, every time. Submit
    # closes the case and takes its CT out of the scene, so the reviewer and the
    # resumed drafts below get a CT of their own, on the same grid.
    volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "ct-review")
    slicer.util.updateVolumeFromArray(volume, np.where(seed > 0, 400, -100).astype(np.int16))
    volume.SetSpacing(0.5, 0.5, 0.6)
    volume.SetOrigin(10, -20, 30)
    four.client = _RecordingClient()
    four.submit()
    check("submit uploads all 21 classes whole",
          four.client.calls == [("upload", True), ("submit", want)]
          and four.client.files == [want], (four.client.calls, four.client.files))
    uploaded = four.client.kept[0]
    stored = labelfile.read_class_stack(uploaded)
    check("in label order, the extended read's channels", stored["names"] == labels.ALL_NAMES,
          stored["names"])
    review = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "review"))
    review.project = four.project
    review.volumeNode = volume
    review.segmentationNode = slicer.util.loadSegmentation(uploaded)
    review.applyProjectNames()
    opened = _countsOf(slicer, review.segmentationNode, volume, labels.ALL_NAMES, segIn)
    check("a reviewer opens all 21 classes whole, even with the toggle off",
          opened == want and not review.extendedClasses, opened)
    review.client = _RecordingClient()
    review.reviseSubmission("s21")
    check("and a revision round-trips all 21",
          review.client.calls == [("upload", True), ("revise", want)]
          and review.client.files == [want]
          and labelfile.read_class_stack(review.client.kept[0])["names"] == labels.ALL_NAMES,
          (review.client.calls, review.client.files))
    slicer.mrmlScene.RemoveNode(review.segmentationNode)

    # 5. The 0.17.x four-class draft reopens intact, toggle off and on.
    for on in (False, True):
        resumed = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "resume"))
        resumed.project = four.project
        resumed.extendedClasses = on
        resumed.volumeNode = volume
        resumed._loadOrCreateSegmentation({"workPath": draft})
        got = _countsOf(slicer, resumed.segmentationNode, volume, labels.ALL_NAMES, segIn)
        expected = dict({n: (0 if on else None) for n in labels.EXTRA_NAMES}, **tubes)
        check("a 0.17.x four-class draft reopens intact (toggle {})".format(
            "on: the 17 added, empty" if on else "off"), got == expected, got)
        path = os.path.join(tmp, "resumed-{}.seg.nrrd".format(on))
        resumed.exportSubmission(path)
        check("  and exports {} classes".format(21 if on else 4),
              labelfile.read_class_stack(path)["names"]
              == (labels.ALL_NAMES if on else labels.NAMES))
        if on:
            # 6. Off again: the empty extended classes go, a painted one stays.
            d1 = np.zeros(SHAPE, np.uint8)
            d1[5:7, 20:23, 20:23] = 1
            slicer.util.updateSegmentBinaryLabelmapFromArray(
                d1, resumed.segmentationNode, segIn(resumed.segmentationNode, "D1"), volume)
            resumed.extendedClasses = False
            removed, kept = resumed.removeEmptyExtendedClasses()
            check("toggling off removes only the empty extended classes",
                  kept == ["D1"] and len(removed) == 16, (removed, kept))
            check("  so the read keeps all 21 channels while D1 has voxels",
                  [s.name for s in resumed.classSpecs()] == labels.ALL_NAMES)
        slicer.mrmlScene.RemoveNode(resumed.segmentationNode)

    # 7. Toggle on from the start: the seed fills the four only; the 17 start empty.
    fresh, volume2 = _seededCase(slicer, np, module, labels, tmp, "fresh", seed, True)
    got = _countsOf(slicer, fresh.segmentationNode, volume2, labels.ALL_NAMES, segIn)
    check("with the toggle on a seeded case opens with the four seeded and 17 empty",
          got == dict({n: 0 for n in labels.EXTRA_NAMES}, **{n: nSeed for n in labels.NAMES}),
          got)


for part in (run, run_extended):
    try:
        part()
    except Exception:
        say("EXCEPTION in", part.__name__, traceback.format_exc())
        checks.append(False)

passed = bool(checks) and all(checks)
say("RESULT", "PASS" if passed else "FAIL")
with open(OUT, "w") as handle:
    handle.write("\n".join(log) + "\n")

import slicer  # noqa: E402  (only importable inside Slicer)

slicer.app.exit(0 if passed else 1)
