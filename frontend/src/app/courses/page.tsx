import Link from "next/link";

import { CourseDeletionProvider, DeleteCourseButton } from "@/components/DeleteCourseButton";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
import { ApiError, listCourses } from "@/lib/api";
import type { CourseSummary } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * 200-with-inline-error, not a thrown 500, and this decision is shared by the other two
 * pages in this batch (courses/[courseId], lessons/[lessonId]) plus the two pages that
 * already worked this way before this change (/ and /usage). A bare re-thrown fetch
 * failure used to reach Next's own error boundary, which renders a generic "A server
 * error occurred" screen with an opaque digest and genuinely returns 500: correct for a
 * bug in OUR code, wrong for "the backend is not running", which is an expected,
 * recoverable condition for a self-hoster and not a defect in this page.
 *
 * The alternative, catch the error and still respond 500 with our own body, was
 * considered and rejected: it would mean every one of the five page types on this site
 * behaves differently under "backend down" depending on which one you loaded first,
 * which is a worse failure mode for a self-hoster to debug than the status code being
 * arguably wrong. A monitoring probe watching a single route will treat a self-hosted
 * study tool as up as long as the Next process answers, backend or no; that is an
 * existing property of / and /usage this change does not newly introduce, and fixing it
 * properly means a dedicated health-check endpoint, not a per-page status code, which is
 * out of scope here.
 */

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
  let courses: CourseSummary[] = [];
  let loadError: string | null = null;
  try {
    courses = await listCourses();
  } catch (err) {
    loadError =
      err instanceof ApiError ? err.message : "Could not reach the server. Is the backend running?";
  }

  return (
    <CourseDeletionProvider>
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <PageHeader
          className="mb-10"
          title="StudyForge"
          description="Turn any material into a structured course with quizzes."
          actions={
            // Suppressed on error too: a load failure means we do not reliably know
            // whether there are zero courses or many, so neither "new course" id below
            // is a truthful thing to offer, and rendering one here would put it on
            // screen alongside the empty-state link that error branch also skips.
            !loadError &&
            courses.length > 0 && (
              <Link id="new-course" href="/courses/new" className={PRIMARY_LINK_CLASSES}>
                New course
              </Link>
            )
          }
        />

        {loadError ? (
          <ErrorState message={loadError} />
        ) : courses.length === 0 ? (
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
