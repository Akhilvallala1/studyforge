import Link from "next/link";

import { CourseDeletionProvider, DeleteCourseButton } from "@/components/DeleteCourseButton";
import { listCourses } from "@/lib/api";

export const dynamic = "force-dynamic";

/**
 * THE CARD IS NO LONGER ONE BIG LINK, and it had to stop being one. Delete is a button,
 * and a button nested inside an anchor is invalid HTML that browsers recover from
 * inconsistently: the press would sometimes navigate to the course it was deleting. The
 * link now wraps only the title and description, and the button is its sibling, so each
 * control has exactly one meaning.
 *
 * The ids on the two "new course" controls are what the deletion provider focuses after a
 * row disappears. They are mutually exclusive, and which one exists is precisely what
 * changes when the last course goes, which is why focus is resolved by lookup at the
 * moment it is needed rather than captured beforehand.
 */
export default async function CoursesPage() {
  const courses = await listCourses();

  return (
    <CourseDeletionProvider>
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
              id="new-course"
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
              id="create-first-course"
              href="/courses/new"
              className="mt-6 inline-block rounded-lg bg-zinc-900 px-5 py-2.5 font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              Create your first course
            </Link>
          </div>
        ) : (
          <ul className="flex flex-col gap-4">
            {courses.map((course) => (
              <li
                key={course.id}
                className="rounded-xl border border-zinc-200 p-5 transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-600"
              >
                <Link href={`/courses/${course.id}`} className="block">
                  <h2 className="text-lg font-medium">{course.title}</h2>
                  <p className="mt-1 line-clamp-2 text-sm text-zinc-600 dark:text-zinc-400">
                    {course.description}
                  </p>
                </Link>
                <DeleteCourseButton courseId={course.id} title={course.title} />
              </li>
            ))}
          </ul>
        )}
      </main>
    </CourseDeletionProvider>
  );
}
