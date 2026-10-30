"""Static and packaging checks on the JanusMRead Slicer module (#156), in the style of
``test_segqueue14_module.py``: the wiring (every attribute, signal and name exists),
its separation from SegQueue14 (library, settings, routes, protocol, archive, release
tag), what a reader may and may not be shown, and the order of the checks before an
upload. ``tests/slicer_selftest_janusm.py`` runs the module inside a real Slicer.

``JanusMRead.py`` imports Qt, VTK and Slicer, so it is parsed, not imported.
"""

import ast
import importlib.util
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE_DIR = REPO / "slicer" / "JanusMRead"
MODULE = MODULE_DIR / "JanusMRead.py"
SEGQUEUE14 = REPO / "slicer" / "SegQueue14" / "SegQueue14.py"
for _lib in (MODULE_DIR, REPO / "slicer" / "SegQueue14", REPO / "src"):
    if str(_lib) not in sys.path:
        sys.path.insert(0, str(_lib))

from JanusMReadLib import halfmax, precheck, updater  # noqa: E402
from JanusMReadLib import release as jrel  # noqa: E402

from janusm_reads import labels as L  # noqa: E402
from janusm_reads import phantom  # noqa: E402

INHERITED = {"parent", "layout", "developerMode"}
SLICER = "5.8"
SCRIPTED = f"JanusMRead/lib/Slicer-{SLICER}/qt-scripted-modules/"


def _source():
    return MODULE.read_text(encoding="utf-8")


def _tree():
    return ast.parse(_source())


def _classes():
    return [n for n in ast.walk(_tree()) if isinstance(n, ast.ClassDef)]


def _method(classname, name):
    cls = next(c for c in _classes() if c.name == classname)
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(_source(), node)


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


def _code_strings():
    """Every string literal in the module that is not a docstring."""
    tree = _tree()
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docs.add(id(first.value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


# ------------------------------------------------------------------ wiring


def test_the_module_parses_on_slicers_python():
    ast.parse(_source(), feature_version=(3, 9))
    for path in (MODULE_DIR / "JanusMReadLib").glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))


@pytest.mark.parametrize("classdef", _classes(), ids=lambda c: c.name)
def test_every_self_attribute_the_class_reads_is_one_it_defines(classdef):
    defined, used = _self_attributes(classdef)
    missing = {n: ln for n, ln in used.items() if n not in defined and n not in INHERITED}
    assert not missing, f"{classdef.name} reads attributes it never defines: {missing}"


def test_the_widget_sets_its_attributes_before_the_base_class_runs_setup():
    # With no parent, ScriptedLoadableModuleWidget.__init__ calls setup() itself.
    init = _method("JanusMReadWidget", "__init__")
    assert init.index("self.plateauLabels = {}") < init.index(
        "ScriptedLoadableModuleWidget.__init__")


def test_every_widget_signal_is_connected_to_something_that_exists():
    widget = next(c for c in _classes() if c.name == "JanusMReadWidget")
    defined, _ = _self_attributes(widget)
    handlers = []
    for node in ast.walk(widget):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "connect"):
            continue
        for arg in node.args:
            for inner in ast.walk(arg):
                if (isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name)
                        and inner.value.id == "self"):
                    handlers.append((inner.attr, inner.lineno))
    assert len(handlers) >= 15
    dead = [(n, ln) for n, ln in handlers if n not in defined]
    assert not dead, f"signals wired to nothing: {dead}"


