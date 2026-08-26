# StudyForge

**Open-source adaptive learning platform.** Turn any material - PDFs, slides, links, notes - into a personalized course with quizzes, spaced review, and an AI tutor. Self-hosted, your data stays yours.

> Inspired by platforms like paradigm.study, but open: bring your own API key or run a local model, export everything, own your learning data.

## Why open source?

Closed adaptive-learning platforms lock in your content, your progress history, and your study data. StudyForge takes the opposite approach:

- **Self-hosted** - run it on your own machine or server; nothing leaves your control
- **Bring your own model** - Claude, or any local model via Ollama
- **No lock-in** - export courses and progress as Markdown, JSON, or Anki decks
- **Community courses** - share course templates as plain files in git, not a walled garden

## Core features (roadmap)

### Phase 1 - Content to course (MVP)
- [x] Upload a PDF / paste text or a URL
- [x] LLM structures it into a course: modules → lessons → key concepts
- [x] Auto-generated quizzes per lesson (multiple choice + short answer)
- [x] Progress tracking in SQLite
- [x] Web UI (Next.js)
- [x] API cost tracking, with a spend alert and an optional hard cap

### Phase 2 - Adaptive learning
- [ ] Spaced repetition scheduling (FSRS algorithm) for review
- [ ] Difficulty adaptation: struggling on a concept → more scaffolding, remedial questions
- [ ] Knowledge graph per course: prerequisites, mastery per concept

### Phase 3 - AI tutor
- [ ] Chat with a tutor grounded in the course material
- [ ] Socratic mode: guides you to answers instead of giving them
- [ ] Study planning: deadlines, session scheduling, reminders

### Phase 4 - Community
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

- **Frontend:** Next.js (App Router) + TypeScript + Tailwind - course creation, lessons, quizzes, progress
- **Backend:** FastAPI (Python) - document ingestion, course generation, quiz grading, progress; FSRS scheduling is planned
- **Storage:** SQLite by default (zero-config), Postgres for multi-user deployments
- **LLM:** provider-agnostic adapter - Anthropic API first, Ollama for fully-local setups

The tutor chat in the diagram and the SRS column in storage are Phase 2–3 - not built yet.

## Getting started

You'll run two processes: the FastAPI backend and the Next.js frontend (Node.js 20+), one terminal each.

**Terminal 1 - backend:**

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

**Terminal 2 - frontend:**

```bash
cd studyforge/frontend
npm install
# Windows: copy .env.local.example .env.local    macOS/Linux: cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 and create your first course - paste text, drop in a URL, or upload a PDF. The frontend talks to the backend via `NEXT_PUBLIC_API_URL` in `frontend/.env.local` (defaults to http://localhost:8000); if you change the frontend's origin, update `STUDYFORGE_CORS_ORIGINS` in `backend/.env` to match.

If you're generating against a paid API, the run reports its estimated cost when it finishes, and http://localhost:3000/usage keeps a running total. See [Cost control](#cost-control) before you point it at a large PDF.

Prefer the raw API? The interactive docs live at http://localhost:8000/docs:

```bash
curl -X POST http://localhost:8000/courses/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "<paste your study material here>"}'
```

Or upload a PDF to `POST /courses/generate/pdf`. Run tests with `pytest backend/tests`.

## Cost control

One course is dozens of LLM calls, so a careless PDF upload can be a surprising bill. StudyForge meters its own API usage and shows you the running total instead of letting you find out later. Every call is recorded with its provider, model, stage (outline or lesson), token counts, and estimated cost, and the same line is logged to the backend console as it happens.

- **Every page** in the web UI shows total estimated spend. **`/usage`** breaks it down by course and lists the recent calls.
- **Generating a course** reports what that run cost when it finishes.
- **`STUDYFORGE_COST_ALERT_USD`** (default 10) raises a banner when cumulative spend crosses the threshold, with an Acknowledge button. It recurs: it fires again at every further multiple, so acknowledging at 10 USD does not silence 20.
- **`STUDYFORGE_COST_LIMIT_USD`** (unset by default, meaning no cap) is a hard cap. Once estimated spend reaches it, further paid calls are refused with HTTP 402. Ollama and the `fake` provider cost nothing and are never blocked.

Upgrading an existing install needs no migration: the two new tables are created on startup.

Two things worth being blunt about.

**These are estimates, not bills.** Costs are computed from the token counts the provider reports, priced against a table built into `backend/app/costs.py`. They are not billed amounts from Anthropic. A model that isn't in that table falls back to `STUDYFORGE_PRICE_DEFAULT_IN_USD` and `STUDYFORGE_PRICE_DEFAULT_OUT_USD` (5.00 and 25.00 per million tokens by default), and every figure derived from it is flagged approximate. Your provider's own dashboard remains the source of truth.

**The cap can overshoot by one call.** The check runs before a call and cannot know what that call will cost, so the call that trips the cap still completes and is billed. With the default model and the default 64k output limit, a single overshoot tops out around 1.60 USD; a more expensive model raises that ceiling proportionally. Set the cap below what you'd actually tolerate spending.

This tracks StudyForge's own API usage only. It has no view of anything else you spend on the same key.

## Contributing

Contributions welcome - see [CONTRIBUTING.md](CONTRIBUTING.md). Good first areas: document ingestion (PDF parsing), quiz generation prompts, FSRS scheduling.

## License

[MIT](LICENSE)
