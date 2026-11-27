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
empty extras when the toggle is on); and turning the toggle off removes nothing
(D53).

D53 (0.25.6, ``run_d53``), the toggle only hides: through the panel, D1 painted, D2
cut with Inverse cut and OM2 trimmed from its seed copy keep every voxel over three
off-and-on toggles; off hides the classes, their rows in the editor's list and the
group rows, and on shows them with the eyes they had; no dialog is raised by the
toggle or by submit; a draft saved with the toggle off resumes with the work; the
export is 21 channels with the work in them when any extended class holds work,
toggle off or on, and the four when they are all empty or untouched seed copies;
a Complete tick with no voxels and a flagged case with nothing drawn are 21 (D47
stands); and a reviewer's panel toggles the same way and revises all 21.

D47 (#322, ``run_d47``): a case flagged for extended mode opens with the extended
classes; the three branch-group "complete" tick-boxes start unticked, are saved
with the draft, go into the class-stack header on submit, are shown to a reviewer
and kept by a revision; and a PDA moved out of the LCx collapses into the LCx.

#335 (``run_compare``), the reviewer's "Compare reads" view: three synthetic reads of
one case load together, read-only; the agreement map's both / A-only / B-only counts
match a hand-computed overlap per class, on the CT grid; the Dice shown is the
server's pair score; an extended read against a four-class read compares after the
collapse; any two of three can be picked; the panel drives it; nothing is written.

Protocol 21 (``run_defect_cases``), the reviewer's case list: the search box narrows
it by case name (any case, every loaded case) without changing its order; a defect
case carries a "Defect" badge with who, when and why; "Defect only" and the
Mark/Unmark button are hidden on an older server; marking asks first, saying how
many annotators hold the case, with an optional reason; unmarking asks; a refusal
is the server's sentence; the benchmark's button is disabled.

0.25.4 (``run_overlap``, D52, D39, D44): a material painted inside an artery keeps both
classes. "Calcified plaque" goes inside a trimmed LAD through Paint, Draw, Scissors
(fill inside), Threshold, Draw tube (when installed), Islands, Logical operators
(copy, add) and Inverse cut, on an own case and as a reviewer editing a submission,
and the LAD keeps every voxel; Slicer's own Segment Editor module, a node made after
a scene clear and the panel all start at "Allow overlap"; a mode the annotator
picks is kept until the next case; the export has two overlapping channels. D52:
on a seeded case the 17 start with 0 voxels and a branch selected in the panel becomes
the seed (that class only);
plaque painted inside the LAD is submitted as plaque, overlapping it; selecting a
hidden class (own case and reviewer) shows it and only it, with no "segment is
hidden" question, and the first paint stroke on it lands.

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


def _layerOf(segmentationNode, segmentId):
    """The labelmap layer (a vtkOrientedImageData) a segment's voxels live in."""
    segment = segmentationNode.GetSegmentation().GetSegment(segmentId)
    return segment.GetRepresentation("Binary labelmap") if segment is not None else None


def _classLayers(segmentationNode, segmentId, labels):
    """``{class: voxels in the labelmap layer holding it}`` for the four classes."""
    found = {}
    for spec in labels.segment_specs():
        layer = _layerOf(segmentationNode, segmentId(spec.name))
        found[spec.name] = int(layer.GetNumberOfPoints()) if layer is not None else 0
    return found


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

    # 0.25.5: each copy is written in place, in a labelmap layer the seed's size --
    # not one the CT's size per class (about 315M voxels at open on a real CT).
    # Each class still in a layer of its own, so trimming one leaves the others.
    ks, js, iz = np.nonzero(seed)
    seedBox = ((ks.max() - ks.min() + 1) * (js.max() - js.min() + 1)
               * (iz.max() - iz.min() + 1))
    classLayers = _classLayers(logic.segmentationNode, logic.segmentIdFor, labels)
    check("the seed copies are not full-CT labelmap layers (0.25.5)", all(
        0 < n <= seedBox < int(np.prod(SHAPE)) for n in classLayers.values()),
        (classLayers, int(seedBox), int(np.prod(SHAPE))))
    check("each seed copy is in a labelmap layer of its own",
          len({_layerOf(logic.segmentationNode, logic.segmentIdFor(n))
               for n in classLayers}) == 4)

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
    assignment = _Assignment(assignment_id=name, case_name=name, attempt=1,
                             has_seed=True, has_prelabel=False)
    logic.assignment = assignment
    logic._loadOrCreateSegmentation({})
    os.makedirs(logic.cache.caseDir(name), exist_ok=True)
    logic.cache.writeManifest(name, {"assignmentId": name})
    seedNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", name + "-seed")
    slicer.util.updateVolumeFromArray(seedNode, seed)
    seedNode.CopyOrientation(volume)
    seedPath = os.path.join(logic.cache.caseDir(name), "seed.nii.gz")
    slicer.util.saveNode(seedNode, seedPath)
    slicer.mrmlScene.RemoveNode(seedNode)
    logic.seedSegmentId = logic._importHelper(seedPath, SEED_NAME, (0.95, 0.85, 0.2), 0.25)
    logic._prefillClassesFromSeed(assignment)
    # D52: as openCase does, the extended classes added at open stay empty; a
    # branch gets its seed copy when first selected (seedOnFirstSelection).
    logic._restoreFirstSelected({})
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
        # D53: the 17 empty extras are not work, so the read is the four either way.
        check("  and exports 4 classes ({})".format(
            "the 17 hold no work" if on else "no extended classes"),
              labelfile.read_class_stack(path)["names"] == labels.NAMES)
        if on:
            # 6. Off again (D53): every extended class stays, hidden; a painted one
            # keeps the read at 21 channels.
            d1 = np.zeros(SHAPE, np.uint8)
            d1[5:7, 20:23, 20:23] = 1
            slicer.util.updateSegmentBinaryLabelmapFromArray(
                d1, resumed.segmentationNode, segIn(resumed.segmentationNode, "D1"), volume)
            resumed.extendedClasses = False
            resumed.setExtendedShown(False)
            check("toggling off keeps every extended class (D53)",
                  all(segIn(resumed.segmentationNode, n) for n in labels.EXTRA_NAMES)
                  and _countsOf(slicer, resumed.segmentationNode, volume, ["D1"], segIn)
                  == {"D1": 18})
            path = os.path.join(tmp, "resumed-off.seg.nrrd")
            resumed.exportSubmission(path)
            check("  and the read is sent with all 21 channels while D1 has work",
                  labelfile.read_class_stack(path)["names"] == labels.ALL_NAMES)
        slicer.mrmlScene.RemoveNode(resumed.segmentationNode)

    # 7. Toggle on from the start: the seed fills the four (D26); the 17 start
    # empty, a branch filled only when first selected (D52).
    fresh, volume2 = _seededCase(slicer, np, module, labels, tmp, "fresh", seed, True)
    got = _countsOf(slicer, fresh.segmentationNode, volume2, labels.ALL_NAMES, segIn)
    check("with the toggle on a seeded case opens with the four seeded and the 17 "
          "extended classes empty (D52)",
          got == {n: 0 if n in labels.EXTRA_NAMES else nSeed for n in labels.ALL_NAMES}, got)


def run_d51():
    """D51: Inverse cut is registered and listed by the editor, and cuts. D51/D52:
    toggle-on adds the extended classes with no seed voxels; on an own case a branch
    becomes the seed on its first selection, exactly that class, once; materials and
    a reviewer's classes stay empty; export sends untouched seed copies empty; the
    toggle off keeps them (D53); a first selection keeps every other 3D surface."""
    import numpy as np

    import slicer

    if not os.environ.get("SEGQUEUE_SELFTEST_INSTALLED"):
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
    import SegQueue14 as module

    from segqueue14 import labelfile, labels

    say("--- D51: inverse cut, seeded extended classes")
    tmp = tempfile.mkdtemp()
    seed = np.zeros(SHAPE, np.uint8)
    for lo, hi in TUBES.values():
        seed[5:35, lo:hi, lo:hi] = 1
    nSeed = int(seed.sum())
    segIn = module._segmentIdIn

    # 1. The effect: registered, with its icon, and listed by an embedded editor.
    check("Inverse cut is registered", module.registerInverseCutEffect())
    factory = slicer.qSlicerSegmentEditorEffectFactory.instance()
    names = [effect.name for effect in factory.registeredEffects()]
    check("  in the effect factory, once", names.count("Inverse cut") == 1, names)
    editor = slicer.qMRMLSegmentEditorWidget()
    editor.setMRMLScene(slicer.mrmlScene)
    editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    editor.setMRMLSegmentEditorNode(editorNode)
    effect = editor.effectByName("Inverse cut")
    check("  and listed by an embedded Segment Editor", effect is not None)
    try:
        # PythonQt does not wrap the C++ icon(); the scripted effect's icon() is
        # the Python one, which is what the editor's button shows.
        check("  with its own icon", not effect.self().icon().isNull())
    except Exception:
        check("  with its own icon", False, traceback.format_exc())

    # 2. Own seeded case, toggle on (D52): the 17 added with no seed voxels; the
    # first selection of a branch fills exactly that one, from the seed.
    logic, volume = _seededCase(slicer, np, module, labels, tmp, "own", seed, True)
    node = logic.segmentationNode
    got = _countsOf(slicer, node, volume, labels.EXTRA_NAMES, segIn)
    check("toggle-on adds the 17 extended classes with no seed voxels (D52)",
          got == {n: 0 for n in labels.EXTRA_NAMES}, got)
    check("  the first selection of a branch fills it from the seed",
          logic.seedOnFirstSelection(segIn(node, "D2")) is True)
    got = _countsOf(slicer, node, volume, labels.EXTRA_NAMES, segIn)
    check("  exactly that one class",
          got == {n: nSeed if n == "D2" else 0 for n in labels.EXTRA_NAMES}, got)
    check("  and it is recorded for the draft",
          logic.seedFirstSelected == {"D2"}
          and logic.cache.manifest("own").get("seedFirstSelected") == ["D2"],
          (logic.seedFirstSelected, logic.cache.manifest("own")))
    for name in labels.EXTRA_NAMES:
        logic.seedOnFirstSelection(segIn(node, name))
    got = _countsOf(slicer, node, volume, labels.EXTRA_NAMES, segIn)
    check("selecting each one: the branches become the seed, the materials stay empty",
          got == {n: 0 if n in labels.MATERIALS else nSeed for n in labels.EXTRA_NAMES}, got)
    emptied = np.zeros(SHAPE, np.uint8)
    slicer.util.updateSegmentBinaryLabelmapFromArray(emptied, node, segIn(node, "D3"), volume)
    check("a branch emptied on purpose is not refilled when selected again",
          logic.seedOnFirstSelection(segIn(node, "D3")) is False
          and _countsOf(slicer, node, volume, ["D3"], segIn) == {"D3": 0})
    slicer.util.updateSegmentBinaryLabelmapFromArray(seed, node, segIn(node, "D3"), volume)

    # 3. Inverse cut through the real path (0.25.1): a real Red slice view and 3D
    # view, an oblique CT, and the mouse driven through the views' interactors.
    try:
        _inverseCutInRealViews(slicer, np, editor, editorNode)
    except Exception:
        check("inverse cut runs in real views", False, traceback.format_exc())
    finally:
        editor.setActiveEffectByName("")

    # 4. Export: untouched seed copies go empty, D1 cut down as it is.
    d1 = slicer.util.arrayFromSegmentBinaryLabelmap(node, segIn(node, "D1"), volume).copy()
    d1[5:10] = 0
    slicer.util.updateSegmentBinaryLabelmapFromArray(d1, node, segIn(node, "D1"), volume)
    path = os.path.join(tmp, "d51.seg.nrrd")
    counts, _, _ = logic.exportSubmission(path)
    stored = labelfile.read_class_stack(path)
    written = labelfile.voxel_counts(stored["masks"], stored["names"])
    want = dict({n: 0 for n in labels.EXTRA_NAMES}, **{n: nSeed for n in labels.NAMES})
    want["D1"] = int(d1.sum())
    check("export sends untouched seed copies empty, the four and D1 as they are",
          written == want and counts == want
          and len(logic.seedCopiesBlanked) == 13
          and not set(logic.seedCopiesBlanked) & set(labels.MATERIALS),
          (written, logic.seedCopiesBlanked))

    # 5. Toggle off: untouched seed copies and the empty materials go, a trimmed
    # D1 stays. With the classes shown in 3D (Show in 3D), the toggle keeps them.
    logic.showPrelabelIn3d()

    def inThreeD(name):
        surface = _closedSurface(slicer, node, segIn(node, name))
        return surface is not None and surface.GetNumberOfPoints() > 0

    # D53: off only hides -- the untouched copies stay copies, D1 stays trimmed.
    kept = _countsOf(slicer, node, volume, labels.EXTRA_NAMES, segIn)
    logic.extendedClasses = False
    logic.setExtendedShown(False)
    check("toggling off removes nothing and changes no voxel (D53)",
          _countsOf(slicer, node, volume, labels.EXTRA_NAMES, segIn) == kept, kept)
    check("  and the classes stay in the 3D view",
          inThreeD("LAD") and inThreeD("D1"), (inThreeD("LAD"), inThreeD("D1")))

    # On again: nothing to add, nothing refilled, the 3D view keeps every class.
    logic.extendedClasses = True
    check("toggling on again adds nothing and keeps every class as it was",
          logic.addExtendedClasses() == 0 and logic.setExtendedShown(True) == 17
          and _countsOf(slicer, node, volume, labels.EXTRA_NAMES, segIn) == kept)
    check("  a branch already selected in this read is not refilled",
          logic.seedOnFirstSelection(segIn(node, "PDA")) is False
          and _countsOf(slicer, node, volume, ["PDA"], segIn) == {"PDA": nSeed})
    check("  and the 3D view keeps the classes without Show in 3D",
          inThreeD("LAD") and inThreeD("D1"), (inThreeD("LAD"), inThreeD("D1")))

    # A first selection with the classes shown in 3D: only that class's surface is
    # built, and every other class keeps its own (D52, in place).
    for name in labels.EXTRA_NAMES:
        node.GetSegmentation().RemoveSegment(segIn(node, name))
    logic.seedFirstSelected = set()
    logic.addExtendedClasses()
    logic.showPrelabelIn3d()
    check("a first selection with surfaces shown builds that class's surface, keeping "
          "the others'", logic.seedOnFirstSelection(segIn(node, "PDA")) is True
          and inThreeD("PDA") and inThreeD("LAD") and inThreeD("RCA"),
          (inThreeD("PDA"), inThreeD("LAD"), inThreeD("RCA")))

    # 6. A reviewer's added classes stay empty, seed in the scene or not.
    logic.assignment = None
    for name in labels.EXTRA_NAMES:
        node.GetSegmentation().RemoveSegment(segIn(node, name))
    logic.seedFirstSelected = set()
    logic.addExtendedClasses()
    for name in labels.EXTRA_NAMES:
        logic.seedOnFirstSelection(segIn(node, name))
    check("a reviewer's extended classes stay empty, also when selected",
          _countsOf(slicer, node, volume, labels.EXTRA_NAMES, segIn)
          == {n: 0 for n in labels.EXTRA_NAMES})



# --------------------------------------------------------------------- D51 views

#: Inverse cut's test CT: not aligned with slice XY. Spacing, origin, and a 20
#: degree turn about S, so a raw event position is nowhere near a voxel index.
_IC_SHAPE = (40, 50, 60)
_IC_SPACING = (0.7, 0.8, 1.5)
_IC_ORIGIN = (-30.0, 12.0, 40.0)
#: The selected segment, ``[k, j, i]``, and the part an outline keeps of it.
_IC_SEGMENT = (slice(5, 35), slice(10, 40), slice(10, 50))
_IC_KEEP = (slice(5, 35), slice(20, 31), slice(20, 31))


def _matrixOf(np, vtkMatrix):
    return np.array([[vtkMatrix.GetElement(r, c) for c in range(4)] for r in range(4)])


def _closedSurface(slicer, node, segmentId):
    """The segment's closed-surface polydata as the 3D view has it, or None."""
    segment = node.GetSegmentation().GetSegment(segmentId)
    name = slicer.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
    return None if segment is None else segment.GetRepresentation(name)


def _rasBox(np, rasOf, keep):
    """Min and max RAS corner of the voxels ``keep`` (k, j, i slices), to their faces."""
    k, j, i = keep
    corners = [rasOf @ [x, y, z, 1]
               for x in (i.start - 0.5, i.stop - 0.5)
               for y in (j.start - 0.5, j.stop - 0.5)
               for z in (k.start - 0.5, k.stop - 0.5)]
    corners = np.array(corners)[:, :3]
    return corners.min(axis=0), corners.max(axis=0)


def _ensureLayout(slicer, qt):
    """The application's layout manager; one of our own under --no-main-window,
    where the Segment Editor would otherwise have no views to observe."""
    if slicer.app.layoutManager() is not None:
        return slicer.app.layoutManager(), None
    viewport = qt.QWidget()
    viewport.resize(900, 700)
    layoutManager = slicer.qSlicerLayoutManager(viewport)
    layoutManager.setMRMLScene(slicer.mrmlScene)
    slicer.app.setLayoutManager(layoutManager)
    viewport.show()
    return layoutManager, viewport


def _drag(vtk, interactor, points):
    """Press at the first point, move through the rest and back, release: what a
    mouse does, as the view's interactor reports it to the Segment Editor."""
    interactor.SetEventPosition(int(round(points[0][0])), int(round(points[0][1])))
    interactor.InvokeEvent(vtk.vtkCommand.LeftButtonPressEvent)
    for x, y in list(points[1:]) + [points[0]]:
        interactor.SetEventPosition(int(round(x)), int(round(y)))
        interactor.InvokeEvent(vtk.vtkCommand.MouseMoveEvent)
    interactor.InvokeEvent(vtk.vtkCommand.LeftButtonReleaseEvent)


def _qtDrag(slicer, qt, widget, points):
    """The same drag as Qt mouse events on the view's OpenGL widget, so it goes
    through VTK's Qt adapter (device-pixel-ratio scaling, y flip) too."""
    ratio = widget.devicePixelRatioF() if hasattr(widget, "devicePixelRatioF") else 1.0
    height = widget.height

    def send(kind, point, button, buttons):
        position = qt.QPointF(point[0] / ratio, height - 1 - point[1] / ratio)
        slicer.app.sendEvent(widget, qt.QMouseEvent(kind, position, button, buttons,
                                                    qt.Qt.NoModifier))

    send(qt.QEvent.MouseMove, points[0], qt.Qt.NoButton, qt.Qt.NoButton)
    send(qt.QEvent.MouseButtonPress, points[0], qt.Qt.LeftButton, qt.Qt.LeftButton)
    for point in list(points[1:]) + [points[0]]:
        send(qt.QEvent.MouseMove, point, qt.Qt.NoButton, qt.Qt.LeftButton)
    send(qt.QEvent.MouseButtonRelease, points[0], qt.Qt.LeftButton, qt.Qt.NoButton)
    slicer.app.processEvents()


def _iconCursor(np, qt, view):
    """Whether ``view`` shows a bitmap cursor with the icon's yellow in it."""
    cursor = view.cursor
    if cursor.shape() != qt.Qt.BitmapCursor or cursor.pixmap().isNull():
        return False
    image = cursor.pixmap().toImage()
    for y in range(image.height()):
        for x in range(image.width()):
            colour = qt.QColor(image.pixel(x, y))
            if colour.red() > 200 and colour.green() > 170 and colour.blue() < 110:
                return True
    return False


def _inverseCutInRealViews(slicer, np, editor, editorNode):
    import qt
    import vtk

    layoutManager, viewport = _ensureLayout(slicer, qt)
    scene = slicer.mrmlScene
    volume = scene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "inverse cut CT")
    slicer.util.updateVolumeFromArray(volume, np.zeros(_IC_SHAPE, np.int16))
    volume.SetSpacing(*_IC_SPACING)
    volume.SetOrigin(*_IC_ORIGIN)
    turn = np.radians(20)
    direction = vtk.vtkMatrix4x4()
    for r, row in enumerate([[np.cos(turn), -np.sin(turn), 0],
                             [np.sin(turn), np.cos(turn), 0], [0, 0, 1]]):
        for c, value in enumerate(row):
            direction.SetElement(r, c, value)
    volume.SetIJKToRASDirectionMatrix(direction)
    node = scene.AddNewNodeByClass("vtkMRMLSegmentationNode", "inverse cut")
    node.CreateDefaultDisplayNodes()
    node.SetReferenceImageGeometryParameterFromVolumeNode(volume)
    lad = node.GetSegmentation().AddEmptySegment("LAD")
    other = node.GetSegmentation().AddEmptySegment("LCx")
    start = np.zeros(_IC_SHAPE, np.uint8)
    start[_IC_SEGMENT] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(start, node, lad, volume)
    slicer.util.updateSegmentBinaryLabelmapFromArray(start, node, other, volume)
    want = np.zeros(_IC_SHAPE, bool)
    want[_IC_KEEP] = True

    def voxels(segmentId):
        return slicer.util.arrayFromSegmentBinaryLabelmap(node, segmentId, volume) > 0

    def reset():
        slicer.util.updateSegmentBinaryLabelmapFromArray(start, node, lad, volume)
        # The writes above drop every segment's surface; put the 3D view back the
        # way the annotator had it (Show in 3D) before the next cut.
        node.CreateClosedSurfaceRepresentation()

    # The classes shown in 3D, as the module's Show in 3D leaves them.
    node.CreateClosedSurfaceRepresentation()
    node.GetDisplayNode().SetVisibility3D(True)
    rasOfIjk = vtk.vtkMatrix4x4()
    volume.GetIJKToRASMatrix(rasOfIjk)

    def surfaceInside(segmentId, keep, label):
        """Check the segment still has a closed surface after a cut, with no Show
        in 3D: non-empty, and inside the RAS box of the voxels ``keep`` (k, j, i
        slices) -- the cut's shape, not the segment it was cut from."""
        surface = _closedSurface(slicer, node, segmentId)
        points = 0 if surface is None else surface.GetNumberOfPoints()
        bounds = None if not points else surface.GetBounds()
        box = _rasBox(np, _matrixOf(np, rasOfIjk), keep)
        # A voxel's slack: the surface overshoots the voxel faces a little (0.5 mm
        # along the 1.5 mm axis in 5.8); the uncut segment is ~9 mm wider.
        slack = max(_IC_SPACING)
        inside = bounds is not None and all(
            box[0][a] - slack <= bounds[2 * a] and bounds[2 * a + 1] <= box[1][a] + slack
            for a in range(3))
        check(label, points > 0 and inside, (points, bounds, box))

    slicer.util.setSliceViewerLayers(background=volume, fit=True)
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    slicer.app.processEvents()
    red = layoutManager.sliceWidget("Red")
    sliceNode = red.mrmlSliceNode()
    red.sliceLogic().FitSliceToAll()
    ijkToRas = vtk.vtkMatrix4x4()
    volume.GetIJKToRASMatrix(ijkToRas)
    rasOf = _matrixOf(np, ijkToRas)
    sliceNode.JumpSliceByCentering(*(rasOf @ [25, 25, 20, 1])[:3])
    slicer.app.processEvents()

    editor.setSegmentationNode(node)
    editor.setSourceVolumeNode(volume)
    editorNode.SetSelectedSegmentID(lad)
    editor.show()
    editor.setActiveEffectByName("Inverse cut")
    slicer.app.processEvents()

    # The cursor: the effect's icon, over the slice view and (as Scissors) the 3D view.
    check("Inverse cut's cursor over the Red view is its icon",
          _iconCursor(np, qt, red.sliceView()), red.sliceView().cursor.shape())

    # The outline: the kept box's corners (half a voxel out), mapped to screen
    # through the slice node, the way the mouse would have to go round it.
    corners = [(19.5, 19.5), (30.5, 19.5), (30.5, 30.5), (19.5, 30.5)]

    def onScreen(i, j):
        xy = np.linalg.inv(_matrixOf(np, sliceNode.GetXYToRAS())) @ (rasOf @ [i, j, 20, 1])
        return xy[0], xy[1]

    lasso = [onScreen(i, j) for i, j in corners]
    interactor = red.sliceView().interactor()
    _drag(vtk, interactor, lasso)
    slicer.app.processEvents()
    got = voxels(lad)
    check("inverse cut in a real Red view keeps what the outline goes round, "
          "every slice", np.array_equal(got, want),
          (int(got.sum()), int(want.sum())))
    check("  and leaves the other class alone",
          np.array_equal(voxels(other), start > 0))
    surfaceInside(lad, _IC_KEEP, "  and it is still in the 3D view, cut, without Show in 3D")
    surfaceInside(other, _IC_SEGMENT, "  and so is the other class, whole")
    editor.undo()
    check("  one undo puts it back", np.array_equal(voxels(lad), start > 0))
    undoButton = editor.findChild(qt.QToolButton, "UndoButton")
    if undoButton is not None:
        check("  in a single undo step", not undoButton.enabled)
    else:
        say("SKIP the undo-depth check: no UndoButton in this Slicer's editor")

    # The fail-safe: an outline beside the segment changes nothing.
    beside = [onScreen(i, j) for i, j in
              [(52.5, 41.5), (58.5, 41.5), (58.5, 48.5), (52.5, 48.5)]]
    _drag(vtk, interactor, beside)
    slicer.app.processEvents()
    check("an outline that holds none of the segment leaves it unchanged",
          np.array_equal(voxels(lad), start > 0), int(voxels(lad).sum()))

    reset()
    # The same drag as Qt mouse events, through VTK's Qt adapter.
    glWidgets = [w for w in red.sliceView().findChildren(qt.QWidget)
                 if "OpenGL" in w.className()]
    if glWidgets:
        _qtDrag(slicer, qt, glWidgets[0], lasso)
        got = voxels(lad)
        check("  and the same from Qt mouse events", np.array_equal(got, want),
              int(got.sum()))
        reset()
    else:
        say("SKIP the Qt-event drag: no OpenGL widget under the Red view")

    reset()
    # A lightbox: four panes, the outline drawn in the top-right one. 0.25.0 read
    # the event position as slice XY and wiped the segment here. Slicer 5.8 has
    # this lightbox (the slice node's layout grid); later Slicers ignore the grid.
    sliceNode.SetLayoutGrid(2, 2)
    slicer.app.processEvents()
    if sliceNode.GetLayoutGridRows() == 2 and sliceNode.GetLayoutGridColumns() == 2:
        width, height = red.sliceView().renderWindow().GetSize()
        paneWidth, paneHeight = width / 2.0, height / 2.0
        lightbox = [(x + paneWidth, y + paneHeight) for x, y in
                    [onScreen(i, j) for i, j in corners]]
        xyz = [0.0, 0.0, 0.0]
        slicer.vtkMRMLAbstractSliceViewDisplayableManager.ConvertDeviceToXYZ(
            interactor, sliceNode, int(round(lightbox[0][0])), int(round(lightbox[0][1])),
            xyz)
        _drag(vtk, interactor, lightbox)
        slicer.app.processEvents()
        got = voxels(lad)
        check("inverse cut in a lightbox pane keeps what the outline goes round",
              np.array_equal(got, want), (int(got.sum()), xyz))
        reset()
        sliceNode.SetLayoutGrid(1, 1)
        slicer.app.processEvents()
    else:
        say("SKIP the lightbox drag: this Slicer has no slice-node layout grid")

    # The 3D view, against VTK's own world-to-display conversion.
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    slicer.app.processEvents()
    threeD = layoutManager.threeDWidget(0).threeDView()
    threeD.resetFocalPoint()
    renderer = threeD.renderWindow().GetRenderers().GetFirstRenderer()
    camera = renderer.GetActiveCamera()
    camera.Azimuth(35)
    camera.Elevation(20)
    camera.OrthogonalizeViewUp()
    renderer.ResetCameraClippingRange()
    threeD.forceRender()
    slicer.app.processEvents()
    check("Inverse cut's cursor over the 3D view is its icon",
          _iconCursor(np, qt, threeD), threeD.cursor.shape())

    def display(ras):
        coordinate = vtk.vtkCoordinate()
        coordinate.SetCoordinateSystemToWorld()
        coordinate.SetValue(*ras)
        return coordinate.GetComputedDoubleDisplayValue(renderer)

    centre = display((rasOf @ [30, 25, 20, 1])[:3])
    box = (centre[0] - 25, centre[1] - 20, centre[0] + 25, centre[1] + 20)
    _drag(vtk, threeD.interactor(),
          [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])])
    slicer.app.processEvents()
    got = voxels(lad)
    k, j, i = np.nonzero(start)
    ras = (np.stack([i, j, k, np.ones_like(i)], axis=1) @ rasOf.T)[:, :3]
    wrong = 0
    for n in range(len(k)):
        x, y = display(ras[n])
        margin = min(x - box[0], box[2] - x, y - box[1], box[3] - y)
        if abs(margin) > 1.0 and (margin > 0) != bool(got[k[n], j[n], i[n]]):
            wrong += 1
    check("inverse cut in the 3D view keeps what projects inside the outline",
          0 < int(got.sum()) < int(start.sum()) and wrong == 0,
          (int(got.sum()), wrong))
    kk, jj, ii = np.nonzero(got)
    kept = (slice(kk.min(), kk.max() + 1), slice(jj.min(), jj.max() + 1),
            slice(ii.min(), ii.max() + 1)) if len(kk) else _IC_KEEP
    surfaceInside(lad, kept, "  and the cut class is still in the 3D view, as cut")
    reset()

    # An empty class takes the seed inside the outline (D51 a), in 3D too.
    seedId = node.GetSegmentation().AddEmptySegment("seed", SEED_NAME)
    slicer.util.updateSegmentBinaryLabelmapFromArray(start, node, seedId, volume)
    empty = node.GetSegmentation().AddEmptySegment("RCA", "RCA")
    node.CreateClosedSurfaceRepresentation()
    editorNode.SetSelectedSegmentID(empty)
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    slicer.app.processEvents()
    _drag(vtk, interactor, lasso)
    slicer.app.processEvents()
    got = voxels(empty)
    check("an empty class takes the seed inside the outline",
          np.array_equal(got, want), int(got.sum()))
    surfaceInside(empty, _IC_KEEP, "  and shows in 3D without Show in 3D")
    check("  the seed is left whole", np.array_equal(voxels(seedId), start > 0))

    editor.setActiveEffectByName("")
    scene.RemoveNode(node)
    scene.RemoveNode(volume)
    if viewport is not None:
        layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
        viewport.hide()


