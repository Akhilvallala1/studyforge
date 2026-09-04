/**
 * Two contracts the courses page carries that nothing else in the suite pins.
 *
 * FIRST, the ids. `#new-course` and `#create-first-course` are a DOM contract between
 * this page and DeleteCourseButton's focus restore: after a row unmounts, the provider
 * looks the surviving control up by id and puts focus there. They are mutually exclusive
 * by construction, and which one exists is exactly what changes when the last course
 * goes, which is why the restore resolves them by lookup at the moment it needs them.
 *
 * focus-restoration.test.tsx already covers the restore itself, but against hand-written
 * <a id="new-course"> fixtures: nothing there renders this page, so an id could be
 * dropped here and that suite would stay green. The restyle moved both ids through NEW
 * component boundaries (PageHeader's `actions` prop, EmptyState's `action` prop), which
 * is precisely the change that could swallow one, for instance if either primitive
 * cloned its slot instead of passing it through. These tests render the real page.
 *
 * SECOND, PRIMARY_LINK_CLASSES. The page cannot use Button for these two controls,
 * because Button renders a native <button> and both of these must be real links for the
 * id lookup above and for Next's prefetch. So the class list is copied by hand, and a
 * hand-copied class list drifts silently the moment Button's own styling moves. Rather
 * than export the constant purely to test it, this asserts against what the page
 * actually renders, which is the thing that has to stay in sync.
 *
 * Mutation-verified, each confirmed by making the change and watching the named test go
 * red:
 * - drop the `courses.length > 0 &&` guard on `actions` -> exclusivity test fails
 *   (both ids present at once on the empty list)
 * - render the empty state unconditionally -> exclusivity test fails
 * - change PRIMARY_LINK_CLASSES `px-4 py-2` to `px-3 py-1.5` -> drift test fails
 * - change Button's md size or primary variant without touching the page -> drift fails
 */
import { render } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

import CoursesPage from "@/app/courses/page";
import { Button } from "@/components/ui/Button";
import { listCourses } from "@/lib/api";
import type { CourseSummary } from "@/lib/types";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  listCourses: vi.fn(),
  getDeletionPreview: vi.fn(),
  deleteCourse: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

const course: CourseSummary = {
  id: 1,
  title: "Organic Chemistry",
  description: "A course.",
};

async function renderPage(courses: CourseSummary[]) {
  vi.mocked(listCourses).mockResolvedValue(courses);
  render(await CoursesPage());
}

/** Order and duplicates are not part of the contract; the set of classes is. */
function classSet(element: Element): Set<string> {
  return new Set(element.className.split(/\s+/).filter(Boolean));
}

describe("courses page new-course id contract", () => {
  beforeEach(() => vi.clearAllMocks());

  test("offers only #new-course while the list has courses", async () => {
    await renderPage([course]);

    const header = document.querySelectorAll("#new-course");
    expect(
      header,
      "the restore looks this up by id, so a second copy would make which one it finds arbitrary",
    ).toHaveLength(1);
    expect(header[0].tagName).toBe("A");
    expect(header[0]).toHaveAttribute("href", "/courses/new");
    expect(
      document.querySelector("#create-first-course"),
      "the empty state's link must not exist while there is anything in the list",
    ).toBeNull();
  });

  test("offers only #create-first-course once the list is empty", async () => {
    await renderPage([]);

    const empty = document.querySelectorAll("#create-first-course");
    expect(empty).toHaveLength(1);
    expect(empty[0].tagName).toBe("A");
    expect(empty[0]).toHaveAttribute("href", "/courses/new");
    expect(
      document.querySelector("#new-course"),
      "deleting the last course removes this control entirely, which is the whole reason the restore falls back to the empty state link",
    ).toBeNull();
  });
});

describe("courses page primary link styling stays level with Button", () => {
  beforeEach(() => vi.clearAllMocks());

  /**
   * The two omissions are deliberate and cannot apply to an anchor, so they are
   * subtracted rather than asserted absent: an <a> is never :disabled.
   */
  const BUTTON_ONLY = new Set(["disabled:opacity-60", "disabled:pointer-events-none"]);

  test.each([
    ["#new-course", [course]],
    ["#create-first-course", [] as CourseSummary[]],
  ])("%s matches Button primary/md", async (selector, courses) => {
    await renderPage(courses);
    const link = document.querySelector(selector);
    expect(link, `${selector} should be rendered for this list`).not.toBeNull();

    // Its own container: the rendered page already has a Delete button per row,
    // so a document-wide role query here would be ambiguous.
    const { container } = render(<Button variant="primary" size="md" />);
    const button = container.querySelector("button") as HTMLButtonElement;

    const expected = new Set([...classSet(button)].filter((c) => !BUTTON_ONLY.has(c)));
    expect(
      classSet(link as Element),
      "PRIMARY_LINK_CLASSES is a hand-copy of Button's primary/md classes; when Button moves, this is what goes stale",
    ).toEqual(expected);
  });
});
