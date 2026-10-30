"""The wire contract between a Janus-M read client and the ``janusm`` Girder plugin.

Shaped like ``segqueue14.protocol`` but shares no name, path, header or number with
it, so the two can never be confused in a log or at a proxy:

* every route is ``/api/v1/janusm/...``;
* the protocol version is :data:`janusm_reads.PROTOCOL_VERSION` (2), on its own
  number line; a missing or older version is refused (426), at ``next`` before any
  case is claimed;
* one asset only, the **seed** (JA7: ``heartchambers_highres`` coarsened to 2 mm and
  smoothed). A blank case has none, and says so (``hasSeed: false``);
* the other read of a case is never served to a reader: reads are independent;
* a read carries a **read form** (JA46 (d), JA67): the CAD-RADS 2.0 grade of each
  main coronary's worst lesion (LM: 0, 1, 2, 4B, 5, N; LAD, LCx, RCA: 0, 1, 2, 3, 4A,
  5, N) and, optionally, a lesion point inside the CT. The server keeps it for the
  export only; it is never shown to another reader;
* a read the check fails is **returned once**; a second failure is accepted and
  **flagged**, with its reasons (Hotel v3 section 5.1 item 7). A returned read
  carries the half-maximum profiles, so the reader can see why.

The **border protocol** (:data:`janusm_reads.BORDER_PROTOCOL`, the reading rules) is
a separate number from the wire version, recorded in every read as
``border_protocol``.

Stdlib only, Python 3.9.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

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
ADMIN_THIRD_READS = "admin/third-reads"
ADMIN_WAVE = "admin/wave"


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
ERR_READ_FORM = "janusm_read_form"
#: JA77: lesion points sent, but the CT's world box could not be read (409; the read
#: stays open and unchanged).
ERR_CT_BOUNDS = "ct_bounds_unavailable"
#: JA78: a case that has been read never changes wave (409, all or none).
ERR_WAVE_FROZEN = "janusm_wave_frozen"
#: JA78: an anchoring report the server cannot accept for a wave (400).
ERR_BAD_REPORT = "janusm_bad_anchoring_report"

# ---------------------------------------------------------------- read form
# JA46 (d): per vessel, the CAD-RADS 2.0 grade of the worst lesion, and an optional
# lesion point in world millimetres (RAS, as Slicer and NIfTI give them).

#: The vessels graded, in the order a form shows them: left main, left anterior
#: descending, left circumflex, right coronary artery (each with its branches).
VESSELS = ("LM", "LAD", "LCx", "RCA")
#: CAD-RADS 2.0 categories (Cury et al., 2022); N = non-diagnostic.
CADRADS_GRADES = ("0", "1", "2", "3", "4A", "4B", "5", "N")
#: JA67: the grades each row allows. LM >= 50 % is 4B in CAD-RADS 2.0, so 3 and 4A are
#: not LM grades; on LAD, LCx and RCA 4B is patient-level, so it is not offered.
VESSEL_GRADES: Dict[str, tuple] = {
    "LM": ("0", "1", "2", "4B", "5", "N"),
    "LAD": ("0", "1", "2", "3", "4A", "5", "N"),
    "LCx": ("0", "1", "2", "3", "4A", "5", "N"),
    "RCA": ("0", "1", "2", "3", "4A", "5", "N"),
}
#: Grades that name a lesion, so a lesion point may be given (1-5; never 0 or N).
LESION_GRADES = frozenset({"1", "2", "3", "4A", "4B", "5"})


def grades_for(vessel: str) -> tuple:
    """The CAD-RADS 2.0 grades the read form offers on ``vessel``'s row (JA67)."""
    return VESSEL_GRADES[vessel]

#: A read the check fails is returned this many times; the next failure is accepted
#: and flagged (Hotel v3 section 5.1 item 7).
MAX_RETURNS = 1


