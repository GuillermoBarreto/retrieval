import json

import pytest

from retrieval.generate import CardGenerationError, generate_cards


def _fake_post(cards, raw=None):
    def post(url, payload, api_key):
        assert url.endswith("/chat/completions")
        assert "messages" in payload
        body = raw if raw is not None else json.dumps(cards)
        return {"choices": [{"message": {"content": body}}]}

    return post


def test_generate_cards_parses_response():
    cards = generate_cards(
        "Some notes.",
        api_key="fake",
        model="test-model",
        http_post=_fake_post(
            [{"front": "Q1?", "back": "A1.", "tags": ["t1"]}]
        ),
    )
    assert cards == [{"front": "Q1?", "back": "A1.", "tags": ["t1"]}]


def test_generate_cards_skips_malformed_entries():
    cards = generate_cards(
        "Notes.",
        api_key="fake",
        http_post=_fake_post(
            [
                {"front": "Good?", "back": "Good."},
                {"front": "", "back": "No front"},
                {"front": "No back"},
                "not a dict",
            ]
        ),
    )
    assert len(cards) == 1
    assert cards[0]["tags"] == []


def test_generate_cards_requires_api_key(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(CardGenerationError, match="API key"):
        generate_cards("Notes.", http_post=_fake_post([]))


def test_generate_cards_rejects_empty_notes():
    with pytest.raises(CardGenerationError, match="No notes"):
        generate_cards("   ", api_key="fake", http_post=_fake_post([]))


def test_generate_cards_rejects_non_json():
    with pytest.raises(CardGenerationError, match="parse"):
        generate_cards("Notes.", api_key="fake", http_post=_fake_post([], raw="not json"))


def test_generate_cards_respects_max_cards():
    many = [{"front": f"Q{i}", "back": f"A{i}"} for i in range(10)]
    cards = generate_cards("Notes.", api_key="fake", max_cards=3, http_post=_fake_post(many))
    assert len(cards) == 3
