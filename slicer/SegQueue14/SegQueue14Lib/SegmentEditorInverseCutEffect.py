"""*Inverse cut*, a Segment Editor effect shipped with SegQueue14 (D51).

The annotator draws a free-form outline, as with Scissors. On release the
selected segment keeps only its voxels inside the outline -- Scissors' "Erase
outside", limited to the selected segment -- instead of being cut away piece by
piece to reach one small branch. If the selected segment is empty and the case
has a vessel seed, it becomes the seed's voxels inside the outline instead.

* As with Scissors' default, the outline is extruded through the whole volume
  along the view direction: drawn in a slice view, it keeps a prism through every
  slice; drawn in the 3D view, everything that projects inside it on screen.
* Only the selected segment changes. Every other segment, and the helpers (the
  vessel seed and the heart region), are never modified; a helper cannot be the
  selected segment for this effect.
* One undoable step, in the editor's own undo history.
* Fail-safe (0.25.1): an outline that holds none of the segment's voxels (or the
  seed's) changes nothing and says so in the status bar. A cut never empties the
  segment.
* A slice view's outline is converted the way Slicer's own Scissors converts it
  (``ConvertDeviceToXYZ``), into the XY of the pane it was drawn in. 0.25.0 read
  the raw event position as slice XY, which is only the same thing outside a
  lightbox: in one, the outline landed in another place and the cut wiped the
  segment.
* The cursor is the effect's icon over the slice views and the 3D view, as for
  Scissors.

Loaded by Slicer through ``qSlicerSegmentEditorScriptedEffect.setPythonSource``
(``SegQueue14.registerInverseCutEffect``), which looks for the class named after
this file. The voxel arithmetic is in ``SegQueue14Lib.inversecut``, tested by
pytest without Slicer; what this file adds is the drawing and the Slicer I/O.
"""

import logging
import os

import qt
import slicer
import vtk
from SegmentEditorEffects import AbstractScriptedSegmentEditorEffect

from SegQueue14Lib import inversecut

try:
    from segqueue14 import protocol as _protocol
    SEED_SEGMENT_NAME = _protocol.SEED_SEGMENT_NAME
    REGION_SEGMENT_NAME = _protocol.REGION_SEGMENT_NAME
except ImportError:  # pragma: no cover - the module puts segqueue14 on the path
    SEED_SEGMENT_NAME = "~ vessel seed (not submitted)"
    REGION_SEGMENT_NAME = "~ heart region (not submitted)"

#: The effect's name, shown under its icon and used to find it in the factory.
EFFECT_NAME = "Inverse cut"
#: The one-line help the effect panel shows.
HELP_TEXT = ("Inverse cut: outline a region and the selected segment keeps only what "
             "is inside it; an empty segment takes the vessel seed inside it instead.")
#: The helper segments, never modified by this effect.
HELPER_NAMES = (SEED_SEGMENT_NAME, REGION_SEGMENT_NAME)

_ICON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "Resources", "Icons", "InverseCut.png")
#: The outline while it is drawn: the seed's yellow, so it reads on the CT.
_LINE_COLOR = (0.95, 0.85, 0.20)


