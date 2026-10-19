"""retrieval: AI-powered spaced-repetition flashcards for studying.

Generate quiz cards from your notes with an LLM, then review them on an
SM-2 spaced-repetition schedule backed by SQLite. No API key is required
for the parts that do not call a model.
"""

__version__ = "0.1.0"

from .cards import Card, parse_deck
from .scheduler import ReviewState, is_due, update

__all__ = ["Card", "ReviewState", "is_due", "parse_deck", "update", "__version__"]
