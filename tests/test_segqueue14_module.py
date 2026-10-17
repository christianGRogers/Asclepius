"""Static checks on the SegQueue14 Slicer module, as ``test_segqueue_module.py``
does for the live one -- plus the properties that make it safe to install beside
the live module: its own library, settings, routes and protocol, no updater that
could install SegQueue over it, the prelabel loaded into the project segments and
the D13 check before upload.

``SegQueue14.py`` imports Qt, VTK and Slicer, so it is parsed, not imported.
"""

import ast
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "slicer" / "SegQueue14" / "SegQueue14.py"
LIVE = REPO / "slicer" / "SegQueue" / "SegQueue.py"

INHERITED = {"parent", "layout", "developerMode"}


def _source():
    return MODULE.read_text(encoding="utf-8")


def _tree():
    return ast.parse(_source())


def _classes():
    return [n for n in ast.walk(_tree()) if isinstance(n, ast.ClassDef)]


def _self_attributes(classdef):
    defined, used = set(), {}
    for node in ast.walk(classdef):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name) and node.value.id == "self"):
            if isinstance(node.ctx, ast.Store):
                defined.add(node.attr)
            elif isinstance(node.ctx, ast.Load):
                used.setdefault(node.attr, node.lineno)
    return defined, used


def _module_level_names(tree):
    names = set(dir(__builtins__)) if isinstance(__builtins__, dict) is False else set(
        __builtins__)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.Try):
            for inner in ast.walk(node):
                if isinstance(inner, (ast.Import, ast.ImportFrom)):
                    for alias in inner.names:
                        names.add((alias.asname or alias.name).split(".")[0])
                if isinstance(inner, ast.Assign):
                    for target in inner.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
        elif isinstance(node, ast.If):
            pass
    return names


def test_the_module_parses():
    assert _tree() is not None


@pytest.mark.parametrize("classdef", _classes(), ids=lambda c: c.name)
def test_every_self_attribute_the_class_reads_is_one_it_defines(classdef):
    defined, used = _self_attributes(classdef)
    missing = {n: ln for n, ln in used.items() if n not in defined and n not in INHERITED}
    assert not missing, "{} reads attributes it never defines: {}".format(
        classdef.name, ", ".join(f"self.{n} (line {ln})" for n, ln in sorted(missing.items())))


def test_every_widget_signal_is_connected_to_something_that_exists():
    widget = next(c for c in _classes() if c.name == "SegQueue14Widget")
    defined, _ = _self_attributes(widget)
    handlers = []
    for node in ast.walk(widget):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("connect", "clicked")):
            continue
        for arg in node.args:
            for inner in ast.walk(arg):
                if (isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name)
                        and inner.value.id == "self"):
                    handlers.append((inner.attr, inner.lineno))
    assert handlers
    dead = [(n, ln) for n, ln in handlers if n not in defined]
    assert not dead, f"signals wired to nothing: {dead}"


def test_every_module_level_name_it_uses_exists():
    """A constant deleted with the updater and still read somewhere is a NameError
    the first time that code path runs -- inside Slicer, in front of an annotator."""
    tree = _tree()
    known = _module_level_names(tree) | {"__file__", "__doc__", "__name__"}
    outer = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        outer += [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    for func in outer:
        local = set()
        args = func.args
        for a in args.args + args.kwonlyargs + ([args.vararg] if args.vararg else []) + \
                ([args.kwarg] if args.kwarg else []):
            local.add(a.arg)
        for node in ast.walk(func):
            if isinstance(node, (ast.FunctionDef, ast.Lambda)) and node is not func:
                inner = node.args
                for a in inner.args + inner.kwonlyargs:
                    local.add(a.arg)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                local.add(node.id)
            elif isinstance(node, (ast.FunctionDef,)):
                local.add(node.name)
            elif isinstance(node, ast.comprehension):
                for sub in ast.walk(node.target):
                    if isinstance(sub, ast.Name):
                        local.add(sub.id)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                local.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    local.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                for sub in ast.walk(node.optional_vars):
                    if isinstance(sub, ast.Name):
                        local.add(sub.id)
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                assert node.id in known or node.id in local, (
                    f"{getattr(func, 'name', 'lambda')} uses undefined name {node.id!r} "
                    f"(line {node.lineno})")


# ------------------------------------------------------- side by side


def test_it_uses_its_own_library_and_never_the_live_one():
    source = _source()
    assert "from SegQueue14Lib import" in source
    assert not re.search(r"^\s*(from|import) SegQueueLib\b", source, re.M)


def test_its_updater_is_its_own_and_only_installs_segqueue14():
    # 0.14.0 on, SegQueue14 is the SegQueue release line and updates itself --
    # with SegQueue14Lib.updater, which refuses an archive without SegQueue14.py,
    # never with the live module's (that would accept a pre-0.14 SegQueue zip).
    source = _source()
    assert "updater" in re.findall(r"from SegQueue14Lib import \(?([^)]*)\)?", source)[0]
    for name in ("checkForUpdate", "installArchive", "onUpdateNow"):
        assert name in source
    lib = (REPO / "slicer" / "SegQueue14" / "SegQueue14Lib" / "updater.py").read_text()
    assert '"/SegQueue14.py"' in lib and '"/SegQueue.py"' not in lib


def test_every_settings_key_is_its_own():
    keys = re.findall(r'^_SETTING_\w+ = "([^"]+)"', _source(), re.M)
    assert keys and all(k.startswith("SegQueue14/") for k in keys), keys
    # The retired module's server URL is read as a default, never written.
    assert "setValue(_LIVE_SETTING_SERVER" not in _source()


def test_its_classes_are_named_so_slicer_registers_a_second_module():
    names = {c.name for c in _classes()}
    assert {"SegQueue14", "SegQueue14Logic", "SegQueue14Widget", "SegQueue14Test"} <= names
    live = {n.name for n in ast.walk(ast.parse(LIVE.read_text(encoding="utf-8")))
            if isinstance(n, ast.ClassDef)}
    shared = {n for n in names & live if not n.startswith("_")}
    assert not shared, "a public class name shared with the live module"


def test_it_never_names_a_live_route():
    assert "/segqueue/" not in _source()
    assert "from segqueue import protocol" not in _source()
    assert "from segqueue14 import protocol" in _source()


# -------------------------------------------------------- the workflow


def _method(classname, name):
    cls = next(c for c in _classes() if c.name == classname)
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)


