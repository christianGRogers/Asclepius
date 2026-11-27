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
    # Changing a segment's label value after the import empties every class but the
    # first (Slicer 5.12; tests/slicer_selftest14.py checks the real thing).
    assert ".SetLabelValue(" not in body


def test_only_the_imagecas_x_reference_is_collapsed_from_14_classes():
    # #68: the reviewer's reference is ImageCAS-X's 14 values and is collapsed to
    # the four (labels.icx14_to_four, D25) because it is the reference -- not by
    # its values. Prelabels and submissions are imported strictly by value.
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                     "importLabelsIntoProject"))
    assert "labels.icx14_to_four(" in body and "if icx14:" in body
    calls = [node for node in ast.walk(ast.parse(_source()))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
             and node.func.attr == "importLabelsIntoProject"]
    collapsing = [any(k.arg == "icx14" and getattr(k.value, "value", None) is True
                      for k in call.keywords) for call in calls]
    assert collapsing.count(True) == 1, collapsing
    reference = ast.get_source_segment(_source(), _method("SegQueue14Widget",
                                                          "onShowReference"))
    assert "icx14=True" in reference and "protocol.ASSET_REFERENCE" in reference


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
    every = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                      "copySegmentIntoEveryClass"))
    assert "copySegmentIntoClasses(" in every and "self.project.segments" in every
    copy = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                     "copySegmentIntoClasses"))
    # Per-class writes (one import into several targets fills only the first), in
    # place (0.25.5): no array round trip against the CT, which made each copy a
    # full-CT labelmap layer.
    code = copy.split('"""')[2]   # the body, without the docstring's history
    assert "self.copySegmentInto(sourceSegmentId, segmentId)" in code
    assert "updateSegmentBinaryLabelmapFromArray" not in code
    assert "arrayFromSegmentBinaryLabelmap" not in code
    assert "ImportLabelmapToSegmentationNode" not in code


@pytest.mark.parametrize("method", ["submit", "reviseSubmission"])
def test_nothing_about_the_segmentation_is_checked_before_the_upload(method):
    # #270 (project lead, 2026-11-02): no D13, D26 or empty-scene refusal.
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic", method))
    assert body.index("self.exportSubmission(") < body.index("uploadFile")
    for gone in ("classOverlaps", "missing_required", "overlap_message", "_exportChecked"):
        assert gone not in body
    # D39 (#275): the upload says it is a class stack, every class whole.
    assert "labelFormat=labelfile.FORMAT_CLASS_STACK" in body


def test_a_reopened_draft_keeps_its_label_values():
    # The false "LAD, LCx and RCA are empty" of #270: re-pinning the label value
    # of a segment loaded from a draft left its voxels unreadable.
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic", "_applyTemplate"))
    assert body.index("if not created:") < body.index("SetLabelValue")


def test_an_empty_scene_is_still_written():
    # An empty class is an all-zero channel on the CT grid, never a refusal.
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic", "_segmentMask"))
    assert "np.zeros(shape, np.uint8)" in body


def test_every_class_is_exported_whole_on_the_ct_grid():
    # D39 (#275): no single label volume (one class per voxel) is written; each
    # class is read against the CT, by name, and written as its own channel.
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic", "exportSubmission"))
    assert "logic().ExportSegmentsToLabelmapNode(" not in body
    assert "labelfile.write_class_stack(" in body
    mask = ast.get_source_segment(_source(), _method("SegQueue14Logic", "_segmentMask"))
    assert "arrayFromSegmentBinaryLabelmap(" in mask and "self.volumeNode" in mask
    assert "_segmentMask(" in ast.get_source_segment(
        _source(), _method("SegQueue14Logic", "_classMask"))
    assert "exportLabelmap" not in _source()


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
            "import segqueue14.protocol, segqueue14.labels, segqueue14.plan, "
            "segqueue14.labelfile; "
            "assert segqueue14.__file__.startswith(sys.path[0]); "
            "print(segqueue14.PROTOCOL_VERSION)")
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "21"


def test_a_half_downloaded_helper_is_never_a_cache_hit(tmp_path):
    # #64: a ``.part`` left by a download Slicer never finished must not be
    # reused as the helper; only a completed file counts.
    import os
    namespace = {"os": os}
    exec(compile(ast.Module(body=[_method("SegQueue14Logic", "_cachedHelper")],
                            type_ignores=[]), str(MODULE), "exec"), namespace)
    cachedHelper = namespace["_cachedHelper"]
    stem = str(tmp_path / "prelabel")
    (tmp_path / "prelabel.nii.gz.part").write_bytes(b"\x1f\x8bhalf")
    assert cachedHelper(None, stem) is None
    (tmp_path / "prelabel.nii.gz").write_bytes(b"\x1f\x8bwhole")
    assert cachedHelper(None, stem) == stem + ".nii.gz"


# --------------------------------------------------- reviewer state filter (#281)

def _review_filters():
    for node in _tree().body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "REVIEW_FILTERS"
                        for t in node.targets)):
            return ast.literal_eval(node.value)
    raise AssertionError("REVIEW_FILTERS not found")


#: The review-list functions, which need nothing from Slicer.
_LISTING = ("_reviewListing", "_parseUtc", "_easternTime", "_newestFirst", "_epochIso",
            "_mySubmissionRows", "_reviewRowShown", "_defectHolders", "_defectPrompt",
            "_defectTooltip")
#: Module constants those functions read.
_LISTING_CONSTANTS = ("REVIEW_HOLDING_STATES",)


def _listing_namespace():
    import sys

    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.append(src)
    from segqueue14 import protocol

    nodes = [n for n in _tree().body
             if isinstance(n, ast.FunctionDef) and n.name in _LISTING]
    assert sorted(n.name for n in nodes) == sorted(_LISTING)
    nodes += [n for n in _tree().body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id in _LISTING_CONSTANTS for t in n.targets)]
    namespace = {"protocol": protocol}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(MODULE), "exec"),
         namespace)
    return namespace


def _review_listing():
    """``_reviewListing`` executed on its own: it needs nothing from Slicer."""
    return _listing_namespace()["_reviewListing"]


class _Client:
    """Answers ``allCases`` the way the 0.3.0 server does: a state filter keeps
    every case with *any* assignment in that state, with all its assignments."""

    def __init__(self, cases):
        self.cases = cases
        self.calls = []

    def allCases(self, state=None, unassigned=False):
        self.calls.append((state, unassigned))
        if unassigned:
            return [c for c in self.cases if not c["assignments"]]
        if state:
            return [c for c in self.cases
                    if any(a["state"] == state for a in c["assignments"])]
        return list(self.cases)


def _case(case_id, *states):
    return {"caseId": case_id, "caseName": case_id,
            "assignments": [{"annotator": "a{}".format(i), "state": s}
                            for i, s in enumerate(states)]}


ALL_STATES = ("assigned", "downloaded", "rejected", "submitted", "under_review",
              "approved", "released")


def _project():
    return [_case("two_reads", "submitted", "downloaded"),
            _case("given_back", "submitted", "released"),
            _case("nobody")] + [_case("only_" + s, s) for s in ALL_STATES]


def test_the_state_filter_has_exactly_the_five_reviewer_entries():
    filters = _review_filters()
    assert [label for label, _ in filters] == [
        "All cases", "Unassigned", "In progress", "Waiting for review", "Approved"]
    assert dict(filters) == {
        "All cases": None,
        "Unassigned": "unassigned",
        "In progress": ("assigned", "downloaded", "rejected"),
        "Waiting for review": ("submitted", "under_review"),
        "Approved": ("approved",),
    }


def test_the_dropdown_is_filled_from_the_filters_and_read_by_index():
    source = ast.get_source_segment(_source(), _method("SegQueue14Widget",
                                                       "onRefreshReview"))
    assert "REVIEW_FILTERS[index]" in source
    assert "itemData" not in source


@pytest.mark.parametrize("other", ["downloaded", "released"])
def test_a_two_read_case_shows_only_its_submitted_read_while_waiting(other):
    listing = _review_listing()
    cases, rows = listing(_Client([_case("c1", "submitted", other)]),
                          ("submitted", "under_review"))
    assert [c["caseId"] for c in cases] == ["c1"]
    assert [(c["caseId"], a["state"]) for c, a in rows] == [("c1", "submitted")]


@pytest.mark.parametrize("label", ["In progress", "Waiting for review", "Approved"])
def test_each_group_shows_only_its_states(label):
    states = dict(_review_filters())[label]
    cases, rows = _review_listing()(_Client(_project()), states)
    shown = {a["state"] for _c, a in rows}
    assert shown == set(states)
    assert all(a is not None for _c, a in rows)
    # Every read in the group is there, and every case listed has a row.
    expected = sum(1 for c in _project() for a in c["assignments"]
                   if a["state"] in states)
    assert len(rows) == expected
    assert {c["caseId"] for c in cases} == {c["caseId"] for c, _a in rows}


def test_all_cases_shows_every_read_and_a_row_for_a_case_nobody_holds():
    client = _Client(_project())
    cases, rows = _review_listing()(client, None)
    assert client.calls == [(None, False)]
    assert len(cases) == len(_project())
    assert ("nobody", None) in [(c["caseId"], a) for c, a in rows]
    assert len(rows) == 1 + sum(len(c["assignments"]) for c in _project())


def test_unassigned_is_the_unassigned_listing_unchanged():
    client = _Client(_project())
    cases, rows = _review_listing()(client, "unassigned")
    assert client.calls == [(None, True)]
    assert [c["caseId"] for c in cases] == ["nobody"]
    assert [(c["caseId"], a) for c, a in rows] == [("nobody", None)]


# ------------------------------------- #280: the reviewer list, newest first, in ET


@pytest.mark.parametrize("stamp, shown", [
    # Winter, EST (UTC-5).
    ("2026-01-15T17:32:10.123000", "2026-01-15 12:32 ET"),
    ("2026-11-10T19:32:00+00:00", "2026-11-10 14:32 ET"),
    # Summer, EDT (UTC-4).
    ("2026-07-01T04:05:00", "2026-07-01 00:05 ET"),
    # DST starts 2026-03-08 at 02:00 EST (07:00 UTC).
    ("2026-03-08T06:59:00", "2026-03-08 01:59 ET"),
    ("2026-03-08T07:00:00", "2026-03-08 03:00 ET"),
    # DST ends 2026-11-01 at 02:00 EDT (06:00 UTC): 01:xx happens twice.
    ("2026-11-01T05:30:00", "2026-11-01 01:30 ET"),
    ("2026-11-01T06:30:00", "2026-11-01 01:30 ET"),
    ("2026-11-01T07:00:00", "2026-11-01 02:00 ET"),
    # Another year's rule dates (2027: 14 March, 7 November).
    ("2027-03-14T07:00:00Z", "2027-03-14 03:00 ET"),
    ("2027-11-07T05:59:00Z", "2027-11-07 01:59 ET"),
    ("2027-11-07T06:00:00Z", "2027-11-07 01:00 ET"),
    # An offset other than UTC is converted, not trusted as Eastern.
    ("2026-07-01T10:00:00+02:00", "2026-07-01 04:00 ET"),
    (None, "--"), ("", "--"), ("not a date", "--"),
])
def test_submission_times_are_shown_in_us_eastern_time(stamp, shown):
    assert _listing_namespace()["_easternTime"](stamp) == shown