def run_d47():
    """D47 (#322): a flagged case opens with the extended classes; the branch-group
    tick-boxes are saved with the draft, written in the class-stack header on
    submit, shown to a reviewer and kept by a revision; a PDA moved out of the LCx
    collapses into the LCx."""
    import numpy as np

    import slicer

    if not os.environ.get("SEGQUEUE_SELFTEST_INSTALLED"):
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
    import SegQueue14 as module

    from segqueue.protocol import ProjectConfig
    from segqueue14 import labelfile, labels

    say("--- D47: branch parents, complete groups, extended-mode cases")
    tmp = tempfile.mkdtemp()
    segIn = module._segmentIdIn
    seed = np.zeros(SHAPE, np.uint8)
    for lo, hi in TUBES.values():
        seed[5:35, lo:hi, lo:hi] = 1

    def ct(name):
        volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", name)
        slicer.util.updateVolumeFromArray(volume, np.where(seed > 0, 400, -100).astype(np.int16))
        volume.SetSpacing(0.5, 0.5, 0.6)
        volume.SetOrigin(10, -20, 30)
        return volume

    project = ProjectConfig(name="selftest", instructions=labels.INSTRUCTIONS,
                            segments=labels.segment_specs())
    flagged = _Assignment(assignment_id="x1", case_id="cx1", case_name="flagged", attempt=1,
                          state="assigned", checksum="", size_bytes=0, has_seed=True,
                          has_prelabel=False, extended_mode=True)

    # 1. A flagged case, toggle off: opens with the extended classes on.
    logic = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache"))
    logic.project = project
    logic.extendedClasses = False
    volume = ct("ct-flagged")
    logic.volumeNode = volume
    manifest = logic.cache.open(flagged)
    logic._applyCaseFlags(flagged, manifest)
    logic._loadOrCreateSegmentation(manifest)
    logic.assignment = flagged
    logic._sessionStart = time.time()
    got = _countsOf(slicer, logic.segmentationNode, volume, labels.ALL_NAMES, segIn)
    check("a flagged case opens with all 21 classes, toggle off",
          logic.extendedOn() and not logic.extendedClasses
          and all(got[n] is not None for n in labels.ALL_NAMES), got)
    plain = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "plain"))
    plain.project = project
    plain.volumeNode = volume
    unflagged = _Assignment(**dict(flagged.__dict__, assignment_id="x0", extended_mode=False))
    plain._applyCaseFlags(unflagged, plain.cache.open(unflagged))
    plain._loadOrCreateSegmentation({})
    check("  an unflagged case still opens with the four",
          not plain.extendedOn() and not plain.hasExtendedSegments())
    path = os.path.join(tmp, "four.seg.nrrd")
    plain.exportSubmission(path)
    check("  and a four-class read writes no complete-groups key",
          labelfile.COMPLETE_KEY not in labelfile.read_header(path))
    slicer.mrmlScene.RemoveNode(plain.segmentationNode)

    # 2. Ticks start off and are saved with the draft.
    check("the branch groups start unticked", logic.completeGroups == set())
    logic.setCompleteGroup(labels.GROUP_RCA, True)
    logic.setCompleteGroup(labels.GROUP_LAD, True)
    logic.setCompleteGroup(labels.GROUP_LAD, False)
    logic.setCompleteGroup(labels.GROUP_LCX, True)
    ticked = [labels.GROUP_LCX, labels.GROUP_RCA]
    check("  ticked ones are saved with the case",
          logic.cache.manifest("x1").get("completeGroups") == ticked,
          logic.cache.manifest("x1"))
    again = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache"))
    again._applyCaseFlags(flagged, again.cache.manifest("x1"))
    check("  and come back when the case is reopened", again.completeGroups == set(ticked))

    # 3. The tick-boxes in the panel.
    try:
        widget = module.SegQueue14Widget()
        widget.setup()
        widget.logic = logic
        widget._updateExtendedBox()
        boxes = widget.completeChecks
        check("the panel has one complete tick-box per branch group",
              list(boxes) == list(labels.COMPLETE_GROUPS), list(boxes))
        check("  showing the open read's ticks",
              [boxes[g].checked for g in labels.COMPLETE_GROUPS] == [False, True, True])
        boxes[labels.GROUP_LAD].setChecked(True)
        boxes[labels.GROUP_LCX].setChecked(False)
        ticked = [labels.GROUP_LAD, labels.GROUP_RCA]
        check("  ticking one updates the read", logic.completeGroups == set(ticked),
              logic.completeGroups)
        check("  the extended-mode note shows on a flagged case, and the toggle is on",
              not widget.extendedModeLabel.isHidden() and widget.extendedCheck.checked)
        widget.logic = plain
        plain.caseExtendedMode = False
        widget._updateExtendedBox()
        check("  and not on an unflagged one", widget.extendedModeLabel.isHidden())
        widget.logic = logic
        try:
            widget.cleanup()
        except Exception:
            pass
    except Exception:
        check("the panel builds with the tick-boxes", False, traceback.format_exc())
        logic.setCompleteGroup(labels.GROUP_LAD, True)
        logic.setCompleteGroup(labels.GROUP_LCX, False)
        ticked = [labels.GROUP_LAD, labels.GROUP_RCA]

    # 4. A PDA moved out of the LCx (left-dominant), submitted with the ticks.
    node = logic.segmentationNode
    lo, hi = TUBES["LCx"]
    for name in labels.NAMES:
        keep = np.zeros(SHAPE, np.uint8)
        a, b = TUBES[name]
        keep[5:35, a:b, a:b] = 1
        slicer.util.updateSegmentBinaryLabelmapFromArray(keep, node, segIn(node, name), volume)
    lcx = slicer.util.arrayFromSegmentBinaryLabelmap(node, segIn(node, "LCx"), volume).copy()
    pda = np.zeros_like(lcx)
    pda[25:35, lo:hi, lo:hi] = lcx[25:35, lo:hi, lo:hi]
    lcx[25:35, lo:hi, lo:hi] = 0
    slicer.util.updateSegmentBinaryLabelmapFromArray(lcx, node, segIn(node, "LCx"), volume)
    slicer.util.updateSegmentBinaryLabelmapFromArray(pda, node, segIn(node, "PDA"), volume)
    review_ct = ct("ct-d47-review")
    logic.client = _RecordingClient()
    logic.submit()
    uploaded = logic.client.kept[0]
    stored = labelfile.read_class_stack(uploaded)
    check("submit writes the ticks in the class-stack header",
          stored["completeGroups"] == ticked, stored["completeGroups"])
    stats = {}
    four = labels.collapse_to_four(stored["masks"], stored["names"], stats=stats)
    check("  and the PDA off the LCx collapses into the LCx, not the RCA",
          int(four[labels.NAMES.index("LCx")].sum()) == TUBE_VOXELS
          and int(four[labels.NAMES.index("RCA")].sum()) == TUBE_VOXELS
          and stats["byParent"] == {"RCA": 0, "LCx": 1}, stats)
    check("  the case is closed and its flags cleared",
          logic.assignment is None and not logic.caseExtendedMode and not logic.completeGroups)

    # 5. A reviewer opens it (the ticks come from the row, else the header) and revises.
    review = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "review"))
    review.project = project
    review.volumeNode = review_ct
    review.segmentationNode = slicer.util.loadSegmentation(uploaded)
    review.applyProjectNames()
    review.setCompleteGroups(labelfile.complete_groups(labelfile.read_header(uploaded)))
    check("a reviewer sees the annotator's ticks", review.completeGroups == set(ticked))
    review.client = _RecordingClient()
    review.reviseSubmission("s47")
    revised = labelfile.read_class_stack(review.client.kept[0])
    check("  and a revision keeps them",
          revised["completeGroups"] == ticked and revised["names"] == labels.ALL_NAMES,
          revised["completeGroups"])
    slicer.mrmlScene.RemoveNode(review.segmentationNode)


