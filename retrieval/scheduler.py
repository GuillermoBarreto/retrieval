"""SM-2 spaced-repetition scheduling.

Implements the classic SuperMemo SM-2 algorithm: after each review the
user grades recall quality from 0 (complete blackout) to 5 (perfect
recall). The easiness factor adapts, intervals grow for cards you know
and collapse for cards you forget.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

MIN_EASINESS = 1.3
INITIAL_EASINESS = 2.5


@dataclass
class ReviewState:
    """Scheduling state for one card."""

    easiness: float = INITIAL_EASINESS
    interval: int = 0  # days until the next review
    repetitions: int = 0  # consecutive successful reviews
    due: date | None = None  # next due date (None = never reviewed)


def _clamp_quality(quality: int) -> int:
    if not 0 <= quality <= 5:
        raise ValueError(f"quality must be 0-5, got {quality}")
    return quality


def update(state: ReviewState, quality: int, today: date | None = None) -> ReviewState:
    """Return the new review state after grading a review with ``quality``.

    Quality < 3 resets the repetition count and schedules the card for
    tomorrow; quality >= 3 grows the interval per SM-2.
    """
    quality = _clamp_quality(quality)
    today = today or date.today()

    easiness = state.easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    easiness = max(easiness, MIN_EASINESS)

    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        repetitions = state.repetitions + 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = max(1, round(state.interval * easiness))

    return ReviewState(
        easiness=round(easiness, 4),
        interval=interval,
        repetitions=repetitions,
        due=today + timedelta(days=interval),
    )


def is_due(state: ReviewState, today: date | None = None) -> bool:
    """True if the card has never been reviewed or its due date passed."""
    today = today or date.today()
    return state.due is None or state.due <= today
