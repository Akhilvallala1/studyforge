import Link from "next/link";
import { notFound } from "next/navigation";

import { LessonMarkdown } from "@/components/LessonMarkdown";
import { MarkCompleteButton } from "@/components/MarkCompleteButton";
import { QuizSection } from "@/components/QuizSection";
import { ErrorState } from "@/components/ui/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
import { ApiError, getLesson } from "@/lib/api";
import type { LessonDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * Shared by both the error branch and the success path below. Previously the identical
 * JSX was pasted verbatim in both places; factored out here the same way the sibling
 * course page factored its own back link into BACK_TO_COURSES_LINK, so the two copies
 * cannot silently drift apart from each other again.
 */
function backToCourseLink(courseId: string) {
  return (
    <Link
      href={`/courses/${courseId}`}
      className="text-small text-ink-muted transition-colors duration-fast ease-standard hover:text-ink"
    >
      &larr; Back to course
    </Link>
  );
}

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
        {backToCourseLink(courseId)}
        {/*
          The failed fetch means we never learned the real lesson title, so PageHeader
          gets the generic "Lesson" and no `actions`. The success path below renders the
          same primitive with the real title and MarkCompleteButton passed as `actions`;
          that is the only difference between the two branches now. (It used to hand-roll
          its own <h1> next to the button instead of using PageHeader at all; see the
          restyle comment on the success branch below for why that changed.)
        */}
        <PageHeader className="mt-4" title="Lesson" />
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
      {backToCourseLink(courseId)}

      {/*
        Previously a hand-rolled <h1 className="text-3xl ...">, kept separate from
        PageHeader specifically so the error branch above (with no real title to show)
        would not have to change alongside it. PageHeader has an `actions` slot,
        already used by courses/page.tsx's "New course" link, and this is exactly that
        shape: a title with one button beside it. Moving onto it removes the duplicated
        title styling and puts this page's success and error branches on the same
        primitive, differing only in the title text and in `actions`. Update the
        comment on the error branch above (and
        concepts/page.tsx's comment on this page's old exception) if this changes again.
      */}
      <PageHeader
        className="mt-4"
        title={lesson.title}
        actions={<MarkCompleteButton lessonId={lesson.id} completed={lesson.completed} />}
      />

      {lesson.concepts.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {lesson.concepts.map((concept) => (
            <li
              key={concept}
              /*
                text-small, not text-micro: a concept name is a proper noun or ordinary
                sentence-case phrase, and text-micro is uppercase and tracked-out by
                convention (see globals.css's type scale comment), which would silently
                shout every concept in caps. Same reasoning ReviewSession's "Missed last
                time" pill uses, on the same size step.
              */
              className="rounded-full border border-line bg-surface-sunken px-3 py-1 text-small font-medium text-ink-muted"
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
