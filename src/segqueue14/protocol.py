"""The wire contract between the SegQueue14 Slicer module and its Girder plugin.

The same shapes as ``segqueue.protocol`` -- and most of the dataclasses are
reused from there unchanged -- with four differences that are the point of
having a separate contract:

* **A separate prefix.** Every route is ``/api/v1/segqueue14/...``, so the two
  plugins load in one Girder without a single shared path.
* **A separate protocol version** (``segqueue14.PROTOCOL_VERSION``), checked on
  every write. There are no legacy SegQueue14 clients to protect, so unlike the
  live check a *missing* version is refused too: a client that does not say what
  it speaks is not one that was written for this server.
* **A ``prelabel`` asset** instead of the live binary coronary ``seed`` (D8, D10):
  a model's prediction in the project's classes, loaded straight into the
  project segments.
* **A ``seed`` asset of its own** (D23): for the pooled new datasets, an
  automatic *binary* vessel mask (TotalSegmentator ``coronary_arteries``) that the
  annotator divides into the four classes (D25). It is a helper segment, like the heart
  region, and is structurally unable to reach a submission.
* **``missing_required``** -- D13's submit rule, refused by name.

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

#: ``https://host/api/v1/segqueue14/...``.
API_PREFIX = "segqueue14"

#: Oldest SegQueue14 client protocol the server accepts.
MIN_CLIENT_PROTOCOL = PROTOCOL_VERSION

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

#: HTTP 400 from /submit: a required class (D13) has no voxels.
ERR_MISSING_REQUIRED = "missing_required"

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
#: What an annotator may fetch. The ImageCAS-X reference is deliberately absent:
#: an annotator who could download it could copy it.
ASSET_KINDS = (ASSET_REGION, ASSET_PRELABEL, ASSET_SEED)
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

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["hasPrelabel"] = self.has_prelabel
        data["prelabelVersion"] = self.prelabel_version
        return data

    @classmethod
    def from_dict(cls, data: dict) -> AssignmentInfo14:
        base = AssignmentInfo.from_dict(data)
        return cls(
            **{k: getattr(base, k) for k in base.__dataclass_fields__},
            has_prelabel=bool(data.get("hasPrelabel", False)),
            prelabel_version=str(data.get("prelabelVersion", "") or ""),
        )


# ------------------------------------------------------------ version check


def too_old_message(sent: Optional[int]) -> str:
    shown = "nothing" if sent is None else str(sent)
    return ("This SegQueue14 module is too old for the server: the server speaks "
            f"SegQueue14 protocol {PROTOCOL_VERSION} and the module sent {shown}. "
            "Update the SegQueue14 module (install the latest SegQueue14 zip from "
            "the project lead and restart Slicer). If you are using the ordinary "
            "SegQueue module, switch to SegQueue14 for this project.")


def check_client_protocol(client_protocol: Optional[Any]) -> None:
    """Raise ``ProtocolError`` unless the client speaks this protocol or newer.

    A missing or unparseable version is refused, unlike the live check: every
    SegQueue14 client ever released sends one.
    """
    try:
        version = None if client_protocol in (None, "") else int(client_protocol)
    except (TypeError, ValueError):
        version = None
    if version is None or version < MIN_CLIENT_PROTOCOL:
        raise ProtocolError(
            ERR_CLIENT_TOO_OLD, too_old_message(version),
            {"minProtocol": MIN_CLIENT_PROTOCOL, "serverProtocol": PROTOCOL_VERSION,
             "module": "SegQueue14"},
        )
