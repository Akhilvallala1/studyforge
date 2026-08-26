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
- [x] Web UI (Next.js)

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

## Architecture

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

- **Frontend:** Next.js (App Router) + TypeScript + Tailwind — course creation, lessons, quizzes, progress
- **Backend:** FastAPI (Python) — document ingestion, course generation, quiz grading, progress; FSRS scheduling is planned
- **Storage:** SQLite by default (zero-config), Postgres for multi-user deployments
- **LLM:** provider-agnostic adapter — Anthropic API first, Ollama for fully-local setups

The tutor chat in the diagram and the SRS column in storage are Phase 2–3 — not built yet.

## Getting started

You'll run two processes: the FastAPI backend and the Next.js frontend (Node.js 20+), one terminal each.

**Terminal 1 — backend:**

```bash
git clone https://github.com/Akhilvallala1/studyforge.git
cd studyforge/backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
# Windows: copy .env.example .env    macOS/Linux: cp .env.example .env
# then edit .env and set ANTHROPIC_API_KEY, or switch to Ollama
uvicorn app.main:app --reload   # .env is loaded automatically at startup
```

**Terminal 2 — frontend:**

```bash
cd studyforge/frontend
npm install
# Windows: copy .env.local.example .env.local    macOS/Linux: cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 and create your first course — paste text, drop in a URL, or upload a PDF. The frontend talks to the backend via `NEXT_PUBLIC_API_URL` in `frontend/.env.local` (defaults to http://localhost:8000); if you change the frontend's origin, update `STUDYFORGE_CORS_ORIGINS` in `backend/.env` to match.

Prefer the raw API? The interactive docs live at http://localhost:8000/docs:

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