def test_every_module_level_name_it_uses_exists():
    tree = _tree()
    known = set(dir(__builtins__) if not isinstance(__builtins__, dict) else __builtins__)
    known |= {"__file__", "__doc__", "__name__"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node in tree.body:
            known.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            known |= {(a.asname or a.name).split(".")[0] for a in node.names}
        elif isinstance(node, ast.Assign) and any(node is n for n in ast.walk(tree)):
            for target in node.targets:
                known |= {s.id for s in ast.walk(target) if isinstance(s, ast.Name)}
        elif isinstance(node, ast.For) and node in tree.body:
            known |= {s.id for s in ast.walk(node.target) if isinstance(s, ast.Name)}
    for func in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Lambda))):
        local = {a.arg for a in func.args.args + func.args.kwonlyargs}
        for extra in (func.args.vararg, func.args.kwarg):
            if extra:
                local.add(extra.arg)
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                local.add(node.id)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                local.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                local |= {(a.asname or a.name).split(".")[0] for a in node.names}
            elif isinstance(node, (ast.Lambda, ast.FunctionDef)) and node is not func:
                local |= {a.arg for a in node.args.args + node.args.kwonlyargs}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                assert node.id in known or node.id in local, (
                    f"{getattr(func, 'name', 'lambda')} uses undefined {node.id!r} "
                    f"(line {node.lineno})")


# ------------------------------------------------------- not SegQueue14


def test_it_is_its_own_module_and_never_segqueue14s():
    source = _source()
    names = {c.name for c in _classes()}
    assert {"JanusMRead", "JanusMReadLogic", "JanusMReadWidget", "JanusMReadTest"} <= names
    theirs = {n.name for n in ast.walk(ast.parse(SEGQUEUE14.read_text(encoding="utf-8")))
              if isinstance(n, ast.ClassDef)}
    assert not {n for n in names & theirs if not n.startswith("_")}
    assert "from JanusMReadLib import" in source
    assert not re.search(r"^\s*(from|import) (SegQueue14Lib|SegQueueLib|segqueue14|segqueue)\b",
                         source, re.M)
    assert "/segqueue" not in source and "segqueue-v" not in source


def test_every_settings_key_is_its_own():
    keys = re.findall(r'^_SETTING_\w+ = "([^"]+)"', _source(), re.M)
    assert keys and all(k.startswith("JanusMRead/") for k in keys), keys
    assert "SegQueue14/" not in _source() and '"SegQueue/' not in _source()


def test_it_speaks_only_the_janusm_read_protocol_through_the_shared_client():
    source = _source()
    assert "from janusm_reads.client import JanusMClient" in source
    assert "from janusm_reads import PROTOCOL_NAME, PROTOCOL_VERSION, labels, protocol" in source
    # Never a route of its own: every call goes through janusm_reads.client.
    strings = " ".join(_code_strings())
    assert not re.search(r"janusm/(project|mine|next|read|admin)", strings)


def test_its_version_line_is_its_own():
    ours = re.search(r'^__version__ = "([^"]+)"', _source(), re.M).group(1)
    assert jrel.parse_version(ours) is not None
    build = _load("build_janusm_v", REPO / "slicer" / "build-extension-janusm.py")
    assert build.moduleVersion() == ours and build.TAG_PREFIX == "janusm-read-v"


# ------------------------------------------------- what a reader is shown


def test_it_never_asks_for_or_names_the_read_set_or_the_other_read():
    source = _source()
    imports = [n for n in ast.walk(_tree()) if isinstance(n, (ast.Import, ast.ImportFrom))]
    used = {(n.module or "") + "." + a.name if isinstance(n, ast.ImportFrom) else a.name
            for n in imports for a in n.names}
    for module in ("readset", "holdout", "checker", "seeds", "anchoring", "phantom"):
        assert not any(module in name for name in used), module
    names = " ".join([n.id for n in ast.walk(_tree()) if isinstance(n, ast.Name)]
                     + [n.attr for n in ast.walk(_tree()) if isinstance(n, ast.Attribute)])
    code = names + " " + " ".join(_code_strings())
    for word in ("readSet", "read_set", "readset", "scored", "ADMIN_", "admin/", "otherRead",
                 "adminCases", "adminReads"):
        assert word not in code, word
    assert "readSet" not in source and "ADMIN_" not in source
    shown = " ".join(_code_strings()).lower()
    for word in ("seal", "decision", "scored", "the other read"):
        assert word not in shown, word


def test_a_read_carries_nothing_but_what_a_reader_may_see():
    from janusm_reads import protocol

    read = protocol.ReadInfo.from_dict({"readId": "R", "caseName": "c", "state": "assigned",
                                        "hasSeed": True, "readSet": "seal", "scored": True})
    assert set(vars(read)) == {"read_id", "case_name", "state", "has_seed", "checksum",
                               "size_bytes", "check_summary", "flagged", "check_profile"}
    # Nothing that says whether the read is a third read, or what the other reader graded.
    assert not {"third", "cadrads", "lesion_points"} & set(vars(read))


