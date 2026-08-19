"""HTTP client for the SegQueue server. No Slicer, no Qt, no VTK.

**This deliberately does not use girder-client.** The obvious choice would have
been Kitware's own Python client, and the design sketch assumed it; it turns out
girder-client 5.x declares ``requires-python >= 3.10`` while Slicer 5.8 ships
Python 3.9, so ``pip_install('girder-client')`` inside Slicer either fails or
silently drags in the 3.x line with a different API. Since the extension needs
about a dozen calls, they are written here against ``requests``, which Slicer
already bundles. The result is one fewer moving part in a student's install and
no pip step at all -- matching the promise ``SegmentatorTrainMonitor`` already
makes.

Keeping this file free of Slicer imports is not incidental either: it is what
lets the whole network layer be tested against a stub session on a machine with
no Slicer and no server.
"""

import json
import os

import requests

from segqueue import PROTOCOL_VERSION, protocol
from segqueue.checksum import CHUNK_BYTES

#: Chunk size for resumable uploads. 8 MiB balances "few round trips" against
#: "how much has to be resent when a home connection drops mid-chunk".
UPLOAD_CHUNK_BYTES = 8 * 1024 * 1024

#: Connect/read timeouts. The read timeout is generous because the server hashes
#: an uploaded file before answering /submit, and a large segmentation on a busy
#: server can take a few seconds.
TIMEOUT = (10, 120)


class SegQueueError(RuntimeError):
    """Anything that went wrong talking to the server, with usable text."""


