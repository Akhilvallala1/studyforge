# Architecture

This document describes the architecture of StudyForge. All four layers below exist today (Phase 1); the adaptive-learning and tutor pieces are still planned. It will evolve as those take shape.

## Overview

StudyForge has four layers:

1. **Web UI (Next.js)** - App Router + TypeScript + Tailwind, talking to the backend via `NEXT_PUBLIC_API_URL`. Current routes:
   - `/` - course list
   - `/courses/new` - create a course from pasted text, a URL, or a PDF upload
   - `/courses/[courseId]` - course detail with progress
   - `/courses/[courseId]/lessons/[lessonId]` - lesson content, quiz, mark complete
   - `/usage` - estimated API spend: totals, per-course breakdown, recent call log

   A site-wide banner renders the running spend total on every page, and the active cost alert on top of it. Tutor chat and a richer progress dashboard are planned, not built.
2. **Backend API (FastAPI)** - document ingestion, course generation orchestration, quiz grading, progress persistence, usage reporting. CORS origins are configurable via `STUDYFORGE_CORS_ORIGINS` (default `http://localhost:3000`); generation failures return a 502 with a JSON `detail` message. Spaced-repetition scheduling is planned. Generation endpoints:
   - `POST /courses/generate` - one or more sources (text, URL, or a mix). Request body has a `sources` list with `{kind, value, ref}` objects; `text` and `url` fields still work for backward compatibility but are deprecated and removed in 0.4.0. Limits: up to 5 sources and 150,000 characters total across all sources. Error response is structured differently for `sources` (a `detail` dict naming each failed source) versus legacy `text`/`url` (a bare string).
   - `POST /courses/generate/pdf` - one or more PDF files (submitted as multiple parts under the `file` field). Single-file uploads work exactly as before.
   Usage endpoints:
   - `GET /usage?limit=50` (clamped to 1-500) - all-time totals, a per-course breakdown, the `limit` most recent calls, alert state, and cap state. A `course_id` of `null` in the breakdown is the "Unattributed" bucket: calls from a run that failed before its course was saved.
   - `POST /usage/alert/ack` - records the current total as acknowledged, clearing the active alert.
   - The generate endpoints return a `usage` object with that run's estimated cost, the new total, and whether the alert is active. Hitting the spend cap surfaces as HTTP 402 with a structured `detail`.
3. **Metering layer** - `MeteredLLM` wraps a provider for the length of one generation run. Before each call it checks the optional hard cap; after each call, including a failed one that still burned tokens, it writes a row to `llm_calls` with the estimated cost and logs the same line to the server console. Generation code depends only on a `Meter` protocol, so it never reaches a provider directly and cost tracking cannot be bypassed by accident. Cost estimates come from a per-model pricing table in `app/costs.py`; unknown model ids fall back to env-configured default rates and mark the row approximate. Only paid providers are priced or capped, so Ollama and the fake provider always record zero and always run.
4. **LLM adapter** - a provider-agnostic interface with three implementations: Anthropic (Claude), Ollama (local models), and a deterministic fake for tests and QA.

**Current limits (Phase 1):** quiz answers are graded by exact case-insensitive string match, progress is per-lesson completion only, there is no auth or multi-user support yet, and the spend cap can overshoot by one call because the pre-call check cannot know what the call will cost.

## Data model (initial sketch)

- **Course** - title, description, source material references, ordered modules
- **Module** - ordered lessons
- **Lesson** - content (markdown), key concepts, generated quiz
- **Concept** - the unit of mastery tracking; lessons reference concepts, concepts can have prerequisites
- **QuizItem** - question, type (MCQ / short answer), answer key, concept reference
- **ReviewCard** - FSRS state per (user, concept): stability, difficulty, due date
- **Attempt** - user's answer history, used to adapt difficulty

Cost tracking adds two tables that exist today:

- **LlmCall** - one row per provider call: run id, course id, provider, model, stage, input/output tokens, estimated USD cost, and an `approximate` flag. The course id is a plain nullable integer rather than a foreign key, so usage history survives deleting the course it paid for.
- **AppSetting** - a small key/value store, currently holding the spend total at which the cost alert was last acknowledged.

Both are created by `create_all` at startup, so existing databases pick them up without a migration.

## Course generation pipeline

1. **Ingest** - PDF/URL/text (one or more sources) → cleaned text chunks with structure hints (headings, page numbers). Sources are requested fail-closed: if any fails (fetch error, unreadable PDF, unsafe URL), the whole request is refused before any LLM call runs.
2. **Outline** - LLM proposes modules and lessons from the chunks.
3. **Author** - per lesson: LLM writes the lesson content grounded in source chunks, extracts key concepts, generates quiz items.
4. **Review loop (planned, not built)** - a second LLM pass to validate quiz answerability and grounding, reducing hallucinated questions. The metering layer already reserves a `review` stage for it.

Every LLM call in steps 2 and 3 goes through the metering layer under a single `run_id`. The course id isn't known until the course is saved, so the run's `llm_calls` rows are backfilled with it afterwards; a run that fails before that point keeps a null course id and shows up as "Unattributed" in the usage breakdown.

## Adaptivity

- **Scheduling:** FSRS (open spaced-repetition algorithm) decides when each concept comes up for review.
- **Difficulty:** repeated failures on a concept trigger remedial content generation (simpler explanation, worked examples) and easier questions until mastery recovers.
- **Pathways:** the concept prerequisite graph gates lesson ordering; mastered prerequisites unlock the next lessons.

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| Default DB | SQLite | Zero-config self-hosting; Postgres optional for multi-user |
| SRS algorithm | FSRS | Open, well-studied, better retention modeling than SM-2 |
| LLM access | Adapter interface | Bring-your-own-key; local-first possible via Ollama |
| Course format | Markdown + JSON manifest | Git-friendly, portable, human-editable |
| Cost accounting | Estimate from reported tokens | No billing API to query, and estimates are local, immediate, and free; the trade is that they are approximate and never authoritative |
