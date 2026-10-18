"""trillium/fetch_cases.py against a fake Girder (issue #79).

The fake serves the D22 layout the PM verified on janus (2026-10-18, #79 first comment): 800
ImageCAS ids in /collection/ImageCAS-X/cases, 200 in /collection/SegQueue/cases beside pool
volumes from other sources, each id as ImageCAS__NNNN.nii.gz (CT) + ImageCAS__NNNN__mask.nii.gz.
Item JSON has the shape Girder's /item endpoint returns. No credentials, no network.
"""

import base64
import importlib.util
import json
import os
import subprocess
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ICX4_LIB = REPO / "trillium" / "icx4" / "lib"
IMAGECAS_X = "/collection/ImageCAS-X/cases"
SEGQUEUE = "/collection/SegQueue/cases"
TOKEN = "fake-token"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fc = _load("fetch_cases_under_test", REPO / "trillium" / "fetch_cases.py")
layout = _load("icx4_layout_for_fetch", ICX4_LIB / "layout.py")


def _item(name, folder, k):
    data = f"{name}:{k}".encode()  # unique bytes per file, so the mapping can be checked
    return {
        "_id": f"{k:024x}",
        "_modelType": "item",
        "name": name,
        "folderId": folder,
        "size": len(data),
        "created": "2026-10-14T12:00:00.000000+00:00",
        "baseParentType": "collection",
        "meta": {},
    }, data


def d22_layout():
    """{girder path: [item names]}: the verified D22 layout; every 5th id is in SegQueue."""
    icx, sq = [], []
    for n in range(1, 1001):
        names = [f"ImageCAS__{n:04d}.nii.gz", f"ImageCAS__{n:04d}__mask.nii.gz"]
        (sq if n % 5 == 0 else icx).extend(names)
    pool = [
        "ImageCHD__0001.nii.gz",
        "ImageCHD__0002__mask.nii.gz",
        "CCA200-HF__0007.nii.gz",
        "CCA200-HF__0007__2.nii.gz",
        "ASOCA__Normal_1.nii.gz",
        "ImageCAS-X__0001__labels14.nii.gz",
        "ImageCAS__12.nii.gz",  # not 4 digits: not an ImageCAS item of this layout
    ]
    return {IMAGECAS_X: icx, SEGQUEUE: sq + pool}


class FakeGirder:
    """Read-only Girder: resource/lookup, item?folderId, item/<id>/download, user/authentication."""

    def __init__(self, folders):
        self.folders, self.items, self.blobs, self.requests = {}, {}, {}, []
        for k, (path, names) in enumerate(folders.items()):
            fid = f"f{k:023d}"
            self.folders[path] = fid
            for name in names:
                it, data = _item(name, fid, len(self.items) + 1)
                self.items[it["_id"]] = it
                self.blobs[it["_id"]] = data
        girder = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, obj, code=200):
                b = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):  # noqa: N802
                u = urllib.parse.urlparse(self.path)
                q = dict(urllib.parse.parse_qsl(u.query))
                p = u.path.removeprefix("/api/v1/")
                girder.requests.append(("GET", p, q, dict(self.headers)))
                if p == "user/authentication":
                    auth = self.headers.get("Authorization", "")
                    if base64.b64decode(auth.removeprefix("Basic ")).decode() != "ann:pw":
                        return self._json({"message": "Login failed."}, 401)
                    return self._json({"authToken": {"token": TOKEN}})
                if self.headers.get("Girder-Token") != TOKEN:
                    return self._json({"message": "Access denied"}, 401)
                if p == "resource/lookup":
                    if q.get("path") not in girder.folders:
                        return self._json({"message": f"Path not found: {q.get('path')}"}, 400)
                    return self._json({"_id": girder.folders[q["path"]], "_modelType": "folder"})
                if p == "item":
                    assert q.get("limit") == "0"
                    return self._json(
                        [i for i in girder.items.values() if i["folderId"] == q["folderId"]]
                    )
                if p.startswith("item/") and p.endswith("/download"):
                    b = girder.blobs[p.split("/")[1]]
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(b)))
                    self.end_headers()
                    self.wfile.write(b)
                    return None
                return self._json({"message": "no such route"}, 404)

            def _refuse(self):
                girder.requests.append((self.command, self.path, {}, {}))
                self._json({"message": "read-only fake"}, 405)

            do_POST = do_PUT = do_DELETE = do_PATCH = _refuse  # noqa: N815

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.api = f"http://127.0.0.1:{self.server.server_address[1]}/api/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def downloads(self):
        return [r[1].split("/")[1] for r in self.requests if r[1].endswith("/download")]

    def by_name(self, name):
        return next(i for i in self.items.values() if i["name"] == name)


