import Link from "next/link";
import { notFound } from "next/navigation";

import { CourseTabs } from "@/components/CourseTabs";
import { ErrorState } from "@/components/ui/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
import { ApiError, getCourse } from "@/lib/api";
import type { CourseDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

const BACK_TO_COURSES_LINK = (
  <Link
    href="/courses"
    className="text-small text-ink-muted transition-colors duration-fast ease-standard hover:text-ink"
  >
    &larr; All courses
  </Link>
);

export default async function CoursePage(props: PageProps<"/courses/[courseId]">) {
  const { courseId } = await props.params;
  const id = Number(courseId);
  // Preserved exactly: a non-numeric id is a genuine 404, not a backend failure, and
  // must keep 404ing even though everything below it now treats a caught error as a
  // friendly inline message instead of a re-thrown 500. See courses/page.tsx for the
  // 200-vs-500 reasoning this page shares.
  if (!Number.isInteger(id)) notFound();

  let course: CourseDetail;
  try {
    course = await getCourse(id);
  } catch (err) {
    // A genuine 404 (course does not exist) must still 404. Everything else, backend
    // down, network failure, a 500 from the API, becomes the inline friendly message
    // instead of propagating into Next's generic error screen.
    if (err instanceof ApiError && err.status === 404) notFound();
    const message =
      err instanceof ApiError ? err.message : "Could not reach the server. Is the backend running?";
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        {BACK_TO_COURSES_LINK}
        {/*
          The failed fetch means we never learned the real course title, so PageHeader
          gets the generic "Course" rather than leaving the page with no h1 at all: a
          screen reader landing here previously had nothing to announce as the page's
          heading, unlike the courses list, whose PageHeader renders unconditionally
          before its own error/empty/list ternary.
        */}
        <PageHeader className="mt-4" title="Course" />
        <ErrorState className="mt-8" message={message} />
      </main>
    );
  }

  const lessons = course.modules.flatMap((m) => m.lessons);
  const completedCount = lessons.filter((lesson) => lesson.completed).length;

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      {BACK_TO_COURSES_LINK}

      <PageHeader className="mt-4" title={course.title} />

      <CourseTabs courseId={course.id} active="lessons" />

      <p className="mt-5 text-ui text-ink-muted">{course.description}</p>
      <p className="mt-3 text-small font-medium text-ink-muted">
        {completedCount} of {lessons.length} lessons complete
      </p>

      <div className="mt-8 flex flex-col gap-8">
        {course.modules.map((module) => (
          <section key={module.id}>
            <h2 className="text-subtitle">{module.title}</h2>
            <ul className="mt-3 flex flex-col gap-2">
              {module.lessons.map((lesson) => (
                <li key={lesson.id}>
                  <Link
                    href={`/courses/${course.id}/lessons/${lesson.id}`}
                    className="flex items-center gap-3 rounded-control border border-line px-4 py-3 transition-colors duration-fast ease-standard hover:border-line-hover"
                  >
                    <span
                      aria-hidden
                      /*
                        line-HOVER, not line-strong, for the empty marker. The name is
                        about hover but the value is what matters here: line-strong is
                        zinc-300 light / zinc-700 dark, and that dark step takes this 1px
                        ring from 2.56:1 down to 1.90:1 on the #0a0a0a page, which is
                        close enough to invisible that the list reads as "green dot" or
                        "nothing there" instead of filled or empty. line-hover is
                        zinc-400 / zinc-600: it restores the dark value the raw classes
                        had exactly, and is more visible than they were in light (2.62
                        against 1.48), so it is not worse in either mode.
                      */
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-micro ${
                        lesson.completed
                          ? "bg-success-fill text-success-on-fill"
                          : "border border-line-hover"
                      }`}
                    >
                      {lesson.completed ? "✓" : ""}
                    </span>
                    {/*
                      ink-muted, NOT ink-subtle, and the difference is not cosmetic. This
                      span is the accessible name of the primary navigation link on the
                      page, and completed lessons are the majority of the list for any
                      learner making progress, so that is the worst place in the app to
                      lose contrast. --sf-ink-subtle's dark value has moved since this was
                      last written (see globals.css, the dark-mode override block) and
                      now clears AA on its own (5.21:1 on the #0a0a0a page); ink-muted is
                      still the deliberate choice here regardless, at 7.72:1 light /
                      7.55:1 dark, because "clears the floor" and "is the best available
                      contrast for this element" are different bars and this element gets
                      the second one. Re-derive both figures from the built CSS before
                      trusting them again: this comment already went stale once.
                    */}
                    <span className={lesson.completed ? "text-ui text-ink-muted" : "text-ui"}>
                      {lesson.title}
                    </span>
                    {lesson.completed && <span className="sr-only">(completed)</span>}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}
