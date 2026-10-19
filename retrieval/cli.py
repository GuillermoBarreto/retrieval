"""Command-line interface: import, quiz, generate, stats."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .cards import Card, parse_deck, render_deck
from .generate import CardGenerationError, generate_cards
from .scheduler import is_due, update
from .store import connect, due_cards, get_review_state, record_review, stats, upsert_cards

DEFAULT_DB = Path.home() / ".retrieval" / "retrieval.db"


def _db(path: str | None):
    db_path = Path(path) if path else DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return connect(db_path)


def cmd_import(args: argparse.Namespace) -> int:
    deck_path = Path(args.file)
    text = deck_path.read_text(encoding="utf-8")
    try:
        cards = parse_deck(text, source=str(deck_path))
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    with _db(args.db) as conn:
        new = upsert_cards(conn, cards)
    print(f"Imported {len(cards)} cards ({new} new).")
    return 0


def cmd_quiz(args: argparse.Namespace) -> int:
    today = date.today()
    with _db(args.db) as conn:
        cards = due_cards(conn, today=today, limit=args.limit)
        if not cards:
            print("Nothing due. Enjoy the day off. 🎉")
            return 0
        print(f"{len(cards)} card(s) due. Grade yourself 0-5 after each answer.\n")
        done = 0
        for card in cards:
            print(f"Q: {card.front}")
            input("  (press Enter to reveal) ")
            print(f"A: {card.back}\n")
            while True:
                raw = input("  Your grade (0-5, or 'q' to quit): ").strip().lower()
                if raw == "q":
                    print(f"\nReviewed {done} card(s). Progress saved.")
                    return 0
                if raw.isdigit() and 0 <= int(raw) <= 5:
                    break
                print("  Please enter 0-5 or 'q'.")
            state = get_review_state(conn, card.id)
            new_state = update(state, int(raw), today=today)
            record_review(conn, card.id, new_state, reviewed_on=today)
            done += 1
            print(f"  Next review in {new_state.interval} day(s).\n")
        print(f"Done! Reviewed {done} card(s).")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    notes = Path(args.notes).read_text(encoding="utf-8")
    try:
        generated = generate_cards(notes, model=args.model, max_cards=args.max_cards)
    except CardGenerationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    cards = [
        Card(id="", front=g["front"], back=g["back"], tags=tuple(g["tags"]), source=args.notes)
        for g in generated
    ]
    # stable ids derive from content; recompute through the deck round-trip
    cards = parse_deck(render_deck(cards), source=args.notes)
    if args.out:
        Path(args.out).write_text(render_deck(cards), encoding="utf-8")
        print(f"Wrote {len(cards)} cards to {args.out}.")
    else:
        with _db(args.db) as conn:
            new = upsert_cards(conn, cards)
        print(f"Generated {len(cards)} cards ({new} new) and saved them.")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    with _db(args.db) as conn:
        s = stats(conn)
    print(f"Total cards:     {s['total_cards']}")
    print(f"Cards reviewed:  {s['reviewed_cards']}")
    print(f"Due today:       {s['due_today']}")
    print(f"Reviewed today:  {s['reviewed_today']}")
    if s["avg_easiness"] is not None:
        print(f"Avg easiness:    {s['avg_easiness']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="retrieval",
        description="AI-powered spaced-repetition flashcards.",
    )
    parser.add_argument("--db", default=None, help="SQLite database path.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Import a markdown deck file.")
    p_import.add_argument("file", help="Path to the .md deck file.")
    p_import.set_defaults(func=cmd_import)

    p_quiz = sub.add_parser("quiz", help="Review due cards.")
    p_quiz.add_argument("--limit", type=int, default=50, help="Max cards per session.")
    p_quiz.set_defaults(func=cmd_quiz)

    p_gen = sub.add_parser("generate", help="Generate cards from notes via an LLM.")
    p_gen.add_argument("notes", help="Path to a text/markdown notes file.")
    p_gen.add_argument("--model", default="gpt-4o-mini", help="Model name.")
    p_gen.add_argument("--max-cards", type=int, default=20, help="Max cards to generate.")
    p_gen.add_argument("--out", default=None, help="Write deck to file instead of the DB.")
    p_gen.set_defaults(func=cmd_generate)

    p_stats = sub.add_parser("stats", help="Show deck statistics.")
    p_stats.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