def test_the_review_list_is_newest_submission_first_and_unsubmitted_last():
    def case(name, *submitted):
        return {"caseId": name, "caseName": name,
                "assignments": [{"annotator": "a{}".format(i), "state": "submitted"
                                 if when else "downloaded", "submittedAt": when}
                                for i, when in enumerate(submitted)]}

    cases = [case("old", "2026-11-01T12:00:00"),
             case("pair", "2026-11-09T08:00:00+00:00", None),
             case("nobody"),
             case("newest", "2026-11-10T19:32:00"),
             case("middle", "2026-11-05T12:00:00")]
    cases[2]["assignments"] = []
    listing = _review_listing()
    _, rows = listing(_Client(cases), None)
    order = [(c["caseName"], (a or {}).get("submittedAt")) for c, a in rows]
    assert order == [("newest", "2026-11-10T19:32:00"),
                     ("pair", "2026-11-09T08:00:00+00:00"),
                     ("middle", "2026-11-05T12:00:00"),
                     ("old", "2026-11-01T12:00:00"),
                     ("pair", None), ("nobody", None)]
    # A state group is sorted the same way.
    _, rows = listing(_Client(cases), ("submitted",))
    assert [c["caseName"] for c, _ in rows] == ["newest", "pair", "middle", "old"]


def test_the_review_table_shows_the_submission_time_in_eastern_time():
    source = MODULE.read_text()
    assert '"Submitted (ET)"' in source
    assert '_easternTime(assignment.get("submittedAt"))' in source


# ---------------------------------------------------- compare reads (#335)

#: Every method of the "Compare reads" view, logic and panel.
_COMPARE_LOGIC = ("loadComparison", "_readClassPieces", "_paintRead", "setAgreementPair",
                  "agreementSegmentName", "_buildAgreementNode", "setCompareMode",
                  "setAgreementClass", "setReadVisible", "setReadOpacity",
                  "_applyCompareVisibility", "closeComparison")
_COMPARE_WIDGET = ("_buildCompareSection", "_comparableReads", "onCompareReads",
                   "_fillComparePanel", "_fillCompareClasses", "_updateCompareSummary",
                   "onCompareModeChanged", "onComparePairChanged", "onCompareClassChanged",
                   "onCloseComparison")


def _calls_in(node):
    return {n.func.attr for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}


def test_the_module_is_0_25_8_and_protocol_21():
    assert re.search(r'^__version__ = "0\.25\.8"$', _source(), re.M)
    sys_path = str(REPO / "src")
    import sys

    if sys_path not in sys.path:
        sys.path.append(sys_path)
    from segqueue14 import PROTOCOL_VERSION

    assert PROTOCOL_VERSION == 21


def test_comparing_never_writes_a_submission_a_draft_or_a_decision():
    """Read-only (#335): the only server calls are downloads, nothing is saved."""
    forbidden = {"uploadFile", "submit", "reviseSubmission", "claim", "claimReview",
                 "verdict", "returnToPool", "releaseCase", "saveNode", "autosave",
                 "exportSubmission", "assignCase", "_bindEditor"}
    for classname, names in (("SegQueue14Logic", _COMPARE_LOGIC),
                             ("SegQueue14Widget", _COMPARE_WIDGET)):
        for name in names:
            used = _calls_in(_method(classname, name)) & forbidden
            assert not used, f"{classname}.{name} calls {sorted(used)}"
    body = ast.get_source_segment(_source(), _method("SegQueue14Widget", "onCompareReads"))
    client = set(re.findall(r"self\.logic\.client\.(\w+)", body))
    assert client == {"downloadReviewFile"}
    # Nothing is left open for review: Save changes & approve stays disabled.
    assert "self._endReview()" in body
    load = ast.get_source_segment(_source(), _method("SegQueue14Logic", "loadComparison"))
    assert "self.segmentationNode = None" in load


def test_the_compare_panel_is_wired():
    build = ast.get_source_segment(_source(), _method("SegQueue14Widget",
                                                      "_buildCompareSection"))
    for wiring in ("self.compareButton.clicked.connect(self.onCompareReads)",
                   "self.compareModeCombo.currentIndexChanged.connect(self.onCompareModeChanged)",
                   "combo.currentIndexChanged.connect(self.onComparePairChanged)",
                   "self.compareClassCombo.currentIndexChanged.connect(self.onCompareClassChanged)",
                   "self.compareReviseButton.clicked.connect(self.onCompareOpenForRevision)",
                   "self.compareCloseButton.clicked.connect(self.onCloseComparison)",
                   "self.includeReopenedCheck.toggled.connect("):
        assert wiring in build, wiring
    review = ast.get_source_segment(_source(), _method("SegQueue14Widget",
                                                       "_buildReviewSection"))
    assert "self._buildCompareSection(layout)" in review
    fill = ast.get_source_segment(_source(), _method("SegQueue14Widget", "_fillComparePanel"))
    assert "self.logic.setReadVisible(key, on)" in fill
    assert "self.logic.setReadOpacity(key, value / 100.0)" in fill


def test_the_compare_modes_are_side_by_side_and_the_agreement_map():
    for node in _tree().body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "COMPARE_MODES"
                        for t in node.targets)):
            modes = ast.literal_eval(node.value)
            break
    else:
        raise AssertionError("COMPARE_MODES not found")
    assert [mode for _label, mode in modes] == ["side", "agreement"]


def test_compare_is_offered_only_with_two_reads_and_reopened_reads_only_when_asked():
    enabled = ast.get_source_segment(_source(), _method("SegQueue14Widget",
                                                        "_updateReviewEnabled"))
    assert "len(self._comparableReads()) >= 2" in enabled
    assert "self.logic.assignment is None" in enabled
    picker = ast.get_source_segment(_source(), _method("SegQueue14Widget",
                                                       "_comparableReads"))
    assert "compare.comparable_reads(" in picker
    assert "self.includeReopenedCheck.checked" in picker


def test_a_review_open_or_a_case_open_ends_the_comparison():
    for classname, name in (("SegQueue14Widget", "onOpenReview"),
                            ("SegQueue14Logic", "closeCase")):
        body = ast.get_source_segment(_source(), _method(classname, name))
        assert "closeComparison()" in body, name


def test_a_refused_release_shows_the_servers_message_and_keeps_the_case():
    """The benchmark (D43) cannot be released: the module does not know a case is
    the benchmark (the kind is never sent), so the server's refusal is what the
    annotator sees. ``releaseCase`` raises before ``closeCase`` purges anything,
    and the widget shows ``str(exc)`` and returns with the case still open."""
    logic = ast.get_source_segment(_source(), _method("SegQueue14Logic", "release"))
    assert logic.index("self.client.releaseCase(") < logic.index("self.closeCase(")
    widget = ast.get_source_segment(_source(), _method("SegQueue14Widget", "onRelease"))
    handler = widget[widget.index("except SegQueueError as exc:"):]
    assert handler.split("return", 1)[0].strip().endswith("slicer.util.errorDisplay(str(exc))")
    assert widget.index("return", widget.index("except SegQueueError")) < widget.index(
        "self.caseLabel.setText(")


# ------------------------------------------- "My submissions" (protocol 20)


def _body(classname, name):
    return ast.get_source_segment(_source(), _method(classname, name))


def test_my_submissions_is_one_folded_line_in_the_case_section():
    """Sleek: a collapsed group at the foot of the Case section, not a new top-level
    section, hidden until a protocol-20 server is logged in to."""
    build = _body("SegQueue14Widget", "_buildMySubmissions")
    assert "ctk.ctkCollapsibleGroupBox()" in build
    assert 'box.title = "My submissions"' in build
    assert "box.collapsed = True" in build and "box.setVisible(False)" in build
    assert "box.toggled.connect(self.onMySubmissionsToggled)" in build
    assert "self.mySubmissionsMoreButton.clicked.connect(self.onMoreMySubmissions)" in build
    assert ("self.refreshMySubmissionsButton.clicked.connect(self.onRefreshMySubmissions)"
            in build)
    assert '["Case", "Submitted (ET)", ""]' in build
    case = _body("SegQueue14Widget", "_buildCaseSection")
    assert "self._buildMySubmissions(layout)" in case
    setup = _body("SegQueue14Widget", "setup")
    assert "_buildMySubmissions" not in setup, "no new top-level section"


def test_each_row_has_a_single_revise_disabled_with_the_reason():
    fill = _body("SegQueue14Widget", "_fillMySubmissions")
    assert fill.count('qt.QPushButton(') == 1 and '"Revise"' in fill
    assert "button.setEnabled(enabled)" in fill and "button.setToolTip(tip)" in fill
    assert "item.setToolTip(tip)" in fill
    assert "self.onRevise(a)" in fill


def test_the_section_is_hidden_on_a_server_too_old_for_it():
    logic = _body("SegQueue14Logic", "supportsRecall")
    assert "protocol.supports_recall(self.project.protocol_version)" in logic
    assert "self.loggedIn" in logic
    shown = _body("SegQueue14Widget", "_updateMySubmissionsVisible")
    assert "self.logic.supportsRecall()" in shown
    assert "self.mySubmissionsBox.setVisible(shown)" in shown
    for name in ("onLogin", "onLogout", "onSubmit", "onRelease"):
        assert "self._updateMySubmissionsVisible()" in _body("SegQueue14Widget", name), name
    # The list is never asked of a server that does not have it.
    assert "if not self.supportsRecall():" in _body("SegQueue14Logic", "mySubmissions")
    assert "not self.logic.supportsRecall()" in _body("SegQueue14Widget",
                                                       "_loadMySubmissions")
    import sys

    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.append(src)
    from segqueue14 import protocol

    assert not protocol.supports_recall(19) and protocol.supports_recall(20)


def test_revise_opens_the_case_from_the_read_and_shows_refusals_cleanly():
    revise = _body("SegQueue14Widget", "onRevise")
    assert "assignment = self.logic.recall(assignmentId)" in revise
    handler = revise[revise.index("except SegQueueError as exc:"):]
    assert handler.index("slicer.util.errorDisplay(str(exc))") < handler.index("return")
    assert "self.onRefreshMySubmissions()" in handler.split("return", 1)[0]
    # Opened through the ordinary path, which opens a reopened case from the
    # annotator's own read (``start_from_own``).
    assert revise.index("self._openAssignment(assignment)") > revise.index("return")
    assert "start_from_own" in _body("SegQueue14Logic", "openCase")
    assert "self.client.recall(assignmentId)" in _body("SegQueue14Logic", "recall")


def test_releasing_a_recalled_case_says_the_read_goes_back():
    release = _body("SegQueue14Widget", "onRelease")
    assert 'getattr(self.logic.assignment, "recalled", False)' in release
    # The confirmation is the one for the open case, from _releaseWording.
    assert "question = _releaseWording(self.logic.assignment)[2]" in release
    assert "question.format(self.logic.assignment.case_name)" in release
    # The action is unchanged: an ordinary release, which the server turns into
    # putting the submitted read back for a recalled case (#344).
    assert 'self.logic.release(reason="released by annotator")' in release


# ---------------------------- the release button on a recalled case (0.22.1)


def _release_namespace():
    node = next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == "_releaseWording")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(MODULE), "exec"),
         namespace)
    method = _method("SegQueue14Widget", "_updateReleaseButton")
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(MODULE), "exec"),
         namespace)
    return namespace