def read_form_problems(cadrads: Dict[str, str],
                       lesion_points: Optional[Dict[str, Sequence[float]]] = None) -> List[str]:
    """What is wrong with a read form, in words; empty when it is complete."""
    out = []
    cadrads = cadrads or {}
    missing = [v for v in VESSELS if not cadrads.get(v)]
    if missing:
        out.append("Grade every vessel (CAD-RADS 2.0, worst lesion): {} not graded."
                   .format(", ".join(missing)))
    for vessel, grade in cadrads.items():
        if vessel not in VESSELS:
            out.append("{!r} is not a graded vessel ({}).".format(vessel, ", ".join(VESSELS)))
        elif grade and grade not in CADRADS_GRADES:
            out.append("{}: {!r} is not a CAD-RADS 2.0 grade ({}).".format(
                vessel, grade, ", ".join(CADRADS_GRADES)))
        elif grade and grade not in VESSEL_GRADES[vessel]:
            out.append("{}: {!r} is not a grade on this vessel ({}).".format(
                vessel, grade, ", ".join(VESSEL_GRADES[vessel])))
    for vessel, point in (lesion_points or {}).items():
        if vessel not in VESSELS:
            out.append(f"A lesion point names {vessel!r}, which is not a graded vessel.")
            continue
        try:
            ok = len(point) == 3 and all(abs(float(c)) < 1e5 for c in point)
        except (TypeError, ValueError):
            ok = False
        if not ok:
            out.append(f"{vessel}: a lesion point is three numbers in mm.")
        elif cadrads.get(vessel) not in LESION_GRADES:
            out.append("{}: a lesion point needs a grade that names a lesion (1-5; not 0 "
                       "or N), not {!r}.".format(vessel, cadrads.get(vessel) or "none"))
    return out


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


# ------------------------------------------------------------------- timing
# PS3-S11 (JA58): every read records when it was claimed and when it was submitted,
# in UTC, server-side. The export writes the time between them with no identifier.
#
# * ``claimed_at`` is set once, when the read is claimed, and never changes. A
#   returned read that is resubmitted keeps it; a released read is finished, and a new
#   claim is a new read with its own ``claimed_at``.
# * ``submitted_at`` is the first submission, set once.
# * ``submitted_at_attempts`` lists every submission's time, first to last, so a
#   returned read's later attempts are recorded too.
#
# These are server records only: they are not in :class:`ReadInfo`, and the wire
# protocol is unchanged.

CLAIMED_AT = "claimed_at"
SUBMITTED_AT = "submitted_at"
SUBMITTED_AT_ATTEMPTS = "submitted_at_attempts"


def as_utc(when: Any) -> Optional[datetime.datetime]:
    """``when`` as an aware UTC datetime, or None. A naive datetime is UTC (pymongo
    returns stored datetimes naive, in UTC); an ISO 8601 string is parsed."""
    if when is None or when == "":
        return None
    if isinstance(when, str):
        try:
            when = datetime.datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(when, datetime.datetime):
        return None
    if when.tzinfo is None:
        return when.replace(tzinfo=datetime.timezone.utc)
    return when.astimezone(datetime.timezone.utc)


def seconds_between(claimed: Any, submitted: Any) -> Optional[float]:
    """Seconds from ``claimed`` to ``submitted``; None if either is missing or the
    second is before the first."""
    start, end = as_utc(claimed), as_utc(submitted)
    if start is None or end is None or end < start:
        return None
    return (end - start).total_seconds()


def read_timing(read: dict) -> Optional[Dict[str, Any]]:
    """One read's timing, with no identifier: seconds from claim to first submission,
    and from claim to each submission. None for a read with no ``claimed_at`` or no
    submission (stored before PS3-S11, or never submitted)."""
    first = seconds_between(read.get(CLAIMED_AT), read.get(SUBMITTED_AT))
    if first is None:
        return None
    attempts = [seconds_between(read.get(CLAIMED_AT), at)
                for at in (read.get(SUBMITTED_AT_ATTEMPTS) or [])]
    return {"secondsToSubmit": first,
            "secondsToEachSubmission": [s for s in attempts if s is not None]}


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
    #: Accepted after a second failed check (return once, then accept and flag).
    flagged: bool = False
    #: On a returned read: the half-maximum profile of each border, as the check
    #: measured it -- ``{border: {"s_mm": [...], "hu": [...], "thresholdHU": t,
    #: "plateausHU": [inside, outside], "offsetMm": o, "failed": bool}}``.
    check_profile: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"readId": self.read_id, "caseName": self.case_name, "state": self.state,
                "hasSeed": self.has_seed, "checksum": self.checksum,
                "sizeBytes": self.size_bytes, "checkSummary": self.check_summary,
                "flagged": self.flagged, "checkProfile": dict(self.check_profile)}

    @classmethod
    def from_dict(cls, data: dict) -> ReadInfo:
        profile = data.get("checkProfile")
        return cls(read_id=str(data["readId"]), case_name=str(data.get("caseName", "")),
                   state=str(data.get("state", "")), has_seed=bool(data.get("hasSeed")),
                   checksum=str(data.get("checksum", "") or ""),
                   size_bytes=int(data.get("sizeBytes", 0) or 0),
                   check_summary=str(data.get("checkSummary", "") or ""),
                   flagged=bool(data.get("flagged")),
                   check_profile=dict(profile) if isinstance(profile, dict) else {})