def run_compare():
    """#335: the reviewer's "Compare reads" view, read-only, on synthetic reads."""
    import hashlib

    import numpy as np
    import vtk

    import slicer

    if not os.environ.get("SEGQUEUE_SELFTEST_INSTALLED"):
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
    import SegQueue14 as module

    from segqueue.protocol import ProjectConfig
    from segqueue14 import compare, labelfile, labels

    say("--- #335: compare reads")
    tmp = tempfile.mkdtemp()
    volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "ct-compare")
    slicer.util.updateVolumeFromArray(volume, np.full(SHAPE, -100, np.int16))
    volume.SetSpacing(0.5, 0.5, 0.6)
    volume.SetOrigin(10, -20, 30)
    volumePath = os.path.join(tmp, "ct.nrrd")
    slicer.util.saveNode(volume, volumePath)
    matrix = vtk.vtkMatrix4x4()
    volume.GetIJKToRASMatrix(matrix)
    ijkToLps = labelfile.ras_to_lps([[matrix.GetElement(r, c) for c in range(4)]
                                     for r in range(4)])
    slicer.mrmlScene.RemoveNode(volume)

    def tube(name, k0=5, k1=35):
        mask = np.zeros(SHAPE, np.uint8)
        lo, hi = TUBES[name]
        mask[k0:k1, lo:hi, lo:hi] = 1
        return mask

    empty = np.zeros(SHAPE, np.uint8)
    # A: the four tubes whole. B: no LM, LAD from k 10, RCA to k 20.
    readA = [tube("LM"), tube("LAD"), tube("LCx"), tube("RCA")]
    readB = [empty, tube("LAD", 10), tube("LCx"), tube("RCA", 5, 20)]
    # C, extended: A's tree with the LAD's end drawn as D1 and the LCx's as a PDA
    # leaving the LCx (left-dominant, D47 Q1). Collapsed, it is A exactly.
    readC = [empty] * len(labels.ALL_NAMES)
    readC[0], readC[1] = tube("LM"), tube("LAD", 5, 25)
    readC[2], readC[3] = tube("LCx", 5, 25), tube("RCA")
    readC[labels.ALL_NAMES.index("D1")] = tube("LAD", 25, 35)
    readC[labels.ALL_NAMES.index("PDA")] = tube("LCx", 25, 35)
    files = {}
    for key, masks, names in (("A", readA, labels.NAMES), ("B", readB, labels.NAMES),
                              ("C", readC, labels.ALL_NAMES)):
        files[key] = os.path.join(tmp, f"read{key}.seg.nrrd")
        labelfile.write_class_stack(files[key], masks, names, ijkToLps)

    def digest():
        out = {}
        for key, path in files.items():
            with open(path, "rb") as handle:
                out[key] = hashlib.sha256(handle.read()).hexdigest()
        return out

    before = digest()
    logic = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache"))
    logic.project = ProjectConfig(name="selftest", instructions=labels.INSTRUCTIONS,
                                  segments=labels.segment_specs())
    logic.client = _RecordingClient()
    reads = [{"key": key, "label": f"{key}: ann{n}", "path": files[key],
              "submissionId": "s" + key} for n, key in enumerate("ABC", start=1)]
    state = logic.loadComparison(volumePath, reads)

    # 1. Three reads load together, on the one CT.
    nodes = [state["reads"][k]["node"] for k in "ABC"]
    check("three synthetic reads of one case load together",
          all(slicer.mrmlScene.IsNodePresent(n) for n in nodes)
          and slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode").GetNumberOfItems() == 1,
          [n.GetName() for n in nodes])
    kept = {k: [int(m.sum()) for m in state["reads"][k]["masks"]][:4] for k in "ABC"}
    check("  each with its own classes whole",
          kept["A"] == [TUBE_VOXELS] * 4
          and kept["B"] == [0, 25 * 9, TUBE_VOXELS, 15 * 9]
          and kept["C"] == [TUBE_VOXELS, 20 * 9, 20 * 9, TUBE_VOXELS], kept)

    # 2. The agreement map of A and B against a hand-computed overlap, per class.
    check("  the first two are the agreement pair", state["pair"] == ("A", "B"))
    result = state["result"]
    hand = {"LM": (0, TUBE_VOXELS, 0), "LAD": (25 * 9, 5 * 9, 0),
            "LCx": (TUBE_VOXELS, 0, 0), "RCA": (15 * 9, 15 * 9, 0)}
    got = {n: tuple(result["per_class"][n][k] for k in ("both", "a_only", "b_only"))
           for n in labels.NAMES}
    check("the agreement map's both / A-only / B-only counts match by hand, per class",
          got == hand, got)
    ids = state["agreementIds"]
    drawn = {}
    for (name, category), segmentId in ids.items():
        drawn[(name, category)] = int(slicer.util.arrayFromSegmentBinaryLabelmap(
            state["agreementNode"], segmentId, logic.volumeNode).sum())
    expected = {(n, c): v for n in labels.NAMES
                for c, v in zip((compare.BOTH, compare.A_ONLY, compare.B_ONLY), hand[n]) if v}
    check("  and the map drawn on the CT grid holds exactly those voxels",
          drawn == expected, drawn)
    names = sorted(state["agreementNode"].GetSegmentation().GetNthSegment(i).GetName()
                   for i in range(state["agreementNode"].GetSegmentation().GetNumberOfSegments()))
    check("  named per class and category", "LAD: A only" in names and "LAD: both" in names,
          names)

    # 3. The Dice shown is the server's pair score on the same voxels.
    a = labelfile.read_class_stack(files["A"])
    b = labelfile.read_class_stack(files["B"])
    try:
        from segqueue14 import scoring

        server = scoring.score_reads(a["masks"], a["names"], b["masks"], b["names"],
                                     a["spacing"])
        serverDice = {n: server["per_structure"][n]["dice"] for n in labels.NAMES}
        how = "segqueue14.scoring.score_reads"
    except ImportError:
        # No scipy in this Slicer: segtrain.metrics.dice_score's formula, from the files.
        serverDice = {}
        for i, n in enumerate(labels.NAMES):
            x, y = a["masks"][i] != 0, b["masks"][i] != 0
            total = int(x.sum()) + int(y.sum())
            serverDice[n] = round(2.0 * int((x & y).sum()) / total, 4) if total else None
        how = "dice_score's formula (segtrain not importable here)"
    shown = {n: result["per_class"][n]["dice"] for n in labels.NAMES}
    check("the Dice shown matches the server's pair scoring", shown == serverDice,
          f"{shown} vs {serverDice} by {how}")

    # 4. The display: side by side, then the map, one class.
    logic.setReadVisible("B", False)
    logic.setReadOpacity("A", 0.4)
    displays = {k: state["reads"][k]["node"].GetDisplayNode() for k in "ABC"}
    check("side by side: a read can be hidden and its opacity set",
          not displays["B"].GetVisibility() and displays["A"].GetVisibility()
          and abs(displays["A"].GetOpacity() - 0.4) < 1e-6)
    colours = {k: tuple(round(c, 2) for c in state["reads"][k]["node"].GetSegmentation()
                        .GetNthSegment(0).GetColor()) for k in "ABC"}
    check("  each read in its own colour", len(set(colours.values())) == 3, colours)
    logic.setCompareMode("agreement")
    logic.setAgreementClass("LAD")
    mapDisplay = state["agreementNode"].GetDisplayNode()
    visible = sorted(name for (name, _c), sid in state["agreementIds"].items()
                     if mapDisplay.GetSegmentVisibility(sid))
    check("agreement map: the reads hide, the map shows, one class at a time",
          mapDisplay.GetVisibility() and not any(d.GetVisibility() for d in displays.values())
          and set(visible) == {"LAD"}, visible)

    # 5. An extended read against a four-class read compares after the collapse.
    ext = logic.setAgreementPair("C", "A")
    check("an extended read against a four-class read compares after the collapse",
          ext["mode"] == compare.MODE_FOUR and ext["names"] == labels.NAMES
          and all(ext["per_class"][n]["dice"] == 1.0 for n in labels.NAMES),
          {n: ext["per_class"][n]["dice"] for n in labels.NAMES})

    # 6. Three reads: pick any two.
    picked = logic.setAgreementPair("B", "C")
    names = [state["agreementNode"].GetSegmentation().GetNthSegment(i).GetName()
             for i in range(state["agreementNode"].GetSegmentation().GetNumberOfSegments())]
    check("three reads: any two can be picked for the map",
          state["pair"] == ("B", "C") and "B vs C" in state["agreementNode"].GetName()
          and "LAD: C only" in names
          and picked["per_class"]["LAD"]["a_only"] == 0
          and picked["per_class"]["LAD"]["b_only"] == 5 * 9, names)

    # 7. The panel drives the same logic.
    try:
        widget = module.SegQueue14Widget()
        widget.setup()
        widget.logic = logic
        widget._fillComparePanel(reads)
        check("the compare panel lists the reads and the classes",
              widget.compareACombo.count == 3 and widget.compareBCombo.count == 3
              and widget.compareClassCombo.count == 1 + len(labels.NAMES)
              and not widget.compareFrame.isHidden())
        widget.compareBCombo.setCurrentIndex(2)
        check("  picking a read re-pairs the map", state["pair"] == ("A", "C"), state["pair"])
        widget.compareModeCombo.setCurrentIndex(1)
        widget.compareClassCombo.setCurrentIndex(widget.compareClassCombo.findText("RCA"))
        check("  the mode and class pickers drive the view",
              state["mode"] == "agreement" and state["selected"] == "RCA",
              (state["mode"], state["selected"]))
        widget._compareReadWidgets[2].setChecked(False)   # B's show box
        check("  a read's show box hides it", state["reads"]["B"].get("visible") is False)
        check("  the summary names the pair", "A vs C" in widget.compareSummary.text)
        try:
            widget.cleanup()
        except Exception:
            pass
    except Exception:
        check("the compare panel builds", False, traceback.format_exc())

    # 8. Read-only.
    check("comparing writes nothing to any submission",
          digest() == before and logic.client.calls == []
          and logic.segmentationNode is None and logic.assignment is None,
          logic.client.calls)
    logic.closeComparison()
    check("  and closing it takes its reads and map out of the scene",
          not any(slicer.mrmlScene.IsNodePresent(n) for n in nodes)
          and logic.comparison is None)


