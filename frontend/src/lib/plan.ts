/**
 * Day arithmetic the plan screen and its day-off control have to agree on.
 *
 * A PLAIN MODULE, NOT A CLIENT ONE, and that is the reason it exists rather than living
 * beside the component that uses it most. The plan page is a server component and
 * DaysOffControl is a client component, and both have to divide the same list at the same
 * date: the page to say how many days off are counted, the control to decide which ones
 * to show. Exporting the function from the "use client" module typechecks and builds
 * cleanly and then throws at render, because a server component may not call into a
 * client module. Neither side owns this, so it sits where both can reach it.
 *
 * NOTHING HERE READS A CLOCK. See serverToday.
 */

import type { CoursePlan, DayOff } from "./types";

/**
 * A day key moved by whole days, pinned to UTC so it cannot slip across a boundary.
 *
 * Day keys are bare YYYY-MM-DD. Parsed without the explicit Z they would be read in the
 * viewer's zone and could come back a day out.
 */
function shiftDayKey(key: string, days: number): string {
  const date = new Date(`${key}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return key;
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/**
 * Today, as the SERVER's study day, recovered from the plan rather than from a clock.
 *
 * THE DATE IS DERIVED, NEVER READ. planning.py sets days_until = deadline - today, where
 * today is the learner's STUDY day: it carries a 04:00 boundary and the configured
 * timezone, so between midnight and 04:00 it is yesterday's date. Neither the browser nor
 * a server render knows any of that, and a today taken from either clock would divide the
 * list differently than the server divided it. Inverting the server's own subtraction
 * recovers exactly the date it used.
 *
 * Works for a passed deadline too, where days_until is simply negative. Null only when
 * the course has no deadline at all, which is the one case that sends nothing to invert.
 */
export function serverToday(plan: CoursePlan): string | null {
  if (plan.deadline === null || plan.days_until === null) return null;
  return shiftDayKey(plan.deadline, -plan.days_until);
}

/**
 * The list split into what is still ahead of the learner and what is already behind them.
 *
 * Null `today` means the course has no deadline, so nothing can be called past without
 * guessing a date: everything is treated as upcoming and the list is shown whole. Without
 * a deadline there is no window for anything to sit outside of, and no count to reconcile.
 *
 * Day keys are YYYY-MM-DD, so lexicographic order is chronological order and the split
 * needs no date parsing.
 *
 * NOTHING IS DROPPED. Both halves are returned and both are rendered; the earlier half is
 * collapsed behind a disclosure rather than filtered away, because a learner who marked a
 * day should always be able to find it again.
 *
 * UPCOMING IS NOT THE COUNTED SET, and callers must not treat it as one. days_off_in_window
 * counts [today, deadline); this returns [today, forever). A day marked after the deadline
 * is upcoming and uncounted, which is why the sentence on the plan page names the subset
 * out of this total instead of claiming the visible list is what the rate counts.
 */
export function splitDaysOff(daysOff: DayOff[], today: string | null) {
  if (today === null) return { upcoming: daysOff, past: [] as DayOff[] };
  return {
    upcoming: daysOff.filter((entry) => entry.day >= today),
    past: daysOff.filter((entry) => entry.day < today),
  };
}
