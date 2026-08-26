# StudyForge

**Open-source adaptive learning platform.** Turn any material — PDFs, slides, links, notes — into a personalized course with quizzes, spaced review, and an AI tutor. Self-hosted, your data stays yours.

> Inspired by platforms like paradigm.study, but open: bring your own API key or run a local model, export everything, own your learning data.

## Why open source?

Closed adaptive-learning platforms lock in your content, your progress history, and your study data. StudyForge takes the opposite approach:

- **Self-hosted** — run it on your own machine or server; nothing leaves your control
- **Bring your own model** — Claude, or any local model via Ollama
- **No lock-in** — export courses and progress as Markdown, JSON, or Anki decks
- **Community courses** — share course templates as plain files in git, not a walled garden

## Core features (roadmap)

### Phase 1 — Content to course (MVP)
- [x] Upload a PDF / paste text or a URL
- [x] LLM structures it into a course: modules → lessons → key concepts
- [x] Auto-generated quizzes per lesson (multiple choice + short answer)
- [x] Progress tracking in SQLite
- [ ] Web UI (Next.js) — currently API-only

### Phase 2 — Adaptive learning
- [ ] Spaced repetition scheduling (FSRS algorithm) for review
- [ ] Difficulty adaptation: struggling on a concept → more scaffolding, remedial questions
- [ ] Knowledge graph per course: prerequisites, mastery per concept

### Phase 3 — AI tutor
- [ ] Chat with a tutor grounded in the course material
- [ ] Socratic mode: guides you to answers instead of giving them
- [ ] Study planning: deadlines, session scheduling, reminders

### Phase 4 — Community
- [ ] Course template format (portable, git-friendly)
- [ ] Public course registry
- [ ] Multi-user / classroom mode

## Architecture (planned)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Next.js web UI │────▶│  FastAPI backend  │────▶│  LLM        │
│  (courses,      │     │  (ingestion,      │     │  (Claude /  │
│   quizzes, chat)│     │   scheduling, API)│     │   Ollama)   │
└─────────────────┘     └────────┬─────────┘     └─────────────┘
                                 │
                        ┌────────▼─────────┐
                        │  SQLite/Postgres │
                        │  (courses,       │
                        │   progress, SRS) │
                        └──────────────────┘
```

- **Frontend:** Next.js + TypeScript + Tailwind
- **Backend:** FastAPI (Python) — document ingestion, course generation, FSRS scheduling
- **Storage:** SQLite by default (zero-config), Postgres for multi-user deployments
- **LLM:** provider-agnostic adapter — Anthropic API first, Ollama for fully-local setups

## Getting started

> ⚠️ Early days — the backend MVP works (API-only); the web UI is next.

```bash
git clone https://github.com/Akhilvallala1/studyforge.git
cd studyforge/backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # set ANTHROPIC_API_KEY, or switch to Ollama
uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs for the interactive API. Generate a course:

```bash
curl -X POST http://localhost:8000/courses/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "<paste your study material here>"}'
```

Or upload a PDF to `POST /courses/generate/pdf`. Run tests with `pytest backend/tests`.

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Good first areas: document ingestion (PDF parsing), quiz generation prompts, FSRS scheduling.

## License

[MIT](LICENSE)
