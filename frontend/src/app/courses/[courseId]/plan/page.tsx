import Link from "next/link";
import { notFound } from "next/navigation";

import { CourseTabs } from "@/components/CourseTabs";
import { DaysOffControl } from "@/components/DaysOffControl";
import { DeadlineForm } from "@/components/DeadlineForm";
import { ApiError, coursePlanIcsUrl, getCoursePlan, listDaysOff } from "@/lib/api";
import { formatDayKey } from "@/lib/copy";
import type { CoursePlan, DayOff } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * The plan screen: how fast new material has to go in, and how fast it actually is.
 *
 * THE SENTENCE THIS WHOLE PAGE IS BUILT AROUND: study planning owns the rate new
 * material enters, and FSRS keeps owning everything already in. A deadline changes
 * nothing about the review schedule, and nothing here may imply that it does. No screen
 * on this route says a concept needs review because of a deadline, offers to review
 * cards early, or colours anything as at risk.
 *
 * That is not a stylistic preference, it is what the data supports. A card's due date is
 * by construction the day its recall decays to about 90%, so a card scheduled past the
 * deadline is predicted at or above 90% ON the deadline day. The set of cards a deadline
 * puts at risk is empty, not merely small, which is why the plan payload carries no
 * concept counts and why this page must not go and fetch them from elsewhere.
 *
 * THE TWO RATES ARE THE PRODUCT and they are shown without a verdict. There is no
 * threshold, no "this is impossible", no amber state, and no motivational framing. Only
 * the learner knows what their next week looks like, so the conclusion is theirs to
 * draw and the page's job is to put the two numbers where they can draw it.
 *
 * A server component throughout, like the concepts page. CourseTabs takes `active` as a
 * prop precisely so it never reads the pathname, and the two mutations live in small
 * client components that refresh this route when they land.
 */

/**
 * A weekly rate as one decimal, matching the figure the .ics description quotes.
 *
 * A SMALL NONZERO RATE DOES NOT ROUND TO ZERO. One lesson left and a deadline six months
 * out is 0.04 a week, and toFixed(1) renders that as "0.0", so the prose read "you need
 * about 0.0 lessons a week to get through the remaining 1 lesson": a number telling the
 * learner they need to do nothing, about work they still have to do. Zero itself is a
 * real answer and keeps its own spelling, reachable only when no lessons remain.
 */
const RATE_FLOOR = 0.05;

function formatRate(value: number): string {
  if (value === 0) return "0";
  if (value < RATE_FLOOR) return "less than 0.1";
  return value.toFixed(1);
}

/**
 * The same rate as it reads inside a sentence.
 *
 * "about" has to come off the floor case or the prose says "about less than 0.1", which
 * hedges a bound that is already exact. Everything else keeps it, because a figure
 * rounded to one decimal is an approximation and should say so.
 */
function ratePhrase(value: number): string {
  if (value !== 0 && value < RATE_FLOOR) return "less than 0.1";
  return `about ${formatRate(value)}`;
}

/** "your Midterm" when they named it, "your deadline" when they did not. */
function deadlineName(plan: CoursePlan): string {
  const label = plan.deadline_label?.trim();
  return label ? `your ${label}` : "your deadline";
}

/** Sentence-initial form of the same phrase. */
function capitalizedDeadlineName(plan: CoursePlan): string {
  const name = deadlineName(plan);
  return name.charAt(0).toUpperCase() + name.slice(1);
}

function lessonCount(count: number): string {
  return count === 1 ? "1 lesson" : `${count} lessons`;
}

function dayCount(count: number): string {
  return count === 1 ? "1 day" : `${count} days`;
}

/**
 * Where the deadline sits relative to today, and how much study time is left before it.
 *
 * Never says a day is "left to prepare" or similar: the days counted here are days new
 * lessons can go in on, which is the only thing this feature measures.
 */
