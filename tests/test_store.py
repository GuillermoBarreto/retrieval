from datetime import date

import pytest

from retrieval.cards import parse_deck
from retrieval.scheduler import ReviewState, update
from retrieval.store import (
    connect,
    due_cards,
    get_review_state,
    record_review,
    stats,
    upsert_cards,
)

TODAY = date(2026, 10, 19)
DECK = """Q: What is a closure?
A: A function that captures variables from its enclosing scope.
Tags: python

---

Q: What does TCP stand for?
A: Transmission Control Protocol.
"""


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield conn
    conn.close()


def test_upsert_is_idempotent(conn):
    cards = parse_deck(DECK)
    assert upsert_cards(conn, cards) == 2
    assert upsert_cards(conn, cards) == 0  # same ids -> ignored


def test_due_cards_includes_never_reviewed(conn):
    cards = parse_deck(DECK)
    upsert_cards(conn, cards)
    due = due_cards(conn, today=TODAY)
    assert {c.id for c in due} == {c.id for c in cards}


def test_due_cards_excludes_future_due(conn):
    cards = parse_deck(DECK)
    upsert_cards(conn, cards)
    future = update(ReviewState(), 5, today=TODAY)  # due tomorrow
    record_review(conn, cards[0].id, future, reviewed_on=TODAY)
    due = due_cards(conn, today=TODAY)
    assert [c.id for c in due] == [cards[1].id]


def test_get_review_state_default(conn):
    state = get_review_state(conn, "nonexistent")
    assert state == ReviewState()


def test_record_review_round_trip(conn):
    cards = parse_deck(DECK)
    upsert_cards(conn, cards)
    new_state = update(ReviewState(), 4, today=TODAY)
    record_review(conn, cards[0].id, new_state, reviewed_on=TODAY)
    assert get_review_state(conn, cards[0].id) == new_state


def test_stats(conn):
    cards = parse_deck(DECK)
    upsert_cards(conn, cards)
    record_review(conn, cards[0].id, update(ReviewState(), 5, today=TODAY), reviewed_on=TODAY)
    s = stats(conn, today=TODAY)
    assert s["total_cards"] == 2
    assert s["reviewed_cards"] == 1
    assert s["reviewed_today"] == 1
    assert s["due_today"] == 1  # only the never-reviewed card
    assert s["avg_easiness"] is not None