class _Button:
    def __init__(self):
        self.text, self.tip = None, None

    def setText(self, text):
        self.text = text

    def setToolTip(self, tip):
        self.tip = tip


class _Logic:
    def __init__(self, assignment=None):
        self.assignment = assignment


class _Widget:
    def __init__(self, logic):
        self.logic = logic
        self.releaseButton = _Button()


def _assignment(**fields):
    class A:
        case_name = "imagecas_0007"

    a = A()
    a.__dict__.update(fields)
    return a


def test_a_recalled_case_reads_discard_changes_and_close():
    wording = _release_namespace()["_releaseWording"]
    text, tip, question = wording(_assignment(recalled=True))
    assert text == "Discard changes and close"
    assert question.format("imagecas_0007") == (
        "Discard your changes to 'imagecas_0007'?\n\nYour submission goes back for "
        "review exactly as you submitted it.")
    assert "goes back for review exactly as you submitted it" in tip
    assert "pool" not in tip and "pool" not in question


@pytest.mark.parametrize("assignment", [
    None, _assignment(), _assignment(recalled=False), _assignment(recalled=None)])
def test_every_other_case_reads_give_this_case_back(assignment):
    text, tip, question = _release_namespace()["_releaseWording"](assignment)
    assert text == "Give this case back"
    assert tip == ("Returns the case to the pool for someone else. Your work on it "
                   "is discarded.")
    assert question.format("imagecas_0007") == (
        "Give 'imagecas_0007' back to the pool?\n\nAnything you have segmented on "
        "it will be discarded.")


def test_the_label_follows_the_open_case_through_recall_resubmit_and_close():
    update = _release_namespace()["_updateReleaseButton"]
    logic = _Logic()
    widget = _Widget(logic)
    seen = []
    for assignment in (None,                        # logged in, nothing open
                       _assignment(recalled=True),  # Revise
                       None,                        # resubmitted / discarded
                       _assignment(),               # an ordinary next case
                       _assignment(recalled=True),  # Revise again
                       None):                       # closed / logged out
        logic.assignment = assignment
        update(widget)
        seen.append(widget.releaseButton.text)
    assert seen == ["Give this case back", "Discard changes and close",
                    "Give this case back", "Give this case back",
                    "Discard changes and close", "Give this case back"]
    assert widget.releaseButton.tip.startswith("Returns the case to the pool")
    # Logged out entirely: no logic at all.
    widget.logic = None
    update(widget)
    assert widget.releaseButton.text == "Give this case back"


def test_every_change_of_the_open_case_relabels_the_button():
    assert "self._updateReleaseButton()" in _body("SegQueue14Widget", "_updateEnabled")
    for name in ("onLogout", "onSubmit", "onRelease", "_openAssignment"):
        assert "self._updateEnabled()" in _body("SegQueue14Widget", name), name
    # Revise opens through _openAssignment.
    assert "self._openAssignment(assignment)" in _body("SegQueue14Widget", "onRevise")
    build = _body("SegQueue14Widget", "_buildSubmitSection")
    assert "self.releaseButton = qt.QPushButton(releaseText)" in build
    assert "_releaseWording(None)" in build


def test_the_labels_are_written_in_one_place():
    """Neither label, nor the old recalled-case question, is a string anywhere but
    ``_releaseWording`` (docstrings aside)."""
    tree = _tree()
    wording = next(n for n in tree.body
                   if isinstance(n, ast.FunctionDef) and n.name == "_releaseWording")
    inside = {id(n) for n in ast.walk(wording)}
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module))
                  and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant)}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in inside and id(node) not in docstrings):
            for text in ("Give this case back", "Discard changes and close",
                         "Stop revising"):
                assert text not in node.value, (text, node.lineno)


def _sub(**kw):
    import sys

    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.append(src)
    from segqueue14 import protocol

    row = dict(assignment_id="a", case_id="c", case_name="imagecas_0007",
               state="submitted", submitted_at=None, can_recall=True)
    row.update(kw)
    return protocol.MySubmission(**row)


def test_rows_show_the_case_the_eastern_time_and_why_not():
    rows = _listing_namespace()["_mySubmissionRows"]([
        # 2026-11-10 19:32 UTC is 14:32 EST.
        _sub(submitted_at=1794339120.0),
        _sub(case_name="", case_id="c9", can_recall=False,
             reason="A reviewer is looking at this case now. Try again once they "
                    "have finished."),
        _sub(can_recall=False, reason=""),
    ])
    assert rows[0] == ("imagecas_0007", "2026-11-10 14:32 ET", True,
                       "Take this case back and open it from what you submitted.")
    assert rows[1][0] == "c9" and rows[1][1] == "--" and rows[1][2] is False
    assert rows[1][3].startswith("A reviewer is looking at this case now")
    assert rows[2][2] is False and rows[2][3] == "This case can't be revised now."
    assert _listing_namespace()["_mySubmissionRows"]([]) == []


# ------------------------------------- search and defect cases (protocol 21)


def test_the_search_box_and_defect_only_sit_above_the_case_list():
    """Sleek, like "My submissions": one quiet line under the state filter, the
    defect toggle hidden until a protocol-21 server."""
    build = _body("SegQueue14Widget", "_buildReviewSection")
    assert 'self.reviewSearch.setPlaceholderText("Search cases by name")' in build
    assert "self.reviewSearch.setClearButtonEnabled(True)" in build
    assert "self.reviewSearch.textChanged.connect(" in build
    assert 'self.defectOnlyCheck = qt.QCheckBox("Defect only")' in build
    assert "self.defectOnlyCheck.setVisible(False)" in build
    assert "self.defectButton.setVisible(False)" in build
    assert "self.defectButton.clicked.connect(self.onToggleDefect)" in build
    # Above the table, below the state filter.
    assert (build.index("self.reviewFilter = qt.QComboBox()")
            < build.index("self.reviewSearch = qt.QLineEdit()")
            < build.index("self.reviewTable = qt.QTableWidget()")
            < build.index("self.defectButton = _link("))


def test_the_search_keeps_the_order_and_hides_rather_than_removes():
    refresh = _body("SegQueue14Widget", "onRefreshReview")
    assert "_reviewListing(" in refresh and "self._applyReviewSearch()" in refresh
    apply = _body("SegQueue14Widget", "_applyReviewSearch")
    assert "self.reviewTable.setRowHidden(index, not shown)" in apply
    assert "_reviewRowShown(case, query, defectOnly)" in apply
    assert "setRowCount" not in apply and "sort" not in apply
    assert "_newestFirst(rows)" in ast.get_source_segment(
        _source(), next(n for n in _tree().body
                        if isinstance(n, ast.FunctionDef) and n.name == "_reviewListing"))


def test_rows_match_by_case_insensitive_substring_and_defect_only():
    shown = _listing_namespace()["_reviewRowShown"]
    case = {"caseName": "imagecas_0042", "defect": False}
    assert shown(case, "") and shown(case, "  CAS_004 ") and shown(case, "0042")
    assert not shown(case, "0043") and not shown(case, "", defectOnly=True)
    assert shown(dict(case, defect=True), "42", defectOnly=True)
    assert not shown(dict(case, defect=True), "43", defectOnly=True)
    assert shown({}, "") and not shown({}, "x")


def test_the_badge_is_on_the_state_cell_with_who_when_and_why():
    refresh = _body("SegQueue14Widget", "onRefreshReview")
    assert 'state = "Defect \\u00b7 " + state' in refresh
    assert "if defect and column == 2:" in refresh
    assert "qt.QColor(DEFECT_BADGE_BACKGROUND)" in refresh
    assert "_defectTooltip(case)" in refresh
    tip = _listing_namespace()["_defectTooltip"]({
        "defect": True, "defectBy": "revy", "defectReason": "motion artefact",
        # 2026-11-10 19:32 UTC is 14:32 EST.
        "defectAt": "2026-11-10T19:32:00+00:00"})
    assert tip == ("Defect: marked by revy on 2026-11-10 14:32 ET: motion artefact. "
                   "Not given to anyone new until it is unmarked.")
    assert _listing_namespace()["_defectTooltip"]({"defect": True}).startswith(
        "Defect: marked by a reviewer on --. Not given")


def test_the_confirmation_says_how_many_hold_the_case():
    ns = _listing_namespace()
    holders, prompt = ns["_defectHolders"], ns["_defectPrompt"]
    case = {"caseName": "c", "assignments": [
        {"state": "assigned"}, {"state": "downloaded"}, {"state": "rejected"},
        {"state": "submitted"}, {"state": "approved"}, {"state": "released"}, None]}
    assert holders(case) == 3
    assert holders(dict(case, holders=1)) == 1, "the server's count when it sent one"
    assert holders({}) == 0
    assert "2 annotators hold it now. They keep it and can finish it." in prompt("c", 2)
    assert "1 annotator holds it now." in prompt("c", 1)
    assert "Nobody holds it now." in prompt("c", 0)
    text = prompt("imagecas_0042", 0)
    assert text.startswith("Mark 'imagecas_0042' defect?")
    assert "not given to any annotator until it is unmarked" in text
    assert text.endswith("Reason (optional):")


def test_mark_and_unmark_ask_first_and_show_refusals_cleanly():
    toggle = _body("SegQueue14Widget", "onToggleDefect")
    assert "not self.logic.supportsDefect()" in toggle
    assert "slicer.util.confirmYesNoDisplay(" in toggle, "unmarking asks"
    assert "self._askDefectReason(case)" in toggle, "marking asks, with a reason"
    assert "self.logic.client.unmarkDefect(case[\"caseId\"])" in toggle
    assert "self.logic.client.markDefect(case[\"caseId\"], reason)" in toggle
    handler = toggle[toggle.index("except SegQueueError as exc:"):]
    assert handler.index("slicer.util.errorDisplay(str(exc))") < handler.index("return")
    assert toggle.index("self.onRefreshReview()") > toggle.index("except SegQueueError")
    dialog = _body("SegQueue14Widget", "_defectDialog")
    assert "_defectPrompt(" in dialog and "_defectHolders(case)" in dialog
    assert 'dialog.setOkButtonText("Mark defect")' in dialog
    ask = _body("SegQueue14Widget", "_askDefectReason")
    assert "self._defectDialog(case)" in ask and "qt.QDialog.Accepted" in ask


def test_the_defect_controls_are_hidden_on_a_server_too_old_for_them():
    logic = _body("SegQueue14Logic", "supportsDefect")
    assert "protocol.supports_defect(self.project.protocol_version)" in logic
    assert "self.loggedIn" in logic
    controls = _body("SegQueue14Widget", "_updateDefectControls")
    assert "self.logic.supportsDefect()" in controls
    assert "self.defectOnlyCheck.setVisible(supported)" in controls
    assert "self.defectButton.setVisible(supported)" in controls
    assert "self.defectOnlyCheck.setChecked(False)" in controls
    assert 'case.get("benchmark")' in controls, "the benchmark's button is disabled"
    for name in ("onLogin", "onLogout"):
        assert "self._updateDefectControls()" in _body("SegQueue14Widget", name), name
    assert "self._updateDefectControls()" in _body("SegQueue14Widget",
                                                    "_updateReviewEnabled")


# ------------------------------------- the annotator's note, for the reviewer (0.24.0)