def run_my_submissions():
    """Protocol 20: "My submissions", a folded line in the Case section. Hidden on an
    older server; opened, one row per submission with a single Revise, disabled with
    the server's reason; Revise opens the recalled case, and a refusal is the
    server's sentence. Saves a screenshot of the panel beside the report."""

    import slicer

    if not os.environ.get("SEGQUEUE_SELFTEST_INSTALLED"):
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
    import SegQueue14 as module

    from segqueue.protocol import ProjectConfig
    from segqueue14 import labels, protocol

    say("--- protocol 20: My submissions")
    reviewing = protocol.RECALL_MESSAGES[protocol.ERR_RECALL_REVIEWING]

    class Client:
        loggedIn = True

        def __init__(self):
            self.calls = []

        def mySubmissions(self, limit=0, offset=0):
            self.calls.append(("list", offset))
            rows = [protocol.MySubmission(
                assignment_id="a{}".format(i), case_id="c{}".format(i),
                case_name="imagecas_{:04d}".format(i), state="submitted",
                # 2026-11-10 19:32 UTC, an hour apart going back: 14:32 EST first.
                submitted_at=1794339120.0 - 3600 * (i - 1), can_recall=i != 2,
                reason="" if i != 2 else reviewing,
                reason_code="" if i != 2 else protocol.ERR_RECALL_REVIEWING)
                for i in range(1 + offset, 4 + offset)]
            return rows, 5

        def recall(self, assignmentId):
            self.calls.append(("recall", assignmentId))
            if assignmentId == "a3":
                raise module.SegQueueError(
                    protocol.RECALL_MESSAGES[protocol.ERR_RECALL_HOLDING],
                    protocol.ERR_RECALL_HOLDING)
            return _Assignment(assignment_id=assignmentId, case_name="imagecas_0001",
                               start_from_own=True, recalled=True)

    tmp = tempfile.mkdtemp()
    logic = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache"))
    logic.client = Client()
    shown, opened = [], []
    realError = slicer.util.errorDisplay
    try:
        widget = module.SegQueue14Widget()
        widget.setup()
        widget.logic = logic
        box = widget.mySubmissionsBox
        check("My submissions starts hidden and folded",
              box.isHidden() and box.collapsed)

        logic.project = ProjectConfig(segments=labels.segment_specs(), protocol_version=19)
        widget._updateMySubmissionsVisible()
        check("  stays hidden on a protocol-19 server, and asks it nothing",
              box.isHidden() and logic.client.calls == [], logic.client.calls)

        logic.project = ProjectConfig(segments=labels.segment_specs(), protocol_version=20)
        widget._updateMySubmissionsVisible()
        check("  shows, folded, on a protocol-20 server, and asks nothing until opened",
              not box.isHidden() and box.collapsed and logic.client.calls == [])

        box.collapsed = False
        table = widget.mySubmissionsTable
        check("  opening it loads the list", logic.client.calls == [("list", 0)]
              and table.rowCount == 3, (logic.client.calls, table.rowCount))
        buttons = [table.cellWidget(r, 2) for r in range(table.rowCount)]
        check("  each row: the case, the time in ET, one Revise",
              table.item(0, 0).text() == "imagecas_0001"
              and table.item(0, 1).text() == "2026-11-10 14:32 ET"
              and all(b.text == "Revise" for b in buttons),
              [table.item(0, c).text() for c in (0, 1)])
        check("  a row a reviewer holds is disabled, with the reason as its tooltip",
              buttons[0].enabled and not buttons[1].enabled
              # Qt may hand a widget's tooltip back as rich text: <p>...</p>.
              and reviewing in buttons[1].toolTip and table.item(1, 0).toolTip() == reviewing,
              {"enabled": [b.enabled for b in buttons],
               "own": [b.isEnabledTo(table) for b in buttons],
               "table": table.enabled, "box": box.enabled,
               "button tip": buttons[1].toolTip, "item tip": table.item(1, 0).toolTip()})
        check("  more are offered when there are more",
              not widget.mySubmissionsMoreButton.isHidden()
              and "3 of 5" in widget.mySubmissionsStatus.text)

        # A screenshot of the panel for the pull request.
        try:
            widget.parent.resize(420, 760)
            widget.parent.show()
            slicer.app.processEvents()
            shot = os.path.join(os.path.dirname(OUT), "my-submissions.png")
            widget.parent.grab().save(shot)
            say("screenshot", shot)
        except Exception:
            say("no screenshot:", traceback.format_exc().splitlines()[-1])

        slicer.util.errorDisplay = lambda text, *a, **k: shown.append(text)
        widget._openAssignment = lambda assignment: opened.append(assignment)
        buttons[2].click()
        check("  a refusal shows the server's sentence and opens nothing",
              shown == [protocol.RECALL_MESSAGES[protocol.ERR_RECALL_HOLDING]]
              and opened == [], shown)
        # The refusal reloaded the list, so the row's button is a new one.
        table.cellWidget(0, 2).click()
        check("  Revise opens the recalled case",
              [a.assignment_id for a in opened] == ["a1"]
              and ("recall", "a1") in logic.client.calls, logic.client.calls)

        # 0.22.1: while the recalled case is open the release button reads
        # "Discard changes and close", and its question says the read goes back.
        release = widget.releaseButton
        check("  with nothing open the button reads 'Give this case back'",
              release.text == "Give this case back", release.text)
        logic.assignment = opened[0]
        widget._updateEnabled()
        asked = []
        realConfirm = slicer.util.confirmYesNoDisplay
        slicer.util.confirmYesNoDisplay = lambda text, *a, **k: asked.append(text) or False
        try:
            release.click()
        finally:
            slicer.util.confirmYesNoDisplay = realConfirm
        check("  a recalled case reads 'Discard changes and close'",
              release.text == "Discard changes and close" and release.enabled
              and "goes back for review exactly" in release.toolTip,
              (release.text, release.toolTip))
        check("  and asks to discard the changes, keeping the case when refused",
              asked == ["Discard your changes to 'imagecas_0001'?\n\nYour submission "
                        "goes back for review exactly as you submitted it."]
              and logic.assignment is opened[0], asked)
        logic.assignment = _Assignment(assignment_id="a9", case_name="other",
                                       recalled=False)
        widget._updateEnabled()
        check("  an ordinary case reads 'Give this case back'",
              release.text == "Give this case back", release.text)
        logic.assignment = None
        widget._updateEnabled()
        check("  and so does nothing open, after a resubmit or close",
              release.text == "Give this case back", release.text)

        widget.mySubmissionsMoreButton.click()
        check("  Show more appends the next page", table.rowCount == 6
              and ("list", 3) in logic.client.calls, table.rowCount)

        logic.client = None
        widget._updateMySubmissionsVisible()
        check("  hidden again once logged out", box.isHidden())
        try:
            widget.cleanup()
        except Exception:
            pass
    except Exception:
        check("the My submissions panel builds", False, traceback.format_exc())
    finally:
        slicer.util.errorDisplay = realError


