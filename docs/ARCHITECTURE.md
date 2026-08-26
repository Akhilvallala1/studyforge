# Architecture

This document describes the planned architecture for StudyForge. It will evolve as the MVP takes shape.

## Overview

StudyForge has three layers:

1. **Web UI (Next.js)** — course browsing, lesson view, quiz-taking, tutor chat, progress dashboard.
2. **Backend API (FastAPI)** — document ingestion, course generation orchestration, quiz grading, spaced-repetition scheduling, progress persistence.
3. **LLM adapter** — a provider-agnostic interface with two implementations: Anthropic (Claude) and Ollama (local models).

## Data model (initial sketch)

- **Course** — title, description, source material references, ordered modules
- **Module** — ordered lessons
- **Lesson** — content (markdown), key concepts, generated quiz
- **Concept** — the unit of mastery tracking; lessons reference concepts, concepts can have prerequisites
- **QuizItem** — question, type (MCQ / short answer), answer key, concept reference
- **ReviewCard** — FSRS state per (user, concept): stability, difficulty, due date
- **Attempt** — user's answer history, used to adapt difficulty

## Course generation pipeline

1. **Ingest** — PDF/URL/text → cleaned text chunks with structure hints (headings, page numbers).
2. **Outline** — LLM proposes modules and lessons from the chunks.
3. **Author** — per lesson: LLM writes the lesson content grounded in source chunks, extracts key concepts, generates quiz items.
4. **Review loop** — a second LLM pass validates quiz answerability and grounding (reduces hallucinated questions).

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
