"""D53: ``SegQueue14Lib/extendedview.py``, the toggle's hide and show, on stand-ins."""

import importlib.util
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "slicer" / "SegQueue14" / "SegQueue14Lib"


def _module():
    spec = importlib.util.spec_from_file_location("extendedview_test", LIB / "extendedview.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Display:
    def __init__(self, visible):
        self.visible = dict(visible)

    def GetSegmentVisibility(self, segment_id):
        return self.visible[segment_id]

    def SetSegmentVisibility(self, segment_id, visible):
        self.visible[segment_id] = bool(visible)


def test_hide_then_show_gives_every_eye_back():
    view = _module().ExtendedView()
    display = _Display({"D1": True, "D2": False, "OM2": True, "LAD": True})
    assert not view.hidden
    assert view.hide(display, ["D1", "D2", "OM2"]) == 3
    assert view.hidden
    assert display.visible == {"D1": False, "D2": False, "OM2": False, "LAD": True}
    assert view.show(display, ["D1", "D2", "OM2"]) == 3
    assert display.visible == {"D1": True, "D2": False, "OM2": True, "LAD": True}
    assert not view.hidden


def test_hiding_twice_keeps_the_first_record():
    view = _module().ExtendedView()
    display = _Display({"D1": True, "D2": True})
    view.hide(display, ["D1"])
    view.hide(display, ["D1", "D2"])          # D2 recorded on the second hide
    view.show(display, ["D1", "D2"])
    assert display.visible == {"D1": True, "D2": True}


def test_many_toggles_change_nothing():
    view = _module().ExtendedView()
    start = {"D1": True, "D2": False, "S1": True}
    display = _Display(start)
    for _ in range(5):
        view.hide(display, list(start))
        view.show(display, list(start))
    assert display.visible == start


def test_show_leaves_a_segment_it_never_hid():
    view = _module().ExtendedView()
    display = _Display({"D1": True, "PDA": False})
    view.hide(display, ["D1"])
    assert view.show(display, ["D1", "PDA"]) == 1
    assert display.visible == {"D1": True, "PDA": False}


def test_reset_forgets_and_no_display_is_harmless():
    view = _module().ExtendedView()
    display = _Display({"D1": True})
    view.hide(display, ["D1"])
    view.reset()
    assert not view.hidden and view.show(display, ["D1"]) == 0
    assert display.visible == {"D1": False}
    assert view.hide(None, ["D1"]) == 0 and view.show(None, ["D1"]) == 0


def test_extendedview_is_python39_clean_and_free_of_slicer():
    import ast

    tree = ast.parse((LIB / "extendedview.py").read_text(), feature_version=(3, 9))
    imported = {alias.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, (ast.Import, ast.ImportFrom))
                for alias in n.names}
    assert not imported & {"slicer", "qt", "vtk", "ctk", "numpy"}


def test_the_release_archive_carries_extendedview():
    workflow = (LIB.parents[2] / ".github" / "workflows" / "segqueue-release.yml").read_text()
    assert '"SegQueue14Lib/extendedview.py"' in workflow


def test_the_panel_hides_and_shows_through_it():
    import ast

    module = LIB.parent / "SegQueue14.py"
    source = module.read_text()
    tree = ast.parse(source)

    def method(cls, name):
        klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
        node = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == name)
        return ast.get_source_segment(source, node)

    toggle = method("SegQueue14Widget", "onToggleExtended")
    assert "self.logic.setExtendedShown(True)" in toggle
    assert "self.logic.setExtendedShown(False)" in toggle
    assert "self._applyExtendedRows()" in toggle
    assert "resetShowTicks=False" in toggle
    assert "self.extendedView = extendedview.ExtendedView()" in source
    assert "self.extendedView.reset()" in method("SegQueue14Logic", "closeCase")
    for name in ("_openAssignment", "onOpenReview"):
        assert "self._applyExtendedView()" in method("SegQueue14Widget", name), name
    rows = method("SegQueue14Widget", "_applyExtendedRows")
    assert "setHideSegments(" in rows


def test_a_class_that_cannot_be_read_is_never_taken_for_empty():
    """D53 root cause on a reviewer's panel: an unreadable class answered 'empty'."""
    import ast

    source = (LIB.parent / "SegQueue14.py").read_text()
    tree = ast.parse(source)
    helper = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == "_segmentHasContent")
    body = ast.get_source_segment(source, helper)
    fallback = body[body.index("except Exception:"):]
    assert "GetSegmentBinaryLabelmapRepresentation" in fallback
    assert fallback.rstrip().split("\n")[-2].strip() == "return True"
    review = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "onOpenReview")
    assert "SetReferenceImageGeometryParameterFromVolumeNode(volumeNode)" in \
        ast.get_source_segment(source, review)
