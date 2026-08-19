"""Review sampling, gold/duplicate injection, and lease expiry."""

import pytest

from segqueue.policy import (
    DUPLICATE,
    GOLD,
    NORMAL,
    AnnotatorRecord,
    SamplingPolicy,
    can_take_more,
    heartbeat_stale,
    injection_kind,
    lease_deadline,
    lease_expired,
    reclaim_reason,
    review_needed,
    review_rate,
    should_reclaim,
)

DAY = 86400.0
HOUR = 3600.0


@pytest.fixture
def policy():
    return SamplingPolicy()


# ------------------------------------------------------------ review sampling


def test_the_training_gate_reviews_everything(policy):
    for n in range(policy.training_gate_cases):
        assert review_rate(AnnotatorRecord(approved=n, clean_streak=n), policy) == 1.0


def test_sampling_starts_once_the_gate_is_passed(policy):
    record = AnnotatorRecord(approved=5, clean_streak=5, since_rejection=5)
    assert review_rate(record, policy) == policy.base_review_rate


def test_a_long_clean_run_earns_a_lighter_touch(policy):
    record = AnnotatorRecord(approved=40, clean_streak=40, since_rejection=40)
    assert review_rate(record, policy) == policy.trusted_review_rate


def test_a_rejection_puts_an_annotator_back_on_full_review(policy):
    """Even a previously trusted one -- the clean streak resets with the verdict."""
    record = AnnotatorRecord(approved=40, rejected=1, clean_streak=0, since_rejection=0)
    assert review_rate(record, policy) == 1.0


def test_probation_is_counted_in_submissions_not_approvals(policy):
    """Otherwise an annotator who is never sampled never leaves probation."""
    still_on = AnnotatorRecord(approved=40, rejected=1, clean_streak=2, since_rejection=2)
    assert review_rate(still_on, policy) == 1.0
    served = AnnotatorRecord(approved=40, rejected=1, clean_streak=3, since_rejection=3)
    assert review_rate(served, policy) < 1.0


def test_review_needed_compares_the_roll_to_the_rate(policy):
    record = AnnotatorRecord(approved=10, clean_streak=10, since_rejection=10)
    assert review_needed(record, policy, roll=0.05)  # below 0.20
    assert not review_needed(record, policy, roll=0.95)


def test_a_bad_gold_score_forces_review_however_the_roll_landed(policy):
    record = AnnotatorRecord(approved=50, clean_streak=50, since_rejection=50)
    assert not review_needed(record, policy, roll=0.99, kind=GOLD, auto_score=0.9)
    assert review_needed(record, policy, roll=0.99, kind=GOLD, auto_score=0.3)


def test_a_bad_duplicate_agreement_forces_review_too(policy):
    record = AnnotatorRecord(approved=50, clean_streak=50, since_rejection=50)
    assert review_needed(record, policy, roll=0.99, kind=DUPLICATE, auto_score=0.2)


def test_a_missing_auto_score_falls_back_to_the_roll(policy):
    """A gold case whose scoring job has not run yet must not auto-approve."""
    record = AnnotatorRecord(approved=50, clean_streak=50, since_rejection=50)
    assert review_needed(record, policy, roll=0.01, kind=GOLD, auto_score=None)


# ----------------------------------------------------------------- injection


def test_the_first_case_is_gold_so_everyone_has_a_baseline(policy):
    assert injection_kind(AnnotatorRecord(), policy, roll=0.99) == GOLD


def test_the_first_case_is_ordinary_when_no_gold_exists_yet(policy):
    assert injection_kind(AnnotatorRecord(), policy, roll=0.99, gold_available=False) == NORMAL


def test_one_roll_partitions_the_three_kinds(policy):
    experienced = AnnotatorRecord(approved=10, clean_streak=10, since_rejection=10)
    assert injection_kind(experienced, policy, roll=0.01) == GOLD
    assert injection_kind(experienced, policy, roll=0.07) == DUPLICATE
    assert injection_kind(experienced, policy, roll=0.5) == NORMAL