# --------------------------------------------------------- the workflow


def test_the_seed_loads_into_the_four_segments_by_value_and_never_over_a_draft():
    body = _method("JanusMReadLogic", "openRead")
    assert "not self.resumedDraft and read.has_seed" in body
    assert "self.importLabels(seed)" in body
    imported = _method("JanusMReadLogic", "importLabels")
    assert "values == int(value)" in imported and "ImportLabelmapToSegmentationNode" in imported
    assert ".SetLabelValue(" not in imported
    segments = _method("JanusMReadLogic", "ensureSegments")
    assert "labels.CLASSES" in segments and "labels.COLORS" in segments


def test_the_checks_come_before_anything_is_written_or_uploaded():
    export = _method("JanusMReadLogic", "exportRead")
    assert export.index("precheck.problems(") < export.index("raise ReadRefused")
    assert export.index("raise ReadRefused") < export.index("saveNode")
    submit = _method("JanusMReadLogic", "submit")
    assert submit.index("self.exportRead(") < submit.index("self.client.submit(")


def test_a_returned_read_shows_its_reasons():
    shown = _method("JanusMReadWidget", "_showRead")
    assert "protocol.RETURNED" in shown and "read.check_summary" in shown
    assert "has_seed" in shown


def test_the_borders_and_plateaus_are_the_protocols():
    assert halfmax.BORDERS == {
        "endocardial": ("LV blood", "myocardium"),
        "epicardial": ("myocardium", "fat"),
        "septal (RV side)": ("RV blood", "myocardium"),
    }
    assert (halfmax.LV_MYO, halfmax.LV_POOL, halfmax.RV_POOL, halfmax.LA_POOL) == \
        (L.LV_MYO, L.LV_POOL, L.RV_POOL, L.LA_POOL)
    assert halfmax.FAT_WINDOW_HU == (-180.0, 0.0)


# -------------------------------------------------------------- halfmax


def test_thresholds_are_halfway_between_plateaus():
    pl = {"LV blood": 420.0, "myocardium": 120.0, "RV blood": 380.0, "fat": -100.0}
    assert halfmax.thresholds(pl) == {"endocardial": 270.0, "epicardial": 10.0,
                                      "septal (RV side)": 250.0}
    # S5 point 1: width 1.5 x |p1 - p2| (Hotel v2 section 5.4, JA21), level at the half.
    assert halfmax.BORDER_WIDTH_FACTOR == 1.5
    assert halfmax.window_for("endocardial", pl) == (450.0, 270.0)
    assert halfmax.window_for("epicardial", pl) == (330.0, 10.0)
    assert halfmax.window_for("septal (RV side)", pl) == (390.0, 250.0)
    assert halfmax.window_for("endocardial", {"LV blood": 121.0, "myocardium": 120.0}) == \
        (halfmax.MIN_BORDER_WIDTH_HU, 120.5)
    assert halfmax.warnings(pl) == []
    with pytest.raises(ValueError, match="fat"):
        halfmax.threshold("epicardial", {"myocardium": 120.0})
    assert halfmax.thresholds({"LV blood": 420.0}) == {}
    bad = halfmax.warnings({"LV blood": 100.0, "myocardium": 120.0, "fat": 40.0})
    assert len(bad) == 2 and "LV blood" in bad[0] and "fat" in bad[1]


