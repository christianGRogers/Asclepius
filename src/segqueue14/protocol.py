"""The wire contract between the SegQueue14 Slicer module and its Girder plugin.

The same shapes as ``segqueue.protocol`` -- and most of the dataclasses are
reused from there unchanged -- with these differences, which are the point of
having a separate contract:

* **A separate prefix.** Every route is ``/api/v1/segqueue14/...``, so the two
  plugins load in one Girder without a single shared path.
* **A separate protocol version** (``segqueue14.PROTOCOL_VERSION``), checked on
  every write. Unlike the live check a *missing* version is refused too: a client
  that does not say what it speaks is not one that was written for this server.
  Protocol 17 (module 0.17.x) is still accepted (D44, #280): it speaks the four
  classes and is refused only on a read with extended classes
  (``check_extended_reader``), which it would save back with four.
* **A ``prelabel`` asset** instead of the live binary coronary ``seed`` (D8, D25):
  a model's prediction in the project's classes, loaded straight into the
  project segments.
* **A ``seed`` asset of its own** (D23): for the pooled new datasets, an
  automatic *binary* vessel mask (TotalSegmentator ``coronary_arteries``) that the
  annotator divides into the four classes (D25). It is a helper segment, like the heart
  region, and is structurally unable to reach a submission.
* **A ``labelFormat``** on submit and revise (protocol 17, D39): what the
  uploaded file is. ``class-stack-nrrd/1`` keeps every class whole, overlaps
  included; a submission without one is an old single label volume
  (``labelmap``), which stays readable everywhere.
* **``missing_required``** -- D13's old submit refusal. No longer raised since
  #270 (project lead, 2026-11-02); the code is kept so an older module still
  recognises it.

Stdlib only, Python 3.9, like the rest of the shared code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# Re-exported so the Slicer module can treat this module as "the protocol" and
# never reach into the live one for a name.
from segqueue.protocol import (  # noqa: F401
    ERR_AT_LIMIT,
    ERR_BAD_STATE,
    ERR_CHECKSUM,
    ERR_CLIENT_TOO_OLD,
    ERR_NO_ASSET,
    ERR_NOT_YOUR_CASE,
    ERR_QUEUE_EMPTY,
    ERR_QUOTA,
    NOTE_MAX_CHARS,
    NOTE_PAGE_SIZE,
    AssignmentInfo,
    CaseNote,
    ProjectConfig,
    ProtocolError,
    SegmentSpec,
    SubmissionMeta,
    clean_note,
    error_body,
    parse_error,
)

from . import PROTOCOL_VERSION
from .labelfile import FORMAT_CLASS_STACK as LABEL_FORMAT_CLASS_STACK  # noqa: F401
from .labelfile import FORMAT_LABELMAP as LABEL_FORMAT_LABELMAP
from .labelfile import FORMATS as LABEL_FORMATS

#: ``https://host/api/v1/segqueue14/...``.
API_PREFIX = "segqueue14"

#: Oldest SegQueue14 client protocol the server accepts. 17 (0.17.x) keeps
#: working after protocol 18 (D44): it speaks the four classes only.
MIN_CLIENT_PROTOCOL = 17

#: The first protocol that knows the 17 extended classes (D44). A reviewer on an
#: older module is refused a read that has them (``check_extended_reader``).
EXTENDED_CLASSES_PROTOCOL = 18

#: The first protocol that opens a reopened case from the annotator's own read
#: (#315). An older module is refused such a case (``check_reopen_reader``).
REOPEN_PROTOCOL = 19

#: Headers. Distinct from the live ones so a proxy log says which module spoke.
CLIENT_VERSION_HEADER = "X-SegQueue14-Client"
PROTOCOL_HEADER = "X-SegQueue14-Protocol"

# ------------------------------------------------------------------ endpoints
# Same templates as the live protocol; only the prefix differs.

NEXT = "next"
MINE = "mine"
PROJECT = "project"
CASE_DOWNLOAD = "case/{case_id}/download"
CASE_ASSET = "case/{case_id}/asset/{kind}"
CASE_NOTES = "case/{case_id}/notes"
CASE_SUBMIT = "assignment/{assignment_id}/submit"
CASE_RELEASE = "assignment/{assignment_id}/release"
HEARTBEAT = "assignment/{assignment_id}/heartbeat"
REVIEW_QUEUE = "review/queue"
REVIEW_CLAIM = "review/{submission_id}/claim"
REVIEW_VERDICT = "review/{submission_id}/verdict"
REVIEW_CASES = "review/cases"
REVIEW_CASE_SUBMISSIONS = "review/case/{case_id}/submissions"
REVIEW_REVISE = "review/{submission_id}/revise"
REVIEW_POOL = "review/{submission_id}/pool"
REVIEW_ANNOTATORS = "review/annotators"
REVIEW_ASSIGN = "review/case/{case_id}/assign"
REVIEW_CASE_VOLUME = "review/case/{case_id}/volume"
REVIEW_CASE_ASSET = "review/case/{case_id}/asset/{kind}"
REVIEW_FILE = "review/{submission_id}/{what}"
STATS = "stats"
PRELABELS_ATTACH = "prelabels/attach"
PRELABELS_STATUS = "prelabels/status"


def path(template: str, **kwargs: Any) -> str:
    """Render an endpoint template into an API-root-relative path."""
    return f"{API_PREFIX}/{template.format(**kwargs)}"


# -------------------------------------------------------------- error codes

#: HTTP 400 from /submit or /revise for a ``labelFormat`` this server cannot read.
ERR_BAD_LABEL_FORMAT = "bad_label_format"

#: Formerly HTTP 400 from /submit for an empty required class (D13); not raised since #270.
ERR_MISSING_REQUIRED = "missing_required"

#: HTTP 426 from a reviewer route when a module older than protocol 18 asks for a
#: read with extended classes (D44): it would show four and save back four.
ERR_UPDATE_TO_REVIEW = "update_to_review"

#: HTTP 426 from an annotator route when a module older than protocol 19 opens or
#: submits a case reopened for the annotator's own revision (#315).
ERR_UPDATE_TO_REVISE = "update_to_revise"

# --------------------------------------------------------- case asset kinds

#: The whole-heart mask from the source dataset, as in the live project. Still
#: shipped: it frames the view and never reaches a submission.
ASSET_REGION = "region"
#: A model's prediction (uint8, values 0..4, on the CT grid). Loaded
#: into the project's own segments, edited, and submitted -- unlike every other
#: asset it *is* the work, once corrected.
ASSET_PRELABEL = "prelabel"
#: A binary (0/1) vessel mask on the CT grid -- an automatic segmentation of the
#: coronary tree with no classes (D23). Shown beside the project segments as a
#: guide to divide into the four classes; never submitted.
ASSET_SEED = "seed"
#: The annotator's own submitted read (a class stack, D39), on a case reopened for
#: their revision (#315): the starting point in place of the prelabel or the seed.
#: Served only for that annotator's reopened assignment.
ASSET_OWN = "own"
#: What an annotator may fetch. The ImageCAS-X reference is deliberately absent:
#: an annotator who could download it could copy it.
ASSET_KINDS = (ASSET_REGION, ASSET_PRELABEL, ASSET_SEED, ASSET_OWN)
#: Reviewers may additionally fetch the ImageCAS-X reference for a case, to see
#: what a low reference score is measured against.
ASSET_REFERENCE = "reference"
REVIEW_ASSET_KINDS = (ASSET_REGION, ASSET_PRELABEL, ASSET_SEED, ASSET_REFERENCE)

#: The heart helper's segment name; prefixed so it cannot collide with a class.
REGION_SEGMENT_NAME = "~ heart region (not submitted)"
#: The binary vessel seed's segment name (D23); prefixed like the region's.
SEED_SEGMENT_NAME = "~ vessel seed (not submitted)"
REFERENCE_SEGMENT_PREFIX = "~ ImageCAS-X "


# ----------------------------------------------------------------- responses


@dataclass
class AssignmentInfo14(AssignmentInfo):
    """The live ``AssignmentInfo`` plus the prelabel the case ships.

    ``has_seed`` says the case ships a binary vessel seed (D23) -- never the live
    project's ImageCAS seed (D8), which SegQueue14 does not reference.
    ``prelabel_version`` is shown to the annotator only as provenance; it says
    nothing about whether the case is scored or duplicated -- blind stays blind.
    """

    has_prelabel: bool = False
    prelabel_version: str = ""
    #: Reopened for the annotator's own revision (#315): open it from the ``own``
    #: asset, their submitted read, instead of the prelabel or the seed.
    start_from_own: bool = False

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["hasPrelabel"] = self.has_prelabel
        data["prelabelVersion"] = self.prelabel_version
        data["startFromOwn"] = self.start_from_own
        return data

    @classmethod
    def from_dict(cls, data: dict) -> AssignmentInfo14:
        base = AssignmentInfo.from_dict(data)
        return cls(
            **{k: getattr(base, k) for k in base.__dataclass_fields__},
            has_prelabel=bool(data.get("hasPrelabel", False)),
            prelabel_version=str(data.get("prelabelVersion", "") or ""),
            start_from_own=bool(data.get("startFromOwn", False)),
        )


# ------------------------------------------------------------ version check


def too_old_message(sent: Optional[int]) -> str:
    """The 426 refusal text: what the server speaks, what the module sent, what to do."""
    shown = "nothing" if sent is None else str(sent)
    return ("This SegQueue14 module is too old for the server: the server speaks "
            f"SegQueue14 protocol {PROTOCOL_VERSION} and the module sent {shown}. "
            "Update the SegQueue14 module (install the latest SegQueue14 zip from "
            "the project lead and restart Slicer). If you are using the ordinary "
            "SegQueue module, switch to SegQueue14 for this project.")


def check_client_protocol(client_protocol: Optional[Any]) -> None:
    """Raise ``ProtocolError`` unless the client speaks ``MIN_CLIENT_PROTOCOL`` or newer.

    A missing or unparseable version is refused, unlike the live check: every
    SegQueue14 client ever released sends one. Protocol 17 is accepted (D44).
    """
    version = _version(client_protocol)
    if version is None or version < MIN_CLIENT_PROTOCOL:
        raise ProtocolError(
            ERR_CLIENT_TOO_OLD, too_old_message(version),
            {"minProtocol": MIN_CLIENT_PROTOCOL, "serverProtocol": PROTOCOL_VERSION,
             "module": "SegQueue14"},
        )


def _version(client_protocol: Optional[Any]) -> Optional[int]:
    try:
        return None if client_protocol in (None, "") else int(client_protocol)
    except (TypeError, ValueError):
        return None


def update_to_review_message(sent: Optional[int]) -> str:
    """The refusal a protocol-17 reviewer gets on an extended read (D44)."""
    return ("Update SegQueue14 to review this read. It has extended classes "
            "(branches or materials) that this version of the module cannot show, "
            "and saving it from here would keep only LM, LAD, LCx and RCA. Install "
            "the latest SegQueue module (Check for updates) and restart Slicer. "
            f"Four-class reads still open as before. (Module protocol {sent}; "
            f"extended classes need {EXTENDED_CLASSES_PROTOCOL}.)")


def check_extended_reader(client_protocol: Optional[Any], extended: bool) -> None:
    """Raise ``ProtocolError`` if a module too old for extended classes asks for
    a read that has them (D44, #280).

    A four-class read is fine from any accepted module. A request that names no
    protocol at all is not a SegQueue14 module (a browser, an admin script): it
    cannot save anything back, so it is not refused here.
    """
    if not extended:
        return
    version = _version(client_protocol)
    if version is None or version >= EXTENDED_CLASSES_PROTOCOL:
        return
    raise ProtocolError(
        ERR_UPDATE_TO_REVIEW, update_to_review_message(version),
        {"minProtocol": EXTENDED_CLASSES_PROTOCOL, "serverProtocol": PROTOCOL_VERSION,
         "module": "SegQueue14", "extendedClasses": True})


def update_to_revise_message(sent: Optional[int]) -> str:
    """The refusal an older module gets on a case reopened for revision (#315)."""
    return ("Update SegQueue14 to open this case. It was reopened so you can look "
            "again at your own submission, and this version of the module would "
            "open it from the seed instead of from your work. Install the latest "
            "SegQueue14 (Check for updates) and restart Slicer; the case then opens "
            f"with your submitted classes. (Module protocol {sent}; reopened cases "
            f"need {REOPEN_PROTOCOL}.)")


def check_reopen_reader(client_protocol: Optional[Any]) -> None:
    """Raise ``ProtocolError`` unless the module can open a reopened case (#315).

    Unlike ``check_extended_reader``, a request naming no protocol is refused too:
    every SegQueue14 module sends one, and these are annotator routes.
    """
    version = _version(client_protocol)
    if version is not None and version >= REOPEN_PROTOCOL:
        return
    raise ProtocolError(
        ERR_UPDATE_TO_REVISE, update_to_revise_message(version),
        {"minProtocol": REOPEN_PROTOCOL, "serverProtocol": PROTOCOL_VERSION,
         "module": "SegQueue14", "reopened": True})


def label_format(value: Optional[Any]) -> str:
    """The stored format for a submit's ``labelFormat``; raise for an unknown one.

    Missing means an old single label volume (``labelmap``): every submission
    from before protocol 17. A client cannot reach the server without protocol
    17 any more, but the default keeps those stored submissions meaningful.
    """
    text = "" if value is None else str(value).strip()
    if not text:
        return LABEL_FORMAT_LABELMAP
    if text not in LABEL_FORMATS:
        raise ProtocolError(
            ERR_BAD_LABEL_FORMAT,
            f"Unknown segmentation file format {text!r}; this server reads "
            + ", ".join(LABEL_FORMATS) + ". Update the SegQueue14 module.",
            {"labelFormat": text, "known": list(LABEL_FORMATS)})
    return text
