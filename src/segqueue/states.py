"""The assignment lifecycle: who owes what, and what may happen next.

**The state lives on the assignment, not on the case.** The design sketch put a
single state machine on the case, which reads well until blind duplicates arrive:
a duplicate is one case held by two annotators at once, and two people cannot
share one ``DOWNLOADED``. Once a case can be out with N annotators, the case only
has a *count* -- how many replicas are wanted, how many are approved -- and every
verb an annotator performs belongs to their own assignment. Rework falls out of
the same choice for free: a rejected assignment returns to ``ASSIGNED`` without
touching the case, so the annotator keeps the case they were already holding.

Every transition is declared in ``TRANSITIONS`` and applied through
``apply_event``. Nothing writes a state field directly -- an illegal transition
raises rather than silently corrupting the queue, which matters because the
alternative failure mode (a case assigned to nobody and complete for no-one) is
invisible until the semester ends.
"""

from __future__ import annotations

from typing import Optional

# --------------------------------------------------------------------- states

#: Assigned to an annotator, who has not fetched the volume yet.
ASSIGNED = "assigned"
#: The volume is on the annotator's machine. This is the state that costs
#: something: a case sitting here is a case nobody else can work on.
DOWNLOADED = "downloaded"
#: Segmentation uploaded and checksum-verified. Awaiting triage.
SUBMITTED = "submitted"
#: A reviewer has claimed it. Claiming is explicit so that two reviewers do not
#: both spend twenty minutes on the same submission.
UNDER_REVIEW = "under_review"
#: Accepted. Terminal, and the only state that counts toward completion.
APPROVED = "approved"
#: Sent back with comments. Not terminal -- ``rework`` returns it to the same
#: annotator, which is the whole point (see policy.py).
REJECTED = "rejected"
#: The annotator gave the case back, or the lease expired. Terminal for this
#: assignment; the case returns to the pool for someone else.
RELEASED = "released"

ALL_STATES = (
    ASSIGNED,
    DOWNLOADED,
    SUBMITTED,
    UNDER_REVIEW,
    APPROVED,
    REJECTED,
    RELEASED,
)

#: States in which the annotator still owes us work. This is the annotator-side
#: question: it decides whether they may be handed another case.
OPEN_STATES = frozenset({ASSIGNED, DOWNLOADED, REJECTED})

#: States from which no further transition is possible.
TERMINAL_STATES = frozenset({APPROVED, RELEASED})

#: States in which this assignment still occupies one of the case's replica
#: slots. The case-side question, and deliberately *not* the same set as
#: ``OPEN_STATES``: a submitted case owes the annotator nothing -- they should be
#: handed their next case at once -- but it must not go out to a second
#: annotator either, because a reviewer may yet reject it and send it back. Get
#: these two confused and a rejected case is silently double-booked.
ACTIVE_STATES = frozenset(set(ALL_STATES) - TERMINAL_STATES)

#: States in which data sits on the annotator's disk. The extension purges its
#: cache on leaving these, which is how "no large local storage footprint" gets
#: enforced structurally instead of by asking students to tidy up.
LOCAL_DATA_STATES = frozenset({DOWNLOADED, REJECTED})

# --------------------------------------------------------------------- events

ASSIGN = "assign"
DOWNLOAD = "download"
SUBMIT = "submit"
CLAIM_REVIEW = "claim_review"
ABANDON_REVIEW = "abandon_review"
APPROVE = "approve"
REJECT = "reject"
REWORK = "rework"
RELEASE = "release"
EXPIRE = "expire"

ALL_EVENTS = (
    ASSIGN,
    DOWNLOAD,
    SUBMIT,
    CLAIM_REVIEW,
    ABANDON_REVIEW,
    APPROVE,
    REJECT,
    REWORK,
    RELEASE,
    EXPIRE,
)

#: ``(state, event) -> next state``. The absence of a key is a refusal.
#:
#: Two entries deserve a note. ``(ASSIGNED, SUBMIT)`` is absent on purpose: you
#: cannot submit a segmentation of a volume you never downloaded, and permitting
#: it would let a broken client fabricate work. ``(SUBMITTED, APPROVE)`` is
#: present without a review claim because most submissions are auto-approved --
#: only the sampled fraction is ever seen by a human (``policy.review_needed``).
TRANSITIONS = {
    (ASSIGNED, DOWNLOAD): DOWNLOADED,
    (ASSIGNED, RELEASE): RELEASED,
    (ASSIGNED, EXPIRE): RELEASED,

    (DOWNLOADED, SUBMIT): SUBMITTED,
    (DOWNLOADED, RELEASE): RELEASED,
    (DOWNLOADED, EXPIRE): RELEASED,

    (SUBMITTED, CLAIM_REVIEW): UNDER_REVIEW,
    (SUBMITTED, APPROVE): APPROVED,
    (SUBMITTED, REJECT): REJECTED,

    (UNDER_REVIEW, APPROVE): APPROVED,
    (UNDER_REVIEW, REJECT): REJECTED,
    (UNDER_REVIEW, ABANDON_REVIEW): SUBMITTED,

    (REJECTED, REWORK): ASSIGNED,
    # An annotator who has left cannot rework. Reclaiming a rejected assignment
    # is the single most common way a case would otherwise strand.
    (REJECTED, RELEASE): RELEASED,
    (REJECTED, EXPIRE): RELEASED,
}


