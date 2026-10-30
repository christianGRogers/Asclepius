"""JanusMRead -- read one Janus-M case's borders in 3D Slicer and send the read back.

Shown in Slicer as **Janus-M Read**. It talks only to the Janus-M read queue
(``/api/v1/janusm``, protocol ``janusm-read`` 1; ``docs/JANUSM-READ-PROTOCOL.md``),
through ``janusm_reads.client``. It is not SegQueue14: its own module name, library
(``JanusMReadLib``), settings (``JanusMRead/...``), cache (``~/.janusm-read``),
archive (``JanusMRead-<v>-Slicer-<x.y>.zip``) and release tag (``janusm-read-v<v>``).
A SegQueue14 install is never offered it, and it is never offered SegQueue14.

What a reader does:

* **Get next case** takes a case, downloads its CT (checked against the case
  checksum) and, unless the case is read from blank, its seed, loaded into the four
  JA1 segments by label value. A blank case starts with the four segments empty.
* The reader draws the four classes under border protocol v1 (JA21, JA46). A
  seeded case opens with its plateaus measured from the seed and on the **border
  window** of the endocardium: level at the half-maximum, width 1.5 x the gap
  between the plateaus. A blank case opens on 800 / 300 until the reader measures
  the plateaus from ROIs. The reader may switch borders, or to 800 / 300.
* The **read form** (JA46 (d)): the CAD-RADS 2.0 grade of each main coronary's worst
  lesion, and optionally its point. It goes to the server with the read and is never
  shown to another reader.
* **Submit** refuses a read whose values are outside 0-4, whose classes overlap,
  with an empty class or an incomplete read form, before anything is uploaded. The
  server's automatic check is the authority. A read it returns comes back here with
  the reasons and the half-maximum profile plot; a read it returns once and fails
  again is accepted and flagged.

The reader is told only whether the case has a seed. Nothing in this module asks
for, or could show, the case's read set, whether it is scored, or the other read:
the read queue never sends them to a reader.
"""

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

__version__ = "0.2.0"

# The shared package, found two ways:
#   checkout   <repo>/slicer/JanusMRead/JanusMRead.py  with  <repo>/src/janusm_reads
#   packaged   .../qt-scripted-modules/JanusMRead.py   with  .../janusm_reads beside it
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_MODULE_DIR))
_SRC = os.path.join(_REPO_ROOT, "src")
_SHARED = _MODULE_DIR if os.path.isdir(os.path.join(_MODULE_DIR, "janusm_reads")) else _SRC
for _path in (_MODULE_DIR, _SHARED):
    if _path not in sys.path:
        sys.path.insert(0, _path)

_IMPORT_ERROR = None
try:
    from janusm_reads import PROTOCOL_NAME, PROTOCOL_VERSION, labels, protocol
    from janusm_reads.client import JanusMClient, JanusMError, sha256_file
    from JanusMReadLib import halfmax, precheck, updater
except Exception:  # pragma: no cover - shown in the panel instead of a blank module
    _IMPORT_ERROR = traceback.format_exc()

HELP_URL = "https://github.com/christianGRogers/Asclepius/blob/dev/docs/JANUSM-READ-PROTOCOL.md"
DEFAULT_SERVER_URL = "https://janus.bradensbay.com"
CLIENT_NAME = "JanusMRead-" + __version__

_SETTING_SERVER = "JanusMRead/serverUrl"
_SETTING_CACHE = "JanusMRead/cacheRoot"

#: The fixed window: available, never the default (protocol v1, section 3).
CT_WINDOW = 800
CT_LEVEL = 300
#: Markups point lists holding the read form's lesion points, one per vessel.
LESION_NODE_PREFIX = "Janus-M lesion "

CT_STEM = "ct"
SEED_FILE = "seed.nii.gz"
DRAFT_FILE = "draft.seg.nrrd"
READ_FILE = "read.nii.gz"


def defaultCacheRoot():
    return os.path.join(os.path.expanduser("~"), ".janusm-read")


class ReadRefused(RuntimeError):
    """The read cannot be uploaded yet; ``problems`` says why, in words."""

    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = list(problems)


class JanusMRead(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Janus-M Read"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Christian Rogers"]
        self.parent.helpText = (
            'Janus-M read protocol: <a href="{0}">{0}</a>'.format(HELP_URL))
        self.parent.acknowledgementText = ""
        icon = os.path.join(_MODULE_DIR, "Resources", "Icons", "JanusMRead.png")
        if os.path.isfile(icon):
            self.parent.icon = qt.QIcon(icon)


class _ReaderClient(JanusMClient if _IMPORT_ERROR is None else object):
    """``janusm_reads.client`` with this module named in its client header."""

    def _headers(self):
        headers = JanusMClient._headers(self)
        headers[protocol.CLIENT_VERSION_HEADER] = CLIENT_NAME
        return headers


# =============================================================================
#  Logic
# =============================================================================