function deadlineSentence(plan: CoursePlan): string {
  if (plan.deadline === null || plan.days_until === null) return "";
  const when = formatDayKey(plan.deadline);
  const name = capitalizedDeadlineName(plan);
  if (plan.status === "passed") {
    return plan.days_until === -1 ? `${name} was yesterday.` : `${name} was on ${when}.`;
  }
  if (plan.days_until === 0) return `${name} is today, ${when}.`;
  if (plan.days_until === 1) return `${name} is tomorrow, ${when}.`;
  return `${name} is in ${dayCount(plan.days_until)}, on ${when}.`;
}

/** "24 study days left before it, after the 2 days you have marked off." */
function studyDaysSentence(plan: CoursePlan): string | null {
  if (plan.status !== "active" || plan.available_days === null) return null;
  const head = `That leaves ${dayCount(plan.available_days)} to study on before it`;
  const off = plan.days_off_in_window ?? 0;
  if (off > 0) {
    return `${head}, once the ${dayCount(off)} you have marked off are taken out. The deadline day itself is not counted, since that is the day you need to already know it.`;
  }
  return `${head}. The deadline day itself is not counted, since that is the day you need to already know it.`;
}

/**
 * Why there is a dash where the required rate would be, written from `reason`.
 *
 * Read off the server's code rather than reconstructed from the other fields, because
 * three of the four cases are the same arithmetic (no study days left before the date)
 * and only the code separates a deadline that is today from one that has passed from a
 * window the learner has marked entirely off.
 */
function requiredDashNote(plan: CoursePlan): string {
  switch (plan.reason) {
    case "deadline_today":
      return `${capitalizedDeadlineName(plan)} is today, so there are no study days left before it and no weekly rate to spread the remaining lessons across.`;
    case "deadline_passed":
      return `${capitalizedDeadlineName(plan)} has passed, so there is no longer a rate to hit for it.`;
    case "all_days_off":
      return `Every day between now and ${deadlineName(plan)} is marked as a day off, so there is no study time left to spread the remaining lessons across. Unmark one and a rate appears.`;
    default:
      return "This course has no deadline, so there is no rate to hit. Set one below and this fills in.";
  }
}

/**
 * One figure. A dash carries NO tooltip, deliberately: what the dash means is written in
 * prose a few lines below it inside the same box, and repeating it in a `title` would put
 * the same sentence into the accessibility tree twice. RetentionStat on the Today screen
 * uses a tooltip because it has nowhere to put the prose; here there is room.
 */
function PlanStat({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex min-w-[8.5rem] flex-col-reverse">
      <dt className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{label}</dt>
      <dd className="font-mono text-[26px] font-medium tabular-nums">{value}</dd>
    </div>
  );
}

/**
 * The two rates, in prose, with no comparison drawn between them.
 *
 * Reads as a report and stops: "you need about 5 a week, you have averaged 2, at that
 * pace you finish on the 19th, your exam is on the 14th." Whether that is fine or a
 * disaster depends entirely on what the learner's next fortnight looks like, which this
 * program has no way of knowing, so it does not say.
 */
function paceSentences(plan: CoursePlan): string[] {
  const lines: string[] = [];

  if (plan.lessons_remaining === 0) {
    lines.push(
      `All ${lessonCount(plan.lessons_total)} in this course are finished, so there is no new material left to fit in.`,
    );
  } else if (plan.required_per_week !== null) {
    lines.push(
      `You need ${ratePhrase(plan.required_per_week)} lessons a week to get through the remaining ${lessonCount(plan.lessons_remaining)} before ${deadlineName(plan)}.`,
    );
  } else {
    lines.push(requiredDashNote(plan));
  }

  if (plan.observed_per_week !== null) {
    lines.push(
      `Over the last 30 days you have averaged ${ratePhrase(plan.observed_per_week)} lessons a week in this course.`,
    );
  } else if (plan.observed_sample === 0) {
    lines.push(
      "You have not finished a lesson in this course in the last 30 days, so there is no pace to measure yet.",
    );
  } else {
    lines.push(
      `You have finished ${lessonCount(plan.observed_sample)} in this course in the last 30 days, which is not enough to call a pace yet: a rate off a handful of lessons would swing every time one more landed.`,
    );
  }

  if (plan.lessons_remaining > 0 && plan.finish_projection !== null) {
    const finish = `At that pace you finish on ${formatDayKey(plan.finish_projection)}`;
    lines.push(
      plan.deadline !== null && plan.status === "active"
        ? `${finish}; ${deadlineName(plan)} is on ${formatDayKey(plan.deadline)}.`
        : `${finish}.`,
    );
  }

  return lines;
}

