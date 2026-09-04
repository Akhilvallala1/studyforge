/**
 * The course detail page caught ApiError-404 and called notFound(), correctly, but
 * everything else fell through to a bare `throw err`, which propagates out of the
 * server component into Next's own generic error boundary instead of the app's own
 * messaging. This pins the fix, and the critical distinction it must not blur: a
 * genuine 404 still has to 404, only non-404 failures become the inline message.
 *
 * Non-numeric ids are asserted separately since that guard runs before the API is
 * even called and must keep 404ing unconditionally.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

import CoursePage from "@/app/courses/[courseId]/page";
import { ApiError, getCourse } from "@/lib/api";

/** Stands in for Next's real signal, which throws so rendering cannot continue. */
class NotFoundSignal extends Error {}

vi.mock("next/navigation", () => ({
  notFound: vi.fn(() => {
    throw new NotFoundSignal("NEXT_NOT_FOUND");
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCourse: vi.fn(),
}));

function renderPage(courseId: string) {
  return CoursePage({ params: Promise.resolve({ courseId }) } as never);
}

describe("course page load failure", () => {
  // Braces, not an expression body: `mockReset()` returns the mock itself, and Vitest
  // treats a value returned from beforeEach as a teardown to run after the test. That
  // teardown would call the mock with whatever implementation the test just set
  // (mockRejectedValue), producing an unhandled rejection attributed to an unrelated
  // line. Confirmed by hand: switching this back to the expression form reintroduces
  // three unhandled-rejection failures with no relation to the assertions themselves.
  beforeEach(() => {
    vi.mocked(getCourse).mockReset();
  });

  test("renders a friendly inline message instead of throwing, for a non-ApiError failure", async () => {
    vi.mocked(getCourse).mockRejectedValue(new TypeError("fetch failed"));

    render(await renderPage("1"));

    expect(
      screen.getByText("Could not reach the server. Is the backend running?"),
    ).toBeInTheDocument();
  });

  test("renders the ApiError's own message for a non-404 API failure", async () => {
    vi.mocked(getCourse).mockRejectedValue(new ApiError(500, "Internal server error"));

    render(await renderPage("1"));

    expect(screen.getByText("Internal server error")).toBeInTheDocument();
  });

  test("still calls notFound() on a genuine 404, rather than showing the friendly message", async () => {
    vi.mocked(getCourse).mockRejectedValue(new ApiError(404, "Course not found"));

    await expect(renderPage("1")).rejects.toBeInstanceOf(NotFoundSignal);
  });

  test("still calls notFound() on a non-numeric course id, without calling the API", async () => {
    await expect(renderPage("abc")).rejects.toBeInstanceOf(NotFoundSignal);
    expect(getCourse).not.toHaveBeenCalled();
  });
});
