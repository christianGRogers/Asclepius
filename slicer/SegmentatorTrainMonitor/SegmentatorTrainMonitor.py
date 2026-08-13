"""SegmentatorTrainMonitor -- watch a segmentation model train, from inside Slicer.

Loss curves tell you a run is converging. They do not tell you the model has
swapped T11 for T12, or that it segments a beautiful liver and has never once
found the gallbladder. This module exists to make the second kind of problem
visible while there is still time to do something about it.

It does not train anything. Training runs as a separate process -- here, on a
remote GPU box, or in a cluster queue -- and appends to ``events.jsonl`` in a run
directory. This module polls that file. Consequences worth knowing:

* Slicer can be closed and reopened mid-run, or attached hours late, and simply
  catches up from the file.
* Nothing here can crash or slow the training process.
* A remote run works identically; only small files cross the network, because
  inference happens beside the GPU and sends back a ~0.3 MB label volume.

Runs against Slicer's bundled Python 3.9 with no pip installs: it imports
``segtrain.events`` from the sibling ``src/`` directory, which is stdlib-only by
design, and shells out to the system ``ssh``/``scp`` for remote runs.
"""

import os
import sys

import ctk
import qt
import slicer
import vtk
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleWidget,
)

# Make the pipeline's own event-stream code importable without installing
# anything into Slicer's Python. segtrain.events is deliberately stdlib-only so
# this works; see its module docstring.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC = os.path.join(_REPO_ROOT, "src")
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)

try:
    from segtrain.events import EventReader, RunState
    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - surfaced in the UI instead
    EventReader = None
    RunState = None
    _IMPORT_ERROR = str(exc)

from SegmentatorTrainMonitorLib import find_modal_cli, make_source

DEFAULT_POLL_SECONDS = 10


class SegmentatorTrainMonitor(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Segmentator Train Monitor"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Christian Rogers"]
        self.parent.helpText = __doc__
        self.parent.acknowledgementText = (
            "Trains nnU-Net models on the TotalSegmentator CT dataset."
        )


