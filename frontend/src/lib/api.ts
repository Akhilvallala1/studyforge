import { formatUsd } from "./format";
import type {
  AlertState,
  AnswerResult,
  CompleteResult,
  CourseConcepts,
  CourseDetail,
  CoursePlan,
  CourseSummary,
  DayOff,
  DayOffRemoval,
  DaysOff,
  GenerateResult,
  LessonDetail,
  PracticeAnswer,
  PracticeConflict,
  PracticeState,
  RemediationConflict,
  RemediationNote,
  ReviewAnswerResult,
  ReviewQueue,
  ReviewRatingResult,
  ReviewToday,
  TutorConflict,
  TutorConversation,
  TutorMode,
  TutorTurn,
  UsageSummary,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Shape of a FastAPI HTTPException(detail={...}) object body, as opposed to a plain string detail. */
interface ObjectDetail {
  error?: string;
  message?: string;
  limit_usd?: number;
  spent_usd?: number;
  [key: string]: unknown;
}

/**
 * What a spend-cap refusal stopped, in the words of the endpoint that was refused.
 *
 * The 402 body is identical whichever endpoint raised it, so the limit and the amounts
 * are the only things this file can state on its own. What the refused call would have
 * produced is not in the body, and only the caller knows it: generation loses a course,
 * a re-teach loses an explanation, and a shared formatter asserting either one is wrong
 * for every other caller. Omit it and the message stops at what is true everywhere.
 */
const COST_LIMIT_CONSEQUENCE = {
  generate: "Generation was stopped, no course was saved for this run.",
  // The cap is checked before the provider call and a re-teach is a single call, so
  // nothing was written and nothing was spent on this attempt.
  remediation: "No explanation was written, and this attempt spent nothing.",
  // True for the same two reasons, and checked against the endpoint rather than assumed:
  // the cap is tested before the model is called, and a turn that fails writes neither
  // row, the learner's own message included. So the transcript is exactly as it was.
  tutor: "No message was recorded, and this attempt spent nothing.",
} as const;

/** Returns null when the detail carries nothing useful, so the caller keeps its statusText fallback. */
function messageFromObjectDetail(detail: ObjectDetail, consequence?: string): string | null {
  if (detail.error === "cost_limit_exceeded") {
    const tail = consequence ? ` ${consequence}` : "";
    if (typeof detail.limit_usd === "number" && typeof detail.spent_usd === "number") {
      return `LLM spend limit reached: ${formatUsd(detail.spent_usd)} spent of a ${formatUsd(detail.limit_usd)} cap.${tail}`;
    }
    return `LLM spend limit reached.${tail}`;
  }
  if (typeof detail.message === "string" && detail.message) {
    return detail.message;
  }
  return null;
}

/** FastAPI sends 422 validation errors as an array of {loc, msg, type}; surface the first msg. */
function messageFromValidationDetail(detail: unknown[]): string | null {
  const first = detail[0];
  if (first && typeof first === "object" && typeof (first as { msg?: unknown }).msg === "string") {
    return (first as { msg: string }).msg;
  }
  return null;
}

async function request<T>(
  path: string,
  init?: RequestInit,
  costLimitConsequence?: string,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    let message = res.statusText || `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      const detail = body?.detail;
      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = messageFromValidationDetail(detail) ?? message;
      } else if (detail && typeof detail === "object") {
        message = messageFromObjectDetail(detail as ObjectDetail, costLimitConsequence) ?? message;
      }
    } catch {
      // Non-JSON error body - keep the statusText fallback.
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

function get<T>(path: string): Promise<T> {
  return request<T>(path, { cache: "no-store" });
}

function postJson<T>(path: string, body: unknown, costLimitConsequence?: string): Promise<T> {
  return request<T>(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    costLimitConsequence,
  );
}

function putJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function listCourses(): Promise<CourseSummary[]> {
  return get("/courses");
}

export function getCourse(id: number): Promise<CourseDetail> {
  return get(`/courses/${id}`);
}

export function getLesson(id: number): Promise<LessonDetail> {
  return get(`/lessons/${id}`);
}

/** The concept map's data: every concept in the course, its lesson, and its mastery. */
export function getCourseConcepts(id: number): Promise<CourseConcepts> {
  return get(`/courses/${id}/concepts`);
}

export function generateFromText(text: string): Promise<GenerateResult> {
  return postJson("/courses/generate", { text }, COST_LIMIT_CONSEQUENCE.generate);
}

export function generateFromUrl(url: string): Promise<GenerateResult> {
  return postJson("/courses/generate", { url }, COST_LIMIT_CONSEQUENCE.generate);
}

export function generateFromPdf(file: File): Promise<GenerateResult> {
  const form = new FormData();
  form.append("file", file);
  return request(
    "/courses/generate/pdf",
    { method: "POST", body: form },
    COST_LIMIT_CONSEQUENCE.generate,
  );
}

/** `elapsedMs` is a soft timing signal; omit it when the measurement is unavailable. */
export function answerQuiz(
  itemId: number,
  answer: string,
  elapsedMs?: number,
): Promise<AnswerResult> {
  const body = elapsedMs === undefined ? { answer } : { answer, elapsed_ms: elapsedMs };
  return postJson(`/quiz/${itemId}/answer`, body);
}

export function completeLesson(id: number): Promise<CompleteResult> {
  return request(`/lessons/${id}/complete`, { method: "POST" });
}

export function uncompleteLesson(id: number): Promise<CompleteResult> {
  return request(`/lessons/${id}/complete`, { method: "DELETE" });
}

export function getReviewToday(): Promise<ReviewToday> {
  return get("/review/today");
}

export function getReviewQueue(limit?: number): Promise<ReviewQueue> {
  const query = limit ? `?limit=${limit}` : "";
  return get(`/review/queue${query}`);
}

/**
 * Record an answer given during a review session. Nothing is scheduled by this:
 * the learner compares their answer with the reference one and then rates, which
 * is what `rateReviewCard` applies. A 409 means this item was already answered in
 * this exposure, which is enforced server-side at one try per item.
 */
export function answerReviewCard(
  cardId: number,
  itemId: number,
  answer: string,
  elapsedMs?: number,
): Promise<ReviewAnswerResult> {
  const body =
    elapsedMs === undefined
      ? { item_id: itemId, answer }
      : { item_id: itemId, answer, elapsed_ms: elapsedMs };
  return postJson(`/review/cards/${cardId}/answer`, body);
}

/**
 * Apply the learner's rating and reschedule the card. `suggestedRating` is passed
 * back so the backend can record whether the learner overrode the derivation.
 */
export function rateReviewCard(
  cardId: number,
  rating: number,
  suggestedRating?: number | null,
  attemptIds?: number[],
): Promise<ReviewRatingResult> {
  return postJson(`/review/cards/${cardId}/rate`, {
    rating,
    suggested_rating: suggestedRating ?? null,
    attempt_ids: attemptIds ?? [],
  });
}

/**
 * What asking for a re-teach came back with.
 *
 * A 409 is not an error here, which is why the conflict is returned rather than
 * thrown. Its four codes do not all mean the same thing, though, and the differences
 * are the whole difficulty:
 *
 * - note_active and cooldown_active carry an explanation to show.
 * - generation_in_progress carries nothing, because another request is still writing
 *   one. Wait for it.
 * - not_flagged carries nothing either, because the concept stopped being one the
 *   learner keeps missing. Say so, kindly.
 *
 * The last two are indistinguishable by payload and opposite in meaning, so a caller
 * must branch on `error` and never on whether `note` arrived. RemediationConflict is
 * a discriminated union to make that the compiler's job.
 *
 * Genuine failures still throw ApiError: 404 unknown card, 402 spend cap reached,
 * 422 no lesson material left to explain from, 502 the model failed.
 */
export type RemediationOutcome =
  | { kind: "note"; note: RemediationNote }
  | { kind: "conflict"; conflict: RemediationConflict };

/** The message logic `request` applies, over a body that has already been read. */
function messageFromErrorBody(
  body: unknown,
  fallback: string,
  costLimitConsequence?: string,
): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return messageFromValidationDetail(detail) ?? fallback;
  if (detail && typeof detail === "object") {
    return messageFromObjectDetail(detail as ObjectDetail, costLimitConsequence) ?? fallback;
  }
  return fallback;
}

/**
 * Re-teach a concept the learner keeps missing. One metered model call, at most one
 * per concept per week; the server refuses with a 409 rather than spending again.
 *
 * Does not go through `request`, which reads the body only to build an error message
 * and would throw the 409 note away.
 */
export async function requestRemediation(cardId: number): Promise<RemediationOutcome> {
  const res = await fetch(`${BASE_URL}/review/cards/${cardId}/remediation`, { method: "POST" });
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // Non-JSON body, so the status has to carry the meaning on its own.
  }
  if (res.ok) return { kind: "note", note: body as RemediationNote };
  if (res.status === 409) {
    const detail = (body as { detail?: RemediationConflict } | null)?.detail;
    if (detail && typeof detail.error === "string") return { kind: "conflict", conflict: detail };
  }
  const fallback = res.statusText || `Request failed with status ${res.status}`;
  throw new ApiError(
    res.status,
    messageFromErrorBody(body, fallback, COST_LIMIT_CONSEQUENCE.remediation),
  );
}

/** The concept's current explanation, or null when it has none. Costs nothing. */
export function getRemediation(cardId: number): Promise<RemediationNote | null> {
  return get(`/review/cards/${cardId}/remediation`);
}

function practicePath(cardId: number): string {
  return `/review/cards/${cardId}/remediation/practice`;
}

/**
 * Today's practice run for a concept. It describes; it never refuses.
 *
 * Any real card answers 200, including "this concept has no explanation open" and
 * "this concept has no quiz questions": those are facts about the run, carried as
 * status and reason, not errors. Only an unknown card is a 404.
 */
export function getPractice(cardId: number): Promise<PracticeState> {
  return get(practicePath(cardId));
}

/**
 * What submitting one practice answer came back with.
 *
 * A 409 is not an error here, which is why the conflict is returned rather than
 * thrown: each of its four codes carries the run the answer could not join, and
 * redrawing that run is the only useful thing a UI can do about it.
 */
export type PracticeOutcome =
  | { kind: "answer"; answer: PracticeAnswer }
  | { kind: "conflict"; conflict: PracticeConflict };

/**
 * Record one practice answer and get back the run that follows it.
 *
 * Does not go through `request`, for the same reason requestRemediation does not:
 * `request` reads the body only to build an error message and would throw the 409's
 * `state` away, which is the whole payload the panel needs to redraw itself.
 *
 * A run can also end on a 200 rather than a 409, which is the case worth being careful
 * about. A note retired underneath an open panel terminates the run without discarding
 * the answer the learner was already holding: that answer is still graded and kept, and
 * the terminal state arrives on the response carrying it. Callers must therefore read
 * `state.status` on success too, and never read 200 as "the run continues".
 *
 * Genuine failures still throw ApiError: 404 for an unknown card or item, 400 for an
 * empty answer or an item that tests another concept.
 */
export async function submitPractice(
  cardId: number,
  itemId: number,
  answer: string,
  elapsedMs?: number,
): Promise<PracticeOutcome> {
  const res = await fetch(`${BASE_URL}${practicePath(cardId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      item_id: itemId,
      answer,
      elapsed_ms: elapsedMs === undefined ? null : elapsedMs,
    }),
  });
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // Non-JSON body, so the status has to carry the meaning on its own.
  }
  if (res.ok) return { kind: "answer", answer: body as PracticeAnswer };
  if (res.status === 409) {
    const detail = (body as { detail?: PracticeConflict } | null)?.detail;
    if (detail && typeof detail.error === "string") return { kind: "conflict", conflict: detail };
  }
  const fallback = res.statusText || `Request failed with status ${res.status}`;
  // No spend-cap consequence: practice calls no model, so a 402 cannot reach here.
  throw new ApiError(res.status, messageFromErrorBody(body, fallback));
}