class TransitionError(RuntimeError):
    """An event the assignment's current state does not permit."""

    def __init__(self, state: str, event: str) -> None:
        self.state = state
        self.event = event
        allowed = sorted(e for (s, e) in TRANSITIONS if s == state)
        detail = ", ".join(allowed) if allowed else "none (terminal)"
        super().__init__(
            f"cannot {event} an assignment in state {state!r}; allowed here: {detail}"
        )


def can(state: str, event: str) -> bool:
    """Whether ``event`` is legal in ``state``. Never raises."""
    return (state, event) in TRANSITIONS


def apply_event(state: str, event: str) -> str:
    """The state after ``event``, or raise ``TransitionError``.

    The only supported way to change an assignment's state. Callers persist the
    return value; they do not compute it themselves.
    """
    try:
        return TRANSITIONS[(state, event)]
    except KeyError:
        raise TransitionError(state, event) from None


def allowed_events(state: str) -> tuple:
    """Every event legal in ``state``, sorted -- for building UI and error text."""
    return tuple(sorted(e for (s, e) in TRANSITIONS if s == state))


def is_open(state: str) -> bool:
    """Whether the annotator still owes work -- i.e. whether it counts against
    their concurrency limit."""
    return state in OPEN_STATES


def is_active(state: str) -> bool:
    """Whether this assignment still holds one of the case's replica slots."""
    return state in ACTIVE_STATES


def holds_local_data(state: str) -> bool:
    """Whether the annotator's machine should still have the volume on disk."""
    return state in LOCAL_DATA_STATES


# ----------------------------------------------------------------- case status

#: No replica of this case is out with anyone, and it is not finished.
CASE_PENDING = "pending"
#: At least one replica is out or approved, but not enough are approved yet.
CASE_IN_PROGRESS = "in_progress"
#: Enough approved replicas exist; the case never needs serving again.
CASE_COMPLETE = "complete"
#: Withdrawn by an admin -- corrupt volume, wrong series, failed de-identification.
CASE_RETIRED = "retired"


def case_status(
    replicas_wanted: int,
    active_assignments: int,
    approved_assignments: int,
    retired: bool = False,
) -> str:
    """Derive a case's status from its assignment counts.

    ``active_assignments`` counts assignments in ``ACTIVE_STATES`` -- every
    replica slot currently spoken for, including ones awaiting review.

    Derived, never stored as the source of truth: a stored case status and a set
    of assignments will disagree the first time a process dies between the two
    writes, and a case stuck that way is precisely the failure this platform
    cannot afford. Cache it for queries if you like -- recompute it here.
    """
    if retired:
        return CASE_RETIRED
    if approved_assignments >= replicas_wanted:
        return CASE_COMPLETE
    if active_assignments > 0 or approved_assignments > 0:
        return CASE_IN_PROGRESS
    return CASE_PENDING


def servable(
    replicas_wanted: int,
    active_assignments: int,
    approved_assignments: int,
    retired: bool = False,
) -> bool:
    """Whether this case still needs to go out to another annotator.

    A case wanting two replicas with one approved and none open still needs a
    second annotator; the same case with one open does not.
    """
    if retired:
        return False
    return (active_assignments + approved_assignments) < replicas_wanted


def next_attempt(previous_attempts: int) -> int:
    """Attempt numbers are 1-based. Rework increments; reassignment does not reset."""
    return max(0, int(previous_attempts)) + 1


def describe(state: str) -> Optional[str]:
    """One line of annotator-facing text for a state, or None if unrecognised."""
    return _DESCRIPTIONS.get(state)


_DESCRIPTIONS = {
    ASSIGNED: "Assigned to you -- not downloaded yet.",
    DOWNLOADED: "On your machine. Segment it, then submit.",
    SUBMITTED: "Submitted. Waiting on review.",
    UNDER_REVIEW: "A reviewer is looking at it now.",
    APPROVED: "Approved. Nothing further to do.",
    REJECTED: "Sent back with comments -- please fix and resubmit.",
    RELEASED: "Returned to the pool.",
}
