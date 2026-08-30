import Link from "next/link";

import { ReteachConcept } from "@/components/ReteachConcept";
import { ApiError, getCourse, getRemediation, getReviewToday, listCourses } from "@/lib/api";
import type {
  CourseDetail,
  CourseSummary,
  LessonSummary,
  RemediationNote,
  ReviewToday,
} from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * How many recent courses "Next up" will look inside. Each one costs a request, and
 * the section is about what the learner is working on now, not an exhaustive search
 * of everything they have ever generated.
 */
const NEXT_UP_COURSES = 5;

/**
 * The study day as the learner would name it. `date` is the local YYYY-MM-DD key,
 * so it is read back in UTC to keep it from shifting a day, and the locale is fixed
 * rather than inherited so the string is stable wherever it renders.
 */
function formatStudyDay(key: string): string {
  const parsed = new Date(`${key}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return key;
  const weekday = parsed.toLocaleDateString("en-GB", { weekday: "long", timeZone: "UTC" });
  const dayMonth = parsed.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  });
  return `${weekday}, ${dayMonth}`;
}

function dueSentence(dueToday: number): string {
  if (dueToday === 0) return "Nothing is due for review";
  if (dueToday === 1) return "1 concept is due for review";
  return `${dueToday} concepts are due for review`;
}

/** "18 due now, about 9 minutes." plus the struggling clause only when there is one.
 *
 * Reads due_now, not due_today. A card rated Again is due in ten minutes, so it counts
 * toward the day's workload while a session cannot serve it yet. Saying "2 due now" off
 * the day figure and then showing an empty session is the bug this distinction fixes,
 * and when the two disagree the gap is explained rather than hidden. */
function sessionSentence(today: ReviewToday): string {
  if (today.due_now === 0) {
    const later = today.due_today;
    if (later > 0) {
      return `Nothing is due right now. ${later} ${
        later === 1 ? "concept comes" : "concepts come"
      } back later today.`;
    }
    return "Nothing is due right now. Concepts come back as their recall probability drops.";
  }
  const head = `${today.due_now} due now, about ${today.estimated_minutes} ${
    today.estimated_minutes === 1 ? "minute" : "minutes"
  }.`;
  const parts = [head];
  // The counts can also disagree while some cards are servable, and the tile above
  // shows the larger number, so account for the difference here too rather than only
  // when nothing at all is due.
  const later = today.due_today - today.due_now;
  if (later > 0) {
    parts.push(`${later} more ${later === 1 ? "comes" : "come"} back later today.`);
  }
  if (today.struggling_due > 0) {
    parts.push(`${today.struggling_due} of these you have struggled with before.`);
  }
  return parts.join(" ");
}

interface NextUp {
  course: CourseDetail;
  lesson: LessonSummary;
}

/** The first unfinished lesson across the learner's most recent courses, if any. */
async function findNextUp(courses: CourseSummary[]): Promise<NextUp | null> {
  const recent = courses.slice(0, NEXT_UP_COURSES);
  // One failing course must not take the whole Today screen down with it.
  const details = await Promise.all(recent.map((course) => getCourse(course.id).catch(() => null)));
  for (const course of details) {
    if (!course) continue;
    for (const courseModule of course.modules) {
      for (const lesson of courseModule.lessons) {
        if (!lesson.completed) return { course, lesson };
      }
    }
  }
  return null;
}

function Stat({
  value,
  label,
  emphasis,
  title,
  note,
}: {
  value: string;
  label: string;
  emphasis?: boolean;
  title?: string;
  note?: string;
}) {
  return (
    <div className="flex flex-col-reverse">
      <dt className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{label}</dt>
      <dd
        title={title}
        className={`font-mono text-[22px] font-medium tabular-nums ${
          emphasis ? "text-emerald-600 dark:text-emerald-500" : ""
        } ${title ? "cursor-help" : ""}`}
      >
        {value}
        {/* `title` alone is not reliably announced, so the same explanation is in the
            accessibility tree as text. */}
        {note && <span className="sr-only"> {note}</span>}
      </dd>
    </div>
  );
}

function RetentionStat({ today }: { today: ReviewToday }) {
  if (today.retention === null) {
    const note = `Not enough review history yet: ${today.sample_size} ${
      today.sample_size === 1 ? "review counts" : "reviews count"
    } so far. A percentage from a handful of reviews could only read 0, 50 or 100 and would swing day to day, so it is held back until there is enough.`;
    return <Stat value="–" label="Retained at review" title={note} note={note} />;
  }
  return (
    <Stat
      value={`${Math.round(today.retention * 100)}%`}
      label="Retained at review"
      emphasis
      title={`Over the last 30 days, across ${today.sample_size} reviews of concepts that were genuinely due.`}
    />
  );
}

export default async function TodayPage() {
  let courses: CourseSummary[] = [];
  let today: ReviewToday | null = null;
  let nextUp: NextUp | null = null;
  let attentionNotes: (RemediationNote | null)[] = [];
  let loadError: string | null = null;

  try {
    courses = await listCourses();
    // A learner with nothing generated has nothing to review, and the Today numbers
    // would all read zero. Skip them and show the first-run panel instead.
    if (courses.length > 0) {
      [today, nextUp] = await Promise.all([getReviewToday(), findNextUp(courses)]);
      // One free read per flagged concept, so the button can say whether an explanation
      // already exists rather than finding out by asking for one. Same fan-out shape as
      // findNextUp, and one failure must not take the screen down with it.
      attentionNotes = await Promise.all(
        today.needs_attention.map((entry) => getRemediation(entry.card_id).catch(() => null)),
      );
    }
  } catch (err) {
    loadError =
      err instanceof ApiError ? err.message : "Could not reach the server. Is the backend running?";
  }

  if (loadError) {
    return (
      <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
        <h1 className="text-3xl font-bold tracking-tight">Today</h1>
        <p
          role="alert"
          className="mt-8 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          {loadError}
        </p>
      </main>
    );
  }

  if (courses.length === 0) {
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <div className="mb-10">
          <h1 className="text-3xl font-semibold tracking-tight">StudyForge</h1>
          <p className="mt-1 text-zinc-600 dark:text-zinc-400">
            Turn any material into a structured course with quizzes.
          </p>
        </div>
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
      </main>
    );
  }

  // Unreachable once courses exist, but it keeps the compiler honest about the null.
  if (!today) return null;

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
      <h1 className="text-3xl font-bold tracking-tight">Today</h1>
      <p className="mt-1.5 text-sm text-zinc-600 dark:text-zinc-400">
        {formatStudyDay(today.date)} &middot; {dueSentence(today.due_today)}
      </p>

      <section
        aria-labelledby="review-session-heading"
        className="mt-6 overflow-hidden rounded-lg border border-zinc-200 dark:border-zinc-800"
      >
        <div className="flex flex-wrap items-center justify-between gap-5 border-b border-zinc-200 bg-zinc-50 px-[22px] py-5 dark:border-zinc-800 dark:bg-zinc-900">
          <div>
            <h2 id="review-session-heading" className="text-[17px] font-semibold">
              Review session
            </h2>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
              {sessionSentence(today)}
            </p>
          </div>
          {today.due_now > 0 && (
            <Link
              href="/review"
              className="shrink-0 whitespace-nowrap rounded-lg bg-zinc-900 px-[18px] py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              Start review
            </Link>
          )}
        </div>
        <dl className="flex flex-wrap gap-7 px-[22px] py-4">
          <Stat value={String(today.due_today)} label="Due today" />
          <Stat value={String(today.due_this_week)} label="This week" />
          <RetentionStat today={today} />
          <Stat value={String(today.day_streak)} label="Day streak" />
        </dl>
      </section>

      {today.needs_attention.length > 0 && (
        <section aria-labelledby="needs-attention-heading">
          <h2 id="needs-attention-heading" className="mt-8 text-[15px] font-semibold">
            Needs attention
          </h2>
          {/* Offered, not automatic, and it does not gate the next review: saying it
              would re-teach these "before testing them again" promised a reset that
              nothing in the scheduler performs. */}
          <p className="mt-1 text-[13px] text-zinc-500 dark:text-zinc-400">
            Concepts you have missed more than once. Ask StudyForge to explain one a
            different way; it stays in your review queue either way.
          </p>
          <ul className="mt-3.5 flex flex-col gap-2">
            {today.needs_attention.map((entry, index) => (
              <ReteachConcept
                key={entry.concept_key}
                entry={entry}
                initialNote={attentionNotes[index] ?? null}
              />
            ))}
          </ul>
        </section>
      )}

      {nextUp && (
        <section aria-labelledby="next-up-heading">
          <h2 id="next-up-heading" className="mt-7 text-[15px] font-semibold">
            Next up
          </h2>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-zinc-200 px-[18px] py-4 dark:border-zinc-800">
            <div>
              <div className="text-[15px] font-medium">{nextUp.lesson.title}</div>
              <div className="mt-0.5 text-[13px] text-zinc-500 dark:text-zinc-400">
                Next unfinished lesson &middot; {nextUp.course.title}
              </div>
            </div>
            <Link
              href={`/courses/${nextUp.course.id}/lessons/${nextUp.lesson.id}`}
              className="shrink-0 rounded-lg border border-zinc-300 px-4 py-1.5 text-[13px] font-medium transition-colors hover:border-zinc-500 dark:border-zinc-700 dark:hover:border-zinc-500"
            >
              Continue
            </Link>
          </div>
        </section>
      )}
    </main>
  );
}
