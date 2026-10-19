"""SQLite persistence for cards and review state."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from .cards import Card
from .scheduler import ReviewState

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reviews (
    card_id TEXT PRIMARY KEY REFERENCES cards(id),
    easiness REAL NOT NULL,
    interval INTEGER NOT NULL,
    repetitions INTEGER NOT NULL,
    due TEXT,
    last_reviewed TEXT
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open the database, creating schema on first use."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_cards(conn: sqlite3.Connection, cards: list[Card]) -> int:
    """Insert cards, ignoring ones already stored. Returns new card count."""
    cur = conn.executemany(
        "INSERT OR IGNORE INTO cards (id, front, back, tags, source) VALUES (?, ?, ?, ?, ?)",
        [(c.id, c.front, c.back, ",".join(c.tags), c.source) for c in cards],
    )
    conn.commit()
    return cur.rowcount


def get_review_state(conn: sqlite3.Connection, card_id: str) -> ReviewState:
    row = conn.execute(
        "SELECT easiness, interval, repetitions, due FROM reviews WHERE card_id = ?",
        (card_id,),
    ).fetchone()
    if row is None:
        return ReviewState()
    return ReviewState(
        easiness=row["easiness"],
        interval=row["interval"],
        repetitions=row["repetitions"],
        due=date.fromisoformat(row["due"]) if row["due"] else None,
    )


def record_review(
    conn: sqlite3.Connection,
    card_id: str,
    state: ReviewState,
    reviewed_on: date | None = None,
) -> None:
    conn.execute(
        """INSERT INTO reviews (card_id, easiness, interval, repetitions, due, last_reviewed)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(card_id) DO UPDATE SET
             easiness=excluded.easiness, interval=excluded.interval,
             repetitions=excluded.repetitions, due=excluded.due,
             last_reviewed=excluded.last_reviewed""",
        (
            card_id,
            state.easiness,
            state.interval,
            state.repetitions,
            state.due.isoformat() if state.due else None,
            (reviewed_on or date.today()).isoformat(),
        ),
    )
    conn.commit()


def due_cards(conn: sqlite3.Connection, today: date | None = None, limit: int = 50) -> list[Card]:
    """Cards due for review, oldest due first (never-reviewed first)."""
    today = today or date.today()
    rows = conn.execute(
        """SELECT c.id, c.front, c.back, c.tags, c.source
           FROM cards c LEFT JOIN reviews r ON r.card_id = c.id
           WHERE r.due IS NULL OR r.due <= ?
           ORDER BY r.due IS NOT NULL, r.due ASC, c.id ASC
           LIMIT ?""",
        (today.isoformat(), limit),
    ).fetchall()
    return [
        Card(
            id=r["id"],
            front=r["front"],
            back=r["back"],
            tags=tuple(t for t in r["tags"].split(",") if t),
            source=r["source"],
        )
        for r in rows
    ]


def stats(conn: sqlite3.Connection, today: date | None = None) -> dict:
    """Deck statistics: totals, due counts, and review history."""
    today = (today or date.today()).isoformat()
    total = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    reviewed = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    due = conn.execute(
        "SELECT COUNT(*) FROM cards c LEFT JOIN reviews r ON r.card_id = c.id "
        "WHERE r.due IS NULL OR r.due <= ?",
        (today,),
    ).fetchone()[0]
    reviewed_today = conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE last_reviewed = ?", (today,)
    ).fetchone()[0]
    avg_easiness = conn.execute("SELECT AVG(easiness) FROM reviews").fetchone()[0]
    return {
        "total_cards": total,
        "reviewed_cards": reviewed,
        "due_today": due,
        "reviewed_today": reviewed_today,
        "avg_easiness": round(avg_easiness, 2) if avg_easiness is not None else None,
    }
