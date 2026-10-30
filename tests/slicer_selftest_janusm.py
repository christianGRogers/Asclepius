"""JanusMRead inside a real 3D Slicer, against a fake Janus-M read queue.

    xvfb-run -a Slicer --no-splash --no-main-window --python-script tests/slicer_selftest_janusm.py

A phantom heart (``janusm_reads.phantom``: no patient data) is served by an
in-process fake of ``/api/v1/janusm`` that speaks ``janusm-read`` 1 and runs the
real automatic check (``janusm_reads.checker``) on every upload. The module, run
through its own logic and widget:

* logs in, takes a seeded case, and loads the seed into the four JA1 segments by
  value (each segment exactly its class's voxels);
* measures the plateaus from the segments and sets the window level to a border's
  half-maximum threshold;
* refuses overlapping classes before any upload;
* submits the uncorrected seed (its LV pool drawn 2 mm too big), which the check
  returns, and shows the reasons;
* corrects the read and resubmits; the check accepts it, and the uploaded file is
  the read voxel for voxel on the CT grid;
* takes a blank case, which starts with four empty segments and is refused before
  upload until every class is drawn;
* never shows the read set or whether a case is scored, even though this fake
  server sends both.

With ``JANUSM_SELFTEST_INSTALLED=<folder>`` it tests the module Slicer loaded from
that installed folder instead of the checkout. The report goes to
``$JANUSM_SELFTEST_OUT`` (default ``./selftest-janusm.txt``); its last line is
``RESULT PASS`` or ``RESULT FAIL``.
"""

import hashlib
import json
import os
import sys
import tempfile
import traceback

OUT = os.environ.get("JANUSM_SELFTEST_OUT", os.path.abspath("selftest-janusm.txt"))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: Things a reader must never be shown; the fake server sends them anyway.
HIDDEN = ("seal", "decision", "scored", "readSet", "otherRead")

log = []
checks = []


def say(*parts):
    log.append(" ".join(str(p) for p in parts))


def check(name, passed, detail=""):
    checks.append(bool(passed))
    say("PASS" if passed else "FAIL", name, detail)


class _Response:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self._body, self._content = status, body, content

    def json(self):
        if self._body is None:
            raise ValueError("no JSON")
        return self._body

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size]


def _refusal(status, code, message):
    return _Response(status, {"message": message, "extra": {"code": code, "message": message}})


