"""``SegQueue14Lib.selection`` (0.25.4, D52): selecting a class shows it.

Classes of a seeded case start hidden (D26, D51); Slicer's editor asks "the
selected segment is hidden, make it visible?" at the first stroke and drops it.
The panel shows the class selected for editing instead, and only that class. The
Slicer side is checked by ``tests/slicer_selftest14.py`` (``run_overlap``); this
is the logic, with stand-ins for the editor node and segmentation, and the
module's wiring, read from its source.
"""

import ast
import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
LIB = REPO / "slicer" / "SegQueue14" / "SegQueue14Lib"
MODULE = REPO / "slicer" / "SegQueue14" / "SegQueue14.py"


def _selection():
    spec = importlib.util.spec_from_file_location("segqueue14_selection", LIB / "selection.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Display:
    def __init__(self, visible):
        self.visible = dict(visible)
        self.sets = []

    def GetSegmentVisibility(self, segment_id):
        return self.visible[segment_id]

    def SetSegmentVisibility(self, segment_id, visible):
        self.sets.append((segment_id, visible))
        self.visible[segment_id] = visible


class _Segmentation:
    def __init__(self, ids):
        self.ids = set(ids)

    def GetSegment(self, segment_id):
        return object() if segment_id in self.ids else None


class _SegmentationNode:
    def __init__(self, visible, display=True):
        self.display = _Display(visible) if display else None
        self.segmentation = _Segmentation(visible)

    def GetDisplayNode(self):
        return self.display

    def GetSegmentation(self):
        return self.segmentation


class _EditorNode:
    def __init__(self, node=None, selected=None):
        self.node, self.selected = node, selected

    def GetSelectedSegmentID(self):
        return self.selected

    def GetSegmentationNode(self):
        return self.node


def _hidden():
    return _SegmentationNode({"LM": False, "LAD": False, "Calcified plaque": False,
                              "seed": True})


def test_selecting_a_hidden_class_shows_it_and_nothing_else():
    sel = _selection()
    node = _hidden()
    editor = _EditorNode(node, "LAD")
    watcher = sel.ShowSelected()
    assert watcher.update(editor) is True
    assert node.display.visible == {"LM": False, "LAD": True, "Calcified plaque": False,
                                    "seed": True}
    assert node.display.sets == [("LAD", True)]


def test_a_new_selection_shows_the_new_class_and_leaves_the_old_one():
    sel = _selection()
    node = _hidden()
    editor = _EditorNode(node, "LAD")
    watcher = sel.ShowSelected()
    watcher.update(editor)
    editor.selected = "Calcified plaque"
    assert watcher.update(editor) is True
    assert node.display.visible["LAD"] and node.display.visible["Calcified plaque"]
    assert not node.display.visible["LM"]


def test_a_class_hidden_again_while_selected_stays_hidden():
    # The editor node is modified by every effect parameter: that is no new selection.
    sel = _selection()
    node = _hidden()
    editor = _EditorNode(node, "LAD")
    watcher = sel.ShowSelected()
    watcher.update(editor)
    node.display.visible["LAD"] = False          # the annotator's eye
    assert watcher.update(editor) is False
    assert node.display.visible["LAD"] is False


def test_binding_shows_the_selection_even_with_the_same_id():
    # The next case's LM may have the id the last case's had: binding forces it.
    sel = _selection()
    first, second = _hidden(), _hidden()
    editor = _EditorNode(first, "LM")
    watcher = sel.ShowSelected()
    watcher.update(editor)
    first.display.visible["LM"] = False
    assert watcher.update(editor, force=True) is True and first.display.visible["LM"]
    # A different segmentation node with the same id is a new selection.
    editor.node = second
    assert watcher.update(editor) is True and second.display.visible["LM"]


def test_an_already_visible_class_is_not_touched():
    sel = _selection()
    node = _SegmentationNode({"LAD": True})
    assert sel.ShowSelected().update(_EditorNode(node, "LAD"), force=True) is False
    assert node.display.sets == []


def test_nothing_selected_or_nothing_to_show_never_raises():
    sel = _selection()
    watcher = sel.ShowSelected()
    assert watcher.update(None) is False
    assert watcher.update(_EditorNode(None, "LAD"), force=True) is False
    assert watcher.update(_EditorNode(_hidden(), None), force=True) is False
    assert watcher.update(_EditorNode(_hidden(), "gone"), force=True) is False
    assert watcher.update(_EditorNode(_SegmentationNode({"LAD": False}, display=False),
                                      "LAD"), force=True) is False

    class Broken:
        def GetSelectedSegmentID(self):
            raise RuntimeError("deleted")

    assert sel.selected_segment(Broken()) == (None, None)
    assert sel.show_segment(None, "LAD") is False


def test_on_select_runs_on_a_new_selection_before_it_is_shown():
    """D52: the module fills a branch's seed copy there, once per new selection."""
    sel = _selection()
    node = _hidden()
    seen = []

    def on_select(segmentation_node, segment_id):
        seen.append((segment_id, segmentation_node.display.visible[segment_id]))

    watcher = sel.ShowSelected(on_select)
    editor = _EditorNode(node, "LAD")
    watcher.update(editor)
    watcher.update(editor)                       # an effect parameter: no new selection
    editor.selected = "Calcified plaque"
    watcher.update(editor)
    watcher.update(editor, force=True)           # a case bound
    assert seen == [("LAD", False), ("Calcified plaque", False), ("Calcified plaque", True)]
    watcher.update(_EditorNode(node, None), force=True)
    assert len(seen) == 3


def test_on_select_writing_into_the_node_does_not_select_again():
    sel = _selection()
    node = _hidden()
    editor = _EditorNode(node, "LAD")
    calls = []

    def on_select(segmentation_node, segment_id):
        calls.append(segment_id)
        watcher.update(editor)                   # the write modifies the editor node

    watcher = sel.ShowSelected(on_select)
    assert watcher.update(editor) is True and calls == ["LAD"]


def test_a_failing_on_select_still_shows_the_class():
    sel = _selection()
    node = _hidden()

    def broken(*args):
        raise RuntimeError("no seed")

    assert sel.ShowSelected(broken).update(_EditorNode(node, "LAD")) is True
    assert node.display.visible["LAD"] is True


def test_selection_is_python39_clean_and_free_of_slicer():
    tree = ast.parse((LIB / "selection.py").read_text(), feature_version=(3, 9))
    imported = {alias.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, (ast.Import, ast.ImportFrom))
                for alias in n.names}
    assert not imported & {"slicer", "qt", "vtk", "ctk", "numpy"}


