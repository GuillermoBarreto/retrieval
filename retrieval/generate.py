"""AI card generation from study notes.

Sends raw study notes to an OpenAI-compatible chat-completions endpoint
and parses the JSON card list it returns. The API key always comes from
the environment (``RETRIEVAL_API_KEY`` or ``OPENAI_API_KEY``) — never
from a file or argument. Everything is stdlib-only (``urllib``), so
generation works with no extra dependencies.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"

SYSTEM_PROMPT = (
    "You turn study notes into flashcards for spaced repetition. "
    "Return ONLY a JSON array of objects with keys \"front\" (a short, specific "
    "question), \"back\" (a concise answer), and \"tags\" (a list of 1-3 topic "
    "strings). One atomic fact per card. No markdown, no commentary."
)


class CardGenerationError(Exception):
    """Raised when cards cannot be generated (no key, bad response, ...)."""


def _default_post(url: str, payload: dict, api_key: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:  # pragma: no cover - network path
        raise CardGenerationError(f"Request to the model failed: {exc}") from exc


def generate_cards(
    notes: str,
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    max_cards: int = 20,
    http_post: Callable[[str, dict, str], dict] | None = None,
) -> list[dict]:
    """Generate flashcard dicts (front/back/tags) from study ``notes``.

    ``http_post`` is injectable for tests; it receives (url, payload,
    api_key) and must return the decoded JSON response.
    """
    key = api_key or os.environ.get("RETRIEVAL_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise CardGenerationError(
            "No API key found. Set RETRIEVAL_API_KEY (or OPENAI_API_KEY)."
        )
    if not notes.strip():
        raise CardGenerationError("No notes provided.")
    post = http_post or _default_post
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Create at most {max_cards} flashcards from these notes:\n\n{notes}",
            },
        ],
        "temperature": 0.3,
    }
    try:
        response = post(f"{base_url.rstrip('/')}/chat/completions", payload, key)
        content = response["choices"][0]["message"]["content"]
        cards = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise CardGenerationError(f"Could not parse the model's response: {exc}") from exc
    if not isinstance(cards, list):
        raise CardGenerationError("The model did not return a JSON array.")
    cleaned: list[dict] = []
    for card in cards:
        if not isinstance(card, dict) or not card.get("front") or not card.get("back"):
            continue
        cleaned.append(
            {
                "front": str(card["front"]).strip(),
                "back": str(card["back"]).strip(),
                "tags": [str(t).strip() for t in card.get("tags", []) if str(t).strip()],
            }
        )
    return cleaned[:max_cards]
