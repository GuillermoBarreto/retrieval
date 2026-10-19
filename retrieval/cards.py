"""Flashcard model and markdown deck parsing.

Deck format (``.md``)::

    Q: What does HTTP 429 mean?
    A: Too Many Requests — the client is being rate limited.
    Tags: http, web

    ---

    Q: Name the SM-2 initial easiness factor.
    A: 2.5

Cards are separated by a line containing only ``---``. ``Tags:`` is
optional. A card id is the SHA-1 of its front and back text, so
re-importing the same deck never creates duplicates.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    """A single flashcard."""

    id: str
    front: str
    back: str
    tags: tuple[str, ...] = ()
    source: str = ""


def _stable_id(front: str, back: str) -> str:
    digest = hashlib.sha1(f"{front}\x00{back}".encode("utf-8")).hexdigest()
    return digest[:12]


def parse_deck(text: str, source: str = "") -> list[Card]:
    """Parse markdown deck text into :class:`Card` objects.

    Raises:
        ValueError: if a block is missing a ``Q:`` or ``A:`` line.
    """
    cards: list[Card] = []
    blocks = [b.strip() for b in text.replace("\r\n", "\n").split("\n---\n")]
    for block in blocks:
        if not block:
            continue
        front: str | None = None
        back_lines: list[str] = []
        tags: list[str] = []
        in_answer = False
        for line in block.split("\n"):
            stripped = line.strip()
            if stripped.startswith("Q:"):
                front = stripped[2:].strip()
                in_answer = False
            elif stripped.startswith("A:"):
                back_lines.append(stripped[2:].strip())
                in_answer = True
            elif stripped.lower().startswith("tags:"):
                tags = [t.strip() for t in stripped[5:].split(",") if t.strip()]
                in_answer = False
            elif in_answer:
                back_lines.append(line.rstrip())
        if front is None or not back_lines:
            raise ValueError(f"Card block is missing a Q: or A: line:\n{block}")
        back = "\n".join(back_lines).strip()
        cards.append(
            Card(
                id=_stable_id(front, back),
                front=front,
                back=back,
                tags=tuple(tags),
                source=source,
            )
        )
    return cards


def render_deck(cards: list[Card]) -> str:
    """Render cards back to the markdown deck format."""
    blocks: list[str] = []
    for card in cards:
        block = f"Q: {card.front}\nA: {card.back}"
        if card.tags:
            block += f"\nTags: {', '.join(card.tags)}"
        blocks.append(block)
    return "\n\n---\n\n".join(blocks) + "\n"