/**
 * The passed state, which is where this feature is most clearly not a cramming tool.
 *
 * The deadline going by changes nothing at all: no card was pulled forward before it and
 * none is dropped after it. Saying so is the point of the panel.
 */
function PassedPanel({ plan }: { plan: CoursePlan }) {
  return (
    <section className="mt-5 rounded-lg border border-zinc-200 px-5 py-4 dark:border-zinc-800">
      <p className="text-[15px] font-medium">
        {deadlineSentence(plan)} Your reviews continue, because you still know this.
      </p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400">
        Nothing was rescheduled when you set the date and nothing was rescheduled when it
        passed. Your concepts come back when your memory of them says so, exactly as they
        would have without a deadline. Clear it below, or set the next one.
      </p>
    </section>
  );
}

function CalendarSection({ plan }: { plan: CoursePlan }) {
  return (
    <section aria-labelledby="plan-calendar-heading">
      <h2 id="plan-calendar-heading" className="mt-9 text-[15px] font-semibold">
        Put it in your calendar
      </h2>
      <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400">
        StudyForge cannot notify you. There are no accounts here and no server running when
        you are not using it, so nothing in this program can send you an email, a push
        notification, or a reminder of any kind, and that is by design. What it can do is
        hand you a calendar file, and let the calendar you already use do the reminding.
      </p>
      {plan.deadline === null ? (
        <p className="mt-3 rounded-lg border border-zinc-200 px-5 py-4 text-[13px] text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
          Set a deadline above and the calendar file appears here.
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-zinc-200 px-5 py-4 dark:border-zinc-800">
          <p className="max-w-lg text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400">
            One all-day event on {formatDayKey(plan.deadline)}, with where you stand written
            into it. This is a file you download and open once, not an address your calendar
            keeps checking: a calendar provider on the internet cannot reach a server running
            on your own machine. Download it again after changing the date and it updates the
            same entry rather than adding a second one.
          </p>
          <a
            href={coursePlanIcsUrl(plan.course_id)}
            className="shrink-0 whitespace-nowrap rounded-lg border border-zinc-300 px-4 py-2 text-[13px] font-medium transition-colors hover:border-zinc-500 dark:border-zinc-700 dark:hover:border-zinc-500"
          >
            Download .ics
          </a>
        </div>
      )}
    </section>
  );
}