def run_defect_cases():
    """Protocol 21: search and defect cases in the reviewer's case list. Saves a
    screenshot of the panel beside the report."""
    import qt

    import slicer

    if not os.environ.get("SEGQUEUE_SELFTEST_INSTALLED"):
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
    import SegQueue14 as module

    from segqueue.protocol import ProjectConfig
    from segqueue14 import labels, protocol

    say("--- protocol 21: search and defect cases")

    def assignment(state, annotator, submitted=None):
        return {"assignmentId": "a-" + annotator + state, "state": state,
                "annotator": annotator, "attempt": 1, "submittedAt": submitted,
                "submissionCount": 1 if submitted else 0, "flagged": []}

    class Client:
        loggedIn = True

        def __init__(self):
            self.calls = []
            self.cases = [
                {"caseId": "c1", "caseName": "imagecas_0001", "defect": True,
                 "defectReason": "motion artefact", "defectBy": "revy",
                 "defectAt": "2026-11-10T19:32:00+00:00", "holders": 0,
                 "assignments": [assignment("submitted", "anna",
                                            "2026-11-10T18:00:00+00:00")]},
                {"caseId": "c2", "caseName": "imagecas_0002", "defect": False,
                 "holders": 1, "assignments": [assignment("downloaded", "bobby")]},
                {"caseId": "c3", "caseName": "imagecas_0010", "defect": False,
                 "holders": 0, "assignments": [assignment(
                     "approved", "cathy", "2026-11-11T18:00:00+00:00")]},
                {"caseId": "c4", "caseName": "annotator_benchmark_0855", "defect": False,
                 "benchmark": True, "holders": 0, "assignments": []},
            ]
            self.refuse = None

        def allCases(self, state=None, unassigned=False, **kwargs):
            self.calls.append(("list", state, unassigned))
            return [dict(c) for c in self.cases]

        def annotators(self):
            return []

        def caseSubmissions(self, caseId):
            return []

        def markDefect(self, caseId, reason=""):
            self.calls.append(("mark", caseId, reason))
            if self.refuse:
                raise module.SegQueueError(self.refuse, protocol.ERR_DEFECT_BENCHMARK)
            for c in self.cases:
                if c["caseId"] == caseId:
                    c.update(defect=True, defectReason=reason, defectBy="revy",
                             defectAt="2026-11-12T15:00:00+00:00")
            return {"caseId": caseId, "defect": True, "changed": True}

        def unmarkDefect(self, caseId):
            self.calls.append(("unmark", caseId))
            for c in self.cases:
                if c["caseId"] == caseId:
                    c.update(defect=False, defectReason="", defectBy="", defectAt=None)
            return {"caseId": caseId, "defect": False, "changed": True}

    tmp = tempfile.mkdtemp()
    logic = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "cache"))
    logic.client = Client()
    shown, asked = [], []
    realError, realConfirm = slicer.util.errorDisplay, slicer.util.confirmYesNoDisplay
    answers = []
    try:
        widget = module.SegQueue14Widget()
        widget.setup()
        widget.logic = logic
        widget.reviewBox.setVisible(True)
        widget.reviewBox.collapsed = False
        table = widget.reviewTable

        def rows():
            return [(table.item(r, 0).text(), table.item(r, 2).text())
                    for r in range(table.rowCount) if not table.isRowHidden(r)]

        def select(caseId):
            widget._selectCase(caseId)
            slicer.app.processEvents()

        # 0.25.8: the note box, Image only, Take & segment and the history
        # caption are gone; the open row is Open submission alone.
        check("the reviewer panel has no note box, Image only or Take & segment",
              not any(hasattr(widget, n) for n in
                      ("verdictComment", "openCaseButton", "takeCaseButton"))
              and not any(b.text in ("Image only", "Take && segment")
                          for b in widget.reviewBox.findChildren(qt.QPushButton))
              and not any(isinstance(w, qt.QLineEdit)
                          and w.placeholderText == "optional note for the case thread"
                          for w in widget.reviewBox.findChildren(qt.QLineEdit))
              and not any("Every submission against" in label.text
                          for label in widget.reviewBox.findChildren(qt.QLabel)))
        check("the search box sits above the list, empty, and shows on any server",
              not widget.reviewSearch.isHidden() and widget.reviewSearch.text == ""
              and widget.reviewSearch.placeholderText == "Search cases by name")

        logic.project = ProjectConfig(segments=labels.segment_specs(), protocol_version=20)
        widget.onRefreshReview()
        check("  on a protocol-20 server: no Defect only, no Mark defect",
              widget.defectOnlyCheck.isHidden() and widget.defectButton.isHidden())
        check("  the order is unchanged: newest submission first, none last",
              [n for n, _ in rows()] == ["imagecas_0010", "imagecas_0001",
                                         "imagecas_0002", "annotator_benchmark_0855"],
              rows())

        widget.reviewSearch.setText("CAS_001")
        check("  search: a case-insensitive substring of the name",
              [n for n, _ in rows()] == ["imagecas_0010"]
              and widget.reviewCountLabel.text == "1 of 4 cases",
              (rows(), widget.reviewCountLabel.text))
        widget.reviewSearch.setText("0")
        check("  the order holds while searching",
              [n for n, _ in rows()][:3] == ["imagecas_0010", "imagecas_0001",
                                             "imagecas_0002"], rows())
        widget.reviewSearch.setText("zzz")
        check("  no match says so", rows() == []
              and widget.reviewCountLabel.text == "No case matches.",
              widget.reviewCountLabel.text)
        widget.reviewSearch.setText("")
        check("  cleared, every case is back",
              len(rows()) == 4 and widget.reviewCountLabel.text == "4 cases",
              widget.reviewCountLabel.text)

        logic.project = ProjectConfig(segments=labels.segment_specs(), protocol_version=21)
        widget.onRefreshReview()
        check("  on a protocol-21 server: Defect only and Mark defect show",
              not widget.defectOnlyCheck.isHidden() and not widget.defectButton.isHidden())
        index = next(r for r in range(table.rowCount)
                     if table.item(r, 0).text() == "imagecas_0001")
        badge = table.item(index, 2)
        check("  a defect case wears a Defect badge: red, bold, with who, when and why",
              badge.text().startswith("Defect \u00b7 submitted")
              and badge.background().color().name() == module.DEFECT_BADGE_BACKGROUND
              and badge.font().bold()
              and "marked by revy on 2026-11-10 14:32 ET: motion artefact"
              in badge.toolTip(), (badge.text(), badge.toolTip()))
        plain = table.item(next(r for r in range(table.rowCount)
                                if table.item(r, 0).text() == "imagecas_0002"), 2)
        check("  and no other case does", not plain.text().startswith("Defect"),
              plain.text())

        widget.defectOnlyCheck.setChecked(True)
        check("  Defect only shows only the defect cases",
              [n for n, _ in rows()] == ["imagecas_0001"]
              and widget.reviewCountLabel.text == "1 of 4 cases", rows())
        widget.reviewSearch.setText("0002")
        check("  with the search too", rows() == [])
        widget.reviewSearch.setText("")
        widget.defectOnlyCheck.setChecked(False)

        select("c2")
        check("  a plain case's button reads Mark defect",
              widget.defectButton.text == "Mark defect\u2026"
              and widget.defectButton.enabled, widget.defectButton.text)
        case = next(c for c, _ in widget._reviewRows if c["caseId"] == "c2")
        dialog = widget._defectDialog(case)
        check("  the confirmation says how many hold it, and asks for an optional reason",
              "1 annotator holds it now. They keep it and can finish it."
              in dialog.labelText() and dialog.labelText().endswith("Reason (optional):")
              and dialog.okButtonText() == "Mark defect", dialog.labelText())
        dialog.reject()

        widget._askDefectReason = lambda c: (asked.append(c["caseId"]) or (False, ""))
        widget.defectButton.click()
        check("  cancelling marks nothing", asked == ["c2"]
              and not [c for c in logic.client.calls if c[0] == "mark"],
              logic.client.calls)

        widget._askDefectReason = lambda c: (True, "truncated scan")
        widget.defectButton.click()
        check("  confirming marks it, with the reason",
              ("mark", "c2", "truncated scan") in logic.client.calls, logic.client.calls)
        selected, _ = widget._selectedReviewRow()
        check("  the list reloads with the case still selected, now defect",
              selected is not None and selected["caseId"] == "c2" and selected["defect"]
              and widget.defectButton.text == "Unmark defect",
              (selected, widget.defectButton.text))

        # A screenshot of the panel for the pull request.
        try:
            widget.reviewSearch.setText("imagecas")
            widget.parent.show()
            box = widget.reviewBox
            box.setMinimumHeight(1100)
            box.resize(460, 1100)
            box.layout().activate()
            slicer.app.processEvents()
            slicer.app.processEvents()
            shot = os.path.join(os.path.dirname(OUT), "defect-cases.png")
            box.grab().save(shot)
            say("screenshot", shot)
            widget.reviewSearch.setText("")
        except Exception:
            say("no screenshot:", traceback.format_exc().splitlines()[-1])

        slicer.util.confirmYesNoDisplay = lambda text, *a, **k: (
            answers.append(text) or False)
        widget.defectButton.click()
        check("  unmarking asks, and No changes nothing",
              len(answers) == 1 and answers[0].startswith("Unmark 'imagecas_0002'")
              and not [c for c in logic.client.calls if c[0] == "unmark"], answers)
        slicer.util.confirmYesNoDisplay = lambda text, *a, **k: True
        widget.defectButton.click()
        selected, _ = widget._selectedReviewRow()
        check("  Yes unmarks it", ("unmark", "c2") in logic.client.calls
              and selected is not None and not selected["defect"]
              and widget.defectButton.text == "Mark defect\u2026", logic.client.calls)

        select("c4")
        check("  the benchmark's button is disabled, and says why",
              not widget.defectButton.enabled
              and "benchmark" in widget.defectButton.toolTip, widget.defectButton.toolTip)

        slicer.util.errorDisplay = lambda text, *a, **k: shown.append(text)
        logic.client.refuse = protocol.DEFECT_BENCHMARK_MESSAGE
        select("c3")
        widget.defectButton.click()
        check("  a refusal shows the server's sentence",
              shown == [protocol.DEFECT_BENCHMARK_MESSAGE], shown)

        widget.defectOnlyCheck.setChecked(True)
        logic.project = ProjectConfig(segments=labels.segment_specs(), protocol_version=20)
        widget.onRefreshReview()
        check("  hidden again on an older server, and Defect only is off",
              widget.defectOnlyCheck.isHidden() and widget.defectButton.isHidden()
              and not widget.defectOnlyCheck.checked and len(rows()) == 4)
        try:
            widget.cleanup()
        except Exception:
            pass
    except Exception:
        check("the search and defect controls build", False, traceback.format_exc())
    finally:
        slicer.util.errorDisplay = realError
        slicer.util.confirmYesNoDisplay = realConfirm