def test_a_case_opens_on_the_border_window_and_800_300_is_only_on_request():
    """S5 point 1: the border window is the default; 800 / 300 stays available."""
    assert halfmax.DEFAULT_BORDER == "endocardial" and halfmax.FIXED_WINDOW == (800.0, 300.0)
    opened = _method("JanusMReadLogic", "openRead")
    assert "self.measurePlateausFromSegments()" in opened
    assert "self.openDefaultWindow()" in opened and "self.resetWindow()" not in opened
    assert opened.index("self.importLabels(seed)") < opened.index(
        "self.measurePlateausFromSegments()") < opened.index("self.openDefaultWindow()")
    default = _method("JanusMReadLogic", "openDefaultWindow")
    assert "halfmax.window_for(self.border, self.plateaus)" in default
    assert "CT_WINDOW, CT_LEVEL" in default            # a blank case before any ROI
    assert 'self.windowMode = "fixed"' in _method("JanusMReadLogic", "resetWindow")
    assert "openDefaultWindow" in _method("JanusMReadWidget", "onMeasureRoi")
    assert '"800 / 300"' in _source() and 'QPushButton("Reset")' not in _source()


def test_the_read_form_is_checked_before_anything_is_uploaded():
    """S5 point 6: per-vessel CAD-RADS 2.0 and an optional lesion point (JA46 (d))."""
    submit = _method("JanusMReadLogic", "submit")
    assert submit.index("protocol.read_form_problems(") < submit.index("raise ReadRefused")
    assert submit.index("raise ReadRefused") < submit.index("self.exportRead(")
    assert "cadrads=cadrads, lesion_points=points" in submit
    form = _method("JanusMReadWidget", "_buildReadFormSection")
    assert "protocol.VESSELS" in form and "protocol.CADRADS_GRADES" in form
    assert "GetNthControlPointPositionWorld" in _method("JanusMReadLogic", "readForm")
    assert "self.clearReadForm()" in _method("JanusMReadLogic", "openRead")


def test_a_returned_read_plots_its_half_maximum_profile():
    """S5 point 3: the profile plot goes with the return."""
    shown = _method("JanusMReadLogic", "showProfile")
    assert "halfmax.profile_table(" in shown and "slicer.util.plot(" in shown
    assert "showProfile" in _method("JanusMReadWidget", "onSubmit")
    assert "showProfile" in _method("JanusMReadWidget", "onRefresh")
    assert "read.flagged" in _method("JanusMReadWidget", "_showRead")
    profile = {"s_mm": [-1.0, 0.0, 1.0], "hu": [420.0, 270.0, 120.0], "thresholdHU": 270.0,
               "plateausHU": [420.0, 120.0], "offsetMm": 0.8, "failed": True}
    table = halfmax.profile_table(profile)
    assert table.shape == (3, len(halfmax.PROFILE_COLUMNS))
    assert (table[:, 2] == 270.0).all() and (table[:, 3] == 420.0).all()
    assert "0.80 mm past" in halfmax.profile_caption("endocardial", profile)
    assert "short of" in halfmax.profile_caption("endocardial", {**profile, "offsetMm": -0.6})
    with pytest.raises(ValueError):
        halfmax.profile_table({})


def test_erosion_and_dilation_are_voxel_steps():
    cube = np.zeros((9, 9, 9), bool)
    cube[2:7, 2:7, 2:7] = True
    assert halfmax.erode(cube, 1).sum() == 27
    assert halfmax.erode(cube, 3).sum() == 0
    assert halfmax.dilate(cube, 1).sum() == 125 + 6 * 25
    assert halfmax.dilate(cube, 1)[2:7, 2:7, 2:7].all()


def test_plateaus_from_the_phantoms_labels():
    truth, spacing = phantom.heart(shape=(64, 64, 64), spacing=0.75, pool_mm=9, wall_mm=6)
    ct = phantom.ct_from(truth, spacing)
    pl = halfmax.plateaus_from_labels(ct, truth, spacing)
    assert abs(pl["LV blood"] - 420) < 5 and abs(pl["myocardium"] - 120) < 10
    assert abs(pl["RV blood"] - 380) < 5 and abs(pl["fat"] + 100) < 5
    # A seed with the pool 2 mm too big still gives the plateau (the median).
    seed = phantom.move_border(truth, spacing, "endocardial", 2.0)
    assert abs(halfmax.plateaus_from_labels(ct, seed, spacing)["LV blood"] - 420) < 10
    empty = halfmax.plateaus_from_labels(ct, np.zeros_like(truth), spacing)
    assert all(v is None for v in empty.values())