class SegmentatorTrainMonitorLogic(ScriptedLoadableModuleLogic):
    """Event-stream state plus the MRML nodes that display it.

    Deliberately holds no Qt: everything here is testable outside the UI, which
    is how the module gets developed on a machine with no GPU and no live run.
    """

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.source = None
        self.reader = None
        self.state = None
        self.lastError = None

        self._tableNode = None
        self._chartNode = None
        self._seriesNodes = {}
        self._segmentationNode = None
        self._volumeNode = None
        self._loadedPreviewKey = None
        self._loadedVolumeCase = None

    # -- connection ---------------------------------------------------------

    def connect(self, location, modal_cli=None):
        """Point at a run directory. Returns True if its event stream is readable."""
        self.source = make_source(location, modal_cli=modal_cli)
        self.state = RunState()
        self.reader = None
        self.lastError = None

        path = self.source.events_path()
        if not path:
            self.lastError = getattr(self.source, "last_error", None) or (
                "no events.jsonl under {}".format(location)
            )
            return False

        self.reader = EventReader(os.path.dirname(path))
        self.poll()
        return True

    def poll(self):
        """Fold any new events into the run state. Returns the new events."""
        if self.reader is None or self.source is None:
            return []
        # For a remote run this re-copies events.jsonl and hands back the local
        # cache path, which is what the reader has been following all along.
        path = self.source.events_path()
        if not path:
            self.lastError = getattr(self.source, "last_error", None)
            return []
        events = self.reader.read_new()
        if events:
            self.state.update(events)
        return events

    # -- summary ------------------------------------------------------------

    def summary(self):
        if not self.state:
            return "not connected"
        meta = self.state.meta
        parts = []
        if meta.get("task"):
            parts.append("{} fold {}".format(meta["task"], meta.get("fold", "?")))
        total = self.state.total_epochs
        current = self.state.current_epoch
        if current is not None:
            parts.append("epoch {}{}".format(current, "/{}".format(total) if total else ""))
        eta = self.state.eta_seconds()
        if eta and not self.state.finished:
            parts.append("eta {:.1f} h".format(eta / 3600.0))
        _, dice = self.state.mean_pseudo_dice()
        if dice:
            parts.append("pseudo Dice {:.3f}".format(dice[-1]))
        parts.append(self.state.status or "waiting")
        return "  |  ".join(parts)

    # -- plots --------------------------------------------------------------

    def _ensurePlotNodes(self):
        """Create the table and chart backing the loss/Dice plot, once."""
        if self._tableNode is None:
            self._tableNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLTableNode", "SegtrainProgress")
            table = self._tableNode.GetTable()
            for name in ("epoch", "train_loss", "val_loss", "pseudo_dice"):
                arr = vtk.vtkFloatArray()
                arr.SetName(name)
                table.AddColumn(arr)

        if self._chartNode is None:
            self._chartNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLPlotChartNode", "SegtrainChart")
            self._chartNode.SetTitle("Training progress")
            self._chartNode.SetXAxisTitle("epoch")
            self._chartNode.SetYAxisTitle("loss  /  pseudo Dice")

            # nnU-Net's loss is negative (Dice + cross-entropy with the Dice term
            # negated), so loss and Dice share a y-axis range well enough to read
            # on one chart -- which is what you want, since the question is
            # whether Dice is still climbing after loss has flattened.
            for column, colour in (("train_loss", (0.85, 0.33, 0.10)),
                                   ("val_loss", (0.00, 0.45, 0.74)),
                                   ("pseudo_dice", (0.20, 0.65, 0.20))):
                series = slicer.mrmlScene.AddNewNodeByClass(
                    "vtkMRMLPlotSeriesNode", column)
                series.SetAndObserveTableNodeID(self._tableNode.GetID())
                series.SetXColumnName("epoch")
                series.SetYColumnName(column)
                series.SetPlotType(slicer.vtkMRMLPlotSeriesNode.PlotTypeScatter)
                series.SetMarkerStyle(slicer.vtkMRMLPlotSeriesNode.MarkerStyleNone)
                series.SetColor(*colour)
                series.SetLineWidth(2)
                self._seriesNodes[column] = series
                self._chartNode.AddAndObservePlotSeriesNodeID(series.GetID())

    def updatePlots(self):
        if not self.state or not self.state.epochs:
            return
        self._ensurePlotNodes()

        dice_by_epoch = dict(zip(*self.state.mean_pseudo_dice()))
        table = self._tableNode.GetTable()
        self._tableNode.StartModify()
        table.SetNumberOfRows(len(self.state.epochs))
        for row, event in enumerate(self.state.epochs):
            epoch = event.get("epoch", row)
            table.SetValue(row, 0, epoch)
            # vtkFloatArray has no null. Repeating the previous value would draw
            # a flat segment that looks like a stalled metric, so a gap is
            # rendered as NaN, which VTK skips.
            for col, key in ((1, "train_loss"), (2, "val_loss")):
                value = event.get(key)
                table.SetValue(row, col, float("nan") if value is None else float(value))
            table.SetValue(row, 3, dice_by_epoch.get(epoch, float("nan")))
        self._tableNode.EndModify(True)
        self._tableNode.Modified()

    def showPlots(self):
        """Put the chart in a visible layout."""
        self._ensurePlotNodes()
        layoutManager = slicer.app.layoutManager()
        if layoutManager is None:
            return
        layoutManager.setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpTableView
            if False
            else slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalPlotView
        )
        plotWidget = layoutManager.plotWidget(0)
        if plotWidget and plotWidget.mrmlPlotViewNode():
            plotWidget.mrmlPlotViewNode().SetPlotChartNodeID(self._chartNode.GetID())

    # -- per-class scores ---------------------------------------------------

    def latestClassScores(self, case=None):
        """[(structure, dice)] from the newest preview, weakest first.

        Preview Dice is real Dice on a held-out case, unlike nnU-Net's pseudo
        Dice, which is computed on training patches and reads far too high early
        on. Falls back to pseudo Dice only when no preview has arrived yet.
        """
        if not self.state:
            return []

        previews = self.state.previews_for(case) if case else self.state.previews
        if previews:
            dice = previews[-1].get("dice") or {}
            return sorted(dice.items(), key=lambda kv: kv[1])

        if self.state.epochs:
            values = self.state.epochs[-1].get("pseudo_dice") or []
            names = self.state.meta.get("class_names") or []
            if names and len(names) == len(values):
                pairs = [(n, v) for n, v in zip(names, values) if v is not None]
                return sorted(pairs, key=lambda kv: kv[1])
        return []

    # -- preview loading ----------------------------------------------------

    def loadPreview(self, preview, withReference=True):
        """Load one preview segmentation into the scene, replacing the last.

        Nodes are reused across epochs rather than reloaded, so the 3D view keeps
        its camera and the segment colours stay put -- otherwise every refresh
        would reset the view and you could not compare one epoch to the next.
        """
        if not preview or not self.source:
            return False

        key = (preview.get("case"), preview.get("epoch"))
        if key == self._loadedPreviewKey:
            return True

        segPath = self.source.fetch(preview.get("seg", ""))
        if not segPath:
            self.lastError = "could not fetch preview {}".format(preview.get("seg"))
            return False

        case = preview.get("case")
        if withReference and case != self._loadedVolumeCase:
            self._loadReference(preview)

        labelNode = None
        try:
            labelNode = slicer.util.loadLabelVolume(segPath)
            if self._segmentationNode is None:
                self._segmentationNode = slicer.mrmlScene.AddNewNodeByClass(
                    "vtkMRMLSegmentationNode", "Preview")
                self._segmentationNode.CreateDefaultDisplayNodes()
            else:
                self._segmentationNode.GetSegmentation().RemoveAllSegments()

            slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
                labelNode, self._segmentationNode)
            self._nameAndColorSegments()
            if self._volumeNode is not None:
                self._segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(
                    self._volumeNode)
            self._segmentationNode.CreateClosedSurfaceRepresentation()
        finally:
            # The labelmap was only a carrier; leaving it in the scene would
            # clutter the volume selectors with one node per refresh.
            if labelNode is not None:
                slicer.mrmlScene.RemoveNode(labelNode)

        self._loadedPreviewKey = key
        return True

    def _loadReference(self, preview):
        path = preview.get("reference_image")
        # The reference CT lives on the training machine and is ~11 MB. Pull it
        # only for local runs; over SSH the segmentation alone is the point.
        if path and getattr(self.source, "kind", "local") == "local" and os.path.isfile(path):
            if self._volumeNode is not None:
                slicer.mrmlScene.RemoveNode(self._volumeNode)
            self._volumeNode = slicer.util.loadVolume(path)
            self._loadedVolumeCase = preview.get("case")
            slicer.util.setSliceViewerLayers(background=self._volumeNode, fit=True)

    def _nameAndColorSegments(self):
        """Give segments their anatomical names and a stable colour.

        Imported labelmap segments arrive as "Label_1", "Label_2", ... The event
        stream carries the structure names in label order, so they can be
        recovered here. Colours are derived from the name, not the index, so a
        structure keeps the same colour across epochs, across cases, and across
        the group models -- which is what makes visual comparison possible.
        """
        names = (self.state.meta.get("class_names") or []) if self.state else []
        segmentation = self._segmentationNode.GetSegmentation()
        for i in range(segmentation.GetNumberOfSegments()):
            segment = segmentation.GetNthSegment(i)
            label = _labelIndexFromSegment(segmentation.GetNthSegmentID(i), segment, i)
            if 1 <= label <= len(names):
                name = names[label - 1]
                segment.SetName(name)
                segment.SetColor(*_colorForName(name))


