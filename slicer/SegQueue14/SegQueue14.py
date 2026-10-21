"""SegQueue14 -- divide one case's coronary tree into LM, LAD, LCx and RCA, send it
back, and keep nothing.

Shown in Slicer as **SegQueue**; the module name SegQueue14 is historical (it was
built for 14 ImageCAS-X classes, D9, reversed by D25). Decisions:
vault/Plans/Human decisions.md, D8-D25. It talks only to ``/api/v1/segqueue14`` on
the same server, keeps its own settings (``SegQueue14/...``) and its own cache
(``~/.segqueue14``), and its library is ``SegQueue14Lib`` so the two modules
cannot shadow each other's code.

What an annotator sees:

* **Get next case** downloads the CT and its yellow *vessel seed* (D23: an
  automatic, uncorrected one-colour mask of the coronary tree), shown beside the
  four empty project segments LM, LAD, LCx and RCA. The annotator divides the seed
  into them -- every side branch takes its parent's class (D1), a ramus
  intermedius is LCx (D1b) -- and corrects the outline (D12). The four segments
  are what is submitted; the seed never is. A case with a model *prelabel*
  instead has it loaded straight into the four segments.
* The heart mask still ships, as a helper segment that is never submitted.
* **Submit** refuses a case whose LAD, LCx or RCA is empty (D13), naming them,
  before anything is uploaded; the server checks again.

The server owns the protocol, local data is a lease, nothing the client says is
trusted: those three decisions are the live module's and are kept unchanged.

From 0.14.0 SegQueue14 *is* the SegQueue release line (project lead, 2026-10-17):
it is published as ``SegQueue-<v>-Slicer-<x.y>.zip`` under ``segqueue-v<v>``,
continuing SegQueue's version numbers, so the update button of SegQueue 0.13
installs it, and the archive's ``SegQueue.py`` is a stub that retires the old
module. Its own update button (``SegQueue14Lib.updater``) only accepts archives
that carry SegQueue14. The server still refuses a module whose protocol is out
of date (``segqueue14.PROTOCOL_VERSION``).
"""

import json
import os
import shutil
import sys
import tempfile
import time
import traceback

import ctk
import qt
import slicer
import vtk
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleWidget,
)

# The shared packages, found the same two ways as the live module finds its own:
#
#   checkout   <repo>/slicer/SegQueue14/SegQueue14.py  with  <repo>/src/segqueue14
#   packaged   .../qt-scripted-modules/SegQueue14.py   with  .../segqueue14 beside it
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_MODULE_DIR))
_SRC = os.path.join(_REPO_ROOT, "src")
_SEARCHED = (os.path.join(_MODULE_DIR, "segqueue14"), _SRC)

_RESOURCES = os.path.join(_MODULE_DIR, "Resources")

_LOGO_LABEL_NAME = "LogoLabel"
_PANEL_DOCK_NAME = "PanelDockWidget"
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

try:
    # Only names the live `segqueue` already had are imported from it: in an
    # installed Slicer the live module's vendored copy may be the one found first.
    from segqueue import states as st
    from segqueue.checksum import sha256_file, verify_file
    from segqueue.dataset import sniff_suffix, suffix_for
    from segqueue.segcheck import Geometry
    from segqueue import release as rel
    from segqueue14 import labels
    from segqueue14 import protocol
    from segqueue14.protocol import SubmissionMeta
    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - surfaced in the UI instead
    st = None
    rel = None
    protocol = None
    labels = None
    _IMPORT_ERROR = str(exc)

from SegQueue14Lib import (
    CacheError,
    CaseCache,
    UpdateError,
    defaultRoot,
    updater,
)
from SegQueue14Lib import SegQueue14Client as SegQueueClient
from SegQueue14Lib import SegQueue14Error as SegQueueError

#: Continues SegQueue's numbering (0.13.0 was the last 4-class release). The
#: release tag is ``segqueue-v`` + this; bump it to publish.
__version__ = "0.16.3"

#: Where the module's help points.
HELP_URL = "https://github.com/christianGRogers/Asclepius"

#: How often the startup update check may ask GitHub, as in the live module.
UPDATE_CHECK_HOURS = 6
#: Delay before that check, so the panel is on screen first.
UPDATE_CHECK_DELAY_MS = 1200

AUTOSAVE_SECONDS = 120
NOTES_REFRESH_SECONDS = 90
HEARTBEAT_SECONDS = 300

#: Window/level for contrast-enhanced coronary CT, as in the live module.
CTA_WINDOW = 800
CTA_LEVEL = 300

REVIEW_FILTERS = (
    ("assigned", "Assigned, not downloaded"),
    ("downloaded", "Being worked on"),
    ("submitted", "Submitted"),
    ("under_review", "Under review"),
    ("approved", "Approved"),
    ("rejected", "Rejected (historical)"),
    ("released", "Given back"),
)
REVIEW_DECIDED_STATES = frozenset({"approved", "released"})

#: Opacity of the classes in the 3D view when a case opens: solid enough to
#: read which branch is which, the question a correction starts from.
PRELABEL_3D_OPACITY = 0.85
#: The binary vessel seed (D23): yellow, a light fill in 2D, faint in 3D, so the
#: classes painted over it stand out against it.
SEED_COLOR = (0.95, 0.85, 0.20)
SEED_FILL = 0.25
SEED_3D_OPACITY = 0.30
#: The heart-region helper: a muted red with a barely-there fill, context only.
REGION_COLOR = (0.85, 0.55, 0.55)
REGION_FILL = 0.08

#: Settings keys: SegQueue14's own, so the two modules can point at different
#: servers or caches without either overwriting the other's.
_SETTING_SERVER = "SegQueue14/serverUrl"
_SETTING_CACHE = "SegQueue14/cacheRoot"
#: Kept solely so that, as in the live module, a remembered username is cleared.
_SETTING_LEGACY_USER = "SegQueue14/lastUser"
_SETTING_UPDATE = "SegQueue14/updateCheck"
#: The retired module's server setting, read (never written) so an annotator who
#: updated from SegQueue 0.13 finds their server already filled in.
_LIVE_SETTING_SERVER = "SegQueue/serverUrl"


class SegQueue14(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SegQueue"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Christian Rogers"]
        # How to annotate lives in the repository, not in the panel.
        self.parent.helpText = (
            'Documentation: <a href="{0}">{0}</a>'.format(HELP_URL))
        self.parent.acknowledgementText = ""
        _icon = os.path.join(_RESOURCES, "Icons", "SegQueue14.png")
        if os.path.isfile(_icon):
            self.parent.icon = qt.QIcon(_icon)


# =============================================================================
#  Logic
# =============================================================================


