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

import json
import os
import shutil
import sys
import tempfile
import time
import traceback

import ctk
import numpy as np
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
    from segqueue import lasso as lasso_geom
    from segqueue import protocol
    from segqueue import release as rel
    from segqueue import seedsplit
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
    seedsplit = None
    lasso_geom = None
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

__version__ = "0.6.0"

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

#: Sphere brush diameter in millimetres, for touching up what the tube missed.
#: Smaller than the vessel on purpose: a brush wider than the lumen cannot be
#: used to correct an edge, only to bury it.
BRUSH_DIAMETER_MM = 1.5
BRUSH_RANGE_MM = (0.25, 8.0)

#: Editable intensity window, in HU. Opacified lumen sits well above 150 and
#: below dense calcium; restricting paint to this range means a slightly sloppy
#: brush stroke still produces a clean lumen edge.
LUMEN_HU_MIN = 150
LUMEN_HU_MAX = 1000

#: The tube effect, from the SegmentEditorExtraEffects extension. Named as a
#: constant because it is referenced in three places and is the one tool this
#: whole panel is arranged around.
TUBE_EFFECT = 'Draw tube'

#: The extension that provides it. Declared as a dependency in the .s4ext too,
#: but a local "Install from file" does not resolve dependencies, so the panel
#: also has to say so at the moment it matters.
TUBE_EXTENSION = 'SegmentEditorExtraEffects'

#: A hidden segment the tube is applied into before being merged. It exists
#: because Draw tube *replaces* the selected segment's contents rather than
#: adding to them -- see ``onApplyTube``. Never exported: the submission is built
#: from an explicit list of the project's own segments.
TUBE_SCRATCH_SEGMENT = "~ tube section (working)"

#: Tube radius in millimetres, and the range the slider offers. A left main
#: lumen is around 2 mm in radius and a distal LAD under 1, so the useful band is
#: narrow and the default sits mid-vessel. The effect's own default is 1.0.
TUBE_RADIUS_MM = 1.25
TUBE_RADIUS_RANGE_MM = (0.25, 6.0)

#: The two effects offered as buttons, with their keyboard shortcut.
#:
#: Deliberately two, not twenty. A coronary artery is a tube: clicking a handful
#: of points down its centreline and letting the effect sweep a tube along them
#: is both faster and more consistent between annotators than any amount of
#: slice-by-slice painting -- and the radius is exactly the degree of freedom
#: that matters, because vessels taper. Paint is here to fix what the tube got
#: wrong, and nothing else earns a button. Every other effect is still one click
#: away in the Segment Editor below.
VESSEL_EFFECTS = (
    (TUBE_EFFECT, 'Q',
     'Click points down the middle of the vessel, then Apply (A). Placement '
     'starts as soon as you press this, and Apply leaves you ready for the next '
     'section -- so a tapering artery is drawn as several sections, each with '
     'its own radius, all adding into the same vessel.'),
    ('Paint', 'W', 'Touch up what the tube missed. Sphere brush, sized in mm.'),
)

#: Prefix for the per-vessel marker lists used to divide the coronary seed. One
#: markups node per branch, named for it, so the annotator can see and drag the
#: points that decided the division rather than re-running a black box -- and so
#: the tilde sorts them beside the other scaffolding in the data module.
DIVIDE_MARKUP_PREFIX = "~ divide: "

#: How solid the seed looks in the 3D view. Enough to read the shape of the tree
#: at a glance, sheer enough to see the branches an annotator has already claimed
#: through it -- which is the comparison the 3D view is open for.
SEED_3D_OPACITY = 0.35

#: The loop an annotator drags around a branch, while they are dragging it.
#: Bright against both the mask and the vessels, and 2 px so it reads as a
#: gesture rather than as another thing rendered in the scene.
LASSO_COLOUR = (1.0, 0.85, 0.1)
LASSO_WIDTH = 2.0

#: A division that places fewer than this share of the mask usually means the
#: markers missed rather than that the mask is odd, and saying so immediately
#: beats the annotator discovering it at submission.
DIVIDE_COVERAGE_WARNING = 0.75

#: Settings keys. Stored in Slicer's own QSettings so a returning annotator does
#: not retype the server URL or re-dial their tool sizes. Neither the username
#: nor the token is stored -- see ``_SETTING_LEGACY_USER`` below and
#: SegQueueClient's docstring.
_SETTING_TUBE_RADIUS = "SegQueue/tubeRadiusMm"
_SETTING_BRUSH = "SegQueue/brushDiameterMm"
_SETTING_SERVER = "SegQueue/serverUrl"
_SETTING_CACHE = "SegQueue/cacheRoot"
#: Whether the coronary seed is rendered in the 3D view when a case opens. On by
#: default: the tree is the thing the annotator is about to divide, and seeing
#: its shape whole is what tells them where the branches go before they have
#: scrolled a single slice.
_SETTING_SEED_3D = "SegQueue/showSeedIn3d"
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


class _LassoTool(object):
    """One freehand loop dragged in a 3D view.

    Deliberately one-shot: it arms, takes a single loop, and disarms itself.
    While it is armed the left button draws instead of rotating the camera --
    there is no way to have both on one button -- and a mode that stays on is a
    mode an annotator forgets they are in and then fights, having dragged the
    view and got a loop. Arming per loop costs one keypress and removes that
    entirely: between loops the view behaves exactly as Slicer always does.

    The loop is drawn on screen as it goes. A lasso you cannot see is a guess.
    """

    def __init__(self, view, onDone):
        self._view = view
        self._onDone = onDone
        self._interactor = view.interactor()
        self._renderer = view.renderWindow().GetRenderers().GetFirstRenderer()
        self._path = []
        self._drawing = False
        self._tags = []
        self._commands = []
        self._actor = None

    # ------------------------------------------------------------- arming

    def start(self):
        if self._tags:
            return
        self._path = []
        self._drawing = False
        events = (
            (vtk.vtkCommand.LeftButtonPressEvent, self._onPress),
            (vtk.vtkCommand.MouseMoveEvent, self._onMove),
            (vtk.vtkCommand.LeftButtonReleaseEvent, self._onRelease),
        )
        for event, handler in events:
            # Above the camera interactor's own priority, so the drag reaches
            # here first and can be swallowed before it rotates the scene.
            tag = self._interactor.AddObserver(event, handler, 10.0)
            self._tags.append(tag)
            self._commands.append(self._interactor.GetCommand(tag))

    def stop(self):
        for tag in self._tags:
            self._interactor.RemoveObserver(tag)
        self._tags = []
        self._commands = []
        self._path = []
        self._drawing = False
        self._clearOverlay()

    @property
    def armed(self):
        return bool(self._tags)

    # ------------------------------------------------------------- events

    def _abort(self):
        """Stop the event before the camera style sees it."""
        for command in self._commands:
            if command is not None:
                command.AbortFlagOn()

    def _onPress(self, caller, event):
        self._drawing = True
        self._path = [self._position()]
        self._abort()

    def _onMove(self, caller, event):
        if not self._drawing:
            return
        self._path.append(self._position())
        self._drawOverlay()
        self._abort()

    def _onRelease(self, caller, event):
        if not self._drawing:
            return
        self._drawing = False
        self._path.append(self._position())
        path = list(self._path)
        self._abort()
        # Disarm before handing the loop over: the callback shows dialogs and
        # runs a division, and leaving observers live across that means a stray
        # click lands in a half-finished lasso.
        self.stop()
        self._onDone(path, self._renderer)

    def _position(self):
        x, y = self._interactor.GetEventPosition()
        return (float(x), float(y))

    # ------------------------------------------------------------ overlay

    def _drawOverlay(self):
        if len(self._path) < 2:
            return
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()
        for x, y in self._path:
            points.InsertNextPoint(x, y, 0.0)
        lines.InsertNextCell(len(self._path))
        for i in range(len(self._path)):
            lines.InsertCellPoint(i)

        polygon = vtk.vtkPolyData()
        polygon.SetPoints(points)
        polygon.SetLines(lines)

        if self._actor is None:
            coordinate = vtk.vtkCoordinate()
            coordinate.SetCoordinateSystemToDisplay()
            mapper = vtk.vtkPolyDataMapper2D()
            mapper.SetTransformCoordinate(coordinate)
            self._actor = vtk.vtkActor2D()
            self._actor.SetMapper(mapper)
            self._actor.GetProperty().SetColor(*LASSO_COLOUR)
            self._actor.GetProperty().SetLineWidth(LASSO_WIDTH)
            self._renderer.AddActor2D(self._actor)
        self._actor.GetMapper().SetInputData(polygon)
        self._view.forceRender()

    def _clearOverlay(self):
        if self._actor is None:
            return
        self._renderer.RemoveActor2D(self._actor)
        self._actor = None
        try:
            self._view.forceRender()
        except Exception:
            # The view can be gone by the time a case is torn down, and failing
            # to rub out a line is not worth an error on the way out.
            pass