class JanusMReadLogic(ScriptedLoadableModuleLogic):
    """Everything the module does, with no widgets in sight."""

    def __init__(self, cacheRoot=None):
        ScriptedLoadableModuleLogic.__init__(self)
        self.cacheRoot = cacheRoot or defaultCacheRoot()
        self.client = None
        self.project = None
        self.read = None
        self.volumeNode = None
        self.segmentationNode = None
        self.resumedDraft = False
        self.seedClasses = 0
        self.plateaus = {name: None for name in halfmax.PLATEAUS}
        self.border = halfmax.DEFAULT_BORDER
        self.windowMode = "border"
        self.cadrads = {}
        self.lesionNodes = {}
        self.profileChart = None
        self._openedAt = None

    # ------------------------------------------------------------ session

    def connect(self, serverUrl, username, password, session=None):
        client = _ReaderClient(serverUrl, session=session)
        user = client.login(username, password)
        self.useClient(client)
        return user

    def useClient(self, client):
        """Adopt a logged-in client and read the project (used by the self-test too)."""
        self.project = client.project()
        self.client = client

    def disconnect(self):
        self.closeCase()
        self.client = None
        self.project = None

    @property
    def loggedIn(self):
        return self.client is not None

    def openReads(self):
        return [r for r in self.client.my_reads() if r.state in protocol.OPEN_STATES]

    def takeNext(self):
        return self.client.next_read()

    def refreshRead(self):
        """The current read as the server has it now (its state and check summary)."""
        if self.read is None:
            return None
        for read in self.client.my_reads():
            if read.read_id == self.read.read_id:
                self.read = read
                break
        return self.read

    # --------------------------------------------------------------- cache

    def caseDir(self, readId):
        safe = "".join(c for c in str(readId) if c.isalnum() or c in "-_") or "read"
        path = os.path.join(self.cacheRoot, safe)
        os.makedirs(path, exist_ok=True)
        return path

    def purgeCache(self):
        shutil.rmtree(self.cacheRoot, ignore_errors=True)

    def _cachedCt(self, read, directory):
        for name in os.listdir(directory):
            if name.startswith(CT_STEM + ".") and not name.endswith(".part"):
                path = os.path.join(directory, name)
                if not read.checksum or sha256_file(path) == read.checksum:
                    return path
                os.unlink(path)
        return None

    def _fetchCt(self, read, directory):
        path = self._cachedCt(read, directory)
        if path:
            return path
        download = os.path.join(directory, CT_STEM + ".download")
        self.client.download_ct(read, download)
        path = os.path.join(directory, CT_STEM + precheck.sniff_suffix(download))
        os.replace(download, path)
        return path

    def _fetchSeed(self, read, directory):
        path = os.path.join(directory, SEED_FILE)
        if os.path.isfile(path):
            return path
        return self.client.download_seed(read, path)

    # ---------------------------------------------------------------- open

    def openRead(self, read):
        """Download and show one read: the CT, the four segments, the seed or a draft."""
        self.closeCase()
        directory = self.caseDir(read.read_id)
        ctPath = self._fetchCt(read, directory)
        self.volumeNode = slicer.util.loadVolume(ctPath)
        if self.volumeNode is None:
            raise RuntimeError("Slicer could not load the CT of " + read.case_name)
        self.volumeNode.SetName(read.case_name or "Janus-M case")
        self.read = read
        self.resumedDraft = False
        self.seedClasses = 0

        draft = os.path.join(directory, DRAFT_FILE)
        if os.path.isfile(draft):
            try:
                self.segmentationNode = slicer.util.loadSegmentation(draft)
                self.resumedDraft = self.segmentationNode is not None
            except Exception:
                self.segmentationNode = None
        if self.segmentationNode is None:
            self.segmentationNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLSegmentationNode", "Janus-M read")
        self.segmentationNode.CreateDefaultDisplayNodes()
        self.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(
            self.volumeNode)
        self.ensureSegments()
        if not self.resumedDraft and read.has_seed:
            seed = self._fetchSeed(read, directory)
            if seed:
                self.seedClasses = self.importLabels(seed)
        self.plateaus = {name: None for name in halfmax.PLATEAUS}
        self.border, self.windowMode = halfmax.DEFAULT_BORDER, "border"
        self.clearReadForm()
        if read.has_seed:
            # Protocol v1: the plateaus come from the seed when the case opens.
            self.measurePlateausFromSegments()
        self.openDefaultWindow()
        slicer.util.setSliceViewerLayers(background=self.volumeNode, fit=True)
        self._openedAt = time.time()
        return read

    def ensureSegments(self):
        """Exactly the four JA1 segments, named and coloured from ``janusm_reads.labels``."""
        segmentation = self.segmentationNode.GetSegmentation()
        for value, name in labels.CLASSES.items():
            segmentId = self.segmentIdFor(value)
            if segmentId is None:
                segmentId = segmentation.AddEmptySegment(name, name, list(labels.COLORS[value]))
            segment = segmentation.GetSegment(segmentId)
            segment.SetName(name)
            segment.SetColor(*labels.COLORS[value])

    def segmentIdFor(self, value):
        if self.segmentationNode is None:
            return None
        name = labels.CLASSES[int(value)]
        segmentation = self.segmentationNode.GetSegmentation()
        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            if segmentation.GetSegment(segmentId).GetName() == name:
                return segmentId
        return None

    def importLabels(self, path):
        """Load a 0-4 label volume into the four segments, one class at a time.

        One 0/1 mask per class into exactly one named segment, so a class absent
        from the seed cannot shift the others into the wrong segment. Values outside
        the four classes are dropped. Returns how many classes got voxels.
        """
        import numpy as np

        labelNode = scratch = None
        filled = 0
        try:
            labelNode = slicer.util.loadLabelVolume(path)
            values = slicer.util.arrayFromVolume(labelNode).copy()
            scratch = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLabelMapVolumeNode", "JanusMReadImport")
            logic = slicer.modules.segmentations.logic()
            for value in labels.CLASSES:
                mask = (values == int(value)).astype(np.uint8)
                if not mask.any():
                    continue
                slicer.util.updateVolumeFromArray(scratch, mask)
                scratch.CopyOrientation(labelNode)
                target = vtk.vtkStringArray()
                target.InsertNextValue(self.segmentIdFor(value))
                logic.ImportLabelmapToSegmentationNode(scratch, self.segmentationNode, target)
                filled += 1
            self.ensureSegments()
        finally:
            for node in (labelNode, scratch):
                if node is not None:
                    slicer.mrmlScene.RemoveNode(node)
        return filled

    # -------------------------------------------------------------- export

    def classMask(self, value):
        """One class as a boolean array on the CT grid (k, j, i)."""
        import numpy as np

        shape = slicer.util.arrayFromVolume(self.volumeNode).shape
        segmentId = self.segmentIdFor(value)
        if segmentId is None:
            return np.zeros(shape, bool)
        try:
            array = slicer.util.arrayFromSegmentBinaryLabelmap(
                self.segmentationNode, segmentId, self.volumeNode)
        except Exception:
            array = None
        if array is None or array.shape != shape:
            return np.zeros(shape, bool)
        return array > 0

    def labelArray(self):
        """``(labels, overlapping voxels)``: the read as one 0-4 array on the CT grid."""
        import numpy as np

        shape = slicer.util.arrayFromVolume(self.volumeNode).shape
        out = np.zeros(shape, np.uint8)
        taken = np.zeros(shape, np.uint8)
        for value in labels.CLASSES:
            mask = self.classMask(value)
            taken += mask
            out[mask] = value
        return out, int((taken > 1).sum())

    def exportRead(self, path):
        """Run the checks, then write the read. Raises :class:`ReadRefused` first if
        anything is wrong; returns ``{value: voxels}``."""
        import numpy as np

        values, overlap = self.labelArray()
        counts = precheck.voxel_counts(values)
        problems = precheck.problems(np.unique(values), counts, overlap)
        if problems:
            raise ReadRefused(problems)
        node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "JanusMReadExport")
        try:
            slicer.util.updateVolumeFromArray(node, values)
            node.CopyOrientation(self.volumeNode)
            if not slicer.util.saveNode(node, path):
                raise RuntimeError("Could not write the read to " + path)
        finally:
            slicer.mrmlScene.RemoveNode(node)
        return counts

    def saveDraft(self):
        if self.segmentationNode is None or self.read is None:
            return False
        return bool(slicer.util.saveNode(
            self.segmentationNode, os.path.join(self.caseDir(self.read.read_id), DRAFT_FILE)))

    def elapsedSeconds(self):
        return 0.0 if self._openedAt is None else max(0.0, time.time() - self._openedAt)

    def submit(self, note=""):
        """Check, export and upload the read and its form. Nothing is uploaded when a
        check fails."""
        if self.read is None:
            raise RuntimeError("No case is open.")
        cadrads, points = self.readForm()
        formProblems = protocol.read_form_problems(cadrads, points)
        if formProblems:
            raise ReadRefused(formProblems)
        path = os.path.join(self.caseDir(self.read.read_id), READ_FILE)
        counts = self.exportRead(path)
        self.saveDraft()
        self.read = self.client.submit(self.read, path, {str(k): v for k, v in counts.items()},
                                       seconds=self.elapsedSeconds(), note=note,
                                       cadrads=cadrads, lesion_points=points)
        return self.read

    # ----------------------------------------------------------- read form

    def setGrade(self, vessel, grade):
        """One vessel's CAD-RADS 2.0 grade (empty: not graded yet)."""
        if vessel not in protocol.VESSELS:
            raise ValueError("Not a graded vessel: " + str(vessel))
        grade = str(grade or "").strip().upper()
        if grade:
            self.cadrads[vessel] = grade
        else:
            self.cadrads.pop(vessel, None)

    def lesionNode(self, vessel, create=True):
        node = self.lesionNodes.get(vessel)
        if node is not None and node.GetScene() is None:
            node = None
        if node is None and create:
            node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode",
                                                      LESION_NODE_PREFIX + vessel)
            node.SetMaximumNumberOfControlPoints(1)
            self.lesionNodes[vessel] = node
        return node

    def setLesionPoint(self, vessel, ras):
        """The worst lesion of ``vessel`` at ``ras`` (world mm), replacing any other."""
        node = self.lesionNode(vessel)
        node.RemoveAllControlPoints()
        node.AddControlPointWorld(vtk.vtkVector3d(*[float(c) for c in ras]))
        return node

    def placeLesionPoint(self, vessel):
        """Let the reader click the worst lesion of ``vessel`` in a view."""
        node = self.lesionNode(vessel)
        node.RemoveAllControlPoints()
        slicer.modules.markups.logic().SetActiveList(node)
        slicer.modules.markups.logic().StartPlaceMode(False)
        return node

    def clearLesionPoint(self, vessel):
        node = self.lesionNode(vessel, create=False)
        if node is not None:
            node.RemoveAllControlPoints()

    def readForm(self):
        """``(cadrads, lesion points)`` as the read submits them."""
        points = {}
        for vessel in protocol.VESSELS:
            node = self.lesionNode(vessel, create=False)
            if node is not None and node.GetNumberOfControlPoints():
                ras = [0.0, 0.0, 0.0]
                node.GetNthControlPointPositionWorld(0, ras)
                points[vessel] = [float(c) for c in ras]
        return dict(self.cadrads), points

    def clearReadForm(self):
        self.cadrads = {}
        for node in list(self.lesionNodes.values()):
            if node is not None and node.GetScene() is not None:
                slicer.mrmlScene.RemoveNode(node)
        self.lesionNodes = {}

    def release(self):
        if self.read is None:
            return None
        done = self.client.release(self.read)
        readId = self.read.read_id
        self.closeCase()
        shutil.rmtree(os.path.join(self.cacheRoot, readId), ignore_errors=True)
        return done

    def closeCase(self):
        self.clearReadForm()
        self.clearProfile()
        for node in (self.segmentationNode, self.volumeNode):
            if node is not None and node.GetScene() is not None:
                slicer.mrmlScene.RemoveNode(node)
        self.segmentationNode = self.volumeNode = None
        self.read = None
        self._openedAt = None

    # ------------------------------------------------------- half-maximum

    def measurePlateausFromSegments(self):
        """Every plateau, measured from the current segments (the seed, at first)."""
        ct = slicer.util.arrayFromVolume(self.volumeNode)
        values, _overlap = self.labelArray()
        spacing = tuple(reversed(self.volumeNode.GetSpacing()))
        measured = halfmax.plateaus_from_labels(ct, values, spacing)
        for name, value in measured.items():
            if value is not None:
                self.plateaus[name] = value
        return measured

    def measurePlateauInRoi(self, name, roiNode):
        """One plateau, the mean HU inside the box of an ROI the reader placed."""
        bounds = [0.0] * 6
        roiNode.GetBounds(bounds)
        matrix = vtk.vtkMatrix4x4()
        self.volumeNode.GetRASToIJKMatrix(matrix)
        corners = []
        for x in bounds[0:2]:
            for y in bounds[2:4]:
                for z in bounds[4:6]:
                    corners.append(matrix.MultiplyPoint((x, y, z, 1.0))[:3])
        ct = slicer.util.arrayFromVolume(self.volumeNode)
        value = halfmax.roi_mean(ct, halfmax.box_slices(corners, ct.shape))
        if value is None:
            raise RuntimeError("The ROI is outside the CT.")
        self.plateaus[name] = value
        return value

    def setWindow(self, window, level):
        display = self.volumeNode.GetDisplayNode() if self.volumeNode is not None else None
        if display is None:
            return
        display.AutoWindowLevelOff()
        display.SetWindowLevel(float(window), float(level))

    def applyBorderWindow(self, border):
        """The border window: level at its half-maximum, width 1.5 x |p1 - p2|."""
        window, level = halfmax.window_for(border, self.plateaus)
        self.setWindow(window, level)
        self.border, self.windowMode = border, "border"
        return window, level

    def openDefaultWindow(self):
        """The current border's window when its plateaus are known, else 800 / 300 (a
        blank case before any ROI). Returns ``(window, level)``."""
        if self.windowMode == "border" and self.border in halfmax.thresholds(self.plateaus):
            window, level = halfmax.window_for(self.border, self.plateaus)
            self.setWindow(window, level)
            return window, level
        self.setWindow(CT_WINDOW, CT_LEVEL)
        return CT_WINDOW, CT_LEVEL

    def resetWindow(self):
        """The fixed 800 / 300 window, on request."""
        self.windowMode = "fixed"
        self.setWindow(CT_WINDOW, CT_LEVEL)

    # ----------------------------------------------------- returned reads

    def showProfile(self, border=None):
        """Plot a returned read's half-maximum profile: HU against signed distance from
        the reader's border, with both plateaus and the half level. ``border``
        defaults to the first that failed. Returns ``(border, chart node)``."""
        profiles = (self.read.check_profile if self.read is not None else {}) or {}
        if not profiles:
            raise RuntimeError("The check sent no half-maximum profile for this read.")
        if border is None:
            failed = [b for b, p in profiles.items() if p.get("failed")]
            border = (failed or sorted(profiles))[0]
        table = halfmax.profile_table(profiles[border])
        self.clearProfile()
        chart = slicer.util.plot(table, xColumnIndex=0, columnNames=list(halfmax.PROFILE_COLUMNS),
                                 title="Half-maximum profile: " + border, show=False)
        self.profileChart = chart
        layout = slicer.app.layoutManager()
        if layout is not None:
            slicer.modules.plots.logic().ShowChartInLayout(chart)
        return border, chart

    def clearProfile(self):
        chart = self.profileChart
        self.profileChart = None
        if chart is None or chart.GetScene() is None:
            return
        for i in range(chart.GetNumberOfPlotSeriesNodes()):
            series = chart.GetNthPlotSeriesNode(i)
            table = series.GetTableNode() if series is not None else None
            for node in (table, series):
                if node is not None and node.GetScene() is not None:
                    slicer.mrmlScene.RemoveNode(node)
        slicer.mrmlScene.RemoveNode(chart)


