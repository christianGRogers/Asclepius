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

# Same trick SegmentatorTrainMonitor uses: make the repository's own packages
# importable without installing anything into Slicer's Python.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC = os.path.join(_REPO_ROOT, "src")
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

try:
    from segqueue import states as st
    from segqueue.checksum import sha256_file, verify_file
    from segqueue.protocol import SubmissionMeta
    from segqueue.segcheck import ERROR, Geometry, blocking, check_submission, summarise
    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - surfaced in the UI instead
    st = None
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

        volumePath = manifest.get("volumePath") or self.cache.volumePath(
            assignment.assignment_id, assignment.case_name)
        if not self._cachedVolumeIsGood(volumePath, assignment):
            self.client.downloadCase(assignment.case_id, volumePath, progress=progress)
            # Verify before loading, not after. A truncated NRRD often loads
            # perfectly well and is simply missing its last slices, which is
            # exactly the kind of silent data loss requirement N3 forbids.
            verify_file(volumePath, assignment.checksum)
        self.cache.update(assignment.assignment_id, volumePath=volumePath)

        self.volumeNode = slicer.util.loadVolume(volumePath)
        self.volumeNode.SetName(assignment.case_name or "case")
        self._loadOrCreateSegmentation(manifest)
        slicer.util.setSliceViewerLayers(background=self.volumeNode, fit=True)
        self._sessionStart = time.time()
        return manifest

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

        Deliberately not a plain ``saveNode`` of the segmentation. Slicer stores
        a ``.seg.nrrd`` binary labelmap cropped to the segments' own bounding
        box, so the file's grid is *not* the source volume's -- it would fail the
        geometry check this module is about to run, and downstream code would
        have to re-register every submission against its CT. Exporting against
        the reference geometry gives a volume that overlays the source voxel for
        voxel, which is what both the QA scorer and the training conversion want.

        Returns ``(voxelCounts, sourceGeometry, segmentationGeometry)``.
        """
        labelmapNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLLabelMapVolumeNode", "SegQueueExport")
        try:
            ok = slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(
                self.segmentationNode, labelmapNode,
                slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY)
            if not ok:
                raise RuntimeError(
                    "Slicer could not export the segments to a label volume.")
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
        self._reviewRows = []
        self._claimedSubmission = None

    # ------------------------------------------------------------------ setup

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        if _IMPORT_ERROR:
            label = qt.QLabel(
                "Could not import the segqueue package:\n{}\n\nExpected it at {}.\n"
                "Load this module from inside a checkout of the Asclepius "
                "repository.".format(_IMPORT_ERROR, _SRC))
            label.setWordWrap(True)
            self.layout.addWidget(label)
            return

        self.logic = SegQueueLogic()

        self._buildLoginSection()
        self._buildCaseSection()
        self._buildEditorSection()
        self._buildSubmitSection()
        self._buildReviewSection()
        self.layout.addStretch(1)

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

    def cleanup(self):
        """Slicer is closing or the module is being reloaded.

        The last autosave here is the one that saves an annotator who quits
        Slicer without submitting, which is a routine end to a session.
        """
        for timer in (self.autosaveTimer, self.heartbeatTimer, self.clockTimer):
            if timer is not None:
                timer.stop()
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
        self.caseBox.collapsed = False
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
        self.reworkBox.setVisible(False)
        self._bindEditor(None, None)
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
