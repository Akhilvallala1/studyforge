/**
 * The lesson page refuses a lesson that belongs to a different course.
 *
 * The API resolves a lesson by its own id and takes no course id, so the course
 * segment of /courses/[courseId]/lessons/[lessonId] is unchecked input. Before this
 * guard, /courses/2/lessons/1 returned 200 and rendered course 1's lesson under
 * course 2's breadcrumb, with a "back to course" link pointing at a course the
 * lesson is not in. The reader had nothing on screen telling them the pairing was
 * wrong.
 *
 * Asserted through notFound() rather than through rendered output, because that is
 * the actual contract: Next turns the thrown signal into the 404 page, and a test
 * that checked for absent text would also pass if the page merely rendered empty.
 *
 * Written with mutation tests. Each was confirmed by making the change and watching
 * the right test go red:
 * - drop the `lesson.course_id !== course` guard -> the mismatch test fails
 * - weaken it to `==` between a string and a number -> the mismatch test fails
 * - drop `Number.isInteger(course)` -> the non-numeric course test fails
 * - tighten it to always call notFound() -> the matching-pair test fails
 */
import { describe, expect, test, vi, beforeEach } from "vitest";

import LessonPage from "@/app/courses/[courseId]/lessons/[lessonId]/page";
import { getLesson } from "@/lib/api";
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

describe("lesson page course scoping", () => {
  beforeEach(() => {
    vi.mocked(getLesson).mockReset();
  });

  test("404s when the lesson belongs to a different course", async () => {
    vi.mocked(getLesson).mockResolvedValue(lessonIn(1));

    await expect(renderPage("2", "1")).rejects.toBeInstanceOf(NotFoundSignal);
  });

  test("renders when the course and lesson agree", async () => {
    vi.mocked(getLesson).mockResolvedValue(lessonIn(2));

    await expect(renderPage("2", "1")).resolves.toBeTruthy();
  });

  test("404s on a non-numeric course id without calling the API", async () => {
    await expect(renderPage("abc", "1")).rejects.toBeInstanceOf(NotFoundSignal);
    expect(getLesson).not.toHaveBeenCalled();
  });

  test("404s on a non-numeric lesson id without calling the API", async () => {
    await expect(renderPage("2", "abc")).rejects.toBeInstanceOf(NotFoundSignal);
    expect(getLesson).not.toHaveBeenCalled();
  });
});