def test_opening_a_submission_shows_its_annotators_note_in_case_notes():
    """The note travels in the reviewer row as ``annotatorNote`` (the server's
    ``_row``, which the history the panel opens from is made of); opening the
    submission puts it in the Case notes box, labelled as the annotator's."""
    opened = _body("SegQueue14Widget", "onOpenReview")
    assert 'self._showAnnotatorNote(entry.get("annotatorNote"))' in opened
    assert opened.index("self._claimedSubmission = submissionId") < opened.index(
        "self._showAnnotatorNote(")
    show = _body("SegQueue14Widget", "_showAnnotatorNote")
    assert '"Annotator\'s note: " + note' in show
    case = _body("SegQueue14Widget", "_buildCaseSection")
    assert "notesLayout.addWidget(self.annotatorNoteLabel)" in case
    assert case.index("self.notesBox = qt.QGroupBox(\"Case notes\")") < case.index(
        "notesLayout.addWidget(self.annotatorNoteLabel)") < case.index(
        "notesLayout.addWidget(self.notesBrowser)"), "in Case notes, above the thread"
    enabled = _body("SegQueue14Widget", "_updateEnabled")
    assert "self.notesBox.setEnabled(hasCase or reviewing)" in enabled
    assert "self.noteInput.setEnabled(hasCase)" in enabled
    assert "self.postNoteButton.setEnabled(hasCase)" in enabled
    assert ("self.annotatorNoteLabel.setVisible(reviewing and bool(self._reviewNote))"
            in enabled), "hidden again once nothing is under review"


def test_the_note_is_shown_alongside_the_thread_not_instead_of_it():
    show = _body("SegQueue14Widget", "_showAnnotatorNote")
    assert "notesBrowser" not in show and "_renderNotes" not in show
    render = _body("SegQueue14Widget", "_renderNotes")
    assert "annotatorNote" not in render and "_reviewNote" not in render


def _show_note(note, claimed="sub1"):
    """Run ``_showAnnotatorNote`` with a stand-in label: what the panel shows."""

    class Label:
        text, visible = None, None

        def setText(self, text):
            self.text = text

        def setVisible(self, on):
            self.visible = on

    namespace = {}
    exec(compile(ast.Module(body=[_method("SegQueue14Widget", "_showAnnotatorNote")],
                            type_ignores=[]), str(MODULE), "exec"), namespace)

    class Widget:
        pass

    widget = Widget()
    widget.annotatorNoteLabel = Label()
    widget._claimedSubmission = claimed
    namespace["_showAnnotatorNote"](widget, note)
    return widget


def test_the_note_is_labelled_as_the_annotators():
    widget = _show_note("distal RCA poorly opacified")
    assert widget.annotatorNoteLabel.text == "Annotator's note: distal RCA poorly opacified"
    assert widget.annotatorNoteLabel.visible is True
    assert widget._reviewNote == "distal RCA poorly opacified"


@pytest.mark.parametrize("note", ["", None, "   \n ", 42])
def test_nothing_extra_appears_without_a_note(note):
    widget = _show_note(note)
    assert widget.annotatorNoteLabel.visible is False
    assert widget.annotatorNoteLabel.text == ""
    assert widget._reviewNote == ""


def test_the_note_is_shown_as_plain_text():
    """Untrusted text from the annotator: a plain-text label, never rich text, and
    the note's characters are passed through as they are, not built into HTML."""
    case = _body("SegQueue14Widget", "_buildCaseSection")
    assert "self.annotatorNoteLabel.setTextFormat(qt.Qt.PlainText)" in case
    assert "setOpenExternalLinks" not in case.split("self.annotatorNoteLabel = ")[1].split(
        "notesLayout.addWidget(self.annotatorNoteLabel)")[0]
    markup = "<b>bold</b> <a href='http://x'>link</a> <img src=x>"
    widget = _show_note(markup)
    assert widget.annotatorNoteLabel.text == "Annotator's note: " + markup
    show = _body("SegQueue14Widget", "_showAnnotatorNote")
    assert "setHtml" not in show and "<" not in show.split('"""')[-1]


def test_the_reviewer_rows_already_carry_the_note():
    """Client-only change: the server's reviewer row has had ``annotatorNote`` all
    along, and the queue, the submission, the claim and the case history all use it."""
    review = (REPO / "server" / "girder_segqueue14" / "rest" / "review.py").read_text(
        encoding="utf-8")
    row = review.split("    def _row(self, assignment, submission):", 1)[1].split(
        "\n    def ", 1)[0]
    assert "'annotatorNote': submission.get('annotatorNote', '')" in row
    for route in ("def reviewQueue", "def getSubmission", "def claim(",
                  "def caseSubmissions"):
        body = review.split(route, 1)[1].split("\n    @access", 1)[0]
        assert "self._row(" in body, route


# --------------------------------- the extended-classes row, without the paragraph


def test_the_extended_row_has_no_paragraph_of_instructions_and_keeps_its_controls():
    build = _body("SegQueue14Widget", "_buildExtendedRow")
    code = build.split('"""', 2)[2]
    assert "EXTENDED_INSTRUCTIONS" not in code
    assert "extendedHelp" not in _source()
    # The controls are all still there, and wired.
    # The label reads without "(optional)" (the lead, via the PM).
    assert 'self.extendedCheck = qt.QCheckBox("Extended classes")' in code
    assert "(optional)" not in code
    assert "self.extendedCheck.setToolTip(" in code
    assert "self.extendedCheck.toggled.connect(self.onToggleExtended)" in code
    assert "self.extendedModeLabel = qt.QLabel(labels.EXTENDED_MODE_NOTE)" in code
    assert 'qt.QLabel("Show:")' in code and 'qt.QLabel("Complete:")' in code
    assert "self.groupChecks[group] = check" in code
    assert "self.completeChecks[group] = check" in code
    assert "self.logic.setGroupVisible(group, on)" in code
    assert "self.onToggleComplete(group, on)" in code
    assert "layout.addWidget(self.extendedBox)" in code


# ------------------------------------------- the case thread, for the reviewer (0.24.1)


class _NotesLogic:
    """``SegQueue14Logic`` as ``onRefreshNotes`` sees it: who asked for which thread."""

    def __init__(self, assignment=None, fail=None):
        self.assignment = assignment
        self.fail = fail
        self.asked = []

    def caseNotes(self, limit=None):
        self.asked.append(("own", self.assignment.case_id))
        return ["own note"]

    def caseNotesFor(self, caseId, limit=None):
        self.asked.append(("review", caseId))
        if self.fail is not None:
            raise self.fail
        return ["posted by the annotator"]


class _NotesError(Exception):
    pass


def _notes_widget(logic, claimed=None, caseId=""):
    """Run the notes methods on a stand-in widget: what they fetch and render."""
    errors = []

    class Util:
        @staticmethod
        def errorDisplay(text):
            errors.append(text)

    class Slicer:
        util = Util

    namespace = {"SegQueueError": _NotesError, "slicer": Slicer, "traceback": None}
    for name in ("onRefreshNotes", "onNotesTimer", "_endReview"):
        exec(compile(ast.Module(body=[_method("SegQueue14Widget", name)], type_ignores=[]),
                     str(MODULE), "exec"), namespace)

    class Widget:
        pass

    widget = Widget()
    widget.logic = logic
    widget._claimedSubmission = claimed
    widget._reviewCaseId = caseId
    widget.rendered = []
    widget.errors = errors
    widget._renderNotes = widget.rendered.append
    for name in ("onRefreshNotes", "onNotesTimer", "_endReview"):
        setattr(widget, name, namespace[name].__get__(widget))
    return widget


def test_the_reviewed_case_s_thread_is_fetched_while_reviewing():
    logic = _NotesLogic()
    widget = _notes_widget(logic, claimed="sub1", caseId="case7")
    widget.onRefreshNotes()
    assert logic.asked == [("review", "case7")]
    assert widget.rendered == [["posted by the annotator"]]


def test_the_timer_refreshes_the_reviewed_case_s_thread():
    logic = _NotesLogic()
    widget = _notes_widget(logic, claimed="sub1", caseId="case7")
    widget.onNotesTimer()
    assert logic.asked == [("review", "case7")]


def test_with_nothing_open_no_thread_is_fetched_and_it_stays_empty():
    logic = _NotesLogic()
    widget = _notes_widget(logic)
    widget.onNotesTimer()
    assert logic.asked == [] and widget.rendered == []
    widget.onRefreshNotes()
    assert logic.asked == [] and widget.rendered == [[]]
    # A stale case id without an open submission is not a review either.
    widget = _notes_widget(logic, claimed=None, caseId="case7")
    widget.onRefreshNotes()
    assert logic.asked == [] and widget.rendered == [[]]


def test_one_s_own_case_still_shows_its_own_thread():
    class Assignment:
        case_id = "own1"

    logic = _NotesLogic(assignment=Assignment())
    widget = _notes_widget(logic)
    widget.onNotesTimer()
    assert logic.asked == [("own", "own1")]


@pytest.mark.parametrize("fail", [_NotesError("403 not_an_annotator"), RuntimeError("down")])
def test_a_failed_fetch_while_reviewing_is_quiet_on_the_timer(fail):
    logic = _NotesLogic(fail=fail)
    widget = _notes_widget(logic, claimed="sub1", caseId="case7")
    widget.onNotesTimer()
    widget.onRefreshNotes(quiet=True)
    assert widget.errors == [] and widget.rendered == []


def test_ending_the_review_forgets_the_case_and_empties_the_thread():
    logic = _NotesLogic()
    widget = _notes_widget(logic, claimed="sub1", caseId="case7")
    widget._endReview()
    assert widget._claimedSubmission is None and widget._reviewCaseId == ""
    assert widget.rendered == [[]]
    widget.onNotesTimer()
    assert logic.asked == []


def test_every_way_out_of_a_review_goes_through_end_review():
    """Verdict, revise, return, compare, view a case, own case, logout: none of them
    may clear ``_claimedSubmission`` and leave the reviewed thread on screen."""
    cls = next(c for c in _classes() if c.name == "SegQueue14Widget")
    for fn in cls.body:
        if not isinstance(fn, ast.FunctionDef) or fn.name in ("__init__", "_endReview"):
            continue
        body = ast.get_source_segment(_source(), fn)
        assert "self._claimedSubmission = None" not in body, fn.name
    for name in ("onReviseSubmission", "onReturnToPool", "onVerdict", "onLogout"):
        assert "self._endReview()" in _body("SegQueue14Widget", name), name


def test_opening_a_submission_keeps_its_case_and_shows_its_thread():
    opened = _body("SegQueue14Widget", "onOpenReview")
    assert 'self._reviewCaseId = str(entry.get("caseId") or "")' in opened
    claim = opened.index("self._claimedSubmission = submissionId")
    assert claim < opened.index("self._reviewCaseId = ") < opened.rindex(
        "self.onRefreshNotes()")
    # The row it is read from carries the case id.
    review = (REPO / "server" / "girder_segqueue14" / "rest" / "review.py").read_text(
        encoding="utf-8")
    row = review.split("    def _row(self, assignment, submission):", 1)[1].split(
        "\n    def ", 1)[0]
    assert "'caseId': str(submission['caseId'])" in row