def test_an_roi_box_is_clipped_to_the_volume():
    ct = np.arange(4 * 5 * 6, dtype=float).reshape(4, 5, 6)   # (k, j, i)
    box = halfmax.box_slices([(1, 1, 1), (2, 3, 2)], ct.shape)  # (i, j, k)
    assert box == (slice(1, 3), slice(1, 4), slice(1, 3))
    assert halfmax.roi_mean(ct, box) == ct[1:3, 1:4, 1:3].mean()
    assert halfmax.box_slices([(-5, -5, -5), (100, 100, 100)], ct.shape) == \
        (slice(0, 4), slice(0, 5), slice(0, 6))
    assert halfmax.box_slices([(10, 10, 10), (12, 12, 12)], ct.shape) is None
    assert halfmax.roi_mean(ct, None) is None


# ------------------------------------------------------------- precheck


def test_the_checks_before_upload():
    values = np.array([[0, 1, 2], [3, 4, 4]])
    counts = precheck.voxel_counts(values)
    assert counts == {1: 1, 2: 1, 3: 1, 4: 2}
    assert precheck.problems(np.unique(values), counts) == []
    out = precheck.problems([0, 1, 2, 7], {1: 1, 2: 1}, overlapping_voxels=3)
    assert len(out) == 3
    assert "outside 0-4 (7)" in out[0] and "3 voxels" in out[1]
    assert "RV blood pool (3)" in out[2] and "LA blood pool (4)" in out[2]


@pytest.mark.parametrize("head,suffix", [
    (b"\x1f\x8b\x08rest", ".nii.gz"), (b"NRRD0004\n", ".nrrd"),
    (b"ObjectType = Image\n", ".mha"), (b"\0" * 344 + b"n+1\0" + b"\0" * 4, ".nii")])
def test_the_ct_format_is_sniffed(tmp_path, head, suffix):
    path = tmp_path / "ct.download"
    path.write_bytes(head)
    assert precheck.sniff_suffix(str(path)) == suffix


# --------------------------------------------- packaging and release line


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    build = _load("build_janusm", REPO / "slicer" / "build-extension-janusm.py")
    archive, version, _ = build.build(str(tmp_path_factory.mktemp("dist")))
    return Path(archive), version


def test_the_archive_is_its_own_extension(built):
    archive, version = built
    assert archive.name == f"JanusMRead-{version}-Slicer-{SLICER}.zip"
    assert jrel.ASSET_PATTERN.match(archive.name)
    names = zipfile.ZipFile(archive).namelist()
    assert {n.split("/")[0] for n in names} == {"JanusMRead"}
    for member in ("JanusMRead.py", "JanusMReadLib/halfmax.py", "JanusMReadLib/updater.py",
                   "janusm_reads/client.py", "janusm_reads/protocol.py",
                   "janusm_reads/labels.py"):
        assert SCRIPTED + member in names, member
    assert f"JanusMRead/share/Slicer-{SLICER}/JanusMRead.s4ext" in names
    assert not any(n.endswith(("SegQueue14.py", "SegQueue.py")) or "segqueue" in n.lower()
                   for n in names)


def test_the_archive_carries_only_the_client_half_of_janusm_reads(built):
    archive, _ = built
    vendored = sorted(n[len(SCRIPTED + "janusm_reads/"):] for n in
                      zipfile.ZipFile(archive).namelist()
                      if n.startswith(SCRIPTED + "janusm_reads/"))
    assert vendored == ["__init__.py", "client.py", "labels.py", "protocol.py"]


def test_the_archive_imports_with_nothing_from_the_repository(built, tmp_path):
    archive, _ = built
    zipfile.ZipFile(archive).extractall(tmp_path / "x")
    path = tmp_path / "x" / SCRIPTED
    code = ("import sys; sys.path[:] = [p for p in sys.path if 'src' not in p "
            "and 'slicer' not in p]; "
            f"sys.path.insert(0, {str(path)!r}); "
            "import janusm_reads.client, janusm_reads.protocol, janusm_reads.labels; "
            "from JanusMReadLib import halfmax, precheck, release, updater; "
            "assert janusm_reads.__file__.startswith(sys.path[0]); "
            "print(janusm_reads.PROTOCOL_VERSION)")
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "1"