def run_overlap():
    """0.25.4 (D52, D39, D44): a material painted inside an artery keeps both classes.

    Through the module's own panel, in a real Red view and 3D-free effects: Paint,
    Draw, Scissors (fill inside), Threshold, Draw tube (when installed), Islands,
    Logical operators (copy, add) and Inverse cut each put "Calcified plaque"
    inside a trimmed LAD and leave every LAD voxel. The same as a reviewer editing
    an opened submission. Slicer's own Segment Editor module, which edits the same
    case and used to start at "Overwrite all", starts at "Allow overlap"; so does
    a node made after a scene clear. A deliberate choice in the Masking panel is
    kept until the next case. A painted plaque is exported as two overlapping
    channels.

    D52: the seeded case's materials start empty and its branches as the seed;
    the plaque painted inside the LAD is submitted as plaque; selecting a hidden
    class shows it (and nothing else), and the first stroke on it lands, with no
    "segment is hidden" question -- on the own case and as a reviewer.
    """
    import shutil

    import numpy as np
    import qt
    import vtk

    import slicer

    if not os.environ.get("SEGQUEUE_SELFTEST_INSTALLED"):
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
    import SegQueue14 as module
    from SegQueue14Lib import overlap

    from segqueue.protocol import ProjectConfig
    from segqueue14 import labelfile, labels

    say("--- 0.25.4: a material inside an artery keeps both (D52, D39, D44)")
    E = slicer.vtkMRMLSegmentEditorNode
    ALLOW = overlap.allow_overlap_mode(E)
    check("'Allow overlap' is OverwriteNone in this Slicer",
          ALLOW is not None and ALLOW == E.OverwriteNone, ALLOW)
    PLAQUE = "Calcified plaque"

    # A modal dialog would stop the run for good: answer it, and say what it was.
    dialogs = []

    def closeModals():
        dialog = slicer.app.activeModalWidget()
        if dialog is not None:
            text = repr(getattr(dialog, "text", ""))[:200]
            dialogs.append(text)
            say("  (answered a dialog:", dialog.windowTitle, text, ")")
            dialog.accept()

    modalTimer = qt.QTimer()
    modalTimer.setInterval(300)
    modalTimer.timeout.connect(closeModals)
    modalTimer.start()
    realError = slicer.util.errorDisplay
    slicer.util.errorDisplay = lambda *a, **k: say("  (error shown:", a[:1], ")")
    layoutManager, viewport = _ensureLayout(slicer, qt)
    tmp = tempfile.mkdtemp()
    try:
        widget = module.SegQueue14Widget()
        widget.setup()
        fresh = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        check("once the panel is built, a new Segment Editor node starts at Allow overlap",
              fresh.GetOverwriteMode() == ALLOW, fresh.GetOverwriteMode())
        slicer.mrmlScene.RemoveNode(fresh)

        # Slicer's own Segment Editor module, if it can be built here, left at
        # "Overwrite all" before the case opens, as an earlier session would.
        seEditor = None
        try:
            seEditor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
        except Exception:
            say("SKIP the Segment Editor module: not available here", traceback.format_exc()[-200:])
        if seEditor is not None:
            check("  the Segment Editor module's node starts at Allow overlap",
                  seEditor.mrmlSegmentEditorNode().GetOverwriteMode() == ALLOW,
                  seEditor.mrmlSegmentEditorNode().GetOverwriteMode())
            seEditor.mrmlSegmentEditorNode().SetOverwriteMode(E.OverwriteAllSegments)

        # An own seeded case through the panel's normal path, extended classes on.
        logic = widget.logic
        logic.project = ProjectConfig(name="selftest", instructions=labels.INSTRUCTIONS,
                                      segments=labels.segment_specs())
        logic.extendedClasses = True
        seed = np.zeros(SHAPE, np.uint8)
        for lo, hi in TUBES.values():
            seed[5:35, lo:hi, lo:hi] = 1

        def openCase(assignment, progress=None):
            fresh, volume = _seededCase(slicer, np, module, labels, tmp, "overlap", seed, True)
            for name in ("volumeNode", "segmentationNode", "seedSegmentId",
                         "seedFirstSelected", "lastAddedExtended", "_sessionStart",
                         "cache"):
                setattr(logic, name, getattr(fresh, name))
            logic.assignment = assignment
            slicer.util.setSliceViewerLayers(background=volume, fit=True)
            # As openCase does on a seeded case (D26): every class starts hidden.
            logic.setClassesVisible(False)

        logic.openCase = openCase
        widget._openAssignment(_Assignment(
            assignment_id="overlap", case_name="overlap", attempt=1, has_seed=True,
            has_prelabel=False, reviewer_comment="", deadline=None))
        editor, editorNode = widget.editorWidget, widget.editorNode
        check("an own case opens with the panel at Allow overlap",
              editorNode.GetOverwriteMode() == ALLOW and editorNode.GetMaskMode() == 0,
              (editorNode.GetOverwriteMode(), editorNode.GetMaskMode()))
        if seEditor is not None:
            check("  and the Segment Editor module's node too",
                  seEditor.mrmlSegmentEditorNode().GetOverwriteMode() == ALLOW,
                  seEditor.mrmlSegmentEditorNode().GetOverwriteMode())

        # D52: on a seeded case the 17 open with no seed voxels -- materials always,
        # branches until their first selection.
        segIn = module._segmentIdIn
        nSeed = int(seed.sum())
        got = _countsOf(slicer, logic.segmentationNode, logic.volumeNode,
                        labels.EXTRA_NAMES, segIn)
        check("D52: on a seeded case the materials start with 0 voxels",
              {n: got[n] for n in labels.MATERIALS} == {n: 0 for n in labels.MATERIALS}, got)
        check("  and so do the branches, before their first selection",
              got == {n: 0 for n in labels.EXTRA_NAMES}, got)
        # D52: binding shows the class the editor selected, and only that one.
        display = logic.segmentationNode.GetDisplayNode()
        selected = editorNode.GetSelectedSegmentID()
        shown = [n for n in labels.ALL_NAMES
                 if display.GetSegmentVisibility(logic.segmentIdFor(n))]
        if selected:
            check("D52: the class the editor selected on opening is shown, the others "
                  "stay hidden", shown == [n for n in labels.ALL_NAMES
                                           if logic.segmentIdFor(n) == selected],
                  (selected, shown))
        else:
            check("D52: with nothing selected on opening, every class stays hidden",
                  shown == [], shown)
        # D52: selecting a branch in the panel's editor, as a click in the segment
        # list does: it becomes the seed -- that class only -- and is shown.
        node = logic.segmentationNode
        editorNode.SetSelectedSegmentID(logic.segmentIdFor("OM1"))
        slicer.app.processEvents()
        got = _countsOf(slicer, node, logic.volumeNode, labels.EXTRA_NAMES, segIn)
        check("D52: selecting a branch in the panel fills exactly that class from the seed",
              got == {n: nSeed if n == "OM1" else 0 for n in labels.EXTRA_NAMES}, got)
        check("  and shows it",
              bool(display.GetSegmentVisibility(logic.segmentIdFor("OM1"))))
        for name in [n for n in labels.EXTRA_NAMES if n not in labels.MATERIALS]:
            editorNode.SetSelectedSegmentID(logic.segmentIdFor(name))
        editorNode.SetSelectedSegmentID(logic.segmentIdFor("LM"))
        slicer.app.processEvents()
        got = _countsOf(slicer, node, logic.volumeNode, labels.EXTRA_NAMES, segIn)
        check("  each branch selected once is the seed; the materials stay empty",
              got == {n: 0 if n in labels.MATERIALS else nSeed for n in labels.EXTRA_NAMES},
              got)
        _selectHiddenAndPaint(slicer, np, vtk, layoutManager, logic, editor, editorNode,
                              PLAQUE, dialogs, "own case")

        results = _materialInsideArtery(slicer, np, vtk, qt, layoutManager, widget,
                                        logic, editor, editorNode, PLAQUE, ALLOW, "own case")

        # The Segment Editor module on the same case: Threshold over the tree.
        if seEditor is not None:
            node, volume = logic.segmentationNode, logic.volumeNode
            _resetClasses(slicer, np, logic, PLAQUE)
            seEditor.setSegmentationNode(node)
            seEditor.setSourceVolumeNode(volume)
            seEditor.mrmlSegmentEditorNode().SetSelectedSegmentID(logic.segmentIdFor(PLAQUE))
            seEditor.setActiveEffectByName("Threshold")
            effect = seEditor.activeEffect()
            effect.setParameter("MinimumThreshold", "300")
            effect.setParameter("MaximumThreshold", "500")
            effect.self().onApply()
            seEditor.setActiveEffectByName("")
            lad, plaque = _voxels(slicer, logic, "LAD"), _voxels(slicer, logic, PLAQUE)
            check("  Threshold in Slicer's Segment Editor module keeps the LAD whole",
                  int(lad.sum()) == TUBE_VOXELS and (plaque & lad).sum() == TUBE_VOXELS,
                  (int(lad.sum()), int((plaque & lad).sum())))
            seEditor.setSegmentationNode(None)

        # A deliberate choice in the Masking panel is the annotator's until the next case.
        editorNode.SetOverwriteMode(E.OverwriteVisibleSegments)
        widget.onToggleExtended(False)
        widget.onToggleExtended(True)
        editor.setActiveEffectByName("Paint")
        editor.setActiveEffectByName("")
        check("a mode chosen in the Masking panel is kept (extended toggle, an effect)",
              editorNode.GetOverwriteMode() == E.OverwriteVisibleSegments,
              editorNode.GetOverwriteMode())
        widget._bindEditor(logic.segmentationNode, logic.volumeNode)
        check("  until the next case or submission is bound",
              editorNode.GetOverwriteMode() == ALLOW, editorNode.GetOverwriteMode())

        # Export: plaque painted inside the LAD is two overlapping channels.
        _resetClasses(slicer, np, logic, PLAQUE)
        _paintPlaque(slicer, np, vtk, layoutManager, logic, editor, editorNode, PLAQUE)
        path = os.path.join(tmp, "overlap.seg.nrrd")
        logic.exportSubmission(path)
        data = labelfile.read_class_stack(path)
        channels = dict(zip(data["names"], data["masks"]))
        lad, plaque = channels["LAD"] != 0, channels[PLAQUE] != 0
        check("the export has the LAD whole and the plaque inside it, overlapping",
              int(lad.sum()) == TUBE_VOXELS and plaque.any()
              and (plaque & lad).sum() == plaque.sum(),
              (int(lad.sum()), int(plaque.sum()), int((plaque & lad).sum())))
        volumePath = os.path.join(tmp, "overlap-ct.nrrd")
        slicer.util.saveNode(logic.volumeNode, volumePath)

        # D52: submitted as plaque -- it started empty, so it is no seed copy to
        # blank (D51 d) -- in its own channel, overlapping the LAD's.
        painted = int(plaque.sum())
        logic.client = _RecordingClient()
        logic.submit()
        sent = labelfile.read_class_stack(logic.client.kept[0]) if logic.client.kept else None
        sentChannels = dict(zip(sent["names"], sent["masks"])) if sent else {}
        sentLad = sentChannels.get("LAD", np.zeros(1)) != 0
        sentPlaque = sentChannels.get(PLAQUE, np.zeros(1)) != 0
        check("D52: plaque painted inside the LAD on a seeded case is submitted as "
              "plaque, overlapping the LAD",
              sent is not None and int(sentPlaque.sum()) == painted > 0
              and int((sentPlaque & sentLad).sum()) == painted
              and int(sentLad.sum()) == TUBE_VOXELS
              and PLAQUE not in logic.seedCopiesBlanked
              and logic.client.calls[-1][1].get(PLAQUE) == painted,
              (painted, logic.client.calls[-1:] if logic.client.calls else None,
               logic.seedCopiesBlanked))

        # A reviewer editing that submission: the scene is cleared and reloaded.
        logic.assignment = None

        class ReviewClient:
            loggedIn = False

            def downloadReviewFile(self, submissionId, kind, out):
                shutil.copy(volumePath if kind == "volume" else path, out)

        logic.client = ReviewClient()
        entry = {"submissionId": "s-overlap", "caseId": "c-overlap", "caseName": "overlap",
                 "volumeName": "overlap-ct.nrrd", "submissionName": "overlap.seg.nrrd",
                 "extended": True, "annotator": {"login": "selftest"}}
        widget._selectedSubmission = lambda: entry
        widget.onRefreshNotes = lambda *a, **k: None
        if seEditor is not None:
            seEditor.mrmlSegmentEditorNode().SetOverwriteMode(E.OverwriteAllSegments)
        widget.onOpenReview()
        editorNode = widget.editorNode
        check("a reviewer's submission opens with the panel at Allow overlap, after the clear",
              logic.segmentationNode is not None and editorNode.GetScene() is not None
              and editorNode.GetOverwriteMode() == ALLOW, editorNode.GetOverwriteMode())
        if seEditor is not None:
            node = slicer.mrmlScene.GetSingletonNode("SegmentEditor", "vtkMRMLSegmentEditorNode")
            check("  and the Segment Editor module's node too",
                  node is not None and node.GetOverwriteMode() == ALLOW,
                  None if node is None else node.GetOverwriteMode())
        _selectHiddenAndPaint(slicer, np, vtk, layoutManager, logic, widget.editorWidget,
                              editorNode, PLAQUE, dialogs, "reviewer")
        reviewed = _materialInsideArtery(slicer, np, vtk, qt, layoutManager, widget, logic,
                                         widget.editorWidget, editorNode, PLAQUE, ALLOW,
                                         "reviewer", effects=("Paint", "Threshold", "Logical copy"))
        results.update(reviewed)

        # After another scene clear, before anything is bound.
        slicer.mrmlScene.Clear(False)
        again = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        check("a Segment Editor node made after a scene clear starts at Allow overlap",
              again.GetOverwriteMode() == ALLOW, again.GetOverwriteMode())
        try:
            widget.cleanup()
        except Exception:
            pass
    except Exception:
        check("the overlap section runs", False, traceback.format_exc())
    finally:
        modalTimer.stop()
        slicer.util.errorDisplay = realError
        if viewport is not None:
            viewport.hide()


def _voxels(slicer, logic, name):
    return slicer.util.arrayFromSegmentBinaryLabelmap(
        logic.segmentationNode, logic.segmentIdFor(name), logic.volumeNode) > 0


def _resetClasses(slicer, np, logic, material):
    """Each vessel class cut to its own tube; the material empty and shown."""
    for name, (lo, hi) in TUBES.items():
        keep = np.zeros(SHAPE, np.uint8)
        keep[5:35, lo:hi, lo:hi] = 1
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            keep, logic.segmentationNode, logic.segmentIdFor(name), logic.volumeNode)
    slicer.util.updateSegmentBinaryLabelmapFromArray(
        np.zeros(SHAPE, np.uint8), logic.segmentationNode, logic.segmentIdFor(material),
        logic.volumeNode)
    # Shown, as an annotator shows it before painting (the editor asks otherwise).
    logic.segmentationNode.GetDisplayNode().SetSegmentVisibility(
        logic.segmentIdFor(material), True)