def test_a_fresh_case_loads_the_prelabel_and_a_draft_does_not():
    open_case = ast.get_source_segment(_source(), _method("SegQueue14Logic", "openCase"))
    assert "_loadPrelabel" in open_case
    assert "not self.resumedDraft" in open_case


def test_the_prelabel_goes_into_the_project_segments_by_label_value():
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                     "importLabelsIntoProject"))
    assert "ImportLabelmapToSegmentationNode" in body
    # One class at a time into one named segment, so a class absent from the
    # prediction cannot shift the rest into the wrong segments.
    assert "values == int(spec.label)" in body


def test_the_vessel_seed_is_a_helper_and_never_a_class():
    # D23: the binary seed is shown beside the classes, as the heart region is,
    # so exportLabelmap (the project's own segments only) can never submit it.
    source = _source()
    loader = ast.get_source_segment(source, _method("SegQueue14Logic", "_loadHelpers"))
    assert "protocol.ASSET_SEED" in loader and "protocol.SEED_SEGMENT_NAME" in loader
    assert "_fetchHelper" in loader and "importLabelsIntoProject" not in loader
    helpers = ast.get_source_segment(source, _method("SegQueue14Logic", "helperIds"))
    assert "seedSegmentId" in helpers and "regionSegmentId" in helpers


def test_a_seeded_case_starts_with_the_seed_in_every_class_hidden():
    # D26: each class is a copy of the seed for the annotator to cut down; the
    # copies are hidden so they do not hide each other. A draft is never refilled.
    open_case = ast.get_source_segment(_source(), _method("SegQueue14Logic", "openCase"))
    assert "elif not self.resumedDraft and assignment.has_seed" in open_case
    assert "_prefillClassesFromSeed" in open_case
    assert open_case.index("applyViewPreset") < open_case.index("setClassesVisible(False)")
    copy = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                     "copySegmentIntoEveryClass"))
    # Per-class array writes: one import into several targets fills only the first.
    assert "updateSegmentBinaryLabelmapFromArray" in copy
    assert "ImportLabelmapToSegmentationNode" not in copy


@pytest.mark.parametrize("method", ["submit", "reviseSubmission"])
def test_overlapping_classes_are_refused_before_the_export(method):
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic", method))
    assert body.index("classOverlaps()") < body.index("exportLabelmap")
    assert "labels.overlap_message" in body


@pytest.mark.parametrize("method", ["submit", "reviseSubmission"])
def test_required_classes_are_checked_before_anything_is_uploaded(method):
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic", method))
    check = body.index("missing_required")
    assert check < body.index("uploadFile"), "the D13 check must come before the upload"


def test_there_is_no_instructions_panel_and_help_is_a_link():
    # Project lead, 2026-10-17: no instructions section in the UI; the module
    # help is a link to the repository.
    source = _source()
    assert "instructionsBox" not in source and "_renderInstructions" not in source
    module = next(c for c in _classes() if c.name == "SegQueue14")
    init = ast.get_source_segment(source, next(
        n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"))
    assert "helpText" in init and "HELP_URL" in init and "__doc__" not in init
    assert 'HELP_URL = "https://github.com/christianGRogers/Asclepius"' in source


# ------------------------------------------------------------ packaging


def test_the_archive_is_the_segqueue_extension_and_is_self_sufficient(tmp_path):
    import importlib.util
    import subprocess
    import sys
    import zipfile

    spec = importlib.util.spec_from_file_location(
        "build14", REPO / "slicer" / "build-extension14.py")
    build14 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build14)
    archive, version, _ = build14.build(str(tmp_path))
    # Named and rooted as SegQueue (tests/test_segqueue14_release_line.py says why).
    assert Path(archive).name == f"SegQueue-{version}-Slicer-5.8.zip"
    names = zipfile.ZipFile(archive).namelist()
    assert {n.split("/")[0] for n in names} == {"SegQueue"}
    scripted = "SegQueue/lib/Slicer-5.8/qt-scripted-modules/"
    assert scripted + "SegQueue14.py" in names
    assert scripted + "segqueue14/protocol.py" in names
    assert scripted + "segqueue/protocol.py" in names
    assert not any("SegQueueLib/" in n for n in names)
    assert "SegQueue/share/Slicer-5.8/SegQueue.s4ext" in names

    # The vendored shared packages import with nothing from the repository on
    # the path.
    zipfile.ZipFile(archive).extractall(tmp_path / "x")
    path = tmp_path / "x" / scripted
    code = ("import sys; sys.path[:] = [p for p in sys.path if 'src' not in p]; "
            f"sys.path.insert(0, {str(path)!r}); "
            # SegQueue14Lib itself needs `requests`, which Slicer bundles.
            "import segqueue14.protocol, segqueue14.labels, segqueue14.plan; "
            "assert segqueue14.__file__.startswith(sys.path[0]); "
            "print(segqueue14.PROTOCOL_VERSION)")
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "16"
