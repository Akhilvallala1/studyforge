import Link from "next/link";
import { notFound } from "next/navigation";

import { LessonMarkdown } from "@/components/LessonMarkdown";
import { MarkCompleteButton } from "@/components/MarkCompleteButton";
import { QuizSection } from "@/components/QuizSection";
import { ErrorState } from "@/components/ui/ErrorState";
import { ApiError, getLesson } from "@/lib/api";
import type { LessonDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function LessonPage(
  props: PageProps<"/courses/[courseId]/lessons/[lessonId]">,
) {
  const { courseId, lessonId } = await props.params;
  const id = Number(lessonId);
  const course = Number(courseId);
  // Preserved exactly: non-numeric ids are a genuine 404, not a backend failure. See
  // courses/page.tsx for the 200-vs-500 reasoning this page shares.
  if (!Number.isInteger(id) || !Number.isInteger(course)) notFound();

  let lesson: LessonDetail;
  try {
    lesson = await getLesson(id);
  } catch (err) {
    // A genuine 404 (lesson does not exist) must still 404. Everything else, backend
    // down, network failure, a 500 from the API, becomes the inline friendly message
    // instead of propagating into Next's generic error screen.
    if (err instanceof ApiError && err.status === 404) notFound();
    const message =
      err instanceof ApiError ? err.message : "Could not reach the server. Is the backend running?";
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <Link
          href={`/courses/${courseId}`}
          className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          &larr; Back to course
        </Link>
        <ErrorState className="mt-8" message={message} />
      </main>
    );
  }

  // The API resolves a lesson by its own id, so /courses/2/lessons/1 would otherwise
  // render course 1's lesson under course 2's breadcrumb with a 200, and "Back to
  // course" would send the reader somewhere the lesson does not exist.
  //
  // Strict inequality, so a payload with no course_id at all fails closed. That is the
  // right direction but it has one bad symptom worth naming: against a backend too old
  // to send the key, course_id is undefined, undefined !== course is always true, and
  // EVERY lesson 404s including correctly paired ones. This project has already lost
  // hours twice to a uvicorn --reload that survived a branch switch and went on serving
  // pre-merge code, so the log line is not decoration: it is the difference between
  // "restart your backend" and a silent site-wide 404 with nothing to search for.
  // Cast because the type states the CONTRACT (course_id is always sent) while this
  // check exists for a violation of it. Widening the type instead would push a null
  // check onto every honest caller to describe a backend that is simply out of date.
  if ((lesson.course_id as number | undefined) === undefined) {
    console.error(
      `Lesson ${id} came back without a course_id. The backend is older than this ` +
        "frontend and cannot be scope-checked, so the lesson is being refused. Restart " +
        "the backend on current code.",
    );
  }
  if (lesson.course_id !== course) notFound();

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      <Link
        href={`/courses/${courseId}`}
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        &larr; Back to course
      </Link>

      <div className="mt-4 flex items-start justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">{lesson.title}</h1>
        <MarkCompleteButton lessonId={lesson.id} completed={lesson.completed} />
      </div>

      {lesson.concepts.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {lesson.concepts.map((concept) => (
            <li
              key={concept}
              className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
            >
              {concept}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-8">
        <LessonMarkdown content={lesson.content} title={lesson.title} />
      </div>

      {lesson.quiz.length > 0 && (
        <div className="mt-12">
          <QuizSection quiz={lesson.quiz} progress={lesson.quiz_progress} />
        </div>
      )}
    </main>
  );
}
