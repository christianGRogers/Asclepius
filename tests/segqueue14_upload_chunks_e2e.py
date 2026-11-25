"""The SegQueue14 module's real ``uploadFile`` against a real Girder, over HTTP.

Annotators submitting a read over 768 KiB got Girder's "Chunk is smaller than the
minimum size. (HTTP 400)": the module sends 768 KiB chunks (under janus's 1 MiB
nginx limit, halved on 413 down to 64 KiB) and Girder refuses every non-final chunk
under ``core.upload_minimum_chunk_size``, 5 MiB by default. CI never saw it: the
acceptance job's client is the 4-class one (8 MiB chunks) on files of a few KB, so
every upload was one final chunk, which Girder exempts; and the server tests write
files through Girder's models, not the client.

Against a running Girder with its **default** minimum and a filesystem assetstore
(CI's acceptance job), with the module's own client:

1. a file of three chunks fails with exactly that 400, shown as the module's
   message, and the setting is Girder's default;
2. the deploy step's tool (``python -m girder_segqueue14.upload_chunks``, as
   ``segqueue14-deploy.sh upload-chunks`` runs it) dry-runs, applies, re-applies;
3. the same upload succeeds and the stored file's checksum matches;
4. behind an nginx-like proxy that refuses bodies over 70 KiB with 413, the client
   halves 768 -> 384 -> 192 -> 96 -> 64 KiB (the floor) and the upload succeeds,
   checksum matching;
5. the printed ``--restore`` puts Girder's default back, and the 400 returns.

Not collected by pytest (it needs a live server), like ``segqueue_e2e.py``::

    GIRDER_MONGO_URI=mongodb://localhost:27017/<db> python tests/segqueue14_upload_chunks_e2e.py \\
        --url http://localhost:8099 --admin-login admin --admin-password ...

``GIRDER_MONGO_URI`` must be the running Girder's database: the tool writes there.
Run it only against a scratch server: it changes the setting and puts it back.
"""

import argparse
import hashlib
import os
import random
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))

from SegQueue14Lib import SegQueue14Client, SegQueue14Error  # noqa: E402
from SegQueue14Lib import client as client14  # noqa: E402

KEY = "core.upload_minimum_chunk_size"
GIRDER_DEFAULT = 5 * 1024 * 1024
GIRDER_400 = "Chunk is smaller than the minimum size. (HTTP 400)"
PROXY_LIMIT = 70 * 1024
NGINX_413 = (b"<html><head><title>413 Request Entity Too Large</title></head>"
             b"<body><center><h1>413 Request Entity Too Large</h1></center>"
             b"<hr><center>nginx</center></body></html>")

_results = []


def check(name, condition, detail=""):
    _results.append((name, bool(condition)))
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""),
          flush=True)
    return bool(condition)


def tool(*args):
    """The deploy step's command, as segqueue14-deploy.sh runs it on janus."""
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "server"))
    done = subprocess.run([sys.executable, "-m", "girder_segqueue14.upload_chunks", *args],
                          capture_output=True, text=True, env=env, timeout=120)
    print("\n".join("      " + line for line in (done.stdout + done.stderr).splitlines()))
    return done.returncode, done.stdout


def setting(client):
    return client._json("GET", "system/setting", params={"key": KEY})


def privateFolder(client):
    me = client._json("GET", "user/me")
    rows = client._json("GET", "folder", params={
        "parentType": "user", "parentId": me["_id"], "name": "Private"})
    return rows[0]["_id"]


def stored(client, fileDoc):
    return client._request("GET", f"file/{fileDoc['_id']}/download").content


def girderSha512(fileDoc):
    """The SHA-512 Girder computed of the bytes it stored. Girder 5 keeps it on the
    file document but does not expose it over REST, so it is read from Mongo."""
    from bson import ObjectId
    from pymongo import MongoClient

    db = MongoClient(os.environ["GIRDER_MONGO_URI"]).get_default_database()
    doc = db.file.find_one({"_id": ObjectId(fileDoc["_id"])}, {"sha512": 1})
    return (doc or {}).get("sha512")