class SegQueueClient:
    """One logged-in session against one server.

    Tokens are held in memory only and never written to disk. On a shared
    undergraduate laptop that is the difference between "log in each session"
    and "anyone who opens Slicer is you".
    """

    def __init__(self, serverUrl, session=None, extensionVersion=''):
        self.serverUrl = serverUrl.rstrip('/')
        if not self.serverUrl.endswith('/api/v1'):
            self.serverUrl += '/api/v1'
        self.session = session or requests.Session()
        self.token = None
        self.user = None
        self.extensionVersion = extensionVersion

    # ------------------------------------------------------------- plumbing

    def _headers(self):
        headers = {
            protocol.PROTOCOL_HEADER: str(PROTOCOL_VERSION),
            protocol.CLIENT_VERSION_HEADER: self.extensionVersion or 'dev',
        }
        if self.token:
            headers['Girder-Token'] = self.token
        return headers

    def _request(self, method, path, stream=False, **kwargs):
        url = f'{self.serverUrl}/{path.lstrip("/")}'
        kwargs.setdefault('timeout', TIMEOUT)
        headers = self._headers()
        headers.update(kwargs.pop('headers', None) or {})
        try:
            response = self.session.request(method, url, headers=headers,
                                            stream=stream, **kwargs)
        except requests.RequestException as exc:
            raise SegQueueError(
                f'Could not reach the server at {self.serverUrl}.\n{exc}\n\n'
                'If you are off campus, check that the VPN is connected.'
            ) from exc

        if response.status_code >= 400:
            raise self._error(response)
        return response

    def _error(self, response):
        """Turn an HTTP failure into the most useful message we can manage."""
        try:
            body = response.json()
        except ValueError:
            body = None

        structured = protocol.parse_error(body)
        if structured is not None:
            error = SegQueueError(str(structured))
            error.code = structured.code
            error.detail = structured.detail
            return error

        message = ''
        if isinstance(body, dict):
            message = body.get('message', '')
        if not message:
            message = response.text[:400] or response.reason

        if response.status_code == 401:
            message = 'Your session has expired. Log in again.'
        error = SegQueueError(f'{message} (HTTP {response.status_code})')
        error.code = None
        error.detail = {}
        return error

    def _json(self, method, path, **kwargs):
        response = self._request(method, path, **kwargs)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise SegQueueError(
                f'The server returned something that is not JSON from {path}. '
                'This usually means a proxy or captive portal is in the way.'
            ) from exc

    # ------------------------------------------------------------------ auth

    def login(self, username, password):
        """Exchange a username and password for a Girder token."""
        response = self._request('GET', 'user/authentication',
                                 auth=(username, password))
        data = response.json()
        self.token = data['authToken']['token']
        self.user = data.get('user', {})
        return self.user

    def loginWithApiKey(self, key):
        """Token from a Girder API key -- for reviewers running unattended."""
        data = self._json('POST', 'api_key/token', params={'key': key})
        self.token = data['authToken']['token']
        self.user = self.whoami()
        return self.user

    def whoami(self):
        return self._json('GET', 'user/me')

    def logout(self):
        self.token = None
        self.user = None

    @property
    def loggedIn(self):
        return bool(self.token)

    # --------------------------------------------------------------- queue

    def project(self):
        return protocol.ProjectConfig.from_dict(
            self._json('GET', protocol.path(protocol.PROJECT)))

    def myAssignments(self, includeFinished=False):
        rows = self._json('GET', protocol.path(protocol.MINE),
                          params={'includeFinished': str(bool(includeFinished)).lower()})
        return [protocol.AssignmentInfo.from_dict(r) for r in rows or []]

    def nextCase(self):
        """Ask for a case. ``None`` when the queue is empty for this user.

        An empty queue is a normal outcome, not an error -- at the end of a
        project every annotator hits it -- so it is a return value rather than
        an exception the UI has to catch.
        """
        try:
            data = self._json('POST', protocol.path(protocol.NEXT),
                              params={'clientProtocol': PROTOCOL_VERSION})
        except SegQueueError as exc:
            if getattr(exc, 'code', None) == protocol.ERR_QUEUE_EMPTY:
                return None
            raise
        return protocol.AssignmentInfo.from_dict(data)

    def downloadCase(self, caseId, destPath, progress=None):
        """Stream a volume to ``destPath``. Returns the byte count written.

        Written to a ``.part`` file and renamed only on success, so an
        interrupted download can never be mistaken for a complete one by the
        code that hashes it next.
        """
        partPath = destPath + '.part'
        response = self._request(
            'GET', protocol.path(protocol.CASE_DOWNLOAD, case_id=caseId), stream=True)
        total = int(response.headers.get('Content-Length') or 0)

        written = 0
        with open(partPath, 'wb') as handle:
            for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                if not chunk:
                    continue
                handle.write(chunk)
                written += len(chunk)
                if progress is not None:
                    progress(written, total)

        if total and written != total:
            os.unlink(partPath)
            raise SegQueueError(
                f'The download stopped early: got {written} of {total} bytes. '
                'Check your connection and try again.')

        if os.path.exists(destPath):
            os.unlink(destPath)
        os.rename(partPath, destPath)
        return written

    def downloadAsset(self, caseId, kind, destPath, progress=None):
        """Fetch a case's helper mask. ``None`` when the case has none.

        A missing asset is the common answer, not an error -- most cases have no
        coronary seed -- so it is a return value the UI can branch on rather
        than an exception it has to catch around every case load.
        """
        try:
            response = self._request(
                'GET', protocol.path(protocol.CASE_ASSET, case_id=caseId, kind=kind),
                stream=True)
        except SegQueueError as exc:
            if getattr(exc, 'code', None) == protocol.ERR_NO_ASSET:
                return None
            raise

        written = 0
        with open(destPath, 'wb') as handle:
            for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                if not chunk:
                    continue
                handle.write(chunk)
                written += len(chunk)
                if progress is not None:
                    progress(written, 0)
        return destPath

    def heartbeat(self, assignmentId):
        """Best-effort. A failed heartbeat must never interrupt segmenting."""
        try:
            self._json('POST', protocol.path(protocol.HEARTBEAT,
                                             assignment_id=assignmentId))
            return True
        except SegQueueError:
            return False

    def releaseCase(self, assignmentId, reason=''):
        return self._json('POST', protocol.path(protocol.CASE_RELEASE,
                                                assignment_id=assignmentId),
                          params={'reason': reason})

    # -------------------------------------------------------------- upload

    def uploadFile(self, path, folderId, name=None, progress=None):
        """Chunked, resumable upload. Returns the Girder file document.

        Resumable is the point. A 20 MB segmentation over a student's home
        upstream can take a minute, and a dropped connection at second fifty
        should cost seconds, not the whole transfer -- so a failed chunk asks
        the server how much it actually has and continues from there.
        """
        name = name or os.path.basename(path)
        size = os.path.getsize(path)

        upload = self._json('POST', 'file', params={
            'parentType': 'folder', 'parentId': folderId,
            'name': name, 'size': size,
        })
        uploadId = upload['_id']

        with open(path, 'rb') as handle:
            offset = 0
            while offset < size:
                handle.seek(offset)
                chunk = handle.read(UPLOAD_CHUNK_BYTES)
                try:
                    upload = self._sendChunk(uploadId, offset, chunk)
                except SegQueueError:
                    # Ask the server what it really has, then continue. If it
                    # agrees with us the chunk genuinely failed, so re-raise
                    # rather than spin.
                    serverOffset = self._uploadOffset(uploadId)
                    if serverOffset <= offset:
                        raise
                    offset = serverOffset
                    continue

                offset += len(chunk)
                if progress is not None:
                    progress(offset, size)

        if '_id' not in upload or upload.get('size') != size:
            # Girder returns the finished file document on the last chunk.
            raise SegQueueError(
                'The server did not confirm the completed upload. Nothing has '
                'been submitted -- please try again.')
        return upload

    def _sendChunk(self, uploadId, offset, chunk):
        return self._json(
            'POST', 'file/chunk',
            params={'uploadId': uploadId, 'offset': offset},
            data=chunk,
            headers={'Content-Type': 'application/octet-stream'},
        )

    def _uploadOffset(self, uploadId):
        data = self._json('GET', 'file/offset', params={'uploadId': uploadId})
        return int((data or {}).get('offset', 0))

    # -------------------------------------------------------------- submit

    def submit(self, assignmentId, meta, fileId, geometry=None):
        """Hand an uploaded file to the queue as a finished segmentation."""
        return self._json(
            'POST', protocol.path(protocol.CASE_SUBMIT, assignment_id=assignmentId),
            params={
                'fileId': fileId,
                'meta': json.dumps(meta.to_dict()),
                'geometry': json.dumps(geometry or {}),
                'clientProtocol': PROTOCOL_VERSION,
            },
        )

    # -------------------------------------------------------------- review

    def reviewQueue(self, limit=50):
        return self._json('GET', protocol.path(protocol.REVIEW_QUEUE),
                          params={'limit': limit}) or []

    def claimReview(self, submissionId):
        return self._json('POST', protocol.path(protocol.REVIEW_CLAIM,
                                                submission_id=submissionId))

    def submitVerdict(self, submissionId, verdict, comment='', secondsSpent=None):
        params = {'verdict': verdict, 'comment': comment}
        if secondsSpent is not None:
            params['secondsSpent'] = secondsSpent
        return self._json('POST', protocol.path(protocol.REVIEW_VERDICT,
                                                submission_id=submissionId),
                          params=params)

    def downloadReviewFile(self, submissionId, what, destPath, progress=None):
        """Fetch a reviewer's copy of the submission (``download``) or the
        source volume (``volume``)."""
        path = f'{protocol.API_PREFIX}/review/{submissionId}/{what}'
        response = self._request('GET', path, stream=True)
        total = int(response.headers.get('Content-Length') or 0)
        written = 0
        with open(destPath, 'wb') as handle:
            for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
                if not chunk:
                    continue
                handle.write(chunk)
                written += len(chunk)
                if progress is not None:
                    progress(written, total)
        return written
