"""``SegQueue14Lib.overlap`` (0.25.4, D52, D39, D44): "Allow overlap" while editing.

A material painted inside an artery must keep both. Slicer's own Segment Editor
module made its parameter node with Slicer's default, "Overwrite all", and erased
the artery under the plaque; the module now registers a default node and sets the
nodes it binds. The Slicer side is checked by ``tests/slicer_selftest14.py``
(``run_overlap``); this is the logic, with stand-ins for the node class and scene.
"""

import ast
import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
LIB = REPO / "slicer" / "SegQueue14" / "SegQueue14Lib"
MODULE = REPO / "slicer" / "SegQueue14" / "SegQueue14.py"


def _overlap():
    spec = importlib.util.spec_from_file_location("segqueue14_overlap", LIB / "overlap.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _EditorNode:
    """``vtkMRMLSegmentEditorNode`` as far as the helper uses it."""

    OverwriteAllSegments, OverwriteVisibleSegments, OverwriteNone = 0, 1, 2

    def __init__(self, mode=0):
        self.mode = mode
        self.sets = 0

    def GetOverwriteMode(self):
        return self.mode

    def SetOverwriteMode(self, mode):
        self.sets += 1
        self.mode = mode


class _NoConstant:
    """A Slicer whose wrapping lost the enum constant but keeps the name lookup."""

    __init__ = _EditorNode.__init__
    GetOverwriteMode = _EditorNode.GetOverwriteMode
    SetOverwriteMode = _EditorNode.SetOverwriteMode

    @staticmethod
    def ConvertOverwriteModeFromString(name):
        return {"OverwriteAllSegments": 0, "OverwriteVisibleSegments": 1,
                "OverwriteNone": 2}.get(name, -1)



class _Unknown:
    """No constant and no lookup: nothing is guessed."""

    def __init__(self):
        self.mode = 0

    def GetOverwriteMode(self):
        return self.mode

    def SetOverwriteMode(self, mode):  # pragma: no cover - must not be called
        raise AssertionError("set without a known mode")


class _Scene:
    def __init__(self, singleton=None, default=None):
        self.defaults = {} if default is None else {"vtkMRMLSegmentEditorNode": default}
        self.singleton = singleton
        self.asked = []

    def GetDefaultNodeByClass(self, name):
        return self.defaults.get(name)

    def AddDefaultNode(self, node):
        self.defaults["vtkMRMLSegmentEditorNode"] = node

    def GetSingletonNode(self, tag, name):
        self.asked.append((tag, name))
        return self.singleton


def test_allow_overlap_is_overwrite_none():
    ov = _overlap()
    assert ov.allow_overlap_mode(_EditorNode) == 2
    node = _EditorNode(0)
    assert not ov.allows_overlap(node, _EditorNode)
    assert ov.allow_overlap(node, _EditorNode)
    assert node.mode == 2 and ov.allows_overlap(node, _EditorNode)


def test_a_node_already_allowing_overlap_is_not_written_again():
    ov = _overlap()
    node = _EditorNode(2)
    assert ov.allow_overlap(node, _EditorNode)
    assert node.sets == 0


def test_the_mode_is_looked_up_by_name_without_the_constant():
    ov = _overlap()
    assert not hasattr(_NoConstant, "OverwriteNone")
    assert ov.allow_overlap_mode(_NoConstant) == 2
    node = _NoConstant(0)
    assert ov.allow_overlap(node, _NoConstant) and node.mode == 2


def test_nothing_is_guessed_when_the_mode_is_unknown():
    ov = _overlap()
    assert ov.allow_overlap_mode(_Unknown) is None
    assert not ov.allow_overlap(_Unknown(), _Unknown)
    assert not ov.allows_overlap(_Unknown(), _Unknown)
    assert not ov.allow_overlap(None, _EditorNode)


def test_a_failing_node_never_raises():
    ov = _overlap()

    class Broken(_EditorNode):
        def SetOverwriteMode(self, mode):
            raise RuntimeError("deleted")

    assert not ov.allow_overlap(Broken(0), _EditorNode)


def test_the_scene_default_starts_new_nodes_at_allow_overlap():
    ov = _overlap()
    scene = _Scene()
    default = ov.allow_overlap_by_default(scene, _EditorNode)
    assert scene.defaults["vtkMRMLSegmentEditorNode"] is default
    assert default.mode == 2
    # Idempotent: the same default node, still Allow overlap.
    assert ov.allow_overlap_by_default(scene, _EditorNode) is default


def test_another_modules_default_node_is_kept_and_only_its_mode_set():
    ov = _overlap()
    theirs = _EditorNode(0)
    theirs.other = "kept"
    scene = _Scene(default=theirs)
    assert ov.allow_overlap_by_default(scene, _EditorNode) is theirs
    assert theirs.mode == 2 and theirs.other == "kept"


def test_a_scene_without_default_nodes_is_left_alone():
    ov = _overlap()
    assert ov.allow_overlap_by_default(None, _EditorNode) is None
    assert ov.allow_overlap_by_default(object(), _EditorNode) is None


def test_binding_sets_the_panel_and_the_segment_editor_modules_node():
    ov = _overlap()
    module_node = _EditorNode(0)        # Slicer's Segment Editor module: Overwrite all
    panel = _EditorNode(1)
    scene = _Scene(singleton=module_node)
    done = ov.allow_overlap_everywhere(scene, _EditorNode, [panel, None])
    assert panel.mode == 2 and module_node.mode == 2
    assert done == [panel, module_node]
    assert scene.asked == [("SegmentEditor", "vtkMRMLSegmentEditorNode")]
    assert scene.defaults["vtkMRMLSegmentEditorNode"].mode == 2


def test_the_same_node_twice_is_set_once():
    ov = _overlap()
    node = _EditorNode(0)
    done = ov.allow_overlap_everywhere(_Scene(singleton=node), _EditorNode, [node])
    assert done == [node] and node.sets == 1


def test_overlap_is_python39_clean_and_free_of_slicer():
    tree = ast.parse((LIB / "overlap.py").read_text(), feature_version=(3, 9))
    imported = {alias.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, (ast.Import, ast.ImportFrom))
                for alias in n.names}
    assert not imported & {"slicer", "qt", "vtk", "ctk", "numpy"}


