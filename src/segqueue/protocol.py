"""The wire contract between the Slicer extension and the Girder plugin.

One file, imported by both sides, so that a route or a field name cannot drift
out of agreement without a test noticing. Everything is plain dicts and JSON --
no Girder types leak into the client, no Qt types leak into the server.

Two conventions carry the compatibility story:

* **Readers ignore unknown keys.** Every ``from_dict`` here takes what it
  recognises and leaves the rest, exactly as ``segtrain.events`` does for event
  kinds. Adding a field to a response therefore never breaks an older client.
* **Removing or repurposing a field bumps** ``PROTOCOL_VERSION``. The server
  refuses clients below ``MIN_CLIENT_PROTOCOL`` with a message telling the
  student how to update, which is the only reliable way to stop a stale
  extension writing subtly wrong data for a month before anyone looks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from . import PROTOCOL_VERSION

#: Mounted under Girder's own API root, so the full URL is
#: ``https://host/api/v1/segqueue/...``.
API_PREFIX = "segqueue"

#: Oldest client protocol this server will still talk to. Kept equal to
#: ``PROTOCOL_VERSION`` until there is a real reason to support two.
MIN_CLIENT_PROTOCOL = 1

#: Header the client sends on every request; the server checks it once, in a
#: single place, rather than each endpoint re-deriving compatibility.
CLIENT_VERSION_HEADER = "X-SegQueue-Client"
PROTOCOL_HEADER = "X-SegQueue-Protocol"

# ------------------------------------------------------------------ endpoints

NEXT = "next"
MINE = "mine"
CASE_DOWNLOAD = "case/{case_id}/download"
#: Optional extras that ship with a case: the heart-region mask used to frame
#: the view and confine editing, and a pre-existing coronary lumen mask used as
#: a starting point. Neither is ever submitted back.
CASE_ASSET = "case/{case_id}/asset/{kind}"
CASE_SUBMIT = "assignment/{assignment_id}/submit"
CASE_RELEASE = "assignment/{assignment_id}/release"
HEARTBEAT = "assignment/{assignment_id}/heartbeat"
PROJECT = "project"
REVIEW_QUEUE = "review/queue"
REVIEW_CLAIM = "review/{submission_id}/claim"
REVIEW_VERDICT = "review/{submission_id}/verdict"
STATS = "stats"


def path(template: str, **kwargs: Any) -> str:
    """Render an endpoint template into an API-root-relative path.

    Client code calls ``path(protocol.CASE_SUBMIT, assignment_id=...)`` instead
    of formatting strings inline, so a renamed route is a one-line change here
    and an immediate ``KeyError`` anywhere that missed it.
    """
    return f"{API_PREFIX}/{template.format(**kwargs)}"


# -------------------------------------------------------------- error codes

#: Returned with HTTP 409 when the annotator already holds their limit.
ERR_AT_LIMIT = "at_limit"
#: HTTP 404 from /next: the pool is genuinely empty for this user right now.
ERR_QUEUE_EMPTY = "queue_empty"
#: HTTP 409: this assignment moved on (submitted twice, released elsewhere).
ERR_BAD_STATE = "bad_state"
#: HTTP 400: uploaded bytes did not match the declared checksum.
ERR_CHECKSUM = "checksum_mismatch"
#: HTTP 426: client too old. The response carries ``minProtocol``.
ERR_CLIENT_TOO_OLD = "client_too_old"
#: HTTP 403: the annotator has used up an admin-set quota.
ERR_QUOTA = "quota_exhausted"
#: HTTP 404: the case has no asset of the requested kind. Normal, not a fault --
#: most cases have no coronary seed.
ERR_NO_ASSET = "no_such_asset"

# --------------------------------------------------------- case asset kinds

#: A whole-heart (or chamber) mask from the source dataset.
ASSET_REGION = "region"
#: A pre-existing binary coronary lumen mask from the source dataset.
ASSET_SEED = "seed"
ASSET_KINDS = (ASSET_REGION, ASSET_SEED)

#: Names the extension gives the two helper segments in the scene. They are
#: prefixed so they sort together, read as scaffolding rather than anatomy, and
#: cannot collide with a project segment name -- the submission export copies
#: only the project's own segments, so anything named here is structurally
#: incapable of reaching the server.
SEED_SEGMENT_NAME = "~ coronary seed (not submitted)"
REGION_SEGMENT_NAME = "~ heart region (not submitted)"


class ProtocolError(RuntimeError):
    """A structured server refusal, re-raised client-side with its code intact."""

    def __init__(self, code: str, message: str, detail: Optional[dict] = None) -> None:
        self.code = code
        self.detail = detail or {}
        super().__init__(message)


def error_body(code: str, message: str, **detail: Any) -> dict:
    """The JSON body every refusal uses. Girder's own errors pass through as-is."""
    body = {"segqueueError": code, "message": message}
    body.update(detail)
    return body


