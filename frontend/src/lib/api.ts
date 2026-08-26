import { formatUsd } from "./format";
import type {
  AlertState,
  AnswerResult,
  CompleteResult,
  CourseDetail,
  CourseSummary,
  GenerateResult,
  LessonDetail,
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

export function answerQuiz(itemId: number, answer: string): Promise<AnswerResult> {
  return postJson(`/quiz/${itemId}/answer`, { answer });
}

export function completeLesson(id: number): Promise<CompleteResult> {
  return request(`/lessons/${id}/complete`, { method: "POST" });
}

export function getUsage(limit?: number): Promise<UsageSummary> {
  const query = limit ? `?limit=${limit}` : "";
  return get(`/usage${query}`);
}

export function acknowledgeCostAlert(): Promise<AlertState> {
  return request("/usage/alert/ack", { method: "POST" });
}
