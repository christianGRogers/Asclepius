"""The wire contract between a Janus-M read client and the ``janusm`` Girder plugin.

Shaped like ``segqueue14.protocol`` but shares no name, path, header or number with
it, so the two can never be confused in a log or at a proxy:

* every route is ``/api/v1/janusm/...``;
* the protocol version is :data:`janusm_reads.PROTOCOL_VERSION` (1), on its own
  number line; a missing or older version is refused (426);
* one asset only, the **seed** (JA7: ``heartchambers_highres`` coarsened to 2 mm and
  smoothed). A blank case has none, and says so (``hasSeed: false``);
* the other read of a case is never served to a reader: reads are independent.

Stdlib only, Python 3.9.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import PROTOCOL_NAME, PROTOCOL_VERSION

API_PREFIX = "janusm"
MIN_CLIENT_PROTOCOL = PROTOCOL_VERSION

CLIENT_VERSION_HEADER = "X-JanusM-Client"
PROTOCOL_HEADER = "X-JanusM-Protocol"

# ------------------------------------------------------------------ endpoints

PROJECT = "project"
MINE = "mine"
NEXT = "next"
CASE_DOWNLOAD = "read/{read_id}/ct"
CASE_SEED = "read/{read_id}/seed"
SUBMIT = "read/{read_id}/submit"
RELEASE = "read/{read_id}/release"
# Admin
ADMIN_CASES = "admin/cases"
ADMIN_READS = "admin/case/{case_id}/reads"
ADMIN_OPEN_SEAL = "admin/seal/open"
ADMIN_CHECK = "admin/read/{read_id}/check"


def path(template: str, **kwargs: Any) -> str:
    return f"{API_PREFIX}/{template.format(**kwargs)}"


# -------------------------------------------------------------- error codes

ERR_CLIENT_TOO_OLD = "janusm_client_too_old"
ERR_NOT_A_READER = "not_a_janusm_reader"
ERR_QUEUE_EMPTY = "janusm_queue_empty"
ERR_AT_LIMIT = "janusm_at_limit"
ERR_NOT_YOURS = "not_your_read"
ERR_BAD_STATE = "janusm_bad_state"
ERR_NO_SEED = "janusm_no_seed"
ERR_CHECKSUM = "janusm_checksum_mismatch"
ERR_MISSING_CLASS = "janusm_missing_class"
ERR_HOLDOUT = "janusm_coronary_holdout"

# ------------------------------------------------------------------- states
# A read is one reader's slot on one case. Deliberately smaller than SegQueue's
# state machine: there is no gold, no sampled review and no duplicate roll.

ASSIGNED = "assigned"      # claimed, not yet submitted
SUBMITTED = "submitted"    # uploaded; waiting for the automatic check
RETURNED = "returned"      # the check failed; back with the reader to fix
ACCEPTED = "accepted"      # passed the check; a reference read
RELEASED = "released"      # given back; the slot is free again

OPEN_STATES = frozenset({ASSIGNED, RETURNED})
ALL_STATES = frozenset({ASSIGNED, SUBMITTED, RETURNED, ACCEPTED, RELEASED})

#: state -> states it may move to.
TRANSITIONS: Dict[str, frozenset] = {
    ASSIGNED: frozenset({SUBMITTED, RELEASED}),
    RETURNED: frozenset({SUBMITTED, RELEASED}),
    SUBMITTED: frozenset({ACCEPTED, RETURNED}),
    ACCEPTED: frozenset(),
    RELEASED: frozenset(),
}


def can_move(state: str, to: str) -> bool:
    return to in TRANSITIONS.get(state, frozenset())


# ---------------------------------------------------------------- responses


@dataclass
class ReadInfo:
    """A reader's view of one of their reads. Never names the read set or the
    other reader: a reader who knows a case is in the seal reads it differently."""

    read_id: str
    case_name: str
    state: str
    has_seed: bool
    checksum: str = ""
    size_bytes: int = 0
    check_summary: str = ""

    def to_dict(self) -> dict:
        return {"readId": self.read_id, "caseName": self.case_name, "state": self.state,
                "hasSeed": self.has_seed, "checksum": self.checksum,
                "sizeBytes": self.size_bytes, "checkSummary": self.check_summary}

    @classmethod
    def from_dict(cls, data: dict) -> ReadInfo:
        return cls(read_id=str(data["readId"]), case_name=str(data.get("caseName", "")),
                   state=str(data.get("state", "")), has_seed=bool(data.get("hasSeed")),
                   checksum=str(data.get("checksum", "") or ""),
                   size_bytes=int(data.get("sizeBytes", 0) or 0),
                   check_summary=str(data.get("checkSummary", "") or ""))


@dataclass
class ReadSubmission:
    """What a client declares with an uploaded read."""

    checksum: str
    size_bytes: int
    voxel_counts: Dict[str, int] = field(default_factory=dict)
    seconds: float = 0.0
    client_version: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {"checksum": self.checksum, "sizeBytes": self.size_bytes,
                "voxelCounts": dict(self.voxel_counts), "seconds": self.seconds,
                "clientVersion": self.client_version, "note": self.note}

    @classmethod
    def from_dict(cls, data: dict) -> ReadSubmission:
        # Unknown keys are ignored, so a newer client still talks to this server.
        return cls(checksum=str(data.get("checksum", "") or "").lower(),
                   size_bytes=int(data.get("sizeBytes", 0) or 0),
                   voxel_counts={str(k): int(v) for k, v in
                                 (data.get("voxelCounts") or {}).items()},
                   seconds=float(data.get("seconds", 0.0) or 0.0),
                   client_version=str(data.get("clientVersion", "") or ""),
                   note=str(data.get("note", "") or "")[:2000])


def error_body(code: str, message: str, **detail: Any) -> dict:
    body = {"protocol": PROTOCOL_NAME, "code": code, "message": message}
    if detail:
        body["detail"] = detail
    return body


class ProtocolError(Exception):
    def __init__(self, code: str, message: str, detail: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}


def check_client_protocol(client_protocol: Optional[Any]) -> None:
    """Raise :class:`ProtocolError` unless the client speaks this protocol or newer."""
    try:
        version = None if client_protocol in (None, "") else int(client_protocol)
    except (TypeError, ValueError):
        version = None
    if version is None or version < MIN_CLIENT_PROTOCOL:
        shown = "nothing" if version is None else str(version)
        raise ProtocolError(
            ERR_CLIENT_TOO_OLD,
            f"This client is too old for the Janus-M read server: the server speaks "
            f"{PROTOCOL_NAME} protocol {PROTOCOL_VERSION} and the client sent {shown}. "
            "A SegQueue or SegQueue14 module cannot read Janus-M cases.",
            {"minProtocol": MIN_CLIENT_PROTOCOL, "serverProtocol": PROTOCOL_VERSION})