def parse_error(body: Any) -> Optional[ProtocolError]:
    """Recover a ``ProtocolError`` from a response body, or None if it is not one.

    Girder wraps a ``RestException``'s structured payload in an ``extra`` key and
    keeps ``message`` at the top level, so a refusal arrives as
    ``{"message": ..., "type": "rest", "extra": {"segqueueError": ...}}``. Both
    shapes are accepted: the nested one because that is what the server actually
    emits, the flat one because it is what a hand-written test or a future
    non-Girder backend would produce.
    """
    if not isinstance(body, dict):
        return None
    payload = body
    if "segqueueError" not in payload:
        extra = body.get("extra")
        if not isinstance(extra, dict) or "segqueueError" not in extra:
            return None
        payload = extra
    detail = {k: v for k, v in payload.items() if k not in ("segqueueError", "message")}
    message = payload.get("message") or body.get("message") or ""
    return ProtocolError(payload["segqueueError"], message, detail)


# ------------------------------------------------------- the labelling protocol


@dataclass(frozen=True)
class SegmentSpec:
    """One structure the annotator is asked to draw.

    The server owns this list, and the extension creates exactly these segments
    -- with these names, these label values and these colours -- before the
    annotator touches anything. That is the whole answer to protocol drift
    across thirty people: there is no free-text segment name to get wrong, and
    the label values written into the ``.seg.nrrd`` are the same ones
    ``segtrain convert`` will later expect.
    """

    name: str
    #: Integer written into the label map. Must match the task's label config.
    label: int
    #: 0-1 RGB, matching Slicer's convention.
    color: tuple = (1.0, 0.0, 0.0)
    #: A segment that may legitimately be empty -- a vessel outside the field of
    #: view, say. Empty *required* segments block submission.
    required: bool = True
    #: Shown in the extension as a tooltip. Short: it competes with the image.
    hint: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "color": list(self.color),
            "required": self.required,
            "hint": self.hint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SegmentSpec:
        color = data.get("color") or [1.0, 0.0, 0.0]
        return cls(
            name=data["name"],
            label=int(data["label"]),
            color=tuple(float(c) for c in color[:3]),
            required=bool(data.get("required", True)),
            hint=data.get("hint", "") or "",
        )


@dataclass
class ProjectConfig:
    """What the extension needs to set a case up correctly, fetched once at login.

    Sent by the server rather than shipped in the extension so that adding a
    structure mid-project, or rewording the instructions, does not require
    thirty students to reinstall anything.
    """

    name: str = ""
    #: Markdown shown in the extension panel above the segment list.
    instructions: str = ""
    segments: list = field(default_factory=list)
    #: Concurrent cases this annotator may hold, already resolved server-side
    #: from the policy and any per-user override.
    max_concurrent: int = 1
    #: Remaining quota for this user, or None for uncapped.
    quota_remaining: Optional[int] = None
    #: Girder folder the client uploads finished segmentations into, before
    #: calling /submit. Sent by the server rather than configured in the client
    #: because it is a deployment detail the extension has no way to guess.
    upload_folder_id: str = ""
    protocol_version: int = PROTOCOL_VERSION

    def required_segments(self) -> list:
        return [s for s in self.segments if s.required]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "instructions": self.instructions,
            "segments": [s.to_dict() for s in self.segments],
            "maxConcurrent": self.max_concurrent,
            "quotaRemaining": self.quota_remaining,
            "uploadFolderId": self.upload_folder_id,
            "protocolVersion": self.protocol_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectConfig:
        return cls(
            name=data.get("name", ""),
            instructions=data.get("instructions", ""),
            segments=[SegmentSpec.from_dict(s) for s in data.get("segments", [])],
            max_concurrent=int(data.get("maxConcurrent", 1)),
            quota_remaining=data.get("quotaRemaining"),
            upload_folder_id=str(data.get("uploadFolderId", "") or ""),
            protocol_version=int(data.get("protocolVersion", PROTOCOL_VERSION)),
        )


# ------------------------------------------------------------------ responses