def _release(tag, asset):
    return {"tag_name": tag, "assets": [{"name": asset, "browser_download_url": "x/" + asset}]}


def test_segqueue14_annotators_are_never_offered_it_and_it_is_never_offered_segqueue14():
    from segqueue import release as srel

    releases = [_release("janusm-read-v9.0.0", f"JanusMRead-9.0.0-Slicer-{SLICER}.zip"),
                _release("segqueue-v9.0.0", f"SegQueue-9.0.0-Slicer-{SLICER}.zip"),
                _release("segqueue14-v9.0.0", f"SegQueue14-9.0.0-Slicer-{SLICER}.zip")]
    theirs = srel.update_available(releases, "0.14.0", slicer_version=SLICER)
    assert theirs["tag_name"] == "segqueue-v9.0.0"
    assert srel.update_available(releases[:1], "0.0.1", slicer_version=SLICER) is None
    # Even a JanusMRead zip mistakenly attached to a segqueue tag is not SegQueue's.
    assert srel.update_available([_release("segqueue-v9.0.0", "JanusMRead-9.0.0-Slicer-5.8.zip")],
                                 "0.14.0", slicer_version=SLICER) is None
    ours = jrel.update_available(releases, "0.1.0", slicer_version=SLICER)
    assert ours["tag_name"] == "janusm-read-v9.0.0"
    assert jrel.update_available(releases[1:], "0.0.1", slicer_version=SLICER) is None
    assert jrel.update_available(releases, "9.0.0", slicer_version=SLICER) is None
    assert jrel.update_available([dict(releases[0], prerelease=True)], "0.1.0") is None


def test_each_updater_refuses_the_others_archive(built, tmp_path):
    from SegQueue14Lib import updater as sq14

    archive, _ = built
    assert updater.inspectArchive(str(archive), SLICER)
    with pytest.raises(sq14.UpdateError, match="SegQueue14"):
        sq14.inspectArchive(str(archive), SLICER)
    build14 = _load("build14_janusm", REPO / "slicer" / "build-extension14.py")
    theirs, _, _ = build14.build(str(tmp_path))
    with pytest.raises(updater.UpdateError, match="JanusMRead"):
        updater.inspectArchive(theirs, SLICER)
    assert not any("janusm" in n.lower() for n in zipfile.ZipFile(theirs).namelist())


def test_it_updates_an_installed_copy_of_itself(built, tmp_path):
    archive, version = built
    root = tmp_path / "Extensions-33241"
    zipfile.ZipFile(archive).extractall(root)
    installed = root / SCRIPTED.rstrip("/")
    assert updater.packagedSlicerVersion(str(installed)) == SLICER
    later = tmp_path / f"JanusMRead-99.0.0-Slicer-{SLICER}.zip"
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(later, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            if item.filename == SCRIPTED + "JanusMRead.py":
                data = data.replace(f'__version__ = "{version}"'.encode(),
                                    b'__version__ = "99.0.0"')
            dst.writestr(item, data)
    backup = updater.installArchive(str(later), str(installed), SLICER)
    assert '__version__ = "99.0.0"' in (installed / "JanusMRead.py").read_text()
    assert f'__version__ = "{version}"' in (Path(backup) / "JanusMRead.py").read_text()
    assert not updater.canInstall(str(MODULE_DIR))[0]   # a checkout updates with git


def test_ci_builds_it_and_nothing_publishes_it():
    workflow = (REPO / ".github" / "workflows" / "janusm-read.yml").read_text()
    assert "build-extension-janusm.py" in workflow and "upload-artifact" in workflow
    assert "slicer_selftest_janusm.py" in workflow
    for word in ("gh release", "softprops", "git tag", "git push", "contents: write",
                 "janus.bradensbay.com", "segqueue-v"):
        assert word not in workflow, word
    release = (REPO / ".github" / "workflows" / "segqueue-release.yml").read_text()
    assert "janusm" not in release.lower() and "JanusMRead" not in release
