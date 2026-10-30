"""A Python client for the Janus-M read queue (``/api/v1/janusm``).

What a reader's tool does, in order: :meth:`JanusMClient.login`, :meth:`project`,
:meth:`next_read`, :meth:`download_ct` (and :meth:`download_seed` unless the case is
blank), then :meth:`submit` with the read's label file, or :meth:`release`.

Every call sends the Janus-M protocol version, so a server that does not speak it
refuses with 426. Downloads are verified against the case checksum; uploads go
through Girder's chunked upload into the Janus-M incoming folder, then ``submit``
with the file's own sha256.

The Slicer reader module (a follow-up) is meant to sit on this. ``requests`` is the
only dependency outside the standard library.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional

from . import PROTOCOL_VERSION, protocol

CHUNK_BYTES = 8 * 1024 * 1024
CLIENT_VERSION = "janusm_reads-client"


class JanusMError(RuntimeError):
    def __init__(self, message: str, code: Optional[str] = None, status: int = 0):
        super().__init__(message)
        self.code = code
        self.status = status


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class JanusMClient:
    def __init__(self, server_url: str, session=None, token: Optional[str] = None):
        if session is None:
            import requests

            session = requests.Session()
        self.api = server_url.rstrip("/")
        if not self.api.endswith("/api/v1"):
            self.api += "/api/v1"
        self.session = session
        self.token = token

    # ------------------------------------------------------------- transport

    def _headers(self) -> Dict[str, str]:
        headers = {protocol.PROTOCOL_HEADER: str(PROTOCOL_VERSION),
                   protocol.CLIENT_VERSION_HEADER: CLIENT_VERSION}
        if self.token:
            headers["Girder-Token"] = self.token
        return headers

    def _request(self, method: str, path: str, stream: bool = False, **kwargs):
        response = self.session.request(method, f"{self.api}/{path}",
                                        headers=self._headers(), stream=stream, **kwargs)
        if response.status_code >= 400:
            code, message = None, f"HTTP {response.status_code}"
            try:
                body = response.json()
                extra = body.get("extra") if isinstance(body, dict) else None
                info = extra if isinstance(extra, dict) else body
                code = info.get("code")
                message = info.get("message") or body.get("message") or message
            except ValueError:
                pass
            raise JanusMError(message, code=code, status=response.status_code)
        return response

    def _json(self, method: str, path: str, **kwargs) -> Any:
        return self._request(method, path, **kwargs).json()

    def _save(self, path: str, dest: str) -> int:
        response = self._request("GET", path, stream=True)
        written = 0
        part = dest + ".part"
        with open(part, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if chunk:
                    handle.write(chunk)
                    written += len(chunk)
        os.replace(part, dest)
        return written

    # ----------------------------------------------------------------- calls

    def login(self, username: str, password: str) -> Dict[str, Any]:
        data = self._json("GET", "user/authentication", auth=(username, password))
        self.token = data["authToken"]["token"]
        return data["user"]

    def project(self) -> Dict[str, Any]:
        return self._json("GET", protocol.path(protocol.PROJECT),
                          params={"clientProtocol": PROTOCOL_VERSION})

    def my_reads(self) -> List[protocol.ReadInfo]:
        return [protocol.ReadInfo.from_dict(r)
                for r in self._json("GET", protocol.path(protocol.MINE))]

    def next_read(self) -> Optional[protocol.ReadInfo]:
        """The next case to read, or None when nothing is waiting for this reader."""
        try:
            data = self._json("POST", protocol.path(protocol.NEXT),
                              params={"clientProtocol": PROTOCOL_VERSION})
        except JanusMError as exc:
            if exc.code == protocol.ERR_QUEUE_EMPTY:
                return None
            raise
        return protocol.ReadInfo.from_dict(data)

    def download_ct(self, read: protocol.ReadInfo, dest: str) -> str:
        self._save(protocol.path(protocol.CASE_DOWNLOAD, read_id=read.read_id), dest)
        if read.checksum and sha256_file(dest) != read.checksum:
            os.unlink(dest)
            raise JanusMError("The CT download does not match its checksum; try again.",
                              code=protocol.ERR_CHECKSUM)
        return dest

    def download_seed(self, read: protocol.ReadInfo, dest: str) -> Optional[str]:
        """The seed, or None for a case read from blank."""
        if not read.has_seed:
            return None
        self._save(protocol.path(protocol.CASE_SEED, read_id=read.read_id), dest)
        return dest

    def upload(self, path: str, folder_id: str) -> Dict[str, Any]:
        size = os.path.getsize(path)
        upload = self._json("POST", "file", params={
            "parentType": "folder", "parentId": folder_id,
            "name": os.path.basename(path), "size": size})
        offset = 0
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(CHUNK_BYTES)
                if not chunk:
                    break
                upload = self._json("POST", "file/chunk", data=chunk,
                                    params={"uploadId": upload["_id"], "offset": offset})
                offset += len(chunk)
        return upload

    def submit(self, read: protocol.ReadInfo, label_path: str,
               voxel_counts: Dict[str, int], seconds: float = 0.0,
               note: str = "", cadrads: Optional[Dict[str, str]] = None,
               lesion_points: Optional[Dict[str, List[float]]] = None) -> protocol.ReadInfo:
        """Upload the read's label volume and read form, and submit them for the
        automatic check."""
        import json

        folder = self.project()["uploadFolderId"]
        file = self.upload(label_path, folder)
        meta = protocol.ReadSubmission(
            checksum=sha256_file(label_path), size_bytes=os.path.getsize(label_path),
            voxel_counts={str(k): int(v) for k, v in voxel_counts.items()},
            seconds=seconds, client_version=CLIENT_VERSION, note=note,
            cadrads=dict(cadrads or {}),
            lesion_points={k: [float(c) for c in v] for k, v in (lesion_points or {}).items()})
        data = self._json("POST", protocol.path(protocol.SUBMIT, read_id=read.read_id),
                          params={"fileId": file["_id"], "meta": json.dumps(meta.to_dict()),
                                  "clientProtocol": PROTOCOL_VERSION})
        return protocol.ReadInfo.from_dict(data)

    def release(self, read: protocol.ReadInfo) -> protocol.ReadInfo:
        return protocol.ReadInfo.from_dict(
            self._json("POST", protocol.path(protocol.RELEASE, read_id=read.read_id)))