/**
 * One concept's whole conversation with the tutor, oldest first. Costs nothing.
 *
 * `concept_key` travels in the query string rather than in a path segment, which is the
 * server's choice and a load-bearing one: keys keep their slashes and spaces, so
 * "big-o / complexity" is an ordinary key, and a path segment holding a "/" would not
 * route at all. Encoded once, here, so no caller has to remember to.
 *
 * Any key answers 200, an empty conversation included: a concept nobody has asked about
 * is a fact rather than an error, and there is no 404 on this endpoint.
 */
export function getTutorConversation(conceptKey: string): Promise<TutorConversation> {
  return get(`/tutor/conversation?concept_key=${encodeURIComponent(conceptKey)}`);
}

/**
 * What asking the tutor one question came back with.
 *
 * A 409 is not an error here, which is why the conflict is returned rather than thrown.
 * Both of its codes are the learner having run out of turns, and they differ in the one
 * thing the learner will act on: concept_turn_limit means go and ask about something
 * else, daily_turn_limit means stop for today. Nothing in `limits` reliably separates
 * them, so a caller must branch on `error`.
 *
 * Genuine failures still throw ApiError: 422 for an empty or over-long message and for a
 * concept with no material left to answer from, 402 for the spend cap, 502 for a model
 * that failed or replied off-schema.
 */
