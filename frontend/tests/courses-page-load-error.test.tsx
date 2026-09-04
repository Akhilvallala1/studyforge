/**
 * The courses page used to have NO try/catch at all: any failure from listCourses,
 * backend down, network error, a non-ApiError throw from fetch itself, propagated
 * straight out of the server component and into Next's own generic error boundary,
 * which renders "This page couldn't load" with an opaque digest and no app-specific
 * messaging. / and /usage already caught this and rendered an inline message; this
 * page did not.
 *
 * Also pins the DOM-contract corollary: on a load failure we do not reliably know
 * whether the course list is empty or not, so neither #new-course nor
 * #create-first-course may render. Rendering either would be a lie (we do not know
 * that create-first-course is true), and rendering both would break the mutually
 * exclusive contract courses-page-contract.test.tsx pins for DeleteCourseButton's
 * focus restore.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

import CoursesPage from "@/app/courses/page";
import { ApiError, listCourses } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  listCourses: vi.fn(),
  getDeletionPreview: vi.fn(),
  deleteCourse: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

describe("courses page load failure", () => {
  beforeEach(() => vi.clearAllMocks());

  test("renders a friendly inline message instead of throwing, for a non-ApiError failure", async () => {
    vi.mocked(listCourses).mockRejectedValue(new TypeError("fetch failed"));

    render(await CoursesPage());

    expect(
      screen.getByText("Could not reach the server. Is the backend running?"),
    ).toBeInTheDocument();
  });

  test("renders the ApiError's own message when the backend answers with a failure", async () => {
    vi.mocked(listCourses).mockRejectedValue(new ApiError(500, "Internal server error"));

    render(await CoursesPage());

    expect(screen.getByText("Internal server error")).toBeInTheDocument();
  });

  test("offers neither #new-course nor #create-first-course while the load failed", async () => {
    vi.mocked(listCourses).mockRejectedValue(new ApiError(500, "Internal server error"));

    render(await CoursesPage());

    expect(document.querySelector("#new-course")).toBeNull();
    expect(document.querySelector("#create-first-course")).toBeNull();
  });
});