class SegQueue14Logic(ScriptedLoadableModuleLogic):
    """Everything the module does, with no Qt in sight."""

    def __init__(self, cacheRoot=None):
        ScriptedLoadableModuleLogic.__init__(self)
        self.client = None
        self.cache = CaseCache(cacheRoot or _storedCacheRoot())
        self.project = None
        self.assignment = None

        self.volumeNode = None
        self.segmentationNode = None
        self._sessionStart = None
        #: Segment id of the heart helper, when the case ships one.
        self.regionSegmentId = None
        #: Segment id of the binary vessel seed (D23), when the case ships one.
        self.seedSegmentId = None
        #: Whether this case opened from an autosaved draft rather than fresh.
        self.resumedDraft = False
        #: How many of the classes the prelabel filled on this open.
        self.prelabelClasses = 0
        #: How many classes were filled with a copy of the seed on this open (D26).
        self.seedPrefilled = 0

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
        volumePath = self.correctSuffix(volumePath)
        self.cache.update(assignment.assignment_id, volumePath=volumePath)

        self.volumeNode = slicer.util.loadVolume(volumePath)
        self.volumeNode.SetName(assignment.case_name or "case")
        self._loadOrCreateSegmentation(manifest)
        self._loadHelpers(assignment)
        # A fresh case starts from the model's prediction; a reopened draft is
        # the annotator's own correction and is left alone.
        self.prelabelClasses = 0
        self.seedPrefilled = 0
        if not self.resumedDraft and assignment.has_prelabel:
            self.prelabelClasses = self._loadPrelabel(assignment)
        elif not self.resumedDraft and assignment.has_seed:
            # D26: every class starts as the whole seed, for the annotator to cut
            # down to that class.
            self.seedPrefilled = self._prefillClassesFromSeed(assignment)
        slicer.util.setSliceViewerLayers(background=self.volumeNode, fit=True)
        self.applyViewPreset()
        if assignment.has_seed and not assignment.has_prelabel:
            # Four identical copies on screen at once would hide each other; the
            # annotator shows one class at a time and trims it (D26).
            self.setClassesVisible(False)
        self._sessionStart = time.time()
        return manifest

    # ------------------------------------------------------- helper masks

    def _loadHelpers(self, assignment):
        """Bring the case's heart mask and vessel seed into the scene, as helpers.

        Scaffolding only: ``exportLabelmap`` copies the project's own segments,
        so a helper is structurally unable to reach the server. The live
        project's ImageCAS seed is never shipped (D8); a pooled new-dataset case
        may ship its own binary vessel seed (D23) -- an automatic outline of the
        whole tree, with no classes, for the annotator to divide into the project's classes
        (Segment Editor: Islands to pick a branch, Logical operators to add it to
        a class).
        """
        self.regionSegmentId = self._helperId(protocol.REGION_SEGMENT_NAME)
        if assignment.has_region and self.regionSegmentId is None:
            self.regionSegmentId = self._fetchHelper(
                assignment, protocol.ASSET_REGION,
                protocol.REGION_SEGMENT_NAME, REGION_COLOR, fill=REGION_FILL)
        self.seedSegmentId = self._helperId(protocol.SEED_SEGMENT_NAME)
        if assignment.has_seed and self.seedSegmentId is None:
            self.seedSegmentId = self._fetchHelper(
                assignment, protocol.ASSET_SEED,
                protocol.SEED_SEGMENT_NAME, SEED_COLOR, fill=SEED_FILL)

    # ------------------------------------------------------------ prelabel

    def _loadPrelabel(self, assignment):
        """Download the case's prediction and fill the project segments.

        Returns how many classes it filled. Never raises: a case whose prelabel
        cannot be fetched or read is still a case the annotator can draw from
        scratch -- a worse start, never a blocked one.
        """
        stem = os.path.join(self.cache.caseDir(assignment.assignment_id),
                            protocol.ASSET_PRELABEL)
        try:
            path = self._cachedHelper(stem)
            if path is None:
                path = self.client.downloadAsset(
                    assignment.case_id, protocol.ASSET_PRELABEL, stem)
            if path is None:
                return 0
            return self.importLabelsIntoProject(path)
        except Exception:
            return 0

    def importLabelsIntoProject(self, path, segmentationNode=None, icx14=False):
        """Load an integer label volume into the project's segments, by value.

        A voxel of value 3 goes into the segment whose label is 3 (LCx), and so
        on for each of the project's four classes (D25): the prelabel and the
        submission use the project's label values, so the value *is* the class.
        Values the project does not know are dropped rather than becoming
        segments nobody asked for.

        ``icx14`` says the volume is an ImageCAS-X reference, in its own 14
        values: it is first collapsed to the four exactly as the server scores
        it (``labels.icx14_to_four``, D25; #68). Only the reviewer's reference
        button sets it, because the reference asset always is ImageCAS-X;
        prelabels and submissions keep the strict by-value import.

        One class at a time, as a 0/1 mask imported into exactly one named
        segment. Slicer's import resamples into the segmentation's geometry when
        the grids differ, and with one value and one target segment there is no
        question of how values map to segments -- a prediction with no IM, say,
        cannot shift every later class into the wrong segment. Returns how many
        classes ended up with voxels.
        """
        import numpy as np

        segmentationNode = segmentationNode or self.segmentationNode
        if segmentationNode is None or self.project is None:
            return 0
        specs = sorted(self.project.segments, key=lambda spec: int(spec.label))

        labelNode = scratch = None
        filled = 0
        try:
            labelNode = slicer.util.loadLabelVolume(path)
            values = slicer.util.arrayFromVolume(labelNode).copy()
            if icx14:
                # arrayFromVolume is (k, j, i); the spacing is (i, j, k).
                values = labels.icx14_to_four(
                    values, tuple(reversed(labelNode.GetSpacing())))
            scratch = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLabelMapVolumeNode", "SegQueue14PrelabelClass")
            logic = slicer.modules.segmentations.logic()
            for spec in specs:
                mask = (values == int(spec.label)).astype(np.uint8)
                segmentId = _segmentIdIn(segmentationNode, spec.name)
                if segmentId is None:
                    segmentId = segmentationNode.GetSegmentation().AddEmptySegment(
                        spec.name, spec.name, list(spec.color))
                if not mask.any():
                    continue
                slicer.util.updateVolumeFromArray(scratch, mask)
                scratch.CopyOrientation(labelNode)
                target = vtk.vtkStringArray()
                target.InsertNextValue(segmentId)
                logic.ImportLabelmapToSegmentationNode(scratch, segmentationNode, target)
                # No SetLabelValue here: the import leaves the voxels in a layer
                # under the value it chose, and changing the segment's value
                # afterwards makes them unreadable -- every class but the first
                # came back empty (Slicer 5.12, found with #68). Nothing needs it:
                # exportLabelmap numbers the classes by project order.
                segment = segmentationNode.GetSegmentation().GetSegment(segmentId)
                if segment is not None:
                    segment.SetName(spec.name)
                    segment.SetColor(*spec.color)
                if _segmentHasContent(segmentationNode, spec.name):
                    filled += 1
        finally:
            for node in (labelNode, scratch):
                if node is not None:
                    slicer.mrmlScene.RemoveNode(node)
        return filled

    def _prefillClassesFromSeed(self, assignment):
        """Fill every project class with a copy of the case's vessel seed (D26).

        The annotator then cuts each class down to its own vessel, instead of
        building it up from nothing. Copied from the seed helper segment
        ``_loadHelpers`` just added, which is already on the CT's grid. Returns
        how many classes were filled; never raises -- a case whose seed cannot be
        copied still opens, with empty classes and the seed shown as a guide.
        """
        try:
            return self.copySegmentIntoEveryClass(self.seedSegmentId)
        except Exception:
            return 0

    def copySegmentIntoEveryClass(self, sourceSegmentId):
        """Put a full copy of one segment's voxels into every project segment.

        Written per class with ``updateSegmentBinaryLabelmapFromArray`` against
        the CT, which keeps the copies as overlapping segments in separate
        labelmap layers; trimming one leaves the others whole. (Importing one
        label volume into several target segments does not: only the first gets
        the voxels -- checked in Slicer 5.8.) ``submit`` refuses the case until
        no voxel is left in two classes. Returns how many classes have voxels.
        """
        if (not sourceSegmentId or self.segmentationNode is None
                or self.volumeNode is None or self.project is None):
            return 0
        mask = slicer.util.arrayFromSegmentBinaryLabelmap(
            self.segmentationNode, sourceSegmentId, self.volumeNode)
        if mask is None or not mask.size or not mask.any():
            return 0
        mask = (mask > 0).astype("uint8")
        filled = 0
        for spec in sorted(self.project.segments, key=lambda spec: int(spec.label)):
            segmentId = self.segmentIdFor(spec.name)
            if segmentId is None:
                segmentId = self.segmentationNode.GetSegmentation().AddEmptySegment(
                    spec.name, spec.name, list(spec.color))
            slicer.util.updateSegmentBinaryLabelmapFromArray(
                mask, self.segmentationNode, segmentId, self.volumeNode)
            if _segmentHasContent(self.segmentationNode, spec.name):
                filled += 1
        return filled

    def setClassesVisible(self, visible):
        """Show or hide the project's class segments, leaving the helpers alone.

        Returns how many segments changed. The per-segment eye in the Segment
        Editor turns each one back on.
        """
        if self.segmentationNode is None or self.project is None:
            return 0
        display = self.segmentationNode.GetDisplayNode()
        if display is None:
            return 0
        changed = 0
        for spec in self.project.segments:
            segmentId = self.segmentIdFor(spec.name)
            if segmentId:
                display.SetSegmentVisibility(segmentId, bool(visible))
                changed += 1
        return changed

    def classOverlaps(self):
        """``[(name, name, voxels), ...]``: every pair of classes sharing voxels.

        On the source grid, one class at a time: each voxel carries a bit per class
        it is in, so memory stays at one mask plus one bit volume however large
        the CT is. A seed-prefilled class that has not been cut down yet overlaps
        every other one, which is how an untouched copy is caught before upload
        (D26).
        """
        import numpy as np

        if self.segmentationNode is None or self.volumeNode is None or self.project is None:
            return []
        specs = sorted(self.project.segments, key=lambda spec: int(spec.label))
        dtype = np.uint8 if len(specs) <= 8 else np.uint32
        bits = None
        seen = []          # (bit index, name) of classes already folded in
        pairs = []
        for index, spec in enumerate(specs):
            segmentId = self.segmentIdFor(spec.name)
            if not segmentId:
                continue
            try:
                mask = slicer.util.arrayFromSegmentBinaryLabelmap(
                    self.segmentationNode, segmentId, self.volumeNode)
            except Exception:
                continue
            if mask is None or not mask.size:
                continue
            mask = mask > 0
            if bits is None:
                bits = np.zeros(mask.shape, dtype)
            if mask.shape != bits.shape:
                continue
            here = bits[mask]
            for other, name in seen:
                shared = int(((here >> other) & 1).sum())
                if shared:
                    pairs.append((name, spec.name, shared))
            bits[mask] |= dtype(1 << index)
            seen.append((index, spec.name))
        return pairs

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
        """An already-downloaded helper, whatever extension it arrived with.

        A ``.part`` file is a download that never finished (Slicer closed
        mid-transfer), so it is never a hit (#64).
        """
        directory, prefix = os.path.dirname(stem), os.path.basename(stem)
        try:
            names = os.listdir(directory)
        except OSError:
            return None
        for filename in sorted(names):
            if filename.startswith(prefix + ".") and not filename.endswith(".part"):
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
        return [s for s in (self.regionSegmentId, self.seedSegmentId) if s]

    def showPrelabelIn3d(self, on=True):
        """Show the classes in the 3D view and keep the heart helper out of it.

        Which branch is which is a question about the *shape* of the tree, and the
        3D view is where a wrong name is obvious at a glance. Returns how many
        segments are showing.
        """
        if self.segmentationNode is None:
            return 0
        display = self.segmentationNode.GetDisplayNode()
        if display is None:
            return 0
        if on:
            self.segmentationNode.CreateClosedSurfaceRepresentation()
        shown = 0
        helpers = set(self.helperIds())
        segmentation = self.segmentationNode.GetSegmentation()
        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            if segmentId == self.seedSegmentId:
                # The seed's shape is the whole point of it: faint, but in 3D.
                display.SetSegmentOpacity3D(segmentId, SEED_3D_OPACITY if on else 0.0)
                continue
            visible = bool(on) and segmentId not in helpers
            display.SetSegmentOpacity3D(segmentId, PRELABEL_3D_OPACITY if visible else 0.0)
            shown += int(visible)
        return shown

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

    def applyProjectNames(self):
        """Put the project's names and colours back onto a loaded submission.

        A submission is stored as a *labelmap*: integers on the source grid, with
        no names and no colours, because that is the one form whose geometry
        matches the CT voxel for voxel and that ``segtrain convert`` can read
        without re-registering anything. The cost is that loading one back gives
        ``Segment_1``, ``Segment_2`` and whatever colours Slicer picked, which
        tells a reviewer nothing about which artery they are looking at.

        The label values do survive, and they are the protocol's -- that is what
        ``_applyTemplate`` pins them to -- so they are enough to put the names
        back. Done on the way in rather than by changing what is stored: the
        stored form is correct, and every submission ever made can be read this
        way, including the ones already on the server.

        It also makes the reviewer's own edits exportable. ``exportLabelmap``
        looks segments up *by name*, so without this a revision saved from a
        submission would find nothing to export and silently write an empty file.

        Returns how many segments were matched.
        """
        if self.segmentationNode is None or self.project is None:
            return 0
        byLabel = {int(spec.label): spec for spec in self.project.segments}
        segmentation = self.segmentationNode.GetSegmentation()
        display = self.segmentationNode.GetDisplayNode()

        # Only when the label values actually tell the segments apart. A label
        # value is unique within a *layer*, not within a segmentation: a working
        # scene can hold four segments that all carry 1 in four separate layers,
        # and renaming by value there would give every one of them the same name
        # and wipe the template. A submission loaded from a labelmap is the case
        # this is for, and there the values are distinct by construction.
        values = [_labelValueOf(segmentation.GetSegment(segmentation.GetNthSegmentID(i)),
                                segmentation.GetNthSegmentID(i))
                  for i in range(segmentation.GetNumberOfSegments())]
        known = [v for v in values if v in byLabel]
        if len(known) != len(set(known)):
            return 0

        matched = 0
        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            segment = segmentation.GetSegment(segmentId)
            spec = byLabel.get(_labelValueOf(segment, segmentId))
            if spec is None:
                continue
            segment.SetName(spec.name)
            segment.SetColor(*spec.color)
            if display is not None:
                # The display node caches the colour it was given when the
                # segment was created, so setting it on the segment alone leaves
                # the slice views showing the old one.
                try:
                    display.SetSegmentOverrideColor(segmentId, *spec.color)
                except AttributeError:  # pragma: no cover - old Slicer
                    pass
            matched += 1
        return matched

    def showSubmissionIn3d(self):
        """Put every segment of the open segmentation into the 3D view.

        The opposite of what a case open does. An annotator starts with four
        identical copies of one mask, so they are hidden and only the mask shows:
        stacked on the same voxels they are not a picture of anything. A reviewer
        is looking at the finished division, where every segment is a different
        vessel and the arrangement between them is the thing being judged -- so
        all of them show, and the surface is built rather than waited for.

        Returns how many segments were made visible.
        """
        if self.segmentationNode is None:
            return 0
        self.segmentationNode.CreateClosedSurfaceRepresentation()
        display = self.segmentationNode.GetDisplayNode()
        if display is None:
            return 0

        display.SetVisibility(True)
        for setter in ("SetVisibility3D", "SetVisibility2DFill",
                       "SetVisibility2DOutline"):
            try:
                getattr(display, setter)(True)
            except AttributeError:  # pragma: no cover - old Slicer naming
                pass

        segmentation = self.segmentationNode.GetSegmentation()
        shown = 0
        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            display.SetSegmentVisibility(segmentId, True)
            try:
                display.SetSegmentOpacity3D(segmentId, 1.0)
            except AttributeError:  # pragma: no cover - old Slicer
                pass
            shown += 1
        return shown

    def centre3d(self):
        """Frame the 3D view on what is in it. Returns whether a view moved.

        The 3D camera belongs to Slicer, not to the case: it keeps the focal
        point and the zoom it was left with, which after the case before this one
        is a point in space this patient does not occupy. The surface builds
        correctly and is simply not on screen -- so the annotator learns to reach
        for the view controller's centre button on every case, and the one who
        does not know that button exists concludes the 3D view is broken.

        The render is forced first because the camera is fitted to the bounds of
        the actors actually in the renderer, and a segment's surface actor does
        not exist until something has drawn it. Then the focal point, as the
        centre button does, and then the distance -- a tree correctly centred and
        two metres away is still not in view.
        """
        layoutManager = slicer.app.layoutManager()
        if layoutManager is None:  # pragma: no cover - no main window
            return False
        try:
            count = layoutManager.threeDViewCount
        except AttributeError:  # pragma: no cover - old Slicer naming
            return False

        moved = False
        for index in range(count):
            widget = layoutManager.threeDWidget(index)
            view = widget.threeDView() if widget is not None else None
            if view is None:
                continue
            try:
                view.forceRender()
                view.resetFocalPoint()
                view.resetCamera()
            except AttributeError:  # pragma: no cover - old Slicer naming
                # Never fail a case open over a camera. A build that spells these
                # differently costs the annotator one click on the centre button;
                # raising here would cost them the case.
                continue
            moved = True
        return moved

    def segmentIdFor(self, name):
        """The id of the open case's segment called ``name``, or None."""
        if self.segmentationNode is None:
            return None
        return _segmentIdIn(self.segmentationNode, name)

    def correctSuffix(self, path):
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
        """Reopen the autosaved draft, or lay out a fresh set of template segments.

        Sets ``resumedDraft``, which is what stops the prelabel overwriting an
        annotator's own corrections when they come back to a case tomorrow.
        """
        self.resumedDraft = False
        draft = manifest.get("workPath")
        if draft and os.path.isfile(draft):
            try:
                self.segmentationNode = slicer.util.loadSegmentation(draft)
                self.resumedDraft = self.segmentationNode is not None
            except Exception:
                # A corrupt autosave must not lock the annotator out of the case.
                # Losing the draft is bad; losing the case is worse.
                slicer.util.errorDisplay(
                    "The autosaved draft for this case could not be reopened, so "
                    "it has been discarded and the case reset to empty segments.\n\n"
                    + traceback.format_exc())
                self.segmentationNode = None
                self.resumedDraft = False
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

    # ------------------------------------------------------------- notes

    def noteDraft(self):
        """Whatever the annotator had typed and not posted, from the manifest."""
        if self.assignment is None:
            return ""
        manifest = self.cache.manifest(self.assignment.assignment_id) or {}
        return manifest.get("noteDraft", "") or ""

    def saveNoteDraft(self, text):
        """Keep an unposted note with the case rather than in the widget.

        A half-written note is the kind of thing that is only written once. It
        rides along with the segmentation draft -- same directory, same purge --
        so a crash costs nothing and a submitted case takes it with it.
        """
        if self.assignment is None:
            return False
        self.cache.update(self.assignment.assignment_id,
                          noteDraft=(text or "")[:protocol.NOTE_MAX_CHARS])
        return True

    def caseNotes(self, limit=None):
        if self.assignment is None or not self.loggedIn:
            return []
        return self.client.caseNotes(self.assignment.case_id, limit=limit)

    def addCaseNote(self, text):
        if self.assignment is None:
            raise SegQueueError("There is no case open to add a note to.")
        return self.client.addCaseNote(self.assignment.case_id, text)

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

        **Named segments, not everything in the scene.** The scene also holds the
        heart mask, which came from the source dataset and
        must never be submitted as if an annotator had drawn them. Passing an
        explicit id list is what excludes them -- structurally, not by
        convention.

        That id list is also load-bearing for a subtler reason. A segmentation
        keeps its binary labelmaps in *layers*, and Slicer adds a layer whenever
        segments might overlap -- which Draw tube does on every apply. Copying
        segments into a scratch segmentation and exporting that silently drops
        everything above layer 0, so the second vessel an annotator draws comes
        out empty. ``ExportSegmentsToLabelmapNode`` walks the layers properly.
        The symptom was a validation failure insisting a vessel was empty while
        it was plainly on screen.

        Returns ``(voxelCounts, sourceGeometry, segmentationGeometry)``.
        """
        segmentIds = vtk.vtkStringArray()
        for spec in self.project.segments:
            segmentId = self.segmentIdFor(spec.name)
            if segmentId:
                segmentIds.InsertNextValue(segmentId)

        labelmapNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "SegQueue14Export")
        try:
            ok = slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(
                self.segmentationNode, segmentIds, labelmapNode, self.volumeNode,
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
            return counts, self.sourceGeometry(), _geometryOf(labelmapNode)
        finally:
            slicer.mrmlScene.RemoveNode(labelmapNode)

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
        counts, sourceGeom, segGeom = self._exportChecked(path, "submit")

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

    def reviseSubmission(self, submissionId, note="", seconds=None, progress=None):
        """Upload the open scene as a reviewer's corrected version of a submission.

        The annotator's upload is never touched. This adds another submission on
        the same assignment, credited to the reviewer, and the server approves the
        case on the strength of it -- see the ``revise`` endpoint for why the
        authorship matters more than it looks.

        Validated with the same checks the annotator's submission runs, including
        the overlap check: a reviewer correcting a case by hand is exactly as able
        to leave two branches sharing a voxel as an annotator is.
        """
        if self.segmentationNode is None or self.volumeNode is None:
            raise SegQueueError("There is no segmentation open to save.")
        if self.client is None or self.project is None:
            raise SegQueueError("You are not logged in.")

        path = os.path.join(self.reviewDir(), "revision.seg.nrrd")
        counts, sourceGeom, segGeom = self._exportChecked(path, "save")

        meta = SubmissionMeta(
            checksum=sha256_file(path),
            size_bytes=os.path.getsize(path),
            # The reviewer's own time on it, not the annotator's. Recording the
            # annotator's here would put their minutes on the reviewer's row.
            annotation_seconds=float(seconds or 0.0),
            voxel_counts=counts,
            slicer_version=slicer.app.applicationVersion,
            extension_version=__version__,
            annotator_note=note,
        )
        uploaded = self.client.uploadFile(
            path, self.project.upload_folder_id,
            name="revision_{}.seg.nrrd".format(submissionId),
            progress=progress)
        return self.client.reviseSubmission(submissionId, meta, uploaded["_id"])

    def _exportChecked(self, path, action):
        """Export the project segments to ``path``, refusing what the server would.

        Returns ``(counts, sourceGeometry, segmentationGeometry)`` as
        ``exportLabelmap`` does. The same checks guard an annotator's submission
        and a reviewer's revision; ``action`` ("submit", "save") only words the
        refusal for an empty scene.
        """
        # D26: no voxel in two classes -- in particular, no class left as an
        # untrimmed copy of the seed. Checked before the export, which would
        # otherwise quietly give each shared voxel to one of the classes.
        overlaps = self.classOverlaps()
        if overlaps:
            raise SegQueueError(labels.overlap_message(overlaps))
        counts, sourceGeom, segGeom = self.exportLabelmap(path)

        # D13: LAD, LCx and RCA must each have something in them. Checked here,
        # on the exported volume the server will receive, so the annotator hears
        # it before an upload rather than after; the server checks again.
        missing = labels.missing_required(counts)
        if missing:
            raise SegQueueError(labels.missing_required_message(missing))
        if not os.path.isfile(path):
            raise SegQueueError(
                "There is nothing to {} -- none of the segments has any "
                "voxels in it.".format(action))
        return counts, sourceGeom, segGeom

    def reviewDir(self):
        """The scratch directory under the cache root that review work goes to."""
        directory = os.path.join(self.cache.root, "review")
        try:
            os.makedirs(directory)
        except OSError:
            pass
        return directory

    def release(self, reason=""):
        """Give a case back to the pool and purge it locally."""
        assignment = self.assignment
        if assignment is None:
            return None
        response = self.client.releaseCase(assignment.assignment_id, reason=reason)
        self.closeCase(purge=True)
        return response


def _labelValueOf(segment, segmentId):
    """The label value a loaded segment carries, however this Slicer exposes it.

    ``GetLabelValue`` is the answer on 5.2 and later. Older builds do not have
    it, and there the name Slicer generated -- ``Segment_3`` for label 3 -- is
    the only record of it, which is exactly the name this is being used to
    replace.
    """
    try:
        return int(segment.GetLabelValue())
    except (AttributeError, TypeError, ValueError):
        pass
    for text in (segment.GetName() or "", segmentId or ""):
        tail = text.rsplit("_", 1)[-1]
        if tail.isdigit():
            return int(tail)
    return None


def _segmentIdIn(segmentationNode, name):
    """The id of the segment called ``name`` in any segmentation node, or None."""
    segmentation = segmentationNode.GetSegmentation()
    for i in range(segmentation.GetNumberOfSegments()):
        segmentId = segmentation.GetNthSegmentID(i)
        if segmentation.GetSegment(segmentId).GetName() == name:
            return segmentId
    return None


def _segmentHasContent(segmentationNode, name):
    """Whether a segment has any voxels, cheaply.

    Reads the internal labelmap, which Slicer keeps cropped to the segment's own
    extent -- for a coronary branch that is a few hundred kilobytes, far cheaper
    than re-exporting the whole volume.
    """
    segmentId = _segmentIdIn(segmentationNode, name)
    if not segmentId:
        return False
    try:
        array = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, segmentId)
    except Exception:
        return False
    return array is not None and array.size > 0 and bool(array.any())


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


class SegQueue14Widget(ScriptedLoadableModuleWidget):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        self.logic = None
        self.editorWidget = None
        self.editorNode = None
        self.autosaveTimer = None
        self.heartbeatTimer = None
        self.clockTimer = None
        self.notesTimer = None
        self._reviewRows = []
        self._reviewCases = []
        self._annotators = []
        self._historyRows = []
        self._claimedSubmission = None
        self._reviewStart = None
        self._slicerLogo = None

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

        self.logic = SegQueue14Logic()

        # Sections sit directly against each other by default, which is what
        # made six collapsible buttons read as one undifferentiated list.
        self.layout.setSpacing(10)

        # Older versions remembered the username. Drop anything they stored, so
        # upgrading actually stops the autofill instead of merely not adding to
        # it. Harmless when the key is already absent.
        qt.QSettings().remove(_SETTING_LEGACY_USER)

        self._buildUpdateBanner()
        self._buildLoginSection()
        self._buildCaseSection()
        self._buildEditorSection()
        self._buildSubmitSection()
        self._buildReviewSection()
        self.layout.addStretch(1)

        self._startTimers()
        self._updateEnabled()










    # ------------------------------------------------------------------ notes

    def _renderNotes(self, notes):
        """Draw the thread. Newest at the bottom, and scrolled to it.

        Chronological rather than newest-first because the thread is read as a
        history of one case -- what was tried, what the reviewer said, what was
        done about it -- and that only makes sense forwards.
        """
        if not notes:
            self.notesBrowser.setHtml(
                "<span style='color:{}'>No notes on this case yet.</span>".format(
                    _themeColours()["muted"]))
            return
        blocks = []
        for note in notes:
            when = ""
            if note.created_at:
                try:
                    when = time.strftime("%d %b %H:%M", time.localtime(note.created_at))
                except (ValueError, OSError):
                    when = ""
            colour = "#6a6a6a" if note.system else "#1466D8"
            blocks.append(
                "<p style='margin:0 0 8px 0'>"
                "<b style='color:{colour}'>{author}</b>"
                "<span style='color:#8a8a8a'>  {when}</span><br>{text}</p>".format(
                    colour=colour, author=_escape(note.author or "unknown"),
                    when=_escape(when),
                    text=_escape(note.text).replace("\n", "<br>")))
        self.notesBrowser.setHtml("".join(blocks))
        # The newest note is the one worth reading; a thread that opens at the
        # top hides it behind three months of history.
        scrollBar = self.notesBrowser.verticalScrollBar()
        scrollBar.setValue(scrollBar.maximum)

    def onRefreshNotes(self, quiet=True):
        """Refetch the thread. Silent on failure when it was the timer asking.

        A note thread that cannot be fetched is a missing panel. It is never a
        reason an annotator cannot get on with the case, so the timer swallows
        everything and only a deliberate press reports.
        """
        if self.logic is None or self.logic.assignment is None:
            self._renderNotes([])
            return
        try:
            notes = self.logic.caseNotes()
        except SegQueueError as exc:
            if not quiet:
                slicer.util.errorDisplay(str(exc))
            return
        except Exception:
            if not quiet:
                slicer.util.errorDisplay(
                    "Could not fetch the notes:\n\n" + traceback.format_exc())
            return
        self._renderNotes(notes)

    def onPostNote(self):
        """Send what is in the box. One press, and it is on the server."""
        if self.logic is None or self.logic.assignment is None:
            return
        text = protocol.clean_note(self.noteInput.text)
        if not text:
            return
        with _busy():
            try:
                self.logic.addCaseNote(text)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
            except Exception:
                slicer.util.errorDisplay(
                    "The note could not be posted, so it has been left in the "
                    "box:\n\n" + traceback.format_exc())
                return
        # Only now: an unsent note must survive a failed send.
        self.noteInput.setText("")
        self.logic.saveNoteDraft("")
        self.onRefreshNotes()

    def _clearNotes(self):
        """Empty the thread and the compose box when the case goes away."""
        self.noteInput.setText("")
        self._renderNotes([])

    def onNotesTimer(self):
        if self.logic is not None and self.logic.assignment is not None:
            self.onRefreshNotes()

    def _saveNoteDraft(self):
        """Persist the unposted note. Cheap, and called wherever work is saved."""
        if self.logic is not None and self.logic.assignment is not None:
            try:
                self.logic.saveNoteDraft(self.noteInput.text)
            except Exception:
                pass

    # ----------------------------------------------------------------- update

    def _buildUpdateBanner(self):
        """A strip that stays hidden until there is something to install.

        Hidden rather than showing "you are up to date", because the panel's job
        is to get an annotator into a case and every permanent widget is a small
        tax on that. It appears when it has something to say and not before.
        """
        frame = qt.QFrame()
        frame.setFrameShape(qt.QFrame.StyledPanel)
        frame.setVisible(False)
        self.updateBanner = frame

        layout = qt.QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)

        self.updateLabel = qt.QLabel()
        self.updateLabel.setWordWrap(True)
        layout.addWidget(self.updateLabel)

        row = qt.QHBoxLayout()
        self.updateButton = qt.QPushButton("Update and restart")
        self.updateButton.setToolTip(
            "Downloads the new version, installs it over this one and restarts "
            "Slicer. Your draft is saved first and the case you are on is "
            "waiting when Slicer comes back.")
        self.updateButton.clicked.connect(self.onUpdateNow)
        row.addWidget(self.updateButton)

        self.updateNotesButton = qt.QPushButton("What changed")
        self.updateNotesButton.setToolTip("Opens the release notes in a browser.")
        self.updateNotesButton.clicked.connect(self.onOpenReleaseNotes)
        row.addWidget(self.updateNotesButton)

        self.updateLaterButton = qt.QPushButton("Not now")
        self.updateLaterButton.setToolTip(
            "Hides this until the next time you open the module.")
        self.updateLaterButton.clicked.connect(
            lambda: self.updateBanner.setVisible(False))
        row.addWidget(self.updateLaterButton)
        layout.addLayout(row)

        self.updateProgress = qt.QProgressBar()
        self.updateProgress.setVisible(False)
        layout.addWidget(self.updateProgress)

        self.layout.addWidget(frame)

    def _slicerMinorVersion(self):
        """``"5.8"`` -- the version extensions are packaged against."""
        try:
            return "{}.{}".format(int(slicer.app.majorVersion),
                                  int(slicer.app.minorVersion))
        except Exception:
            pass
        try:
            parts = str(slicer.app.applicationVersion).split(".")
            return "{}.{}".format(int(parts[0]), int(parts[1]))
        except Exception:
            return ""

    def _checkForUpdateQuietly(self):
        """The startup check. Silent about everything except a real update.

        Every failure here -- offline, proxied, rate-limited, GitHub down -- is
        treated as "no update". None of them is the annotator's problem, and a
        dialogue box about one is worse than not knowing.
        """
        cached = updater.readCache(slicer.util.settingsValue(_SETTING_UPDATE, ""))
        if updater.cacheIsFresh(cached, UPDATE_CHECK_HOURS * 3600):
            return
        try:
            release = updater.checkForUpdate(__version__, self._slicerMinorVersion())
        except UpdateError:
            return
        except Exception:
            return
        self._recordCheck(release)
        if release is not None:
            self._showUpdate(release)

    def onCheckForUpdates(self):
        """The manual check. Ignores the cache and always says what it found."""
        with _busy():
            try:
                release = updater.checkForUpdate(
                    __version__, self._slicerMinorVersion())
            except UpdateError as exc:
                slicer.util.errorDisplay(str(exc))
                return
        self._recordCheck(release)
        if release is None:
            slicer.util.infoDisplay(
                "SegQueue {} is the newest published version.".format(__version__))
            return
        self._showUpdate(release)

    def _recordCheck(self, release):
        tag = str((release or {}).get("tag_name") or "")
        qt.QSettings().setValue(_SETTING_UPDATE, json.dumps({
            "checkedAt": time.time(), "tag": tag}))

    def _showUpdate(self, release):
        self._pendingUpdate = release
        ok, reason = updater.canInstall(_MODULE_DIR)
        self.updateLabel.setText(
            "<b>SegQueue {} is available.</b> You are running {}.{}".format(
                rel.describe(release), __version__,
                "" if ok else "<br><span style='color:#b26500'>{}</span>".format(reason)))
        self.updateButton.setEnabled(ok)
        self.updateNotesButton.setEnabled(bool(release.get("html_url")))
        self.updateBanner.setVisible(True)

    def onOpenReleaseNotes(self):
        url = str((self._pendingUpdate or {}).get("html_url") or "")
        if url:
            qt.QDesktopServices.openUrl(qt.QUrl(url))

    def onUpdateNow(self):
        """Download, install, restart. One press, and reversible until the last.

        The order matters. The draft is saved before anything is touched, so the
        worst case -- a failed swap on a machine that then has to be reinstalled
        by hand -- still leaves the annotator's work on disk and their case
        assigned to them.
        """
        release = self._pendingUpdate
        if not release:
            return
        ok, reason = updater.canInstall(_MODULE_DIR)
        if not ok:
            slicer.util.errorDisplay(reason)
            return

        asset = rel.asset_for(release, self._slicerMinorVersion())
        if asset is None:
            slicer.util.errorDisplay(
                "That release has no archive for Slicer {}.".format(
                    self._slicerMinorVersion()))
            return

        openCase = self.logic.assignment is not None if self.logic else False
        if not slicer.util.confirmYesNoDisplay(
                "Install SegQueue {} and restart Slicer?\n\n{}".format(
                    rel.describe(release),
                    "Your draft is saved first, and the case you are on is still "
                    "yours when Slicer comes back."
                    if openCase else
                    "Slicer will restart when the update is installed.")):
            return

        if self.logic is not None:
            self.logic.autosave()

        self.updateProgress.setVisible(True)
        self.updateProgress.setValue(0)
        self.updateButton.setEnabled(False)

        progress = _progressInto(self.updateProgress)

        staging = tempfile.mkdtemp(prefix="segqueue14-download-")
        try:
            with _busy():
                archive = os.path.join(staging, str(asset.get("name") or "SegQueue-update.zip"))
                updater.downloadAsset(asset, archive, progress=progress)
                backup = updater.installArchive(
                    archive, _MODULE_DIR, self._slicerMinorVersion())
        except UpdateError as exc:
            slicer.util.errorDisplay(str(exc))
            return
        except Exception:
            slicer.util.errorDisplay(
                "The update failed:\n\n" + traceback.format_exc()
                + "\n\nNothing has been lost -- your draft is saved and the "
                  "previous version is still installed.")
            return
        finally:
            self.updateProgress.setVisible(False)
            self.updateButton.setEnabled(True)
            shutil.rmtree(staging, ignore_errors=True)

        # The check cache is cleared rather than refreshed: the version this
        # answer was computed for is about to stop being the running version.
        qt.QSettings().remove(_SETTING_UPDATE)
        self.updateBanner.setVisible(False)

        if slicer.util.confirmOkCancelDisplay(
                "SegQueue {} is installed.\n\nSlicer needs to restart to load "
                "it. The previous version was backed up to:\n{}".format(
                    rel.describe(release), backup)):
            self._restartSlicer()

    def _restartSlicer(self):
        for restart in (getattr(slicer.util, "restart", None),
                        getattr(slicer.app, "restart", None)):
            if restart is None:
                continue
            try:
                restart()
                return
            except Exception:
                continue
        slicer.util.infoDisplay(
            "Please close and reopen Slicer to finish the update.")

    # --------------------------------------------------------------- branding

    def enter(self):
        """The module became visible: put our name above the panel, and see
        whether a newer release is out."""
        if self.logic is None:
            return
        self._applyPanelBranding()
        # Deferred so the panel is on screen first: an annotator must never wait
        # on GitHub to see the Get next case button.
        qt.QTimer.singleShot(UPDATE_CHECK_DELAY_MS, self._checkForUpdateQuietly)

    def _logoLabel(self):
        """Slicer's logo label above the module panel, or None."""
        try:
            main = slicer.util.mainWindow()
        except Exception:
            return None
        if main is None:
            return None
        label = main.findChild(qt.QLabel, _LOGO_LABEL_NAME)
        if label is not None:
            return label
        # A renamed or customised build still puts the same widget in the same
        # place, so reach it by role rather than by name.
        dock = main.findChild(qt.QDockWidget, _PANEL_DOCK_NAME)
        widget = dock.titleBarWidget() if dock is not None else None
        return widget if hasattr(widget, "setPixmap") else None

    def _applyPanelBranding(self):
        """Swap the Slicer logo for the Bradensbay wordmark.

        The wordmark only -- no mark. The mark is already the module's icon in
        the selector immediately below, and stacking the two reads as two
        separate pieces of branding rather than one.
        """
        label = self._logoLabel()
        if label is None:
            return
        if self._slicerLogo is None:
            try:
                # Copied, not referenced: the label owns the pixmap it is
                # showing, and it is about to be showing a different one.
                self._slicerLogo = qt.QPixmap(label.pixmap)
            except Exception:
                self._slicerLogo = qt.QPixmap()
        wordmark = self._wordmarkPixmap()
        if wordmark is None:
            return
        label.setPixmap(wordmark)
        label.setToolTip("SegQueue14 {} -- Bradensbay".format(__version__))

    def _restorePanelBranding(self):
        """Give Slicer its logo back, on the way out of the module."""
        label = self._logoLabel()
        if label is None or self._slicerLogo is None:
            return
        try:
            if self._slicerLogo.isNull():
                label.clear()
            else:
                label.setPixmap(self._slicerLogo)
            label.setToolTip("")
        except Exception:
            pass

    def _wordmarkPixmap(self):
        """The wordmark for the current theme, scaled to the logo it replaces.

        Matching the original's pixel height and device pixel ratio is what
        keeps the title bar from changing size as the annotator moves between
        modules. Two assets rather than one recoloured: on a dark background the
        wordmark is white, not a lightened navy.
        """
        dark = False
        try:
            dark = slicer.app.palette().color(qt.QPalette.Window).lightness() < 128
        except Exception:
            pass
        path = os.path.join(_RESOURCES, "Icons",
                            "wordmark-dark.png" if dark else "wordmark-light.png")
        if not os.path.isfile(path):
            return None
        pixmap = qt.QPixmap(path)
        if pixmap.isNull():
            return None

        height, ratio = 0, 1.0
        original = self._slicerLogo
        if original is not None and not original.isNull():
            height = int(original.height())
            try:
                ratio = float(original.devicePixelRatio()) or 1.0
            except Exception:
                ratio = 1.0
        if height <= 0:
            # No logo to measure -- a customised build, or Qt handed back
            # nothing. 24 device pixels is the height Slicer's own logo uses.
            height, ratio = 24, 1.0

        pixmap = pixmap.scaledToHeight(height, qt.Qt.SmoothTransformation)
        try:
            pixmap.setDevicePixelRatio(ratio)
        except Exception:
            pass
        return pixmap

    def _buildLoginSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Server"
        self.layout.addWidget(box)
        form = qt.QFormLayout(box)
        self.loginBox = box

        self.serverEdit = qt.QLineEdit(
            slicer.util.settingsValue(
                _SETTING_SERVER,
                slicer.util.settingsValue(_LIVE_SETTING_SERVER,
                                          "https://segqueue.example.edu")))
        self.serverEdit.setToolTip(
            "Base URL of the server (the same one as SegQueue). /api/v1 is added "
            "automatically; SegQueue14 uses its own /segqueue14 routes on it.")
        form.addRow("Server:", self.serverEdit)

        # Deliberately empty, and never pre-filled from settings: see
        # _SETTING_LEGACY_USER. Whoever is sitting here types who they are.
        self.userEdit = qt.QLineEdit()
        self.userEdit.setPlaceholderText("Your username")
        self.userEdit.setToolTip(
            "Not saved. Type it each session, so submissions are always "
            "attributed to whoever is actually at this machine.")
        self.userEdit.returnPressed.connect(self.onLogin)
        form.addRow("Username:", self.userEdit)

        self.passwordEdit = qt.QLineEdit()
        self.passwordEdit.setEchoMode(qt.QLineEdit.Password)
        self.passwordEdit.returnPressed.connect(self.onLogin)
        # Never persisted: on a shared machine, a remembered password means
        # every submission is attributed to whoever logged in last.
        self.passwordEdit.setToolTip("Not saved. You log in once per Slicer session.")
        form.addRow("Password:", self.passwordEdit)

        self.loginButton = _primary(qt.QPushButton("Log in"))
        self.loginButton.clicked.connect(self.onLogin)
        # "and purge" was in the label to warn, and warned nobody: it is one
        # click behind a confirmation that spells out exactly what is deleted.
        self.logoutButton = qt.QPushButton("Log out")
        self.logoutButton.setToolTip(
            "Logs out and deletes every locally cached case.")
        self.logoutButton.clicked.connect(self.onLogout)
        row = qt.QHBoxLayout()
        row.addWidget(self.loginButton, 1)
        row.addWidget(self.logoutButton)
        form.addRow(row)

        statusRow = qt.QHBoxLayout()
        # Deliberately not word-wrapped. A wrapping label in a row with a
        # button gets the row's height from its unwrapped size hint, so the
        # second line was drawn below the row and clipped. It is kept short
        # instead, with the long form in the tooltip.
        self.statusLabel = qt.QLabel("Not logged in.")
        statusRow.addWidget(self.statusLabel, 1)
        # As in the live module: beside the status line, because "am I on the
        # current version?" is asked when there is no update banner.
        self.checkUpdateButton = _link(qt.QPushButton("Check for updates"))
        self.checkUpdateButton.setToolTip(
            "Asks GitHub whether a newer SegQueue14 has been published. Runs "
            "automatically when you open the module, at most a few times a day.")
        self.checkUpdateButton.clicked.connect(self.onCheckForUpdates)
        statusRow.addWidget(self.checkUpdateButton)
        form.addRow(statusRow)

    def _buildCaseSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Case"
        self.layout.addWidget(box)
        layout = qt.QVBoxLayout(box)
        self.caseBox = box

        layout.setSpacing(8)

        self.nextButton = _primary(qt.QPushButton("Get next case"))
        self.nextButton.setToolTip(
            "Ask the server for your next assignment and download it.")
        self.nextButton.clicked.connect(self.onNextCase)
        layout.addWidget(self.nextButton)

        # Which case, and how long it has taken, on one line. They were two
        # rows with the notes box between them, which put the clock nowhere
        # near the case it was timing.
        headerRow = qt.QHBoxLayout()
        self.caseLabel = qt.QLabel("No case open.")
        self.caseLabel.setWordWrap(True)
        headerRow.addWidget(self.caseLabel, 1)

        self.timerLabel = _muted(qt.QLabel("--"))
        self.timerLabel.setToolTip("Time spent on the case that is open.")
        headerRow.addWidget(self.timerLabel)
        layout.addLayout(headerRow)

        # Only shown for rework, and now a tinted line rather than the framed
        # group box it used to be: the comment is a sentence, and a titled box
        # around one sentence took more of the panel than the sentence did.
        self.reworkLabel = _tint(qt.QLabel(), "warn")
        self.reworkLabel.setWordWrap(True)
        self.reworkLabel.setVisible(False)
        layout.addWidget(self.reworkLabel)

        self.notesBox = qt.QGroupBox("Case notes")
        notesLayout = qt.QVBoxLayout(self.notesBox)
        notesLayout.setContentsMargins(8, 6, 8, 6)
        notesLayout.setSpacing(6)

        self.notesBrowser = qt.QTextBrowser()
        self.notesBrowser.setMaximumHeight(150)
        self.notesBrowser.setOpenExternalLinks(True)
        # No frame: it is already inside the group box's frame, and two
        # nested borders is what made this corner of the panel look busiest.
        self.notesBrowser.setFrameShape(qt.QFrame.NoFrame)
        notesLayout.addWidget(self.notesBrowser)

        noteRow = qt.QHBoxLayout()
        self.noteInput = qt.QLineEdit()
        self.noteInput.setPlaceholderText(
            "Something the next person should know about this case")
        self.noteInput.setToolTip(
            "Everyone who works on this case sees this, with your name on it. "
            "Notes cannot be edited or deleted once posted. Your unposted text "
            "is saved with the case, so closing Slicer does not lose it, and "
            "goes to the reviewer with the case when you submit.")
        self.noteInput.setMaxLength(protocol.NOTE_MAX_CHARS)
        self.noteInput.returnPressed.connect(self.onPostNote)
        noteRow.addWidget(self.noteInput, 1)

        self.postNoteButton = qt.QPushButton("Post")
        self.postNoteButton.setToolTip(
            "Adds this to the thread now, for whoever opens the case next.")
        self.postNoteButton.clicked.connect(self.onPostNote)
        noteRow.addWidget(self.postNoteButton)
        notesLayout.addLayout(noteRow)

        layout.addWidget(self.notesBox)
        self._renderNotes([])

        self.progressBar = qt.QProgressBar()
        self.progressBar.setVisible(False)
        layout.addWidget(self.progressBar)

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

        layout.setSpacing(8)

        # There is no note box here any more. There were two -- one in "Case
        # notes" for the thread and one here for the reviewer -- so writing a
        # sentence meant first deciding which of them it belonged in, and it
        # was written in whichever happened to be nearer. One box now, in
        # "Case notes", and whatever is still typed in it when the case is
        # submitted travels with the submission too.
        self.submitButton = _primary(qt.QPushButton("Submit case"))
        self.submitButton.setToolTip(
            "Uploads the segmentation and deletes the local copy. Anything "
            "typed in 'Case notes' goes with it, for the reviewer.")
        self.submitButton.clicked.connect(self.onSubmit)
        layout.addWidget(self.submitButton)

        row = qt.QHBoxLayout()
        self.saveButton = qt.QPushButton("Save draft")
        self.saveButton.setToolTip(
            "Drafts also save automatically every {} minutes.".format(
                AUTOSAVE_SECONDS // 60))
        self.saveButton.clicked.connect(self.onSaveDraft)
        row.addWidget(self.saveButton)

        self.releaseButton = qt.QPushButton("Give this case back")
        self.releaseButton.setToolTip(
            "Returns the case to the pool for someone else. Your work on it is "
            "discarded.")
        self.releaseButton.clicked.connect(self.onRelease)
        row.addWidget(self.releaseButton)
        layout.addLayout(row)

        # Named for what it says now. It was "problemsLabel" and carried the
        # validation findings; those are gone, and all it reports is whether
        # the draft went to disk.
        self.saveStatusLabel = _muted(qt.QLabel())
        self.saveStatusLabel.setWordWrap(True)
        layout.addWidget(self.saveStatusLabel)

    def _buildReviewSection(self):
        """The submission viewer: every case, what happened to it, and what to do.

        It replaced a review *queue*, which showed only the sampled fraction
        awaiting a verdict and could not answer the question reviewers actually
        arrive with -- where is case s0042, and who has it. So this lists every
        case in the project, assigned or not, submitted or not, finished or not.

        Two tables rather than one. The top one is cases; selecting a case fills
        the bottom one with every submission ever made against it, because
        submissions are append-only and "what did they send the first time?" is
        a question worth being able to answer months later.
        """
        box = ctk.ctkCollapsibleButton()
        box.text = "Submissions"
        box.collapsed = True
        # Hidden until the server confirms the role, so an annotator never sees
        # a section that would only ever tell them they are not allowed.
        box.setVisible(False)
        self.layout.addWidget(box)
        self.reviewBox = box
        layout = qt.QVBoxLayout(box)
        layout.setSpacing(8)

        # The filter first and wide, the refresh after it: choosing what to
        # look at is the thing done on arrival, and reloading is the thing
        # done when in doubt.
        controls = qt.QHBoxLayout()
        self.reviewFilter = qt.QComboBox()
        # The order is the lifecycle, so the list reads as a progression rather
        # than as an alphabetised set of jargon.
        self.reviewFilter.addItem("All cases", "")
        self.reviewFilter.addItem("Unassigned", "unassigned")
        for state, label in REVIEW_FILTERS:
            self.reviewFilter.addItem(label, state)
        self.reviewFilter.setToolTip(
            "Narrow the list to cases with an assignment in one state. "
            "'Unassigned' is the cases nobody has been given yet.")
        self.reviewFilter.currentIndexChanged.connect(
            lambda _index: self.onRefreshReview())
        controls.addWidget(self.reviewFilter, 1)

        self.refreshReviewButton = qt.QPushButton("Refresh")
        self.refreshReviewButton.setToolTip("Reload the case list.")
        self.refreshReviewButton.clicked.connect(self.onRefreshReview)
        controls.addWidget(self.refreshReviewButton)
        layout.addLayout(controls)

        self.reviewTable = qt.QTableWidget()
        # Five columns rather than the original seven, because the dock is
        # narrow and the case name is the one thing every row is looked up
        # by -- it gets whatever width it needs and the rest give way.
        #
        # "Attempt" was a column of its own and read "1" on almost every
        # row; it is a suffix on the state now, and only when it is not the
        # first attempt, which is the only time anybody looks for it.
        # "Flags" held whole sentences -- "mean Dice 0.62 against the
        # reference" -- in forty pixels, so it was never once readable. It
        # is a mark against the state and the sentence in the row's tooltip.
        self.reviewTable.setColumnCount(5)
        self.reviewTable.setHorizontalHeaderLabels(
            ["Case", "Annotator", "State", "Submitted", "#"])
        # "#" rather than "Subs": the column holds a single digit, and the word
        # was forty pixels wide to label it -- forty the case name wanted.
        header = self.reviewTable.horizontalHeaderItem(4)
        if header is not None:
            header.setToolTip("How many submissions have been made on this case.")
        _tidyTable(self.reviewTable, [104, 70, 110, 78, 26], 190)
        self.reviewTable.itemSelectionChanged.connect(self.onReviewRowChanged)
        layout.addWidget(self.reviewTable)

        layout.addWidget(_caption(
            "Every submission against the selected case, oldest first. Nothing "
            "is ever overwritten, so a superseded attempt is still here."))
        self.historyTable = qt.QTableWidget()
        self.historyTable.setColumnCount(5)
        self.historyTable.setHorizontalHeaderLabels(
            ["When", "Author", "Role", "Attempt", "Dice"])
        _tidyTable(self.historyTable, [112, 72, 62, 48, 50], 110)
        layout.addWidget(self.historyTable)

        openRow = qt.QHBoxLayout()
        self.openReviewButton = _primary(qt.QPushButton("Open submission"))
        self.openReviewButton.setToolTip(
            "Loads the volume and that segmentation into the scene. Picks the "
            "highlighted row in the history table, or the case's latest "
            "submission if none is highlighted.")
        self.openReviewButton.clicked.connect(self.onOpenReview)
        openRow.addWidget(self.openReviewButton, 1)

        self.openCaseButton = qt.QPushButton("Image only")
        self.openCaseButton.setToolTip(
            "Loads the case's own volume and whatever masks ship with it. For a "
            "case nobody has worked on there is no submission to open, and the "
            "image is what says whether the scan is usable at all.")
        self.openCaseButton.clicked.connect(self.onOpenCase)
        openRow.addWidget(self.openCaseButton)

        self.takeCaseButton = qt.QPushButton("Take && segment")
        self.takeCaseButton.setToolTip(
            "Assigns the selected case to you and opens it as an ordinary case, "
            "so you can segment and submit it yourself. It becomes genuinely "
            "yours: it shows in your queue and is reviewed like any other.")
        self.takeCaseButton.clicked.connect(self.onTakeCase)
        openRow.addWidget(self.takeCaseButton)
        layout.addLayout(openRow)

        self.referenceButton = qt.QPushButton("Show ImageCAS-X reference")
        self.referenceButton.setToolTip(
            "Loads the case's ImageCAS-X segmentation beside what is open, as "
            "outlines in its own segmentation, to see what the automatic score "
            "was measured against.")
        self.referenceButton.clicked.connect(self.onShowReference)
        layout.addWidget(self.referenceButton)

        self.reviewStatusLabel = qt.QLabel()
        self.reviewStatusLabel.setWordWrap(True)
        layout.addWidget(self.reviewStatusLabel)

        # -- deciding
        #
        # Three verdict buttons, a comment box and the assignment controls
        # used to run down the panel as one column of equally-weighted rows,
        # which gave no clue that the first three act on the submission that
        # is open and the last acts on the row that is selected. They are two
        # groups, so they are drawn as two, each under what it operates on.
        layout.addWidget(_separator())
        layout.addWidget(_caption(
            "What to do with the submission that is open."))

        self.verdictComment = qt.QLineEdit()
        self.verdictComment.setPlaceholderText(
            "optional note for the case thread")
        layout.addWidget(self.verdictComment)

        row = qt.QHBoxLayout()
        self.approveButton = qt.QPushButton("Approve")
        self.approveButton.setToolTip(
            "Accept this submission as it stands. Approval is the only state "
            "the training export selects.")
        self.approveButton.clicked.connect(lambda: self.onVerdict("approve"))
        row.addWidget(self.approveButton)

        self.reviseButton = qt.QPushButton("Save changes && approve")
        self.reviseButton.setToolTip(
            "Upload what is now in the scene as your own corrected version and "
            "approve it. The annotator's submission is kept exactly as they "
            "sent it; yours is stored beside it, credited to you.")
        self.reviseButton.clicked.connect(self.onReviseSubmission)
        row.addWidget(self.reviseButton)

        self.poolButton = qt.QPushButton("Return to pool")
        self.poolButton.setToolTip(
            "Give the case back to the pool for another annotator. The "
            "submission stays on record.")
        self.poolButton.clicked.connect(self.onReturnToPool)
        row.addWidget(self.poolButton)
        layout.addLayout(row)

        # -- handing work out
        layout.addWidget(_separator())
        layout.addWidget(_caption(
            "Give the selected case to someone. The count beside each name is "
            "what they are already holding."))
        assignRow = qt.QHBoxLayout()
        self.annotatorCombo = qt.QComboBox()
        self.annotatorCombo.setToolTip(
            "Annotators, with how many cases each has open. Refreshed with the "
            "case list.")
        assignRow.addWidget(self.annotatorCombo, 1)

        self.assignButton = qt.QPushButton("Assign case")
        self.assignButton.setToolTip(
            "Hands the selected case to the chosen annotator straight away, "
            "without waiting for them to ask for one. Refused if the case is "
            "retired, already out, or has been theirs before.")
        self.assignButton.clicked.connect(self.onAssignCase)
        assignRow.addWidget(self.assignButton)
        layout.addLayout(assignRow)

    # ------------------------------------------------------ submission viewer

    def onRefreshReview(self):
        """Reload the case list. Cheap enough to be the answer to most doubts."""
        if self.logic is None or self.logic.client is None:
            return
        selected = self.reviewFilter.itemData(self.reviewFilter.currentIndex)
        with _busy():
            try:
                # Every case, not the first page: a thousand-case project
                # would otherwise show its first two hundred and look complete.
                self._reviewCases = self.logic.client.allCases(
                    state=None if selected in ("", "unassigned") else selected,
                    unassigned=(selected == "unassigned"))
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return

        # One row per *assignment*, not per case: a case can be out with two
        # annotators at once, and each of them has their own state to show. A
        # case nobody holds still gets a row, because "nothing has happened to
        # this one" is the most useful thing the viewer can say about it.
        self._reviewRows = []
        for case in self._reviewCases:
            assignments = case.get("assignments") or []
            if not assignments:
                self._reviewRows.append((case, None))
                continue
            for assignment in assignments:
                self._reviewRows.append((case, assignment))

        self.reviewTable.setRowCount(len(self._reviewRows))
        for index, (case, assignment) in enumerate(self._reviewRows):
            assignment = assignment or {}
            attempt = assignment.get("attempt")
            state = assignment.get("state", "") or "unassigned"
            try:
                if int(attempt) > 1:
                    state = "{} #{}".format(state, int(attempt))
            except (TypeError, ValueError):
                pass
            flagged = assignment.get("flagged") or []
            if flagged:
                state = "\u26a0 " + state
            cells = [
                case.get("caseName", ""),
                assignment.get("annotator", "") or "--",
                state,
                # The date only. The minute matters when two attempts on one
                # case are being compared, which is what the history table is
                # for; here it is a thousand rows being scanned for "when was
                # this last touched", and the time cost a column of width.
                _shortTime(assignment.get("submittedAt"))[:10],
                str(assignment.get("submissionCount", 0)),
            ]
            # One tooltip for the whole row: the flags are sentences, and a
            # reviewer who sees the mark wants them wherever they point.
            tip = "\n".join(flagged)
            for column, text in enumerate(cells):
                item = qt.QTableWidgetItem(text)
                if column == 3:
                    item.setToolTip(_shortTime(assignment.get("submittedAt"))
                                    or tip)
                elif tip:
                    item.setToolTip(tip)
                self.reviewTable.setItem(index, column, item)
        # No resizeColumnsToContents: it measures every row of every column,
        # and this table is the whole project. Only the case name is sized to
        # its contents, because it is what every row is looked up by and the
        # names differ between projects -- `s0042` in one, `imagecas_0001` in
        # this one, and a width that suits the first clips the second.
        _fitColumn(self.reviewTable, 0,
                   [case.get("caseName", "") for case in self._reviewCases],
                   floor=70, ceiling=150)
        self._refreshAnnotators()
        self._clearHistory()
        self._updateReviewEnabled()

    def onReviewRowChanged(self):
        """Fill the history table for whichever case is selected."""
        case, _assignment = self._selectedReviewRow()
        if case is None:
            self._clearHistory()
            self._updateReviewEnabled()
            return
        with _busy():
            try:
                self._historyRows = self.logic.client.caseSubmissions(case["caseId"])
            except SegQueueError as exc:
                self._historyRows = []
                self.reviewStatusLabel.setText(_escape(str(exc)))

        self.historyTable.setRowCount(len(self._historyRows))
        for index, entry in enumerate(self._historyRows):
            score = (entry.get("autoScore") or {}).get("mean_dice")
            cells = [
                _shortTime(entry.get("created")),
                (entry.get("annotator") or {}).get("login", ""),
                entry.get("authorRole", "annotator"),
                str(entry.get("attempt", 1)),
                "--" if score is None else "{:.3f}".format(score),
            ]
            perClass = (entry.get("autoScore") or {}).get("per_class_dice") or {}
            tip = "\n".join("{}: {}".format(name, "--" if dice is None else
                                             "{:.2f}".format(dice))
                            for name, dice in perClass.items())
            if entry.get("prelabelVersion"):
                tip = "prelabel {}\n{}".format(entry["prelabelVersion"], tip)
            for column, text in enumerate(cells):
                item = qt.QTableWidgetItem(text)
                if tip:
                    item.setToolTip(tip)
                self.historyTable.setItem(index, column, item)
        self._updateReviewEnabled()

    def _clearHistory(self):
        self._historyRows = []
        self.historyTable.setRowCount(0)

    def _selectedReviewRow(self):
        row = self.reviewTable.currentRow()
        if row < 0 or row >= len(self._reviewRows):
            return None, None
        return self._reviewRows[row]

    def _selectedSubmission(self):
        """The submission to act on: the highlighted history row, else the latest.

        Defaulting to the latest is what makes the common path one click. Being
        able to pick an older row is what makes the history worth showing at all
        -- comparing an attempt against what replaced it is most of why a
        reviewer opens this.
        """
        row = self.historyTable.currentRow()
        if 0 <= row < len(self._historyRows):
            return self._historyRows[row]
        _case, assignment = self._selectedReviewRow()
        if assignment and assignment.get("submissionId"):
            return next((e for e in self._historyRows
                         if e.get("submissionId") == assignment["submissionId"]),
                        None) or {"submissionId": assignment["submissionId"]}
        return None

    def _updateReviewEnabled(self):
        submission = self._selectedSubmission()
        _case, assignment = self._selectedReviewRow()
        state = (assignment or {}).get("state", "")
        hasSubmission = bool(submission and submission.get("submissionId"))
        decided = state in REVIEW_DECIDED_STATES

        self.openReviewButton.setEnabled(hasSubmission)
        # A case with no submission can still be opened and still be handed out.
        self.openCaseButton.setEnabled(_case is not None)
        # Taking a case needs a free hand: holding one already is what the
        # concurrency limit exists to prevent.
        self.takeCaseButton.setEnabled(
            _case is not None and self.logic is not None
            and self.logic.assignment is None)
        self.assignButton.setEnabled(
            _case is not None and self.annotatorCombo.count > 0)
        self.referenceButton.setEnabled(
            _case is not None and self.logic is not None
            and self.logic.volumeNode is not None)
        self.approveButton.setEnabled(hasSubmission and not decided)
        self.poolButton.setEnabled(hasSubmission and not decided)
        # Revising uploads whatever is in the scene, so it needs an opened
        # submission as well as an undecided one -- otherwise the obvious
        # accident is approving the previous case's segmentation onto this one.
        self.reviseButton.setEnabled(
            bool(self._claimedSubmission) and hasSubmission and not decided)

    def _reviewPaths(self, entry):
        """``(volumePath, segPath)`` named after what the files actually are.

        The whole bug this method exists for: Slicer chooses its reader from the
        extension, and these volumes are ``.nii.gz``. Written as ``volume.nrrd``
        they download, verify and then fail to open with a message that never
        mentions the name -- which is precisely what "the review does not load"
        was. The server sends the real names; where it is too old to, the bytes
        get sniffed after the download (``SegQueue14Logic.correctSuffix``).
        """
        directory = self.logic.reviewDir()
        return (os.path.join(directory, _safeName(entry.get("volumeName"),
                                                  "volume.nrrd")),
                os.path.join(directory, _safeName(entry.get("submissionName"),
                                                  "submission.seg.nrrd")))

    def onOpenReview(self):
        """Load a submission into the scene, whichever one is selected."""
        entry = self._selectedSubmission()
        if not entry or not entry.get("submissionId"):
            slicer.util.errorDisplay("Select a submission first.")
            return
        if self.logic.assignment is not None:
            slicer.util.errorDisplay(
                "You have a case of your own open. Submit it or give it back "
                "before reviewing -- opening a submission clears the scene.")
            return
        submissionId = entry["submissionId"]

        with _busy():
            volumePath, segPath = self._reviewPaths(entry)
            try:
                self.logic.client.downloadReviewFile(
                    submissionId, "volume", volumePath)
                self.logic.client.downloadReviewFile(
                    submissionId, "download", segPath)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return

            # Last line of defence on the name, for a server too old to send it.
            volumePath = self.logic.correctSuffix(volumePath)

            slicer.mrmlScene.Clear(False)
            try:
                volumeNode = slicer.util.loadVolume(volumePath)
                segmentationNode = slicer.util.loadSegmentation(segPath)
            except Exception:
                slicer.util.errorDisplay(
                    "The submission downloaded but Slicer could not open it:\n\n"
                    + traceback.format_exc())
                return
            slicer.util.setSliceViewerLayers(background=volumeNode, fit=True)
            self.logic.volumeNode = volumeNode
            self.logic.segmentationNode = segmentationNode
            # A submission is stored as a labelmap, so it comes back as
            # Segment_1, Segment_2 ... in colours Slicer chose. The label values
            # are the protocol's, which is enough to put the names back.
            self.logic.applyProjectNames()
            self.logic.applyViewPreset()
            self._bindEditor(segmentationNode, volumeNode)
            slicer.app.layoutManager().setLayout(
                slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
            # Built and shown before centring, not after: the camera is fitted to
            # the bounds of the actors in the renderer, so centring an empty 3D
            # view frames nothing and the submission opens off screen.
            self.logic.showSubmissionIn3d()
            self.logic.centre3d()

        self._claimedSubmission = submissionId
        self._reviewStart = time.time()
        self.reviewStatusLabel.setText(
            "Reviewing <b>{}</b> by {} — edit it in the Segment Editor if you "
            "want to correct it.".format(
                _escape(entry.get("caseName", "")),
                _escape((entry.get("annotator") or {}).get("login", ""))))
        self.editorBox.collapsed = False
        self._updateReviewEnabled()
        # The Segment Editor is enabled by whether there is something to edit,
        # which during a review is the submission rather than an assignment.
        self._updateEnabled()

    def _refreshAnnotators(self):
        """Fill the picker with who can be given a case, and what they hold.

        The holding count is the whole reason this is a list rather than a text
        box: handing out a thousand cases without it means handing most of them
        to whoever is top of the alphabet.
        """
        current = self.annotatorCombo.currentText
        try:
            self._annotators = self.logic.client.annotators()
        except SegQueueError:
            # Not fatal: the rest of the viewer works, and this only costs the
            # ability to hand work out until the next refresh.
            self._annotators = []

        self.annotatorCombo.clear()
        for person in self._annotators:
            if person.get("disabled"):
                continue
            label = "{}  ({} open)".format(person.get("login", "?"),
                                           person.get("openCases", 0))
            quota = person.get("quota")
            if quota is not None:
                label += ", quota {}".format(quota)
            self.annotatorCombo.addItem(label, person.get("userId"))
        index = self.annotatorCombo.findText(current)
        if index >= 0:
            self.annotatorCombo.setCurrentIndex(index)

    def onAssignCase(self):
        """Hand the selected case to the chosen annotator."""
        case, _assignment = self._selectedReviewRow()
        if case is None:
            slicer.util.errorDisplay("Select a case first.")
            return
        userId = self.annotatorCombo.itemData(self.annotatorCombo.currentIndex)
        who = self.annotatorCombo.currentText.split("  (")[0]
        if not userId:
            slicer.util.errorDisplay(
                "There is nobody to assign to. Check the annotator group has "
                "members.")
            return
        if not slicer.util.confirmYesNoDisplay(
                "Give {} to {}?".format(case.get("caseName", "this case"), who)):
            return

        with _busy():
            try:
                self.logic.client.assignCase(case["caseId"], userId)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
        self.reviewStatusLabel.setText(
            "Assigned <b>{}</b> to {}.".format(
                _escape(case.get("caseName", "")), _escape(who)))
        self.onRefreshReview()

    def onOpenCase(self):
        """Load a case's own volume, for one with no submission to open.

        A case nobody has worked on has nothing in the history table, so the
        submission path has nothing to download. Looking at the image before
        deciding who should get it is most of why a reviewer opens a case at
        all, and it is the only way to tell a usable scan from a broken one.
        """
        case, _assignment = self._selectedReviewRow()
        if case is None:
            slicer.util.errorDisplay("Select a case first.")
            return
        if self.logic.assignment is not None:
            slicer.util.errorDisplay(
                "You have a case of your own open. Submit it or give it back "
                "first -- opening a case clears the scene.")
            return

        directory = self.logic.reviewDir()
        volumePath = os.path.join(
            directory, _safeName(case.get("volumeName"), "case.nrrd"))

        with _busy():
            try:
                self.logic.client.downloadCaseVolume(case["caseId"], volumePath)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
            volumePath = self.logic.correctSuffix(volumePath)

            slicer.mrmlScene.Clear(False)
            try:
                volumeNode = slicer.util.loadVolume(volumePath)
            except Exception:
                slicer.util.errorDisplay(
                    "The case downloaded but Slicer could not open it:\n\n"
                    + traceback.format_exc())
                return

            self.logic.volumeNode = volumeNode
            self.logic.segmentationNode = None
            slicer.util.setSliceViewerLayers(background=volumeNode, fit=True)
            self.logic.applyViewPreset()

            # The masks that ship with the case, when it has them. They are what
            # makes the 3D view worth looking at before anyone has segmented
            # anything -- and whether a case has a usable coronary mask is
            # exactly what decides how long it will take whoever gets it.
            self._loadCaseHelpers(case, directory)

            slicer.app.layoutManager().setLayout(
                slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
            self.logic.centre3d()

        self._claimedSubmission = None
        self.reviewStatusLabel.setText(
            "Viewing <b>{}</b> — no submission on it yet.".format(
                _escape(case.get("caseName", ""))))
        self._updateEnabled()
        self._updateReviewEnabled()

    def onTakeCase(self):
        """Assign the selected case to yourself and open it as a case.

        A reviewer looking at an unassigned case often wants to *do* it -- a
        tricky one, a demonstration, or simply the last few nobody picked up.

        Deliberately routed through an ordinary assignment rather than a
        reviewer-only way to submit. Everything that makes a submission correct
        hangs off having one: the project's segments created with the right names
        and label values, the branches started from the coronary mask, the
        autosave, the elapsed-time record, the overlap check, and the upload the
        server will accept. A second path to submitting would have to reproduce
        all of that, and would drift from it.

        So the case becomes genuinely theirs -- it shows in their queue, counts
        against their quota, and is submitted and reviewed like any other.
        """
        case, _assignment = self._selectedReviewRow()
        if case is None:
            slicer.util.errorDisplay("Select a case first.")
            return
        if self.logic.assignment is not None:
            slicer.util.errorDisplay(
                "Finish or give back the case you already have before taking "
                "another one.")
            return
        if case.get("assignments"):
            # Not a hard refusal: a case can want a second annotator. But taking
            # one somebody is already working on is much more often a misclick
            # than a decision, so it is worth one sentence.
            if not slicer.util.confirmYesNoDisplay(
                    "{} is already out with {}.\n\nTake it as well?".format(
                        case.get("caseName", "This case"),
                        ", ".join(sorted({a.get("annotator", "?")
                                          for a in case["assignments"]})))):
                return
        elif not slicer.util.confirmYesNoDisplay(
                "Take {} and start segmenting it yourself?".format(
                    case.get("caseName", "this case"))):
            return

        with _busy():
            try:
                me = self.logic.client.whoami() or {}
                myId = me.get("_id")
                if not myId:
                    slicer.util.errorDisplay("The server did not say who you are.")
                    return
                self.logic.client.assignCase(case["caseId"], myId)
                assignment = next(
                    (a for a in self.logic.outstanding()
                     if a.case_id == case["caseId"]), None)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return

        if assignment is None:
            slicer.util.errorDisplay(
                "The case was assigned to you but did not come back in your "
                "list. Press 'Get next case' to pick it up.")
            self.onRefreshReview()
            return

        self.reviewStatusLabel.setText(
            "Took <b>{}</b> — it is yours now, and submits like any other "
            "case.".format(_escape(case.get("caseName", ""))))
        self._openAssignment(assignment)
        self.onRefreshReview()

    def _loadCaseHelpers(self, case, directory):
        """Bring in the case's heart mask and its prelabel, if it has them.

        For a reviewer opening a case nobody has submitted: the prelabel is what
        whoever gets the case will start from, which is most of what decides how
        long it will take them.
        """
        if self.logic.segmentationNode is None:
            self.logic.segmentationNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLSegmentationNode", "Case masks")
            self.logic.segmentationNode.CreateDefaultDisplayNodes()
            self.logic.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(
                self.logic.volumeNode)

        self.logic.seedSegmentId = None
        path = os.path.join(directory, "case_seed.nii.gz")
        try:
            got = self.logic.client.downloadCaseAsset(
                case["caseId"], protocol.ASSET_SEED, path)
        except SegQueueError:
            got = None
        if got:
            self.logic.seedSegmentId = self.logic._importHelper(
                path, protocol.SEED_SEGMENT_NAME, SEED_COLOR, SEED_FILL)

        self.logic.regionSegmentId = None
        path = os.path.join(directory, "case_region.nii.gz")
        try:
            got = self.logic.client.downloadCaseAsset(
                case["caseId"], protocol.ASSET_REGION, path)
        except SegQueueError:
            got = None
        if got:
            self.logic.regionSegmentId = self.logic._importHelper(
                path, protocol.REGION_SEGMENT_NAME, REGION_COLOR, REGION_FILL)

        path = os.path.join(directory, "case_prelabel.nii.gz")
        try:
            got = self.logic.client.downloadCaseAsset(
                case["caseId"], protocol.ASSET_PRELABEL, path)
        except SegQueueError:
            got = None
        if got:
            try:
                self.logic.importLabelsIntoProject(path)
            except Exception:
                pass
        self.logic.showPrelabelIn3d(True)

    def onShowReference(self):
        """Load the ImageCAS-X reference for the open case, for comparison.

        Reviewer-only on the server. Loaded into its own segmentation node, with
        a prefix on every name, so it can never be mistaken for -- or exported
        as -- the read being reviewed.
        """
        case, _assignment = self._selectedReviewRow()
        if case is None or self.logic.volumeNode is None:
            slicer.util.errorDisplay("Open a case or a submission first.")
            return
        directory = self.logic.reviewDir()
        path = os.path.join(directory, "case_reference.nii.gz")
        with _busy():
            try:
                got = self.logic.client.downloadCaseAsset(
                    case["caseId"], protocol.ASSET_REFERENCE, path)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
            if not got:
                slicer.util.infoDisplay("This case has no ImageCAS-X reference.")
                return
            node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLSegmentationNode", "ImageCAS-X reference (not submitted)")
            node.CreateDefaultDisplayNodes()
            node.SetReferenceImageGeometryParameterFromVolumeNode(self.logic.volumeNode)
            self.logic.importLabelsIntoProject(path, segmentationNode=node, icx14=True)
            segmentation = node.GetSegmentation()
            for i in range(segmentation.GetNumberOfSegments()):
                segment = segmentation.GetSegment(segmentation.GetNthSegmentID(i))
                segment.SetName(protocol.REFERENCE_SEGMENT_PREFIX + segment.GetName())
            display = node.GetDisplayNode()
            if display is not None:
                display.SetVisibility2DFill(False)
        self.reviewStatusLabel.setText(
            "ImageCAS-X reference loaded as its own segmentation (outlines only).")

    def _prelabelText(self, assignment):
        if not assignment.has_prelabel and assignment.has_seed:
            if self.logic is not None and self.logic.resumedDraft:
                return " · your draft"
            return (" · <i>each class starts as the whole seed (hidden): show one "
                    "at a time and cut it down</i>")
        if not assignment.has_prelabel:
            return " · <i>no prelabel: draw from scratch</i>"
        filled = self.logic.prelabelClasses if self.logic else 0
        if self.logic is not None and self.logic.resumedDraft:
            return " · your draft"
        return " · prelabel {} ({} classes)".format(
            _escape(assignment.prelabel_version or "?"), filled)

    def onReviseSubmission(self):
        """Upload what is in the scene as the reviewer's own version, and approve."""
        if not self._claimedSubmission:
            slicer.util.errorDisplay("Open a submission first.")
            return
        if self.logic.segmentationNode is None:
            slicer.util.errorDisplay("There is no segmentation in the scene.")
            return
        if not slicer.util.confirmYesNoDisplay(
                "Save what is in the scene as your own corrected version and "
                "approve this case?\n\nThe annotator's submission is kept "
                "exactly as they sent it."):
            return

        seconds = (time.time() - self._reviewStart) if self._reviewStart else None
        with _busy():
            try:
                self.logic.reviseSubmission(
                    self._claimedSubmission,
                    note=self.verdictComment.text.strip(), seconds=seconds)
            except (SegQueueError, RuntimeError) as exc:
                slicer.util.errorDisplay(str(exc))
                return
            except Exception:
                slicer.util.errorDisplay(
                    "Could not save the revision:\n\n" + traceback.format_exc())
                return

        self._claimedSubmission = None
        self.reviewStatusLabel.setText(
            "Saved your version and approved the case.")
        self.verdictComment.setText("")
        self.onRefreshReview()
        self._updateEnabled()

    def onReturnToPool(self):
        """Give the case back so a different annotator can be handed it."""
        entry = self._selectedSubmission()
        if not entry or not entry.get("submissionId"):
            slicer.util.errorDisplay("Select a submission first.")
            return
        case = _escape(entry.get("caseName", "this case"))
        if not slicer.util.confirmYesNoDisplay(
                "Send {} back to the pool?\n\nThe annotator loses the case and "
                "somebody else will be handed it. Their submission stays on "
                "record.".format(entry.get("caseName", "this case"))):
            return

        with _busy():
            try:
                self.logic.client.returnToPool(
                    entry["submissionId"], reason=self.verdictComment.text.strip())
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return

        if self._claimedSubmission == entry["submissionId"]:
            self._claimedSubmission = None
        self.reviewStatusLabel.setText("Sent {} back to the pool.".format(case))
        self.verdictComment.setText("")
        self.onRefreshReview()
        self._updateEnabled()

    def onVerdict(self, verdict):
        """Approve the selected submission. Approve is the only verdict."""
        entry = self._selectedSubmission()
        if not entry or not entry.get("submissionId"):
            slicer.util.errorDisplay("Select a submission first.")
            return
        seconds = (time.time() - self._reviewStart) if self._reviewStart else None
        with _busy():
            try:
                self.logic.client.submitVerdict(
                    entry["submissionId"], verdict,
                    comment=self.verdictComment.text.strip(),
                    secondsSpent=seconds)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return

        if self._claimedSubmission == entry["submissionId"]:
            self._claimedSubmission = None
        self._reviewStart = None
        self.reviewStatusLabel.setText("Approved {}.".format(
            _escape(entry.get("caseName", "the case"))))
        self.verdictComment.setText("")
        self.onRefreshReview()
        self._updateEnabled()

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

        self.notesTimer = qt.QTimer()
        self.notesTimer.setInterval(NOTES_REFRESH_SECONDS * 1000)
        self.notesTimer.timeout.connect(self.onNotesTimer)
        self.notesTimer.start()

    def cleanup(self):
        """Slicer is closing or the module is being reloaded.

        The last autosave here is the one that saves an annotator who quits
        Slicer without submitting, which is a routine end to a session.
        """
        for timer in (self.autosaveTimer, self.heartbeatTimer, self.clockTimer,
                      self.notesTimer):
            if timer is not None:
                timer.stop()
        self._restorePanelBranding()
        self._saveNoteDraft()
        if self.logic is not None:
            self.logic.autosave()
        if self.editorWidget is not None:
            self.editorWidget.setMRMLScene(None)
        if self.editorNode is not None:
            slicer.mrmlScene.RemoveNode(self.editorNode)
            self.editorNode = None

    def exit(self):
        # Leaving the module for another one should not lose work either, and
        # should not leave our name over somebody else's panel.
        self._restorePanelBranding()
        self._saveNoteDraft()
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

        project = self.logic.project
        login = user.get("login", username)
        quota = ("" if project.quota_remaining is None
                 else "  ·  {} left in quota".format(project.quota_remaining))
        self.statusLabel.setText(login + quota)
        self.statusLabel.setToolTip(
            "Logged in as {}{}".format(
                login,
                "" if project.quota_remaining is None
                else ". {} case(s) left in your quota.".format(
                    project.quota_remaining)))
        self.loginBox.collapsed = True

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
        self._clearNotes()
        self.reworkLabel.setVisible(False)
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

        progress = _progressInto(self.progressBar)

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
            "<b>{}</b> — attempt {}{}{}".format(
                assignment.case_name, assignment.attempt,
                _deadlineText(assignment.deadline),
                self._prelabelText(assignment)))
        self.reworkLabel.setVisible(bool(assignment.reviewer_comment))
        self.reworkLabel.setText(
            "Reviewer asked for changes: {}".format(
                assignment.reviewer_comment or ""))
        self.noteInput.setText(self.logic.noteDraft())
        self.onRefreshNotes()
        self._bindEditor(self.logic.segmentationNode, self.logic.volumeNode)
        # Taking a case ends any review: the scene is this case now.
        self._claimedSubmission = None
        self._reviewStart = None

        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        # The classes go into the 3D view as the case opens: a wrong name is
        # obvious in the tree's shape long before it is in a slice.
        self.logic.showPrelabelIn3d(True)
        self.logic.centre3d()

        self.caseBox.collapsed = False
        # Left open on purpose: it is now the whole interface. Every effect, the
        # masking options and the per-segment eyes all live in there.
        self.editorBox.collapsed = False
        self._updateEnabled()

    def _ensureEditorNode(self):
        """Make sure the editor still has a parameter node that is in the scene.

        ``mrmlScene.Clear`` removes it. It is an ordinary node, not a singleton,
        so clearing the scene to load a submission for review took it with it --
        and the widget was left holding a node the scene no longer had. From
        there every binding is refused ("need to set segment editor and
        segmentation nodes first"), silently, and the segment table stays empty
        however many segments the segmentation actually has. That is precisely
        what a submission opened for review looked like.

        Checked here rather than after the one ``Clear`` that caused it, so that
        any future scene reset is covered by construction instead of by somebody
        remembering.
        """
        if self.editorWidget is None:
            return None
        node = self.editorNode
        # Both conditions: a removed node has its scene reference cleared, and
        # the id lookup catches the case where it was replaced. Checking the id
        # alone would be fooled by a *different* editor node that happened to be
        # given the same id -- which is not exotic, because clearing the scene
        # resets the counter that generates them.
        if (node is not None and node.GetScene() is not None
                and slicer.mrmlScene.GetNodeByID(node.GetID()) is not None):
            return node
        self.editorWidget.setMRMLScene(slicer.mrmlScene)
        self.editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        self.editorWidget.setMRMLSegmentEditorNode(self.editorNode)
        return self.editorNode

    def _bindEditor(self, segmentationNode, volumeNode):
        if self.editorWidget is None:
            return
        # Order matters: the widget refuses a segmentation while its parameter
        # node is missing, and says so only in the application log.
        self._ensureEditorNode()
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

    # -------------------------------------------------------------- actions

    def onSaveDraft(self):
        self._saveNoteDraft()
        if self.logic.autosave():
            self.saveStatusLabel.setText("Draft saved.")
        else:
            self.saveStatusLabel.setText("Nothing to save yet.")

    def onAutosave(self):
        self.logic.autosave()
        self._saveNoteDraft()

    def onHeartbeat(self):
        self.logic.heartbeat()

    def _updateClock(self):
        if self.logic is None or self.logic.assignment is None:
            self.timerLabel.setText("--")
            return
        seconds = int(self.logic.elapsedSeconds())
        self.timerLabel.setText("{:d}:{:02d}:{:02d}".format(
            seconds // 3600, (seconds % 3600) // 60, seconds % 60))

    def onSubmit(self):
        if self.logic.assignment is None:
            slicer.util.errorDisplay("There is no case open.")
            return
        if not slicer.util.confirmYesNoDisplay(
                "Submit '{}'?\n\nThe local copy is deleted once the server has "
                "it.".format(self.logic.assignment.case_name)):
            return

        self.progressBar.setVisible(True)

        progress = _progressInto(self.progressBar)

        with _busy():
            try:
                self.logic.submit(note=self.noteInput.text.strip(),
                                  progress=progress)
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

        self._clearNotes()
        self.saveStatusLabel.setText("")
        self.caseLabel.setText("Submitted. Press 'Get next case' when you are ready.")
        self.reworkLabel.setVisible(False)
        self._bindEditor(None, None)
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
        self._clearNotes()
        self.reworkLabel.setVisible(False)
        self._bindEditor(None, None)
        self._updateEnabled()

    # --------------------------------------------------------------- review

    # ---------------------------------------------------------------- state

    def _updateEnabled(self):
        loggedIn = self.logic is not None and self.logic.loggedIn
        hasCase = loggedIn and self.logic.assignment is not None
        # A reviewer holds no assignment, so gating the Segment Editor on one
        # left them with the submission loaded and the segment list greyed out --
        # which looked like the segments had not loaded at all.
        reviewing = loggedIn and bool(self._claimedSubmission)

        self.loginButton.setEnabled(not loggedIn)
        self.logoutButton.setEnabled(loggedIn)
        self.serverEdit.setEnabled(not loggedIn)
        self.userEdit.setEnabled(not loggedIn)
        self.passwordEdit.setEnabled(not loggedIn)

        self.nextButton.setEnabled(loggedIn and not hasCase)
        for button in (self.saveButton, self.submitButton, self.releaseButton):
            button.setEnabled(hasCase)
        self.editorBox.setEnabled(hasCase or reviewing)
        self.notesBox.setEnabled(hasCase)


def _progressInto(bar):
    """A ``progress(done, total)`` callback that drives ``bar`` and keeps the UI live."""
    def progress(done, total):
        bar.setMaximum(max(1, total))
        bar.setValue(done)
        slicer.app.processEvents()
    return progress


def _deadlineText(deadline):
    if not deadline:
        return ""
    days = (deadline - time.time()) / 86400.0
    if days < 0:
        return "  |  <span style='color:#b00'>overdue</span>"
    return "  |  due in {:.0f} day(s)".format(max(1.0, days))


def _safeName(name, default):
    """A server-supplied filename, reduced to something safe to write.

    Used verbatim rather than rebuilt from a sniffed extension, because the whole
    extension is what matters: ``suffix_for`` maps ``s0042.seg.nrrd`` to
    ``.nrrd``, which loses the ``.seg`` that tells Slicer the file is a
    segmentation rather than a labelmap volume. Taking the basename is what keeps
    a server-supplied string from writing outside the review directory.
    """
    name = os.path.basename((name or "").strip().replace("\\", "/"))
    if not name or name in (".", "..") or name.startswith("."):
        return default
    return name


# Slicer ships a light and a dark theme and the workstations use both, so no
# colour below is a literal. Each is picked from the running palette, which is
# the only thing that knows which theme is on. The panel used to hardcode a
# light-theme grey for its captions and a brown for its warning, and on "Dark
# Slicer" -- what most of the workstations are set to -- both came out very
# nearly the same colour as the background they were drawn on.

_THEMES = {
    "dark": {
        "muted": "#9aa3ad",
        "accent": "#4c9be8",
        "accentHover": "#63aaf0",
        "accentText": "#10171f",
        "warn": "#e8a24c",
        "ok": "#5fb878",
        "line": "#4a515b",
    },
    "light": {
        "muted": "#5a5f66",
        "accent": "#1a6fb5",
        "accentHover": "#2280cd",
        "accentText": "#ffffff",
        "warn": "#8a3b00",
        "ok": "#1d7a3a",
        "line": "#d4d8dd",
    },
    # Used only if the palette cannot be read. Deliberately not a copy of
    # either of the others: these are the colours that are legible on both,
    # which matters more here than being the best choice for one.
    "unknown": {
        "muted": "#808a94",
        "accent": "#2f8fd8",
        "accentHover": "#46a0e4",
        "accentText": "#ffffff",
        "warn": "#c07000",
        "ok": "#2f9152",
        "line": "#808a94",
    },
}


def _themeColours():
    """The palette for the theme Slicer is currently drawing in."""
    try:
        window = qt.QApplication.palette().color(qt.QPalette.Window)
        return _THEMES["dark" if window.lightness() < 128 else "light"]
    except Exception:  # pragma: no cover - no application, or an older Qt
        return _THEMES["unknown"]


def _muted(label):
    """Secondary text: present, and clearly not the thing to read first."""
    label.setStyleSheet("QLabel { color: %s; }" % _themeColours()["muted"])
    return label


def _tint(label, kind):
    """``"warn"`` or ``"ok"`` -- a label that carries its own weight."""
    label.setStyleSheet("QLabel { color: %s; }" % _themeColours()[kind])
    return label


def _caption(text):
    label = qt.QLabel(text)
    label.setWordWrap(True)
    return _muted(label)


def _primary(button):
    """The one action a section exists for.

    Every button in the panel used to be the same button, so "Get next case"
    and "Check for updates" had equal weight and a section read as a wall of
    controls with no way in. Exactly one button per section gets this.
    """
    colours = _themeColours()
    button.setStyleSheet(
        "QPushButton {"
        " background-color: %(accent)s; color: %(accentText)s; border: none;"
        " border-radius: 4px; padding: 7px 14px; font-weight: bold; }"
        "QPushButton:hover { background-color: %(accentHover)s; }"
        "QPushButton:disabled {"
        " background-color: transparent; color: %(muted)s;"
        " border: 1px solid %(line)s; font-weight: normal; }" % colours)
    return button


def _link(button):
    """A rarely-wanted action: reads as text, behaves as a button."""
    button.setFlat(True)
    button.setStyleSheet(
        "QPushButton { border: none; padding: 2px 6px; color: %s; }"
        "QPushButton:hover { text-decoration: underline; }"
        % _themeColours()["accent"])
    return button


def _separator():
    """A hairline rule.

    A one-pixel box with a background rather than an ``HLine``: a styled
    ``HLine`` takes its colour from the frame palette and ignores the
    stylesheet, which on the dark theme drew it in the background colour --
    a rule that was there in the layout and invisible on screen.
    """
    line = qt.QFrame()
    line.setFrameShape(qt.QFrame.NoFrame)
    line.setFixedHeight(1)
    line.setStyleSheet(
        "QFrame { background-color: %s; }" % _themeColours()["line"])
    return line


def _fitColumn(table, column, texts, floor, ceiling):
    """Widen one column to the longest string it will actually hold.

    The alternative, ``resizeColumnsToContents``, lays out every row of
    every column; this measures one string. The longest of a thousand case
    names is found by comparing strings, which costs nothing, and only that
    one is handed to the font.

    Fixed widths were wrong here for a reason worth keeping: they were
    chosen against the names in a test fixture, and the real project's are
    `imagecas_0001` -- half as wide again, and clipped on every row.
    """
    longest = ""
    for text in texts:
        if len(text) > len(longest):
            longest = text
    try:
        metrics = qt.QFontMetrics(table.font)
        try:
            width = metrics.horizontalAdvance(longest)
        except AttributeError:  # pragma: no cover - Qt < 5.11
            width = metrics.width(longest)
        table.setColumnWidth(column, min(ceiling, max(floor, width + 14)))
    except Exception:  # pragma: no cover - no font metrics available
        table.setColumnWidth(column, floor)


def _tidyTable(table, widths, minimumHeight):
    """The look both tables in the panel share.

    Row numbers off, because they number the rows on screen rather than the
    cases, so on a filtered list they say something untrue. Column widths set
    by hand rather than by ``ResizeToContents``, which measures every row --
    affordable for the ten rows in the history table and not for the thousand
    in the case list.

    Every column gets a width, the last one included -- any the caller leaves
    out get a narrow default rather than Qt's 100px. ``stretchLastSection``
    grows the last column into space left over but never shrinks it, so one
    unsized column pushes the whole table past the edge of the dock and puts a
    horizontal scrollbar under a list that would otherwise fit.
    """
    table.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    table.setSelectionMode(qt.QAbstractItemView.SingleSelection)
    table.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setMinimumHeight(minimumHeight)
    try:
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(22)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setHighlightSections(False)
        for column in range(table.columnCount):
            table.setColumnWidth(
                column, widths[column] if column < len(widths) else 44)
    except AttributeError:  # pragma: no cover - a Qt without these accessors
        pass
    return table


def _shortTime(value):
    """An ISO timestamp as ``2026-09-27 15:04``, or ``--``.

    Local time, seconds dropped. A reviewer comparing two attempts wants to know
    which came first and roughly when, and a column of full ISO strings with
    microseconds and an offset makes that harder rather than easier.
    """
    if not value:
        return "--"
    text = str(value).replace("T", " ")
    for cut in ("+", "."):
        if cut in text:
            text = text.split(cut)[0]
    return text[:16]


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


class SegQueue14Test(ScriptedLoadableModuleWidget):
    """Placeholder so Slicer's self-test machinery has something to find.

    The real tests live in ``tests/test_segqueue14_*.py`` and run under plain
    pytest, because the parts worth testing -- the state machine, the sampling
    policy, the wire protocol, the cache -- were deliberately written to need
    neither Slicer nor a server.
    """

    def runTest(self):
        slicer.util.infoDisplay(
            "SegQueue14's tests run under pytest in the repository:\n"
            "    pytest tests/test_segqueue14_*.py\n"
            "Nothing to run inside Slicer.")