class SegQueue(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SegQueue"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Christian Rogers"]
        self.parent.helpText = __doc__
        self.parent.acknowledgementText = (
            "Distributed CT segmentation for the Asclepius coronary dataset. "
            "Built and operated by Bradensbay."
        )

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
        #: What the last seed division gave each branch, by segment name. See
        #: ``rememberSplit``.
        self._lastSplit = {}
        #: Voxels circled in the 3D view, by segment name. Sources for the
        #: division exactly as the clicked markers are; see ``addLassoVoxels``.
        self._lassoVoxels = {}
        #: The mask's connected pieces, cached per case. See ``seedPieces``.
        self._seedPieces = None

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
        self.restoreMarkers(self.savedMarkers())
        self.restoreLasso()
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

    def scratchSegmentId(self):
        """A hidden segment to apply a tube into, created on first use.

        Draw tube replaces whatever is in the selected segment. Applying
        straight into a vessel therefore erases every section drawn before it,
        which makes a tapering artery -- wide proximally, narrow distally --
        impossible to build. Applying into this instead, then merging, turns
        each apply into an addition.
        """
        segmentId = self.segmentIdFor(TUBE_SCRATCH_SEGMENT)
        if segmentId:
            return segmentId
        segmentation = self.segmentationNode.GetSegmentation()
        segmentId = segmentation.AddEmptySegment(
            TUBE_SCRATCH_SEGMENT, TUBE_SCRATCH_SEGMENT, [0.6, 0.6, 0.6])
        display = self.segmentationNode.GetDisplayNode()
        if display is not None:
            # Invisible: it holds one section for a fraction of a second, and a
            # grey blob flashing over the vessel would be pure noise.
            display.SetSegmentVisibility(segmentId, False)
        return segmentId


    def helperIds(self):
        return [s for s in (self.seedSegmentId, self.regionSegmentId,
                            self.segmentIdFor(TUBE_SCRATCH_SEGMENT)) if s]

    # -------------------------------------------------- dividing the seed

    def seedVoxels(self):
        """The coronary seed as a set of ``(k, j, i)`` on the volume's own grid.

        On the *volume's* grid specifically, not the segment's. Slicer keeps each
        segment's binary labelmap cropped to its own extent, so two segments'
        arrays are indexed differently and comparing them voxel for voxel is
        quietly wrong -- the same mistake ``exportLabelmap`` exists to avoid at
        the other end of the case.
        """
        if not self.seedSegmentId or self.volumeNode is None:
            return set()
        array = self._segmentArray(self.seedSegmentId)
        if array is None:
            return set()
        # tolist() converts once, in C, and yields real Python ints -- the set
        # comprehension over numpy rows instead does eighty thousand scalar
        # extractions for the same answer, on the press of a button.
        return {tuple(voxel) for voxel in np.argwhere(array > 0).tolist()}

    def _segmentArray(self, segmentId):
        """One segment as a numpy array on the source grid, or None."""
        try:
            return slicer.util.arrayFromSegmentBinaryLabelmap(
                self.segmentationNode, segmentId, self.volumeNode)
        except Exception:
            return None

    def rasToVoxel(self, ras):
        """A scene point as an array index. ``MultiplyPoint`` gives IJK; arrays are KJI."""
        matrix = vtk.vtkMatrix4x4()
        self.volumeNode.GetRASToIJKMatrix(matrix)
        i, j, k, _ = matrix.MultiplyPoint((ras[0], ras[1], ras[2], 1.0))
        return (int(round(k)), int(round(j)), int(round(i)))

    def projectSeed(self, renderer, voxels=None):
        """Every seed voxel as ``(voxel, x, y, depth)`` in one renderer's view.

        Screen pixels from the camera's projection, and depth in **millimetres
        along the view direction** rather than the clip-space z the same matrix
        would give. Clip-space depth is non-linear, so a tolerance expressed in
        it means something different at the front of the heart than at the back;
        millimetres are what "within a vessel's thickness" is actually about.

        Vectorised because it runs on a mouse release with tens of thousands of
        voxels. The same work through ``renderer.WorldToDisplay`` one voxel at a
        time is the difference between a loop that lands and one the annotator
        draws twice thinking they missed.
        """
        voxels = self.seedVoxels() if voxels is None else voxels
        if not voxels or renderer is None:
            return []

        index = np.array(sorted(voxels), dtype=np.float64)
        # Array order is (k, j, i); the geometry matrices want (i, j, k, 1).
        homogeneous = np.empty((len(index), 4), dtype=np.float64)
        homogeneous[:, 0] = index[:, 2]
        homogeneous[:, 1] = index[:, 1]
        homogeneous[:, 2] = index[:, 0]
        homogeneous[:, 3] = 1.0

        ras = homogeneous @ _matrixArray(self._ijkToRas()).T

        camera = renderer.GetActiveCamera()
        size = renderer.GetSize()
        width, height = float(size[0]), float(size[1])
        if width <= 0 or height <= 0:
            return []

        clip = ras @ _matrixArray(
            camera.GetCompositeProjectionTransformMatrix(
                width / height, -1.0, 1.0)).T
        w = clip[:, 3]
        # w <= 0 is behind the camera, where the perspective divide is
        # meaningless and the point is not on screen to be circled anyway.
        visible = w > 1e-9
        if not visible.any():
            return []

        ndc = clip[visible, :3] / w[visible, None]
        x = (ndc[:, 0] + 1.0) * 0.5 * width
        y = (ndc[:, 1] + 1.0) * 0.5 * height

        position = np.array(camera.GetPosition(), dtype=np.float64)
        direction = np.array(camera.GetFocalPoint(), dtype=np.float64) - position
        norm = np.linalg.norm(direction)
        if norm <= 0:
            return []
        depth = (ras[visible, :3] - position) @ (direction / norm)

        keys = [tuple(v) for v in index[visible].astype(np.int64).tolist()]
        return list(zip(keys, x.tolist(), y.tolist(), depth.tolist()))

    def _ijkToRas(self):
        matrix = vtk.vtkMatrix4x4()
        self.volumeNode.GetIJKToRASMatrix(matrix)
        return matrix

    def seedPieces(self):
        """The mask's connected pieces, computed once per case.

        Cached because a loop needs them on every mouse release and the mask does
        not change while the case is open -- the vessels are built beside it, not
        out of it. Half a second per loop, spent once.
        """
        if self._seedPieces is None:
            if seedsplit is None:
                return []
            self._seedPieces = seedsplit.components(self.seedVoxels())
        return self._seedPieces

    def addLassoVoxels(self, name, voxels):
        """Record a circled region as belonging to one branch.

        Kept apart from the clicked markers rather than converted into them. A
        loop yields thousands of voxels, and a thousand fiducials in the scene
        would be unusable as well as unreadable -- but they are the same thing to
        ``computeSplit``, which only ever wanted source voxels.
        """
        if not voxels:
            return 0
        voxels = set(voxels)
        # The newest gesture wins. A loose loop around the LAD catches a little
        # of the LCx, and the LCx loop that follows has to be able to take it
        # back -- otherwise the same voxel is a source for two branches, the
        # partition silently gives it to whichever comes first in the project,
        # and circling a branch again does not fix it.
        for other, claimed in self._lassoVoxels.items():
            if other != name:
                claimed -= voxels
        current = self._lassoVoxels.setdefault(name, set())
        current |= voxels
        return len(current)

    def lassoVoxels(self, name):
        return self._lassoVoxels.get(name, set())

    def hasLasso(self):
        return any(self._lassoVoxels.values())

    def clearLasso(self, name=None):
        if name is None:
            self._lassoVoxels = {}
        else:
            self._lassoVoxels.pop(name, None)

    def computeSplit(self, markers):
        """Work out which part of the seed belongs to which branch.

        ``markers`` maps a project segment name to RAS points the annotator
        dropped on that branch. Returns a ``seedsplit.Split``. Nothing is written
        here and nothing is judged here: the panel decides what counts as a
        division worth keeping, and the panel writes it, because writing goes
        through the Segment Editor's own merge and that lives on the Qt side.
        """
        if seedsplit is None:
            raise SegQueueError(
                "This install is missing the segqueue package and cannot divide "
                "the mask. Reinstall the extension from a release.")
        if not self.seedSegmentId:
            raise SegQueueError("This case has no coronary mask to divide.")
        voxels = self.seedVoxels()
        if not voxels:
            # Two ways to get here and the annotator can act on both, so the
            # message names both rather than picking one and being wrong half the
            # time. Reading a segment on the source grid is the part an older
            # Slicer cannot do.
            raise SegQueueError(
                "Could not read this case's coronary mask.\n\nEither it is "
                "empty, or this Slicer is older than the divide tool needs "
                "(5.8). Painting inside the mask still works either way.")

        sources = {}
        for name in self._sourceNames(markers):
            landed = []
            for ras in markers.get(name, ()):
                voxel = self.rasToVoxel(ras)
                snapped = seedsplit.snap_to_mask(voxel, voxels)
                # A marker that missed by more than a few voxels is kept where it
                # fell rather than dropped, so the partition can report it as
                # stray and the panel can name the branch it was meant for. A
                # silently discarded marker produces an empty vessel and no clue.
                landed.append(snapped if snapped is not None else voxel)
            # Circled regions need no snapping: they were selected *from* the
            # mask, so they are on it by construction.
            landed.extend(sorted(self.lassoVoxels(name) & voxels))
            sources[name] = landed

        return seedsplit.geodesic_partition(voxels, sources)

    def _sourceNames(self, markers):
        """Branches with any source at all, in the project's own order.

        The project's order, not the dict's, because ties in the partition go to
        whichever branch was offered first -- so the order has to be a property
        of the project rather than of which vessel the annotator happened to
        circle first, or the same markers divide differently between two runs.
        """
        named = set(markers) | set(self._lassoVoxels)
        ordered = [spec.name for spec in self.project.segments
                   if spec.name in named]
        # Anything not in the project any more still gets a turn, at the end,
        # rather than vanishing without the panel being able to say so.
        return ordered + [name for name in named if name not in set(ordered)]

    def splitBuffer(self):
        """A zeroed array on the source grid, for handing voxels to a segment."""
        return np.zeros(
            slicer.util.arrayFromVolume(self.volumeNode).shape, dtype=np.uint8)

    def loadScratch(self, voxels, buffer=None):
        """Put an arbitrary set of voxels into the hidden working segment.

        The one genuinely new thing this feature asks of Slicer. Everything after
        it -- adding those voxels to a vessel, taking a previous division back
        out -- is the same ``Logical operators`` merge that Draw tube has been
        going through since 0.1.0, so the division inherits its undo behaviour,
        its layer handling and its indifference to the editor's masking.
        """
        scratch = self.scratchSegmentId()
        buffer = self.splitBuffer() if buffer is None else buffer
        buffer.fill(0)
        if voxels:
            index = np.array(list(voxels), dtype=np.int64)
            buffer[index[:, 0], index[:, 1], index[:, 2]] = 1
        self._setSegmentArray(scratch, buffer)
        return scratch

    def _setSegmentArray(self, segmentId, array):
        """Write a whole-volume binary array into one segment.

        Two routes because the one-line one is not present in every build this
        module is asked to run in, and an annotator meeting a bare
        ``AttributeError`` halfway through a division has no way to read it as
        "your Slicer is older than this feature".
        """
        try:
            slicer.util.updateSegmentBinaryLabelmapFromArray(
                array, self.segmentationNode, segmentId, self.volumeNode)
            return
        except AttributeError:
            pass

        labelNode = slicer.modules.volumes.logic().CreateAndAddLabelVolume(
            slicer.mrmlScene, self.volumeNode, "SegQueueDivideScratch")
        try:
            slicer.util.updateVolumeFromArray(labelNode, array)
            targets = vtk.vtkStringArray()
            targets.InsertNextValue(segmentId)
            ok = slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
                labelNode, self.segmentationNode, targets)
            if not ok:
                raise RuntimeError("import returned false")
        except Exception as exc:
            raise SegQueueError(
                "This build of Slicer cannot be written to by the divide tool "
                "({}). Divide needs Slicer 5.8; you can still paint inside the "
                "mask by hand.".format(exc))
        finally:
            slicer.mrmlScene.RemoveNode(labelNode)

    def rememberSplit(self, split):
        """Record what the last division gave each branch.

        Kept so that dividing *again* can take the previous answer back out of
        each vessel before putting the new one in. An annotator divides, looks at
        it in 3D, drops two more points on the branch that came out wrong and
        divides again -- and anything they painted by hand in between has to
        survive that, or the 3D view becomes a thing you dare not act on.
        """
        self._lastSplit = {name: set(claimed)
                           for name, claimed in split.assigned.items()}

    def previousShare(self, name):
        """What the last division gave this branch, or an empty set."""
        return self._lastSplit.get(name, set())

    def forgetSplit(self):
        """Drop the record of the last division.

        Called when the markers are cleared, and whenever a case leaves the
        scene. Without it the next division would subtract a partition the
        annotator has explicitly walked away from, taking their hand-painted
        corrections inside it along with it.
        """
        self._lastSplit = {}

    # ------------------------------------------------------- branch markers

    def markerNode(self, name, create=True):
        """The markups node holding one branch's division points.

        One node per branch rather than one node with labelled points, because
        the annotator has to be able to see which points belong to which vessel
        at a glance in a 3D view with four trees of them, and Slicer gives a
        colour to a *node*. It also makes "clear this branch's markers" a node
        operation rather than a search.
        """
        if self.project is None:
            return None
        nodeName = DIVIDE_MARKUP_PREFIX + name
        node = slicer.mrmlScene.GetFirstNodeByName(nodeName)
        if node is not None or not create:
            return node

        node = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsFiducialNode", nodeName)
        # Excluded from the scene views an annotator might save, and from the
        # segmentation entirely: these are an instruction to this module, not
        # anatomy, and nothing about them should reach the server.
        node.SetSaveWithScene(False)
        node.CreateDefaultDisplayNodes()
        spec = next((s for s in self.project.segments if s.name == name), None)
        display = node.GetDisplayNode()
        if display is not None and spec is not None:
            display.SetSelectedColor(*spec.color)
            display.SetColor(*spec.color)
            # Small glyphs and no text. The points sit on a 3 mm vessel, and the
            # default glyph is wider than the artery it is marking -- an
            # annotator cannot tell whether they hit the lumen or missed it.
            display.SetGlyphScale(1.5)
            display.SetTextScale(0.0)
        return node

    def markerPoints(self, name):
        """One branch's markers, as RAS triples."""
        node = self.markerNode(name, create=False)
        if node is None:
            return []
        return [[float(c) for c in node.GetNthControlPointPosition(i)]
                for i in range(node.GetNumberOfControlPoints())]

    def allMarkerPoints(self):
        """Every branch's markers, keyed by segment name, branches with none omitted."""
        if self.project is None:
            return {}
        points = {}
        for spec in self.project.segments:
            placed = self.markerPoints(spec.name)
            if placed:
                points[spec.name] = placed
        return points

    def restoreMarkers(self, points):
        """Put saved markers back, so reopening a case does not mean re-marking.

        Never raises. A case that comes back without its markers costs a minute;
        a case that refuses to open because a saved coordinate was malformed
        costs the annotator the case.
        """
        if self.project is None or not points:
            return
        names = {spec.name for spec in self.project.segments}
        for name, placed in points.items():
            if name not in names:
                # A branch the project no longer has. Dropping its markers is
                # right: there is no segment left for them to fill.
                continue
            node = self.markerNode(name)
            if node is None:
                continue
            for ras in placed:
                try:
                    node.AddControlPoint(
                        vtk.vtkVector3d(float(ras[0]), float(ras[1]), float(ras[2])))
                except Exception:
                    continue

    def saveMarkers(self):
        """Keep the branch markers with the case, beside the draft and the note.

        The markers *are* the division: given them, the same split is one press
        away, and without them an annotator who closes Slicer mid-case comes back
        to a segmentation they cannot adjust without re-marking every branch.
        They ride in the manifest and are purged with everything else on submit.
        """
        if self.assignment is None:
            return False
        try:
            self.cache.update(
                self.assignment.assignment_id,
                dividePoints=self.allMarkerPoints(),
                divideLasso={name: sorted(voxels)
                             for name, voxels in self._lassoVoxels.items()
                             if voxels})
        except Exception:
            # Runs from closeCase and from the autosave timer. A manifest that
            # will not take the markers is not a reason to fail either.
            return False
        return True

    def savedMarkers(self):
        """Markers stored with the case by an earlier session."""
        if self.assignment is None:
            return {}
        manifest = self.cache.manifest(self.assignment.assignment_id) or {}
        points = manifest.get("dividePoints") or {}
        return points if isinstance(points, dict) else {}

    def restoreLasso(self):
        """Put circled regions back after a reopen.

        Stored as voxel indices, which are only meaningful against this case's
        own grid -- which is fine, because they are stored in this case's own
        manifest and purged with it. Never raises, for the same reason
        ``restoreMarkers`` does not: coming back without them costs a gesture,
        and refusing to open the case costs the case.
        """
        if self.assignment is None:
            return
        manifest = self.cache.manifest(self.assignment.assignment_id) or {}
        stored = manifest.get("divideLasso") or {}
        if not isinstance(stored, dict):
            return
        for name, voxels in stored.items():
            try:
                self._lassoVoxels[name] = {
                    (int(v[0]), int(v[1]), int(v[2])) for v in voxels}
            except (TypeError, ValueError, IndexError):
                continue

    def clearMarkers(self, name=None):
        """Remove one branch's markers, or every branch's."""
        if self.project is None:
            return
        for spec in self.project.segments:
            if name is not None and spec.name != name:
                continue
            node = self.markerNode(spec.name, create=False)
            if node is not None:
                node.RemoveAllControlPoints()

    def removeMarkerNodes(self):
        """Take the marker nodes out of the scene entirely, on case close."""
        if self.project is None:
            return
        for spec in self.project.segments:
            node = self.markerNode(spec.name, create=False)
            if node is not None:
                slicer.mrmlScene.RemoveNode(node)

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

        The seed is the thing the annotator has been asked to divide, so seeing
        the whole tree at once is not a nicety: which arm is the LAD and which is
        the LCx is a question about the *shape* of the tree, and answering it by
        scrolling slices is how a branch ends up half-labelled. The 2D views show
        a cross-section of a vessel; the 3D view shows the vessel.

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
        self.saveMarkers()
        self.removeMarkerNodes()
        self.forgetSplit()
        self.clearLasso()
        self._seedPieces = None
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
        self.saveMarkers()
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
        self.notesTimer = None
        self._reviewRows = []
        self._claimedSubmission = None
        self._segmentButtons = {}
        self._shortcuts = []
        self._slicerLogo = None
        self._pendingUpdate = None
        #: The armed freehand loop, while one is armed. See ``_LassoTool``.
        self._lasso = None
        #: What the last loop picked up, kept so the division it triggers can
        #: show it rather than replacing it a tenth of a second later.
        self._lassoNote = ""

    def _stopLasso(self):
        if self._lasso is not None:
            self._lasso.stop()
            self._lasso = None

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
        self._buildVesselSection()
        self._buildEditorSection()
        self._buildSubmitSection()
        self._buildReviewSection()
        self.layout.addStretch(1)
        self._installShortcuts()

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
        toolRow = qt.QHBoxLayout()
        self._toolButtons = {}
        for name, key, tip in VESSEL_EFFECTS:
            button = qt.QPushButton("{}  ({})".format(name, key))
            button.setToolTip(tip)
            button.clicked.connect(lambda _checked=False, n=name: self.onEffect(n))
            toolRow.addWidget(button)
            self._toolButtons[name] = button
        layout.addLayout(toolRow)

        self.applyTubeButton = qt.QPushButton("Apply tube  (A)")
        self.applyTubeButton.setToolTip(
            "Add the section you just placed to the selected vessel, then start "
            "the next one. Sections accumulate, so draw a wide one proximally "
            "and narrower ones as the artery tapers. Needs at least two points.")
        self.applyTubeButton.clicked.connect(self.onApplyTube)
        layout.addWidget(self.applyTubeButton)

        sizes = qt.QFormLayout()
        self.tubeRadiusSlider = _mmSlider(
            TUBE_RADIUS_RANGE_MM,
            _storedFloat(_SETTING_TUBE_RADIUS, TUBE_RADIUS_MM),
            "Radius of the tube swept along the points you place. Change it "
            "mid-vessel as the artery tapers -- the preview updates as you drag.")
        self.tubeRadiusSlider.connect("valueChanged(double)", self.onTubeRadiusChanged)
        sizes.addRow("Tube radius:", self.tubeRadiusSlider)

        self.brushSlider = _mmSlider(
            BRUSH_RANGE_MM, _storedFloat(_SETTING_BRUSH, BRUSH_DIAMETER_MM),
            "Diameter of the paint brush, in millimetres rather than screen "
            "pixels, so it stays the same size as you zoom.")
        self.brushSlider.connect("valueChanged(double)", self.onBrushChanged)
        sizes.addRow("Brush diameter:", self.brushSlider)
        layout.addLayout(sizes)

        self.toolWarning = qt.QLabel()
        self.toolWarning.setWordWrap(True)
        self.toolWarning.setStyleSheet("QLabel { color: #8a3b00; }")
        self.toolWarning.setVisible(False)
        layout.addWidget(self.toolWarning)

        layout.addWidget(_caption(
            "Every other effect is still available in the Segment Editor below."))

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

        self.seed3dCheck = qt.QCheckBox("Show the mask in the 3D view")
        self.seed3dCheck.setToolTip(
            "Renders the whole tree at once. Which arm is the LAD and which is "
            "the LCx is a question about the shape of the tree, and the 3D view "
            "is where that is one glance rather than forty slices.")
        self.seed3dCheck.setChecked(_storedBool(_SETTING_SEED_3D, True))
        self.seed3dCheck.toggled.connect(self.onShowSeed3d)
        seedLayout.addWidget(self.seed3dCheck)

        seedLayout.addWidget(_caption(
            "The fastest way to split it: pick a vessel above, press "
            "<b>Circle branch</b>, and drag a loop around that artery in the 3D "
            "view. It fills in straight away. Repeat for each branch.<br><br>"
            "Everything under the loop goes to that vessel — what is "
            "<i>behind</i> another branch is left alone, so circling the LAD "
            "does not take the RCA sitting behind it. The rest of the branch "
            "fills in from what you circled, so you only need the part you can "
            "see."))

        self.lassoButton = qt.QPushButton("Circle branch in 3D  (L)")
        self.lassoButton.setToolTip(
            "Drag a loop around the selected vessel in the 3D view. One loop "
            "per press: the view rotates normally again as soon as you let go.")
        self.lassoButton.clicked.connect(self.onLasso)
        seedLayout.addWidget(self.lassoButton)

        seedLayout.addWidget(_caption(
            "Or mark the branches by clicking points down them — better where "
            "two vessels overlap from every angle — then press <b>Divide</b>. "
            "Either way, every voxel of the mask goes to the branch whose "
            "points are nearest <i>along the vessel</i>, so the LAD and the LCx "
            "separate correctly even though they meet at the left main."))

        divideRow = qt.QHBoxLayout()
        self.markButton = qt.QPushButton("Mark branch (M)")
        self.markButton.setToolTip(
            "Starts dropping points on the selected vessel. Click down the "
            "middle of the artery; a few are plenty, and more only matter where "
            "two branches meet. Press again after switching vessel.")
        self.markButton.clicked.connect(self.onMarkBranch)
        divideRow.addWidget(self.markButton)

        self.divideButton = qt.QPushButton("Divide (D)")
        self.divideButton.setToolTip(
            "Splits the mask between the branches you have marked and fills "
            "them in. Safe to run again after adding points -- your own painting "
            "is kept.")
        self.divideButton.clicked.connect(self.onDivide)
        divideRow.addWidget(self.divideButton)
        seedLayout.addLayout(divideRow)

        self.divideStatus = qt.QLabel()
        self.divideStatus.setWordWrap(True)
        self.divideStatus.setStyleSheet("QLabel { color: #5a5f66; }")
        self.divideStatus.setVisible(False)
        seedLayout.addWidget(self.divideStatus)

        extraRow = qt.QHBoxLayout()
        self.clearMarkersButton = qt.QPushButton("Clear markers")
        self.clearMarkersButton.setToolTip(
            "Removes every branch marker. What has already been divided into "
            "the vessels stays -- this only forgets where the points were.")
        self.clearMarkersButton.clicked.connect(self.onClearMarkers)
        extraRow.addWidget(self.clearMarkersButton)

        self.copySeedButton = qt.QPushButton("Add the whole mask to this vessel")
        self.copySeedButton.setToolTip(
            "Copies the entire tree into the selected branch. Useful for the "
            "branch that dominates the tree -- then trim with Scissors.")
        self.copySeedButton.clicked.connect(self.onCopySeed)
        extraRow.addWidget(self.copySeedButton)
        seedLayout.addLayout(extraRow)

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
                      self.checklistTimer, self.notesTimer):
            if timer is not None:
                timer.stop()
        for shortcut in self._shortcuts:
            shortcut.setParent(None)
        self._shortcuts = []
        self._restorePanelBranding()
        self._stopPlacing()
        self._stopLasso()
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
        # should not leave our name over somebody else's panel -- nor our point
        # placement armed over somebody else's views, where every click would
        # land a branch marker in a module that has never heard of them.
        self._restorePanelBranding()
        self._stopPlacing()
        self._stopLasso()
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

        self._checkToolsAvailable()
        self.seedGroup.setVisible(bool(self.logic.seedSegmentId))
        self.jumpButton.setEnabled(bool(self.logic.regionSegmentId))
        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        # The mask goes into the 3D view as the case opens rather than on a
        # button, because it is the first question of the case -- where do these
        # branches go -- and an annotator who has to ask for it has usually
        # already started scrolling slices to answer it the slow way.
        self._setDivideStatus("")
        self.onShowSeed3d()
        self.onMaskingChanged()
        if self.logic.project.segments:
            self.onSelectSegment(self.logic.project.segments[0].name)
        self._updateChecklist()

        self.caseBox.collapsed = False
        self.vesselBox.collapsed = False
        # Left open on purpose. Draw tube's Apply button, and its point add and
        # delete controls, live in the effect's own options frame inside this
        # widget -- collapsing it leaves the annotator with a tool they can
        # start and cannot finish.
        self.editorBox.collapsed = False
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
        self._followMarkerTarget(name)

    def _followMarkerTarget(self, name):
        """While marking branches, a vessel change moves the markers with it.

        Pressing 2 in the middle of marking means "this next run of clicks is the
        LCx", and having it silently keep filing them under the LAD is a mistake
        an annotator only finds after dividing. Does nothing unless placement is
        actually armed, so the number keys behave exactly as before at every
        other moment.
        """
        if self.logic is None or not self.logic.seedSegmentId:
            return
        interaction = slicer.app.applicationLogic().GetInteractionNode()
        if interaction.GetCurrentInteractionMode() != interaction.Place:
            return
        node = self.logic.markerNode(name)
        if node is None:
            return
        selection = slicer.app.applicationLogic().GetSelectionNode()
        if selection.GetActivePlaceNodeID() == node.GetID():
            return
        selection.SetActivePlaceNodeID(node.GetID())
        self._setDivideStatus(
            "Clicking down <b>{}</b>. Press D to divide, or pick another vessel."
            .format(_shortName(name)))

    def onEffect(self, name):
        """Activate an effect and apply this panel's sizes to it."""
        if self.editorWidget is None:
            return
        self.editorWidget.setActiveEffectByName(name)
        effect = self.editorWidget.activeEffect()
        if effect is None:
            self._reportMissingEffect(name)
            return

        if name == "Paint":
            self._applyBrush(effect)
        elif name == TUBE_EFFECT:
            self._applyTubeRadius(effect)
            # The effect's activate() explicitly turns point placement *off*,
            # expecting the annotator to arm it from its own options frame. Ours
            # is a one-press button, so pressing it has to mean "I am about to
            # place points" -- otherwise the tool looks broken: it lights up and
            # clicking the image does nothing.
            self._setTubePlaceMode(effect, True)
            self.editorBox.collapsed = False

    def _reportMissingEffect(self, name):
        """Say which extension is missing, rather than that something failed."""
        if name == TUBE_EFFECT:
            message = (
                "The '{}' effect is not installed.\n\nIt comes from the {} "
                "extension: Extensions Manager \u2192 Install Extensions \u2192 "
                "search for it \u2192 restart Slicer.\n\nUntil then you can "
                "still segment with Paint, it is just slower."
            ).format(TUBE_EFFECT, TUBE_EXTENSION)
        else:
            message = "This build of Slicer has no '{}' effect.".format(name)
        self.toolWarning.setText(message.replace("\n\n", " "))
        self.toolWarning.setVisible(True)
        slicer.util.errorDisplay(message)

    def _applyBrush(self, effect):
        # Sized in millimetres rather than screen pixels, so it stays correct
        # when the annotator zooms -- which they will, constantly.
        effect.setParameter("BrushSphere", "1")
        effect.setParameter("BrushDiameterIsRelative", "0")
        effect.setParameter("BrushAbsoluteDiameter", str(self.brushSlider.value))

    def _applyTubeRadius(self, effect):
        """Push the slider's radius into the tube effect.

        The radius is not a scripted-effect parameter -- it lives on the
        effect's own logic object, and its spin box is what keeps the two in
        step. Writing the spin box rather than the logic attribute is therefore
        deliberate: it updates the effect's visible control *and* triggers the
        preview redraw, so dragging this slider reshapes the tube already on
        screen. Setting ``logic.radius`` alone would change the next apply and
        nothing the annotator can see.
        """
        try:
            effect.self().radiusSpinBox.value = float(self.tubeRadiusSlider.value)
            return True
        except AttributeError:
            # A future version of the effect that renamed its control. The tube
            # still works at its own default; only this slider stops steering it.
            return False

    def _setTubePlaceMode(self, effect, enabled):
        """Arm or disarm control-point placement for the tube effect."""
        try:
            effect.self().fiducialPlacementToggle.setPlaceModeEnabled(bool(enabled))
            return True
        except AttributeError:
            return False

    def _tubeEffect(self):
        """The active tube effect, or None."""
        if self.editorWidget is None:
            return None
        effect = self.editorWidget.activeEffect()
        if effect is None or effect.name != TUBE_EFFECT:
            return None
        return effect

    def onApplyTube(self):
        """Add the placed section to the selected vessel, then start the next.

        Draw tube applies with ``ModificationModeSet``: it *replaces* the
        selected segment rather than adding to it. Applied directly, a second
        section would erase the first, and a coronary artery cannot be drawn as
        one tube -- it tapers, so it takes a wide proximal section and
        progressively narrower ones down the vessel.

        So the tube goes into a hidden scratch segment, which is then unioned
        into the vessel and emptied. Each apply becomes an addition, and the
        radius slider is free to change between sections. Slicer's own Undo
        still covers the whole thing, because both steps save undo state.
        """
        effect = self._tubeEffect()
        if effect is None:
            slicer.util.errorDisplay(
                "Select the {} tool first (Q).".format(TUBE_EFFECT))
            return

        active = next((n for n, b in self._segmentButtons.items() if b.checked), None)
        target = self.logic.segmentIdFor(active) if active else None
        if target is None:
            slicer.util.errorDisplay("Choose a vessel first (1-4).")
            return

        try:
            placed = effect.self().getNumberOfDefinedControlPoints()
        except AttributeError:
            placed = 2  # unknown build; let the effect decide
        if placed < 2:
            slicer.util.errorDisplay(
                "Place at least two points down the middle of the vessel "
                "before applying.\n\nClick along the artery in a slice view; "
                "the tube follows the points.")
            return

        with _busy():
            scratch = self.logic.scratchSegmentId()
            self.editorNode.SetSelectedSegmentID(scratch)
            effect.self().onApply()

            self.editorNode.SetSelectedSegmentID(target)
            merged = self._logicalOp("UNION", scratch)
            # Emptied, not deleted. Deleting it is tidier -- it leaves no extra
            # row in the segment list -- but removing a segment reshuffles the
            # segmentation's labelmap layers, and measurably cost voxels from
            # sections already merged: three tapering sections came to 620 voxels
            # deleted against 810 emptied. An extra clearly-labelled empty row is
            # a much smaller price than silently losing part of a vessel.
            self._logicalOp("CLEAR", None, segmentId=scratch)

            self.editorNode.SetSelectedSegmentID(target)
            self.editorWidget.setActiveEffectByName(TUBE_EFFECT)
            effect = self.editorWidget.activeEffect()
            if effect is not None:
                self._applyTubeRadius(effect)
                self._setTubePlaceMode(effect, True)

        if not merged:
            slicer.util.errorDisplay(
                "Could not merge the section into {!r}. The 'Logical operators' "
                "effect is missing from this Slicer.".format(active))
        self._updateChecklist()

    def _logicalOp(self, operation, modifierSegmentId, segmentId=None):
        """Run one Logical operators apply. Returns False if the effect is absent."""
        if segmentId is not None:
            self.editorNode.SetSelectedSegmentID(segmentId)
        self.editorWidget.setActiveEffectByName("Logical operators")
        effect = self.editorWidget.activeEffect()
        if effect is None:
            return False
        effect.setParameter("Operation", operation)
        if modifierSegmentId:
            effect.setParameter("ModifierSegmentID", modifierSegmentId)
        # Without this the merge is clipped by whatever mask is in force -- the
        # coronary seed, or the intensity window -- and a section drawn slightly
        # outside either would be silently trimmed on the way in.
        effect.setParameter("BypassMasking", "1")
        effect.self().onApply()
        return True

    def onTubeRadiusChanged(self, value):
        qt.QSettings().setValue(_SETTING_TUBE_RADIUS, float(value))
        effect = self.editorWidget.activeEffect() if self.editorWidget else None
        if effect is not None and effect.name == TUBE_EFFECT:
            self._applyTubeRadius(effect)

    def onBrushChanged(self, value):
        qt.QSettings().setValue(_SETTING_BRUSH, float(value))
        effect = self.editorWidget.activeEffect() if self.editorWidget else None
        if effect is not None and effect.name == "Paint":
            self._applyBrush(effect)

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

    # ------------------------------------------------------ dividing the seed

    def _activeSegmentName(self):
        return next((n for n, b in self._segmentButtons.items() if b.checked), None)

    def onShowSeed3d(self, checked=None):
        """Put the coronary mask into the 3D view, or take it out."""
        if self.logic is None:
            return
        on = bool(self.seed3dCheck.checked)
        qt.QSettings().setValue(_SETTING_SEED_3D, on)
        if not self.logic.seedSegmentId:
            return
        with _busy():
            self.logic.showSeedIn3d(on)

    def onMarkBranch(self):
        """Start dropping division markers on the selected vessel.

        Placement is persistent, so the annotator clicks their way down the
        artery without going back to a button between points -- which is the same
        bargain Draw tube makes, and for the same reason: the points come in runs
        of five or ten, not singly.
        """
        if self.logic is None or self.logic.project is None:
            return
        if self.logic.assignment is None:
            return
        active = self._activeSegmentName()
        if active is None:
            slicer.util.errorDisplay("Choose a vessel first (1-4).")
            return
        node = self.logic.markerNode(active)
        if node is None:
            return

        # Leaving an effect armed while placing markers means the next click
        # paints as well as marking.
        if self.editorWidget is not None:
            self.editorWidget.setActiveEffectByName("")

        selection = slicer.app.applicationLogic().GetSelectionNode()
        selection.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        selection.SetActivePlaceNodeID(node.GetID())
        interaction = slicer.app.applicationLogic().GetInteractionNode()
        interaction.SetPlaceModePersistence(1)
        interaction.SetCurrentInteractionMode(interaction.Place)
        self._setDivideStatus(
            "Clicking down <b>{}</b>. Press D to divide, or pick another vessel "
            "and press M again.".format(_shortName(active)))

    def _stopPlacing(self):
        interaction = slicer.app.applicationLogic().GetInteractionNode()
        interaction.SetCurrentInteractionMode(interaction.ViewTransform)

    # ------------------------------------------------------ circling in 3D

    def _threeDView(self):
        layoutManager = slicer.app.layoutManager()
        if layoutManager is None or layoutManager.threeDViewCount < 1:
            return None
        widget = layoutManager.threeDWidget(0)
        return widget.threeDView() if widget is not None else None

    def onLasso(self):
        """Arm one freehand loop in the 3D view for the selected vessel."""
        if self.logic is None or self.logic.assignment is None:
            return
        if not self.logic.seedSegmentId:
            return
        active = self._activeSegmentName()
        if active is None:
            slicer.util.errorDisplay("Choose a vessel first (1-4).")
            return
        if not self.seed3dCheck.checked:
            slicer.util.errorDisplay(
                "Turn on 'Show the mask in the 3D view' first — there is "
                "nothing to circle otherwise.")
            return

        view = self._threeDView()
        if view is None:
            slicer.util.errorDisplay(
                "This layout has no 3D view. Switch to Four-Up and try again.")
            return

        # Neither of these should be live while the left button is drawing a
        # loop: one would paint under it, the other would drop a marker.
        self._stopPlacing()
        if self.editorWidget is not None:
            self.editorWidget.setActiveEffectByName("")

        if self._lasso is not None:
            self._lasso.stop()
        self._lasso = _LassoTool(
            view, lambda path, renderer, name=active: self._onLassoDone(
                path, renderer, name))
        self._lasso.start()
        self._setDivideStatus(
            "Drag a loop around <b>{}</b> in the 3D view.".format(
                _shortName(active)))

    def _onLassoDone(self, path, renderer, name):
        """A loop was drawn: take what is under it and re-divide."""
        self._lasso = None
        if self.logic is None or lasso_geom is None:
            return

        polygon = lasso_geom.simplify(path)
        if len(polygon) < 3:
            self._setDivideStatus("")
            return

        with _busy():
            try:
                voxels = self.logic.seedVoxels()
                projected = self.logic.projectSeed(renderer, voxels)
                picked = lasso_geom.select_visible(
                    projected, polygon, pieces=self.logic.seedPieces())
            except Exception:
                slicer.util.errorDisplay(
                    "Could not read what that loop covered:\n\n"
                    + traceback.format_exc())
                return

        if not picked:
            self._setDivideStatus(lasso_geom.describe(picked, _shortName(name)))
            return

        self.logic.addLassoVoxels(name, picked.voxels)
        self._lassoNote = lasso_geom.describe(picked, _shortName(name))
        # Divide straight away. "Circle a branch and it becomes that branch" is
        # the whole gesture, and making the annotator press a second button to
        # see whether it worked breaks the loop they are actually in: circle,
        # look, adjust.
        self.onDivide()

    def onDivide(self):
        """Split the mask between the marked branches and fill them in."""
        if self.logic is None or not self.logic.seedSegmentId:
            return
        markers = self.logic.allMarkerPoints()
        if not markers and not self.logic.hasLasso():
            slicer.util.errorDisplay(
                "Nothing is marked yet.\n\nPick a vessel and either press "
                "'Circle branch in 3D' (L) and drag a loop around that artery "
                "in the 3D view, or press 'Mark branch' (M) and click a few "
                "points down it. Repeat for each branch.")
            return

        self._stopPlacing()
        with _busy():
            try:
                split = self.logic.computeSplit(markers)
                self._applySplit(split)
            except SegQueueError as exc:
                slicer.util.errorDisplay(str(exc))
                return
            except Exception:
                slicer.util.errorDisplay(
                    "Could not divide the mask:\n\n" + traceback.format_exc())
                return
            self.logic.rememberSplit(split)
            active = self._activeSegmentName()
            if active:
                self.onSelectSegment(active)

        self._updateChecklist()
        self._reportSplit(split)

    def _applySplit(self, split):
        """Move each branch's share of the mask into its segment.

        Through the same ``Logical operators`` merge Draw tube applies with,
        rather than by writing the vessel's labelmap directly. That path has
        already been made to handle the two things that quietly break here --
        segmentation layers, and the editor's active mask clipping the write --
        and a second implementation of it would get to discover both again.
        """
        buffer = self.logic.splitBuffer()
        for name, claimed in split.assigned.items():
            target = self.logic.segmentIdFor(name)
            if target is None:
                continue
            # Out with the last division before in with this one, so re-dividing
            # after adding a marker keeps whatever was painted by hand.
            previous = self.logic.previousShare(name)
            if previous:
                scratch = self.logic.loadScratch(previous, buffer)
                if not self._logicalOp("SUBTRACT", scratch, segmentId=target):
                    raise SegQueueError(
                        "This build of Slicer has no 'Logical operators' effect, "
                        "which the divide tool needs.")
            scratch = self.logic.loadScratch(claimed, buffer)
            if not self._logicalOp("UNION", scratch, segmentId=target):
                raise SegQueueError(
                    "This build of Slicer has no 'Logical operators' effect, "
                    "which the divide tool needs.")

        self._logicalOp("CLEAR", None, segmentId=self.logic.scratchSegmentId())

    def _reportSplit(self, split):
        """Say what the division did, and complain about what it could not do.

        The split between the status line and a dialog is the whole point of this
        method. A real mask nearly always leaves a few disconnected specks, so a
        dialog for *any* leftover would put a modal in front of the annotator on
        every single divide -- and a warning that always fires is one nobody
        reads by the third case. The line under the buttons carries the ordinary
        result; the dialog is kept for the three things that mean the division is
        actually wrong and they need to do something about it.
        """
        counts = split.counts()
        placed = split.total_assigned()
        total = placed + len(split.unreachable)
        leftovers = seedsplit.describe_leftovers(split.unreachable)

        summary = ", ".join(
            "{} {}".format(_shortName(name), counts[name]) for name in counts)
        status = "Divided: {}.".format(summary) if summary else ""
        if leftovers:
            status = (status + " " + leftovers).strip()
        if self._lassoNote:
            status = (self._lassoNote + " " + status).strip()
            self._lassoNote = ""
        self._setDivideStatus(status)

        problems = []
        empty = split.empty_labels()
        if empty:
            problems.append(
                "These branches are marked but came out empty: {}.\n\nThe marker "
                "is probably beside the vessel rather than on it. Drag it onto "
                "the mask and divide again.".format(
                    ", ".join(_shortName(name) for name in empty)))

        strayed = [name for name, points in split.stray.items() if points]
        if strayed:
            problems.append(
                "Some markers are not on the mask at all ({}), and were "
                "ignored.".format(", ".join(_shortName(name) for name in strayed)))

        if leftovers and total and placed < total * DIVIDE_COVERAGE_WARNING:
            problems.append(
                leftovers + "\n\nThat is most of the mask, so a branch you have "
                "not marked is probably sitting there unclaimed. Mark it and "
                "divide again.")

        if problems:
            slicer.util.warningDisplay("\n\n".join(problems))

    def onClearMarkers(self):
        """Forget every marker and circled region, leaving the vessels as they are."""
        if self.logic is None:
            return
        self._stopPlacing()
        self._stopLasso()
        self._lassoNote = ""
        self.logic.clearMarkers()
        self.logic.clearLasso()
        # Forgetting the markers has to forget the division they produced too.
        # Otherwise the next divide subtracts a partition nothing on screen
        # refers to any more, and takes the annotator's corrections with it.
        self.logic.forgetSplit()
        self._setDivideStatus("")

    def _setDivideStatus(self, text):
        self.divideStatus.setText(text)
        self.divideStatus.setVisible(bool(text))

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
        if not self._logicalOp("UNION", self.logic.seedSegmentId):
            slicer.util.errorDisplay(
                "This build of Slicer has no 'Logical operators' effect.")
            return
        self.editorWidget.setActiveEffectByName("")
        self._updateChecklist()

    def _checkToolsAvailable(self):
        """Flag a missing tube effect on case open, not on first click.

        An annotator who discovers the main tool is absent halfway through their
        first case has already wasted the part of the session where they were
        most willing to ask for help.
        """
        if self.editorWidget is None:
            return
        available = list(self.editorWidget.availableEffectNames())
        missing = TUBE_EFFECT not in available
        button = self._toolButtons.get(TUBE_EFFECT)
        if button is not None:
            button.setEnabled(not missing)
        if missing:
            self.toolWarning.setText(
                "The '{}' effect is missing. Install the {} extension "
                "(Extensions Manager \u2192 Install Extensions) and restart. "
                "Paint still works meanwhile.".format(TUBE_EFFECT, TUBE_EXTENSION))
        self.toolWarning.setVisible(missing)
        self.tubeRadiusSlider.setEnabled(not missing)
        self.applyTubeButton.setEnabled(not missing)

    def onJumpToHeart(self):
        if self.logic is not None and not self.logic.jumpToHeart():
            slicer.util.errorDisplay("This case has no heart mask to centre on.")

    def onShow3d(self):
        if self.logic is None or self.logic.segmentationNode is None:
            return
        with _busy():
            self.logic.segmentationNode.CreateClosedSurfaceRepresentation()
            # Scaffolding stays out of the 3D view -- a solid heart would hide
            # the very tree the annotator opened 3D to inspect -- with the
            # coronary mask the deliberate exception, because comparing the
            # branches drawn so far against the mask they came from is most of
            # what the 3D view is for on a seeded case.
            self.logic.showSeedIn3d(bool(self.seed3dCheck.checked))
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
        bindings.append(("A", self.onApplyTube))
        bindings.append(("M", self.onMarkBranch))
        bindings.append(("D", self.onDivide))
        bindings.append(("L", self.onLasso))

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
        self.seedGroup.setVisible(False)
        self._stopLasso()
        self._setDivideStatus("")
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
        self._clearNotes()
        self.reworkBox.setVisible(False)
        self.seedGroup.setVisible(False)
        self._stopLasso()
        self._setDivideStatus("")
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