def _redView(slicer, np, vtk, layoutManager, volume):
    """The Red view on the LAD at slice 20, and ``onScreen(i, j)`` for it."""
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    slicer.app.processEvents()
    red = layoutManager.sliceWidget("Red")
    sliceNode = red.mrmlSliceNode()
    red.sliceLogic().FitSliceToAll()
    ijkToRas = vtk.vtkMatrix4x4()
    volume.GetIJKToRASMatrix(ijkToRas)
    rasOf = _matrixOf(np, ijkToRas)
    sliceNode.JumpSliceByCentering(*(rasOf @ [21, 21, 20, 1])[:3])
    slicer.app.processEvents()

    def onScreen(i, j):
        xy = np.linalg.inv(_matrixOf(np, sliceNode.GetXYToRAS())) @ (rasOf @ [i, j, 20, 1])
        return xy[0], xy[1]

    return red.sliceView().interactor(), onScreen, rasOf


def _paintPlaque(slicer, np, vtk, layoutManager, logic, editor, editorNode, material):
    interactor, onScreen, _ = _redView(slicer, np, vtk, layoutManager, logic.volumeNode)
    editorNode.SetSelectedSegmentID(logic.segmentIdFor(material))
    editor.setActiveEffectByName("Paint")
    effect = editor.activeEffect()
    effect.setCommonParameter("BrushDiameterIsRelative", 0)
    effect.setCommonParameter("BrushAbsoluteDiameter", 1.2)
    effect.setCommonParameter("BrushSphere", 0)
    centre = onScreen(21, 21)
    _drag(vtk, interactor, [centre, (centre[0] + 1, centre[1])])
    slicer.app.processEvents()
    editor.setActiveEffectByName("")


def _selectHiddenAndPaint(slicer, np, vtk, layoutManager, logic, editor, editorNode,
                          material, dialogs, who):
    """D52: selecting a hidden class shows it, and only it; the first stroke lands.

    As the annotator does it: another class is selected, the material is hidden
    and empty, then the material is clicked in the segment list (which sets the
    editor node's selection) and painted at once.
    """
    _resetClasses(slicer, np, logic, material)
    node = logic.segmentationNode
    display = node.GetDisplayNode()
    materialId = logic.segmentIdFor(material)
    editorNode.SetSelectedSegmentID(logic.segmentIdFor("LM"))
    slicer.app.processEvents()
    display.SetSegmentVisibility(materialId, False)
    others = {n: bool(display.GetSegmentVisibility(logic.segmentIdFor(n)))
              for n in [spec.name for spec in logic.classSpecs()] if n != material}
    del dialogs[:]
    editorNode.SetSelectedSegmentID(materialId)
    slicer.app.processEvents()
    check("D52 {}: selecting a hidden class shows it".format(who),
          bool(display.GetSegmentVisibility(materialId)))
    after = {n: bool(display.GetSegmentVisibility(logic.segmentIdFor(n))) for n in others}
    check("  and leaves every other class's visibility as it was", after == others,
          [n for n in others if after[n] != others[n]])
    _paintPlaque(slicer, np, vtk, layoutManager, logic, editor, editorNode, material)
    painted = int(_voxels(slicer, logic, material).sum())
    check("  and the first paint stroke on it lands, with no 'segment is hidden' question",
          painted > 0 and not dialogs, (painted, list(dialogs)))


_OVERLAP_EFFECTS = ("Paint", "Draw", "Scissors", "Threshold", "Draw tube", "Islands",
                    "Logical copy", "Logical add", "Inverse cut")


def _materialInsideArtery(slicer, np, vtk, qt, layoutManager, widget, logic, editor,
                          editorNode, material, allow, who, effects=_OVERLAP_EFFECTS):
    """Each effect puts ``material`` inside the trimmed LAD; the LAD keeps every voxel."""
    volume = logic.volumeNode
    interactor, onScreen, rasOf = _redView(slicer, np, vtk, layoutManager, volume)
    square = [onScreen(i, j) for i, j in
              [(19.6, 19.6), (22.4, 19.6), (22.4, 22.4), (19.6, 22.4)]]
    seed = np.zeros(SHAPE, np.uint8)
    for lo, hi in TUBES.values():
        seed[5:35, lo:hi, lo:hi] = 1
    node = logic.segmentationNode
    materialId = logic.segmentIdFor(material)

    def paint():
        _paintPlaque(slicer, np, vtk, layoutManager, logic, editor, editorNode, material)

    def draw():
        editor.setActiveEffectByName("Draw")
        _drag(vtk, interactor, square)
        interactor.SetKeySym("a")                 # Draw's "apply" key
        interactor.InvokeEvent(vtk.vtkCommand.KeyPressEvent)

    def scissors():
        editor.setActiveEffectByName("Scissors")
        editor.activeEffect().setParameter("Operation", "FillInside")
        editor.activeEffect().setParameter("Shape", "FreeForm")
        _drag(vtk, interactor, square)

    def threshold():
        editor.setActiveEffectByName("Threshold")
        editor.activeEffect().setParameter("MinimumThreshold", "300")
        editor.activeEffect().setParameter("MaximumThreshold", "500")
        editor.activeEffect().self().onApply()

    def drawTube():
        editor.setActiveEffectByName("Draw tube")
        tube = editor.activeEffect().self()
        if tube.segmentMarkupNode is None:
            tube.createNewMarkupNode()
        tube.logic.radius = 0.6
        for k in (8, 15, 22):
            tube.segmentMarkupNode.AddControlPoint(vtk.vtkVector3d(*(rasOf @ [21, 21, k, 1])[:3]))
        slicer.app.processEvents()
        tube.onApply()

    def islands():
        # A stroke left in two pieces inside the LAD: keep the larger.
        pieces = np.zeros(SHAPE, np.uint8)
        pieces[10:20, 20:23, 20:23] = 1
        pieces[25:27, 20:23, 20:23] = 1
        slicer.util.updateSegmentBinaryLabelmapFromArray(pieces, node, materialId, volume)
        editor.setActiveEffectByName("Islands")
        editor.activeEffect().setParameter("Operation", "KEEP_LARGEST_ISLAND")
        editor.activeEffect().setParameter("MinimumSize", "1")
        editor.activeEffect().self().onApply()

    def logical(operation):
        def apply():
            editor.setActiveEffectByName("Logical operators")
            editor.activeEffect().setParameter("Operation", operation)
            editor.activeEffect().setParameter("ModifierSegmentID", logic.segmentIdFor("LAD"))
            editor.activeEffect().self().onApply()
        return apply

    def inverseCut():
        # The material starts empty (D52): Inverse cut gives it the seed inside the
        # outline, which is the LAD there.
        editor.setActiveEffectByName("Inverse cut")
        _drag(vtk, interactor, square)

    run = {"Paint": paint, "Draw": draw, "Scissors": scissors, "Threshold": threshold,
           "Draw tube": drawTube, "Islands": islands, "Logical copy": logical("COPY"),
           "Logical add": logical("UNION"), "Inverse cut": inverseCut}
    results = {}
    for name in effects:
        effectName = {"Logical copy": "Logical operators", "Logical add": "Logical operators",
                      "Scissors": "Scissors"}.get(name, name)
        if editor.effectByName(effectName) is None:
            say("SKIP", who, name, "-- not in this Slicer's editor")
            continue
        try:
            _resetClasses(slicer, np, logic, material)
            editorNode.SetSelectedSegmentID(materialId)
            slicer.app.processEvents()
            run[name]()
            slicer.app.processEvents()
            lad, plaque = _voxels(slicer, logic, "LAD"), _voxels(slicer, logic, material)
            ok = int(lad.sum()) == TUBE_VOXELS and bool((plaque & lad).any())
            results[name] = ok
            check("{}: {} puts the plaque inside the LAD and keeps the LAD whole".format(
                who, name), ok, (int(lad.sum()), int(plaque.sum()), int((plaque & lad).sum()),
                                 editorNode.GetOverwriteMode()))
            check("  and leaves the panel at Allow overlap",
                  editorNode.GetOverwriteMode() == allow, editorNode.GetOverwriteMode())
        except Exception:
            results[name] = False
            check("{}: {} runs".format(who, name), False, traceback.format_exc())
        finally:
            editor.setActiveEffectByName("")
    return results


# --------------------------------------------------------------------- D53


def _paintAt(slicer, np, vtk, layoutManager, logic, editor, editorNode, name, i, j):
    """One Paint stroke into class ``name`` at voxel (i, j) of slice 20, in the Red view."""
    interactor, onScreen, _ = _redView(slicer, np, vtk, layoutManager, logic.volumeNode)
    editorNode.SetSelectedSegmentID(logic.segmentIdFor(name))
    slicer.app.processEvents()
    editor.setActiveEffectByName("Paint")
    effect = editor.activeEffect()
    effect.setCommonParameter("BrushDiameterIsRelative", 0)
    effect.setCommonParameter("BrushAbsoluteDiameter", 1.2)
    effect.setCommonParameter("BrushSphere", 0)
    centre = onScreen(i, j)
    _drag(vtk, interactor, [centre, (centre[0] + 1, centre[1])])
    slicer.app.processEvents()
    editor.setActiveEffectByName("")


def _inverseCutAround(slicer, np, vtk, layoutManager, logic, editor, editorNode, name):
    """Inverse cut on class ``name``: an outline around the LAD at slice 20."""
    interactor, onScreen, _ = _redView(slicer, np, vtk, layoutManager, logic.volumeNode)
    editorNode.SetSelectedSegmentID(logic.segmentIdFor(name))
    slicer.app.processEvents()
    editor.setActiveEffectByName("Inverse cut")
    _drag(vtk, interactor, [onScreen(i, j) for i, j in
                            [(19.6, 19.6), (22.4, 19.6), (22.4, 22.4), (19.6, 22.4)]])
    slicer.app.processEvents()
    editor.setActiveEffectByName("")


def _masksOf(slicer, np, node, volume, segmentIdIn, names):
    """``{name: 0/1 array on the CT grid}``, None for a class not in ``node``."""
    out = {}
    for name in names:
        segmentId = segmentIdIn(node, name)
        out[name] = None if not segmentId else (slicer.util.arrayFromSegmentBinaryLabelmap(
            node, segmentId, volume) > 0).astype(np.uint8)
    return out


def _sameMasks(np, a, b):
    """The names whose masks differ between ``a`` and ``b`` (presence included)."""
    return [n for n in a if (a[n] is None) != (b.get(n) is None)
            or (a[n] is not None and not np.array_equal(a[n], b[n]))]


def _tablesHiding(slicer, editor):
    """``[ids hidden]`` for each segment list in the editor widget that shows the
    case (an unbound one, with no segmentation, has nothing to filter)."""
    return [list(t.hideSegments()) for t in
            slicer.util.findChildren(editor, className="qMRMLSegmentsTableView")
            if t.segmentationNode() is not None]


