"""SegQueue -- fetch one case, segment it, send it back, and keep nothing.

This is the annotator's entire experience of the platform. There is no file
browser, no server URL to remember beyond the first login, no "where do I put
the output" and no naming convention to get wrong. Press *Get next case*, the
volume arrives with the project's segments already created and named, the
Segment Editor opens on it, and *Validate & submit* uploads the result and
deletes the local copy.

Three decisions shape the whole module:

* **The server owns the protocol.** Segment names, label values and colours come
  from ``/segqueue/project`` at login, not from anything shipped in this file.
  Adding a structure mid-project is a server-side setting change; nobody
  reinstalls anything.
* **Local data is a lease, not a library.** Every byte lives under one managed
  cache directory holding one case, purged the moment that case is submitted or
  released. See ``SegQueueLib/cache.py``.
* **Nothing here is trusted.** Validation runs client-side so the annotator gets
  an instant, specific complaint instead of a rejection three days later -- and
  the identical checks run again on the server, because a client can be old or
  patched.

Runs against Slicer's bundled Python 3.9 with no pip installs. It imports
``segqueue`` from the sibling ``src/`` directory, which is stdlib-only by design,
and talks to the server with ``requests``, which Slicer already ships. (The
obvious ``girder-client`` needs Python 3.10; see ``SegQueueLib/client.py``.)
"""

import os
import sys
import time
import traceback

import ctk
import qt
import slicer
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleWidget,
)

# Make the repository's own `segqueue` package importable without installing
# anything into Slicer's Python. Two layouts have to work, because the module
# ships both ways:
#
#   checkout   <repo>/slicer/SegQueue/SegQueue.py  with  <repo>/src/segqueue
#   packaged   .../qt-scripted-modules/SegQueue.py with  .../qt-scripted-modules/segqueue
#
# The packaged case needs no help -- Slicer puts a scripted module's own
# directory on sys.path, which is the same mechanism that finds SegQueueLib --
# so this only has to add the checkout's src/. Both are recorded for the error
# message, since "it could not find its own code" is otherwise a bad five
# minutes for whoever installed it.
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_MODULE_DIR))
_SRC = os.path.join(_REPO_ROOT, "src")
_SEARCHED = (os.path.join(_MODULE_DIR, "segqueue"), _SRC)
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

try:
    from segqueue import protocol
    from segqueue import states as st
    from segqueue.checksum import sha256_file, verify_file
    from segqueue.dataset import sniff_suffix, suffix_for
    from segqueue.protocol import SubmissionMeta
    from segqueue.segcheck import ERROR, Geometry, blocking, check_submission, summarise
    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - surfaced in the UI instead
    st = None
    protocol = None
    _IMPORT_ERROR = str(exc)

from SegQueueLib import CacheError, CaseCache, SegQueueClient, SegQueueError, defaultRoot

__version__ = "0.1.0"

#: How often the in-progress segmentation is written to disk. Two minutes is
#: chosen against the cost of losing work rather than the cost of the write: a
#: 400-slice segmentation saves in well under a second, and no annotator should
#: have to redo more than two minutes of tracing after a crash.
AUTOSAVE_SECONDS = 120

#: How often the client tells the server it is still alive. The server's lease is
#: measured in days, so this only needs to be frequent enough to distinguish
#: "working slowly" from "closed the laptop and went home in October".
HEARTBEAT_SECONDS = 300

#: Window/level for contrast-enhanced coronary CT. Auto window/level on a
#: whole-chest CT lands somewhere useless for 3 mm vessels -- wide enough that
#: lumen and myocardium look alike. These are the numbers a cardiac reader would
#: dial in, applied automatically so nobody has to.
CTA_WINDOW = 800
CTA_LEVEL = 300

#: Sphere brush diameter in millimetres. A left main is 4-5 mm and a distal LAD
#: under 2, so a 3 mm brush covers most of the tree in one pass without spilling
#: into myocardium. The annotator can still change it in the effect's own panel.
BRUSH_DIAMETER_MM = 3.0

#: Editable intensity window, in HU. Opacified lumen sits well above 150 and
#: below dense calcium; restricting paint to this range means a slightly sloppy
#: brush stroke still produces a clean lumen edge.
LUMEN_HU_MIN = 150
LUMEN_HU_MAX = 1000

#: Effects offered as one-click buttons, with their keyboard shortcut. Chosen
#: for *this* task rather than exposing all twenty: level tracing and scissors
#: are how a vessel actually gets segmented quickly, and islands is how a stray
#: blob gets removed.
VESSEL_EFFECTS = (
    ('Paint', 'Q', 'Paint the lumen. Sphere brush, sized for a coronary.'),
    ('Erase', 'W', 'Erase from the active segment only.'),
    ('Level tracing', 'E', 'Click inside the lumen to trace its boundary on this slice.'),
    ('Scissors', 'R', 'Cut away everything outside (or inside) a drawn outline.'),
    ('Islands', 'T', 'Keep the largest island, or remove a stray blob.'),
    ('Smoothing', 'Y', 'Even out a jagged vessel wall.'),
)

#: Settings keys. Stored in Slicer's own QSettings so a returning annotator does
#: not retype the server URL. The token is deliberately *not* stored -- see
#: SegQueueClient's docstring.
_SETTING_SERVER = "SegQueue/serverUrl"
_SETTING_USER = "SegQueue/lastUser"
_SETTING_CACHE = "SegQueue/cacheRoot"


class SegQueue(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SegQueue"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Christian Rogers"]
        self.parent.helpText = __doc__
        self.parent.acknowledgementText = (
            "Distributed CT segmentation for the Asclepius coronary dataset."
        )


# =============================================================================
#  Logic
# =============================================================================