class FakeQueue:
    """``/api/v1/janusm`` in memory: one reader, a queue of cases, the real check."""

    def __init__(self, slicer, cases, tmp):
        from janusm_reads import PROTOCOL_VERSION

        self.slicer, self.cases, self.tmp = slicer, list(cases), tmp
        self.version = str(PROTOCOL_VERSION)
        self.reads, self.uploads, self.files = {}, {}, {}
        self.calls, self.headers = [], []

    def _info(self, read):
        case = read["case"]
        return {"readId": read["id"], "caseName": case["name"], "state": read["state"],
                "hasSeed": case["seed"] is not None,
                "checksum": hashlib.sha256(case["ct"]).hexdigest(),
                "sizeBytes": len(case["ct"]), "checkSummary": read.get("summary", ""),
                # A reader's tool must drop these: a server that leaked them is tested.
                "readSet": case["set"], "scored": True, "otherRead": "R-other"}

    def request(self, method, url, headers=None, stream=False, **kw):
        from janusm_reads import labels as L
        from janusm_reads import protocol
        from janusm_reads.checker import check_read

        path = url.split("/api/v1/", 1)[1]
        self.calls.append((method, path))
        self.headers.append(dict(headers or {}))
        if path == "user/authentication":
            return _Response(body={"authToken": {"token": "T"}, "user": {"login": "reader"}})
        if path.startswith("janusm/") and \
                (headers or {}).get(protocol.PROTOCOL_HEADER) != self.version:
            return _refusal(426, protocol.ERR_CLIENT_TOO_OLD, "old client")
        if path == "janusm/project":
            return _Response(body={"protocol": "janusm-read", "protocolVersion": 1,
                                   "uploadFolderId": "F1", "maxOpen": 1})
        if path == "janusm/mine":
            return _Response(body=[self._info(r) for r in self.reads.values()])
        if path == "janusm/next":
            if any(r["state"] in protocol.OPEN_STATES for r in self.reads.values()):
                return _refusal(409, protocol.ERR_AT_LIMIT, "finish first")
            if not self.cases:
                return _refusal(404, protocol.ERR_QUEUE_EMPTY, "nothing")
            read = {"id": "R%d" % (len(self.reads) + 1), "case": self.cases.pop(0),
                    "state": protocol.ASSIGNED}
            self.reads[read["id"]] = read
            return _Response(body=self._info(read))
        if path == "file":
            uid = "U%d" % (len(self.uploads) + 1)
            self.uploads[uid] = b""
            return _Response(body={"_id": uid})
        if path == "file/chunk":
            uid = kw["params"]["uploadId"]
            self.uploads[uid] += kw["data"]
            fid = "FILE-" + uid
            self.files[fid] = self.uploads[uid]
            return _Response(body={"_id": fid})
        parts = path.split("/")
        read = self.reads.get(parts[2]) if len(parts) == 4 else None
        if read is None:
            return _refusal(404, None, "no route " + path)
        case, action = read["case"], parts[3]
        if action == "ct":
            return _Response(content=case["ct"])
        if action == "seed":
            if case["seed"] is None:
                return _refusal(404, protocol.ERR_NO_SEED, "blank")
            return _Response(content=case["seed"])
        if action == "release":
            read["state"] = protocol.RELEASED
            return _Response(body=self._info(read))
        if action == "submit":
            if read["state"] not in protocol.OPEN_STATES:
                return _refusal(409, protocol.ERR_BAD_STATE, read["state"])
            meta = json.loads(kw["params"]["meta"])
            data = self.files[kw["params"]["fileId"]]
            if hashlib.sha256(data).hexdigest() != meta["checksum"]:
                return _refusal(400, protocol.ERR_CHECKSUM, "checksum")
            missing = L.missing_required(meta["voxelCounts"])
            if missing:
                return _refusal(400, protocol.ERR_MISSING_CLASS, L.missing_message(missing))
            values = self._array(data)
            report = check_read(values, case["ctArray"], case["spacing"])
            read["state"] = protocol.ACCEPTED if report.passed else protocol.RETURNED
            read["summary"] = report.summary()
            read["uploaded"] = values
            read["meta"] = meta
            return _Response(body=self._info(read))
        return _refusal(404, None, "no route " + path)

    def _array(self, data):
        path = os.path.join(self.tmp, "uploaded-%d.nii.gz" % len(self.calls))
        with open(path, "wb") as handle:
            handle.write(data)
        node = self.slicer.util.loadLabelVolume(path)
        try:
            return self.slicer.util.arrayFromVolume(node).copy()
        finally:
            self.slicer.mrmlScene.RemoveNode(node)


def _volumeBytes(slicer, array, spacing, path, label):
    cls = "vtkMRMLLabelMapVolumeNode" if label else "vtkMRMLScalarVolumeNode"
    node = slicer.mrmlScene.AddNewNodeByClass(cls, "phantom")
    slicer.util.updateVolumeFromArray(node, array)
    node.SetSpacing(*spacing)
    node.SetOrigin(-20.0, 15.0, 40.0)
    slicer.util.saveNode(node, path)
    slicer.mrmlScene.RemoveNode(node)
    with open(path, "rb") as handle:
        return handle.read()


def _counts(logic, L):
    return {v: int(logic.classMask(v).sum()) for v in L.CLASSES}


def _draw(slicer, logic, values):
    """What a reader's editing leaves: each segment set to one class of ``values``."""
    import numpy as np

    from janusm_reads import labels as L

    for value in L.CLASSES:
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            (values == value).astype(np.uint8), logic.segmentationNode,
            logic.segmentIdFor(value), logic.volumeNode)


