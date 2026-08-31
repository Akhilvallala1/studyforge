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
 * What nothing inside the re-teach panel does, practice included. Said ONCE.
 *
 * The one thing a learner might reasonably assume, from asking for an explanation or
 * from getting practice questions right, is that they have moved the needle. They have
 * not: re-teaching writes a note and practice writes an attempt row, and neither
 * touches the schedule, the mastery buckets, the attention flag, or the retention
 * figure. That promise is the panel's, not any one control's, which is why it is one
 * sentence at the bottom of the panel rather than one per control: practice used to
 * carry its own wording of it, two lines above this one, and every learner who opened
 * practice read the same fact twice.
 */
export const SCHEDULE_PROMISE =
  "This concept stays in your review queue on its usual schedule. Nothing here, " +
  "practice included, reschedules it or marks it learned.";
