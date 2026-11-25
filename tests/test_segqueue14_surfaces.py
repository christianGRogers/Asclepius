"""``SegQueue14Lib.surfaces`` (0.25.2): a direct voxel write keeps the 3D view.

Slicer 5.8's ``updateSegmentBinaryLabelmapFromArray`` drops the closed surface of
every segment; ``keeping_closed_surface`` rebuilds it when it was there. The
Slicer side is checked by ``tests/slicer_selftest14.py``; this is the logic.
"""

import importlib.util
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
PATH = REPO / "slicer" / "SegQueue14" / "SegQueue14Lib" / "surfaces.py"


def _surfaces():
    spec = importlib.util.spec_from_file_location("segqueue14_surfaces", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Segmentation:
    def __init__(self, segments=2, surfaces=False):
        self.segments, self.surfaces, self.asked = segments, surfaces, []

    def GetNumberOfSegments(self):
        return self.segments

    def ContainsRepresentation(self, name):
        self.asked.append(name)
        return self.surfaces


class _Node:
    def __init__(self, segmentation):
        self.segmentation, self.built = segmentation, 0

    def GetSegmentation(self):
        return self.segmentation

    def CreateClosedSurfaceRepresentation(self):
        self.built += 1
        self.segmentation.surfaces = True

    def write(self):
        """What slicer.util's write does to the surfaces."""
        self.segmentation.surfaces = False


def test_the_representation_name_is_slicers():
    surfaces = _surfaces()
    assert surfaces.CLOSED_SURFACE == "Closed surface"
    segmentation = _Segmentation(surfaces=True)
    assert surfaces.has_closed_surface(_Node(segmentation))
    assert segmentation.asked == ["Closed surface"]


@pytest.mark.parametrize("node", [None, _Node(None), _Node(_Segmentation(segments=0))])
def test_nothing_has_no_surface(node):
    assert _surfaces().has_closed_surface(node) is False


def test_surfaces_shown_before_a_write_are_rebuilt_after_it():
    surfaces = _surfaces()
    node = _Node(_Segmentation(surfaces=True))
    with surfaces.keeping_closed_surface(node) as had:
        node.write()
        assert had and not surfaces.has_closed_surface(node)
    assert node.built == 1 and surfaces.has_closed_surface(node)


def test_no_surfaces_are_built_when_none_were_shown():
    surfaces = _surfaces()
    node = _Node(_Segmentation(surfaces=False))
    with surfaces.keeping_closed_surface(node) as had:
        node.write()
    assert had is False and node.built == 0


def test_a_failed_write_still_leaves_the_3d_view_showing():
    surfaces = _surfaces()
    node = _Node(_Segmentation(surfaces=True))
    with pytest.raises(RuntimeError):
        with surfaces.keeping_closed_surface(node):
            node.write()
            raise RuntimeError("write failed")
    assert node.built == 1 and surfaces.has_closed_surface(node)


def test_no_node_is_a_no_op():
    with _surfaces().keeping_closed_surface(None) as had:
        pass
    assert had is False


def test_it_is_python_3_9_clean_and_free_of_slicer():
    source = PATH.read_text(encoding="utf-8")
    for name in ("import slicer", "import vtk", "import qt", "match ", " | None"):
        assert name not in source