@pytest.fixture
def girder(monkeypatch):
    made = []

    def make(folders=None):
        g = FakeGirder(folders or d22_layout())
        made.append(g)
        monkeypatch.setattr(fc, "API", g.api)
        monkeypatch.setenv("GIRDER_TOKEN", TOKEN)
        return g

    yield make
    for g in made:
        g.server.shutdown()


def _blob(g, name):
    return g.blobs[g.by_name(name)["_id"]]


# ------------------------------------------------------------------------------- the happy path
def test_fetches_exactly_the_1000_imagecas_cts_and_skips_the_pool(girder, tmp_path, capsys):
    g = girder()
    out = tmp_path / "cases"
    fc.main([str(out)])
    dirs = sorted(p.name for p in out.iterdir() if p.is_dir())
    assert dirs == [f"c{i:04d}" for i in range(1000)]
    for n in (1, 5, 500, 1000):  # ImageCAS id n -> c{n-1}, from either folder
        d = out / f"c{n - 1:04d}"
        assert (d / "ct.nii.gz").read_bytes() == _blob(g, f"ImageCAS__{n:04d}.nii.gz")
        assert sorted(os.listdir(d)) == ["ct.nii.gz"]  # CT only by default
    got = {g.items[i]["name"] for i in g.downloads()}
    assert got == {f"ImageCAS__{n:04d}.nii.gz" for n in range(1, 1001)}  # no mask, no pool volume
    rows = json.loads((out / "cases.json").read_text())
    assert len(rows) == 1000 and rows[0]["case"] == "c0000" and rows[0]["imagecas_id"] == 1
    assert {r["folder"] for r in rows if r["imagecas_id"] % 5 == 0} == {SEGQUEUE}
    assert {r["folder"] for r in rows if r["imagecas_id"] % 5} == {IMAGECAS_X}
    log = capsys.readouterr().out
    assert f"{IMAGECAS_X}: 800 ImageCAS ids (1600 items, 0 other volumes skipped)" in log
    assert f"{SEGQUEUE}: 200 ImageCAS ids (407 items, 7 other volumes skipped)" in log
    assert "1000 ImageCAS cases (CT only)" in log
    # read-only: every request is a GET, and every one past login carries the token
    assert {r[0] for r in g.requests} == {"GET"}
    assert all(r[3].get("Girder-Token") == TOKEN for r in g.requests)


def test_masks_flag_also_fetches_the_original_masks(girder, tmp_path):
    g = girder()
    out = tmp_path / "cases"
    fc.main(["--masks", str(out)])
    d = out / "c0041"
    assert sorted(os.listdir(d)) == ["coronary_arteries.nii.gz", "ct.nii.gz"]
    assert (d / "coronary_arteries.nii.gz").read_bytes() == _blob(g, "ImageCAS__0042__mask.nii.gz")
    assert len(g.downloads()) == 2000


