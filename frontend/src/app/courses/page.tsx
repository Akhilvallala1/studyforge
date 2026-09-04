import Link from "next/link";

import { CourseDeletionProvider, DeleteCourseButton } from "@/components/DeleteCourseButton";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { listCourses } from "@/lib/api";

export const dynamic = "force-dynamic";

/**
 * Shared with both "new course" entry points below rather than routed through Button:
 * Button only wraps a native <button>, and both of these have to be real links so the
 * empty-list focus restore (see DeleteCourseButton) can find them by id and Next can
 * prefetch the route. The string is Button's own BASE + primary + md, kept in sync by
 * hand until a link-flavoured variant of that primitive exists.
 */
const PRIMARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control bg-fill " +
  "px-4 py-2 text-ui font-medium text-on-fill transition-colors duration-fast ease-standard " +
  "hover:bg-fill-hover";

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
        <PageHeader
          className="mb-10"
          title="StudyForge"
          description="Turn any material into a structured course with quizzes."
          actions={
            courses.length > 0 && (
              <Link id="new-course" href="/courses/new" className={PRIMARY_LINK_CLASSES}>
                New course
              </Link>
            )
          }
        />

        {courses.length === 0 ? (
          <EmptyState
            title="No courses yet"
            description="Paste text, drop in a URL, or upload a PDF to get started."
            action={
              <Link id="create-first-course" href="/courses/new" className={PRIMARY_LINK_CLASSES}>
                Create your first course
              </Link>
            }
          />
        ) : (
          <ul className="flex flex-col gap-4">
            {courses.map((course) => (
              <li key={course.id}>
                <Card className="transition-colors duration-fast ease-standard hover:border-line-hover">
                  <Link href={`/courses/${course.id}`} className="block">
                    <h2 className="text-subtitle">{course.title}</h2>
                    <p className="mt-1 line-clamp-2 text-ui text-ink-muted">
                      {course.description}
                    </p>
                  </Link>
                  <DeleteCourseButton courseId={course.id} title={course.title} />
                </Card>
              </li>
            ))}
          </ul>
        )}
      </main>
    </CourseDeletionProvider>
  );
}
