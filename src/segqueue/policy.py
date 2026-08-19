"""Who gets reviewed, who gets a gold case, and when a lease has run out.

Three decisions live here, and all three are pure functions of a few counters so
that they can be reasoned about and tested without a database:

1. **Review sampling.** Reviewing everything does not scale to 30 annotators;
   reviewing nothing means finding out in April that one student misunderstood
   the protocol in January. The compromise is a rate that moves with evidence --
   every case for the first few (the training gate), a sliding sample after
   that, and a snap back to every case after any rejection.
2. **Injection.** A fraction of served cases are gold standards (scored
   automatically against an expert reference) or blind duplicates (scored
   against another annotator). Neither is visible to the annotator; both are
   drawn from one uniform roll so the rates cannot silently overlap.
3. **Leases.** An assignment is a lease, not a gift. Undergraduate attrition is
   the highest-likelihood risk in this project, so a case held past its deadline
   returns to the pool automatically rather than waiting for someone to notice.

Nothing here reads a clock or a random number generator of its own: the caller
passes ``now`` and ``roll``. That is what makes the sampling behaviour
reproducible in tests and auditable in production -- the roll is stored on the
assignment, so months later you can still say why a given case was reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ------------------------------------------------------------------ injection

#: An ordinary case drawn from the pool.
NORMAL = "normal"
#: A case with an expert reference segmentation, scored automatically on submit.
GOLD = "gold"
#: A case deliberately served to a second annotator for inter-rater agreement.
DUPLICATE = "duplicate"


@dataclass(frozen=True)
class SamplingPolicy:
    """Project-wide knobs. One instance per project, stored as a Girder setting.

    The defaults are the design document's: ~5% gold, ~5% duplicates, a
    five-case training gate, 20% sampled review dropping to 10% once an
    annotator has a long clean run.
    """

    #: Every one of an annotator's first N submissions is reviewed. This is a
    #: training device more than a filter -- it is the only point at which a
    #: misunderstanding is cheap to correct.
    training_gate_cases: int = 5
    #: Sampled review rate once past the gate.
    base_review_rate: float = 0.20
    #: Rate for an annotator with a long clean run.
    trusted_review_rate: float = 0.10
    #: Consecutive approvals needed to earn the trusted rate.
    trusted_after_clean: int = 20
    #: After a rejection, review this many submissions in full before sampling
    #: resumes. A rejection means the annotator misunderstood something, and the
    #: fix needs confirming rather than assuming.
    probation_cases: int = 3

    #: Fraction of served cases that are gold standards.
    gold_rate: float = 0.05
    #: Fraction served as blind duplicates.
    duplicate_rate: float = 0.05
    #: Serve every annotator a gold case first. One measured case before any
    #: real work costs one case and calibrates everything that follows.
    gold_first_case: bool = True

    #: Days an annotator may hold a case before the lease expires.
    lease_days: float = 7.0
    #: Hours without a heartbeat after which a case is presumed abandoned even
    #: though the lease has not expired. Distinguishes "working slowly" from
    #: "dropped the course".
    stale_heartbeat_hours: float = 72.0

    #: Concurrent open assignments per annotator. 1 by default -- raise to 2-3
    #: only to let someone buffer work for a flight or a dead connection.
    max_concurrent: int = 1

    #: Mean Dice on a gold case below which the submission is flagged for a
    #: human regardless of the sampling roll.
    gold_dice_flag: float = 0.70
    #: Pairwise Dice between duplicate submissions below which both are flagged.
    duplicate_dice_flag: float = 0.70

    def validate(self) -> None:
        """Raise ``ValueError`` on a policy that cannot mean anything.

        Called when an admin saves settings, not on every request. The overlap
        check matters: rates summing above 1.0 would silently starve the normal
        pool, and the symptom (annotators only ever seeing gold cases) is very
        confusing to diagnose from the outside.
        """
        for name in ("base_review_rate", "trusted_review_rate", "gold_rate", "duplicate_rate"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value!r}")
        if self.gold_rate + self.duplicate_rate > 1.0:
            raise ValueError(
                "gold_rate + duplicate_rate must not exceed 1.0 "
                f"(got {self.gold_rate:.3f} + {self.duplicate_rate:.3f})"
            )
        if self.max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        if self.lease_days <= 0:
            raise ValueError("lease_days must be positive")
        if self.training_gate_cases < 0 or self.probation_cases < 0:
            raise ValueError("case counts must not be negative")


@dataclass(frozen=True)
class AnnotatorRecord:
    """The counters the policy reads. Maintained by the server on each verdict."""

    #: Submissions ever approved.
    approved: int = 0
    #: Submissions ever rejected.
    rejected: int = 0
    #: Approvals since the most recent rejection.
    clean_streak: int = 0
    #: Submissions made since the most recent rejection, reviewed or not. Drives
    #: the probation window, which must count *submissions* and not approvals --
    #: otherwise an annotator who is never sampled never leaves probation.
    since_rejection: int = 0

    @property
    def submitted(self) -> int:
        return self.approved + self.rejected


# --------------------------------------------------------------- review policy


def review_rate(record: AnnotatorRecord, policy: SamplingPolicy) -> float:
    """The probability that this annotator's next submission is reviewed.

    Returns 1.0 inside the training gate and inside a probation window; those
    are not sampled at all, and expressing them as a rate of 1.0 keeps every
    caller on one code path.
    """
    if record.submitted < policy.training_gate_cases:
        return 1.0
    if record.rejected > 0 and record.since_rejection < policy.probation_cases:
        return 1.0
    if record.clean_streak >= policy.trusted_after_clean:
        return policy.trusted_review_rate
    return policy.base_review_rate


def review_needed(
    record: AnnotatorRecord,
    policy: SamplingPolicy,
    roll: float,
    kind: str = NORMAL,
    auto_score: Optional[float] = None,
) -> bool:
    """Whether a submission goes to a human reviewer.

    ``roll`` is a uniform draw in [0, 1) made once per submission and stored
    alongside it. ``auto_score`` is the mean Dice against the gold reference or
    the duplicate partner, when one exists; a bad automatic score forces review
    no matter what the roll said, which is the entire point of seeding them.
    """
    if kind == GOLD and auto_score is not None and auto_score < policy.gold_dice_flag:
        return True
    if kind == DUPLICATE and auto_score is not None and auto_score < policy.duplicate_dice_flag:
        return True
    return roll < review_rate(record, policy)


# ------------------------------------------------------------ what to serve next


def injection_kind(
    record: AnnotatorRecord,
    policy: SamplingPolicy,
    roll: float,
    gold_available: bool = True,
    duplicate_available: bool = True,
) -> str:
    """Which flavour of case to serve next: ``GOLD``, ``DUPLICATE`` or ``NORMAL``.

    One roll is partitioned rather than two rolls compared, so the rates are
    exactly the rates and a case can never be both. Availability flags let the
    caller degrade gracefully: a project with no gold cases loaded yet, or one
    with nothing left that a *second* annotator could take, must still serve
    ordinary work rather than returning an empty queue.
    """
    if policy.gold_first_case and record.submitted == 0 and gold_available:
        return GOLD
    if gold_available and roll < policy.gold_rate:
        return GOLD
    if duplicate_available and roll < policy.gold_rate + policy.duplicate_rate:
        return DUPLICATE
    return NORMAL


def can_take_more(open_assignments: int, policy: SamplingPolicy,
                  quota_remaining: Optional[int] = None) -> bool:
    """Whether this annotator may be handed another case.

    ``quota_remaining`` is the per-user cap an admin may set (``None`` for no
    cap). Quotas exist so that a course can promise "50 cases each" and have the
    server hold that line without anyone watching a dashboard.
    """
    if quota_remaining is not None and quota_remaining <= 0:
        return False
    return open_assignments < policy.max_concurrent


# -------------------------------------------------------------------- leases


def lease_deadline(assigned_at: float, policy: SamplingPolicy) -> float:
    """Unix timestamp at which an assignment made at ``assigned_at`` expires."""
    return assigned_at + policy.lease_days * 86400.0


def lease_expired(assigned_at: float, now: float, policy: SamplingPolicy) -> bool:
    return now >= lease_deadline(assigned_at, policy)


def heartbeat_stale(last_heartbeat: Optional[float], now: float,
                    policy: SamplingPolicy) -> bool:
    """Whether the client has been silent long enough to presume abandonment.

    A missing heartbeat is *not* stale on its own: an annotator who downloaded a
    case one minute before the server restarted has not abandoned anything. Only
    the absence of contact over the configured window counts.
    """
    if last_heartbeat is None:
        return False
    return (now - last_heartbeat) >= policy.stale_heartbeat_hours * 3600.0


def should_reclaim(
    assigned_at: float,
    last_heartbeat: Optional[float],
    now: float,
    policy: SamplingPolicy,
) -> bool:
    """Whether the sweeper should expire this assignment and re-pool the case."""
    return lease_expired(assigned_at, now, policy) or heartbeat_stale(
        last_heartbeat, now, policy
    )


def reclaim_reason(
    assigned_at: float,
    last_heartbeat: Optional[float],
    now: float,
    policy: SamplingPolicy,
) -> Optional[str]:
    """Human-readable cause, recorded on the assignment for the audit trail."""
    if lease_expired(assigned_at, now, policy):
        return f"lease of {policy.lease_days:.3g} days expired"
    if heartbeat_stale(last_heartbeat, now, policy):
        return f"no heartbeat for {policy.stale_heartbeat_hours:.3g} hours"
    return None
