# StudyForge

**Open-source adaptive learning platform.** Turn a PDF, a link, or pasted notes into a personalized course with quizzes and spaced review. Self-hosted, your data stays yours. There is an AI tutor, scoped to the concepts you keep missing.

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
- [x] Chat with a tutor grounded in the course material
- [x] Work-it-out mode: the tutor stops one move short and hands that move back to you
- [x] Study planning: a deadline per course, the weekly rate it implies against the pace you are keeping across all your courses, days off, and a calendar file

All three are narrower than the lines above sound, in the same deliberate way Phase 2 is.

**The tutor is per concept, and it lives where the re-teaching does.** It is not a course-wide chat window. It sits inside the re-teaching panel on Today, underneath the explanation and the practice run, so you reach it for a concept you keep missing rather than from anywhere in the course. It answers from your course material, and it splits what it says into two registers, one of which states outright that the content is not from your course. It is never shown the answer key for a question you could still be asked and have your recall counted. Two daily caps bound it, 12 turns on one concept and 40 across all of them. A conversation is not a retrieval test: nothing the tutor writes touches a review card, a review log, or an attempt, so you cannot talk your way to a longer interval.

**Work-it-out mode is not a tutor that answers a question with a question.** It sets out everything in your course that bears on what you asked, carries it forward until exactly one move is left, and hands you that move. Whatever it withholds has to be answerable from the explanation directly above it, or it is a riddle rather than a step. It fades over two turns: the first withholds the final move, the second states the method for that move and withholds only the value it produces. After that the tutor answers outright, because below the second rung there is nothing left to withhold that is still worth asking for. The run is counted off the conversation itself rather than stored anywhere, and any ordinary answer resets it. It is two buttons in the panel rather than a setting: "Let me work it out" sits beside the ordinary Ask, which stays the default and is what Ctrl or Cmd and Enter sends. A toggle would claim to hold a choice that the next ordinary answer resets underneath it. A line below the buttons says what the second one does, and once you have spent both rungs it changes to say the next reply will be the full answer: the button stays live, that answer arrives as an ordinary reply rather than as an error, and the line clears itself on the following turn. The withheld move gets a heading of its own, directly under the explanation and above anything marked as not from your course, because what it asks for is grounded in the course material. Over the API it is `mode` set to `guided` on `POST /tutor/messages`.

**Study planning owns the rate new material goes in, and nothing else.** A course takes one deadline, labelled in your own words. From it you get two figures side by side: the lessons a week you need in order to finish this course's remaining ones in time, and the lessons a week you have actually been finishing across all your courses over the last 30 days. The second counts every completion anywhere rather than only the ones here, and so does the minimum of five it waits for before showing a number instead of a dash. Counted per course that minimum was not slow to reach but unreachable, because a course of four lessons can never produce five completions, which made the dash permanent however much work you did. The finish date comes from a third number again: this course's share of that throughput, which reduces to the rate you are putting into this course alone. So the date deliberately does not equal your remaining lessons divided by the rate on display, and the page names the share in the same sentence as the date rather than leaving the arithmetic looking broken. The rate is a fact about you, the date is a fact about this course. Projecting it off your whole throughput instead would answer when you would finish if you dropped everything else, which runs optimistic by roughly the number of courses you have open and never pessimistic, and optimistic is the wrong direction to be wrong in about a deadline. A course you have already finished gets no date rather than one reading today, and if you have cleared the minimum elsewhere but finished nothing here inside the window, the page says exactly that instead of implying you have never worked here. Days off are global rather than per course, since a day you are away is a day you are away from all of it. The date stays a projection and not a promise: the page sets it beside the deadline and draws no conclusion from the pair, because whether that gap is comfortable depends on the fortnight you have coming and nothing here knows anything about that. There is no threshold, no at-risk colouring, and no verdict. None of it moves a review: a deadline schedules no card, pulls nothing forward, and marks no concept at risk, because a card due after your exam is predicted at about 90% recall on the day of it.

**StudyForge cannot remind you.** There are no accounts here and no server running while you are not using it, so nothing in this program sends an email, a push notification, or a reminder of any kind. What the plan page offers instead is a calendar file: one all-day event on your deadline, which you download and open once. It is a file, not a feed your calendar keeps checking, because a calendar provider on the internet cannot reach a server on your own machine. Download it again after changing the date and it updates that same entry rather than adding a second one.

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

- **Frontend:** Next.js (App Router) + TypeScript + Tailwind - course creation, lessons, quizzes, progress, review sessions, concept map, re-teaching with its practice panel and tutor, and a per-course plan screen
- **Backend:** FastAPI (Python) - document ingestion, course generation, quiz grading, progress, FSRS review scheduling, re-teaching, remedial practice, the tutor, study planning and calendar export
- **Storage:** SQLite by default (zero-config), Postgres for multi-user deployments
- **LLM:** provider-agnostic adapter - Anthropic API first, Ollama for fully-local setups

Everything in the diagram is real now, the tutor chat and the SRS column included.

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

Once a course exists, Today (http://localhost:3000) shows what is due, http://localhost:3000/review runs a rating session over it, and each course has a Concept map tab showing how well you are holding each concept. A concept you keep missing is offered on Today with an explanation in plainer words, and a short practice run and the tutor sit inside that explanation. Each course also has a Plan tab, where a deadline gets you the weekly rate it implies beside the pace you have been keeping across all your courses.

If you're generating against a paid API, the run reports its estimated cost when it finishes, and http://localhost:3000/usage keeps a running total. See [Cost control](#cost-control) before you point it at a large PDF.

Prefer the raw API? The interactive docs live at http://localhost:8000/docs:

```bash
curl -X POST http://localhost:8000/courses/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "<paste your study material here>"}'
```

Or upload a PDF to `POST /courses/generate/pdf`. Run tests with `pytest backend/tests`.

## Cost control

One course is dozens of LLM calls, so a careless PDF upload can be a surprising bill. StudyForge meters its own API usage and shows you the running total instead of letting you find out later. Every call is recorded with its provider, model, stage (outline, lesson, remediation, or tutor), token counts, and estimated cost, and the same line is logged to the backend console as it happens.

- **Every page** in the web UI shows total estimated spend. **`/usage`** breaks it down by course and lists the recent calls.
- **Generating a course** reports what that run cost when it finishes.
- **The tutor** spends one call per question you ask, bounded by its own daily caps of 12 turns on a concept and 40 overall, so a long conversation cannot quietly run away with your budget. Study planning and remedial practice call no model at all.
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