def _method(name):
    tree = ast.parse(MODULE.read_text())
    widget = next(n for n in tree.body
                  if isinstance(n, ast.ClassDef) and n.name == "SegQueue14Widget")
    return next(n for n in widget.body if isinstance(n, ast.FunctionDef) and n.name == name)


def test_every_editor_node_the_panel_makes_is_watched():
    source = MODULE.read_text()
    for name in ("_buildEditorSection", "_ensureEditorNode"):
        body = ast.get_source_segment(source, _method(name))
        assert body.index("setMRMLSegmentEditorNode(self.editorNode)") < body.index(
            "self._watchSelection(self.editorNode)"), name
    watch = ast.get_source_segment(source, _method("_watchSelection"))
    assert "RemoveObserver(" in watch and "vtk.vtkCommand.ModifiedEvent" in watch
    assert "self._onEditorNodeModified" in watch
    assert "selection.ShowSelected(self._onClassSelected)" in watch
    cleanup = ast.get_source_segment(source, _method("cleanup"))
    assert "self._watchSelection(None)" in cleanup


def test_binding_a_case_shows_the_selected_class():
    body = ast.get_source_segment(MODULE.read_text(), _method("_bindEditor"))
    assert body.index("setSegmentationNode(segmentationNode)") < body.index(
        "self._showSelected.update(self.editorNode, force=True)")


def test_the_release_archive_carries_selection():
    workflow = (REPO / ".github" / "workflows" / "segqueue-release.yml").read_text()
    assert '"SegQueue14Lib/selection.py"' in workflow