class SegmentEditorInverseCutEffect(AbstractScriptedSegmentEditorEffect):
    """Keep only the inside of a drawn outline, in the selected segment (D51)."""

    def __init__(self, scriptedEffect):
        scriptedEffect.name = EFFECT_NAME
        scriptedEffect.perSegment = True
        scriptedEffect.requireSegments = True
        # The editor builds the cursor from icon(); for a scripted effect it shows
        # it over the slice views only unless told otherwise (Scissors shows both).
        scriptedEffect.showEffectCursorInSliceView = True
        scriptedEffect.showEffectCursorInThreeDView = True
        AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)
        #: The outline being drawn, per view: {viewWidget: _Outline}.
        self._outlines = {}

    def clone(self):
        import qSlicerSegmentationsEditorEffectsPythonQt as effects

        cloned = effects.qSlicerSegmentEditorScriptedEffect(None)
        cloned.setPythonSource(os.path.abspath(__file__).replace("\\", "/"))
        return cloned

    def icon(self):
        if os.path.isfile(_ICON):
            return qt.QIcon(_ICON)
        return qt.QIcon()

    def helpText(self):
        return HELP_TEXT

    def setupOptionsFrame(self):
        label = qt.QLabel(
            "Hold the left button and draw around the part to keep. Only the selected "
            "segment changes; Ctrl+Z undoes it.")
        label.setWordWrap(True)
        self.scriptedEffect.addOptionsWidget(label)

    def deactivate(self):
        for viewWidget in list(self._outlines):
            self._dropOutline(viewWidget)

    # ------------------------------------------------------------ drawing

    def processInteractionEvents(self, callerInteractor, eventId, viewWidget):
        if eventId == vtk.vtkCommand.LeftButtonPressEvent:
            if callerInteractor.GetShiftKey() or callerInteractor.GetControlKey():
                return False
            outline = self._outlineFor(viewWidget)
            position = callerInteractor.GetEventPosition()
            outline.start(position, _paneXY(viewWidget, callerInteractor, position))
            self._render(viewWidget)
            return True
        outline = self._outlines.get(viewWidget)
        if outline is None or not outline.drawing:
            return False
        if eventId == vtk.vtkCommand.MouseMoveEvent:
            outline.add(callerInteractor.GetEventPosition())
            self._render(viewWidget)
            return True
        if eventId == vtk.vtkCommand.LeftButtonReleaseEvent:
            outline.add(callerInteractor.GetEventPosition())
            start, paneStart = outline.deviceStart, outline.paneStart
            points = inversecut.outline_in_pane(outline.finish(), start, paneStart)
            self._render(viewWidget)
            try:
                self.apply(viewWidget, points)
            except Exception:
                logging.exception("Inverse cut failed")
                slicer.util.errorDisplay(
                    "Inverse cut failed; the segment is unchanged (Ctrl+Z undoes any "
                    "change).", detailedText=_traceback())
            return True
        return False

    def _outlineFor(self, viewWidget):
        outline = self._outlines.get(viewWidget)
        if outline is None:
            outline = _Outline()
            self.scriptedEffect.addActor2D(viewWidget, outline.actor)
            self._outlines[viewWidget] = outline
        return outline

    def _dropOutline(self, viewWidget):
        outline = self._outlines.pop(viewWidget, None)
        if outline is not None:
            try:
                self.scriptedEffect.removeActor2D(viewWidget, outline.actor)
            except Exception:  # pragma: no cover - the view went away
                pass
            self._render(viewWidget)

    def _render(self, viewWidget):
        try:
            self.scriptedEffect.scheduleRender(viewWidget)
        except Exception:  # pragma: no cover - older Slicer
            pass

    # ------------------------------------------------------------ the cut

    def apply(self, viewWidget, polygon):
        """Cut the selected segment to the outline ``polygon``: in a slice view the
        pane's XY (``inversecut.outline_in_pane``), in the 3D view display points."""
        if len(inversecut.simplify_polygon(polygon)) < 3:
            return False
        parameters = self.scriptedEffect.parameterSetNode()
        segmentationNode = parameters.GetSegmentationNode()
        segmentId = parameters.GetSelectedSegmentID()
        volumeNode = _sourceVolume(parameters)
        if segmentationNode is None or not segmentId:
            _status("Inverse cut: select a segment first.")
            return False
        if volumeNode is None:
            _status("Inverse cut: there is no CT to cut against.")
            return False
        segmentation = segmentationNode.GetSegmentation()
        if segmentation.GetSegment(segmentId).GetName() in HELPER_NAMES:
            _status("Inverse cut never changes the vessel seed or the heart region; "
                    "select a class.")
            return False

        segment = slicer.util.arrayFromSegmentBinaryLabelmap(
            segmentationNode, segmentId, volumeNode)
        seed = None
        if segment is None or not segment.any():
            seedId = _segmentIdNamed(segmentation, SEED_SEGMENT_NAME)
            if seedId:
                seed = slicer.util.arrayFromSegmentBinaryLabelmap(
                    segmentationNode, seedId, volumeNode)
        shape = slicer.util.arrayFromVolume(volumeNode).shape
        segment = _onGrid(segment, shape)
        seed = _onGrid(seed, shape) if seed is not None else None

        toDisplay = _ijkToDisplay(viewWidget, volumeNode)
        if toDisplay is None:
            _status("Inverse cut works in the slice views and the 3D view.")
            return False
        source = segment if segment.any() else seed
        if source is None or not source.any():
            _status("Inverse cut: the segment is empty and there is no seed to take "
                    "from.")
            return False
        inside = inversecut.inside_region(source, toDisplay, polygon)
        result, used = inversecut.inverse_cut(segment, inside, seed)
        if used == "outside":
            # Fail-safe: never empty the segment (0.25.1).
            _status("Inverse cut: the outline holds none of the {}; nothing was "
                    "changed.".format("seed" if source is seed else "selected segment"))
            return False
        if result is None:
            return False

        self.scriptedEffect.saveStateForUndo()
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            result, segmentationNode, segmentId, volumeNode)
        display = segmentationNode.GetDisplayNode()
        if display is not None:
            # A seeded class starts hidden (D26, D51); show the one just cut.
            display.SetSegmentVisibility(segmentId, True)
        _status("Inverse cut: kept {} voxels{}.".format(
            int(result.sum()), " of the seed" if used == "seed" else ""))
        return True