class SegQueueLogic(ScriptedLoadableModuleLogic):
    """Everything the module does, with no Qt in sight.

    The split matters more here than in most Slicer modules: the interesting
    failure modes are a dropped upload, a checksum mismatch and a half-purged
    cache, and none of them should need a human clicking a button to reproduce.
    """

    def __init__(self, cacheRoot=None):
        ScriptedLoadableModuleLogic.__init__(self)
        self.client = None
        self.cache = CaseCache(cacheRoot or _storedCacheRoot())
        self.project = None
        self.assignment = None

        self.volumeNode = None
        self.segmentationNode = None
        self._sessionStart = None
        #: Segment ids of the two helper segments, when the case ships them.
        #: Held here rather than looked up by name each time, so that a rename by
        #: a curious annotator cannot silently turn scaffolding into anatomy.
        self.seedSegmentId = None
        self.regionSegmentId = None

    # ------------------------------------------------------------ session

    def connect(self, serverUrl, username, password):
        """Log in and fetch the project. Returns the Girder user document."""
        self.client = SegQueueClient(serverUrl, extensionVersion=__version__)
        user = self.client.login(username, password)
        self.project = self.client.project()
        self.cache.maxCases = max(1, int(self.project.max_concurrent))
        return user

    def disconnect(self):
        """Log out and leave nothing on disk.

        Purging at logout, not just at submit, is what makes a shared teaching
        laptop safe: the next person to sit down cannot open the previous
        student's case out of the cache.
        """
        self.closeCase(purge=True)
        if self.client is not None:
            self.client.logout()
        self.cache.purgeAll()

    @property
    def loggedIn(self):
        return self.client is not None and self.client.loggedIn

    def isReviewer(self):
        """Whether the server lets this user see the review queue.

        Asked by trying, rather than by reading roles out of the user document:
        the server is the only authority on it, and a client-side guess that
        disagrees produces a menu item that always errors.
        """
        if not self.loggedIn:
            return False
        try:
            self.client.reviewQueue(limit=1)
            return True
        except SegQueueError:
            return False

    # --------------------------------------------------------------- cases

    def outstanding(self):
        """Assignments the server still expects work on, newest first."""
        if not self.loggedIn:
            return []
        return [a for a in self.client.myAssignments() if st.is_open(a.state)]

    def requestNext(self):
        """Ask for a case. Returns an ``AssignmentInfo`` or None if none is free."""
        return self.client.nextCase()

    def openCase(self, assignment, progress=None):
        """Fetch, verify and load a case, then set the scene up to work on it.

        Resumes rather than re-downloads when the cached volume already matches
        the case checksum -- which is both the crash-recovery path and, for a
        rejected case coming back for rework, the difference between a click and
        another 400 MB.
        """
        self.closeCase(purge=False)
        self.cache.checkRoomFor(assignment.size_bytes)
        manifest = self.cache.open(assignment)
        self.assignment = assignment

        # Named from the server's own filename, because Slicer chooses its
        # reader from the extension. A gzipped NIfTI saved as `.nrrd` downloads
        # cleanly, verifies its checksum cleanly, and then fails to open with an
        # error that says nothing about the name.
        suffix = suffix_for(assignment.volume_name, default=".nrrd")
        volumePath = self.cache.volumePath(
            assignment.assignment_id, assignment.case_name, suffix)

        cached = manifest.get("volumePath")
        if cached and cached != volumePath and os.path.isfile(cached):
            # A copy left by an older build under the wrong name. The bytes are
            # right -- it is only the name Slicer objects to -- so rename rather
            # than make the annotator wait for the same 400 MB twice.
            try:
                os.replace(cached, volumePath)
            except OSError:
                pass

        if not self._cachedVolumeIsGood(volumePath, assignment):
            self.client.downloadCase(assignment.case_id, volumePath, progress=progress)
            # Verify before loading, not after. A truncated NRRD often loads
            # perfectly well and is simply missing its last slices, which is
            # exactly the kind of silent data loss requirement N3 forbids.
            verify_file(volumePath, assignment.checksum)

        # Last line of defence on the name. A server too old to send
        # `volumeName` leaves the suffix guessed, and a guessed suffix that
        # disagrees with the file's own magic number produces a load failure
        # whose message never mentions the filename. The checksum has already
        # proved the bytes; only the name can still be wrong.
        volumePath = self._correctSuffix(volumePath)
        self.cache.update(assignment.assignment_id, volumePath=volumePath)

        self.volumeNode = slicer.util.loadVolume(volumePath)
        self.volumeNode.SetName(assignment.case_name or "case")
        self._loadOrCreateSegmentation(manifest)
        self._loadHelpers(assignment)
        slicer.util.setSliceViewerLayers(background=self.volumeNode, fit=True)
        self.applyViewPreset()
        self._sessionStart = time.time()
        return manifest

    # ------------------------------------------------------- helper masks

    def _loadHelpers(self, assignment):
        """Bring the case's heart mask and coronary seed into the scene.

        Both come from the source dataset, both are scaffolding, and neither is
        ever submitted -- the export in ``exportLabelmap`` copies only the
        project's own segments, so a helper is *structurally* unable to reach
        the server rather than merely conventionally excluded.

        They live in the working segmentation node rather than one of their own
        because the Segment Editor can only mask against segments in the same
        segmentation, and masking to the seed is the largest time saving
        available here: painting inside an existing tree is minutes, drawing one
        is an hour.
        """
        self.seedSegmentId = self._helperId(protocol.SEED_SEGMENT_NAME)
        self.regionSegmentId = self._helperId(protocol.REGION_SEGMENT_NAME)

        if assignment.has_region and self.regionSegmentId is None:
            self.regionSegmentId = self._fetchHelper(
                assignment, protocol.ASSET_REGION,
                protocol.REGION_SEGMENT_NAME, (0.85, 0.55, 0.55), fill=0.08)
        if assignment.has_seed and self.seedSegmentId is None:
            self.seedSegmentId = self._fetchHelper(
                assignment, protocol.ASSET_SEED,
                protocol.SEED_SEGMENT_NAME, (0.95, 0.95, 0.35), fill=0.35)

    def _helperId(self, name):
        """Segment id for a helper already in the scene -- e.g. from a draft."""
        return self.segmentIdFor(name)

    def _fetchHelper(self, assignment, kind, name, color, fill):
        stem = os.path.join(self.cache.caseDir(assignment.assignment_id), kind)
        try:
            path = self._cachedHelper(stem)
            if path is None:
                # downloadAsset appends the server's own extension and hands
                # back the path it actually wrote.
                path = self.client.downloadAsset(assignment.case_id, kind, stem)
                if path is None:
                    return None
            return self._importHelper(path, name, color, fill)
        except Exception:
            # A missing or unreadable helper is a degraded experience, never a
            # blocked case: the annotator can still segment, just without the
            # head start. Failing the whole case load over scaffolding would be
            # the wrong trade every time.
            return None

    def _cachedHelper(self, stem):
        """An already-downloaded helper, whatever extension it arrived with."""
        directory, prefix = os.path.dirname(stem), os.path.basename(stem)
        try:
            names = os.listdir(directory)
        except OSError:
            return None
        for filename in sorted(names):
            if filename.startswith(prefix + "."):
                return os.path.join(directory, filename)
        return None

    def _importHelper(self, path, name, color, fill):
        """Load a binary mask and add it to the working segmentation, named."""
        segmentation = self.segmentationNode.GetSegmentation()
        before = {segmentation.GetNthSegmentID(i)
                  for i in range(segmentation.GetNumberOfSegments())}

        labelNode = None
        try:
            labelNode = slicer.util.loadLabelVolume(path)
            slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
                labelNode, self.segmentationNode)
        finally:
            if labelNode is not None:
                slicer.mrmlScene.RemoveNode(labelNode)

        after = [segmentation.GetNthSegmentID(i)
                 for i in range(segmentation.GetNumberOfSegments())]
        added = [s for s in after if s not in before]
        if not added:
            return None

        # A mask carrying more than one label value would arrive as several
        # segments. Keep the first and discard the rest rather than leaving
        # debris named Label_2 in the annotator's segment list.
        for extra in added[1:]:
            segmentation.RemoveSegment(extra)

        segmentId = added[0]
        segment = segmentation.GetSegment(segmentId)
        segment.SetName(name)
        segment.SetColor(*color)

        display = self.segmentationNode.GetDisplayNode()
        if display is not None:
            display.SetSegmentOpacity2DFill(segmentId, fill)
            display.SetSegmentOpacity2DOutline(segmentId, 0.6)
            display.SetSegmentOpacity3D(segmentId, 0.0)
        return segmentId

    def helperIds(self):
        return [s for s in (self.seedSegmentId, self.regionSegmentId) if s]

    # ------------------------------------------------------------- viewing

    def applyViewPreset(self):
        """Window/level for CTA, and centre the views on the heart.

        Slicer's automatic window/level on a whole-chest CT lands somewhere that
        makes a 3 mm opacified vessel look much like myocardium. Every annotator
        would otherwise dial the same numbers in on every case, and some would
        not bother.
        """
        if self.volumeNode is None:
            return
        display = self.volumeNode.GetDisplayNode()
        if display is not None:
            display.SetAutoWindowLevel(False)
            display.SetWindowLevel(CTA_WINDOW, CTA_LEVEL)
        self.jumpToHeart()

    def jumpToHeart(self):
        """Centre the slice views on the heart mask, when the case has one."""
        if self.segmentationNode is None or not self.regionSegmentId:
            return False
        try:
            centre = self.segmentationNode.GetSegmentCenterRAS(self.regionSegmentId)
        except Exception:
            return False
        if centre is None:
            return False
        slicer.modules.markups.logic().JumpSlicesToLocation(
            centre[0], centre[1], centre[2], True)
        return True

    def segmentIdFor(self, name):
        if self.segmentationNode is None:
            return None
        segmentation = self.segmentationNode.GetSegmentation()
        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            if segmentation.GetSegment(segmentId).GetName() == name:
                return segmentId
        return None

    def segmentHasContent(self, name):
        """Whether a segment has any voxels, cheaply.

        Reads the internal labelmap, which Slicer keeps cropped to the segment's
        own extent -- for a coronary branch that is a few hundred kilobytes, so
        this is affordable on a timer in a way re-exporting the whole volume
        would not be.
        """
        segmentId = self.segmentIdFor(name)
        if not segmentId:
            return False
        try:
            array = slicer.util.arrayFromSegmentBinaryLabelmap(
                self.segmentationNode, segmentId)
        except Exception:
            return False
        return array is not None and array.size > 0 and bool(array.any())

    def _correctSuffix(self, path):
        """Rename a volume to match what its bytes actually are.

        Returns the path to use. A no-op in the normal case, where the server
        told us the name; it earns its keep against a server too old to send
        one, where the alternative is Slicer refusing to open a file that
        downloaded and verified perfectly.
        """
        actual = sniff_suffix(path)
        if not actual or path.lower().endswith(actual):
            return path

        current = suffix_for(path, default="")
        corrected = (path[: -len(current)] if current else path) + actual
        try:
            os.replace(path, corrected)
        except OSError:
            return path
        return corrected

    def _cachedVolumeIsGood(self, path, assignment):
        if not path or not os.path.isfile(path):
            return False
        if assignment.size_bytes and os.path.getsize(path) != assignment.size_bytes:
            return False
        if not assignment.checksum:
            return True
        return sha256_file(path) == assignment.checksum

    def _loadOrCreateSegmentation(self, manifest):
        """Reopen the autosaved draft, or lay out a fresh set of template segments."""
        draft = manifest.get("workPath")
        if draft and os.path.isfile(draft):
            try:
                self.segmentationNode = slicer.util.loadSegmentation(draft)
            except Exception:
                # A corrupt autosave must not lock the annotator out of the case.
                # Losing the draft is bad; losing the case is worse.
                slicer.util.errorDisplay(
                    "The autosaved draft for this case could not be reopened, so "
                    "it has been discarded and the case reset to empty segments.\n\n"
                    + traceback.format_exc())
                self.segmentationNode = None
        if self.segmentationNode is None:
            self.segmentationNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLSegmentationNode", "Segmentation")

        self.segmentationNode.CreateDefaultDisplayNodes()
        self.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(
            self.volumeNode)
        self._applyTemplate()

    def _applyTemplate(self):
        """Make the scene's segments exactly the project's segments.

        This is the single most valuable thing the extension does for data
        quality. With thirty annotators, free-text segment names produce
        "LAD", "lad", "Left Anterior Descending" and "Segment_2" within a week,
        and no downstream conversion can safely guess which is which. Here the
        names, label values and colours are the server's, created before the
        annotator can type anything.
        """
        segmentation = self.segmentationNode.GetSegmentation()
        existing = {}
        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            existing[segmentation.GetSegment(segmentId).GetName()] = segmentId

        for spec in self.project.segments:
            segmentId = existing.get(spec.name)
            if segmentId is None:
                segmentId = segmentation.AddEmptySegment(spec.name, spec.name,
                                                         list(spec.color))
            segment = segmentation.GetSegment(segmentId)
            segment.SetColor(*spec.color)
            # Pin the exported label value to the protocol's, so the integers in
            # the submitted volume mean the same thing for every annotator and
            # match what `segtrain convert` expects. Older Slicer builds lack
            # this setter; there the export order below still produces the right
            # values, it is just not guaranteed by the file itself.
            try:
                segment.SetLabelValue(int(spec.label))
            except AttributeError:  # pragma: no cover - old Slicer
                pass

    def closeCase(self, purge=False):
        """Take the case out of the scene, banking any elapsed time first."""
        self.bankTime()
        for node in (self.segmentationNode, self.volumeNode):
            if node is not None:
                slicer.mrmlScene.RemoveNode(node)
        self.segmentationNode = None
        self.volumeNode = None
        if purge and self.assignment is not None:
            self.cache.purge(self.assignment.assignment_id)
        self.assignment = None
        self._sessionStart = None

    # ---------------------------------------------------------------- time

    def bankTime(self):
        """Move time spent this session into the manifest. Returns the total."""
        if self.assignment is None or self._sessionStart is None:
            return 0.0
        elapsed = max(0.0, time.time() - self._sessionStart)
        self._sessionStart = time.time()
        return self.cache.addElapsed(self.assignment.assignment_id, elapsed)

    def elapsedSeconds(self):
        if self.assignment is None:
            return 0.0
        banked = self.cache.elapsed(self.assignment.assignment_id)
        if self._sessionStart is not None:
            banked += max(0.0, time.time() - self._sessionStart)
        return banked

    # ------------------------------------------------------------ autosave

    def autosave(self):
        """Write the draft and bank the clock. Never raises: it runs on a timer.

        A failing autosave that threw would pop a modal dialogue over the Segment
        Editor every two minutes, which is a far more effective way to lose an
        annotator than losing their draft would be.
        """
        if self.segmentationNode is None or self.assignment is None:
            return False
        self.bankTime()
        path = self.cache.workPath(self.assignment.assignment_id)
        try:
            if not slicer.util.saveNode(self.segmentationNode, path):
                return False
        except Exception:
            return False
        self.cache.update(self.assignment.assignment_id, workPath=path)
        return True

    def heartbeat(self):
        if self.assignment is None or not self.loggedIn:
            return False
        return self.client.heartbeat(self.assignment.assignment_id)

    # ---------------------------------------------------------- validation

    def exportLabelmap(self, path):
        """Write the segmentation as a label volume on the source grid.

        Two deliberate departures from the obvious implementation.

        **Not a plain ``saveNode``.** Slicer stores a ``.seg.nrrd`` binary
        labelmap cropped to the segments' own bounding box, so the file's grid is
        *not* the source volume's -- it would fail the geometry check this module
        is about to run, and downstream code would have to re-register every
        submission against its CT. Exporting against the reference geometry gives
        a volume that overlays the source voxel for voxel, which is what both the
        QA scorer and the training conversion want.

        **Not the working node.** The scene also holds the heart mask and the
        coronary seed, which came from the source dataset and must never be
        submitted as if an annotator had drawn them. Rather than exporting
        everything and filtering afterwards -- where one renamed segment would
        leak an entire pre-existing tree into the training set, silently, and
        look like excellent work -- the protocol's segments are copied into a
        throwaway segmentation and that is what gets exported. Anything not in
        the project's list is structurally incapable of reaching the server.

        Returns ``(voxelCounts, sourceGeometry, segmentationGeometry)``.
        """
        exportNode = self._protocolOnlySegmentation()
        labelmapNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "SegQueueExport")
        try:
            ok = slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
                exportNode, labelmapNode,
                slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY)
            if not ok:
                raise RuntimeError(
                    "Slicer could not export the segments to a label volume.")

            # Nothing drawn yet: Slicer exports a labelmap of zero extent, and
            # every way of writing that to disk fails. Reporting the write
            # failure would be technically true and useless -- the annotator
            # would see "could not write the segmentation" at the exact moment
            # the honest answer is "you have not segmented anything yet". Hand
            # back empty counts instead and let the ordinary checks say which
            # vessels are missing, by name.
            image = labelmapNode.GetImageData()
            if image is None or 0 in tuple(image.GetDimensions()):
                empty = {spec.name: 0 for spec in self.project.segments}
                return empty, self.sourceGeometry(), None

            if not slicer.util.saveNode(labelmapNode, path):
                raise RuntimeError("Could not write the segmentation to " + path)
            counts = self._voxelCounts(labelmapNode)
            self._assertNoStrayLabels(labelmapNode)
            return counts, self.sourceGeometry(), _geometryOf(labelmapNode)
        finally:
            slicer.mrmlScene.RemoveNode(labelmapNode)
            slicer.mrmlScene.RemoveNode(exportNode)

    def _protocolOnlySegmentation(self):
        """A throwaway segmentation holding only the project's own segments."""
        exportNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLSegmentationNode", "SegQueueExportSource")
        exportNode.SetReferenceImageGeometryParameterFromVolumeNode(self.volumeNode)
        source = self.segmentationNode.GetSegmentation()
        target = exportNode.GetSegmentation()

        for spec in self.project.segments:
            segmentId = self.segmentIdFor(spec.name)
            if segmentId is None:
                continue
            target.CopySegmentFromSegmentation(source, segmentId, False)
            copied = target.GetSegment(target.GetSegmentIdBySegmentName(spec.name))
            if copied is not None:
                try:
                    copied.SetLabelValue(int(spec.label))
                except AttributeError:  # pragma: no cover - old Slicer
                    pass
        return exportNode

    def _assertNoStrayLabels(self, labelmapNode):
        """Refuse to submit a volume containing a label the protocol does not name.

        The copy above should make this impossible. It is checked anyway because
        the failure it guards against -- shipping the dataset's own coronary mask
        back as though a student had drawn it -- would corrupt the training set
        while every dashboard number looked healthy.
        """
        array = slicer.util.arrayFromVolume(labelmapNode)
        expected = {0} | {int(s.label) for s in self.project.segments}
        present = {int(v) for v in set(array.flatten().tolist())} if array.size else {0}
        stray = sorted(present - expected)
        if stray:
            raise RuntimeError(
                "The exported segmentation contains label value(s) "
                + ", ".join(str(v) for v in stray)
                + " that are not part of this project. Nothing has been "
                "submitted. Please report this.")

    def _voxelCounts(self, labelmapNode):
        """Voxels per segment, counted from the exported volume.

        Counted from the export rather than from the editor's segments on
        purpose: it measures what is actually about to be uploaded, so an export
        that silently dropped or merged a structure shows up as an empty segment
        here instead of as a mystery three weeks later.
        """
        array = slicer.util.arrayFromVolume(labelmapNode)
        counts = {}
        for spec in self.project.segments:
            counts[spec.name] = int((array == int(spec.label)).sum())
        return counts

    def sourceGeometry(self):
        return _geometryOf(self.volumeNode)

    def validate(self, voxelCounts, sourceGeometry, segGeometry):
        return check_submission(
            voxel_counts=voxelCounts,
            segments=self.project.segments,
            source_geometry=sourceGeometry,
            segmentation_geometry=segGeometry,
            annotation_seconds=self.elapsedSeconds() or None,
        )

    # -------------------------------------------------------------- submit

    def submit(self, note="", progress=None):
        """Export, validate, upload and hand over. Returns the server's response.

        Raises ``SegQueueError`` with the annotator-facing text on any refusal.
        On success the local copy is gone before this returns.
        """
        assignment = self.assignment
        if assignment is None:
            raise SegQueueError("There is no case open to submit.")

        self.bankTime()
        path = os.path.join(self.cache.caseDir(assignment.assignment_id),
                            "submission.seg.nrrd")
        counts, sourceGeom, segGeom = self.exportLabelmap(path)

        problems = self.validate(counts, sourceGeom, segGeom)
        if blocking(problems):
            raise SegQueueError(
                "This segmentation is not ready to submit:\n\n"
                + summarise(blocking(problems)))

        # Belt and braces for a project whose segments are all optional: the
        # checks above would pass on an empty scene, and the export writes no
        # file in that case. Uploading nothing must not look like a submission.
        if not os.path.isfile(path):
            raise SegQueueError(
                "There is nothing to submit -- none of the segments has any "
                "voxels in it.")

        meta = SubmissionMeta(
            checksum=sha256_file(path),
            size_bytes=os.path.getsize(path),
            annotation_seconds=self.elapsedSeconds(),
            voxel_counts=counts,
            slicer_version=slicer.app.applicationVersion,
            extension_version=__version__,
            annotator_note=note,
        )
        uploaded = self.client.uploadFile(
            path, self.project.upload_folder_id,
            name="{}_attempt{}.seg.nrrd".format(
                assignment.case_name or "case", assignment.attempt),
            progress=progress)

        response = self.client.submit(
            assignment.assignment_id, meta, uploaded["_id"],
            geometry={
                "source": sourceGeom.to_dict() if sourceGeom else None,
                "segmentation": segGeom.to_dict() if segGeom else None,
            })

        # Only now is the data safely on the server, so only now is it safe to
        # delete the local copy. Marking the manifest first means that if the
        # purge is interrupted, the leftovers are not offered back as resumable
        # work.
        self.cache.update(assignment.assignment_id, submitted=True)
        self.closeCase(purge=True)
        return response

    def release(self, reason=""):
        """Give a case back to the pool and purge it locally."""
        assignment = self.assignment
        if assignment is None:
            return None
        response = self.client.releaseCase(assignment.assignment_id, reason=reason)
        self.closeCase(purge=True)
        return response