def test_the_reviewer_s_compose_row_stays_disabled():
    enabled = _body("SegQueue14Widget", "_updateEnabled")
    assert "self.noteInput.setEnabled(hasCase)" in enabled
    assert "self.postNoteButton.setEnabled(hasCase)" in enabled
    post = _body("SegQueue14Widget", "onPostNote")
    assert "if self.logic is None or self.logic.assignment is None:" in post
    assert "_reviewCaseId" not in post and "caseNotesFor" not in post


def test_the_logic_reads_any_case_s_thread_but_only_when_logged_in():
    namespace = {}
    exec(compile(ast.Module(body=[_method("SegQueue14Logic", "caseNotesFor")],
                            type_ignores=[]), str(MODULE), "exec"), namespace)
    calls = []

    class Client:
        def caseNotes(self, caseId, limit=None):
            calls.append((caseId, limit))
            return ["n"]

    class Logic:
        loggedIn = True
        client = Client()

    logic = Logic()
    assert namespace["caseNotesFor"](logic, "case7") == ["n"]
    assert calls == [("case7", None)]
    assert namespace["caseNotesFor"](logic, "") == []
    logic.loggedIn = False
    assert namespace["caseNotesFor"](logic, "case7") == []
    assert calls == [("case7", None)]


def test_the_reviewer_s_fetch_is_by_case_id_only_and_never_filtered():
    """The lead's rule: the whole thread for the case -- every annotator's notes,
    system notes and the auto screener's. Fetched by the reviewed case's id alone,
    and nothing on the client drops a note by annotator, author or ``system``."""
    logic_fetch = _body("SegQueue14Logic", "caseNotesFor")
    assert "self.client.caseNotes(caseId, limit=limit)" in logic_fetch
    refresh = _body("SegQueue14Widget", "onRefreshNotes")
    assert "self.logic.caseNotesFor(caseId)" in refresh
    opened = _body("SegQueue14Widget", "onOpenReview")
    assert 'self._reviewCaseId = str(entry.get("caseId") or "")' in opened
    for name, body in (("caseNotesFor", logic_fetch), ("onRefreshNotes", refresh),
                       ("_renderNotes", _body("SegQueue14Widget", "_renderNotes"))):
        code = body.split('"""')[-1]
        for word in ("annotator", "author_id", "authorId", "userId",
                     "filter(", "for n in notes if", "for note in notes if"):
            assert word not in code, (name, word)
    # ``system`` only colours a note in the renderer; every note is drawn.
    render = _body("SegQueue14Widget", "_renderNotes")
    assert "for note in notes:" in render and "continue" not in render
    # Run it: notes from two annotators, a system note and the auto screener all
    # reach the renderer, in the server's order.
    thread = [{"author": "anna"}, {"author": "SegQueue14", "system": True},
              {"author": "bobby"}, {"author": "auto screener", "system": True}]
    logic = _NotesLogic()
    logic.caseNotesFor = lambda caseId, limit=None: (logic.asked.append(caseId), thread)[1]
    widget = _notes_widget(logic, claimed="sub1", caseId="case7")
    widget.onRefreshNotes()
    assert logic.asked == ["case7"] and widget.rendered == [thread]


# ------------------------------------------- D51: inverse cut, seeded extended classes

LIB = REPO / "slicer" / "SegQueue14" / "SegQueue14Lib"
EFFECT = LIB / "SegmentEditorInverseCutEffect.py"
ICON = REPO / "slicer" / "SegQueue14" / "Resources" / "Icons" / "InverseCut.png"


def _inversecut():
    import importlib.util

    spec = importlib.util.spec_from_file_location("inversecut_d51", LIB / "inversecut.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extendedview():
    import importlib.util

    spec = importlib.util.spec_from_file_location("extendedview_d53", LIB / "extendedview.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _surfaces():
    import importlib.util

    spec = importlib.util.spec_from_file_location("surfaces_d51", LIB / "surfaces.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _effect_tree():
    return ast.parse(EFFECT.read_text(encoding="utf-8"))


def test_inverse_cut_is_registered_when_the_module_loads_and_before_the_editor():
    source = _source()
    assert 'INVERSE_CUT_EFFECT_NAME = "Inverse cut"' in source
    assert '"SegQueue14Lib", "SegmentEditorInverseCutEffect.py"' in source
    register = next(n for n in _tree().body if isinstance(n, ast.FunctionDef)
                    and n.name == "registerInverseCutEffect")
    body = ast.get_source_segment(source, register)
    # Slicer's scripted-effect pattern, registered once.
    assert "qSlicerSegmentEditorScriptedEffect(None)" in body
    assert "setPythonSource(" in body and ".self().register()" in body
    assert "registeredEffects()" in body
    module = next(c for c in _classes() if c.name == "SegQueue14")
    init = ast.get_source_segment(source, next(
        n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"))
    assert '"startupCompleted()", registerInverseCutEffect' in init
    # In the panel the embedded editor lists the effects registered when it is
    # built, so the effect is registered first.
    editor = ast.get_source_segment(source, _method("SegQueue14Widget", "_buildEditorSection"))
    assert editor.index("registerInverseCutEffect()") < editor.index(
        "qMRMLSegmentEditorWidget()")


def test_the_effect_is_a_scripted_segment_editor_effect_with_its_own_icon():
    tree = _effect_tree()
    source = EFFECT.read_text(encoding="utf-8")
    # setPythonSource looks for the class named after the file.
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
               and n.name == EFFECT.stem)
    assert [b.id for b in cls.bases] == ["AbstractScriptedSegmentEditorEffect"]
    methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    assert {"clone", "icon", "helpText", "setupOptionsFrame",
            "processInteractionEvents", "apply", "deactivate"} <= methods
    assert 'EFFECT_NAME = "Inverse cut"' in source
    assert "scriptedEffect.name = EFFECT_NAME" in source
    assert '"Resources", "Icons", "InverseCut.png"' in source
    help_text = next(n for n in tree.body if isinstance(n, ast.Assign)
                     and getattr(n.targets[0], "id", "") == "HELP_TEXT")
    text = ast.literal_eval(help_text.value)
    assert text.startswith("Inverse cut:") and "\n" not in text
    assert ICON.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_the_effect_changes_only_the_selected_segment_in_one_undo_step():
    tree = _effect_tree()
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == EFFECT.stem)
    apply = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "apply")
    body = ast.get_source_segment(EFFECT.read_text(encoding="utf-8"), apply)
    # The helpers are refused, the voxels come from inversecut, one undo state is
    # saved before the one write, and the write is the selected segment's --
    # through the editor, as Slicer's effects write (0.25.2): slicer.util's
    # updateSegmentBinaryLabelmapFromArray drops every segment's closed surface,
    # which blanked the 3D view until Show in 3D.
    assert "HELPER_NAMES" in body and "inversecut.inverse_cut(" in body
    assert body.count("saveStateForUndo()") == 1
    assert "updateSegmentBinaryLabelmapFromArray(" not in body
    assert body.count("modifySelectedSegmentByLabelmap(") == 1
    assert body.index("saveStateForUndo()") < body.index(
        "modifySelectedSegmentByLabelmap(")
    assert "_labelmapOnGrid(result, volumeNode, segmentationNode)" in body
    write = body[body.index("modifySelectedSegmentByLabelmap("):]
    write = write[:write.index(")\n")]
    # Set, not Add: the class becomes the result. Masking bypassed: the editor's
    # overwrite mode must not reach the other (overlapping) classes or the helpers.
    assert "ModificationModeSet" in write and write.rstrip().endswith("True")
    assert "SEED_SEGMENT_NAME" in body
    assert "SEED_SEGMENT_NAME = _protocol.SEED_SEGMENT_NAME" in EFFECT.read_text(
        encoding="utf-8")


def test_the_effect_and_its_icon_are_in_the_archive_and_the_release_check(tmp_path):
    import importlib.util
    import zipfile

    spec = importlib.util.spec_from_file_location(
        "build14_d51", REPO / "slicer" / "build-extension14.py")
    build14 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build14)
    archive, _, _ = build14.build(str(tmp_path))
    names = zipfile.ZipFile(archive).namelist()
    scripted = "SegQueue/lib/Slicer-5.8/qt-scripted-modules/"
    for path in ("SegQueue14Lib/SegmentEditorInverseCutEffect.py",
                 "SegQueue14Lib/inversecut.py", "Resources/Icons/InverseCut.png"):
        assert scripted + path in names, path
    workflow = (REPO / ".github" / "workflows" / "segqueue-release.yml").read_text()
    for path in ("SegQueue14Lib/SegmentEditorInverseCutEffect.py",
                 "SegQueue14Lib/inversecut.py", "Resources/Icons/InverseCut.png"):
        assert '"{}"'.format(path) in workflow


def test_a_lasso_is_tested_by_the_even_odd_rule():
    np = pytest.importorskip("numpy")
    ic = _inversecut()
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    got = ic.points_in_polygon([(5, 5), (11, 5), (-1, -1), (9.5, 0.5)], square)
    assert got.tolist() == [True, False, False, True]
    assert ic.simplify_polygon([(0, 0), (0, 0), (1, 1)]).shape == (0, 2)
    assert len(ic.simplify_polygon(np.random.default_rng(1).random((1000, 2)))) == 256
    # A 3D view's matrix is projective: the divide by w is applied.
    m = np.eye(4)
    m[3] = [0, 0, 0.5, 1]
    assert np.allclose(ic.project([(2, 4, 2)], m), [(1, 2)])


def _grid():
    np = pytest.importorskip("numpy")
    # [k, j, i]; display x = i, y = j: a slice view looking down k.
    return np, np.eye(4)


def test_inverse_cut_keeps_only_the_inside_through_every_slice():
    np, eye = _grid()
    ic = _inversecut()
    segment = np.zeros((4, 10, 10), np.uint8)
    segment[:, 2:8, 2:8] = 1
    inside = ic.inside_region(segment, eye, [(3.5, 3.5), (6.5, 3.5), (6.5, 6.5), (3.5, 6.5)])
    result, source = ic.inverse_cut(segment, inside, seed=np.ones_like(segment))
    assert source == "segment"
    want = np.zeros_like(segment)
    want[:, 4:7, 4:7] = 1
    assert np.array_equal(result, want)
    # Only the segment's own voxels are ever kept, never anything new.
    assert not (result & (segment == 0)).any()


def test_an_empty_segment_takes_the_seed_inside_the_region():
    np, eye = _grid()
    ic = _inversecut()
    seed = np.zeros((3, 8, 8), np.uint8)
    seed[:, 1:7, 3] = 1
    empty = np.zeros_like(seed)
    lasso = [(2, 0.5), (5, 0.5), (5, 3.5), (2, 3.5)]
    inside = ic.inside_region(seed, eye, lasso)
    result, source = ic.inverse_cut(empty, inside, seed)
    assert source == "seed"
    want = np.zeros_like(seed)
    want[:, 1:4, 3] = 1
    assert np.array_equal(result, want)
    # Nothing to cut: an empty segment and no seed, or an empty seed.
    assert ic.inverse_cut(empty, inside) == (None, None)
    assert ic.inverse_cut(empty, inside, np.zeros_like(seed)) == (None, None)
    with pytest.raises(ValueError):
        ic.inverse_cut(empty[0], inside)



def test_a_cut_that_misses_every_voxel_leaves_the_segment_alone():
    # Fail-safe (0.25.1): 0.25.0 emptied the segment when the region and the
    # segment did not overlap (a lightbox outline landed elsewhere).
    np, eye = _grid()
    ic = _inversecut()
    segment = np.zeros((4, 10, 10), np.uint8)
    segment[:, 2:5, 2:5] = 1
    beside = ic.inside_region(segment, eye, [(7, 7), (9, 7), (9, 9), (7, 9)])
    assert not beside.any()
    assert ic.inverse_cut(segment, beside) == (None, "outside")
    # The same for an empty class taking the seed: the seed outside the outline.
    empty = np.zeros_like(segment)
    assert ic.inverse_cut(empty, beside, seed=segment) == (None, "outside")
    # One voxel inside is a cut, not a refusal.
    one = np.zeros_like(segment, bool)
    one[0, 2, 2] = True
    result, source = ic.inverse_cut(segment, one)
    assert source == "segment" and int(result.sum()) == 1


def test_the_effect_refuses_a_cut_that_would_empty_the_segment():
    source = EFFECT.read_text(encoding="utf-8")
    cls = next(n for n in _effect_tree().body if isinstance(n, ast.ClassDef)
               and n.name == EFFECT.stem)
    apply = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "apply")
    body = ast.get_source_segment(source, apply)
    # Checked, with a message, before the undo state and the write.
    assert 'used == "outside"' in body and "nothing was" in body
    assert body.index('used == "outside"') < body.index("saveStateForUndo()")


