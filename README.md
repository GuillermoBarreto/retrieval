# retrieval

AI-powered spaced-repetition flashcards for studying. Turn your study notes into quiz cards with an LLM, then review them on an SM-2 schedule — the algorithm behind SuperMemo and Anki.

## Why

Studying works best when you actively recall facts on a smart schedule instead of re-reading notes. `retrieval` gives you that loop in the terminal: paste notes in, get atomic flashcards out, and review only what's due.

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/GuillermoBarreto/retrieval.git
cd retrieval
pip install -r requirements.txt
```

Run the CLI with `python -m retrieval.cli`.

## Usage

**1. Import a deck** — a markdown file of `Q:`/`A:` blocks separated by `---`:

```markdown
Q: What does HTTP 429 mean?
A: Too Many Requests — the client is being rate limited.
Tags: http, web

---

Q: Name the SM-2 initial easiness factor.
A: 2.5
```

```bash
python -m retrieval.cli import my-deck.md
```

**2. Quiz yourself** — only due cards are shown, oldest first:

```bash
python -m retrieval.cli quiz
```

After each answer, grade your recall 0–5. Perfect recalls stretch the interval (1 → 6 → ~15 days…); forgotten cards reset to tomorrow.

**3. Generate cards from notes with an LLM:**

```bash
export RETRIEVAL_API_KEY=sk-...
python -m retrieval.cli generate my-notes.md
```

Any OpenAI-compatible endpoint works (the key always comes from the environment, never a file). Use `--out deck.md` to review the cards before importing.

**4. Check progress:**

```bash
python -m retrieval.cli stats
```

The review database lives at `~/.retrieval/retrieval.db` (override with `--db`).

## How it works

- `retrieval/cards.py` — flashcard model + markdown deck parsing (stable SHA-1 ids, so re-imports never duplicate).
- `retrieval/scheduler.py` — SM-2 spaced-repetition: easiness adapts per grade, quality < 3 resets the streak.
- `retrieval/store.py` — SQLite persistence for cards and review state.
- `retrieval/generate.py` — card generation via any OpenAI-compatible chat API (stdlib `urllib` only, no SDK needed).

## Roadmap

- [ ] Anki (`.apkg`) export
- [ ] Deck folders / multiple decks with per-deck stats
- [ ] Cloze-deletion card type (`{{c1::...}}`)
- [ ] Review heatmap (`retrieval heatmap`)
- [ ] Optional web UI for editing decks

## License

MIT — see [LICENSE](LICENSE).