function PlanScreen({ plan, daysOff }: { plan: CoursePlan; daysOff: DayOff[] }) {
  const studyDays = studyDaysSentence(plan);
  const offInWindow = plan.days_off_in_window ?? 0;

  return (
    <>
      <p className="mt-5 max-w-2xl text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
        This page is about the rate new material goes in, and only that. Your reviews are
        scheduled by how your memory of each concept decays, and a deadline does not move
        any of them: nothing here brings a review forward, and nothing here is at risk
        because a date is close.
      </p>

      {plan.status === "passed" && <PassedPanel plan={plan} />}

      <section aria-labelledby="plan-pace-heading">
        <h2 id="plan-pace-heading" className="mt-8 text-[15px] font-semibold">
          Your pace
        </h2>
        {plan.status === "active" && (
          <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400">
            {deadlineSentence(plan)} {studyDays}
          </p>
        )}
        <div className="mt-4 rounded-lg border border-zinc-200 px-5 py-5 dark:border-zinc-800">
          <dl className="flex flex-wrap gap-x-12 gap-y-6">
            <PlanStat
              value={
                plan.required_per_week === null ? "–" : formatRate(plan.required_per_week)
              }
              label="Lessons a week needed"
            />
            <PlanStat
              value={
                plan.observed_per_week === null ? "–" : formatRate(plan.observed_per_week)
              }
              label="Lessons a week, your pace"
            />
          </dl>
          <div className="mt-5 max-w-2xl border-t border-zinc-200 pt-4 text-[13px] leading-relaxed text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
            {paceSentences(plan).map((line) => (
              <p key={line} className="mt-1 first:mt-0">
                {line}
              </p>
            ))}
          </div>
        </div>
      </section>

      <section aria-labelledby="plan-deadline-heading">
        <h2 id="plan-deadline-heading" className="mt-9 text-[15px] font-semibold">
          Deadline
        </h2>
        <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400">
          {plan.deadline === null
            ? "This course has no deadline. Setting one works out the weekly rate above; it changes nothing else, and clearing it later puts everything back."
            : "Changing the date works out a new weekly rate. It moves no review and un-completes no lesson, and clearing it puts the course back to where it was."}
        </p>
        {/*
          NOT keyed on the deadline, and that is a deliberate reversal. The form does
          still reseed its inputs when the saved deadline changes, so clearing a date
          empties them; it now does that by adjusting its own state during render rather
          than by being destroyed and rebuilt. The reset is identical and the component
          survives its own mutations, which is what lets it hold the focus it has to
          restore in an ordinary ref. See the comment on that reset in DeadlineForm.
        */}
        <DeadlineForm plan={plan} />
      </section>

      <CalendarSection plan={plan} />

      <section aria-labelledby="plan-days-off-heading">
        <h2 id="plan-days-off-heading" className="mt-9 text-[15px] font-semibold">
          Days off
        </h2>
        <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400">
          Days off apply to every course, not just this one. A day marked here stops counting
          as a study day everywhere, so the weekly rate on your other courses moves too. It
          changes no review: your concepts still come back when they come back.
          {/*
            "between today and" rather than "before", and the difference is the whole
            correctness of the sentence. `days_off_in_window` counts only days inside the
            study window, which is today INCLUSIVE to the deadline EXCLUSIVE. The list
            underneath comes from an endpoint with no date filter at all, and nothing
            prunes it, so a day marked off last month sits there in plain view, falls
            before the deadline in plain English, and is not in this count. "Before" made
            the sentence contradict the list directly beneath it, permanently rather than
            transiently. The count is right; the preposition was wrong.
          */}
          {plan.status === "active" && offInWindow > 0
            ? ` ${offInWindow} of the days below ${offInWindow === 1 ? "falls" : "fall"} between today and ${deadlineName(plan)}.`
            : ""}
        </p>
        <DaysOffControl daysOff={daysOff} />
      </section>
    </>
  );
}

export default async function CoursePlanPage(props: PageProps<"/courses/[courseId]/plan">) {
  const { courseId } = await props.params;
  const id = Number(courseId);
  if (!Number.isInteger(id)) notFound();

  let plan: CoursePlan;
  let daysOff: DayOff[];
  try {
    // A course with no deadline answers 200 here with a null-deadline shape, so there is
    // no "has a plan" branch to take: only an unknown course id is a 404.
    const [planResult, daysOffResult] = await Promise.all([getCoursePlan(id), listDaysOff()]);
    plan = planResult;
    daysOff = daysOffResult.days_off;
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        <h1 className="text-3xl font-semibold tracking-tight">Plan</h1>
        <p
          role="alert"
          className="mt-8 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          {err instanceof ApiError
            ? err.message
            : "Could not reach the server. Is the backend running?"}
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      <Link
        href="/courses"
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        &larr; All courses
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">{plan.title}</h1>

      <CourseTabs courseId={plan.course_id} active="plan" />

      <PlanScreen plan={plan} daysOff={daysOff} />
    </main>
  );
}
