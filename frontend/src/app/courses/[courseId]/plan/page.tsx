import Link from "next/link";
import { notFound } from "next/navigation";

import { CourseTabs } from "@/components/CourseTabs";
import { DaysOffControl } from "@/components/DaysOffControl";
import { DeadlineForm } from "@/components/DeadlineForm";
import { ErrorState } from "@/components/ui/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  ApiError,
  coursePlanIcsFilename,
  coursePlanIcsUrl,
  getCoursePlan,
  listDaysOff,
} from "@/lib/api";
import { formatDayKey } from "@/lib/copy";
import { serverToday, splitDaysOff } from "@/lib/plan";
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
 *
 * EVERY NULLABLE FIELD OF THE PAYLOAD IS TESTED WITH `== null`, NOT `=== null`, and that
 * is deliberate rather than sloppy. TypeScript describes the payload; it does not enforce
 * it, because the server is free to stop sending a field and the declaration here will go
 * on claiming it exists. That is not hypothetical: this payload has already renamed its
 * pace fields once, and under `=== null` an absent field silently took the branch that
 * assumes a number, since `undefined === null` is false. A strict test turns "the server
 * stopped sending this" into a wrong number on a deadline screen; a nullish test turns it
 * into the dash, which is what the learner should see when nothing is known. Loud beats
 * silent here, and the dash is the honest answer either way.
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

/**
 * The window both observed rates are measured over, in days.
 *
 * A constant rather than three literals because three sentences describe this window, and
 * a copy edit that changes one number and not the others is the drift it exists to stop.
 *
 * MIRRORS PACE_WINDOW_DAYS in backend/app/planning.py, hand-written like ProjectionReason
 * and with the same limit: nothing compares the two, so this keeps the sentences honest
 * with EACH OTHER and cannot keep them honest with the server. If that constant moves,
 * this one has to be changed to match.
 */
const PACE_WINDOW_DAYS = 30;

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
 *
 * THE OMISSION ABOVE IS LOAD-BEARING AND MUST NOT BE "SIMPLIFIED" BACK. The share sentence
 * interpolates this result and capitalizes the whole string; it does not prepend "About"
 * of its own. So the floor branch already reads correctly there, "Less than 0.1 of that is
 * in this course", and it is THIS function dropping the hedge that makes it so. Restoring
 * an unconditional "about" here to tidy the branch away is what would produce "About less
 * than 0.1", which is why the rule lives in one place rather than at the call site.
 *
 * The floor branch is also unreachable from that sentence, and the argument is structural
 * rather than a list of cases. The share sentence runs only where `projection_reason` is
 * null, and the server produces a null reason only after its zero-share branch has already
 * returned, so a rate arriving here from that path is truthy by construction. Above zero
 * the floor cannot be hit either: the rate is completions over a fixed window, so its
 * smallest non-zero value is one completion at about 0.23 a week, well clear of RATE_FLOOR.
 *
 * Deliberately NOT phrased as "zero routes to `no_progress_in_this_course`". That was the
 * earlier wording and it went stale the moment `already_finished` was added, which also
 * carries a zero share: an enumeration of the server's reason codes has to be revisited
 * every time one is added, and this file has already been caught out by that once. The
 * structural form covers every code, including ones not yet written.
 *
 * Both halves rest on the SERVER's branch ordering rather than on anything this file
 * enforces, which is why they are the backup and not the primary reason. The prose reading
 * correctly at the floor is the property that holds no matter what the server sends.
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
  if (plan.deadline == null || plan.days_until == null) return "";
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
  if (plan.status !== "active" || plan.available_days == null) return null;
  const head = `That leaves ${dayCount(plan.available_days)} to study on before it`;
  const off = plan.days_off_in_window ?? 0;
  if (off > 0) {
    return `${head}, once the ${dayCount(off)} you have marked off are taken out. The deadline day itself is not counted, since that is the day you need to already know it.`;
  }
  return `${head}. The deadline day itself is not counted, since that is the day you need to already know it.`;
}

