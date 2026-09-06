/**
 * A deleted course's spend row must not be a link.
 *
 * `course_id` survives deletion, because the backend needs it to keep a dead course's
 * spend in its own bucket (main.py buckets on the deletion stamp as well as the id).
 * SQLite then reissues that id to the next course created. So the page's old test,
 * `row.course_id !== null`, was true for dead courses too, and a dead course's row was
 * rendered as a link to the LIVE course that had inherited its rowid: clicking a row
 * labelled with one course's name, showing that course's money, navigated to a different
 * course entirely. Where the id had not been reissued, the link 404ed instead.
 *
 * The signal is `title`, which the backend documents as the live course's title and null
 * once it is gone. These tests are written against the reused-id case specifically,
 * because that is the one where a wrong answer is silent: the 404 announces itself.
 *
 * Found by qa-tester on a real server, not deduced from the types.
 *
 * Mutation-verified against the whole suite, each mutant the only edit and each restore
 * checked byte for byte. Measured, not predicted: I guessed two of these wrong.
 * - ignore `title`, test only the id, which
 *   is the shape this replaced                 -> three fail: both no-link tests and the
 *   "(deleted)" test, the last because a linked row carries no such text
 * - send a deleted row to the note link
 *   instead of plain text                      -> the SAME three, and that is the point
 *   of asserting no link at all rather than a specific wrong href: the suite does not
 *   care which wrong destination it is, only that there is one
 * - key on group and id alone                  -> only the key test fails, two rows
 *   sharing `course:1`. Nothing else notices, which is why that test spies on
 *   console.error rather than on the rendered output
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

import UsagePage from "@/app/usage/page";
import { getUsage } from "@/lib/api";
import type { PerCourseUsage, UsageSummary } from "@/lib/types";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getUsage: vi.fn(),
}));

function courseRow(over: Partial<PerCourseUsage>): PerCourseUsage {
  return {
    group: "course",
    course_id: 1,
    title: "Organic Chemistry",
    label: "Organic Chemistry",
    note: null,
    calls: 3,
    input_tokens: 100,
    output_tokens: 200,
    estimated_cost_usd: 0.5,
    ...over,
  };
}

/** Deleted: the backend keeps the id and the historical name, and nulls the title. */
const DELETED = courseRow({ course_id: 1, title: null, label: "Photosynthesis" });
/** Live, and holding the same rowid the deleted one used to have. */
const REUSED = courseRow({ course_id: 1, title: "Cell Biology", label: "Cell Biology" });

async function renderUsage(perCourse: PerCourseUsage[]) {
  const usage: UsageSummary = {
    totals: {
      calls: 3,
      input_tokens: 100,
      output_tokens: 200,
      estimated_cost_usd: 0.5,
      approximate: false,
      approximate_note: null,
    },
    per_course: perCourse,
    recent_calls: [],
    alert: { active: false, threshold_usd: 10, total_usd: 0.5, acknowledged: null },
    limit: { configured: false, limit_usd: null, reached: false },
  };
  vi.mocked(getUsage).mockResolvedValue(usage);
  render(await UsagePage());
}

function attributionCell(label: string): HTMLElement {
  const cell = screen.getByText(label, { selector: "td *" }).closest("td");
  if (!cell) throw new Error(`no attribution cell for ${label}`);
  return cell;
}

describe("usage attribution for a deleted course", () => {
  beforeEach(() => vi.clearAllMocks());

  test("does not link a deleted course to the live course that reused its id", async () => {
    await renderUsage([REUSED, DELETED]);

    // The row is still shown: the money was really spent and hiding it would be worse.
    // What it must not be is navigable, since every href available to it is wrong.
    const cell = attributionCell("Photosynthesis");
    expect(
      within(cell).queryByRole("link"),
      "a deleted course has no correct destination, so it must not be a link at all",
    ).toBeNull();

    // The live row is untouched, which is the half a careless fix breaks.
    const live = within(attributionCell("Cell Biology")).getByRole("link");
    expect(live).toHaveAttribute("href", "/courses/1");
  });

  test("does not link a deleted course whose id was never reissued", async () => {
    await renderUsage([DELETED]);

    expect(within(attributionCell("Photosynthesis")).queryByRole("link")).toBeNull();
  });

  test("says the course is gone rather than leaving the name unexplained", async () => {
    await renderUsage([DELETED]);

    // Without this the learner sees a name they cannot click and is told nothing. The
    // assertion is on the cell, not the whole page, so it cannot pass on stray copy.
    expect(attributionCell("Photosynthesis")).toHaveTextContent("(deleted)");
  });

  test("gives the two rows distinct keys despite the shared id", async () => {
    // React logs a duplicate key as console.error and still renders, so asserting on the
    // rendered output alone would pass with the bug present. Spy on the channel the
    // warning actually uses.
    const errors: unknown[][] = [];
    const spy = vi.spyOn(console, "error").mockImplementation((...args) => {
      errors.push(args);
    });
    try {
      await renderUsage([REUSED, DELETED]);
    } finally {
      spy.mockRestore();
    }

    const duplicate = errors.filter((args) => String(args[0]).includes("same key"));
    expect(duplicate, `React reported a duplicate key: ${JSON.stringify(duplicate)}`).toHaveLength(
      0,
    );
  });

  test("leaves a non-course group pointing at its own note", async () => {
    // The deleted-course branch must not swallow these: they are not courses, they have
    // no id, and their note anchor is the only correct destination they have.
    await renderUsage([
      courseRow({ group: "remediation", course_id: null, title: null, label: "Re-teaching" }),
    ]);

    const link = within(attributionCell("Re-teaching")).getByRole("link");
    expect(link).toHaveAttribute("href", "#note-remediation");
  });
});