export type TutorOutcome =
  | { kind: "turn"; turn: TutorTurn }
  | { kind: "conflict"; conflict: TutorConflict };

/**
 * Ask the tutor one question about one concept. One metered model call, two rows.
 *
 * Does not go through `request`, for the same reason requestRemediation does not:
 * `request` reads the body only to build an error message and would throw the payload
 * away. Here that payload is the fresh `limits`, which is the entire subject of the
 * refusal and the only thing that tells the panel what it may still offer.
 *
 * NOTHING IS WRITTEN when this fails, on every failing path: the endpoint builds both
 * rows only after the reply has parsed and commits them together. So a caller may keep
 * the learner's typed text and let them send it again, and the transcript it is holding
 * is still correct.
 *
 * `mode` is required rather than defaulted. The server defaults a missing mode to
 * "answer" and that default is its promise to clients written before guided mode
 * existed; inside this client the two registers are a deliberate choice per question, so
 * a call site that has not said which one it wants is a bug worth a compile error. A
 * value the server does not answer in is a 422 `invalid_mode`, which throws like any
 * other 422, and the union makes that unreachable from here.
 *
 * Asking for "guided" is a REQUEST, not a guarantee. With the concept's guided run
 * already spent the server answers 200 in answer mode instead, and `turn.mode` is how a
 * caller learns which it got.
 */