def test_rates_are_honoured_over_many_rolls(policy):
    experienced = AnnotatorRecord(approved=10, clean_streak=10, since_rejection=10)
    n = 10000
    kinds = [injection_kind(experienced, policy, roll=i / n) for i in range(n)]
    assert abs(kinds.count(GOLD) / n - policy.gold_rate) < 0.01
    assert abs(kinds.count(DUPLICATE) / n - policy.duplicate_rate) < 0.01


def test_injection_degrades_to_normal_when_nothing_is_available(policy):
    experienced = AnnotatorRecord(approved=10, clean_streak=10, since_rejection=10)
    kind = injection_kind(experienced, policy, roll=0.01,
                          gold_available=False, duplicate_available=False)
    assert kind == NORMAL


def test_a_duplicate_roll_with_no_duplicate_available_is_not_promoted_to_gold(policy):
    """Availability must remove a kind, never redirect the roll into another."""
    experienced = AnnotatorRecord(approved=10, clean_streak=10, since_rejection=10)
    assert injection_kind(experienced, policy, roll=0.07,
                          duplicate_available=False) == NORMAL


# -------------------------------------------------------------------- quotas


def test_concurrency_limit_is_enforced(policy):
    assert can_take_more(0, policy)
    assert not can_take_more(1, policy)
    buffered = SamplingPolicy(max_concurrent=3)
    assert can_take_more(2, buffered)
    assert not can_take_more(3, buffered)


def test_an_exhausted_quota_blocks_even_an_idle_annotator(policy):
    assert not can_take_more(0, policy, quota_remaining=0)
    assert can_take_more(0, policy, quota_remaining=1)
    assert can_take_more(0, policy, quota_remaining=None)


# -------------------------------------------------------------------- leases


def test_lease_expires_after_the_configured_days(policy):
    assigned = 1_000_000.0
    assert lease_deadline(assigned, policy) == assigned + policy.lease_days * DAY
    assert not lease_expired(assigned, assigned + 6 * DAY, policy)
    assert lease_expired(assigned, assigned + 7 * DAY, policy)


def test_a_silent_client_is_reclaimed_before_the_lease_runs_out(policy):
    assigned = 1_000_000.0
    now = assigned + 4 * DAY
    quiet_since = assigned + 1 * HOUR
    assert not lease_expired(assigned, now, policy)
    assert heartbeat_stale(quiet_since, now, policy)
    assert should_reclaim(assigned, quiet_since, now, policy)


def test_no_heartbeat_at_all_is_not_evidence_of_abandonment(policy):
    """A case downloaded just before a server restart has not been abandoned."""
    assigned = 1_000_000.0
    assert not heartbeat_stale(None, assigned + HOUR, policy)
    assert not should_reclaim(assigned, None, assigned + HOUR, policy)
    # ...but the lease still governs it.
    assert should_reclaim(assigned, None, assigned + 8 * DAY, policy)


def test_reclaim_reason_is_recorded_for_the_audit_trail(policy):
    assigned = 1_000_000.0
    assert reclaim_reason(assigned, None, assigned + HOUR, policy) is None
    assert "lease" in reclaim_reason(assigned, None, assigned + 8 * DAY, policy)
    assert "heartbeat" in reclaim_reason(
        assigned, assigned + HOUR, assigned + 4 * DAY, policy
    )


# ------------------------------------------------------------------ validation


def test_a_policy_that_cannot_mean_anything_is_rejected():
    SamplingPolicy().validate()
    with pytest.raises(ValueError, match="exceed 1.0"):
        SamplingPolicy(gold_rate=0.7, duplicate_rate=0.7).validate()
    with pytest.raises(ValueError, match="max_concurrent"):
        SamplingPolicy(max_concurrent=0).validate()
    with pytest.raises(ValueError, match="lease_days"):
        SamplingPolicy(lease_days=0).validate()
    with pytest.raises(ValueError, match="in .0, 1."):
        SamplingPolicy(base_review_rate=1.5).validate()
