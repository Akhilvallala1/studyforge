import Link from "next/link";
import { notFound } from "next/navigation";

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
        href="/"
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        &larr; All courses
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">{course.title}</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">{course.description}</p>
      <p className="mt-3 text-sm font-medium text-zinc-700 dark:text-zinc-300">
        {completedCount} of {lessons.length} lessons complete
      </p>

      <div className="mt-10 flex flex-col gap-8">
        {course.modules.map((module) => (
          <section key={module.id}>
            <h2 className="text-lg font-semibold">{module.title}</h2>
            <ul className="mt-3 flex flex-col gap-2">
              {module.lessons.map((lesson) => (
                <li key={lesson.id}>
                  <Link
                    href={`/courses/${course.id}/lessons/${lesson.id}`}
                    className="flex items-center gap-3 rounded-lg border border-zinc-200 px-4 py-3 transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-600"
                  >
                    <span
                      aria-hidden
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs ${
                        lesson.completed
                          ? "bg-emerald-600 text-white"
                          : "border border-zinc-300 dark:border-zinc-600"
                      }`}
                    >
                      {lesson.completed ? "✓" : ""}
                    </span>
                    <span className={lesson.completed ? "text-zinc-500 dark:text-zinc-400" : ""}>
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