def _geometryOf(node):
    """A ``segcheck.Geometry`` for a Slicer volume node, or None."""
    if node is None:
        return None
    image = node.GetImageData()
    if image is None:
        return None
    return Geometry(size=tuple(image.GetDimensions()),
                    spacing=tuple(node.GetSpacing()),
                    origin=tuple(node.GetOrigin()))


def _storedCacheRoot():
    return slicer.util.settingsValue(_SETTING_CACHE, defaultRoot())


# =============================================================================
#  Widget
# =============================================================================


class SegQueueWidget(ScriptedLoadableModuleWidget):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        self.logic = None
        self.editorWidget = None
        self.editorNode = None
        self.autosaveTimer = None
        self.heartbeatTimer = None
        self.clockTimer = None
        self.checklistTimer = None
        self._reviewRows = []
        self._claimedSubmission = None
        self._segmentButtons = {}
        self._shortcuts = []

    # ------------------------------------------------------------------ setup

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        if _IMPORT_ERROR:
            label = qt.QLabel(
                "Could not import the segqueue package:\n{}\n\nLooked in:\n"
                "  {}\n\nInstall the extension package, or load this module from "
                "inside a checkout of the Asclepius repository with src/ beside "
                "slicer/.".format(_IMPORT_ERROR, "\n  ".join(_SEARCHED)))
            label.setWordWrap(True)
            self.layout.addWidget(label)
            return

        self.logic = SegQueueLogic()

        self._buildLoginSection()
        self._buildCaseSection()
        self._buildVesselSection()
        self._buildEditorSection()
        self._buildSubmitSection()
        self._buildReviewSection()
        self.layout.addStretch(1)
        self._installShortcuts()

        self._startTimers()
        self._updateEnabled()

    def _buildLoginSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Server"
        self.layout.addWidget(box)
        form = qt.QFormLayout(box)
        self.loginBox = box

        self.serverEdit = qt.QLineEdit(
            slicer.util.settingsValue(_SETTING_SERVER, "https://segqueue.example.edu"))
        self.serverEdit.setToolTip(
            "Base URL of the SegQueue server. /api/v1 is added automatically.")
        form.addRow("Server:", self.serverEdit)

        self.userEdit = qt.QLineEdit(slicer.util.settingsValue(_SETTING_USER, ""))
        form.addRow("Username:", self.userEdit)

        self.passwordEdit = qt.QLineEdit()
        self.passwordEdit.setEchoMode(qt.QLineEdit.Password)
        self.passwordEdit.returnPressed.connect(self.onLogin)
        # Never persisted: on a shared machine, a remembered password means
        # every submission is attributed to whoever logged in last.
        self.passwordEdit.setToolTip("Not saved. You log in once per Slicer session.")
        form.addRow("Password:", self.passwordEdit)

        self.loginButton = qt.QPushButton("Log in")
        self.loginButton.clicked.connect(self.onLogin)
        self.logoutButton = qt.QPushButton("Log out and purge")
        self.logoutButton.setToolTip(
            "Logs out and deletes every locally cached case.")
        self.logoutButton.clicked.connect(self.onLogout)
        row = qt.QHBoxLayout()
        row.addWidget(self.loginButton)
        row.addWidget(self.logoutButton)
        form.addRow(row)

        self.statusLabel = qt.QLabel("Not logged in.")
        self.statusLabel.setWordWrap(True)
        form.addRow(self.statusLabel)

    def _buildCaseSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Case"
        self.layout.addWidget(box)
        layout = qt.QVBoxLayout(box)
        self.caseBox = box

        self.nextButton = qt.QPushButton("Get next case")
        self.nextButton.setToolTip(
            "Ask the server for your next assignment and download it.")
        self.nextButton.clicked.connect(self.onNextCase)
        layout.addWidget(self.nextButton)

        self.caseLabel = qt.QLabel("No case open.")
        self.caseLabel.setWordWrap(True)
        layout.addWidget(self.caseLabel)

        # Only shown for rework. The reviewer's comment is the single most
        # important thing on screen when it exists, so it gets its own framed,
        # coloured box rather than a line in a status label.
        self.reworkBox = qt.QGroupBox("Reviewer asked for changes")
        reworkLayout = qt.QVBoxLayout(self.reworkBox)
        self.reworkLabel = qt.QLabel()
        self.reworkLabel.setWordWrap(True)
        self.reworkLabel.setStyleSheet("QLabel { color: #8a3b00; }")
        reworkLayout.addWidget(self.reworkLabel)
        self.reworkBox.setVisible(False)
        layout.addWidget(self.reworkBox)

        self.instructionsBrowser = qt.QTextBrowser()
        self.instructionsBrowser.setMaximumHeight(160)
        self.instructionsBrowser.setOpenExternalLinks(True)
        layout.addWidget(self.instructionsBrowser)

        self.progressBar = qt.QProgressBar()
        self.progressBar.setVisible(False)
        layout.addWidget(self.progressBar)

        self.timerLabel = qt.QLabel("Time on this case: --")
        layout.addWidget(self.timerLabel)

    def _buildVesselSection(self):
        """The task-specific panel: which vessel, which tool, what help there is.

        The Segment Editor below can do everything in here already. It is worth
        the duplication because it cannot do it *for this task*: a first-year
        undergraduate should not have to learn which of twenty effects segments a
        3 mm vessel, nor scroll a segment list to change branch two hundred times
        an hour. Four labelled buttons and a number key each is the whole
        interface most of the time.
        """
        box = ctk.ctkCollapsibleButton()
        box.text = "Vessel tools"
        self.layout.addWidget(box)
        layout = qt.QVBoxLayout(box)
        self.vesselBox = box

        layout.addWidget(_caption("Which vessel are you labelling?  (keys 1-4)"))
        self.segmentButtonRow = qt.QGridLayout()
        layout.addLayout(self.segmentButtonRow)

        self.segmentHintLabel = qt.QLabel()
        self.segmentHintLabel.setWordWrap(True)
        self.segmentHintLabel.setStyleSheet("QLabel { color: #444; }")
        layout.addWidget(self.segmentHintLabel)

        layout.addWidget(_caption("Tools"))
        toolRow = qt.QGridLayout()
        for i, (name, key, tip) in enumerate(VESSEL_EFFECTS):
            button = qt.QPushButton("{}  ({})".format(name, key))
            button.setToolTip(tip)
            button.clicked.connect(lambda _checked=False, n=name: self.onEffect(n))
            toolRow.addWidget(button, i // 3, i % 3)
        layout.addLayout(toolRow)

        # -- the head start, when the case ships one
        self.seedGroup = qt.QGroupBox("This case comes with a coronary mask")
        seedLayout = qt.QVBoxLayout(self.seedGroup)
        seedLayout.addWidget(_caption(
            "The dataset already contains the coronary tree as one unlabelled "
            "mask. Your job is to split it into the four branches -- not to "
            "redraw it."))

        self.maskToSeedCheck = qt.QCheckBox("Only let me paint inside that mask")
        self.maskToSeedCheck.setToolTip(
            "Confines every effect to the existing tree, so a fast, sloppy "
            "brush stroke still produces a clean vessel edge.")
        self.maskToSeedCheck.setChecked(True)
        self.maskToSeedCheck.toggled.connect(self.onMaskingChanged)
        seedLayout.addWidget(self.maskToSeedCheck)

        self.copySeedButton = qt.QPushButton("Add the whole mask to this vessel")
        self.copySeedButton.setToolTip(
            "Copies the entire tree into the selected branch. Useful for the "
            "branch that dominates the tree -- then trim with Scissors.")
        self.copySeedButton.clicked.connect(self.onCopySeed)
        seedLayout.addWidget(self.copySeedButton)
        self.seedGroup.setVisible(False)
        layout.addWidget(self.seedGroup)

        # -- view helpers
        viewRow = qt.QHBoxLayout()
        self.jumpButton = qt.QPushButton("Centre on heart")
        self.jumpButton.setToolTip(
            "Jumps the slice views to the middle of the heart mask.")
        self.jumpButton.clicked.connect(self.onJumpToHeart)
        viewRow.addWidget(self.jumpButton)

        self.presetButton = qt.QPushButton("CTA window/level")
        self.presetButton.setToolTip(
            "Resets brightness and contrast to {}/{}, where opacified lumen is "
            "clearly separable from myocardium.".format(CTA_WINDOW, CTA_LEVEL))
        self.presetButton.clicked.connect(lambda: self.logic.applyViewPreset())
        viewRow.addWidget(self.presetButton)

        self.show3dButton = qt.QPushButton("Show in 3D")
        self.show3dButton.setToolTip(
            "Builds a surface of what you have drawn. The fastest way to spot a "
            "branch that stops early or a stray blob.")
        self.show3dButton.clicked.connect(self.onShow3d)
        viewRow.addWidget(self.show3dButton)
        layout.addLayout(viewRow)

        self.lumenMaskCheck = qt.QCheckBox(
            "Only paint over opacified lumen ({}-{} HU)".format(
                LUMEN_HU_MIN, LUMEN_HU_MAX))
        self.lumenMaskCheck.setToolTip(
            "Ignores voxels outside the contrast range, so the brush cannot "
            "spill into myocardium or fat.")
        self.lumenMaskCheck.setChecked(True)
        self.lumenMaskCheck.toggled.connect(self.onMaskingChanged)
        layout.addWidget(self.lumenMaskCheck)

    def _buildSegmentButtons(self):
        """One button per project segment, rebuilt whenever the project changes.

        Built from the server's segment list rather than hardcoded, so adding a
        fifth branch mid-project changes a server setting and nothing else.
        """
        for button in self._segmentButtons.values():
            button.setParent(None)
        self._segmentButtons = {}
        if self.logic is None or self.logic.project is None:
            return

        for i, spec in enumerate(self.logic.project.segments):
            label = "{}  {}".format(i + 1, _shortName(spec.name))
            button = qt.QPushButton(label)
            button.setCheckable(True)
            button.setToolTip(spec.hint or spec.name)
            colour = "rgb({},{},{})".format(*[int(255 * c) for c in spec.color])
            button.setStyleSheet(
                "QPushButton { text-align: left; padding: 4px 8px; "
                "border-left: 6px solid %s; }"
                "QPushButton:checked { font-weight: bold; background: #dfe8f0; }"
                % colour)
            button.clicked.connect(
                lambda _checked=False, n=spec.name: self.onSelectSegment(n))
            self.segmentButtonRow.addWidget(button, i // 2, i % 2)
            self._segmentButtons[spec.name] = button

    def _buildEditorSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Segment Editor"
        self.layout.addWidget(box)
        layout = qt.QVBoxLayout(box)
        self.editorBox = box

        # Slicer's own editor widget, embedded rather than reimplemented. Every
        # effect, keyboard shortcut and undo behaviour an annotator learns here
        # is the one they would learn in the Segment Editor module, which is also
        # what every tutorial and every YouTube video shows.
        self.editorWidget = slicer.qMRMLSegmentEditorWidget()
        self.editorWidget.setMRMLScene(slicer.mrmlScene)
        self.editorWidget.setSegmentationNodeSelectorVisible(False)
        try:
            self.editorWidget.setSourceVolumeNodeSelectorVisible(False)
        except AttributeError:  # pragma: no cover - Slicer < 5.2 naming
            self.editorWidget.setMasterVolumeNodeSelectorVisible(False)
        self.editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        self.editorWidget.setMRMLSegmentEditorNode(self.editorNode)
        layout.addWidget(self.editorWidget)

    def _buildSubmitSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Submit"
        self.layout.addWidget(box)
        layout = qt.QVBoxLayout(box)
        self.submitBox = box

        self.noteEdit = qt.QLineEdit()
        self.noteEdit.setPlaceholderText(
            "optional note for the reviewer, e.g. 'RCA barely opacified distally'")
        layout.addWidget(self.noteEdit)

        self.saveButton = qt.QPushButton("Save draft now")
        self.saveButton.setToolTip(
            "Drafts also save automatically every {} minutes.".format(
                AUTOSAVE_SECONDS // 60))
        self.saveButton.clicked.connect(self.onSaveDraft)
        layout.addWidget(self.saveButton)

        self.checkButton = qt.QPushButton("Check without submitting")
        self.checkButton.clicked.connect(self.onCheck)
        layout.addWidget(self.checkButton)

        self.submitButton = qt.QPushButton("Validate && submit")
        self.submitButton.setToolTip(
            "Uploads the segmentation and deletes the local copy.")
        self.submitButton.clicked.connect(self.onSubmit)
        layout.addWidget(self.submitButton)

        self.releaseButton = qt.QPushButton("Give this case back")
        self.releaseButton.setToolTip(
            "Returns the case to the pool for someone else. Your work on it is "
            "discarded.")
        self.releaseButton.clicked.connect(self.onRelease)
        layout.addWidget(self.releaseButton)

        self.problemsLabel = qt.QLabel()
        self.problemsLabel.setWordWrap(True)
        layout.addWidget(self.problemsLabel)

    def _buildReviewSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Review"
        box.collapsed = True
        # Hidden until the server confirms the role, so an annotator never sees
        # a section that would only ever tell them they are not allowed.
        box.setVisible(False)
        self.layout.addWidget(box)
        self.reviewBox = box
        layout = qt.QVBoxLayout(box)

        self.refreshReviewButton = qt.QPushButton("Refresh queue")
        self.refreshReviewButton.clicked.connect(self.onRefreshReview)
        layout.addWidget(self.refreshReviewButton)

        self.reviewTable = qt.QTableWidget()
        self.reviewTable.setColumnCount(5)
        self.reviewTable.setHorizontalHeaderLabels(
            ["Case", "Annotator", "Attempt", "Auto score", "Flags"])
        self.reviewTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.reviewTable.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.reviewTable.setMinimumHeight(160)
        layout.addWidget(self.reviewTable)

        self.openReviewButton = qt.QPushButton("Claim && open selected")
        self.openReviewButton.clicked.connect(self.onOpenReview)
        layout.addWidget(self.openReviewButton)

        self.verdictComment = qt.QLineEdit()
        self.verdictComment.setPlaceholderText(
            "comment (required when rejecting -- say what to fix)")
        layout.addWidget(self.verdictComment)

        row = qt.QHBoxLayout()
        self.approveButton = qt.QPushButton("Approve")
        self.approveButton.clicked.connect(lambda: self.onVerdict("approve"))
        self.rejectButton = qt.QPushButton("Reject && send back")
        self.rejectButton.clicked.connect(lambda: self.onVerdict("reject"))
        row.addWidget(self.approveButton)
        row.addWidget(self.rejectButton)
        layout.addLayout(row)

    def _startTimers(self):
        self.autosaveTimer = qt.QTimer()
        self.autosaveTimer.setInterval(AUTOSAVE_SECONDS * 1000)
        self.autosaveTimer.timeout.connect(self.onAutosave)
        self.autosaveTimer.start()

        self.heartbeatTimer = qt.QTimer()
        self.heartbeatTimer.setInterval(HEARTBEAT_SECONDS * 1000)
        self.heartbeatTimer.timeout.connect(self.onHeartbeat)
        self.heartbeatTimer.start()

        self.clockTimer = qt.QTimer()
        self.clockTimer.setInterval(1000)
        self.clockTimer.timeout.connect(self._updateClock)
        self.clockTimer.start()

        # The checklist reads each segment's internal labelmap, which is cropped
        # to the vessel's own extent and therefore small. Five seconds is often
        # enough to feel live and rare enough to cost nothing.
        self.checklistTimer = qt.QTimer()
        self.checklistTimer.setInterval(5000)
        self.checklistTimer.timeout.connect(self._updateChecklist)
        self.checklistTimer.start()

    def cleanup(self):
        """Slicer is closing or the module is being reloaded.

        The last autosave here is the one that saves an annotator who quits
        Slicer without submitting, which is a routine end to a session.
        """
        for timer in (self.autosaveTimer, self.heartbeatTimer, self.clockTimer,
                      self.checklistTimer):
            if timer is not None:
                timer.stop()
        for shortcut in self._shortcuts:
            shortcut.setParent(None)
        self._shortcuts = []
        if self.logic is not None:
            self.logic.autosave()
        if self.editorWidget is not None:
            self.editorWidget.setMRMLScene(None)
        if self.editorNode is not None:
            slicer.mrmlScene.RemoveNode(self.editorNode)
            self.editorNode = None

    def exit(self):
        # Leaving the module for another one should not lose work either.
        if self.logic is not None:
            self.logic.autosave()

    # ------------------------------------------------------------------ auth

    def onLogin(self):
        server = self.serverEdit.text.strip()
        username = self.userEdit.text.strip()
        if not server or not username:
            slicer.util.errorDisplay("Enter the server address and your username.")
            return
        with _busy():
            try:
                user = self.logic.connect(server, username, self.passwordEdit.text)
            except SegQueueError as exc:
                self.statusLabel.setText("Login failed.")
                slicer.util.errorDisplay(str(exc))
                return
            finally:
                self.passwordEdit.setText("")

        qt.QSettings().setValue(_SETTING_SERVER, server)
        qt.QSettings().setValue(_SETTING_USER, username)

        project = self.logic.project
        quota = ("" if project.quota_remaining is None
                 else "  |  {} case(s) left in your quota".format(project.quota_remaining))
        self.statusLabel.setText("Logged in as {}{}".format(
            user.get("login", username), quota))
        self.instructionsBrowser.setMarkdown(project.instructions or "")
        self.loginBox.collapsed = True

        self._buildSegmentButtons()
        self.reviewBox.setVisible(self.logic.isReviewer())
        self._updateEnabled()
        self._offerResume()

    def onLogout(self):
        if not slicer.util.confirmYesNoDisplay(
                "Log out and delete all locally cached cases?\n\nAny unsubmitted "
                "work will be lost, and open cases stay assigned to you on the "
                "server until they expire."):
            return
        with _busy():
            self.logic.disconnect()
        self.statusLabel.setText("Not logged in.")
        self.caseLabel.setText("No case open.")
        self.reworkBox.setVisible(False)
        self.reviewBox.setVisible(False)
        self._bindEditor(None, None)
        self._updateEnabled()

    # ------------------------------------------------------------------ case

    def _offerResume(self):
        """After login, pick up whatever the annotator already owes.

        Silently resuming would be wrong -- they may have logged in on a
        different machine -- but making them hunt for it would be worse, so the
        cases they still owe are named and offered.
        """
        try:
            outstanding = self.logic.outstanding()
        except SegQueueError as exc:
            slicer.util.errorDisplay(str(exc))
            return
        if not outstanding:
            return
        first = outstanding[0]
        extra = ""
        if first.state == st.REJECTED:
            extra = "\n\nIt was sent back for changes."
        if slicer.util.confirmYesNoDisplay(
                "You still have {} case(s) assigned. Open '{}' now?{}".format(
                    len(outstanding), first.case_name, extra)):
            self._openAssignment(first)

    def onNextCase(self):
        if self.logic.assignment is not None:
            slicer.util.errorDisplay(
                "Finish or give back the case you already have before asking for "
                "another one.")
            return
        with _busy():
            try:
                # An open assignment the server already knows about always wins
                # over a new one: leaving rework unfinished while collecting
                # fresh cases is exactly what the concurrency limit exists to
                # prevent, and the server would refuse anyway.
                outstanding = self.logic.outstanding()
                assignment = outstanding[0] if outstanding else self.logic.requestNext()
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
        if assignment is None:
            slicer.util.infoDisplay(
                "There are no cases available for you right now.\n\nThis usually "
                "means the pool is finished, or every remaining case has already "
                "been shown to you. Check with the study coordinator.")
            return
        self._openAssignment(assignment)

    def _openAssignment(self, assignment):
        self.progressBar.setVisible(True)
        self.progressBar.setValue(0)

        def progress(done, total):
            self.progressBar.setMaximum(max(1, total))
            self.progressBar.setValue(done)
            slicer.app.processEvents()

        with _busy():
            try:
                self.logic.openCase(assignment, progress=progress)
            except (SegQueueError, CacheError) as exc:
                slicer.util.errorDisplay(str(exc))
                return
            except Exception:
                slicer.util.errorDisplay(
                    "Could not open this case:\n\n" + traceback.format_exc())
                return
            finally:
                self.progressBar.setVisible(False)

        self.caseLabel.setText(
            "<b>{}</b> — attempt {}{}".format(
                assignment.case_name, assignment.attempt,
                _deadlineText(assignment.deadline)))
        self.reworkBox.setVisible(bool(assignment.reviewer_comment))
        self.reworkLabel.setText(assignment.reviewer_comment or "")
        self._bindEditor(self.logic.segmentationNode, self.logic.volumeNode)

        self.seedGroup.setVisible(bool(self.logic.seedSegmentId))
        self.jumpButton.setEnabled(bool(self.logic.regionSegmentId))
        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        self.onMaskingChanged()
        if self.logic.project.segments:
            self.onSelectSegment(self.logic.project.segments[0].name)
        self._updateChecklist()

        self.caseBox.collapsed = False
        self.vesselBox.collapsed = False
        self.editorBox.collapsed = True
        self._updateEnabled()

    def _bindEditor(self, segmentationNode, volumeNode):
        if self.editorWidget is None:
            return
        self.editorWidget.setSegmentationNode(segmentationNode)
        try:
            self.editorWidget.setSourceVolumeNode(volumeNode)
        except AttributeError:  # pragma: no cover - Slicer < 5.2 naming
            self.editorWidget.setMasterVolumeNode(volumeNode)

        if segmentationNode is not None and self.editorNode is not None:
            # Branches are disjoint anatomy, so painting one must never erase
            # another. The default overwrites, and an annotator who finds their
            # LAD half gone after working on the LCx has no way to know why.
            self.editorNode.SetOverwriteMode(
                slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

    # ----------------------------------------------------- vessel tooling

    def onSelectSegment(self, name):
        """Make one branch active, everywhere it matters."""
        if self.logic is None or self.logic.segmentationNode is None:
            return
        segmentId = self.logic.segmentIdFor(name)
        if segmentId and self.editorNode is not None:
            self.editorNode.SetSelectedSegmentID(segmentId)

        for otherName, button in self._segmentButtons.items():
            button.setChecked(otherName == name)

        spec = next((x for x in self.logic.project.segments if x.name == name), None)
        self.segmentHintLabel.setText(spec.hint if spec else "")

    def onEffect(self, name):
        """Activate an effect, pre-tuned for a coronary artery."""
        if self.editorWidget is None:
            return
        self.editorWidget.setActiveEffectByName(name)
        effect = self.editorWidget.activeEffect()
        if effect is None:
            slicer.util.errorDisplay(
                "This build of Slicer has no '{}' effect.".format(name))
            return
        if name == "Paint":
            # A brush sized in millimetres rather than screen pixels, so it stays
            # correct when the annotator zooms -- which they will, constantly.
            effect.setParameter("BrushSphere", "1")
            effect.setParameter("BrushDiameterIsRelative", "0")
            effect.setParameter("BrushAbsoluteDiameter", str(BRUSH_DIAMETER_MM))

    def onMaskingChanged(self):
        """Apply the two masks that make sloppy-but-fast painting safe."""
        if self.logic is None or self.editorNode is None:
            return
        if self.logic.segmentationNode is None:
            return

        seedId = self.logic.seedSegmentId
        if self.maskToSeedCheck.checked and seedId:
            # Segment id *before* mode, and not the other way round. Setting the
            # mode first makes the editor node validate against a mask segment
            # that is still empty, whereupon it silently falls back to
            # "everywhere" -- the checkbox looks applied and confines nothing,
            # which on this task is the difference between splitting a tree in
            # minutes and painting it by hand. Verified against Slicer 5.8.
            self.editorNode.SetMaskSegmentID(seedId)
            self.editorNode.SetMaskMode(
                slicer.vtkMRMLSegmentationNode.EditAllowedInsideSingleSegment)
        else:
            self.editorNode.SetMaskMode(
                slicer.vtkMRMLSegmentationNode.EditAllowedEverywhere)

        on = bool(self.lumenMaskCheck.checked)
        # Renamed in Slicer 5.2 when "master volume" became "source volume".
        for setEnabled, setRange in (
                ("SetSourceVolumeIntensityMask", "SetSourceVolumeIntensityMaskRange"),
                ("SetMasterVolumeIntensityMask", "SetMasterVolumeIntensityMaskRange")):
            if hasattr(self.editorNode, setEnabled):
                getattr(self.editorNode, setEnabled)(on)
                if on:
                    getattr(self.editorNode, setRange)(LUMEN_HU_MIN, LUMEN_HU_MAX)
                break

    def onCopySeed(self):
        """Union the whole pre-existing tree into the active branch."""
        if self.logic is None or not self.logic.seedSegmentId:
            return
        active = next((n for n, b in self._segmentButtons.items() if b.checked), None)
        if active is None:
            slicer.util.errorDisplay("Choose a vessel first.")
            return
        if not slicer.util.confirmYesNoDisplay(
                "Add the entire coronary mask to '{}'?\n\nYou would then trim it "
                "down with Scissors. For most branches, painting inside the mask "
                "is faster.".format(active)):
            return

        self.onSelectSegment(active)
        self.editorWidget.setActiveEffectByName("Logical operators")
        effect = self.editorWidget.activeEffect()
        if effect is None:
            slicer.util.errorDisplay(
                "This build of Slicer has no 'Logical operators' effect.")
            return
        effect.setParameter("Operation", "UNION")
        effect.setParameter("ModifierSegmentID", self.logic.seedSegmentId)
        # Without this the copy is clipped by the very mask being copied from,
        # which silently does nothing and looks like a broken button.
        effect.setParameter("BypassMasking", "1")
        effect.self().onApply()
        self.editorWidget.setActiveEffectByName("")
        self._updateChecklist()

    def onJumpToHeart(self):
        if self.logic is not None and not self.logic.jumpToHeart():
            slicer.util.errorDisplay("This case has no heart mask to centre on.")

    def onShow3d(self):
        if self.logic is None or self.logic.segmentationNode is None:
            return
        with _busy():
            self.logic.segmentationNode.CreateClosedSurfaceRepresentation()
            display = self.logic.segmentationNode.GetDisplayNode()
            if display is not None:
                # Scaffolding stays out of the 3D view: a solid heart would hide
                # the very tree the annotator opened 3D to inspect.
                for segmentId in self.logic.helperIds():
                    display.SetSegmentOpacity3D(segmentId, 0.0)
            slicer.app.layoutManager().setLayout(
                slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)

    def _updateChecklist(self):
        """Tick the vessels that have something in them."""
        if self.logic is None or self.logic.assignment is None:
            for button in self._segmentButtons.values():
                button.setText(button.text.replace("  \u2713", ""))
            return
        for i, spec in enumerate(self.logic.project.segments):
            button = self._segmentButtons.get(spec.name)
            if button is None:
                continue
            done = self.logic.segmentHasContent(spec.name)
            required = "" if spec.required else "  (optional)"
            button.setText("{}  {}{}{}".format(
                i + 1, _shortName(spec.name), required,
                "  \u2713" if done else ""))

    def _installShortcuts(self):
        """Number keys pick a vessel; letters pick a tool.

        Keyboard rather than mouse because branch changes happen hundreds of
        times an hour, and every one of them through a list widget is a second
        of attention taken off the image.
        """
        bindings = []
        for i in range(1, 10):
            bindings.append((str(i), lambda index=i - 1: self._selectByIndex(index)))
        for name, key, _tip in VESSEL_EFFECTS:
            bindings.append((key, lambda n=name: self.onEffect(n)))

        for key, handler in bindings:
            shortcut = qt.QShortcut(slicer.util.mainWindow())
            shortcut.setKey(qt.QKeySequence(key))
            shortcut.connect("activated()", handler)
            self._shortcuts.append(shortcut)

    def _selectByIndex(self, index):
        if self.logic is None or self.logic.project is None:
            return
        segments = self.logic.project.segments
        if 0 <= index < len(segments):
            self.onSelectSegment(segments[index].name)

    # -------------------------------------------------------------- actions

    def onSaveDraft(self):
        if self.logic.autosave():
            self.problemsLabel.setText("Draft saved.")
        else:
            self.problemsLabel.setText("Nothing to save yet.")

    def onAutosave(self):
        self.logic.autosave()

    def onHeartbeat(self):
        self.logic.heartbeat()

    def _updateClock(self):
        if self.logic is None or self.logic.assignment is None:
            self.timerLabel.setText("Time on this case: --")
            return
        seconds = int(self.logic.elapsedSeconds())
        self.timerLabel.setText("Time on this case: {:d}:{:02d}:{:02d}".format(
            seconds // 3600, (seconds % 3600) // 60, seconds % 60))

    def onCheck(self):
        problems = self._runChecks()
        if problems is None:
            return
        if not problems:
            self.problemsLabel.setText(
                "<span style='color:#2e7d32'>All checks passed.</span>")
            return
        self.problemsLabel.setText(_problemsHtml(problems))

    def _runChecks(self):
        """Export to a scratch file and validate it. Returns problems, or None."""
        if self.logic.assignment is None:
            slicer.util.errorDisplay("There is no case open.")
            return None
        scratch = os.path.join(
            self.logic.cache.caseDir(self.logic.assignment.assignment_id),
            "check.seg.nrrd")
        with _busy():
            try:
                counts, source, seg = self.logic.exportLabelmap(scratch)
            except Exception:
                slicer.util.errorDisplay(
                    "Could not export the segmentation:\n\n" + traceback.format_exc())
                return None
            finally:
                if os.path.exists(scratch):
                    os.unlink(scratch)
            return self.logic.validate(counts, source, seg)

    def onSubmit(self):
        if self.logic.assignment is None:
            slicer.util.errorDisplay("There is no case open.")
            return
        problems = self._runChecks()
        if problems is None:
            return
        if blocking(problems):
            self.problemsLabel.setText(_problemsHtml(problems))
            slicer.util.errorDisplay(
                "This segmentation cannot be submitted yet:\n\n"
                + summarise(blocking(problems)))
            return

        warningText = ""
        if problems:
            warningText = "\n\nWarnings:\n" + summarise(problems)
        if not slicer.util.confirmYesNoDisplay(
                "Submit '{}'?\n\nThe local copy is deleted once the server has "
                "it.{}".format(self.logic.assignment.case_name, warningText)):
            return

        self.progressBar.setVisible(True)

        def progress(done, total):
            self.progressBar.setMaximum(max(1, total))
            self.progressBar.setValue(done)
            slicer.app.processEvents()

        with _busy():
            try:
                self.logic.submit(note=self.noteEdit.text.strip(), progress=progress)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
            except Exception:
                slicer.util.errorDisplay(
                    "The submission failed:\n\n" + traceback.format_exc()
                    + "\n\nYour work is still saved locally; try again.")
                return
            finally:
                self.progressBar.setVisible(False)

        self.noteEdit.setText("")
        self.problemsLabel.setText("")
        self.caseLabel.setText("Submitted. Press 'Get next case' when you are ready.")
        self.reworkBox.setVisible(False)
        self.seedGroup.setVisible(False)
        self._bindEditor(None, None)
        self._updateChecklist()
        self._updateEnabled()

    def onRelease(self):
        if self.logic.assignment is None:
            return
        if not slicer.util.confirmYesNoDisplay(
                "Give '{}' back to the pool?\n\nAnything you have segmented on it "
                "will be discarded.".format(self.logic.assignment.case_name)):
            return
        with _busy():
            try:
                self.logic.release(reason="released by annotator")
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
        self.caseLabel.setText("No case open.")
        self.reworkBox.setVisible(False)
        self.seedGroup.setVisible(False)
        self._bindEditor(None, None)
        self._updateChecklist()
        self._updateEnabled()

    # --------------------------------------------------------------- review

    def onRefreshReview(self):
        with _busy():
            try:
                self._reviewRows = self.logic.client.reviewQueue()
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
        self.reviewTable.setRowCount(len(self._reviewRows))
        for row, entry in enumerate(self._reviewRows):
            score = entry.get("autoScore") or {}
            mean = score.get("mean_dice")
            cells = [
                entry.get("caseName", ""),
                entry.get("annotator", ""),
                str(entry.get("attempt", 1)),
                "--" if mean is None else "{:.3f}".format(mean),
                ", ".join(entry.get("flagged") or []),
            ]
            for column, text in enumerate(cells):
                self.reviewTable.setItem(row, column, qt.QTableWidgetItem(text))
        self.reviewTable.resizeColumnsToContents()

    def onOpenReview(self):
        row = self.reviewTable.currentRow()
        if row < 0 or row >= len(self._reviewRows):
            slicer.util.errorDisplay("Select a submission first.")
            return
        entry = self._reviewRows[row]
        submissionId = entry["submissionId"]

        with _busy():
            try:
                self.logic.client.claimReview(submissionId)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return

            directory = os.path.join(self.logic.cache.root, "review")
            try:
                os.makedirs(directory)
            except OSError:
                pass
            volumePath = os.path.join(directory, "volume.nrrd")
            segPath = os.path.join(directory, "submission.seg.nrrd")
            try:
                self.logic.client.downloadReviewFile(submissionId, "volume", volumePath)
                self.logic.client.downloadReviewFile(submissionId, "download", segPath)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return

            slicer.mrmlScene.Clear(False)
            volumeNode = slicer.util.loadVolume(volumePath)
            slicer.util.loadSegmentation(segPath)
            slicer.util.setSliceViewerLayers(background=volumeNode, fit=True)

        self._claimedSubmission = submissionId
        self._reviewStart = time.time()

    def onVerdict(self, verdict):
        if not self._claimedSubmission:
            slicer.util.errorDisplay("Claim and open a submission first.")
            return
        comment = self.verdictComment.text.strip()
        if verdict == "reject" and not comment:
            # The server enforces this too. Doing it here as well is the
            # difference between a useful sentence and a round trip: a rejection
            # with no comment sends the case back to a student who has no idea
            # what to change.
            slicer.util.errorDisplay(
                "A rejection needs a comment saying what to fix.")
            return
        seconds = int(time.time() - getattr(self, "_reviewStart", time.time()))
        with _busy():
            try:
                self.logic.client.submitVerdict(
                    self._claimedSubmission, verdict, comment=comment,
                    secondsSpent=seconds)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
        self._claimedSubmission = None
        self.verdictComment.setText("")
        slicer.mrmlScene.Clear(False)
        self.onRefreshReview()

    # ---------------------------------------------------------------- state

    def _updateEnabled(self):
        loggedIn = self.logic is not None and self.logic.loggedIn
        hasCase = loggedIn and self.logic.assignment is not None

        self.loginButton.setEnabled(not loggedIn)
        self.logoutButton.setEnabled(loggedIn)
        self.serverEdit.setEnabled(not loggedIn)
        self.userEdit.setEnabled(not loggedIn)
        self.passwordEdit.setEnabled(not loggedIn)

        self.nextButton.setEnabled(loggedIn and not hasCase)
        for button in (self.saveButton, self.checkButton, self.submitButton,
                       self.releaseButton):
            button.setEnabled(hasCase)
        self.editorBox.setEnabled(hasCase)
        self.vesselBox.setEnabled(hasCase)


def _deadlineText(deadline):
    if not deadline:
        return ""
    days = (deadline - time.time()) / 86400.0
    if days < 0:
        return "  |  <span style='color:#b00'>overdue</span>"
    return "  |  due in {:.0f} day(s)".format(max(1.0, days))


def _problemsHtml(problems):
    lines = []
    for problem in problems:
        color = "#b00" if problem.level == ERROR else "#8a6d00"
        lines.append("<span style='color:{}'>&bull; {}</span>".format(
            color, _escape(problem.message)))
    return "<br>".join(lines)


def _caption(text):
    label = qt.QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("QLabel { color: #5a5f66; }")
    return label


def _shortName(name):
    """``left_anterior_descending`` -> ``Left anterior descending``.

    The underscored form is what the file format needs and what the server
    stores. It is not what anyone should have to read two hundred times a day.
    """
    return name.replace("_", " ").capitalize()


def _escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class _busy:
    """Wait cursor for the duration of a block, restored even on an exception."""

    def __enter__(self):
        qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
        return self

    def __exit__(self, *exc):
        qt.QApplication.restoreOverrideCursor()
        return False


class SegQueueTest(ScriptedLoadableModuleWidget):
    """Placeholder so Slicer's self-test machinery has something to find.

    The real tests live in ``tests/test_segqueue_*.py`` and run under plain
    pytest, because the parts worth testing -- the state machine, the sampling
    policy, the wire protocol, the cache -- were deliberately written to need
    neither Slicer nor a server.
    """

    def runTest(self):
        slicer.util.infoDisplay(
            "SegQueue's tests run under pytest in the repository:\n"
            "    pytest tests/test_segqueue_*.py\n"
            "Nothing to run inside Slicer.")