def test_a_lightbox_outline_is_moved_into_its_pane():
    np = pytest.importorskip("numpy")
    ic = _inversecut()
    # Slicer put the first point (330, 250) at (18, 30) in its pane.
    lasso = [(330, 250), (360, 250), (360, 280)]
    got = ic.outline_in_pane(lasso, (330, 250), (18.0, 30.0, 1.0))
    assert np.allclose(got, [(18, 30), (48, 30), (48, 60)])
    # Outside a lightbox Slicer's XY is the event position: nothing moves.
    assert np.allclose(ic.outline_in_pane(lasso, (330, 250), (330, 250, 0)), lasso)
    # A lasso straying into the next pane stays one shape in its own.
    got = ic.outline_in_pane([(300, 10), (320, 10), (320, 30)], (300, 10), (290, 10))
    assert np.allclose(got, [(290, 10), (310, 10), (310, 30)])


def test_the_effect_converts_a_slice_outline_as_slicer_does_and_shows_its_cursor():
    source = EFFECT.read_text(encoding="utf-8")
    # Scissors' own conversion, from the first point; the outline moved with it.
    assert "vtkMRMLAbstractSliceViewDisplayableManager.ConvertDeviceToXYZ(" in source
    assert "inversecut.outline_in_pane(outline.finish()" in source
    # The icon is the cursor over the 3D view too, as for Scissors.
    assert "scriptedEffect.showEffectCursorInThreeDView = True" in source
    assert "scriptedEffect.showEffectCursorInSliceView = True" in source


def test_the_icon_is_sized_like_slicers_own_effect_icons():
    import struct

    data = ICON.read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    # The editor builds the cursor from the icon at its own size; Slicer's effects
    # use 21 x 21 (a 64-pixel grey square made a cursor three times Scissors').
    assert (width, height) == (21, 21)
    assert data[25] == 6  # RGBA: a transparent background, as Slicer's icons

def test_an_untouched_seed_copy_is_exact():
    np, _ = _grid()
    ic = _inversecut()
    seed = np.zeros((3, 4, 4), np.uint8)
    seed[1, 1:3, 1:3] = 1
    assert ic.is_untouched_copy(seed.copy() * 7, seed)
    edited = seed.copy()
    edited[1, 1, 1] = 0
    assert not ic.is_untouched_copy(edited, seed)
    assert not ic.is_untouched_copy(np.zeros_like(seed), seed)
    assert not ic.is_untouched_copy(np.zeros_like(seed), np.zeros_like(seed))
    assert not ic.is_untouched_copy(seed[:2], seed)
    assert not ic.is_untouched_copy(None, seed)


# The logic, run on numpy masks: the real methods, compiled out of the module
# with a stand-in for Slicer's segmentation node.

SEED_ID = "seed"
_D51_METHODS = (
    "extraSpecs", "hasExtendedSegments", "classSpecs", "extendedOn",
    "completeGroupsForExport", "addExtendedClasses", "seedOnFirstSelection",
    "copySegmentInto", "_saveFirstSelected", "_restoreFirstSelected",
    "_seedIdInScene", "seedMask", "isUntouchedSeedCopy", "extendedWork",
    "showExtendedIfWorked", "extendedSegmentIds", "setExtendedShown", "submitsExtended",
    "orderSegments", "copySegmentIntoEveryClass", "copySegmentIntoClasses",
    "segmentIdFor", "exportSubmission", "_classMask", "_segmentMask", "sourceGeometry",
)


class _Segment:
    def __init__(self, name, color):
        self.name, self.color, self.label = name, color, None

    def GetName(self):
        return self.name

    def SetLabelValue(self, value):
        self.label = value


class _Segmentation:
    def __init__(self, node):
        self.node, self.ids = node, []
        self.segments = {}
        #: Whether the segments have closed surfaces (shown in 3D).
        self.surfaces = False

    def ContainsRepresentation(self, name):
        return self.surfaces and name == "Closed surface"

    def AddEmptySegment(self, segmentId, name, color):
        self.ids.append(segmentId)
        self.segments[segmentId] = _Segment(name, color)
        return segmentId

    def GetSegment(self, segmentId):
        return self.segments.get(segmentId)

    def RemoveSegment(self, segmentId):
        self.ids.remove(segmentId)
        del self.segments[segmentId]
        self.node.masks.pop(segmentId, None)

    def GetNumberOfSegments(self):
        return len(self.ids)

    def GetNthSegmentID(self, i):
        return self.ids[i]

    def SetSegmentIndex(self, segmentId, position):
        self.ids.remove(segmentId)
        self.ids.insert(position, segmentId)


class _Display:
    def __init__(self):
        self.visible = {}

    def SetSegmentVisibility(self, segmentId, visible):
        self.visible[segmentId] = visible

    def GetSegmentVisibility(self, segmentId):
        return self.visible.get(segmentId, True)


class _SegNode:
    def __init__(self, shape):
        self.shape, self.masks = shape, {}
        self.segmentation, self.display = _Segmentation(self), _Display()

    def GetSegmentation(self):
        return self.segmentation

    def GetDisplayNode(self):
        return self.display

    def CreateClosedSurfaceRepresentation(self):
        self.segmentation.surfaces = True
        self.surfacesBuilt = getattr(self, "surfacesBuilt", 0) + 1


class _Volume:
    def __init__(self, shape):
        self.shape = shape

    def GetIJKToRASMatrix(self, matrix):
        pass


def _fake_slicer(np):
    class Util:
        @staticmethod
        def arrayFromSegmentBinaryLabelmap(node, segmentId, reference=None):
            mask = node.masks.get(segmentId)
            return None if mask is None else mask.copy()

        @staticmethod
        def updateSegmentBinaryLabelmapFromArray(array, node, segmentId, reference):
            node.masks[segmentId] = (np.asarray(array) != 0).astype(np.uint8)
            # As Slicer 5.8 does: the re-import drops every segment's surface.
            node.segmentation.surfaces = False

        @staticmethod
        def arrayFromVolume(volume):
            return np.zeros(volume.shape, np.int16)

    class OrientedImage:
        mask = None

    class SegmentationsLogic:
        """``vtkSlicerSegmentationsModuleLogic``: the in-place, one-segment write."""
        MODE_REPLACE = 0

        @staticmethod
        def GetSegmentBinaryLabelmapRepresentation(node, segmentId, image):
            image.mask = node.masks.get(segmentId)
            return image.mask is not None

        @staticmethod
        def SetBinaryLabelmapToSegment(image, node, segmentId, mode):
            node.masks[segmentId] = image.mask.copy()
            # As Slicer does: the other segments keep their surfaces; this one
            # gets its own if the segmentation shows surfaces.
            node.segmentWrites = getattr(node, "segmentWrites", []) + [segmentId]

    class Slicer:
        util = Util
        vtkOrientedImageData = OrientedImage
        vtkSlicerSegmentationsModuleLogic = SegmentationsLogic

    return Slicer


class _Cache:
    def __init__(self):
        self.manifest = {}

    def update(self, assignmentId, **fields):
        self.manifest.update(fields)
        return dict(self.manifest)


class _Vtk:
    class vtkMatrix4x4:
        def GetElement(self, r, c):
            return float(r == c)


class _LabelFile:
    def __init__(self):
        self.written = None

    def write_class_stack(self, path, masks, names, affine, colors=None,
                          complete_groups=None):
        self.written = dict(zip(names, (m.copy() for m in masks)))
        self.complete = complete_groups

    @staticmethod
    def ras_to_lps(matrix):
        return matrix


def _d51_logic(np, assignment=True, extended=True, seed=True, shape=(4, 6, 6)):
    """A ``SegQueue14Logic`` with the D51 methods, the four classes laid out and
    (when ``seed``) the case's seed as a helper segment, as a fresh case has them."""
    import sys

    if str(REPO / "src") not in sys.path:
        sys.path.append(str(REPO / "src"))
    from segqueue14 import labels

    cls = next(c for c in _classes() if c.name == "SegQueue14Logic")
    body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in _D51_METHODS]
    assert {n.name for n in body} == set(_D51_METHODS)
    helpers = [n for n in _tree().body if isinstance(n, ast.FunctionDef)
               and n.name in ("_segmentIdIn", "_segmentHasContent")]
    labelfile = _LabelFile()
    namespace = {"slicer": _fake_slicer(np), "vtk": _Vtk, "labels": labels,
                 "labelfile": labelfile, "inversecut": _inversecut(),
                 "surfaces": _surfaces(), "extendedview": _extendedview(),
                 "_geometryOf": lambda node: None}
    module = ast.Module(body=helpers + [ast.ClassDef(
        name="Logic", bases=[], keywords=[], body=body, decorator_list=[])],
        type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(MODULE), "exec"), namespace)
    logic = namespace["Logic"]()

    class Project:
        segments = labels.segment_specs()

    logic.project = Project()
    logic.extendedClasses, logic.caseExtendedMode = extended, False
    logic.extendedWorkOpened, logic.caseFlaggedExtended = False, False
    logic.extendedView = namespace["extendedview"].ExtendedView()
    logic.completeGroups = set()
    logic.lastAddedExtended, logic.seedCopiesBlanked = [], []
    logic.seedFirstSelected, logic.resumedDraft = set(), False
    logic.cache = _Cache()

    class Assignment:
        assignment_id = "a1"

    logic.assignment = Assignment() if assignment else None
    logic.volumeNode = _Volume(shape)
    logic.segmentationNode = node = _SegNode(shape)
    for spec in labels.segment_specs():
        node.segmentation.AddEmptySegment(spec.name, spec.name, spec.color)
    logic.seedSegmentId = None
    seedMask = np.zeros(shape, np.uint8)
    seedMask[1:3, 1:5, 2] = 1
    if seed:
        node.segmentation.AddEmptySegment(SEED_ID, "~ vessel seed (not submitted)", (1, 1, 0))
        node.masks[SEED_ID] = seedMask.copy()
        logic.seedSegmentId = SEED_ID
        logic.copySegmentIntoEveryClass(SEED_ID)  # D26: the four start as the seed
        # In place since 0.25.5, one write per class; the tests count their own.
        assert node.segmentWrites == [logic.segmentIdFor(s.name)
                                      for s in labels.segment_specs()]
        node.segmentWrites = []
    return logic, labels, labelfile, seedMask


