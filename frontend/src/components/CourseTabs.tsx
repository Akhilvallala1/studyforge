import Link from "next/link";

export type CourseTab = "lessons" | "concepts" | "plan";

const TAB_CLASS = "-mb-px border-b-2 pb-2.5 text-small transition-colors duration-fast ease-standard";
/**
 * `border-accent`: globals.css names "the active nav/tab indicator" as one of the
 * accent's three sanctioned uses (alongside focus rings and inline text links), so
 * this is the one border in scope that is allowed to reach for it instead of `ink`.
 */
const ACTIVE_CLASS = "border-accent font-semibold";
const INACTIVE_CLASS = "border-transparent text-ink-muted hover:text-ink";

/**
 * The course-level tab bar. `active` is passed in rather than read from the pathname
 * so this stays a server component: each page already knows which tab it is.
 *
 * History is rendered disabled rather than omitted. The artboard shows the tab and the
 * screen reads wrong with a gap where one was, but the route does not exist yet, so it
 * must not be a link that 404s. Plan sits beside it as a real link precisely because
 * that route does exist: the disabled treatment is about a missing route, not a house
 * style, and copying it for a page that ships would be the wrong lesson to take.
 */
export function CourseTabs({ courseId, active }: { courseId: number; active: CourseTab }) {
  return (
    <nav aria-label="Course views" className="mt-4 border-b border-line">
      <ul className="flex items-center gap-6">
        <li>
          <Link
            href={`/courses/${courseId}`}
            aria-current={active === "lessons" ? "page" : undefined}
            className={`${TAB_CLASS} block ${active === "lessons" ? ACTIVE_CLASS : INACTIVE_CLASS}`}
          >
            Lessons
          </Link>
        </li>
        <li>
          <Link
            href={`/courses/${courseId}/concepts`}
            aria-current={active === "concepts" ? "page" : undefined}
            className={`${TAB_CLASS} block ${active === "concepts" ? ACTIVE_CLASS : INACTIVE_CLASS}`}
          >
            Concept map
          </Link>
        </li>
        <li>
          <Link
            href={`/courses/${courseId}/plan`}
            aria-current={active === "plan" ? "page" : undefined}
            className={`${TAB_CLASS} block ${active === "plan" ? ACTIVE_CLASS : INACTIVE_CLASS}`}
          >
            Plan
          </Link>
        </li>
        <li>
          <span
            aria-disabled="true"
            title="Not built yet"
            className={`${TAB_CLASS} block cursor-not-allowed border-transparent text-ink-muted`}
          >
            History
          </span>
        </li>
      </ul>
    </nav>
  );
}
