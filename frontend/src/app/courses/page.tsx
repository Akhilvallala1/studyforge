import Link from "next/link";

import { listCourses } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CoursesPage() {
  const courses = await listCourses();

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      <div className="mb-10 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">StudyForge</h1>
          <p className="mt-1 text-zinc-600 dark:text-zinc-400">
            Turn any material into a structured course with quizzes.
          </p>
        </div>
        {courses.length > 0 && (
          <Link
            href="/courses/new"
            className="shrink-0 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            New course
          </Link>
        )}
      </div>

      {courses.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-300 px-6 py-16 text-center dark:border-zinc-700">
          <p className="text-lg font-medium">No courses yet</p>
          <p className="mt-1 text-zinc-600 dark:text-zinc-400">
            Paste text, drop in a URL, or upload a PDF to get started.
          </p>
          <Link
            href="/courses/new"
            className="mt-6 inline-block rounded-lg bg-zinc-900 px-5 py-2.5 font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            Create your first course
          </Link>
        </div>
      ) : (
        <ul className="flex flex-col gap-4">
          {courses.map((course) => (
            <li key={course.id}>
              <Link
                href={`/courses/${course.id}`}
                className="block rounded-xl border border-zinc-200 p-5 transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-600"
              >
                <h2 className="text-lg font-medium">{course.title}</h2>
                <p className="mt-1 line-clamp-2 text-sm text-zinc-600 dark:text-zinc-400">
                  {course.description}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
