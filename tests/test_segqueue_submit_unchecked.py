"""#270: SegQueue14 and SegQueue submit and revise whatever the segments hold.

Project lead, 2026-11-02: no segmentation check before submit, client or server.
These drive the real ``submit`` and ``reviseSubmission`` of both Slicer modules
with Slicer stubbed out and the export replaced by one that writes a synthetic
file, so what is under test is the logic between the export and the upload: it
must upload and hand over for an empty LAD, LCx or RCA, overlapping classes and
an empty scene alike. The export itself (the false "empty" of #270, and an empty
scene still writing a file) is covered inside Slicer by tests/slicer_selftest14.py.
"""

import importlib
import os
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).resolve().parents[1]

#: (module directory, module name, logic class)
MODULES = [("SegQueue14", "SegQueue14", "SegQueue14Logic"),
           ("SegQueue", "SegQueue", "SegQueueLogic")]

#: What the export reports, per case; "overlap" also has classOverlaps() say so.
CASES = {
    "LAD empty": {"LM": 10, "LAD": 0, "LCx": 20, "RCA": 30},
    "LCx empty": {"LM": 10, "LAD": 20, "LCx": 0, "RCA": 30},
    "RCA empty": {"LM": 10, "LAD": 20, "LCx": 30, "RCA": 0},
    "overlap": {"LM": 10, "LAD": 20, "LCx": 20, "RCA": 30},
    "all empty": {"LM": 0, "LAD": 0, "LCx": 0, "RCA": 0},
}


class _Base:
    def __init__(self, *args, **kwargs):
        pass


def _stubSlicer():
    stubs = {name: mock.MagicMock(name=name) for name in ("ctk", "qt", "vtk")}
    slicer = mock.MagicMock(name="slicer")
    slicer.app.applicationVersion = "5.8.1"
    scripted = types.ModuleType("slicer.ScriptedLoadableModule")
    scripted.ScriptedLoadableModule = _Base
    scripted.ScriptedLoadableModuleLogic = _Base
    scripted.ScriptedLoadableModuleWidget = _Base
    slicer.ScriptedLoadableModule = scripted
    stubs["slicer"] = slicer
    stubs["slicer.ScriptedLoadableModule"] = scripted
    return stubs


@pytest.fixture(params=MODULES, ids=[m[1] for m in MODULES])
def module(request, monkeypatch):
    directory, name, logicName = request.param
    for key, value in _stubSlicer().items():
        monkeypatch.setitem(sys.modules, key, value)
    monkeypatch.syspath_prepend(str(REPO / "src"))
    monkeypatch.syspath_prepend(str(REPO / "slicer" / directory))
    for cached in [m for m in sys.modules if m == name or m.startswith(name + "Lib")]:
        monkeypatch.delitem(sys.modules, cached)
    loaded = importlib.import_module(name)
    yield loaded, getattr(loaded, logicName)
    for cached in [m for m in sys.modules if m == name or m.startswith(name + "Lib")]:
        sys.modules.pop(cached, None)


class _Client:
    def __init__(self):
        self.calls = []

    def uploadFile(self, path, folderId, name=None, progress=None):
        assert os.path.isfile(path)
        self.calls.append(("upload", name))
        return {"_id": "file1"}

    def submit(self, assignmentId, meta, fileId, geometry=None):
        self.calls.append(("submit", assignmentId, meta.voxel_counts, geometry))
        return {"submissionId": "s1"}

    def reviseSubmission(self, submissionId, meta, fileId):
        self.calls.append(("revise", submissionId, meta.voxel_counts))
        return {"submissionId": "s2", "state": "approved"}


def _logic(module, tmp_path, counts):
    mod, Logic = module
    from segqueue.protocol import ProjectConfig
    from segqueue14 import labels

    logic = Logic(cacheRoot=str(tmp_path / "cache"))
    logic.project = ProjectConfig(name="t", instructions="",
                                  segments=labels.segment_specs(), upload_folder_id="f")
    logic.client = _Client()
    logic.volumeNode = object()
    logic.segmentationNode = object()
    logic.assignment = types.SimpleNamespace(assignment_id="a1", case_name="synthetic",
                                             attempt=1)
    os.makedirs(logic.cache.caseDir("a1"), exist_ok=True)

    def export(path):
        with open(path, "wb") as handle:
            handle.write(b"synthetic labelmap")
        return dict(counts), None, None

    logic.exportLabelmap = export
    # If anything still asked about overlaps, the answer would be "yes".
    logic.classOverlaps = lambda: [("LAD", "LCx", 20)]
    logic.bankTime = lambda: None
    logic.elapsedSeconds = lambda: 60.0
    logic.closeCase = lambda purge=False: None
    logic.cache.update = lambda *a, **k: None
    return logic


@pytest.mark.parametrize("case", list(CASES))
def test_submit_uploads_and_hands_over_whatever_the_segments_hold(module, tmp_path, case):
    logic = _logic(module, tmp_path, CASES[case])
    assert logic.submit() == {"submissionId": "s1"}
    kinds = [call[0] for call in logic.client.calls]
    assert kinds == ["upload", "submit"]
    assert logic.client.calls[1][2] == CASES[case]      # recorded as metadata


@pytest.mark.parametrize("case", list(CASES))
def test_a_reviewers_revision_uploads_whatever_the_segments_hold(module, tmp_path, case):
    logic = _logic(module, tmp_path, CASES[case])
    assert logic.reviseSubmission("s0")["state"] == "approved"
    assert [call[0] for call in logic.client.calls] == ["upload", "revise"]
    assert logic.client.calls[1][2] == CASES[case]


def test_no_segmentation_refusal_is_left_in_either_module():
    for directory, name, _ in MODULES:
        source = (REPO / "slicer" / directory / f"{name}.py").read_text(encoding="utf-8")
        for gone in ("missing_required", "overlap_message", "_exportChecked",
                     "There is nothing to"):
            assert gone not in source, (name, gone)