def test_resumes_and_redoes_only_what_is_missing_or_wrong(girder, tmp_path):
    g = girder()
    out = tmp_path / "cases"
    fc.main([str(out)])
    n0 = len(g.downloads())
    (out / "c0007" / "ct.nii.gz").unlink()
    (out / "c0008" / "ct.nii.gz").write_bytes(b"x")  # truncated by a kill
    (out / "c0009" / "ct.nii.gz.part").write_bytes(b"junk")
    fc.main([str(out)])
    redone = {g.items[i]["name"] for i in g.downloads()[n0:]}
    assert redone == {"ImageCAS__0008.nii.gz", "ImageCAS__0009.nii.gz"}
    assert (out / "c0007" / "ct.nii.gz").read_bytes() == _blob(g, "ImageCAS__0008.nii.gz")


def test_logs_in_with_user_and_password(girder, tmp_path, monkeypatch):
    g = girder()
    monkeypatch.delenv("GIRDER_TOKEN")
    monkeypatch.setenv("GIRDER_USER", "ann")
    monkeypatch.setenv("GIRDER_PASSWORD", "pw")
    assert fc.login() == TOKEN
    assert g.requests[0][1] == "user/authentication"


# ------------------------------------------------------------------- the completeness verdict (#82)
def test_a_complete_run_says_1000_of_1000(girder, tmp_path, capsys):
    girder()
    fc.main([str(tmp_path / "cases")])
    assert "1000 of 1000 CTs complete" in capsys.readouterr().out


def test_an_interrupted_fetch_exits_nonzero_with_the_resume_hint(
    girder, tmp_path, monkeypatch, capsys
):
    girder()
    out = tmp_path / "cases"
    real = fc.fetch
    cut = {f"c{i:04d}" for i in range(0, 1000, 3)}  # 334 transfers drop; some leave a .part

    def flaky(token, item, dest):
        case = os.path.basename(os.path.dirname(dest))
        if case in cut:
            if int(case[1:]) % 2:
                with open(f"{dest}.part.{os.getpid()}", "wb") as f:
                    f.write(b"half")
            raise SystemExit(f"failed to download {dest}")
        return real(token, item, dest)

    monkeypatch.setattr(fc, "fetch", flaky)
    with pytest.raises(SystemExit) as e:
        fc.main([str(out)])
    assert e.value.code == 1
    log = capsys.readouterr().out
    assert "INCOMPLETE: 666 of 1000 CTs complete; 167 missing / 167 partial (.part)" in log
    assert f"re-run to resume: python3 {REPO / 'trillium' / 'fetch_cases.py'} {out}" in log
    assert "1000 of 1000" not in log
    # the folders exist, but icx4 sees them as incomplete, not as cases
    assert len(layout.scan(str(out))[1]) == 666 and len(layout.incomplete(str(out))) == 334

    monkeypatch.setattr(fc, "fetch", real)  # the re-run resumes and finishes
    fc.main([str(out)])
    assert "1000 of 1000 CTs complete" in capsys.readouterr().out


# ---------------------------------------------------- one fetch per cases/, own .part files (#82)
HOLD = """
import fcntl, sys, time
f = open(sys.argv[1], "a+")
fcntl.flock(f, fcntl.LOCK_EX)
f.seek(0); f.truncate(); f.write("4242\\n"); f.flush()
print("locked", flush=True)
time.sleep(60)
"""


def test_a_second_fetch_on_the_same_cases_dir_is_refused(girder, tmp_path):
    g = girder()
    out = tmp_path / "cases"
    out.mkdir()
    other = subprocess.Popen(
        [sys.executable, "-c", HOLD, str(out / ".fetch.lock")], stdout=subprocess.PIPE, text=True
    )
    try:
        assert other.stdout.readline().strip() == "locked"
        held = r"another fetch_cases.py \(pid 4242\) is already filling"
        with pytest.raises(SystemExit, match=held):
            fc.main([str(out)])
        assert not g.downloads() and not (out / "cases.json").exists()
    finally:
        other.kill()
        other.wait()
    fc.main([str(out)])  # the other run is gone: this one takes the lock and finishes
    assert len(g.downloads()) == 1000
    assert (out / ".fetch.lock").read_text().strip() == str(os.getpid())