@dataclass
class AssignmentInfo:
    """One row of the annotator's queue: the case plus their standing in it."""

    assignment_id: str = ""
    case_id: str = ""
    #: Human-facing case label. Deliberately not the patient identifier -- see
    #: the de-identification note in the README.
    case_name: str = ""
    state: str = ""
    attempt: int = 1
    #: Bytes of the source volume, so the client can show a real progress bar
    #: and refuse to start on a full disk.
    size_bytes: int = 0
    #: Lowercase hex SHA-256 of the source volume, verified after download.
    checksum: str = ""
    #: The volume's filename on the server, e.g. ``s0004.nii.gz``. Sent because
    #: the client has to name the local copy *before* downloading it -- to know
    #: whether it is already cached -- and because Slicer picks its reader from
    #: the extension. A gzipped NIfTI saved as ``.nrrd`` transfers and verifies
    #: perfectly, then refuses to open.
    volume_name: str = ""
    #: Unix timestamps; None where the step has not happened.
    assigned_at: Optional[float] = None
    deadline: Optional[float] = None
    #: Populated only when ``state`` is ``rejected``: what to fix.
    reviewer_comment: str = ""
    #: Server-side flavour (normal/gold/duplicate). Present in admin responses
    #: and *absent* from anything an annotator sees -- blind means blind.
    kind: Optional[str] = None
    #: The case ships a heart-region mask. The extension uses it to frame the
    #: view and, optionally, to keep edits inside the heart.
    has_region: bool = False
    #: The case ships a pre-existing binary coronary mask. The extension loads
    #: it as a helper segment so the annotator splits a tree rather than drawing
    #: one. Safe to expose: it says nothing about gold or duplicate status,
    #: because it is a property of the source data, not of the assignment.
    has_seed: bool = False

    def to_dict(self) -> dict:
        data = {
            "assignmentId": self.assignment_id,
            "caseId": self.case_id,
            "caseName": self.case_name,
            "state": self.state,
            "attempt": self.attempt,
            "sizeBytes": self.size_bytes,
            "checksum": self.checksum,
            "volumeName": self.volume_name,
            "assignedAt": self.assigned_at,
            "deadline": self.deadline,
            "reviewerComment": self.reviewer_comment,
            "hasRegion": self.has_region,
            "hasSeed": self.has_seed,
        }
        if self.kind is not None:
            data["kind"] = self.kind
        return data

    @classmethod
    def from_dict(cls, data: dict) -> AssignmentInfo:
        return cls(
            assignment_id=str(data.get("assignmentId", "")),
            case_id=str(data.get("caseId", "")),
            case_name=data.get("caseName", "") or "",
            state=data.get("state", "") or "",
            attempt=int(data.get("attempt", 1)),
            size_bytes=int(data.get("sizeBytes", 0)),
            checksum=data.get("checksum", "") or "",
            volume_name=data.get("volumeName", "") or "",
            assigned_at=data.get("assignedAt"),
            deadline=data.get("deadline"),
            reviewer_comment=data.get("reviewerComment", "") or "",
            kind=data.get("kind"),
            has_region=bool(data.get("hasRegion", False)),
            has_seed=bool(data.get("hasSeed", False)),
        )


@dataclass
class SubmissionMeta:
    """What the client reports about a segmentation besides the file itself.

    The per-segment voxel counts are computed client-side because the client
    already has the array in memory, and shipping them turns the dashboard's
    "is this plausible?" queries into ordinary Mongo aggregations instead of a
    job that reopens every volume. The server still recomputes them for gold and
    duplicate cases, where the number decides something -- a client-supplied
    number is a hint, never evidence.
    """

    checksum: str = ""
    size_bytes: int = 0
    #: Wall-clock seconds the annotator spent with the case open. The single
    #: best predictor of careless work when it is implausibly small.
    annotation_seconds: float = 0.0
    #: ``{segment name: voxel count}``.
    voxel_counts: dict = field(default_factory=dict)
    slicer_version: str = ""
    extension_version: str = ""
    #: Free-text note from the annotator: "RCA is barely opacified distally".
    annotator_note: str = ""

    def to_dict(self) -> dict:
        return {
            "checksum": self.checksum,
            "sizeBytes": self.size_bytes,
            "annotationSeconds": self.annotation_seconds,
            "voxelCounts": self.voxel_counts,
            "slicerVersion": self.slicer_version,
            "extensionVersion": self.extension_version,
            "annotatorNote": self.annotator_note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SubmissionMeta:
        return cls(
            checksum=data.get("checksum", "") or "",
            size_bytes=int(data.get("sizeBytes", 0)),
            annotation_seconds=float(data.get("annotationSeconds", 0.0)),
            voxel_counts=dict(data.get("voxelCounts") or {}),
            slicer_version=data.get("slicerVersion", "") or "",
            extension_version=data.get("extensionVersion", "") or "",
            annotator_note=data.get("annotatorNote", "") or "",
        )


def check_client_protocol(client_protocol: Optional[int]) -> None:
    """Raise ``ProtocolError`` if a client is too old to be allowed to write.

    A missing header is treated as protocol 1: the first release did not send
    one, and refusing it would strand exactly the users this check protects.
    """
    version = PROTOCOL_VERSION if client_protocol is None else int(client_protocol)
    if version < MIN_CLIENT_PROTOCOL:
        raise ProtocolError(
            ERR_CLIENT_TOO_OLD,
            "This SegQueue extension is too old for the server (needs protocol "
            f"{MIN_CLIENT_PROTOCOL}, sent {version}). Reinstall the extension from "
            "the lab repository.",
            {"minProtocol": MIN_CLIENT_PROTOCOL, "serverProtocol": PROTOCOL_VERSION},
        )