/**
 * How many of the learner's upcoming days off the weekly rate actually counts.
 *
 * THE COUNT AND THE VISIBLE LIST ARE DIFFERENT SETS, and this sentence exists to keep
 * that from being a contradiction. `days_off_in_window` counts [today, deadline). The
 * list defaults to today onward, which is a SUPERSET: a day marked after the deadline is
 * upcoming and uncounted. So the sentence never says "the days below" are the counted
 * ones. It names the subset out of the total, and when the two sets happen to coincide it
 * says so rather than printing "3 of 3".
 *
 * "your upcoming days off" rather than "the days below", deliberately: opening the
 * earlier-days disclosure puts more days below without changing which ones are counted,
 * and a sentence that said "below" would quietly go false the moment it was opened.
 *
 * Empty when nothing is counted. A learner whose only days off are after the deadline has
 * a denominator this feature never touched, and the paragraph above already says what a
 * day off does.
 */
function daysOffCountSentence(plan: CoursePlan, upcomingCount: number): string {
  const counted = plan.days_off_in_window ?? 0;
  if (plan.status !== "active" || counted === 0) return "";
  const name = deadlineName(plan);
  if (counted === upcomingCount) {
    return upcomingCount === 1
      ? ` Your one upcoming day off falls between today and ${name}.`
      : ` All ${upcomingCount} of your upcoming days off fall between today and ${name}.`;
  }
  return ` ${counted} of your ${upcomingCount} upcoming days off ${counted === 1 ? "falls" : "fall"} between today and ${name}.`;
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
      <dt className="mt-0.5 text-xs text-ink-muted">{label}</dt>
      <dd className="font-mono text-[26px] font-medium tabular-nums">{value}</dd>
    </div>
  );
}

/**
 * The SECOND half of the pace pair: which slice of that throughput is this course, and
 * therefore where the finish date came from.
 *
 * This sentence exists because the two numbers do not divide. A learner who reads "3 a
 * week" and then sees a date that is not the remaining lessons over 3 would be looking at
 * an error; naming the share answers that in the same breath instead of apologising for
 * it afterwards. The split is also the actionable part: with a tight deadline and three
 * courses open, "about 0.9 of that is in this course" says what to change.
 *
 * EXHAUSTIVE ON `projection_reason`, now enforced by a `never` check rather than claimed
 * in a comment. The fallback still says nothing about why: an unrecognised code must not
 * render as a blank panel, and must not invent a cause either, the same discipline
 * weakestExplanation follows on the concepts page.
 *
 * `already_finished` CANNOT REACH THIS FUNCTION TODAY, and the reason is worth knowing
 * before anyone moves the call. The server returns it exactly when lessons_remaining is
 * zero, and the only call site guards on `plan.lessons_remaining > 0`. That guard is
 * therefore LOAD-BEARING rather than incidental: it is what keeps a finished course out
 * of here, and a second consumer added without it would reach this branch immediately.
 *
 * WHICH IS WHY THAT BRANCH ANSWERS RATHER THAN ASSERTS. Throwing would have been the
 * tidier way to encode "unreachable", and it would be wrong here: this is a server
 * component's render path, so a throw takes down the whole plan screen, deadline form and
 * calendar file and days-off list included, for a course whose only sin is being finished.
 * The caller that reaches it is a future one that forgot a guard, and the useful response
 * to that is a true sentence on their screen rather than a broken page. The neighbouring
 * default branch already answers rather than throwing, on strictly stranger input.
 */
