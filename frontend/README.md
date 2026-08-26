# StudyForge frontend

Next.js (App Router + TypeScript + Tailwind) web UI for the StudyForge backend. See the [root README](../README.md) for the full project setup.

## Running locally

The backend must be running first (default: http://localhost:8000 - see [`../backend`](../backend)).

```bash
npm install
cp .env.local.example .env.local   # Windows: copy .env.local.example .env.local
npm run dev
```

Then open http://localhost:3000.

`.env.local` sets `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000` if unset). If you serve the frontend from a different origin, set `STUDYFORGE_CORS_ORIGINS` on the backend to match.

## Structure

- `src/lib/api.ts` - the single typed API client; all backend calls go through it
- `src/lib/types.ts` - response types matching the backend contracts
- `src/app/` - routes: `/` (course list), `/courses/new` (create course), `/courses/[courseId]` (course detail), `/courses/[courseId]/lessons/[lessonId]` (lesson + quiz)
- `src/components/` - client components (generate form, quiz, markdown renderer)

`npm run build` type-checks and builds; `npm run lint` runs ESLint.
