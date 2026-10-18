"""HTTP client for the SegQueue14 server routes (``/api/v1/segqueue14``). No
Slicer, no Qt, no VTK.

The live module's client (``slicer/SegQueue/SegQueueLib/client.py``) with the
SegQueue14 protocol: its own prefix, headers and version, sent on every write and
at login, and the ``prelabel`` asset. Kept a separate copy rather than a subclass
so the live module's file is untouched and the two can be installed side by side.

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
from typing import Any, Callable, Dict, List, Optional

import requests

from segqueue14 import PROTOCOL_VERSION, protocol
from segqueue.checksum import CHUNK_BYTES
from segqueue.dataset import suffix_for

#: Chunk size for resumable uploads. 8 MiB balances "few round trips" against
#: "how much has to be resent when a home connection drops mid-chunk".
UPLOAD_CHUNK_BYTES = 8 * 1024 * 1024

#: Connect/read timeouts. The read timeout is generous because the server hashes
#: an uploaded file before answering /submit, and a large segmentation on a busy
#: server can take a few seconds.
TIMEOUT = (10, 120)

#: ``progress(bytesDone, bytesTotal)``; total is 0 when the server sent no length.
Progress = Optional[Callable[[int, int], None]]


class SegQueue14Error(RuntimeError):
    """Anything that went wrong talking to the server, with usable text.

    ``code`` is the server's structured refusal code (a ``protocol.ERR_*``) and
    ``detail`` its extra fields, when the failure was such a refusal; otherwise
    ``None`` and ``{}``. Every instance carries both, so callers can branch on
    ``exc.code`` without first asking whether it is there.
    """

    def __init__(self, message: str, code: Optional[str] = None,
                 detail: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.detail = detail if detail is not None else {}


def _unlinkQuietly(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def filenameFromResponse(response: requests.Response) -> str:
    """The filename a server suggested in Content-Disposition, or ''.

    Girder sends one on every file download. It is the only way to learn the
    extension of a helper mask without adding a field to the wire protocol for
    each one -- and the extension is what Slicer reads to choose a loader.
    """
    header = response.headers.get('Content-Disposition', '') or ''
    for part in header.split(';'):
        part = part.strip()
        if part.lower().startswith('filename='):
            return part.split('=', 1)[1].strip().strip('"\'')
    return ''


class SegQueue14Client:
    """One logged-in session against one server.

    Tokens are held in memory only and never written to disk. On a shared
    undergraduate laptop that is the difference between "log in each session"
    and "anyone who opens Slicer is you".
    """

    def __init__(self, serverUrl: str, session: Optional[requests.Session] = None,
                 extensionVersion: str = '') -> None:
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
            raise SegQueue14Error(
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
            return SegQueue14Error(str(structured), structured.code, structured.detail)

        message = ''
        if isinstance(body, dict):
            message = body.get('message', '')
        if not message:
            message = response.text[:400] or response.reason

        if response.status_code == 401:
            message = 'Your session has expired. Log in again.'
        return SegQueue14Error(f'{message} (HTTP {response.status_code})')

    @staticmethod
    def _writeBody(response, handle, total=0, progress=None):
        """Copy a streamed response body into an open file. Returns bytes written.

        ``total`` is only passed through to ``progress``; nothing here checks it.
        """
        written = 0
        for chunk in response.iter_content(chunk_size=CHUNK_BYTES):
            if not chunk:
                continue
            handle.write(chunk)
            written += len(chunk)
            if progress is not None:
                progress(written, total)
        return written

    def _saveBody(self, response, destPath, progress=None, reportTotal=True):
        """Save a streamed response at ``destPath``. Returns bytes written.

        Written to ``destPath + '.part'`` and renamed only once the whole body
        has arrived, checked against ``Content-Length`` when the server sent
        one. A dropped connection or a short body removes the ``.part`` file
        and raises, so nothing at ``destPath`` is ever a partial download.
        ``reportTotal=False`` passes 0 as the total to ``progress``.
        """
        partPath = destPath + '.part'
        total = int(response.headers.get('Content-Length') or 0)
        try:
            with open(partPath, 'wb') as handle:
                written = self._writeBody(
                    response, handle, total if reportTotal else 0, progress)
        except BaseException:
            _unlinkQuietly(partPath)
            raise

        if total and written != total:
            _unlinkQuietly(partPath)
            raise SegQueue14Error(
                f'The download stopped early: got {written} of {total} bytes. '
                'Check your connection and try again.')

        os.replace(partPath, destPath)
        return written

    def _json(self, method, path, **kwargs):
        response = self._request(method, path, **kwargs)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise SegQueue14Error(
                f'The server returned something that is not JSON from {path}. '
                'This usually means a proxy or captive portal is in the way.'
            ) from exc

    # ------------------------------------------------------------------ auth

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Exchange a username and password for a Girder token."""
        response = self._request('GET', 'user/authentication',
                                 auth=(username, password))
        data = response.json()
        self.token = data['authToken']['token']
        self.user = data.get('user', {})
        return self.user

    def loginWithApiKey(self, key: str) -> Dict[str, Any]:
        """Token from a Girder API key -- for reviewers running unattended."""
        data = self._json('POST', 'api_key/token', params={'key': key})
        self.token = data['authToken']['token']
        self.user = self.whoami()
        return self.user

    def whoami(self) -> Optional[Dict[str, Any]]:
        """The logged-in user's Girder document."""
        return self._json('GET', 'user/me')

    def logout(self) -> None:
        """Forget the token locally; nothing is sent to the server."""
        self.token = None
        self.user = None

    @property
    def loggedIn(self) -> bool:
        return bool(self.token)

    # --------------------------------------------------------------- queue

    def project(self) -> 'protocol.ProjectConfig':
        """The project protocol. Refused (426) for an out-of-date module."""
        return protocol.ProjectConfig.from_dict(
            self._json('GET', protocol.path(protocol.PROJECT),
                       params={'clientProtocol': PROTOCOL_VERSION}))

    def myAssignments(self, includeFinished: bool = False
                      ) -> List['protocol.AssignmentInfo14']:
        """This user's assignments; finished ones too only when asked."""
        rows = self._json('GET', protocol.path(protocol.MINE),
                          params={'includeFinished': str(bool(includeFinished)).lower()})
        return [protocol.AssignmentInfo14.from_dict(r) for r in rows or []]

    def nextCase(self) -> Optional['protocol.AssignmentInfo14']:
        """Ask for a case. ``None`` when the queue is empty for this user.

        An empty queue is a normal outcome, not an error -- at the end of a
        project every annotator hits it -- so it is a return value rather than
        an exception the UI has to catch.
        """
        try:
            data = self._json('POST', protocol.path(protocol.NEXT),
                              params={'clientProtocol': PROTOCOL_VERSION})
        except SegQueue14Error as exc:
            if exc.code == protocol.ERR_QUEUE_EMPTY:
                return None
            raise
        return protocol.AssignmentInfo14.from_dict(data)

    def downloadCase(self, caseId: str, destPath: str, progress: Progress = None) -> int:
        """Stream a volume to ``destPath``. Returns the byte count written.

        Written to a ``.part`` file and renamed only on success, so an
        interrupted download can never be mistaken for a complete one by the
        code that hashes it next.
        """
        response = self._request(
            'GET', protocol.path(protocol.CASE_DOWNLOAD, case_id=caseId), stream=True)
        return self._saveBody(response, destPath, progress)

    def downloadAsset(self, caseId: str, kind: str, destPath: str,
                      progress: Progress = None) -> Optional[str]:
        """Fetch a case's helper mask. ``None`` when the case has none.

        A missing asset is the common answer, not an error -- most cases have no
        coronary seed -- so it is a return value the UI can branch on rather
        than an exception it has to catch around every case load.

        ``destPath`` is a stem: the server's own extension is appended, because
        Slicer chooses its reader from the filename and a NIfTI written as
        ``.nrrd`` fails to open with an error that never mentions the name.
        Returns the path actually written.
        """
        try:
            response = self._request(
                'GET', protocol.path(protocol.CASE_ASSET, case_id=caseId, kind=kind),
                stream=True)
        except SegQueue14Error as exc:
            if exc.code == protocol.ERR_NO_ASSET:
                return None
            raise

        suffix = suffix_for(filenameFromResponse(response), default='.nii.gz')
        if not destPath.lower().endswith(suffix):
            destPath += suffix

        # Through a ``.part`` file like every other download: the panel caches
        # helpers by name and reuses whatever it finds, so a half-written mask
        # left at ``destPath`` would be reused on every reopen (#64).
        self._saveBody(response, destPath, progress, reportTotal=False)
        return destPath

    def heartbeat(self, assignmentId: str) -> bool:
        """Best-effort. A failed heartbeat must never interrupt segmenting."""
        try:
            self._json('POST', protocol.path(protocol.HEARTBEAT,
                                             assignment_id=assignmentId))
            return True
        except SegQueue14Error:
            return False

    def releaseCase(self, assignmentId: str, reason: str = '') -> Any:
        """Give an assignment back to the pool."""
        return self._json('POST', protocol.path(protocol.CASE_RELEASE,
                                                assignment_id=assignmentId),
                          params={'reason': reason})

    # --------------------------------------------------------------- notes

    def caseNotes(self, caseId: str,
                  limit: Optional[int] = None) -> List['protocol.CaseNote']:
        """The case's note thread, oldest first. ``[]`` when there is none.

        Read every time a case is opened and on a slow timer while it is open,
        so it is deliberately cheap and deliberately forgiving: a thread that
        cannot be fetched is a missing panel, not a case an annotator cannot
        work on.
        """
        params = {}
        if limit:
            params['limit'] = int(limit)
        rows = self._json('GET', protocol.path(protocol.CASE_NOTES, case_id=caseId),
                          params=params) or []
        return [protocol.CaseNote.from_dict(row) for row in rows]

    def addCaseNote(self, caseId: str, text: str) -> 'protocol.CaseNote':
        """Append one note. Returns it as the server stored it.

        The author is not sent: the server resolves it from the session. A
        client-supplied name in a thread people use to judge segmentations would
        be a claim about identity rather than a fact about it.
        """
        cleaned = protocol.clean_note(text)
        if not cleaned:
            raise SegQueue14Error('There is nothing to post.')
        row = self._json('POST', protocol.path(protocol.CASE_NOTES, case_id=caseId),
                         params={'text': cleaned})
        return protocol.CaseNote.from_dict(row or {})

    # -------------------------------------------------------------- upload

    def uploadFile(self, path: str, folderId: str, name: Optional[str] = None,
                   progress: Progress = None) -> Dict[str, Any]:
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
                except SegQueue14Error:
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
            raise SegQueue14Error(
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

    def submit(self, assignmentId: str, meta: 'protocol.SubmissionMeta', fileId: str,
               geometry: Optional[Dict[str, Any]] = None) -> Any:
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

    def reviewQueue(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Submissions sampled for review and awaiting a verdict."""
        return self._json('GET', protocol.path(protocol.REVIEW_QUEUE),
                          params={'limit': limit}) or []

    def caseOverview(self, limit: int = 200, offset: int = 0, state: Optional[str] = None,
                     unassigned: bool = False) -> List[Dict[str, Any]]:
        """Every case and every lease ever taken on it.

        The submission viewer's own call, and deliberately not ``reviewQueue``:
        that returns only the sampled fraction awaiting a verdict, which cannot
        answer "where is case s0042?" -- the question a reviewer actually has.
        """
        params = {'limit': limit, 'offset': offset}
        if state:
            params['state'] = state
        if unassigned:
            params['unassigned'] = True
        return self._json('GET', protocol.path(protocol.REVIEW_CASES),
                          params=params) or []

    def allCases(self, state: Optional[str] = None, unassigned: bool = False,
                 page: int = 200, progress: Optional[Callable[[int], None]] = None
                 ) -> List[Dict[str, Any]]:
        """Every case in the project, paged.

        One request would be simpler and wrong: the endpoint pages, and a
        project of a thousand cases silently returns the first page to a caller
        who asked for all of them -- which looks like the pool being smaller
        than it is, the one mistake a reviewer cannot detect by eye.

        A filtered page can also come back *short* without the listing being
        over, because the state filter is applied after the page is read. So the
        loop stops on an empty page, not on a short one.
        """
        out, offset = [], 0
        while True:
            batch = self.caseOverview(limit=page, offset=offset, state=state,
                                      unassigned=unassigned)
            if not batch:
                return out
            out.extend(batch)
            offset += page
            if progress is not None:
                progress(len(out))
            if len(out) > 100000:  # pragma: no cover - a loop that cannot end
                raise SegQueue14Error(
                    'The server kept returning cases past any plausible project '
                    'size; stopping rather than filling memory.')

    def caseSubmissions(self, caseId: str) -> List[Dict[str, Any]]:
        """Every submission ever made against one case, oldest first."""
        return self._json('GET', protocol.path(protocol.REVIEW_CASE_SUBMISSIONS,
                                               case_id=caseId)) or []

    def reviseSubmission(self, submissionId: str, meta: 'protocol.SubmissionMeta',
                         fileId: str) -> Any:
        """Store a reviewer's corrected version, which also approves the case."""
        return self._json(
            'POST', protocol.path(protocol.REVIEW_REVISE,
                                  submission_id=submissionId),
            params={'fileId': fileId, 'meta': json.dumps(meta.to_dict())})

    def annotators(self) -> List[Dict[str, Any]]:
        """Who a case can be handed to, with how much each already holds."""
        return self._json('GET', protocol.path(protocol.REVIEW_ANNOTATORS)) or []

    def assignCase(self, caseId: str, userId: str) -> Any:
        """Hand one case to one annotator."""
        return self._json('POST', protocol.path(protocol.REVIEW_ASSIGN,
                                                case_id=caseId),
                          params={'userId': userId})

    def downloadCaseVolume(self, caseId: str, destPath: str,
                           progress: Progress = None) -> int:
        """A case's source volume, for a reviewer who does not hold it."""
        return self._stream(
            protocol.path(protocol.REVIEW_CASE_VOLUME, case_id=caseId),
            destPath, progress=progress)

    def downloadCaseAsset(self, caseId: str, kind: str, destPath: str,
                          progress: Progress = None) -> Optional[int]:
        """A case's helper mask, or None when it ships none."""
        try:
            return self._stream(
                protocol.path(protocol.REVIEW_CASE_ASSET, case_id=caseId,
                              kind=kind),
                destPath, progress=progress)
        except SegQueue14Error as exc:
            # Most cases ship neither mask and the panel asks for both on every
            # one, so absence is an answer rather than a failure.
            if exc.code == protocol.ERR_NO_ASSET:
                return None
            raise

    def _stream(self, path, destPath, progress=None):
        """Download to a file, reporting progress. Returns the bytes written."""
        response = self._request('GET', path, stream=True)
        return self._saveBody(response, destPath, progress)

    def returnToPool(self, submissionId: str, reason: str = '') -> Any:
        """Send a submitted case back to the pool for a different annotator."""
        return self._json('POST', protocol.path(protocol.REVIEW_POOL,
                                                submission_id=submissionId),
                          params={'reason': reason})

    def claimReview(self, submissionId: str) -> Any:
        """Take a sampled submission to review."""
        return self._json('POST', protocol.path(protocol.REVIEW_CLAIM,
                                                submission_id=submissionId))

    def submitVerdict(self, submissionId: str, verdict: str, comment: str = '',
                      secondsSpent: Optional[float] = None) -> Any:
        """Record a reviewer's decision on a submission."""
        params = {'verdict': verdict, 'comment': comment}
        if secondsSpent is not None:
            params['secondsSpent'] = secondsSpent
        return self._json('POST', protocol.path(protocol.REVIEW_VERDICT,
                                                submission_id=submissionId),
                          params=params)

    def downloadReviewFile(self, submissionId: str, what: str, destPath: str,
                           progress: Progress = None) -> int:
        """Fetch a reviewer's copy of the submission (``download``) or the
        source volume (``volume``).

        ``destPath`` has to carry the *right* extension. Slicer picks its reader
        from the name, so a gzipped NIfTI written as ``volume.nrrd`` downloads
        cleanly, verifies cleanly and then refuses to open -- which is what
        "review does not load" looked like before 0.9.0. The names travel with
        the submission row for exactly this; see ``_reviewPaths``."""
        return self._stream(
            protocol.path(protocol.REVIEW_FILE, submission_id=submissionId, what=what),
            destPath, progress=progress)