function projectionSentence(plan: CoursePlan): string {
  const noDate = "There is no finish date to project for this course just now.";
  switch (plan.projection_reason) {
    case "no_pace_yet":
      return "There is no finish date to project until you have finished a few more lessons.";
    case "no_progress_in_this_course":
      /*
       * SCOPED TO THE WINDOW, NOT TO THE LEARNER'S HISTORY, because this branch is reached
       * two ways and the payload cannot say which. One is someone who has never opened this
       * course. The other is someone whose lessons here were all finished before the window
       * began: the in-window count is zero, the share is zero, and the server routes here
       * exactly as designed. For that second learner "yet" was simply false. They have
       * worked in this course, just not lately, and a screen telling them otherwise is
       * wrong about the one thing they would know better than it does.
       */
      return `None of that has been in this course in the last ${PACE_WINDOW_DAYS} days, so there is no finish date to project.`;
    case "already_finished":
      // Unreachable today, and answered rather than asserted. See the header above.
      return "You have finished this course, so there is no finish date left to project.";
    case null:
    case undefined:
      break;
    default: {
      /*
       * Two jobs, which is why this is not simply a return.
       *
       * The assignment is the COMPILE-TIME half: once every member of ProjectionReason is
       * handled above, this narrows to `never` and the assignment is legal. Add a member
       * to the union without a case for it and this line stops compiling and points here,
       * which is the check that was missing when `already_finished` was added.
       *
       * The return is the RUNTIME half, and it is still needed, because the union is a
       * hand-written copy of the server's constants: the server can send a code this file
       * has never heard of, which no amount of type-checking sees. That case gets a
       * sentence claiming nothing about why, rather than a blank panel or a guess.
       */
      const unhandled: never = plan.projection_reason;
      void unhandled;
      return noDate;
    }
  }
  if (plan.finish_projection == null || plan.observed_per_week_this_course == null) {
    return noDate;
  }
  /*
   * "of that", not "of those", IN EVERY SENTENCE HERE, the no-progress branch above
   * included. "Those" refers to a set of lessons and forces a plural, which made the verb
   * wrong above one: "about 1.4 of those is". "That" refers to the rate as a single
   * quantity, so the singular is correct at every value and the sentence has no input at
   * which it reads wrong. Fixed by the noun rather than by switching the verb on the
   * number, because there is then no threshold to get wrong and no second string to keep
   * in step with the first. The branches are mutually exclusive, so no learner ever sees
   * two of them, but a reader of this function sees all of them at once and should not
   * have to work out whether two pronouns for one antecedent were deliberate.
   *
   * THE EQUALITY BRANCH IS GATED ON THE UNDERLYING FLOATS, NOT THE ROUNDED DISPLAY. Two
   * rates that both render as "1.4" can differ underneath, and "all of that" would then
   * be the only thing on the page claiming they are the same while the projected date
   * quietly disagreed. Exact equality makes the claim exactly true; anything else falls
   * through to the share, even when the two printed numbers happen to match. It also
   * fires correctly for a learner with several courses whose completions are all in this
   * one, which is the same fact stated about a different situation.
   *
   * DO NOT REPLACE THIS WITH A COMPARISON OF THE DISPLAYED STRINGS, however tempting the
   * arithmetic makes it look. Both OBSERVED rates are count/30*7, so the smallest gap
   * between two of them is 7/30, about 0.233, far wider than the 0.05 bucket that
   * one-decimal rounding collapses: enumerating every reachable rate gives distinct
   * displayed values with no collisions, so a display comparison would agree with this one
   * on every input the system can produce today.
   *
   * THAT PROOF COVERS THE TWO OBSERVED RATES AND NOTHING ELSE, which is the part that gets
   * over-read. required_per_week is lessons_remaining/available_days*7 and is NOT on that
   * lattice, so it can display equal to an observed rate while differing underneath. The
   * plan tiles now sit those two side by side, which is new, so the temptation to reach
   * for the collision proof and apply it to that pair is new as well. Nothing compares
   * them for equality and nothing should. This gate is right because it is right by
   * construction, not because of a coincidence that holds for one of the three rates.
   */
  const share =
    plan.observed_per_week_this_course === plan.observed_per_week_all_courses
      ? "All of that is in this course, and that is the pace your finish date uses."
      : `${ratePhrase(plan.observed_per_week_this_course)} of that is in this course, and that is the pace your finish date uses.`;
  const finish = `At that pace you finish on ${formatDayKey(plan.finish_projection)}`;
  return plan.deadline != null && plan.status === "active"
    ? `${capitalize(share)} ${finish}; ${deadlineName(plan)} is on ${formatDayKey(plan.deadline)}.`
    : `${capitalize(share)} ${finish}.`;
}