def _select(logic, name):
    """What the panel does when a class is selected for editing (D52)."""
    return logic.seedOnFirstSelection(logic.segmentIdFor(name))


def _selectAll(logic, labels):
    """Every extended class selected once, as an annotator going through them."""
    for name in labels.EXTRA_NAMES:
        _select(logic, name)


def test_toggle_on_adds_the_17_empty_and_writes_no_seed_voxels():
    """D52 (lag report): no seed copies, no surfaces dropped or rebuilt."""
    np = pytest.importorskip("numpy")
    logic, labels, _, seed = _d51_logic(np, extended=False)
    node = logic.segmentationNode
    node.CreateClosedSurfaceRepresentation()      # Show in 3D
    assert logic.addExtendedClasses() == 17
    assert all(name not in node.masks for name in labels.EXTRA_NAMES)
    assert node.segmentation.surfaces and node.surfacesBuilt == 1
    assert getattr(node, "segmentWrites", []) == []
    assert node.segmentation.GetSegment("PDA").label == labels.ALL_LABEL_VALUES["PDA"]
    assert np.array_equal(node.masks[SEED_ID], seed)


def test_the_first_selection_of_a_branch_fills_exactly_that_class():
    np = pytest.importorskip("numpy")
    logic, labels, _, seed = _d51_logic(np)
    logic.addExtendedClasses()
    node = logic.segmentationNode
    node.CreateClosedSurfaceRepresentation()
    assert _select(logic, "D1") is True
    assert np.array_equal(node.masks["D1"], seed)
    assert [n for n in labels.EXTRA_NAMES if n in node.masks] == ["D1"]
    # One in-place write: the other surfaces are kept, none rebuilt.
    assert node.segmentWrites == ["D1"] and node.surfacesBuilt == 1
    assert node.segmentation.surfaces
    # Recorded, and in the draft's manifest.
    assert logic.seedFirstSelected == {"D1"}
    assert logic.cache.manifest["seedFirstSelected"] == ["D1"]
    assert np.array_equal(node.masks[SEED_ID], seed)


def test_a_branch_is_filled_only_the_first_time():
    np = pytest.importorskip("numpy")
    logic, _, _, seed = _d51_logic(np)
    logic.addExtendedClasses()
    node = logic.segmentationNode
    _select(logic, "D1")
    node.masks["D1"] = np.zeros_like(seed)        # emptied on purpose
    assert _select(logic, "D1") is False
    assert not node.masks["D1"].any()


def test_a_branch_already_drawn_is_left_as_it_is():
    np = pytest.importorskip("numpy")
    logic, _, _, seed = _d51_logic(np)
    logic.addExtendedClasses()
    node = logic.segmentationNode
    own = np.zeros_like(seed)
    own[0, 0, 0] = 1
    node.masks["D2"] = own.copy()
    assert _select(logic, "D2") is False
    assert np.array_equal(node.masks["D2"], own) and "D2" in logic.seedFirstSelected


def test_materials_the_four_and_the_helpers_are_never_filled_on_selection():
    np = pytest.importorskip("numpy")
    logic, labels, _, seed = _d51_logic(np)
    logic.addExtendedClasses()
    node = logic.segmentationNode
    lad = node.masks["LAD"].copy()
    for name in labels.MATERIALS + ["LAD"]:
        assert _select(logic, name) is False, name
    assert logic.seedOnFirstSelection(SEED_ID) is False
    assert logic.seedOnFirstSelection(None) is False
    assert all(name not in node.masks for name in labels.MATERIALS)
    assert np.array_equal(node.masks["LAD"], lad)
    assert logic.seedFirstSelected == set()


@pytest.mark.parametrize("assignment,seed", [(False, True), (True, False)],
                         ids=["reviewer", "seedless"])
def test_extended_classes_stay_empty_for_a_reviewer_and_on_a_seedless_case(assignment, seed):
    np = pytest.importorskip("numpy")
    logic, labels, _, _ = _d51_logic(np, assignment=assignment, seed=seed)
    assert logic.addExtendedClasses() == 17
    _selectAll(logic, labels)
    node = logic.segmentationNode
    assert all(name not in node.masks for name in labels.EXTRA_NAMES)


def test_the_branches_come_from_the_labels():
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                     "seedOnFirstSelection"))
    code = body.split('"""')[-1]
    assert "labels.PARENT" in code
    assert '"Stent"' not in code and "plaque" not in code.lower()


def test_first_selections_are_restored_from_the_draft():
    np = pytest.importorskip("numpy")
    logic, labels, _, _ = _d51_logic(np)
    logic.addExtendedClasses()
    # A fresh case: none.
    logic._restoreFirstSelected({})
    assert logic.seedFirstSelected == set()
    # A 0.25.4 draft: its own record (unknown names dropped).
    logic.resumedDraft = True
    logic._restoreFirstSelected({"seedFirstSelected": ["D1", "PDA", "Stent", "LAD"]})
    assert logic.seedFirstSelected == {"D1", "PDA"}
    assert logic.cache.manifest["seedFirstSelected"] == ["D1", "PDA"]
    # An older draft, or a reopened read: every branch in it counts as selected,
    # except those the toggle added at open.
    logic.lastAddedExtended = ["S1", "S2"]
    logic._restoreFirstSelected({})
    assert logic.seedFirstSelected == set(labels.PARENT) - {"S1", "S2"}
    assert _select(logic, "D1") is False and _select(logic, "S1") is True


def test_at_open_the_extended_classes_stay_empty_and_the_record_is_restored():
    open_case = ast.get_source_segment(_source(), _method("SegQueue14Logic", "openCase"))
    assert "fillExtendedFromSeed" not in _source() and "fromSeed" not in _source()
    assert open_case.index("self._loadOrCreateSegmentation(") < open_case.index(
        "self._restoreFirstSelected(manifest)")
    template = ast.get_source_segment(_source(), _method("SegQueue14Logic", "_applyTemplate"))
    assert "self.lastAddedExtended = []" in template
    close = ast.get_source_segment(_source(), _method("SegQueue14Logic", "closeCase"))
    assert "self.seedFirstSelected = set()" in close


def test_the_panel_fills_on_selection_and_never_at_toggle_on():
    toggle = ast.get_source_segment(_source(), _method("SegQueue14Widget", "onToggleExtended"))
    assert "self.logic.addExtendedClasses()" in toggle
    review = ast.get_source_segment(_source(), _method("SegQueue14Widget", "onOpenReview"))
    assert "self.logic.addExtendedClasses()" in review
    selected = ast.get_source_segment(_source(), _method("SegQueue14Widget",
                                                         "_onClassSelected"))
    assert "logic.seedOnFirstSelection(segmentId)" in selected
    assert "segmentationNode is logic.segmentationNode" in selected


def _edited(np, logic, labels, seed):
    """D1 trimmed, PDA grown, plaque painted, the rest as selection left them."""
    node = logic.segmentationNode
    trimmed = seed.copy()
    trimmed[1, 1, 2] = 0
    node.masks[logic.segmentIdFor("D1")] = trimmed
    grown = seed.copy()
    grown[0, 0, 0] = 1
    node.masks[logic.segmentIdFor("PDA")] = grown
    plaque = np.zeros_like(seed)
    plaque[1, 2, 2] = 1
    node.masks[logic.segmentIdFor("Calcified plaque")] = plaque
    return {name: node.masks.get(logic.segmentIdFor(name)) for name in labels.ALL_NAMES}


def test_toggle_off_only_hides_and_on_shows_them_as_they_were():
    """D53: the toggle never removes, empties, refills or re-seeds a class."""
    np = pytest.importorskip("numpy")
    logic, labels, _, seed = _d51_logic(np)
    logic.addExtendedClasses()
    _selectAll(logic, labels)
    before = _edited(np, logic, labels, seed)
    node = logic.segmentationNode
    ids = {name: logic.segmentIdFor(name) for name in labels.ALL_NAMES}
    node.display.SetSegmentVisibility(ids["D2"], False)       # hidden by its eye
    for _ in range(3):
        assert logic.setExtendedShown(False) == 17
        assert logic.setExtendedShown(False) == 17              # off twice: no loss
        assert not any(node.display.visible[ids[n]] for n in labels.EXTRA_NAMES)
        assert all(node.display.GetSegmentVisibility(ids[n]) for n in labels.NAMES
                   if ids[n] not in node.display.visible)
        logic.extendedClasses = True
        assert logic.addExtendedClasses() == 0                    # nothing re-added
        assert logic.setExtendedShown(True) == 17
        assert node.display.visible[ids["D2"]] is False           # as it was
        assert node.display.visible[ids["D1"]] is True
        # Selecting a branch again never re-seeds it.
        for name in labels.EXTRA_NAMES:
            assert _select(logic, name) is False
        after = {name: node.masks.get(ids[name]) for name in labels.ALL_NAMES}
        assert all(np.array_equal(before[n], after[n]) for n in labels.ALL_NAMES
                   if before[n] is not None)
        assert [n for n in labels.ALL_NAMES if after[n] is None] == [
            n for n in labels.ALL_NAMES if before[n] is None]
    assert [logic.segmentIdFor(n) for n in labels.ALL_NAMES] == list(ids.values())


def test_the_removal_path_and_the_kept_box_are_gone():
    assert "removeEmptyExtendedClasses" not in _source()
    assert "because you have changed them" not in _source()
    toggle = ast.get_source_segment(_source(), _method("SegQueue14Widget", "onToggleExtended"))
    assert "RemoveSegment" not in toggle and "Display(" not in toggle
    for name in ("onToggleExtended", "onSubmit", "_applyExtendedView",
                 "_applyExtendedRows", "_deselectExtended"):
        body = ast.get_source_segment(_source(), _method("SegQueue14Widget", name))
        assert "infoDisplay" not in body and "warningDisplay" not in body, name
    for name in ("setExtendedShown", "extendedWork", "showExtendedIfWorked",
                 "exportSubmission"):
        body = ast.get_source_segment(_source(), _method("SegQueue14Logic", name))
        assert "RemoveSegment" not in body, name


def test_export_is_four_classes_when_no_extended_class_holds_work():
    """D53: empty extended classes and untouched seed copies are not work."""
    np = pytest.importorskip("numpy")
    logic, labels, labelfile, seed = _d51_logic(np)
    logic.addExtendedClasses()
    _selectAll(logic, labels)                     # 14 untouched copies, 3 empty
    counts, _, _ = logic.exportSubmission("unused.seg.nrrd")
    assert list(labelfile.written) == labels.NAMES and list(counts) == labels.NAMES
    assert labelfile.complete is None             # a four-class read has no ticks
    assert logic.seedCopiesBlanked == []
    assert logic.extendedWork() == []


