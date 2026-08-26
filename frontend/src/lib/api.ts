import type {
  AnswerResult,
  CompleteResult,
  CourseDetail,
  CourseSummary,
  GenerateResult,
  LessonDetail,
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    let message = res.statusText || `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Non-JSON error body — keep the statusText fallback.
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