def proxy(upstream, limit):
    """An nginx stand-in: 413 for any body over ``limit``, else pass through."""
    counts = {"413": 0, "chunks": []}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _forward(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            if length > limit:
                counts["413"] += 1
                return self._reply(413, NGINX_413, {"Content-Type": "text/html"})
            if "file/chunk" in self.path:
                counts["chunks"].append(length)
            headers = {k: v for k, v in self.headers.items()
                       if k.lower() not in ("host", "content-length", "connection")}
            got = requests.request(self.command, upstream + self.path, headers=headers,
                                   data=body, timeout=60)
            keep = {k: v for k, v in got.headers.items()
                    if k.lower() in ("content-type", "content-disposition")}
            self._reply(got.status_code, got.content, keep)

        def _reply(self, status, body, headers):
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PUT = do_DELETE = _forward

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, counts


def main(argv=None):
    parser = argparse.ArgumentParser(prog="segqueue14_upload_chunks_e2e.py")
    parser.add_argument("--url", required=True)
    parser.add_argument("--admin-login", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--workdir", default=os.environ.get("RUNNER_TEMP", "/tmp"))
    args = parser.parse_args(argv)
    if not os.environ.get("GIRDER_MONGO_URI"):
        sys.exit("set GIRDER_MONGO_URI to the running Girder's database")

    client = SegQueue14Client(args.url, extensionVersion="e2e-chunks")
    client.login(args.admin_login, args.admin_password)
    folder = privateFolder(client)

    # Three chunks of the module's size: two non-final ones Girder checks.
    size = 2 * client14.UPLOAD_CHUNK_BYTES + 12345
    data = random.Random(14).randbytes(size)
    path = os.path.join(args.workdir, "extended-read.seg.nrrd")
    with open(path, "wb") as handle:
        handle.write(data)
    sha512 = hashlib.sha512(data).hexdigest()

    print("1. Girder's default minimum: the module's upload is refused")
    check("the setting is Girder's default (5 MiB)", setting(client) == GIRDER_DEFAULT,
          repr(setting(client)))
    try:
        client.uploadFile(path, folder, name="refused.seg.nrrd")
        check("the upload over 768 KiB fails", False, "it succeeded")
    except SegQueue14Error as exc:
        check("the upload over 768 KiB fails with HTTP 400", exc.status == 400, repr(exc.status))
        check("Girder's reason is exactly 'Chunk is smaller than the minimum size.'",
              str(exc.__cause__) == GIRDER_400, str(exc.__cause__))
        check("the annotator sees the module's message",
              str(exc) == client14.UPLOAD_CHUNK_REFUSED_MESSAGE, str(exc))
    check("the local file is untouched", os.path.exists(path) and os.path.getsize(path) == size)

    print("2. the deploy step: upload-chunks, then upload-chunks --apply")
    code, out = tool()
    check("the dry run exits 0", code == 0)
    check("the dry run prints the current and new value",
          f"{KEY}: current {GIRDER_DEFAULT} (not stored: Girder's default) -> new 0" in out)
    check("the dry run changes nothing", setting(client) == GIRDER_DEFAULT)
    code, out = tool("--apply")
    check("--apply exits 0", code == 0)
    check("Girder now answers 0", setting(client) == 0, repr(setting(client)))
    restore = next((line.split("--restore=", 1)[1].strip("'") for line in out.splitlines()
                    if "to put the old value back" in line), None)
    check("--apply prints the restore command", restore == '{"%s": null}' % KEY, repr(restore))
    code, out = tool("--apply")
    check("--apply again is a no-op", code == 0 and "already 0; nothing to change" in out)

    print("3. the same upload, through the module's client")
    try:
        doc = client.uploadFile(path, folder, name="accepted.seg.nrrd")
        check("the upload succeeds", doc.get("size") == size, repr(doc.get("size")))
        check("Girder's SHA-512 of the stored file matches", girderSha512(doc) == sha512,
              repr(girderSha512(doc))[:20])
        check("the stored file reads back byte for byte", stored(client, doc) == data)
        check("in chunks of 768 KiB", client.uploadChunkBytes == client14.UPLOAD_CHUNK_BYTES)
    except SegQueue14Error as exc:
        check("the upload succeeds", False, str(exc))

    print(f"4. behind a proxy refusing bodies over {PROXY_LIMIT // 1024} KiB (413), minimum 0")
    server, counts = proxy(client.serverUrl.rsplit("/api/v1", 1)[0], PROXY_LIMIT)
    try:
        behind = SegQueue14Client(f"http://127.0.0.1:{server.server_address[1]}",
                                  extensionVersion="e2e-chunks")
        behind.login(args.admin_login, args.admin_password)
        doc = behind.uploadFile(path, folder, name="behind-proxy.seg.nrrd")
        floor = client14.UPLOAD_CHUNK_FLOOR_BYTES
        check("the chunk halves down to the 64 KiB floor", behind.uploadChunkBytes == floor,
              f"{behind.uploadChunkBytes} bytes after {counts['413']} x 413")
        check("four 413s on the way (768 -> 384 -> 192 -> 96 -> 64 KiB)", counts["413"] == 4,
              repr(counts["413"]))
        check("every chunk Girder took was at most 64 KiB",
              counts["chunks"] and max(counts["chunks"]) <= floor)
        check("the upload succeeds", doc.get("size") == size, repr(doc.get("size")))
        check("Girder's SHA-512 of the stored file matches", girderSha512(doc) == sha512,
              repr(girderSha512(doc))[:20])
        check("the stored file reads back byte for byte", stored(client, doc) == data)
    except SegQueue14Error as exc:
        check("the upload behind the proxy succeeds", False, str(exc))
    finally:
        server.shutdown()

    print("5. --restore puts Girder's default back")
    code, _out = tool(f"--restore={restore}")
    check("--restore exits 0", code == 0)
    check("Girder answers its default again", setting(client) == GIRDER_DEFAULT,
          repr(setting(client)))
    try:
        client.uploadFile(path, folder, name="refused-again.seg.nrrd")
        check("and the 400 is back", False, "it succeeded")
    except SegQueue14Error as exc:
        check("and the 400 is back", exc.status == 400 and str(exc.__cause__) == GIRDER_400,
              str(exc.__cause__))

    failed = [name for name, ok in _results if not ok]
    print(f"\n{len(_results) - len(failed)} passed, {len(failed)} failed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
