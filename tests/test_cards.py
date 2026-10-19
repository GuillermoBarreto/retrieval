import json
from datetime import date

import pytest

from retrieval.cards import Card, parse_deck, render_deck


DECK = """Q: What does HTTP 429 mean?
A: Too Many Requests — the client is being rate limited.
Tags: http, web

---

Q: Name the SM-2 initial easiness factor.
A: 2.5
"""


def test_parse_deck_basic():
    cards = parse_deck(DECK)
    assert len(cards) == 2
    assert cards[0].front == "What does HTTP 429 mean?"
    assert "Too Many Requests" in cards[0].back
    assert cards[0].tags == ("http", "web")
    assert cards[1].tags == ()


def test_card_ids_are_stable_and_unique():
    again = parse_deck(DECK)
    assert [c.id for c in again] == [c.id for c in parse_deck(DECK)]
    ids = {c.id for c in parse_deck(DECK)}
    assert len(ids) == 2


def test_multiline_answers():
    deck = "Q: Explain ACID.\nA: Atomicity\nConsistency\nIsolation\nDurability\n"
    cards = parse_deck(deck)
    assert cards[0].back.split("\n") == ["Atomicity", "Consistency", "Isolation", "Durability"]


def test_missing_answer_raises():
    with pytest.raises(ValueError):
        parse_deck("Q: No answer here.\n")


def test_missing_question_raises():
    with pytest.raises(ValueError):
        parse_deck("A: Orphan answer.\n")


def test_render_deck_round_trip():
    cards = parse_deck(DECK)
    assert parse_deck(render_deck(cards)) == cards


def test_custom_card_dataclass_defaults():
    card = Card(id="abc", front="f", back="b")
    assert card.tags == ()
    assert card.source == ""
