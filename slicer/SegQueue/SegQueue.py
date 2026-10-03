"""SegQueue -- fetch one case, segment it, send it back, and keep nothing.

This is the annotator's entire experience of the platform. There is no file
browser, no server URL to remember beyond the first login, no "where do I put
the output" and no naming convention to get wrong. Press *Get next case*, the
volume arrives with the project's segments already created and named, the
Segment Editor opens on it, and *Validate & submit* uploads the result and
deletes the local copy.

On a case that ships a coronary mask -- most of them -- each of those segments
arrives holding a copy of the whole tree, hidden, and the work is to show one and
cut it back to a single vessel. That happens entirely in the Segment Editor: this
module creates the case, checks it and sends it, and puts no tooling of its own
in front of Slicer's.

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

#: Icons and logo artwork. Sits beside this file in both layouts -- the
#: checkout and the installed extension -- so no second search is needed.
_RESOURCES = os.path.join(_MODULE_DIR, "Resources")

#: Slicer's own logo lives above the module panel, in a QLabel the application
#: installs as the panel dock's title-bar widget. It is application chrome
#: shared by every module, so this one *borrows* it for as long as SegQueue is
#: the open module and hands it back untouched on the way out -- an annotator
#: who switches to Volumes should see Slicer's branding, not ours.
_LOGO_LABEL_NAME = "LogoLabel"
_PANEL_DOCK_NAME = "PanelDockWidget"
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

try:
    from segqueue import protocol
    from segqueue import release as rel
    from segqueue import states as st
    from segqueue.checksum import sha256_file, verify_file
    from segqueue.dataset import sniff_suffix, suffix_for
    from segqueue.protocol import SubmissionMeta
    from segqueue.segcheck import ERROR, Geometry, blocking, check_submission, summarise
    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - surfaced in the UI instead
    st = None
    rel = None
    protocol = None
    _IMPORT_ERROR = str(exc)

from SegQueueLib import (
    CacheError,
    CaseCache,
    SegQueueClient,
    SegQueueError,
    UpdateError,
    defaultRoot,
    updater,
)

__version__ = "0.11.1"

#: How often the in-progress segmentation is written to disk. Two minutes is
#: chosen against the cost of losing work rather than the cost of the write: a
#: 400-slice segmentation saves in well under a second, and no annotator should
#: have to redo more than two minutes of tracing after a crash.
AUTOSAVE_SECONDS = 120

#: How often the case-note thread is refetched while a case is open. Slow on
#: purpose: notes are left for the next person, not chatted in real time, and
#: every poll is a request from thirty machines against one small server.
NOTES_REFRESH_SECONDS = 90

#: How long a "no update available" answer is trusted before GitHub is asked
#: again. Unauthenticated GitHub allows sixty requests an hour *per address*,
#: and a teaching lab is thirty annotators behind one NAT who each open the
#: module several times a day. Six hours is far more often than releases happen
#: and far less often than the module is opened.
UPDATE_CHECK_HOURS = 6

#: Delay before the update check fires, in milliseconds. The panel draws first;
#: an annotator opening the module to start work should never wait on GitHub.
UPDATE_CHECK_DELAY_MS = 1200

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

#: The state filters the submission viewer offers, in lifecycle order so the
#: list reads as a progression rather than as an alphabetised set of jargon. The
#: labels are the words a reviewer would use, not the stored state names.
REVIEW_FILTERS = (
    ("assigned", "Assigned, not downloaded"),
    ("downloaded", "Being worked on"),
    ("submitted", "Submitted"),
    ("under_review", "Under review"),
    ("approved", "Approved"),
    ("rejected", "Rejected (historical)"),
    ("released", "Given back"),
)

#: States in which there is nothing left for a reviewer to decide. Approving or
#: returning one of these is refused by the server anyway; disabling the buttons
#: is the difference between that refusal and a reviewer who never tried.
REVIEW_DECIDED_STATES = frozenset({"approved", "released"})

#: How solid the seed looks in the 3D view. Enough to read the shape of the tree
#: at a glance, sheer enough to see the branches an annotator has already claimed
#: through it -- which is the comparison the 3D view is open for.
SEED_3D_OPACITY = 0.35

#: Settings keys. Stored in Slicer's own QSettings so a returning annotator does
#: not retype the server URL. Neither the username nor the token is stored -- see
#: ``_SETTING_LEGACY_USER`` below and SegQueueClient's docstring.
_SETTING_SERVER = "SegQueue/serverUrl"
_SETTING_CACHE = "SegQueue/cacheRoot"
#: Last update check: {"checkedAt": <unix seconds>, "tag": <tag or "">}. Cached
#: so the rate limit is spent on real checks rather than on reopening a panel.
_SETTING_UPDATE = "SegQueue/updateCheck"

#: The username used to be remembered here. It no longer is: the password field
#: is deliberately blank at every login so that a shared annotation workstation
#: cannot attribute one person's submissions to another, and a pre-filled
#: username undoes most of that -- the next person tabs past a name that is not
#: theirs and only the password stands between them and someone else's queue.
#: The key is kept solely to delete the value left behind by earlier versions.
_SETTING_LEGACY_USER = "SegQueue/lastUser"


class SegQueue(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SegQueue"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Christian Rogers"]
        self.parent.helpText = __doc__
        self.parent.acknowledgementText = ""

        # Slicer gives a scripted module with no icon of its own the application's
        # generic module logo -- which is what used to appear in the module
        # selector and in the header above the panel. The base class does look for
        # Resources/Icons/<ModuleName>.{svg,png}, but it resolves that against
        # `parent.path`, which differs between a checkout and an installed
        # extension; setting the icon here makes it independent of that.
        _icon = os.path.join(_RESOURCES, "Icons", "SegQueue.png")
        if os.path.isfile(_icon):
            self.parent.icon = qt.QIcon(_icon)


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
        #: Whether this case opened from an autosaved draft rather than fresh.
        self.resumedDraft = False

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
        # After the helpers, necessarily: the mask it copies is one of them.
        self._startBranchesFromSeed()
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

    def showSeedIn3d(self, on):
        """Render the coronary seed in the 3D view, or stop.

        The seed is the thing the annotator has been asked to cut up, so seeing
        the whole tree at once is not a nicety: which arm is the LAD and which is
        the LCx is a question about the *shape* of the tree, and answering it by
        scrolling slices is how a branch ends up half-labelled. The 2D views show
        a cross-section of a vessel; the 3D view shows the vessel -- and a loop
        round it is one gesture there.

        The heart mask deliberately stays out of it -- a solid chamber wall would
        hide the very tree this is for.

        Returns whether the seed is now showing. Building the surface is the
        expensive part and only happens when turning it on. A case with no seed
        is not an early return: the heart mask still has to be pushed out of the
        3D view, which is what this loop does for every helper that is not the
        seed.
        """
        if self.segmentationNode is None:
            return False
        display = self.segmentationNode.GetDisplayNode()
        if display is None:
            return False
        if on and self.seedSegmentId:
            self.segmentationNode.CreateClosedSurfaceRepresentation()
        for segmentId in self.helperIds():
            display.SetSegmentOpacity3D(
                segmentId,
                SEED_3D_OPACITY if (on and segmentId == self.seedSegmentId) else 0.0)
        return bool(on and self.seedSegmentId)

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

        Sets ``resumedDraft``, which is what stops ``_startBranchesFromSeed``
        overwriting an annotator's own trimming with four fresh copies of the
        mask when they come back to a case tomorrow.
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

    def _startBranchesFromSeed(self):
        """Start every branch as its own copy of the coronary mask, all hidden.

        On a seeded case the tree is already drawn; the job is to say which part
        of it is which. So every branch begins as the whole tree and is cut back
        to one vessel, and the Segment Editor's own segment list -- show the one
        you are working on, hide the rest -- is the entire interface for that.

        Four independent copies rather than one tree handed round in turn. The
        branches can then be done in any order, no branch's work rests on
        another's having been finished first, and there is no state to explain:
        what a branch holds is what the annotator left in it.

        **Hidden, all of them.** Four identical masks stacked on the same voxels
        is not a picture of anything, and the one thing worth seeing on opening is
        the tree about to be divided -- which is the mask itself, and stays
        visible. The eyes in the segment list are how they come back.

        Only on a case with no work on it: a reopened draft is the annotator's own
        trimming and has to survive being closed. Returns how many branches were
        started.

        Copied through the segment arrays rather than the Logical operators
        effect, because nothing here needs the Segment Editor -- this runs while
        the case is still being assembled, before any panel is bound to it -- and
        because on the source grid a copy is a copy.
        """
        if self.resumedDraft or self.segmentationNode is None:
            return 0
        if not self.seedSegmentId or self.project is None:
            return 0

        try:
            mask = slicer.util.arrayFromSegmentBinaryLabelmap(
                self.segmentationNode, self.seedSegmentId, self.volumeNode)
        except Exception:
            # A case whose mask cannot be read is still a case the annotator can
            # segment by hand. Empty branches are a worse start, never a blocked
            # one.
            return 0
        if mask is None or not mask.size or not mask.any():
            return 0

        display = self.segmentationNode.GetDisplayNode()
        started = 0
        for spec in self.project.segments:
            segmentId = self.segmentIdFor(spec.name)
            if not segmentId:
                continue
            slicer.util.updateSegmentBinaryLabelmapFromArray(
                mask, self.segmentationNode, segmentId, self.volumeNode)
            if display is not None:
                display.SetSegmentVisibility(segmentId, False)
            started += 1
        return started

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
        heart mask and the coronary seed, which came from the source dataset and
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
            "vtkMRMLLabelMapVolumeNode", "SegQueueExport")
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
            self._assertNoStrayLabels(labelmapNode)
            return counts, self.sourceGeometry(), _geometryOf(labelmapNode)
        finally:
            slicer.mrmlScene.RemoveNode(labelmapNode)

    def _assertNoStrayLabels(self, labelmapNode):
        """Refuse to submit a volume containing a label the protocol does not name.

        The explicit id list should make this impossible. It is checked anyway
        because the failure it guards against -- shipping the dataset's own
        coronary mask back as though a student had drawn it -- would corrupt the
        training set while every dashboard number looked healthy. It also catches
        a subtler drift: if a future Slicer numbered exported segments by
        position rather than by each segment's label value, a project whose
        labels are not 1..N would quietly relabel every vessel.
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

        directory = os.path.join(self.cache.root, "review")
        try:
            os.makedirs(directory)
        except OSError:
            pass
        path = os.path.join(directory, "revision.seg.nrrd")

        counts, sourceGeom, segGeom = self.exportLabelmap(path)
        problems = self.validate(counts, sourceGeom, segGeom)
        if blocking(problems):
            raise SegQueueError(
                "This segmentation is not ready to save:\n\n"
                + summarise(blocking(problems)))
        if not os.path.isfile(path):
            raise SegQueueError(
                "There is nothing to save -- none of the segments has any "
                "voxels in it.")

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
        self.notesTimer = None
        self._reviewRows = []
        self._reviewCases = []
        self._annotators = []
        self._historyRows = []
        self._claimedSubmission = None
        self._reviewStart = None
        self._slicerLogo = None
        self._pendingUpdate = None

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

        def progress(done, total):
            self.updateProgress.setMaximum(max(1, total))
            self.updateProgress.setValue(done)
            slicer.app.processEvents()

        staging = tempfile.mkdtemp(prefix="segqueue-download-")
        try:
            with _busy():
                archive = os.path.join(staging, str(asset.get("name") or "SegQueue.zip"))
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

    # ------------------------------------------------------------------ notes

    def _renderNotes(self, notes):
        """Draw the thread. Newest at the bottom, and scrolled to it.

        Chronological rather than newest-first because the thread is read as a
        history of one case -- what was tried, what the reviewer said, what was
        done about it -- and that only makes sense forwards.
        """
        if not notes:
            self.notesBrowser.setHtml(
                "<span style='color:#888'>No notes on this case yet.</span>")
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

    # --------------------------------------------------------------- branding

    def enter(self):
        """The module became visible: put our name above the panel, and see
        whether the annotator is running a version we have since replaced."""
        if self.logic is None:
            return
        self._applyPanelBranding()
        # Deferred so the panel is on screen first. An annotator sitting down to
        # segment must never wait on GitHub to see the Get next case button.
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
        label.setToolTip("SegQueue {} -- Bradensbay".format(__version__))

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
            slicer.util.settingsValue(_SETTING_SERVER, "https://segqueue.example.edu"))
        self.serverEdit.setToolTip(
            "Base URL of the SegQueue server. /api/v1 is added automatically.")
        form.addRow("Server:", self.serverEdit)

        # Deliberately empty, and never pre-filled from settings: see
        # _SETTING_LEGACY_USER. Whoever is sitting here types who they are.
        self.userEdit = qt.QLineEdit()
        self.userEdit.setPlaceholderText("Your SegQueue username")
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

        # Deliberately here rather than in the update banner: the banner only
        # exists when there is an update, and "am I on the current version?" is
        # a question people ask when there is not.
        self.checkUpdateButton = qt.QPushButton("Check for updates")
        self.checkUpdateButton.setToolTip(
            "Asks GitHub whether a newer SegQueue has been published. Runs "
            "automatically when you open the module, at most a few times a day.")
        self.checkUpdateButton.clicked.connect(self.onCheckForUpdates)
        form.addRow(self.checkUpdateButton)

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

        # Where the project instructions used to be. They were the same text on
        # every case, read once in week one and then wallpaper; this space is
        # worth more as the thing that differs between cases. Notes follow the
        # *case*, so the annotator doing the rework, the reviewer who rejected
        # it and whoever had it before are all reading the same list.
        self.notesBox = qt.QGroupBox("Case notes")
        notesLayout = qt.QVBoxLayout(self.notesBox)
        notesLayout.setContentsMargins(8, 6, 8, 6)

        self.notesBrowser = qt.QTextBrowser()
        self.notesBrowser.setMaximumHeight(150)
        self.notesBrowser.setOpenExternalLinks(True)
        notesLayout.addWidget(self.notesBrowser)

        noteRow = qt.QHBoxLayout()
        self.noteInput = qt.QLineEdit()
        self.noteInput.setPlaceholderText(
            "Something the next person should know about this case")
        self.noteInput.setToolTip(
            "Everyone who works on this case sees this, with your name on it. "
            "Notes cannot be edited or deleted once posted. Your unposted text "
            "is saved with the case, so closing Slicer does not lose it.")
        self.noteInput.setMaxLength(protocol.NOTE_MAX_CHARS)
        self.noteInput.returnPressed.connect(self.onPostNote)
        noteRow.addWidget(self.noteInput)

        self.postNoteButton = qt.QPushButton("Post")
        self.postNoteButton.clicked.connect(self.onPostNote)
        noteRow.addWidget(self.postNoteButton)

        self.refreshNotesButton = qt.QPushButton("Refresh")
        self.refreshNotesButton.setToolTip(
            "Fetch new notes now. This happens on its own every couple of "
            "minutes while a case is open.")
        self.refreshNotesButton.clicked.connect(lambda: self.onRefreshNotes(quiet=False))
        noteRow.addWidget(self.refreshNotesButton)
        notesLayout.addLayout(noteRow)

        layout.addWidget(self.notesBox)
        self._renderNotes([])

        self.progressBar = qt.QProgressBar()
        self.progressBar.setVisible(False)
        layout.addWidget(self.progressBar)

        self.timerLabel = qt.QLabel("Time on this case: --")
        layout.addWidget(self.timerLabel)

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

        controls = qt.QHBoxLayout()
        self.refreshReviewButton = qt.QPushButton("Refresh")
        self.refreshReviewButton.clicked.connect(self.onRefreshReview)
        controls.addWidget(self.refreshReviewButton)

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
        controls.addWidget(self.reviewFilter)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.reviewTable = qt.QTableWidget()
        self.reviewTable.setColumnCount(7)
        self.reviewTable.setHorizontalHeaderLabels(
            ["Case", "Annotator", "State", "Attempt", "Submitted", "Subs", "Flags"])
        self.reviewTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.reviewTable.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.reviewTable.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.reviewTable.setMinimumHeight(170)
        self.reviewTable.itemSelectionChanged.connect(self.onReviewRowChanged)
        layout.addWidget(self.reviewTable)

        layout.addWidget(_caption(
            "Every submission against the selected case, oldest first. Nothing "
            "is ever overwritten, so a superseded attempt is still here."))
        self.historyTable = qt.QTableWidget()
        self.historyTable.setColumnCount(5)
        self.historyTable.setHorizontalHeaderLabels(
            ["When", "Author", "Role", "Attempt", "Auto score"])
        self.historyTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.historyTable.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.historyTable.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.historyTable.setMinimumHeight(110)
        layout.addWidget(self.historyTable)

        openRow = qt.QHBoxLayout()
        self.openReviewButton = qt.QPushButton("Open selected submission")
        self.openReviewButton.setToolTip(
            "Loads the volume and that segmentation into the scene. Picks the "
            "highlighted row in the history table, or the case's latest "
            "submission if none is highlighted.")
        self.openReviewButton.clicked.connect(self.onOpenReview)
        openRow.addWidget(self.openReviewButton)

        self.openCaseButton = qt.QPushButton("Open case image")
        self.openCaseButton.setToolTip(
            "Loads the case's own volume and whatever masks ship with it. For a "
            "case nobody has worked on there is no submission to open, and the "
            "image is what says whether the scan is usable at all.")
        self.openCaseButton.clicked.connect(self.onOpenCase)
        openRow.addWidget(self.openCaseButton)

        self.takeCaseButton = qt.QPushButton("Take case && segment it")
        self.takeCaseButton.setToolTip(
            "Assigns the selected case to you and opens it as an ordinary case, "
            "so you can segment and submit it yourself. It becomes genuinely "
            "yours: it shows in your queue and is reviewed like any other.")
        self.takeCaseButton.clicked.connect(self.onTakeCase)
        openRow.addWidget(self.takeCaseButton)
        layout.addLayout(openRow)

        self.reviewStatusLabel = qt.QLabel()
        self.reviewStatusLabel.setWordWrap(True)
        layout.addWidget(self.reviewStatusLabel)

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

        self.reviseButton = qt.QPushButton("Save my changes && approve")
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
            cells = [
                case.get("caseName", ""),
                assignment.get("annotator", "") or "--",
                assignment.get("state", "") or "unassigned",
                str(assignment.get("attempt", "")) or "--",
                _shortTime(assignment.get("submittedAt")),
                str(assignment.get("submissionCount", 0)),
                ", ".join(assignment.get("flagged") or []),
            ]
            for column, text in enumerate(cells):
                self.reviewTable.setItem(index, column, qt.QTableWidgetItem(text))
        self.reviewTable.resizeColumnsToContents()
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
            for column, text in enumerate(cells):
                self.historyTable.setItem(index, column, qt.QTableWidgetItem(text))
        self.historyTable.resizeColumnsToContents()
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
        get sniffed after the download, the same fallback ``_correctSuffix`` is.
        """
        directory = os.path.join(self.logic.cache.root, "review")
        try:
            os.makedirs(directory)
        except OSError:
            pass
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

        directory = os.path.join(self.logic.cache.root, "review")
        try:
            os.makedirs(directory)
        except OSError:
            pass
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
        """Bring the case's heart and coronary masks in, if it ships them."""
        if self.logic.segmentationNode is None:
            self.logic.segmentationNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLSegmentationNode", "Case masks")
            self.logic.segmentationNode.CreateDefaultDisplayNodes()
            self.logic.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(
                self.logic.volumeNode)

        self.logic.seedSegmentId = None
        self.logic.regionSegmentId = None
        wanted = ((protocol.ASSET_REGION, protocol.REGION_SEGMENT_NAME,
                   (0.85, 0.55, 0.55), 0.08),
                  (protocol.ASSET_SEED, protocol.SEED_SEGMENT_NAME,
                   (0.95, 0.95, 0.35), 0.35))
        for kind, name, colour, fill in wanted:
            path = os.path.join(directory, "case_{}.nii.gz".format(kind))
            try:
                got = self.logic.client.downloadCaseAsset(
                    case["caseId"], kind, path)
            except SegQueueError:
                got = None
            if not got:
                continue
            segmentId = self.logic._importHelper(path, name, colour, fill)
            if kind == protocol.ASSET_SEED:
                self.logic.seedSegmentId = segmentId
            else:
                self.logic.regionSegmentId = segmentId

        if self.logic.seedSegmentId:
            self.logic.showSeedIn3d(True)

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
        quota = ("" if project.quota_remaining is None
                 else "  |  {} case(s) left in your quota".format(project.quota_remaining))
        self.statusLabel.setText("Logged in as {}{}".format(
            user.get("login", username), quota))
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
        self.noteInput.setText(self.logic.noteDraft())
        self.onRefreshNotes()
        self._bindEditor(self.logic.segmentationNode, self.logic.volumeNode)
        # Taking a case ends any review: the scene is this case now.
        self._claimedSubmission = None
        self._reviewStart = None

        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        # The mask goes into the 3D view as the case opens rather than on a
        # button, because it is the first question of the case -- where do these
        # branches go -- and an annotator who has to ask for it has usually
        # already started scrolling slices to answer it the slow way. Centred as
        # well as built: a mask rendered off camera is the same as no mask.
        self.logic.showSeedIn3d(True)
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
            self.problemsLabel.setText("Draft saved.")
        else:
            self.problemsLabel.setText("Nothing to save yet.")

    def onAutosave(self):
        self.logic.autosave()
        self._saveNoteDraft()

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
        self._clearNotes()
        self.problemsLabel.setText("")
        self.caseLabel.setText("Submitted. Press 'Get next case' when you are ready.")
        self.reworkBox.setVisible(False)
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
        self.reworkBox.setVisible(False)
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
        for button in (self.saveButton, self.checkButton, self.submitButton,
                       self.releaseButton):
            button.setEnabled(hasCase)
        self.editorBox.setEnabled(hasCase or reviewing)
        self.notesBox.setEnabled(hasCase)


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


def _caption(text):
    label = qt.QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("QLabel { color: #5a5f66; }")
    return label


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