def run():
    import numpy as np

    import slicer

    installed = os.environ.get("JANUSM_SELFTEST_INSTALLED")
    if installed:
        import JanusMRead as module

        where = os.path.dirname(os.path.abspath(module.__file__))
        check("testing the installed module",
              os.path.normcase(where) == os.path.normcase(os.path.abspath(installed)), where)
        import janusm_reads
        import janusm_reads.client

        check("with its own vendored client", os.path.normcase(os.path.dirname(
            janusm_reads.client.__file__)).startswith(os.path.normcase(
                os.path.abspath(installed))), janusm_reads.client.__file__)
        # The checker and the phantom are not shipped to readers; the fake server and
        # the test data take them from the checkout.
        janusm_reads.__path__.append(os.path.join(REPO, "src", "janusm_reads"))
    else:
        sys.path.insert(0, os.path.join(REPO, "src"))
        sys.path.insert(0, os.path.join(REPO, "slicer", "JanusMRead"))
        import JanusMRead as module
    check("the module's support code imported", module._IMPORT_ERROR is None,
          module._IMPORT_ERROR or "")

    from JanusMReadLib import halfmax

    from janusm_reads import labels as L
    from janusm_reads import phantom

    tmp = tempfile.mkdtemp()
    truth, spacing = phantom.heart()
    ct = phantom.ct_from(truth, spacing)
    seedLabels = phantom.move_border(truth, spacing, "endocardial", 2.0)
    ctBytes = _volumeBytes(slicer, ct, spacing, os.path.join(tmp, "ct.nii.gz"), False)
    seedBytes = _volumeBytes(slicer, seedLabels, spacing, os.path.join(tmp, "seed.nii.gz"), True)
    cases = [
        {"name": "phantom-seeded", "set": "decision", "ct": ctBytes, "seed": seedBytes,
         "ctArray": ct, "spacing": spacing},
        {"name": "phantom-blank", "set": "seal", "ct": ctBytes, "seed": None,
         "ctArray": ct, "spacing": spacing},
    ]
    server = FakeQueue(slicer, cases, tmp)

    # ---------------------------------------------------------- the widget
    widget = None
    try:
        widget = module.JanusMReadWidget()   # no parent: the base class runs setup()
        check("the panel builds", widget.logic is not None)
    except Exception:
        check("the panel builds", False, traceback.format_exc())

    logic = widget.logic if widget is not None and widget.logic is not None else \
        module.JanusMReadLogic()
    logic.cacheRoot = os.path.join(tmp, "cache")
    logic.connect("https://janus.example", "reader", "secret", session=server)
    check("logged in and read the project", logic.loggedIn and logic.project["uploadFolderId"]
          == "F1")

    # -------------------------------------------------------- seeded case
    read = logic.takeNext()
    logic.openRead(read)
    if widget is not None:
        widget._bindEditor()
        widget._showRead()
        widget._updateEnabled()
    counts = _counts(logic, L)
    expected = {v: int((seedLabels == v).sum()) for v in L.CLASSES}
    check("the seed loads into the four segments by value", counts == expected,
          (counts, expected))
    names = [logic.segmentationNode.GetSegmentation().GetNthSegment(i).GetName()
             for i in range(logic.segmentationNode.GetSegmentation().GetNumberOfSegments())]
    check("the segments are exactly the four JA1 classes",
          sorted(names) == sorted(L.CLASSES.values()), names)
    colour = logic.segmentationNode.GetSegmentation().GetSegment(
        logic.segmentIdFor(L.LV_POOL)).GetColor()
    check("with the JA1 colours", np.allclose(colour, L.COLORS[L.LV_POOL], atol=1e-3), colour)

    plateaus = logic.measurePlateausFromSegments()
    check("plateaus from the segments", abs(plateaus[halfmax.LV_BLOOD] - 420) < 10
          and abs(plateaus[halfmax.MYOCARDIUM] - 120) < 25
          and abs(plateaus[halfmax.FAT] + 100) < 15, plateaus)
    window, level = logic.applyBorderWindow(halfmax.ENDOCARDIAL)
    display = logic.volumeNode.GetDisplayNode()
    check("the endocardial window is at its half-maximum level",
          abs(display.GetLevel() - level) < 0.5 and abs(display.GetWindow() - window) < 0.5
          and abs(level - (plateaus[halfmax.LV_BLOOD] + plateaus[halfmax.MYOCARDIUM]) / 2)
          < 0.5, (display.GetWindow(), display.GetLevel()))

    roi = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", "roi")
    ijkToRas = vtk_matrix(slicer, logic.volumeNode)
    pool = np.argwhere(truth == L.LV_POOL).mean(axis=0)  # (k, j, i)
    centre = ijkToRas.MultiplyPoint((pool[2], pool[1], pool[0], 1.0))[:3]
    roi.SetXYZ(*centre)
    roi.SetRadiusXYZ(2.0, 2.0, 2.0)
    measured = logic.measurePlateauInRoi(halfmax.LV_BLOOD, roi)
    check("an ROI in the LV pool measures the LV blood plateau", abs(measured - 420) < 5,
          measured)

    before = len([c for c in server.calls if c[1] == "file"])
    myo = logic.classMask(L.LV_MYO)
    both = (myo | logic.classMask(L.LV_POOL)).astype(np.uint8)
    slicer.util.updateSegmentBinaryLabelmapFromArray(
        both, logic.segmentationNode, logic.segmentIdFor(L.LV_POOL), logic.volumeNode)
    try:
        logic.submit()
        refused = None
    except module.ReadRefused as exc:
        refused = exc.problems
    check("overlapping classes are refused before any upload",
          refused and "more than one class" in refused[0]
          and len([c for c in server.calls if c[1] == "file"]) == before, refused)
    _draw(slicer, logic, seedLabels)

    done = logic.submit()
    check("the uncorrected seed is returned by the check", done.state == "returned",
          done.state)
    check("with its reasons", "endocardial" in done.check_summary, done.check_summary)
    sent = server.reads[read.read_id]
    check("the upload is the read, voxel for voxel on the CT grid",
          np.array_equal(sent["uploaded"], seedLabels))
    check("its voxel counts were declared", {int(k): v for k, v in
                                              sent["meta"]["voxelCounts"].items()} == expected)
    if widget is not None:
        widget._showRead()
        shown = widget.checkLabel.text
        check("the panel shows the returned read's reasons",
              "returned" in shown and "endocardial" in shown, shown)

    _draw(slicer, logic, truth)
    done = logic.submit()
    check("the corrected read is accepted", done.state == "accepted", done.check_summary)
    check("and what was uploaded is the corrected read",
          np.array_equal(server.reads[read.read_id]["uploaded"], truth))

    # ---------------------------------------------------------- blank case
    blank = logic.takeNext()
    logic.openRead(blank)
    if widget is not None:
        widget._bindEditor()
        widget._showRead()
    check("a blank case says it has no seed", not blank.has_seed)
    check("and starts with four empty segments",
          all(n == 0 for n in _counts(logic, L).values()), _counts(logic, L))
    check("no seed was asked for", not any(p.endswith("/seed") and p.startswith(
        "janusm/read/" + blank.read_id) for _m, p in server.calls))
    before = len([c for c in server.calls if c[1] == "file"])
    try:
        logic.submit()
        refused = None
    except module.ReadRefused as exc:
        refused = exc.problems
    check("an empty read is refused before any upload",
          refused and "empty" in refused[-1]
          and len([c for c in server.calls if c[1] == "file"]) == before, refused)
    _draw(slicer, logic, truth)
    done = logic.submit()
    check("the drawn blank read is accepted", done.state == "accepted", done.check_summary)

    # -------------------------------------------------------- independence
    check("every Janus-M call carried the janusm-read protocol",
          all(h.get("X-JanusM-Protocol") == "1" for (m, p), h in
              zip(server.calls, server.headers) if p.startswith("janusm/")))
    check("and named this module", all(h.get("X-JanusM-Client", "").startswith("JanusMRead-")
                                       for h in server.headers))
    check("no admin route was called", not any("admin" in p for _m, p in server.calls))
    check("the reads it holds carry no read set", not any(
        hasattr(r, "read_set") or hasattr(r, "scored") for r in (read, blank, done)))
    if widget is not None:
        texts = " ".join(str(w.text) for w in (widget.caseLabel, widget.checkLabel,
                                                 widget.submitLabel, widget.statusLabel))
        check("the panel never shows the read set or scoring",
              not any(word.lower() in texts.lower() for word in HIDDEN), texts)
    check("the queue is now empty", logic.takeNext() is None)


def vtk_matrix(slicer, volume):
    import vtk

    matrix = vtk.vtkMatrix4x4()
    volume.GetIJKToRASMatrix(matrix)
    return matrix


try:
    run()
except Exception:
    say("EXCEPTION", traceback.format_exc())
    checks.append(False)

passed = bool(checks) and all(checks)
say("RESULT", "PASS" if passed else "FAIL")
with open(OUT, "w") as handle:
    handle.write("\n".join(log) + "\n")

import slicer  # noqa: E402  (only importable inside Slicer)

slicer.app.exit(0 if passed else 1)
