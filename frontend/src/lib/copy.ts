/**
 * Sentences and formatters that two components on the Today screen have to agree on.
 *
 * Small on purpose. Nothing lands here because it is generically useful; things land
 * here because saying the same fact twice, in two wordings, is a bug the learner can
 * see. The re-teach button and the practice panel sit inside the same list row and can
 * both be talking about the same concept at the same moment.
 *
 * A component module would technically do, since ReteachConcept already imports
 * ConceptPractice and there would be no cycle. It is still the wrong home: a component
 * that owns the words another component must say makes the dependency about rendering
 * when it is really about copy, and the next component needing the same sentence has
 * to import a panel to get it.
 */

/**
 * A fixed locale, so a date rendered on the server survives hydration unchanged.
 * Falls back to the raw ISO string rather than showing "Invalid Date".
 */
export function formatDay(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

/**
 * A local YYYY-MM-DD study day as the learner would write it: "25 September 2026".
 *
 * NOT formatDay above, and the difference is a whole day. formatDay takes a full ISO
 * timestamp; handed a bare "2026-09-25" the Date constructor reads it as UTC midnight,
 * and toLocaleDateString then renders it in the browser's zone, which is the 24th
 * anywhere west of Greenwich. The deadline, the finish projection and every day off are
 * bare day keys, so they are pinned to UTC on the way in and on the way out and the
 * date arrives as the one that was stored.
 *
 * The locale is fixed rather than inherited so the server render and the client render
 * produce the same string and hydration does not tear.
 */
export function formatDayKey(key: string): string {
  const date = new Date(`${key}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return key;
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * That a concept has stopped being one the learner keeps missing, in one wording.
 *
 * Two places reach this fact by different routes: the re-teach button is told
 * `not_flagged` when it asks for an explanation, and the practice panel finds the note
 * retired underneath it. Both are good news and both are the same news, so they get
 * the same clause. A second phrasing would have one list row disagree with itself
 * depending on which control the learner happened to touch.
 *
 * Returned without a trailing stop, so callers can carry the sentence on.
 */
export function noLongerMissed(conceptLabel: string): string {
  return `${conceptLabel} is no longer one of the concepts you keep missing`;
}

/**
 * What nothing inside the re-teach panel does, practice and the tutor included. Said ONCE.
 *
 * The one thing a learner might reasonably assume, from asking for an explanation, from
 * getting practice questions right, or from talking a concept through with the tutor, is
 * that they have moved the needle. They have not: re-teaching writes a note, practice
 * writes an attempt row, the tutor writes two message rows, and none of them touches the
 * schedule, the mastery buckets, the attention flag, or the retention figure. That
 * promise is the panel's, not any one control's, which is why it is one sentence at the
 * bottom of the panel rather than one per control: practice used to carry its own
 * wording of it, two lines above this one, and every learner who opened practice read
 * the same fact twice.
 *
 * The tutor was added by WIDENING the clause below rather than by adding a second
 * sentence beside it, for exactly that reason. Two near-identical paragraphs one rule
 * apart is what this constant exists to prevent, and at 390px it costs seven lines to
 * say one thing twice.
 */
export const SCHEDULE_PROMISE =
  "This concept stays in your review queue on its usual schedule. Nothing here, " +
  "practice and the tutor included, reschedules it or marks it learned.";
