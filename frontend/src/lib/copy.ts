/**
 * Sentences and formatters that two components on the Today screen have to agree on.
 *
 * Small on purpose. Nothing lands here because it is generically useful; things land
 * here because saying the same fact twice, in two wordings, is a bug the learner can
 * see. The re-teach button and the practice panel sit inside the same list row and can
 * both be talking about the same concept at the same moment.
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
