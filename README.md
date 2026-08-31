# StudyForge

**Open-source adaptive learning platform.** Turn a PDF, a link, or pasted notes into a personalized course with quizzes and spaced review. Self-hosted, your data stays yours. An AI tutor is on the roadmap, not built.

> Inspired by platforms like paradigm.study, but open: bring your own API key or run a local model, own your learning data.

## Why open source?

Closed adaptive-learning platforms lock in your content, your progress history, and your study data. StudyForge takes the opposite approach:

- **Self-hosted** - run it on your own machine or server; your courses and progress never leave it, though the material you feed it goes to your model provider unless that provider is Ollama
- **Bring your own model** - Claude, or any local model via Ollama
- **No lock-in** - your courses and progress live in a SQLite file you own, not behind anyone's account. Export to Markdown, JSON, or Anki decks is on the roadmap, not built
- **Community courses** (planned) - course templates as plain files in git, not a walled garden

## Core features (roadmap)

### Phase 1 - Content to course (MVP)
- [x] Upload a PDF / paste text or a URL
- [x] LLM structures it into a course: modules → lessons → key concepts
- [x] Auto-generated quizzes per lesson (multiple choice + short answer)
- [x] Progress tracking in SQLite
- [x] Web UI (Next.js)
- [x] API cost tracking, with a spend alert and an optional hard cap

### Phase 2 - Adaptive learning
- [x] Spaced repetition scheduling (FSRS-6) for review: a card per concept, a daily due queue, and a rating session at `/review`
- [x] Mastery per concept, drawn as a per-course concept map (mastered / solid / shaky / not started)
- [x] Re-teaching: a concept you keep missing is explained again in plainer words, with a worked example
- [x] Remedial practice: a short run at a weak concept, using the quiz questions the course already has
- [ ] Concept prerequisites

Three of these are narrower than they sound, deliberately, so you know before you go looking.

**Re-teaching is offered, not forced.** Miss a concept on two or more of its last five ratings and StudyForge offers to explain it again, at most once a week per concept. Taking the explanation does not reschedule the card and does not mark the concept learned: it keeps its stability, its lapses, and its due date, and it stays in the review queue. The lapse history is exactly what the trigger reads, so wiping it would make the next failure look like a first offence.

**Practice does not advance your schedule.** After reading the explanation you get a short run at the concept, built from quiz questions the course already has: no new questions are written for it and the feature makes no model call at all. It stops at two correct answers, at three answers, or when that concept's questions run out, whichever comes first, and there is one run per concept per study day. It is a study event and not an assessment, so it writes no review log and touches no column of the review card: not the due date, not the mastery bucket, not the "needs attention" flag, not the retention figure, and not where the concept sits in the review queue. Whether the re-teaching worked is measured at your next cold scheduled review, because that is the only place it can be measured honestly. Every answer is still recorded permanently as an attempt, and the only thing practice moves is which of that concept's questions comes up next, since one you have just answered rotates to the back. Practice lives inside the re-teaching panel, so the explanation is on screen before any question is asked, and it is deliberately not reachable from inside a review session, because that session is the cold measurement.

Practice attempts are stored with `source` set to `remedial_practice`, a third value on `GET /lessons/{lesson_id}/attempts` alongside `lesson_quiz` and `review_session`. Nothing was removed or renamed, but anything switching on that field needs to handle it.

**The concept map has no prerequisite arrows and no locked concepts.** Nothing in the system extracts real dependencies between concepts, and inferring them from lesson order would draw confident arrows that are frequently wrong. The map shows each concept grouped under the lesson that teaches it, coloured by how well you are holding it, and no more than that. It is not a prerequisite graph and it does not plot a path through the course.

### Phase 3 - AI tutor
- [ ] Chat with a tutor grounded in the course material
- [ ] Socratic mode: guides you to answers instead of giving them
- [ ] Study planning: deadlines, session scheduling, reminders

### Phase 4 - Community
- [ ] Export courses and progress as Markdown, JSON, or Anki decks
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

- **Frontend:** Next.js (App Router) + TypeScript + Tailwind - course creation, lessons, quizzes, progress, review sessions, concept map, re-teaching and its practice panel
- **Backend:** FastAPI (Python) - document ingestion, course generation, quiz grading, progress, FSRS review scheduling, re-teaching, remedial practice
- **Storage:** SQLite by default (zero-config), Postgres for multi-user deployments
- **LLM:** provider-agnostic adapter - Anthropic API first, Ollama for fully-local setups

The tutor chat in the diagram is Phase 3 and is not built yet. The rest of the diagram, the SRS column included, is real.

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

Once a course exists, Today (http://localhost:3000) shows what is due, http://localhost:3000/review runs a rating session over it, and each course has a Concept map tab showing how well you are holding each concept. A concept you keep missing is offered on Today with an explanation in plainer words, and a short practice run sits inside that explanation.

If you're generating against a paid API, the run reports its estimated cost when it finishes, and http://localhost:3000/usage keeps a running total. See [Cost control](#cost-control) before you point it at a large PDF.

Prefer the raw API? The interactive docs live at http://localhost:8000/docs:

```bash
curl -X POST http://localhost:8000/courses/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "<paste your study material here>"}'
```

Or upload a PDF to `POST /courses/generate/pdf`. Run tests with `pytest backend/tests`.

## Cost control

One course is dozens of LLM calls, so a careless PDF upload can be a surprising bill. StudyForge meters its own API usage and shows you the running total instead of letting you find out later. Every call is recorded with its provider, model, stage (outline, lesson, or remediation), token counts, and estimated cost, and the same line is logged to the backend console as it happens.

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

Contributions welcome - see [CONTRIBUTING.md](CONTRIBUTING.md). Good first areas: document ingestion (PDF parsing), quiz generation prompts, and the Phase 4 export formats (Markdown, JSON, Anki), which nothing has been written for yet.

## License

[MIT](LICENSE)