@pytest.mark.parametrize("toggle", [True, False])
def test_a_complete_tick_with_no_voxels_is_sent_as_21_with_the_tick(toggle):
    """D53 as amended: D47 Q3 stands -- a ticked group with no branches is work."""
    np = pytest.importorskip("numpy")
    logic, labels, labelfile, seed = _d51_logic(np)
    logic.addExtendedClasses()
    _selectAll(logic, labels)                     # nothing drawn: copies and empties
    logic.completeGroups = {labels.COMPLETE_GROUPS[1]}
    logic.extendedClasses = toggle
    logic.setExtendedShown(toggle)
    logic.exportSubmission("unused.seg.nrrd")
    assert list(labelfile.written) == labels.ALL_NAMES
    assert labelfile.complete == [labels.COMPLETE_GROUPS[1]]
    assert not any(labelfile.written[n].any() for n in labels.EXTRA_NAMES)  # D51 d


@pytest.mark.parametrize("toggle", [True, False])
def test_a_flagged_case_with_nothing_drawn_is_sent_as_21(toggle):
    """D53 as amended: D47 Q6 stands -- a flagged case is always an extended read,
    also when the toggle was turned off and when the scene lacks the 17."""
    np = pytest.importorskip("numpy")
    logic, labels, labelfile, seed = _d51_logic(np, extended=toggle)
    logic.caseFlaggedExtended = True
    if toggle:
        logic.addExtendedClasses()
    logic.exportSubmission("unused.seg.nrrd")
    assert list(labelfile.written) == labels.ALL_NAMES
    assert labelfile.complete == []
    assert not any(labelfile.written[n].any() for n in labels.EXTRA_NAMES)


def test_the_toggle_off_never_clears_the_case_flag():
    toggle = ast.get_source_segment(_source(), _method("SegQueue14Widget", "onToggleExtended"))
    assert "caseFlaggedExtended" not in toggle
    close = ast.get_source_segment(_source(), _method("SegQueue14Logic", "closeCase"))
    assert "self.caseFlaggedExtended = False" in close
    flags = ast.get_source_segment(_source(), _method("SegQueue14Logic", "_applyCaseFlags"))
    assert "self.caseFlaggedExtended = self.caseExtendedMode" in flags
    review = ast.get_source_segment(_source(), _method("SegQueue14Widget", "onOpenReview"))
    assert "self.logic.caseFlaggedExtended = self.logic.caseExtendedMode" in review


@pytest.mark.parametrize("toggle", [True, False])
def test_export_is_21_classes_when_one_holds_work_whatever_the_toggle(toggle):
    np = pytest.importorskip("numpy")
    logic, labels, labelfile, seed = _d51_logic(np)
    logic.addExtendedClasses()
    _selectAll(logic, labels)
    before = _edited(np, logic, labels, seed)
    logic.completeGroups = {labels.COMPLETE_GROUPS[0]}
    logic.extendedClasses = toggle
    logic.setExtendedShown(toggle)
    counts, _, _ = logic.exportSubmission("unused.seg.nrrd")
    assert list(labelfile.written) == labels.ALL_NAMES
    for name in ("D1", "PDA", "Calcified plaque"):
        assert np.array_equal(labelfile.written[name], before[name]), name
    assert labelfile.complete == [labels.COMPLETE_GROUPS[0]]          # D47 Q3
    assert len(logic.seedCopiesBlanked) == 12                         # D51 d
    assert logic.extendedWork() == [n for n in labels.EXTRA_NAMES
                                    if n in ("D1", "PDA", "Calcified plaque")]


def test_a_read_opened_with_extended_work_shows_them_and_one_without_does_not():
    np = pytest.importorskip("numpy")
    logic, labels, _, seed = _d51_logic(np, extended=False)
    assert logic.showExtendedIfWorked() is False              # no extended classes
    logic.addExtendedClasses()
    _selectAll(logic, labels)
    assert logic.showExtendedIfWorked() is False              # copies and empties
    assert not logic.extendedOn()
    _edited(np, logic, labels, seed)
    assert logic.showExtendedIfWorked() is True and logic.extendedOn()
    assert logic.extendedClasses is False                     # the login's choice kept


def test_toggle_on_never_overwrites_an_existing_class():
    np = pytest.importorskip("numpy")
    logic, labels, _, seed = _d51_logic(np)
    logic.addExtendedClasses()
    _selectAll(logic, labels)
    before = _edited(np, logic, labels, seed)
    for _ in range(3):
        assert logic.addExtendedClasses() == 0
    node = logic.segmentationNode
    assert all(np.array_equal(node.masks.get(logic.segmentIdFor(n)), before[n])
               for n in labels.ALL_NAMES if before[n] is not None)


def test_export_blanks_untouched_seed_copies_but_not_the_four():
    np = pytest.importorskip("numpy")
    logic, labels, labelfile, seed = _d51_logic(np)
    logic.addExtendedClasses()
    _selectAll(logic, labels)
    node = logic.segmentationNode
    trimmed = seed.copy()
    trimmed[1, 1, 2] = 0
    node.masks["D1"] = trimmed
    counts, _, _ = logic.exportSubmission("unused.seg.nrrd")
    written = labelfile.written
    assert list(written) == labels.ALL_NAMES
    n = int(seed.sum())
    for name in labels.NAMES:                      # D26/D38: sent as they are
        assert np.array_equal(written[name], seed) and counts[name] == n
    assert np.array_equal(written["D1"], trimmed) and counts["D1"] == n - 1
    # D52: the 13 untouched branches (each selected once, so a seed copy) are
    # blanked; the materials never were seed copies, and are written empty.
    blanked = [name for name in labels.EXTRA_NAMES
               if name != "D1" and name not in labels.MATERIALS]
    assert len(blanked) == 13
    for name in blanked + labels.MATERIALS:
        assert not written[name].any() and counts[name] == 0, name
    assert logic.seedCopiesBlanked == [n for n in labels.ALL_NAMES if n in blanked]
    # D47 Q3: the complete ticks are unchanged by it.
    assert "seedCopiesBlanked" not in ast.get_source_segment(
        _source(), _method("SegQueue14Logic", "completeGroupsForExport"))


def test_plaque_painted_inside_a_seeded_lad_is_submitted_as_plaque():
    """D52: on a seeded case the plaque starts empty, so plaque painted inside the
    LAD is sent as plaque, overlapping the LAD (D39), not blanked as a seed copy."""
    np = pytest.importorskip("numpy")
    logic, labels, labelfile, seed = _d51_logic(np)
    logic.addExtendedClasses()
    node = logic.segmentationNode
    plaque = np.zeros_like(seed)
    plaque[1, 2, 2] = 1                               # inside the seed, so the LAD
    assert seed[1, 2, 2] == 1
    node.masks["Calcified plaque"] = plaque.copy()
    counts, _, _ = logic.exportSubmission("unused.seg.nrrd")
    written = labelfile.written
    assert np.array_equal(written["Calcified plaque"], plaque)
    assert counts["Calcified plaque"] == 1
    assert (written["Calcified plaque"] & written["LAD"]).sum() == 1
    assert "Calcified plaque" not in logic.seedCopiesBlanked


def test_a_material_left_as_the_seed_by_an_older_draft_is_still_blanked():
    np = pytest.importorskip("numpy")
    logic, labels, labelfile, seed = _d51_logic(np)
    logic.addExtendedClasses()
    logic.segmentationNode.masks["Stent"] = seed.copy()    # as 0.25.0-0.25.3 seeded it
    logic.exportSubmission("unused.seg.nrrd")
    # D53: a seed copy is not work, so alone it leaves the read four classes.
    assert list(labelfile.written) == labels.NAMES
    painted = np.zeros_like(seed)
    painted[0, 0, 0] = 1
    logic.segmentationNode.masks["D1"] = painted
    logic.exportSubmission("unused.seg.nrrd")
    assert not labelfile.written["Stent"].any()
    assert "Stent" in logic.seedCopiesBlanked


def test_without_a_seed_nothing_is_blanked_or_removed_as_a_copy():
    np = pytest.importorskip("numpy")
    logic, labels, labelfile, _ = _d51_logic(np, seed=False)
    logic.addExtendedClasses()
    node = logic.segmentationNode
    painted = np.zeros(node.shape, np.uint8)
    painted[0, 0, 0] = 1
    node.masks["D2"] = painted
    logic.exportSubmission("unused.seg.nrrd")
    assert logic.seedCopiesBlanked == [] and labelfile.written["D2"].sum() == 1
    assert logic.extendedWork() == ["D2"]


def test_one_helper_decides_what_is_an_untouched_seed_copy():
    for name in ("extendedWork", "exportSubmission"):
        body = ast.get_source_segment(_source(), _method("SegQueue14Logic", name))
        assert "self.isUntouchedSeedCopy(" in body, name
        assert "is_untouched_copy" not in body, name
    helper = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                       "isUntouchedSeedCopy"))
    assert "inversecut.is_untouched_copy(mask, seed)" in helper


def test_the_module_writes_seed_copies_inside_keeping_closed_surface():
    copy = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                     "copySegmentIntoClasses"))
    guard = copy.index("with surfaces.keeping_closed_surface(self.segmentationNode)")
    assert guard < copy.index("self.copySegmentInto(")
    assert "from SegQueue14Lib import inversecut, surfaces" in _source()


# ------------------------------------------- a simpler reviewer panel (0.25.8)

def _call_named(node, attr):
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == attr]


def test_the_reviewer_panel_has_no_note_box_image_only_take_or_history_caption():
    """0.25.8: the note box, *Image only*, *Take & segment* and the caption over
    the history table are gone, and nothing still refers to them."""
    source = _source()
    for gone in ("verdictComment", "openCaseButton", "takeCaseButton",
                 "onOpenCase", "onTakeCase", "_loadCaseHelpers",
                 "optional note for the case thread", '"Image only"',
                 "Take && segment", "Every submission against the selected case"):
        assert gone not in source, gone
    widget = next(c for c in _classes() if c.name == "SegQueue14Widget")
    names = {n.name for n in widget.body if isinstance(n, ast.FunctionDef)}
    assert not names & {"onOpenCase", "onTakeCase", "_loadCaseHelpers"}
    # The open row is Open submission alone, and the captions that stay, stay.
    build = _body("SegQueue14Widget", "_buildReviewSection")
    row = build[build.index("openRow = qt.QHBoxLayout()"):
                build.index("layout.addLayout(openRow)")]
    assert row.count("openRow.addWidget(") == 1
    assert "self.openReviewButton" in row
    assert "What to do with the submission that is open." in build


def test_verdict_revise_and_pool_send_no_reviewer_note():
    """The calls still go out, with the client's own "no note" default ('')."""
    verdict = _method("SegQueue14Widget", "onVerdict")
    (call,) = _call_named(verdict, "submitVerdict")
    assert {k.arg for k in call.keywords} == {"secondsSpent"}
    assert len(call.args) == 2
    revise = _method("SegQueue14Widget", "onReviseSubmission")
    (call,) = _call_named(revise, "reviseSubmission")
    assert {k.arg for k in call.keywords} == {"seconds"}
    pool = _method("SegQueue14Widget", "onReturnToPool")
    (call,) = _call_named(pool, "returnToPool")
    assert not call.keywords and len(call.args) == 1

    client = (REPO / "slicer" / "SegQueue14" / "SegQueue14Lib" / "client.py").read_text()
    assert "def submitVerdict(self, submissionId: str, verdict: str, comment: str = ''," \
        in client
    assert "def returnToPool(self, submissionId: str, reason: str = '')" in client
    logic = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                      "reviseSubmission"))
    assert 'note=""' in logic.splitlines()[0]
