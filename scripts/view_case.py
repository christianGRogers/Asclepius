"""Load one case's CT, ground truth and (optionally) a prediction into Slicer.

Complements the monitor module, which follows a *run*. This looks at a single
case directly -- most useful for eyeballing the conversion itself, i.e. that the
117 binary masks merged into a sane multilabel volume, independently of whether
any model has been trained yet.

    "…/Slicer.exe" --no-splash --python-script scripts/view_case.py -- \
        --case s0325 [--pred path/to/prediction.nii.gz] [--screenshot out.png]

Structure colours are derived from the structure name, matching the monitor, so
the same anatomy is the same colour everywhere.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "slicer", "SegmentatorTrainMonitor"))

import slicer  # noqa: E402

from segtrain.config import load_config, load_task  # noqa: E402


def _arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def _color_for_name(name):
    from SegmentatorTrainMonitor import _colorForName

    return _colorForName(name)


def _load_segmentation(path, names, node_name, opacity):
    labelNode = slicer.util.loadLabelVolume(path)
    segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", node_name)
    segNode.CreateDefaultDisplayNodes()
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelNode, segNode)
    slicer.mrmlScene.RemoveNode(labelNode)

    segmentation = segNode.GetSegmentation()
    for i in range(segmentation.GetNumberOfSegments()):
        segment = segmentation.GetNthSegment(i)
        digits = "".join(ch for ch in (segment.GetName() or "") if ch.isdigit())
        index = int(digits) if digits else i + 1
        if 1 <= index <= len(names):
            segment.SetName(names[index - 1])
            segment.SetColor(*_color_for_name(names[index - 1]))
    segNode.CreateClosedSurfaceRepresentation()
    segNode.GetDisplayNode().SetOpacity(opacity)
    return segNode


def main():
    case = _arg("--case")
    pred = _arg("--pred")
    shot = _arg("--screenshot")
    task_ref = _arg("--task", "701")
    if not case:
        print("usage: --case sXXXX [--pred file.nii.gz] [--screenshot out.png]")
        slicer.util.exit(2)

    cfg = load_config()
    task = load_task(task_ref)
    names = task.label_set.names
    raw = task.raw_dir(cfg)

    ct = raw / "imagesTr" / (case + "_0000.nii.gz")
    gt = raw / "labelsTr" / (case + ".nii.gz")
    if not ct.is_file():
        ct = raw / "imagesTs" / (case + "_0000.nii.gz")
        gt = raw / "labelsTs" / (case + ".nii.gz")
    if not ct.is_file():
        print("no converted case {} under {}".format(case, raw))
        slicer.util.exit(1)

    print("CT:           {}".format(ct))
    volume = slicer.util.loadVolume(str(ct))

    if gt.is_file():
        print("ground truth: {}".format(gt))
        _load_segmentation(str(gt), names, "GroundTruth", 0.6)

    if pred and os.path.isfile(pred):
        print("prediction:   {}".format(pred))
        _load_segmentation(pred, names, "Prediction", 0.6)

    slicer.util.setSliceViewerLayers(background=volume, fit=True)
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    for view in ("Red", "Yellow", "Green"):
        layoutManager.sliceWidget(view).sliceController().setSliceVisible(True)

    threeD = layoutManager.threeDWidget(0).threeDView()
    threeD.resetFocalPoint()
    threeD.forceRender()

    if shot:
        slicer.app.processEvents()
        slicer.util.saveScreenshot = getattr(slicer.util, "saveScreenshot", None)
        image = slicer.util.mainWindow().grab()
        image.save(shot)
        print("screenshot:   {}".format(shot))
        slicer.util.exit(0)

    print("\nLoaded. Ground truth and prediction are separate segmentation nodes -- "
          "toggle them in the Data module to compare.")


main()