class _Outline:
    """The polyline drawn while the button is held, in display coordinates."""

    def __init__(self):
        self.points = []
        self.drawing = False
        #: The first point as an event position, and in its pane's XY.
        self.deviceStart = self.paneStart = (0, 0)
        self.polyData = vtk.vtkPolyData()
        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(self.polyData)
        self.actor = vtk.vtkActor2D()
        self.actor.SetMapper(mapper)
        prop = self.actor.GetProperty()
        prop.SetColor(*_LINE_COLOR)
        prop.SetLineWidth(2)
        self.actor.VisibilityOff()

    def start(self, xy, paneXY=None):
        self.points = [tuple(xy)]
        self.deviceStart = tuple(xy)[:2]
        self.paneStart = tuple(paneXY)[:2] if paneXY is not None else self.deviceStart
        self.drawing = True
        self.actor.VisibilityOn()
        self._update()

    def add(self, xy):
        xy = tuple(xy)
        if not self.points or self.points[-1] != xy:
            self.points.append(xy)
            self._update()

    def finish(self):
        points, self.points, self.drawing = self.points, [], False
        self.actor.VisibilityOff()
        self._update()
        return points

    def _update(self):
        vtkPoints = vtk.vtkPoints()
        line = vtk.vtkPolyLine()
        for x, y in self.points:
            line.GetPointIds().InsertNextId(vtkPoints.InsertNextPoint(x, y, 0))
        if len(self.points) > 2:
            line.GetPointIds().InsertNextId(0)  # closed, as the cut will be
        cells = vtk.vtkCellArray()
        if self.points:
            cells.InsertNextCell(line)
        self.polyData.SetPoints(vtkPoints)
        self.polyData.SetLines(cells)
        self.polyData.Modified()


def _paneXY(viewWidget, interactor, position):
    """``position`` (an event position) in the XY that the slice node's XYToRAS
    takes: relative to the lightbox pane under it, as Slicer's own effects convert
    it. Anything but a slice view keeps its display position."""
    if viewWidget.className() != "qMRMLSliceWidget":
        return tuple(position)[:2]
    xyz = [0.0, 0.0, 0.0]
    slicer.vtkMRMLAbstractSliceViewDisplayableManager.ConvertDeviceToXYZ(
        interactor, viewWidget.mrmlSliceNode(), position[0], position[1], xyz)
    return xyz[0], xyz[1]


def _sourceVolume(parameters):
    try:
        return parameters.GetSourceVolumeNode()
    except AttributeError:  # pragma: no cover - Slicer < 5.2 naming
        return parameters.GetMasterVolumeNode()


def _segmentIdNamed(segmentation, name):
    for i in range(segmentation.GetNumberOfSegments()):
        segmentId = segmentation.GetNthSegmentID(i)
        if segmentation.GetSegment(segmentId).GetName() == name:
            return segmentId
    return None


def _onGrid(mask, shape):
    """A segment array as 0/1 on the CT grid; zeros if it came back empty."""
    import numpy as np

    if mask is None or tuple(mask.shape) != tuple(shape):
        if mask is not None and mask.size and mask.any():
            raise RuntimeError("Slicer returned a {} array on the CT's {} grid".format(
                tuple(mask.shape), tuple(shape)))
        return np.zeros(shape, np.uint8)
    return (mask != 0).astype(np.uint8)


def _matrix(vtkMatrix):
    import numpy as np

    return np.array([[vtkMatrix.GetElement(r, c) for c in range(4)] for r in range(4)])


def _ijkToDisplay(viewWidget, volumeNode):
    """4x4 from the CT's voxel index to this view's outline coordinates (a slice
    view's pane XY, the 3D view's display positions), or None for a view this
    effect does not know."""
    import numpy as np

    ijkToRas = vtk.vtkMatrix4x4()
    volumeNode.GetIJKToRASMatrix(ijkToRas)
    worldFromIjk = _matrix(ijkToRas)
    parent = volumeNode.GetParentTransformNode()
    if parent is not None:
        toWorld = vtk.vtkMatrix4x4()
        if slicer.vtkMRMLTransformNode.GetMatrixTransformBetweenNodes(parent, None, toWorld):
            worldFromIjk = _matrix(toWorld) @ worldFromIjk

    kind = viewWidget.className()
    if kind == "qMRMLSliceWidget":
        # Slice XY is the outline's pane XY (_paneXY); dropping the third coordinate
        # extrudes it through every slice, as Scissors' default does.
        xyToRas = _matrix(viewWidget.mrmlSliceNode().GetXYToRAS())
        return np.linalg.inv(xyToRas) @ worldFromIjk
    if kind == "qMRMLThreeDWidget":
        renderer = viewWidget.threeDView().renderWindow().GetRenderers().GetFirstRenderer()
        camera = renderer.GetActiveCamera()
        projection = _matrix(camera.GetCompositeProjectionTransformMatrix(
            renderer.GetTiledAspectRatio(), -1, 1))
        width, height = renderer.GetSize()
        x0, y0 = renderer.GetOrigin()
        viewport = np.array([[width / 2.0, 0, 0, x0 + width / 2.0],
                             [0, height / 2.0, 0, y0 + height / 2.0],
                             [0, 0, 1, 0],
                             [0, 0, 0, 1]])
        return viewport @ projection @ worldFromIjk
    return None


def _status(text):
    try:
        slicer.util.showStatusMessage(text, 4000)
    except Exception:  # pragma: no cover - no main window
        logging.info(text)


def _traceback():
    import traceback

    return traceback.format_exc()
