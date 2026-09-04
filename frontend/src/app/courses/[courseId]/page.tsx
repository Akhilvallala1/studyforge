import Link from "next/link";
import { notFound } from "next/navigation";

import { CourseTabs } from "@/components/CourseTabs";
import { PageHeader } from "@/components/ui/PageHeader";
import { ApiError, getCourse } from "@/lib/api";
import type { CourseDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function CoursePage(props: PageProps<"/courses/[courseId]">) {
  const { courseId } = await props.params;
  const id = Number(courseId);
  if (!Number.isInteger(id)) notFound();

  let course: CourseDetail;
  try {
    course = await getCourse(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const lessons = course.modules.flatMap((m) => m.lessons);
  const completedCount = lessons.filter((lesson) => lesson.completed).length;

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      <Link
        href="/courses"
        className="text-small text-ink-muted transition-colors duration-fast ease-standard hover:text-ink"
      >
        &larr; All courses
      </Link>

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
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-micro ${
                        lesson.completed
                          ? "bg-success-fill text-success-on-fill"
                          : "border border-line-strong"
                      }`}
                    >
                      {lesson.completed ? "✓" : ""}
                    </span>
                    {/*
                      ink-muted, NOT ink-subtle, and the difference is not cosmetic.
                      --sf-ink-subtle is zinc-500 in BOTH modes by deliberate design
                      (globals.css:48 and :280), so on the dark surface #0a0a0a it
                      measures 4.10:1 and misses the 4.5 AA floor for 16px text. This
                      span is the accessible name of the primary navigation link on the
                      page, and completed lessons are the majority of the list for any
                      learner making progress, so that is the worst place in the app to
                      lose contrast. ink-muted is zinc-600 light / zinc-400 dark: 7.72
                      and 7.55, never worse than the zinc-500/zinc-400 pair it replaces.
                    */}
                    <span className={lesson.completed ? "text-ink-muted" : ""}>
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
