/**
 * The lesson page caught ApiError-404 and called notFound(), correctly, but everything
 * else fell through to a bare `throw err`, which propagates out of the server component
 * into Next's own generic error boundary instead of the app's own messaging.
 *
 * The five hostile-URL cases this route has to survive: nonexistent course, nonexistent
 * lesson, wrong-course lesson, non-numeric course id, non-numeric lesson id. All five
 * must still 404. lesson-course-scope.test.tsx already pins the wrong-course and
 * non-numeric cases against the pre-existing code path; this file adds the nonexistent-
 * lesson 404 and the new non-404 friendly-message behaviour without touching those.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

import LessonPage from "@/app/courses/[courseId]/lessons/[lessonId]/page";
import { ApiError, getLesson } from "@/lib/api";
import type { LessonDetail } from "@/lib/types";

/** Stands in for Next's real signal, which throws so rendering cannot continue. */
class NotFoundSignal extends Error {}

vi.mock("next/navigation", () => ({
  notFound: vi.fn(() => {
    throw new NotFoundSignal("NEXT_NOT_FOUND");
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getLesson: vi.fn(),
}));

function lessonIn(courseId: number): LessonDetail {
  return {
    id: 1,
    course_id: courseId,
    title: "Lesson A",
    content: "# Lesson A",
    concepts: [],
    completed: false,
    completed_at: null,
    quiz: [],
    quiz_progress: { items: 0, answered: 0, correct: 0, first_try_correct: 0 },
  };
}

function renderPage(courseId: string, lessonId: string) {
  return LessonPage({ params: Promise.resolve({ courseId, lessonId }) } as never);
}

describe("lesson page load failure", () => {
  // Braces, not an expression body: see course-page-load-error.test.tsx for why an
  // expression-bodied beforeEach here causes an unrelated unhandled rejection.
  beforeEach(() => {
    vi.mocked(getLesson).mockReset();
  });

  test("renders a friendly inline message instead of throwing, for a non-ApiError failure", async () => {
    vi.mocked(getLesson).mockRejectedValue(new TypeError("fetch failed"));

    render(await renderPage("1", "1"));

    expect(
      screen.getByText("Could not reach the server. Is the backend running?"),
    ).toBeInTheDocument();
  });

  test("renders the ApiError's own message for a non-404 API failure", async () => {
    vi.mocked(getLesson).mockRejectedValue(new ApiError(500, "Internal server error"));

    render(await renderPage("1", "1"));

    expect(screen.getByText("Internal server error")).toBeInTheDocument();
  });

  test("still calls notFound() when the lesson does not exist", async () => {
    vi.mocked(getLesson).mockRejectedValue(new ApiError(404, "Lesson not found"));

    await expect(renderPage("1", "1")).rejects.toBeInstanceOf(NotFoundSignal);
  });

  test("still calls notFound() when the lesson belongs to a different course", async () => {
    vi.mocked(getLesson).mockResolvedValue(lessonIn(1));

    await expect(renderPage("2", "1")).rejects.toBeInstanceOf(NotFoundSignal);
  });

  test("still calls notFound() on a non-numeric course id, without calling the API", async () => {
    await expect(renderPage("abc", "1")).rejects.toBeInstanceOf(NotFoundSignal);
    expect(getLesson).not.toHaveBeenCalled();
  });

  test("still calls notFound() on a non-numeric lesson id, without calling the API", async () => {
    await expect(renderPage("1", "abc")).rejects.toBeInstanceOf(NotFoundSignal);
    expect(getLesson).not.toHaveBeenCalled();
  });

  test("still renders normally when course and lesson agree", async () => {
    vi.mocked(getLesson).mockResolvedValue(lessonIn(1));

    await expect(renderPage("1", "1")).resolves.toBeTruthy();
  });
});
