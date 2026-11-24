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
    copy = ast.get_source_segment(_source(), _method("SegQueue14Logic",
                                                     "copySegmentIntoEveryClass"))
    # Per-class array writes: one import into several targets fills only the first.
    assert "updateSegmentBinaryLabelmapFromArray" in copy
    assert "ImportLabelmapToSegmentationNode" not in copy


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
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic", "_classMask"))
    assert "np.zeros(shape, np.uint8)" in body


def test_every_class_is_exported_whole_on_the_ct_grid():
    # D39 (#275): no single label volume (one class per voxel) is written; each
    # class is read against the CT, by name, and written as its own channel.
    body = ast.get_source_segment(_source(), _method("SegQueue14Logic", "exportSubmission"))
    assert "logic().ExportSegmentsToLabelmapNode(" not in body
    assert "labelfile.write_class_stack(" in body
    mask = ast.get_source_segment(_source(), _method("SegQueue14Logic", "_classMask"))
    assert "arrayFromSegmentBinaryLabelmap(" in mask and "self.volumeNode" in mask
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


def test_the_module_is_0_24_0_and_protocol_21():
    assert re.search(r'^__version__ = "0\.24\.0"$', _source(), re.M)
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
    assert "self._claimedSubmission = None" in body
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
                            ("SegQueue14Widget", "onOpenCase"),
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
