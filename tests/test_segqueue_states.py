"""The assignment state machine -- the part that strands cases when it is wrong."""

import pytest

from segqueue import states as st


def test_the_happy_path_reaches_approved():
    state = st.ASSIGNED
    for event in (st.DOWNLOAD, st.SUBMIT, st.CLAIM_REVIEW, st.APPROVE):
        state = st.apply_event(state, event)
    assert state == st.APPROVED
    assert state in st.TERMINAL_STATES


def test_unreviewed_submissions_can_be_approved_directly():
    """Most submissions are never claimed by a human; they still must finish."""
    assert st.apply_event(st.SUBMITTED, st.APPROVE) == st.APPROVED


def test_cannot_submit_without_downloading():
    """A client that never fetched the volume cannot have segmented it."""
    assert not st.can(st.ASSIGNED, st.SUBMIT)
    with pytest.raises(st.TransitionError):
        st.apply_event(st.ASSIGNED, st.SUBMIT)


def test_rework_returns_to_the_same_annotator_not_the_pool():
    assert st.apply_event(st.REJECTED, st.REWORK) == st.ASSIGNED


def test_rejected_work_can_still_be_reclaimed():
    """The commonest way a case would strand: rejected, then the student leaves."""
    assert st.can(st.REJECTED, st.EXPIRE)
    assert st.apply_event(st.REJECTED, st.EXPIRE) == st.RELEASED


def test_terminal_states_admit_nothing():
    for state in st.TERMINAL_STATES:
        assert st.allowed_events(state) == ()
        for event in st.ALL_EVENTS:
            assert not st.can(state, event)


def test_every_open_state_has_an_escape_hatch():
    """No state may hold a case with no way to get it back."""
    for state in st.OPEN_STATES:
        assert st.EXPIRE in st.allowed_events(state), state
        assert st.RELEASE in st.allowed_events(state), state


def test_every_state_is_reachable_from_assigned():
    reached = {st.ASSIGNED}
    frontier = [st.ASSIGNED]
    while frontier:
        state = frontier.pop()
        for event in st.ALL_EVENTS:
            if st.can(state, event):
                nxt = st.apply_event(state, event)
                if nxt not in reached:
                    reached.add(nxt)
                    frontier.append(nxt)
    assert reached == set(st.ALL_STATES)


def test_transition_table_only_names_declared_states_and_events():
    for (state, event), result in st.TRANSITIONS.items():
        assert state in st.ALL_STATES
        assert event in st.ALL_EVENTS
        assert result in st.ALL_STATES


def test_transition_error_lists_what_was_allowed():
    with pytest.raises(st.TransitionError) as excinfo:
        st.apply_event(st.SUBMITTED, st.DOWNLOAD)
    message = str(excinfo.value)
    assert "submitted" in message
    assert "approve" in message


def test_a_submitted_case_frees_the_annotator_but_not_the_replica_slot():
    """The bug this separation exists to prevent: a rejected case going out to a
    second annotator while the first is still on the hook to fix it."""
    assert not st.is_open(st.SUBMITTED)      # annotator may take another case
    assert st.is_active(st.SUBMITTED)        # nobody else may take this one
    assert st.is_active(st.UNDER_REVIEW)
    assert st.OPEN_STATES < st.ACTIVE_STATES


def test_active_states_are_exactly_the_non_terminal_ones():
    assert st.ACTIVE_STATES == set(st.ALL_STATES) - st.TERMINAL_STATES
    for state in st.TERMINAL_STATES:
        assert not st.is_active(state)


def test_local_data_states_are_exactly_where_a_purge_matters():
    """If this drifts, either the cache leaks or rework loses its volume."""
    assert st.holds_local_data(st.DOWNLOADED)
    assert st.holds_local_data(st.REJECTED)
    assert not st.holds_local_data(st.SUBMITTED)
    assert not st.holds_local_data(st.APPROVED)


# ------------------------------------------------------------------ case level


def test_case_status_follows_the_counts():
    assert st.case_status(1, 0, 0) == st.CASE_PENDING
    assert st.case_status(1, 1, 0) == st.CASE_IN_PROGRESS
    assert st.case_status(1, 0, 1) == st.CASE_COMPLETE
    assert st.case_status(2, 0, 1) == st.CASE_IN_PROGRESS
    assert st.case_status(2, 0, 2) == st.CASE_COMPLETE


def test_retired_beats_everything():
    assert st.case_status(1, 0, 1, retired=True) == st.CASE_RETIRED
    assert not st.servable(1, 0, 0, retired=True)


def test_a_duplicate_wants_a_second_annotator_but_only_one_at_a_time():
    # Wanting two, one approved, none out: someone else should get it.
    assert st.servable(2, 0, 1)
    # Wanting two, one approved, one already out: nobody else.
    assert not st.servable(2, 1, 1)
    # A plain case that is already out is not servable again.
    assert not st.servable(1, 1, 0)


def test_attempts_are_one_based_and_only_ever_increase():
    assert st.next_attempt(0) == 1
    assert st.next_attempt(1) == 2
    assert st.next_attempt(-5) == 1


def test_every_state_has_annotator_facing_text():
    for state in st.ALL_STATES:
        assert st.describe(state)
    assert st.describe("nonsense") is None