def _mmSlider(rangeMm, value, tooltip):
    """A millimetre slider with a spin box beside it, for a physical size."""
    slider = ctk.ctkSliderWidget()
    slider.minimum, slider.maximum = rangeMm
    slider.singleStep = 0.05
    slider.decimals = 2
    slider.suffix = " mm"
    slider.value = max(rangeMm[0], min(rangeMm[1], float(value)))
    slider.setToolTip(tooltip)
    return slider


def _storedFloat(key, default):
    try:
        return float(slicer.util.settingsValue(key, str(default)))
    except (TypeError, ValueError):
        return default


def _matrixArray(matrix):
    """A vtkMatrix4x4 as a 4x4 numpy array, so points can be transformed in bulk.

    VTK's own ``MultiplyPoint`` is per-point and crosses the Python boundary each
    time, which is fine for a marker and hopeless for a mask: the projection in
    ``projectSeed`` runs it over tens of thousands of voxels on a mouse release.
    """
    return np.array([[matrix.GetElement(row, column) for column in range(4)]
                     for row in range(4)], dtype=np.float64)


def _storedBool(key, default):
    """A checkbox's remembered state.

    ``settingsValue`` hands back the string QSettings stored, and ``bool("false")``
    is ``True`` -- which would turn every remembered "off" back on at the next
    launch, silently, once per annotator per session.
    """
    return slicer.util.settingsValue(key, default, converter=slicer.util.toBool)


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