def run_d53():
    """D53 (0.25.6): the extended-classes toggle only hides; the export decides 4 or 21."""
    import numpy as np
    import qt
    import vtk

    import slicer

    if not os.environ.get("SEGQUEUE_SELFTEST_INSTALLED"):
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))
    import SegQueue14 as module

    from segqueue.protocol import ProjectConfig
    from segqueue14 import labelfile, labels

    say("--- D53: the extended-classes toggle only hides")
    segIn = module._segmentIdIn
    seed = np.zeros(SHAPE, np.uint8)
    for lo, hi in TUBES.values():
        seed[5:35, lo:hi, lo:hi] = 1
    nSeed = int(seed.sum())

    # Every dialog the toggle or submit could raise is recorded (and answered).
    dialogs = []

    def closeModals():
        dialog = slicer.app.activeModalWidget()
        if dialog is not None:
            dialogs.append(repr(getattr(dialog, "text", ""))[:200])
            dialog.accept()

    modalTimer = qt.QTimer()
    modalTimer.setInterval(300)
    modalTimer.timeout.connect(closeModals)
    modalTimer.start()
    patched = {}
    for name in ("infoDisplay", "warningDisplay", "errorDisplay", "messageBox"):
        patched[name] = getattr(slicer.util, name)
        setattr(slicer.util, name,
                lambda *a, _n=name, **k: dialogs.append((_n, str(a[:1])[:200])))
    realConfirm = slicer.util.confirmYesNoDisplay
    layoutManager, viewport = _ensureLayout(slicer, qt)
    tmp = tempfile.mkdtemp()
    try:
        widget = module.SegQueue14Widget()
        widget.setup()
        logic = widget.logic
        logic.project = ProjectConfig(name="selftest", instructions=labels.INSTRUCTIONS,
                                      segments=labels.segment_specs())
        logic.extendedClasses = True

        def openCase(assignment, progress=None):
            fresh, volume = _seededCase(slicer, np, module, labels, tmp, "d53", seed, True)
            for name in ("volumeNode", "segmentationNode", "seedSegmentId",
                         "seedFirstSelected", "lastAddedExtended", "_sessionStart",
                         "cache"):
                setattr(logic, name, getattr(fresh, name))
            logic.assignment = assignment
            slicer.util.setSliceViewerLayers(background=volume, fit=True)
            logic.setClassesVisible(False)

        logic.openCase = openCase
        widget._openAssignment(_Assignment(
            assignment_id="d53", case_name="d53", attempt=1, has_seed=True,
            has_prelabel=False, reviewer_comment="", deadline=None))
        editor, editorNode = widget.editorWidget, widget.editorNode
        node, volume = logic.segmentationNode, logic.volumeNode
        display = node.GetDisplayNode()
        check("the panel opens a seeded case with the extended classes on",
              widget.extendedCheck.checked and all(
                  logic.segmentIdFor(n) for n in labels.EXTRA_NAMES))

        # The edits: D1 painted (outside the seed), D2 cut with Inverse cut, OM2
        # trimmed from its seed copy to the LCx, plaque painted inside the LAD, D3
        # selected and left an untouched seed copy.
        _paintAt(slicer, np, vtk, layoutManager, logic, editor, editorNode, "D1", 26, 26)
        _inverseCutAround(slicer, np, vtk, layoutManager, logic, editor, editorNode, "D2")
        editorNode.SetSelectedSegmentID(logic.segmentIdFor("OM2"))
        slicer.app.processEvents()
        om2 = slicer.util.arrayFromSegmentBinaryLabelmap(
            node, logic.segmentIdFor("OM2"), volume).copy()
        keep = np.zeros_like(om2)
        keep[5:35, 30:33, 30:33] = 1
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            om2 * keep, node, logic.segmentIdFor("OM2"), volume)
        _paintAt(slicer, np, vtk, layoutManager, logic, editor, editorNode,
                 "Calcified plaque", 21, 21)
        editorNode.SetSelectedSegmentID(logic.segmentIdFor("D3"))
        slicer.app.processEvents()
        before = _masksOf(slicer, np, node, volume, segIn, labels.ALL_NAMES)
        counts = {n: int(before[n].sum()) for n in ("D1", "D2", "OM2", "D3")}
        check("D1 painted, D2 cut with Inverse cut, OM2 trimmed, D3 an untouched copy",
              counts["D1"] > nSeed and 0 < counts["D2"] < nSeed
              and counts["OM2"] == TUBE_VOXELS and counts["D3"] == nSeed
              and before["Calcified plaque"].any(), counts)
        display.SetSegmentVisibility(logic.segmentIdFor("S1"), False)   # hidden by its eye
        eyes = {n: bool(display.GetSegmentVisibility(logic.segmentIdFor(n)))
                for n in labels.ALL_NAMES}
        ids = [logic.segmentIdFor(n) for n in labels.ALL_NAMES]
        editorNode.SetSelectedSegmentID(logic.segmentIdFor("D1"))
        slicer.app.processEvents()
        del dialogs[:]

        for cycle in range(1, 4):
            widget.extendedCheck.setChecked(False)
            slicer.app.processEvents()
            off = _masksOf(slicer, np, node, volume, segIn, labels.ALL_NAMES)
            check("toggle off #{}: every voxel unchanged, nothing removed".format(cycle),
                  not _sameMasks(np, before, off), _sameMasks(np, before, off))
            hiddenNow = [n for n in labels.EXTRA_NAMES
                         if display.GetSegmentVisibility(logic.segmentIdFor(n))]
            check("  the extended classes are hidden, the four as they were",
                  not hiddenNow and all(
                      bool(display.GetSegmentVisibility(logic.segmentIdFor(n))) == eyes[n]
                      for n in labels.NAMES), hiddenNow)
            extIds = set(logic.extendedSegmentIds())
            tables = _tablesHiding(slicer, editor)
            check("  their rows are hidden in the editor's list, and the group rows",
                  tables and all(set(t) == extIds for t in tables)
                  and not widget.extendedBox.isVisibleTo(widget.parent), tables)
            check("  and no extended class is left selected for editing",
                  editorNode.GetSelectedSegmentID() not in extIds,
                  editorNode.GetSelectedSegmentID())
            widget.extendedCheck.setChecked(True)
            slicer.app.processEvents()
            on = _masksOf(slicer, np, node, volume, segIn, labels.ALL_NAMES)
            check("toggle on #{}: every voxel unchanged, nothing added".format(cycle),
                  not _sameMasks(np, before, on)
                  and [logic.segmentIdFor(n) for n in labels.ALL_NAMES] == ids,
                  _sameMasks(np, before, on))
            now = {n: bool(display.GetSegmentVisibility(logic.segmentIdFor(n)))
                   for n in labels.ALL_NAMES}
            check("  every class shown or hidden as it was", now == eyes,
                  [n for n in now if now[n] != eyes[n]])
            check("  and the rows are back",
                  all(not t for t in _tablesHiding(slicer, editor))
                  and widget.extendedBox.isVisibleTo(widget.parent))
            # A branch selected again is never re-seeded or emptied (D52).
            for name in ("D1", "D2", "OM2", "D3"):
                editorNode.SetSelectedSegmentID(logic.segmentIdFor(name))
                slicer.app.processEvents()
            check("  selecting the branches again changes none of them",
                  not _sameMasks(np, before, _masksOf(slicer, np, node, volume, segIn,
                                                      labels.ALL_NAMES)))
        check("no dialog is raised by the toggle", not dialogs, dialogs)

        # A group hidden with its Show tick stays hidden, and its tick unticked.
        widget.groupChecks[labels.GROUP_LAD].setChecked(False)
        widget.extendedCheck.setChecked(False)
        widget.extendedCheck.setChecked(True)
        slicer.app.processEvents()
        check("a group hidden by its Show tick stays hidden over a toggle, tick unticked",
              not widget.groupChecks[labels.GROUP_LAD].checked
              and not display.GetSegmentVisibility(logic.segmentIdFor("D1")))
        widget.groupChecks[labels.GROUP_LAD].setChecked(True)

        # Export with the toggle off and work present: all 21, the work in them.
        widget.extendedCheck.setChecked(False)
        slicer.app.processEvents()
        path = os.path.join(tmp, "d53-off.seg.nrrd")
        logic.exportSubmission(path)
        stored = labelfile.read_class_stack(path)
        written = dict(zip(stored["names"], stored["masks"]))
        check("export with the toggle off and work present: 21 channels",
              stored["names"] == labels.ALL_NAMES, stored["names"])
        check("  with the work in them, voxel for voxel, D3 sent empty (D51 d)",
              all(np.array_equal(written[n] > 0, before[n] > 0)
                  for n in ("D1", "D2", "OM2", "Calcified plaque", "LAD"))
              and not written["D3"].any() and logic.seedCopiesBlanked == ["D3"],
              logic.seedCopiesBlanked)

        # A draft saved with the toggle off resumes with the work, and shows it.
        check("a draft saves with the toggle off", logic.autosave())
        draft = logic.cache.manifest("d53").get("workPath")
        resumed = module.SegQueue14Logic(cacheRoot=os.path.join(tmp, "d53-resume"))
        resumed.project = logic.project
        resumed.volumeNode = volume
        resumed.extendedClasses = False
        resumed.assignment = _Assignment(assignment_id="d53r")
        resumed._loadOrCreateSegmentation({"workPath": draft})
        resumed.seedSegmentId = resumed.segmentIdFor(SEED_NAME)
        back = _masksOf(slicer, np, resumed.segmentationNode, volume, segIn, labels.ALL_NAMES)
        check("  and resumes with every class, voxel for voxel",
              not _sameMasks(np, before, back), _sameMasks(np, before, back))
        check("  with the extended classes shown for it (they hold work)",
              resumed.showExtendedIfWorked() and resumed.extendedOn()
              and not resumed.extendedClasses)
        path = os.path.join(tmp, "d53-resumed.seg.nrrd")
        resumed.exportSubmission(path)
        check("  and exports all 21",
              labelfile.read_class_stack(path)["names"] == labels.ALL_NAMES)
        slicer.mrmlScene.RemoveNode(resumed.segmentationNode)

        # Submit through the panel with the toggle off: no dialog but the
        # confirmation, and all 21 uploaded with the work.
        logic.client = _RecordingClient()
        logic.client.loggedIn = True
        slicer.util.confirmYesNoDisplay = lambda *a, **k: True
        del dialogs[:]
        reviewCt = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "ct-d53")
        slicer.util.updateVolumeFromArray(reviewCt, np.where(seed > 0, 400, -100).astype(np.int16))
        reviewCt.SetSpacing(0.5, 0.5, 0.6)
        reviewCt.SetOrigin(10, -20, 30)
        widget.onSubmit()
        slicer.app.processEvents()
        check("no dialog is raised by submit", not dialogs, dialogs)
        uploaded = logic.client.kept[0] if logic.client.kept else None
        stored = labelfile.read_class_stack(uploaded) if uploaded else {"names": []}
        check("submit with the toggle off uploads all 21 with the work",
              stored["names"] == labels.ALL_NAMES and all(
                  np.array_equal(dict(zip(stored["names"], stored["masks"]))[n] > 0,
                                 before[n] > 0) for n in ("D1", "D2", "OM2")),
              stored["names"])

        # A reviewer's panel: the 21-class read opens whole, toggles the same way.
        if uploaded:
            widget._claimedSubmission = "s-d53"
            logic.assignment = None
            logic.volumeNode = reviewCt
            logic.segmentationNode = slicer.util.loadSegmentation(uploaded)
            logic.applyProjectNames()
            logic.extendedView.reset()
            logic.extendedClasses = False
            # As onOpenReview does (D53), and checked first without it: a loaded
            # read with no reference geometry still reads its classes' content.
            check("reviewer: an extended class reads as having content on a loaded read",
                  module._segmentHasContent(logic.segmentationNode, "D1"))
            logic.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(reviewCt)
            logic.showExtendedIfWorked()
            widget._bindEditor(logic.segmentationNode, reviewCt)
            widget._updateExtendedBox()
            widget._applyExtendedView()
            rnode = logic.segmentationNode
            review = _masksOf(slicer, np, rnode, reviewCt, segIn, labels.ALL_NAMES)
            check("reviewer: a read with extended work opens with them on, toggle off "
                  "for the login", widget.extendedCheck.checked and not logic.extendedClasses)
            for _ in range(3):
                widget.extendedCheck.setChecked(False)
                widget.extendedCheck.setChecked(True)
                slicer.app.processEvents()
            again = _masksOf(slicer, np, rnode, reviewCt, segIn, labels.ALL_NAMES)
            check("reviewer: three toggles change no voxel and raise no dialog",
                  not _sameMasks(np, review, again) and not dialogs,
                  (_sameMasks(np, review, again), dialogs))
            widget.extendedCheck.setChecked(False)
            logic.client = _RecordingClient()
            logic.reviseSubmission("s-d53")
            revised = labelfile.read_class_stack(logic.client.kept[0])
            check("reviewer: a revision with the toggle off sends all 21 with the work",
                  revised["names"] == labels.ALL_NAMES and all(
                      np.array_equal(dict(zip(revised["names"], revised["masks"]))[n] > 0,
                                     review[n] > 0) for n in ("D1", "D2", "OM2")))
            widget._endReview()
            slicer.mrmlScene.RemoveNode(rnode)

        # Only empty classes and untouched seed copies: the four, toggle on or off.
        for on in (True, False):
            fresh, freshCt = _seededCase(slicer, np, module, labels, tmp,
                                         "d53-none-{}".format(on), seed, True)
            for name in ("D1", "OM2", "PDA"):
                fresh.seedOnFirstSelection(fresh.segmentIdFor(name))
            fresh.extendedClasses = on
            fresh.setExtendedShown(on)
            path = os.path.join(tmp, "d53-none-{}.seg.nrrd".format(on))
            fresh.exportSubmission(path)
            check("only empty classes and untouched copies (toggle {}): 4 channels".format(
                "on" if on else "off"),
                labelfile.read_class_stack(path)["names"] == labels.NAMES
                and fresh.seedCopiesBlanked == [])
            slicer.mrmlScene.RemoveNode(fresh.segmentationNode)

        # D53 as amended (D47 stands): a Complete tick with no voxels, and a case
        # flagged for extended mode with nothing drawn, are sent as 21.
        for on in (True, False):
            fresh, freshCt = _seededCase(slicer, np, module, labels, tmp,
                                         "d53-tick-{}".format(on), seed, True)
            for name in ("D1", "OM2"):
                fresh.seedOnFirstSelection(fresh.segmentIdFor(name))
            fresh.setCompleteGroup(labels.COMPLETE_GROUPS[0], True)
            fresh.extendedClasses = on
            fresh.setExtendedShown(on)
            path = os.path.join(tmp, "d53-tick-{}.seg.nrrd".format(on))
            fresh.exportSubmission(path)
            stored = labelfile.read_class_stack(path)
            ticks = labelfile.complete_groups(labelfile.read_header(path))
            check("a Complete tick with no voxels (toggle {}): 21 channels and the "
                  "tick".format("on" if on else "off"),
                  stored["names"] == labels.ALL_NAMES
                  and ticks == [labels.COMPLETE_GROUPS[0]]
                  and not any(m.any() for n, m in zip(stored["names"], stored["masks"])
                              if n in labels.EXTRA_NAMES), (stored["names"], ticks))
            slicer.mrmlScene.RemoveNode(fresh.segmentationNode)
        for on in (True, False):
            fresh, freshCt = _seededCase(slicer, np, module, labels, tmp,
                                         "d53-flag-{}".format(on), seed, on)
            fresh.caseExtendedMode = fresh.caseFlaggedExtended = True
            if not on:                      # the annotator turned the box off
                fresh.caseExtendedMode = False
                fresh.setExtendedShown(False)
            path = os.path.join(tmp, "d53-flag-{}.seg.nrrd".format(on))
            fresh.exportSubmission(path)
            stored = labelfile.read_class_stack(path)
            check("a flagged case with nothing drawn ({}): 21 channels".format(
                "box on" if on else "box turned off, 17 never added"),
                stored["names"] == labels.ALL_NAMES, stored["names"])
            slicer.mrmlScene.RemoveNode(fresh.segmentationNode)
    finally:
        modalTimer.stop()
        for name, function in patched.items():
            setattr(slicer.util, name, function)
        slicer.util.confirmYesNoDisplay = realConfirm


#: ``SEGQUEUE_SELFTEST_ONLY=run_d51,...`` runs only those parts (for a quick local run).
_ONLY = [name for name in os.environ.get("SEGQUEUE_SELFTEST_ONLY", "").split(",") if name]
for part in (run, run_extended, run_d47, run_d51, run_compare, run_my_submissions,
             run_defect_cases, run_overlap, run_d53):
    if _ONLY and part.__name__ not in _ONLY:
        continue
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