# =============================================================================
#  Widget
# =============================================================================


class JanusMReadWidget(ScriptedLoadableModuleWidget):
    def __init__(self, parent=None):
        # Set before the base class runs, which calls setup() when there is no parent.
        self.logic = None
        self.editorWidget = None
        self.editorNode = None
        self.roiNode = None
        self.plateauLabels = {}
        self.gradeCombos = {}
        ScriptedLoadableModuleWidget.__init__(self, parent)

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        if _IMPORT_ERROR:
            label = qt.QLabel("JanusMRead could not load its support code:\n\n" + _IMPORT_ERROR)
            label.setWordWrap(True)
            self.layout.addWidget(label)
            return
        self.logic = JanusMReadLogic(
            slicer.util.settingsValue(_SETTING_CACHE, defaultCacheRoot()))
        self._buildServerSection()
        self._buildReadSection()
        self._buildHalfMaxSection()
        self._buildEditorSection()
        self._buildReadFormSection()
        self._buildSubmitSection()
        self.layout.addStretch(1)
        self._updateEnabled()

    # ------------------------------------------------------------ sections

    def _buildServerSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Server"
        self.layout.addWidget(box)
        form = qt.QFormLayout(box)
        self.serverEdit = qt.QLineEdit(
            slicer.util.settingsValue(_SETTING_SERVER, DEFAULT_SERVER_URL))
        self.serverEdit.setToolTip("The server with the Janus-M read queue (/api/v1/janusm).")
        form.addRow("Server:", self.serverEdit)
        self.userEdit = qt.QLineEdit()
        self.userEdit.setPlaceholderText("Your username")
        self.userEdit.setToolTip("Not saved: type it each session.")
        self.userEdit.returnPressed.connect(self.onLogin)
        form.addRow("Username:", self.userEdit)
        self.passwordEdit = qt.QLineEdit()
        self.passwordEdit.setEchoMode(qt.QLineEdit.Password)
        self.passwordEdit.setToolTip("Never saved.")
        self.passwordEdit.returnPressed.connect(self.onLogin)
        form.addRow("Password:", self.passwordEdit)
        row = qt.QHBoxLayout()
        self.loginButton = qt.QPushButton("Log in")
        self.loginButton.clicked.connect(self.onLogin)
        self.logoutButton = qt.QPushButton("Log out")
        self.logoutButton.setToolTip("Logs out and deletes the locally cached cases.")
        self.logoutButton.clicked.connect(self.onLogout)
        row.addWidget(self.loginButton, 1)
        row.addWidget(self.logoutButton)
        form.addRow(row)
        status = qt.QHBoxLayout()
        self.statusLabel = qt.QLabel("Not logged in.")
        status.addWidget(self.statusLabel, 1)
        self.updateButton = qt.QPushButton("Check for updates")
        self.updateButton.setFlat(True)
        self.updateButton.setToolTip("Asks GitHub for a newer JanusMRead (janusm-read-v*).")
        self.updateButton.clicked.connect(self.onCheckForUpdates)
        status.addWidget(self.updateButton)
        form.addRow(status)

    def _buildReadSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Case"
        self.layout.addWidget(box)
        layout = qt.QVBoxLayout(box)
        self.caseLabel = qt.QLabel("No case open.")
        self.caseLabel.setWordWrap(True)
        layout.addWidget(self.caseLabel)
        self.checkLabel = qt.QLabel("")
        self.checkLabel.setWordWrap(True)
        layout.addWidget(self.checkLabel)
        row = qt.QHBoxLayout()
        self.nextButton = qt.QPushButton("Get next case")
        self.nextButton.setToolTip("Opens the read you hold, or takes the next case.")
        self.nextButton.clicked.connect(self.onNextCase)
        self.refreshButton = qt.QPushButton("Refresh status")
        self.refreshButton.setToolTip("Asks the server whether the automatic check has run.")
        self.refreshButton.clicked.connect(self.onRefresh)
        row.addWidget(self.nextButton, 1)
        row.addWidget(self.refreshButton)
        layout.addLayout(row)
        self.profileButton = qt.QPushButton("Show half-maximum profile")
        self.profileButton.setToolTip(
            "Plots the profile across the border the check returned: HU against distance "
            "from your border, with both plateaus and the half level.")
        self.profileButton.clicked.connect(self.onShowProfile)
        layout.addWidget(self.profileButton)
        legend = qt.QHBoxLayout()
        for value, name in labels.CLASSES.items():
            r, g, b = (int(255 * c) for c in labels.COLORS[value])
            label = qt.QLabel("<span style='color:rgb({},{},{})'>&#9632;</span> {}"
                              .format(r, g, b, name))
            label.setToolTip("{} ({}): {}".format(name, value, labels.CONVENTIONS[value]))
            legend.addWidget(label)
        layout.addLayout(legend)

    def _buildHalfMaxSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Half-maximum"
        self.layout.addWidget(box)
        self.halfMaxBox = box
        form = qt.QFormLayout(box)
        for name in halfmax.PLATEAUS:
            label = qt.QLabel("--")
            self.plateauLabels[name] = label
            form.addRow("{} plateau:".format(name), label)
        roiRow = qt.QHBoxLayout()
        self.plateauCombo = qt.QComboBox()
        for name in halfmax.PLATEAUS:
            self.plateauCombo.addItem(name)
        self.placeRoiButton = qt.QPushButton("Place ROI")
        self.placeRoiButton.setToolTip("Place a small box well inside one tissue, away from edges.")
        self.placeRoiButton.clicked.connect(self.onPlaceRoi)
        self.measureRoiButton = qt.QPushButton("Measure")
        self.measureRoiButton.setToolTip("Mean HU inside the ROI becomes the chosen plateau.")
        self.measureRoiButton.clicked.connect(self.onMeasureRoi)
        roiRow.addWidget(self.plateauCombo, 1)
        roiRow.addWidget(self.placeRoiButton)
        roiRow.addWidget(self.measureRoiButton)
        form.addRow("ROI:", roiRow)
        self.fromSegmentsButton = qt.QPushButton("Plateaus from the segments")
        self.fromSegmentsButton.setToolTip(
            "Measures every plateau from the current segments (the seed, until you edit).")
        self.fromSegmentsButton.clicked.connect(self.onPlateausFromSegments)
        form.addRow(self.fromSegmentsButton)
        borders = qt.QHBoxLayout()
        self.borderButtons = {}
        for border in halfmax.BORDERS:
            button = qt.QPushButton(border.capitalize())
            a, b = halfmax.BORDERS[border]
            button.setToolTip("Level at ({} + {}) / 2, width {:g} x |{} - {}|.".format(
                a, b, halfmax.BORDER_WIDTH_FACTOR, a, b))
            button.clicked.connect(lambda _=False, name=border: self.onBorderWindow(name))
            self.borderButtons[border] = button
            borders.addWidget(button)
        self.resetWindowButton = qt.QPushButton("800 / 300")
        self.resetWindowButton.setToolTip("The fixed window. The border window is the default.")
        self.resetWindowButton.clicked.connect(self.onResetWindow)
        borders.addWidget(self.resetWindowButton)
        form.addRow("Window at:", borders)
        self.halfMaxLabel = qt.QLabel("")
        self.halfMaxLabel.setWordWrap(True)
        form.addRow(self.halfMaxLabel)

    def _buildEditorSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Segment Editor"
        self.layout.addWidget(box)
        layout = qt.QVBoxLayout(box)
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

    def _buildReadFormSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Read form"
        self.layout.addWidget(box)
        self.readFormBox = box
        form = qt.QFormLayout(box)
        note = qt.QLabel("CAD-RADS 2.0 grade of each vessel's worst lesion (N: "
                         "non-diagnostic). Optionally mark the lesion.")
        note.setWordWrap(True)
        form.addRow(note)
        for vessel in protocol.VESSELS:
            row = qt.QHBoxLayout()
            combo = qt.QComboBox()
            combo.addItem("")
            for grade in protocol.CADRADS_GRADES:
                combo.addItem(grade)
            combo.currentTextChanged.connect(
                lambda text, name=vessel: self.onGrade(name, text))
            self.gradeCombos[vessel] = combo
            mark = qt.QPushButton("Mark lesion")
            mark.setToolTip("Click the worst lesion of this vessel in a view (optional).")
            mark.clicked.connect(lambda _=False, name=vessel: self.onMarkLesion(name))
            clear = qt.QPushButton("Clear")
            clear.clicked.connect(lambda _=False, name=vessel: self.onClearLesion(name))
            row.addWidget(combo, 1)
            row.addWidget(mark)
            row.addWidget(clear)
            form.addRow(vessel + ":", row)

    def _buildSubmitSection(self):
        box = ctk.ctkCollapsibleButton()
        box.text = "Submit"
        self.layout.addWidget(box)
        layout = qt.QVBoxLayout(box)
        self.noteEdit = qt.QLineEdit()
        self.noteEdit.setPlaceholderText("Optional note for this read")
        layout.addWidget(self.noteEdit)
        row = qt.QHBoxLayout()
        self.saveButton = qt.QPushButton("Save draft")
        self.saveButton.clicked.connect(self.onSaveDraft)
        self.submitButton = qt.QPushButton("Submit read")
        self.submitButton.clicked.connect(self.onSubmit)
        self.releaseButton = qt.QPushButton("Give back")
        self.releaseButton.setToolTip("Releases this case. It is never handed back to you.")
        self.releaseButton.clicked.connect(self.onRelease)
        row.addWidget(self.saveButton)
        row.addWidget(self.submitButton, 1)
        row.addWidget(self.releaseButton)
        layout.addLayout(row)
        self.submitLabel = qt.QLabel("")
        self.submitLabel.setWordWrap(True)
        layout.addWidget(self.submitLabel)

    # ------------------------------------------------------------- display

    def _showRead(self):
        read = self.logic.read
        if read is None:
            self.caseLabel.setText("No case open.")
            self.checkLabel.setText("")
            return
        if read.has_seed:
            start = ("Starts from the seed: correct it." if not self.logic.resumedDraft
                     else "Your saved draft is loaded.")
        else:
            start = "Read from blank: there is no seed for this case."
        self.caseLabel.setText("<b>{}</b> -- {}<br>{}".format(
            _escape(read.case_name), _escape(read.state), start))
        if read.state == protocol.RETURNED:
            lines = [halfmax.profile_caption(b, p) for b, p in
                     sorted((read.check_profile or {}).items()) if p.get("failed")]
            self.checkLabel.setText(
                "The automatic check returned this read. Fix it and submit again: a read "
                "that fails again is accepted and flagged.<br>"
                + _escape(read.check_summary or "(no reasons given)")
                + "".join("<br>" + _escape(line) for line in lines))
        elif read.state == protocol.SUBMITTED:
            self.checkLabel.setText("Submitted: waiting for the automatic check.")
        elif read.state == protocol.ACCEPTED and read.flagged:
            summary = read.check_summary or ""
            if not summary.startswith("Accepted and flagged"):
                summary = "Accepted and flagged: " + summary
            self.checkLabel.setText(_escape(summary))
        elif read.state == protocol.ACCEPTED:
            self.checkLabel.setText("Accepted by the automatic check.")
        else:
            self.checkLabel.setText("")

    def _showPlateaus(self):
        for name, label in self.plateauLabels.items():
            value = self.logic.plateaus.get(name)
            label.setText("--" if value is None else "{:.0f} HU".format(value))
        lines = ["{}: level {:.0f} HU".format(b, t)
                 for b, t in halfmax.thresholds(self.logic.plateaus).items()]
        lines += halfmax.warnings(self.logic.plateaus)
        self.halfMaxLabel.setText("\n".join(lines))

    def _updateEnabled(self):
        loggedIn = self.logic is not None and self.logic.loggedIn
        hasCase = loggedIn and self.logic.read is not None
        editable = hasCase and self.logic.read.state in protocol.OPEN_STATES
        self.loginButton.setEnabled(not loggedIn)
        self.logoutButton.setEnabled(loggedIn)
        self.nextButton.setEnabled(loggedIn and not editable)
        self.refreshButton.setEnabled(hasCase)
        self.halfMaxBox.setEnabled(hasCase)
        self.readFormBox.setEnabled(editable)
        self.profileButton.setEnabled(
            hasCase and self.logic.read.state == protocol.RETURNED
            and bool(self.logic.read.check_profile))
        self.saveButton.setEnabled(editable)
        self.submitButton.setEnabled(editable)
        self.releaseButton.setEnabled(editable)

    def _bindEditor(self):
        if self.editorWidget is None:
            return
        if self.editorNode is None or self.editorNode.GetScene() is None:
            self.editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
            self.editorWidget.setMRMLSegmentEditorNode(self.editorNode)
        self.editorWidget.setSegmentationNode(self.logic.segmentationNode)
        try:
            self.editorWidget.setSourceVolumeNode(self.logic.volumeNode)
        except AttributeError:  # pragma: no cover - Slicer < 5.2 naming
            self.editorWidget.setMasterVolumeNode(self.logic.volumeNode)
        # The four classes are a partition: painting one takes the voxels from the rest.
        self.editorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteAllSegments)

    # ------------------------------------------------------------- actions

    def onLogin(self):
        url = self.serverEdit.text.strip()
        try:
            with _busy():
                self.logic.connect(url, self.userEdit.text.strip(), self.passwordEdit.text)
        except Exception as exc:
            self.statusLabel.setText("Not logged in.")
            slicer.util.errorDisplay(_explain(exc))
            return
        finally:
            self.passwordEdit.setText("")
        qt.QSettings().setValue(_SETTING_SERVER, url)
        self.statusLabel.setText("Logged in ({} {}).".format(PROTOCOL_NAME, PROTOCOL_VERSION))
        self._updateEnabled()

    def onLogout(self):
        if not slicer.util.confirmOkCancelDisplay(
                "Log out and delete the locally cached cases? Submitted reads are safe on "
                "the server; an unsubmitted draft is lost."):
            return
        self.logic.disconnect()
        self.logic.purgeCache()
        self.statusLabel.setText("Not logged in.")
        self._showRead()
        self._updateEnabled()

    def onNextCase(self):
        try:
            with _busy():
                held = self.logic.openReads()
                read = held[0] if held else self.logic.takeNext()
                if read is None:
                    slicer.util.infoDisplay("No Janus-M case is waiting for you.")
                    return
                self.logic.openRead(read)
        except Exception as exc:
            slicer.util.errorDisplay(_explain(exc))
            return
        self._bindEditor()
        self._showRead()
        self._showPlateaus()
        self._showReadForm()
        self._updateEnabled()

    def _showReadForm(self):
        for vessel, combo in self.gradeCombos.items():
            combo.blockSignals(True)
            index = combo.findText(self.logic.cadrads.get(vessel, ""))
            combo.setCurrentIndex(max(0, index))
            combo.blockSignals(False)

    def onRefresh(self):
        try:
            read = self.logic.refreshRead()
            if read is not None and read.state == protocol.RETURNED and read.check_profile:
                self.logic.showProfile()
        except Exception as exc:
            slicer.util.errorDisplay(_explain(exc))
        self._showRead()
        self._updateEnabled()

    def onPlaceRoi(self):
        if self.roiNode is None or self.roiNode.GetScene() is None:
            self.roiNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsROINode", "Janus-M plateau ROI")
        self.roiNode.RemoveAllControlPoints()
        slicer.modules.markups.logic().StartPlaceMode(False)
        slicer.modules.markups.logic().SetActiveList(self.roiNode)

    def onMeasureRoi(self):
        if self.roiNode is None or self.roiNode.GetNumberOfControlPoints() == 0:
            slicer.util.errorDisplay("Place the ROI first.")
            return
        try:
            self.logic.measurePlateauInRoi(self.plateauCombo.currentText, self.roiNode)
            self.logic.openDefaultWindow()   # a blank case reaches its border window here
        except Exception as exc:
            slicer.util.errorDisplay(_explain(exc))
        self._showPlateaus()

    def onPlateausFromSegments(self):
        with _busy():
            self.logic.measurePlateausFromSegments()
            self.logic.openDefaultWindow()
        self._showPlateaus()

    def onBorderWindow(self, border):
        try:
            self.logic.applyBorderWindow(border)
        except ValueError as exc:
            slicer.util.errorDisplay(str(exc))

    def onResetWindow(self):
        self.logic.resetWindow()

    def onGrade(self, vessel, text):
        self.logic.setGrade(vessel, text)

    def onMarkLesion(self, vessel):
        if self.logic.read is None:
            return
        self.logic.placeLesionPoint(vessel)

    def onClearLesion(self, vessel):
        self.logic.clearLesionPoint(vessel)

    def onShowProfile(self):
        try:
            self.logic.showProfile()
        except Exception as exc:
            slicer.util.errorDisplay(_explain(exc))

    def onSaveDraft(self):
        if self.logic.saveDraft():
            self.submitLabel.setText("Draft saved on this computer.")

    def onSubmit(self):
        try:
            with _busy():
                self.logic.submit(self.noteEdit.text.strip())
        except ReadRefused as exc:
            slicer.util.errorDisplay("Not submitted:\n\n" + "\n".join(exc.problems))
            return
        except Exception as exc:
            slicer.util.errorDisplay(_explain(exc))
            return
        self.noteEdit.setText("")
        self.submitLabel.setText("Submitted. The automatic check runs on the server; press "
                                 "Refresh status to see its result.")
        if self.logic.read.state == protocol.RETURNED and self.logic.read.check_profile:
            try:
                self.logic.showProfile()
            except Exception as exc:
                slicer.util.errorDisplay(_explain(exc))
        self._showRead()
        self._updateEnabled()

    def onRelease(self):
        if not slicer.util.confirmOkCancelDisplay(
                "Give this case back? It will not be handed back to you."):
            return
        try:
            self.logic.release()
        except Exception as exc:
            slicer.util.errorDisplay(_explain(exc))
        self._showRead()
        self._updateEnabled()

    def onCheckForUpdates(self):
        slicerVersion = updater.packagedSlicerVersion(_MODULE_DIR) or "{}.{}".format(
            slicer.app.majorVersion, slicer.app.minorVersion)
        try:
            with _busy():
                found = updater.checkForUpdate(__version__, slicerVersion)
        except updater.UpdateError as exc:
            slicer.util.errorDisplay(str(exc))
            return
        if found is None:
            slicer.util.infoDisplay("JanusMRead {} is the newest published.".format(__version__))
            return
        ok, reason = updater.canInstall(_MODULE_DIR)
        if not ok:
            slicer.util.infoDisplay("JanusMRead {} is published. {}".format(
                updater.rel.describe(found), reason))
            return
        if not slicer.util.confirmOkCancelDisplay(
                "Install JanusMRead {} and restart Slicer?".format(updater.rel.describe(found))):
            return
        staging = tempfile.mkdtemp(prefix="janusm-read-dl-")
        try:
            with _busy():
                asset = updater.rel.asset_for(found, slicerVersion)
                path = os.path.join(staging, asset["name"])
                updater.downloadAsset(asset, path)
                updater.installArchive(path, _MODULE_DIR, slicerVersion)
        except updater.UpdateError as exc:
            slicer.util.errorDisplay(str(exc))
            return
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        slicer.util.restart()

    def cleanup(self):
        pass


def _explain(exc):
    """What went wrong, for a reader."""
    if isinstance(exc, JanusMError):
        if exc.status == 401:
            return "Wrong username or password."
        if exc.code == protocol.ERR_NOT_A_READER:
            return "This account is not a Janus-M reader. Ask the project lead."
        if exc.code == protocol.ERR_CLIENT_TOO_OLD:
            return "This JanusMRead is out of date: " + str(exc)
        if exc.status == 404 and exc.code is None:
            return "This server has no Janus-M read queue."
    return str(exc) or exc.__class__.__name__


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class _busy:
    def __enter__(self):
        qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
        return self

    def __exit__(self, *exc):
        qt.QApplication.restoreOverrideCursor()
        return False


class JanusMReadTest(ScriptedLoadableModuleWidget):
    """Slicer's self-test hook. The tests are ``tests/test_janusm_read_*.py`` (pytest)
    and ``tests/slicer_selftest_janusm.py`` (inside Slicer)."""

    def runTest(self):
        slicer.util.infoDisplay(
            "JanusMRead's tests are in the repository:\n"
            "    pytest tests/test_janusm_read_module.py\n"
            "    Slicer --python-script tests/slicer_selftest_janusm.py")