def _labelIndexFromSegment(segmentId, segment, fallbackIndex):
    """Recover the original label value from an imported segment.

    Slicer names imported segments after their labelmap value, but the exact
    format has varied between versions, so the digits are parsed out of either
    the id or the name and the ordinal position is used as a last resort.
    """
    for text in (segment.GetName() or "", segmentId or ""):
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            try:
                return int(digits)
            except ValueError:
                pass
    return fallbackIndex + 1


def _colorForName(name):
    """Deterministic, reasonably distinct colour for a structure name.

    A hash gives stability across sessions; forcing saturation and value high
    keeps every structure visible against the CT rather than letting some land
    on near-black or near-grey.
    """
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    hue = (h % 360) / 360.0
    sat = 0.55 + ((h >> 9) % 40) / 100.0
    val = 0.70 + ((h >> 17) % 30) / 100.0
    return _hsvToRgb(hue, sat, min(val, 1.0))


def _hsvToRgb(h, s, v):
    i = int(h * 6.0)
    f = h * 6.0 - i
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]


class SegmentatorTrainMonitorWidget(ScriptedLoadableModuleWidget):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        self.logic = None
        self.timer = None
        self._previewIndex = -1

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        if _IMPORT_ERROR:
            label = qt.QLabel(
                "Could not import segtrain.events:\n{}\n\n"
                "Expected it at {}.\nCheck out the full segmentator-train repo and load "
                "this module from within it.".format(_IMPORT_ERROR, _SRC))
            label.setWordWrap(True)
            self.layout.addWidget(label)
            return

        self.logic = SegmentatorTrainMonitorLogic()

        # -- connection
        connBox = ctk.ctkCollapsibleButton()
        connBox.text = "Run"
        self.layout.addWidget(connBox)
        connLayout = qt.QFormLayout(connBox)

        self.runDirEdit = qt.QLineEdit()
        self.runDirEdit.setPlaceholderText(
            r"C:\segtrain\runs\Dataset701_Total3mm__fold0   or   user@gpu-box:/data/runs/...")
        self.runDirEdit.setToolTip(
            "A local path, a mounted share, or user@host:/path for a run on the "
            "training machine (uses your system ssh/scp, honouring ~/.ssh/config).")
        browse = qt.QPushButton("Browse...")
        browse.clicked.connect(self.onBrowse)
        row = qt.QHBoxLayout()
        row.addWidget(self.runDirEdit)
        row.addWidget(browse)
        connLayout.addRow("Run directory:", row)

        # Slicer's PATH is not the shell's, so the CLI is auto-detected in the
        # project venv first. This field is only for overriding that.
        self.modalCliEdit = qt.QLineEdit()
        detected = find_modal_cli()
        if detected:
            self.modalCliEdit.text = detected
        self.modalCliEdit.setPlaceholderText("auto-detected   (modal:// runs only)")
        self.modalCliEdit.setToolTip(
            "Path to the modal CLI, used to read runs from a Modal volume. "
            "Ignored for local run directories.")
        cliBrowse = qt.QPushButton("Browse...")
        cliBrowse.clicked.connect(self.onBrowseModalCli)
        cliRow = qt.QHBoxLayout()
        cliRow.addWidget(self.modalCliEdit)
        cliRow.addWidget(cliBrowse)
        connLayout.addRow("modal CLI:", cliRow)

        self.connectButton = qt.QPushButton("Connect")
        self.connectButton.clicked.connect(self.onConnect)
        connLayout.addRow(self.connectButton)

        self.autoRefresh = qt.QCheckBox("Refresh automatically")
        self.autoRefresh.checked = True
        self.pollSpin = qt.QSpinBox()
        self.pollSpin.setRange(2, 600)
        self.pollSpin.value = DEFAULT_POLL_SECONDS
        self.pollSpin.suffix = " s"
        pollRow = qt.QHBoxLayout()
        pollRow.addWidget(self.autoRefresh)
        pollRow.addWidget(self.pollSpin)
        pollRow.addStretch(1)
        connLayout.addRow("Polling:", pollRow)

        self.statusLabel = qt.QLabel("not connected")
        self.statusLabel.setWordWrap(True)
        connLayout.addRow("Status:", self.statusLabel)

        self.progressBar = qt.QProgressBar()
        self.progressBar.setTextVisible(True)
        connLayout.addRow("Progress:", self.progressBar)

        # -- quality
        qualityBox = ctk.ctkCollapsibleButton()
        qualityBox.text = "Segmentation quality"
        self.layout.addWidget(qualityBox)
        qualityLayout = qt.QVBoxLayout(qualityBox)

        selectorRow = qt.QHBoxLayout()
        self.caseCombo = qt.QComboBox()
        self.caseCombo.setToolTip("Held-out case to display")
        self.caseCombo.currentIndexChanged.connect(self.onCaseChanged)
        selectorRow.addWidget(qt.QLabel("Case:"))
        selectorRow.addWidget(self.caseCombo, 1)
        qualityLayout.addLayout(selectorRow)

        # Stepping back through epochs is the point of keeping every preview:
        # watching a structure sharpen (or a vertebra label slide by one) over
        # training is far more informative than any single snapshot.
        epochRow = qt.QHBoxLayout()
        self.epochSlider = qt.QSlider(qt.Qt.Horizontal)
        self.epochSlider.setToolTip("Step through the previews captured so far")
        self.epochSlider.valueChanged.connect(self.onEpochSliderMoved)
        self.epochLabel = qt.QLabel("-")
        self.followLatest = qt.QCheckBox("Follow latest")
        self.followLatest.checked = True
        epochRow.addWidget(qt.QLabel("Epoch:"))
        epochRow.addWidget(self.epochSlider, 1)
        epochRow.addWidget(self.epochLabel)
        epochRow.addWidget(self.followLatest)
        qualityLayout.addLayout(epochRow)

        self.loadButton = qt.QPushButton("Load preview into 3D view")
        self.loadButton.clicked.connect(self.onLoadPreview)
        qualityLayout.addWidget(self.loadButton)

        self.scoreTable = qt.QTableWidget()
        self.scoreTable.setColumnCount(2)
        self.scoreTable.setHorizontalHeaderLabels(["structure", "Dice"])
        self.scoreTable.horizontalHeader().setStretchLastSection(True)
        self.scoreTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.scoreTable.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.scoreTable.setMinimumHeight(240)
        self.scoreTable.setSortingEnabled(True)
        qualityLayout.addWidget(qt.QLabel("Weakest structures first:"))
        qualityLayout.addWidget(self.scoreTable)

        self.showPlotButton = qt.QPushButton("Show training curves")
        self.showPlotButton.clicked.connect(self.onShowPlots)
        qualityLayout.addWidget(self.showPlotButton)

        self.layout.addStretch(1)

        self.timer = qt.QTimer()
        self.timer.setInterval(DEFAULT_POLL_SECONDS * 1000)
        self.timer.timeout.connect(self.onPoll)

    # -- callbacks ----------------------------------------------------------

    def onBrowse(self):
        path = qt.QFileDialog.getExistingDirectory(None, "Select a run directory")
        if path:
            self.runDirEdit.text = path

    def onBrowseModalCli(self):
        path = qt.QFileDialog.getOpenFileName(None, "Select the modal CLI")
        if path:
            self.modalCliEdit.text = path

    def onConnect(self):
        location = self.runDirEdit.text.strip()
        if not location:
            return
        cli = self.modalCliEdit.text.strip() or None
        if self.logic.connect(location, modal_cli=cli):
            self.statusLabel.text = "connected"
            self.timer.start(self.pollSpin.value * 1000)
            self.refreshUi()
        else:
            self.statusLabel.text = "could not connect: {}".format(self.logic.lastError)
            self.timer.stop()

    def onPoll(self):
        if not self.autoRefresh.checked or self.logic.reader is None:
            return
        self.timer.setInterval(self.pollSpin.value * 1000)
        if self.logic.poll():
            self.refreshUi()

    def refreshUi(self):
        state = self.logic.state
        self.statusLabel.text = self.logic.summary()
        self.logic.updatePlots()

        total, current = state.total_epochs, state.current_epoch
        if total and current is not None:
            self.progressBar.setRange(0, int(total))
            self.progressBar.setValue(int(current) + 1)
            self.progressBar.setFormat("%v / %m epochs")
        elif current is not None:
            self.progressBar.setRange(0, 0)

        self._refreshCases()
        self._refreshEpochSlider()
        self._refreshScores()

        if self.followLatest.checked and state.previews:
            self.onLoadPreview()

    def _refreshCases(self):
        cases = self.logic.state.preview_cases()
        existing = [self.caseCombo.itemText(i) for i in range(self.caseCombo.count)]
        if cases == existing:
            return
        blocked = self.caseCombo.blockSignals(True)
        self.caseCombo.clear()
        for case in cases:
            self.caseCombo.addItem(case)
        self.caseCombo.blockSignals(blocked)

    def _currentCase(self):
        return self.caseCombo.currentText or None

    def _previewsForCurrentCase(self):
        case = self._currentCase()
        if not case:
            return []
        return self.logic.state.previews_for(case)

    def _refreshEpochSlider(self):
        previews = self._previewsForCurrentCase()
        blocked = self.epochSlider.blockSignals(True)
        if previews:
            self.epochSlider.setRange(0, len(previews) - 1)
            if self.followLatest.checked:
                self.epochSlider.setValue(len(previews) - 1)
            self.epochLabel.text = str(previews[self.epochSlider.value].get("epoch", "-"))
        else:
            self.epochSlider.setRange(0, 0)
            self.epochLabel.text = "-"
        self.epochSlider.blockSignals(blocked)

    def onCaseChanged(self, _index):
        self._refreshEpochSlider()
        self._refreshScores()
        if self.followLatest.checked:
            self.onLoadPreview()

    def onEpochSliderMoved(self, index):
        previews = self._previewsForCurrentCase()
        if 0 <= index < len(previews):
            self.epochLabel.text = str(previews[index].get("epoch", "-"))
            # Moving the slider by hand is an explicit request to look at that
            # epoch, so stop yanking the view forward on the next poll.
            self.followLatest.checked = False
            self.onLoadPreview()

    def _selectedPreview(self):
        previews = self._previewsForCurrentCase() or self.logic.state.previews
        if not previews:
            return None
        index = self.epochSlider.value
        return previews[index] if 0 <= index < len(previews) else previews[-1]

    def onLoadPreview(self):
        preview = self._selectedPreview()
        if not preview:
            return
        if not self.logic.loadPreview(preview):
            self.statusLabel.text = self.logic.lastError or "preview failed to load"

    def _refreshScores(self):
        preview = self._selectedPreview()
        scores = []
        if preview and preview.get("dice"):
            scores = sorted(preview["dice"].items(), key=lambda kv: kv[1])
        else:
            scores = self.logic.latestClassScores(self._currentCase())

        self.scoreTable.setSortingEnabled(False)
        self.scoreTable.setRowCount(len(scores))
        for row, (name, value) in enumerate(scores):
            nameItem = qt.QTableWidgetItem(str(name))
            valueItem = qt.QTableWidgetItem("{:.4f}".format(value))
            # Colour is the fastest way to spot a structure that never learned,
            # which is what you are scanning this table for.
            if value < 0.3:
                valueItem.setBackground(qt.QBrush(qt.QColor(220, 120, 120)))
            elif value < 0.7:
                valueItem.setBackground(qt.QBrush(qt.QColor(230, 200, 120)))
            else:
                valueItem.setBackground(qt.QBrush(qt.QColor(150, 210, 150)))
            self.scoreTable.setItem(row, 0, nameItem)
            self.scoreTable.setItem(row, 1, valueItem)
        self.scoreTable.setSortingEnabled(True)

    def onShowPlots(self):
        self.logic.updatePlots()
        self.logic.showPlots()

    def cleanup(self):
        if self.timer:
            self.timer.stop()
