import { formatUsd } from "./format";
import type {
  AlertState,
  AnswerResult,
  CompleteResult,
  CourseDetail,
  CourseSummary,
  GenerateResult,
  LessonDetail,
  RemediationConflict,
  RemediationNote,
  ReviewAnswerResult,
  ReviewQueue,
  ReviewRatingResult,
  ReviewToday,
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

/** Returns null when the detail carries nothing useful, so the caller keeps its statusText fallback. */
function messageFromObjectDetail(detail: ObjectDetail): string | null {
  if (detail.error === "cost_limit_exceeded") {
    if (typeof detail.limit_usd === "number" && typeof detail.spent_usd === "number") {
      return `LLM spend limit reached: ${formatUsd(detail.spent_usd)} spent of a ${formatUsd(detail.limit_usd)} cap. Generation was stopped, no course was saved for this run.`;
    }
    return "LLM spend limit reached. Generation was stopped, no course was saved for this run.";
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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
        message = messageFromObjectDetail(detail as ObjectDetail) ?? message;
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

function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
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

export function generateFromText(text: string): Promise<GenerateResult> {
  return postJson("/courses/generate", { text });
}

export function generateFromUrl(url: string): Promise<GenerateResult> {
  return postJson("/courses/generate", { url });
}

export function generateFromPdf(file: File): Promise<GenerateResult> {
  const form = new FormData();
  form.append("file", file);
  return request("/courses/generate/pdf", { method: "POST", body: form });
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

export function getUsage(limit?: number): Promise<UsageSummary> {
  const query = limit ? `?limit=${limit}` : "";
  return get(`/usage${query}`);
}

export function acknowledgeCostAlert(): Promise<AlertState> {
  return request("/usage/alert/ack", { method: "POST" });
}