def test_part_files_are_per_process_and_stale_ones_are_cleared(girder, tmp_path, monkeypatch):
    g = girder()
    out = tmp_path / "cases"
    d = out / "c0011"
    d.mkdir(parents=True)
    (d / "ct.nii.gz.part").write_bytes(b"old-style leftover")
    (d / "ct.nii.gz.part.99999").write_bytes(b"from a dead run")
    renamed = []
    real = os.replace
    monkeypatch.setattr(fc.os, "replace", lambda a, b: (renamed.append(a), real(a, b))[1])
    fc.main([str(out)])
    assert renamed and all(r.endswith(f".part.{os.getpid()}") for r in renamed)
    assert sorted(os.listdir(d)) == ["ct.nii.gz"]
    assert (d / "ct.nii.gz").read_bytes() == _blob(g, "ImageCAS__0012.nii.gz")


# ------------------------------------------------------------------------------------- refusals
def _mutate(fn):
    f = d22_layout()
    fn(f)
    return f


REFUSALS = {
    "a CT missing": (
        lambda f: f[IMAGECAS_X].remove("ImageCAS__0001.nii.gz"),
        "mask(s) without a CT",
    ),
    "an id missing entirely": (
        lambda f: [f[SEGQUEUE].remove(f"ImageCAS__0005{s}.nii.gz") for s in ("", "__mask")],
        "expected 200 ImageCAS ids, found 199",
    ),
    "an id in both folders": (
        lambda f: (
            [f[SEGQUEUE].remove(f"ImageCAS__0005{s}.nii.gz") for s in ("", "__mask")],
            f[SEGQUEUE].append("ImageCAS__0001.nii.gz"),
        ),
        "more than one folder",
    ),
    "an id outside 1-1000": (
        lambda f: (
            [f[SEGQUEUE].remove(f"ImageCAS__0005{s}.nii.gz") for s in ("", "__mask")],
            f[SEGQUEUE].append("ImageCAS__1001.nii.gz"),
        ),
        "not exactly 1-1000",
    ),
    "a duplicated item": (
        lambda f: f[IMAGECAS_X].append("ImageCAS__0001.nii.gz"),
        "two items named ImageCAS__0001.nii.gz",
    ),
    "a folder that is not there": (
        lambda f: f.pop(SEGQUEUE),
        "HTTP Error 400",
    ),
}


@pytest.mark.parametrize("case", sorted(REFUSALS))
def test_refuses_anything_but_exactly_ids_1_to_1000(girder, tmp_path, case):
    fn, msg = REFUSALS[case]
    g = girder(_mutate(fn))
    out = tmp_path / "cases"
    with pytest.raises((SystemExit, OSError)) as e:
        fc.main([str(out)])
    assert msg in str(e.value)
    assert not g.downloads() and not out.exists()  # refused before writing anything


def test_masks_flag_refuses_a_case_without_a_mask(girder, tmp_path):
    g = girder(_mutate(lambda f: f[IMAGECAS_X].remove("ImageCAS__0002__mask.nii.gz")))
    with pytest.raises(SystemExit, match="have no __mask item"):
        fc.main(["--masks", str(tmp_path / "cases")])
    assert not g.downloads()
    fc.main([str(tmp_path / "cases")])  # CT only does not need it
    assert len(g.downloads()) == 1000


# ------------------------------------------------------------------------ icx4 accepts the result
def test_icx4_layout_accepts_what_fetch_cases_writes(girder, tmp_path):
    girder()
    out = tmp_path / "cases"
    fc.main([str(out)])
    kind, cases = layout.scan(str(out))
    assert kind == "girder-ct" and len(cases) == 1000
    assert cases["c0999"] == {"ct": str(out / "c0999" / "ct.nii.gz"), "mask": None}

    out2 = tmp_path / "with_masks" / "cases"
    fc.main(["--masks", str(out2)])
    kind, cases = layout.scan(str(out2))
    assert kind == "girder" and len(cases) == 1000


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