def _method(name):
    tree = ast.parse(MODULE.read_text())
    widget = next(n for n in tree.body
                  if isinstance(n, ast.ClassDef) and n.name == "SegQueue14Widget")
    return next(n for n in widget.body if isinstance(n, ast.FunctionDef) and n.name == name)


def test_every_editor_node_the_module_makes_allows_overlap():
    source = MODULE.read_text()
    assert "from SegQueue14Lib import overlap" in source
    for name in ("_buildEditorSection", "_ensureEditorNode"):
        body = ast.get_source_segment(source, _method(name))
        default = body.index("overlap.allow_overlap_by_default(")
        made = body.index('AddNewNodeByClass("vtkMRMLSegmentEditorNode")')
        assert default < made, name
        assert body.index("overlap.allow_overlap(self.editorNode") > made, name


def test_binding_a_case_allows_overlap_on_every_editor_node():
    body = ast.get_source_segment(MODULE.read_text(), _method("_bindEditor"))
    assert "overlap.allow_overlap_everywhere(" in body
    assert body.index("_ensureEditorNode()") < body.index("allow_overlap_everywhere(")
    # Only on binding, never observed: a deliberate choice in the Masking panel
    # stays until the next case opens.
    assert "AddObserver" not in body


def test_the_release_archive_carries_overlap():
    workflow = (REPO / ".github" / "workflows" / "segqueue-release.yml").read_text()
    assert '"SegQueue14Lib/overlap.py"' in workflow