/** Sentence-initial form, for a phrase that starts with a lower-case rate word. */
function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
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
  } else if (plan.required_per_week != null) {
    lines.push(
      `You need ${ratePhrase(plan.required_per_week)} lessons a week to get through the remaining ${lessonCount(plan.lessons_remaining)} before ${deadlineName(plan)}.`,
    );
  } else {
    lines.push(requiredDashNote(plan));
  }

  const sample = plan.observed_sample_all_courses;
  if (plan.observed_per_week_all_courses != null) {
    // "all" is load-bearing and must survive any trimming of this sentence. Without it
    // this is the old claim, which counted only this course, and it is now false.
    lines.push(
      `Across all your courses, you have been finishing ${ratePhrase(plan.observed_per_week_all_courses)} lessons a week.`,
    );
  } else if (sample === 0) {
    lines.push(
      `You have not finished a lesson in any course in the last ${PACE_WINDOW_DAYS} days, so there is no pace to measure yet.`,
    );
  } else if (typeof sample === "number") {
    lines.push(
      `You have finished ${lessonCount(sample)} across all your courses in the last ${PACE_WINDOW_DAYS} days, which is not enough to call a pace yet: a rate off a handful of lessons would swing every time one more landed.`,
    );
  } else {
    // Claims no count, because a payload that stopped sending one is a payload whose
    // count we do not know. Saying "you have finished 0" there would be inventing it.
    lines.push("There is not enough finished work across your courses to call a pace yet.");
  }

  if (plan.lessons_remaining > 0) {
    lines.push(projectionSentence(plan));
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
    <section className="mt-5 rounded-surface border border-line px-5 py-4">
      <p className="text-[15px] font-medium">
        {deadlineSentence(plan)} Your reviews continue, because you still know this.
      </p>
      <p className="mt-1.5 text-small text-ink-muted">
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
      <h2 id="plan-calendar-heading" className="mt-9 text-subtitle">
        Put it in your calendar
      </h2>
      <p className="mt-1.5 max-w-2xl text-small text-ink-muted">
        StudyForge cannot notify you. There are no accounts here and no server running when
        you are not using it, so nothing in this program can send you an email, a push
        notification, or a reminder of any kind, and that is by design. What it can do is
        hand you a calendar file, and let the calendar you already use do the reminding.
      </p>
      {plan.deadline == null ? (
        <p className="mt-3 rounded-surface border border-line px-5 py-4 text-small text-ink-muted">
          Set a deadline above and the calendar file appears here.
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-4 rounded-surface border border-line px-5 py-4">
          <p className="max-w-lg text-small text-ink-muted">
            One all-day event on {formatDayKey(plan.deadline)}, with where you stand written
            into it. It saves as {coursePlanIcsFilename(plan.course_id)}. This is a file you
            download and open once, not an address your calendar keeps checking: a calendar
            provider on the internet cannot reach a server running on your own machine.
            Download it again after changing the date and it updates the same entry rather
            than adding a second one.
          </p>
          <a
            href={coursePlanIcsUrl(plan.course_id)}
            className="shrink-0 whitespace-nowrap rounded-control border border-line-strong px-4 py-2 text-small font-medium transition-colors duration-fast ease-standard hover:border-line-hover"
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
  // The same split the list renders, so the sentence and the list can never be counting
  // different things. One definition, two callers.
  const today = serverToday(plan);
  const upcomingDaysOff = splitDaysOff(daysOff, today).upcoming.length;

  return (
    <>
      <p className="mt-5 max-w-2xl text-ui text-ink-muted">
        This page is about the rate new material goes in, and only that. Your reviews are
        scheduled by how your memory of each concept decays, and a deadline does not move
        any of them: nothing here brings a review forward, and nothing here is at risk
        because a date is close.
      </p>

      {plan.status === "passed" && <PassedPanel plan={plan} />}

      <section aria-labelledby="plan-pace-heading">
        <h2 id="plan-pace-heading" className="mt-8 text-subtitle">
          Your pace
        </h2>
        {plan.status === "active" && (
          <p className="mt-1.5 max-w-2xl text-small text-ink-muted">
            {deadlineSentence(plan)} {studyDays}
          </p>
        )}
        <div className="mt-4 rounded-surface border border-line px-5 py-5">
          <dl className="flex flex-wrap gap-x-12 gap-y-6">
            <PlanStat
              value={
                plan.required_per_week == null ? "–" : formatRate(plan.required_per_week)
              }
              label="Lessons a week needed"
            />
            {/*
              THE SECOND TILE IS THIS COURSE'S SHARE, NOT THE ALL-COURSES RATE, and the
              reason overturns what this comment used to say. Labelling the all-courses
              rate accurately was not enough: two numbers in the largest type on the page,
              side by side, in the same units, ARE a comparison whatever the labels say. A
              learner seeing "needed 2.3" beside "all courses 2.8" reads "comfortably
              ahead" at a glance, while the share is 0.9 and the projected finish is a
              month past the deadline. The number that compares to 2.3 is 0.9, and it was
              nowhere in the tiles, only in the third and smallest sentence below.

              That glance was a verdict, and an optimistic one, on a page whose whole
              discipline is not to draw verdicts because only the learner knows what their
              next fortnight looks like. An accidental verdict is still a verdict. At 390px
              the tiles stack one directly above the other, which tightens the false
              comparison rather than loosening it.

              TWO TILES, NOT THREE. A third tile carrying the all-courses rate would put
              the mis-comparison straight back in the row: the eye pairs the largest
              adjacent numbers sharing a unit, and a disambiguating third number does not
              stop that, it gives it more to work with. The all-courses rate is context
              rather than a target, so it belongs in the prose, where the share sentence
              contextualises it in the same breath.

              ZERO IS SHOWN AS ZERO, NOT AS A DASH. A learner with a rate elsewhere and
              none here has a share that is genuinely measured and genuinely zero, while
              the dash means "not enough data to say", which would be a different and false
              claim. The dash appears only where the server nulls the rate, and it nulls
              both OBSERVED RATES together, so those two can never disagree about whether a
              pace exists at all. That is also what made this swap safe: since the two
              observed rates go null in lockstep, changing which one this tile renders
              cannot change when a dash appears.

              THE TWO TILES CAN STILL DISAGREE, and that is fine. Tile one is
              required_per_week, which is not an observed rate and goes null for unrelated
              reasons: no deadline, a deadline today, every remaining day marked off. So
              "2.3 | dash" is reachable, for a learner with a deadline and under five
              completions anywhere, and so is "dash | 0.9", for one with a pace and no
              deadline. Both are coherent and the prose explains each; neither is a bug.

              A FINISHED COURSE SHOWS 0 AGAINST 0 AND IS NOT SPECIAL-CASED, because
              special-casing it would contradict the rule just above. Both zeroes are
              measurements, not absences: nothing is needed because nothing remains, and
              nothing was finished here inside the window. Replacing two true measurements
              with a glyph that means "not enough data to say" is exactly the false claim
              the zero-versus-dash rule exists to prevent, so the rule decides this case
              rather than a judgement about how the pair looks. A course finished INSIDE
              the window reads "0 | 2.3" for the same reason, and is equally fine.
            */}
            <PlanStat
              value={
                plan.observed_per_week_this_course == null
                  ? "–"
                  : formatRate(plan.observed_per_week_this_course)
              }
              label="Lessons a week, this course"
            />
          </dl>
          <div className="mt-5 max-w-2xl border-t border-line pt-4 text-small text-ink-muted">
            {paceSentences(plan).map((line) => (
              <p key={line} className="mt-1 first:mt-0">
                {line}
              </p>
            ))}
          </div>
        </div>
      </section>

      <section aria-labelledby="plan-deadline-heading">
        <h2 id="plan-deadline-heading" className="mt-9 text-subtitle">
          Deadline
        </h2>
        <p className="mt-1.5 max-w-2xl text-small text-ink-muted">
          {plan.deadline == null
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
        <h2 id="plan-days-off-heading" className="mt-9 text-subtitle">
          Days off
        </h2>
        <p className="mt-1.5 max-w-2xl text-small text-ink-muted">
          Days off apply to every course, not just this one. A day marked here stops counting
          as a study day everywhere, so the weekly rate on your other courses moves too. It
          changes no review: your concepts still come back when they come back.
          {daysOffCountSentence(plan, upcomingDaysOff)}
        </p>
        <DaysOffControl daysOff={daysOff} today={today} />
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
        <PageHeader title="Plan" />
        <ErrorState
          title=""
          className="mt-8"
          message={
            err instanceof ApiError
              ? err.message
              : "Could not reach the server. Is the backend running?"
          }
        />
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      <Link
        href="/courses"
        className="text-small text-ink-muted transition-colors duration-fast ease-standard hover:text-ink"
      >
        &larr; All courses
      </Link>
      <PageHeader className="mt-4" title={plan.title} />

      <CourseTabs courseId={plan.course_id} active="plan" />

      <PlanScreen plan={plan} daysOff={daysOff} />
    </main>
  );
}