def profile_for_reader(check: Optional[dict]) -> Dict[str, Any]:
    """The half-maximum profiles of a check report (``CheckReport.to_dict()``), in the
    shape :attr:`ReadInfo.check_profile` carries. Only the image and the reader's own
    read went into them."""
    out: Dict[str, Any] = {}
    for name, border in ((check or {}).get("borders") or {}).items():
        prof = border.get("profile") or {}
        if not prof.get("s_mm"):
            continue
        offset = border.get("offset_mm")
        tol = ((check or {}).get("config") or {}).get("tolerance_mm")
        out[name] = {"s_mm": list(prof["s_mm"]), "hu": list(prof["hu"]),
                     "thresholdHU": border.get("threshold_hu"),
                     "plateausHU": list(border.get("plateaus_hu") or []),
                     "offsetMm": offset,
                     "failed": bool(offset is not None and tol is not None
                                    and abs(offset) > tol)}
    return out


@dataclass
class ReadSubmission:
    """What a client declares with an uploaded read."""

    checksum: str
    size_bytes: int
    voxel_counts: Dict[str, int] = field(default_factory=dict)
    seconds: float = 0.0
    client_version: str = ""
    note: str = ""
    #: The read form (JA46 (d)): vessel -> CAD-RADS 2.0 grade of its worst lesion.
    cadrads: Dict[str, str] = field(default_factory=dict)
    #: Optional: vessel -> the worst lesion's point, world mm (RAS).
    lesion_points: Dict[str, List[float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"checksum": self.checksum, "sizeBytes": self.size_bytes,
                "voxelCounts": dict(self.voxel_counts), "seconds": self.seconds,
                "clientVersion": self.client_version, "note": self.note,
                "cadrads": dict(self.cadrads),
                "lesionPoints": {k: list(v) for k, v in self.lesion_points.items()}}

    def form_problems(self) -> List[str]:
        return read_form_problems(self.cadrads, self.lesion_points)

    @classmethod
    def from_dict(cls, data: dict) -> ReadSubmission:
        # Unknown keys are ignored, so a newer client still talks to this server.
        points = {}
        for k, v in (data.get("lesionPoints") or {}).items():
            try:
                points[str(k)] = [float(c) for c in v]
            except (TypeError, ValueError):
                points[str(k)] = []
        return cls(checksum=str(data.get("checksum", "") or "").lower(),
                   size_bytes=int(data.get("sizeBytes", 0) or 0),
                   voxel_counts={str(k): int(v) for k, v in
                                 (data.get("voxelCounts") or {}).items()},
                   seconds=float(data.get("seconds", 0.0) or 0.0),
                   client_version=str(data.get("clientVersion", "") or ""),
                   note=str(data.get("note", "") or "")[:2000],
                   cadrads={str(k): str(v).strip().upper() for k, v in
                            (data.get("cadrads") or {}).items() if v is not None},
                   lesion_points=points)


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
    """Raise :class:`ProtocolError` unless the client speaks a version this server knows
    (:data:`MIN_CLIENT_PROTOCOL` .. :data:`PROTOCOL_VERSION`).

    A version above the server's is refused too: no Janus-M client is newer than its
    server, and a SegQueue or SegQueue14 module sending its own number (14, 16) must
    not pass for a Janus-M client.
    """
    try:
        version = None if client_protocol in (None, "") else int(client_protocol)
    except (TypeError, ValueError):
        version = None
    if version is None or not MIN_CLIENT_PROTOCOL <= version <= PROTOCOL_VERSION:
        shown = "nothing" if version is None else str(version)
        raise ProtocolError(
            ERR_CLIENT_TOO_OLD,
            f"This client does not speak the Janus-M read protocol: the server speaks "
            f"{PROTOCOL_NAME} {PROTOCOL_VERSION} and the client sent {shown}. "
            "A SegQueue or SegQueue14 module cannot read Janus-M cases.",
            {"minProtocol": MIN_CLIENT_PROTOCOL, "serverProtocol": PROTOCOL_VERSION})
