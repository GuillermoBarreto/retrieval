from datetime import date, timedelta

import pytest

from retrieval.scheduler import ReviewState, is_due, update

TODAY = date(2026, 10, 19)


def test_first_successful_review_schedules_tomorrow():
    state = update(ReviewState(), 5, today=TODAY)
    assert state.repetitions == 1
    assert state.interval == 1
    assert state.due == TODAY + timedelta(days=1)


def test_sm2_interval_progression():
    """Perfect reviews should follow the classic 1 -> 6 -> ~15 day curve."""
    state = ReviewState()
    state = update(state, 5, today=TODAY)  # rep 1 -> interval 1
    state = update(state, 5, today=TODAY)  # rep 2 -> interval 6
    assert state.interval == 6
    state = update(state, 5, today=TODAY)  # rep 3 -> interval ~= 6 * easiness
    assert state.interval == round(6 * state.easiness)
    assert state.interval >= 15


def test_failed_review_resets():
    state = ReviewState(repetitions=3, interval=30, easiness=2.5)
    state = update(state, 2, today=TODAY)
    assert state.repetitions == 0
    assert state.interval == 1
    assert state.due == TODAY + timedelta(days=1)


def test_easiness_never_below_floor():
    state = ReviewState(easiness=1.3)
    state = update(state, 0, today=TODAY)
    assert state.easiness >= 1.3


def test_quality_bounds_checked():
    with pytest.raises(ValueError):
        update(ReviewState(), 6, today=TODAY)
    with pytest.raises(ValueError):
        update(ReviewState(), -1, today=TODAY)


def test_is_due():
    assert is_due(ReviewState(due=None), today=TODAY)
    assert is_due(ReviewState(due=TODAY), today=TODAY)
    assert is_due(ReviewState(due=TODAY - timedelta(days=3)), today=TODAY)
    assert not is_due(ReviewState(due=TODAY + timedelta(days=3)), today=TODAY)
