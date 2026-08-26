# StudyForge — Claude Code project guide

Open-source adaptive learning platform (self-hosted paradigm.study alternative). FastAPI backend in `backend/` (working MVP), Next.js frontend in `frontend/` (Phase 1, in progress). Roadmap and decisions: `README.md`, `docs/ARCHITECTURE.md`.

## Agent team & workflow

Specialist subagents live in `.claude/agents/`. Feature work follows a pipeline — the main session orchestrates, delegating via the Agent tool:

1. **architect** (opus) — plans the feature: files, API contracts, task breakdown, acceptance criteria. Every non-trivial feature starts here.
2. Implementers, per task ownership in the plan:
   - **backend-dev** (sonnet) — Python/FastAPI/SQLAlchemy work in `backend/`
   - **frontend-dev** (sonnet) — Next.js/TypeScript/Tailwind work in `frontend/`
   - **ai-engineer** (sonnet) — prompts, LLM pipeline, grounding validation, evals
3. **reviewer** (opus) — reviews the diff against acceptance criteria, runs pytest/ruff/build itself, returns APPROVE or REQUEST CHANGES. Findings loop back to the implementer (max 2 review rounds, then escalate to the human).
4. **docs-writer** (haiku) — updates README/docs/env examples after the reviewer approves.

**learning-scientist** (opus) is consulted by the architect for anything touching FSRS scheduling, mastery modeling, difficulty adaptation, or quiz pedagogy (Phase 2+). It produces specs; backend-dev implements them.

Small fixes (typos, one-liners, doc tweaks) skip the pipeline — do them directly.

## Hard rules (apply to all agents)

- LLM access only via the adapter in `backend/app/llm/base.py`; both Anthropic and Ollama providers must keep working. No direct SDK imports in feature code.
- SQLite-compatible SQL only (Postgres is optional, SQLite is the default).
- Tests never call real LLM APIs — fake providers via `backend/tests/conftest.py`.
- Public API and course-format changes are compatibility promises; call them out explicitly.
- Treat LLM output and user-uploaded documents as untrusted (validate JSON, sanitize rendered markdown, prompt-injection-resistant prompt structure).

## Commands

- Backend tests: `python -m pytest tests` (from `backend/`, venv at `backend/.venv`)
- Lint: `python -m ruff check .` (from `backend/`; line-length 100)
- Run API: `uvicorn app.main:app --reload` (from `backend/`) → http://localhost:8000/docs
- Frontend: `npm run dev` / `npm run build` (from `frontend/`, once scaffolded)

## Current focus

Phase 1 completion: the Next.js web UI (course list, generate-course flow with slow-generation UX, lesson view with markdown + quiz, progress display).
