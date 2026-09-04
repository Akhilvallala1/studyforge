/**
 * The concept map page was the last one under src/app still ending its catch with a
 * bare `throw err`, so with the backend down it served Next's generic 500 while its
 * own sibling tabs served the friendly inline message. CourseTabs links straight here
 * from the course page, so the inconsistency was one click wide, not buried.
 *
 * Same contract as the course and lesson pages: a genuine 404 still 404s, a non-numeric
 * id still 404s without the API being called, and everything else renders inline.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

import ConceptsPage from "@/app/courses/[courseId]/concepts/page";
import { ApiError, getCourseConcepts } from "@/lib/api";

/** Stands in for Next's real signal, which throws so rendering cannot continue. */
class NotFoundSignal extends Error {}

vi.mock("next/navigation", () => ({
  notFound: vi.fn(() => {
    throw new NotFoundSignal("NEXT_NOT_FOUND");
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCourseConcepts: vi.fn(),
}));

function renderPage(courseId: string) {
  return ConceptsPage({ params: Promise.resolve({ courseId }) } as never);
}

describe("concepts page load failure", () => {
  // Braces, not an expression body: `mockReset()` returns the mock itself, and Vitest
  // treats a value returned from beforeEach as a teardown to run after the test, which
  // would call the mock with the rejection the test just installed.
  beforeEach(() => {
    vi.mocked(getCourseConcepts).mockReset();
  });

  test("renders a friendly inline message instead of throwing, for a non-ApiError failure", async () => {
    vi.mocked(getCourseConcepts).mockRejectedValue(new TypeError("fetch failed"));

    render(await renderPage("1"));

    expect(
      screen.getByText("Could not reach the server. Is the backend running?"),
    ).toBeInTheDocument();
  });

  test("renders the ApiError's own message for a non-404 API failure", async () => {
    vi.mocked(getCourseConcepts).mockRejectedValue(new ApiError(500, "Internal server error"));

    render(await renderPage("1"));

    expect(screen.getByText("Internal server error")).toBeInTheDocument();
  });

  test("renders a heading on the error branch, so the page is not left without one", async () => {
    vi.mocked(getCourseConcepts).mockRejectedValue(new ApiError(500, "Internal server error"));

    render(await renderPage("1"));

    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  test("keeps the way back out of the error branch", async () => {
    vi.mocked(getCourseConcepts).mockRejectedValue(new ApiError(500, "Internal server error"));

    render(await renderPage("1"));

    // The error branch is a dead end without this: the tab bar is part of the success
    // branch, so with the backend down this link is the only navigation on the page.
    expect(screen.getByRole("link", { name: /All courses/ })).toHaveAttribute("href", "/courses");
  });

  test("still calls notFound() on a genuine 404, rather than showing the friendly message", async () => {
    vi.mocked(getCourseConcepts).mockRejectedValue(new ApiError(404, "Course not found"));

    await expect(renderPage("1")).rejects.toBeInstanceOf(NotFoundSignal);
  });

  test("still calls notFound() on a non-numeric course id, without calling the API", async () => {
    await expect(renderPage("abc")).rejects.toBeInstanceOf(NotFoundSignal);
    expect(getCourseConcepts).not.toHaveBeenCalled();
  });
});