export async function sendTutorMessage(
  conceptKey: string,
  message: string,
  mode: TutorMode,
): Promise<TutorOutcome> {
  const res = await fetch(`${BASE_URL}/tutor/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ concept_key: conceptKey, message, mode }),
  });
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // Non-JSON body, so the status has to carry the meaning on its own.
  }
  if (res.ok) return { kind: "turn", turn: body as TutorTurn };
  if (res.status === 409) {
    const detail = (body as { detail?: TutorConflict } | null)?.detail;
    if (detail && typeof detail.error === "string") return { kind: "conflict", conflict: detail };
  }
  const fallback = res.statusText || `Request failed with status ${res.status}`;
  throw new ApiError(res.status, messageFromErrorBody(body, fallback, COST_LIMIT_CONSEQUENCE.tutor));
}

/**
 * The course's pace figures. Costs nothing and never refuses.
 *
 * A COURSE WITH NO DEADLINE ANSWERS 200 with a null-deadline shape, not 404: the
 * observed pace is real and worth showing either way, and "no deadline" is a state of
 * this resource rather than the absence of it. Only an unknown course id is a 404.
 *
 * None of the planning endpoints has a 409 carrying a payload, so none of them needs
 * the bespoke fetch that requestRemediation, submitPractice and sendTutorMessage use.
 * They all go through plain get/postJson/putJson, deliberately.
 */
export function getCoursePlan(id: number): Promise<CoursePlan> {
  return get(`/courses/${id}/plan`);
}

/**
 * Set or move the deadline, and get the recomputed plan back.
 *
 * THE BODY FIELD IS `deadline`, not `day`, which is the one place this feature's two
 * date-carrying endpoints disagree: a day off posts `{day}`. Sending the wrong one is a
 * generic pydantic 422 rather than this feature's own sentence, so it is worth the note.
 *
 * Today is accepted and the past is not. A past date throws ApiError carrying the
 * server's own message; so does a malformed date or an over-long label.
 */
export function setCourseDeadline(
  id: number,
  deadline: string,
  label: string,
): Promise<CoursePlan> {
  return putJson(`/courses/${id}/deadline`, { deadline, label });
}

/**
 * Remove the deadline. Idempotent, and it touches nothing else: no review card moves
 * and no lesson is un-completed. The course goes back to behaving exactly as one that
 * never had a deadline.
 */
export function clearCourseDeadline(id: number): Promise<CoursePlan> {
  return request(`/courses/${id}/deadline`, { method: "DELETE" });
}

/**
 * Where the deadline's calendar file lives, as a URL for an ordinary link.
 *
 * A DOWNLOAD, NOT A SUBSCRIPTION. The response is text/calendar with a
 * Content-Disposition attachment header, so following the link saves a file; there is
 * no webcal address to offer, because a calendar provider cannot reach a server running
 * on the learner's own machine. 404 when the course has no deadline, which is why the
 * link is only rendered once one is set.
 */
export function coursePlanIcsUrl(id: number): string {
  return `${BASE_URL}/courses/${id}/plan.ics`;
}

/**
 * What the downloaded calendar file will be called, so the screen can say so.
 *
 * MIRRORS ics.download_filename, which owns this shape. Restating it rather than reading
 * it back off the response is safe for the same reason the server hardcodes it: the only
 * variable in the name is an integer primary key. The course title is deliberately not in
 * it, because a title is LLM output and a title in a Content-Disposition header is header
 * injection rather than a badly named file. That is what makes the shape stable enough to
 * mirror; if the server ever changes it, this changes with it.
 */
export function coursePlanIcsFilename(id: number): string {
  return `studyforge-course-${id}.ics`;
}

/** Every day the learner has marked off, oldest first. Global, not per course. */
export function listDaysOff(): Promise<DaysOff> {
  return get("/plan/days-off");
}

/**
 * Mark a day off. IDEMPOTENT: marking an already-marked day returns the existing row
 * unchanged rather than a 409, and does not overwrite its note. Changing a note means
 * unmarking the day and marking it again.
 */
export function addDayOff(day: string, note: string): Promise<DayOff> {
  return postJson("/plan/days-off", { day, note });
}

/**
 * Unmark a day. Succeeds whether or not it was marked; `removed` says which happened.
 *
 * The date travels in the PATH here, unlike the tutor's concept_key, which has to use
 * the query string because a normalized key can contain a slash. A YYYY-MM-DD cannot,
 * so the plainer URL is safe.
 */
export function removeDayOff(day: string): Promise<DayOffRemoval> {
  return request(`/plan/days-off/${encodeURIComponent(day)}`, { method: "DELETE" });
}

export function getUsage(limit?: number): Promise<UsageSummary> {
  const query = limit ? `?limit=${limit}` : "";
  return get(`/usage${query}`);
}

export function acknowledgeCostAlert(): Promise<AlertState> {
  return request("/usage/alert/ack", { method: "POST" });
}
