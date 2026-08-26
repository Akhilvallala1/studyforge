# Architecture

This document describes the architecture of StudyForge. The first two layers exist today (Phase 1); the adaptive-learning and tutor pieces are still planned. It will evolve as those take shape.

## Overview

StudyForge has three layers:

1. **Web UI (Next.js)** - App Router + TypeScript + Tailwind, talking to the backend via `NEXT_PUBLIC_API_URL`. Current routes:
   - `/` - course list
   - `/courses/new` - create a course from pasted text, a URL, or a PDF upload
   - `/courses/[courseId]` - course detail with progress
   - `/courses/[courseId]/lessons/[lessonId]` - lesson content, quiz, mark complete

   Tutor chat and a richer progress dashboard are planned, not built.
2. **Backend API (FastAPI)** - document ingestion, course generation orchestration, quiz grading, progress persistence. CORS origins are configurable via `STUDYFORGE_CORS_ORIGINS` (default `http://localhost:3000`); generation failures return a 502 with a JSON `detail` message. Spaced-repetition scheduling is planned.
3. **LLM adapter** - a provider-agnostic interface with two implementations: Anthropic (Claude) and Ollama (local models).

**Current limits (Phase 1):** quiz answers are graded by exact case-insensitive string match, progress is per-lesson completion only, and there is no auth or multi-user support yet.

## Data model (initial sketch)

- **Course** - title, description, source material references, ordered modules
- **Module** - ordered lessons
- **Lesson** - content (markdown), key concepts, generated quiz
- **Concept** - the unit of mastery tracking; lessons reference concepts, concepts can have prerequisites
- **QuizItem** - question, type (MCQ / short answer), answer key, concept reference
- **ReviewCard** - FSRS state per (user, concept): stability, difficulty, due date
- **Attempt** - user's answer history, used to adapt difficulty

## Course generation pipeline

1. **Ingest** - PDF/URL/text → cleaned text chunks with structure hints (headings, page numbers).
2. **Outline** - LLM proposes modules and lessons from the chunks.
3. **Author** - per lesson: LLM writes the lesson content grounded in source chunks, extracts key concepts, generates quiz items.
4. **Review loop** - a second LLM pass validates quiz answerability and grounding (reduces hallucinated questions).

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
