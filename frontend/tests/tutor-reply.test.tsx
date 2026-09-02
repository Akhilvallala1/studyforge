/**
 * The tutor reply's register layout: the one place the grounded/ungrounded boundary
 * becomes something a learner can see.
 *
 * The server sends `answer`, `ask`, `beyond` and `check` as separate fields, and
 * TutorReply is the component that keeps them separate on screen. Two properties carry
 * the whole guarantee and both are asserted here.
 *
 * ORDER AND SIBLINGHOOD. There is exactly one boundary marker in a reply, the
 * disclaimer sentence inside the `beyond` block, and everything above it is grounded by
 * construction. `ask` is grounded (the move it asks for is answerable from the course
 * text directly above), so it must sit ABOVE `beyond`; put it below, or nest it inside,
 * and a grounded handover reads as unchecked general knowledge. The driving case is a
 * reply carrying `beyond` AND `ask` together, which a partly-covered question really
 * produces.
 *
 * DISTINGUISHABILITY WITHOUT COLOUR. The registers are told apart by headings, borders
 * and the disclaimer, never by hue alone: the reader who most needs the boundary is the
 * one who cannot see a hue change. jsdom loads no stylesheet, so the assertions pin the
 * class contract that carries this (border style and width), which is exactly the thing
 * a restyle could silently drop.
 *
 * TutorReply is module-private and rendered through ConceptTutor on purpose: exporting
 * it for tests would invite callers, and the conversation fetch is one mock away.
 *
 * Written as mutation tests. Each was confirmed by making the change and watching the
 * right test go red:
 *   - swap the ask and beyond JSX blocks        -> the ordering test fails
 *   - move the ask block inside beyond's div    -> the siblinghood test fails
 *   - lift the disclaimer above the four blocks -> the disclaimer test fails
 *   - drop border-dashed from beyond            -> the greyscale test fails
 *   - flatten ask's border-l-4 to border        -> the greyscale test fails
 */

import { render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { ConceptTutor } from "@/components/ConceptTutor";
import { getTutorConversation } from "@/lib/api";
import type { TutorMessage } from "@/lib/types";

import { conversation, tutorRow } from "./fixtures";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getTutorConversation: vi.fn(),
  sendTutorMessage: vi.fn(),
}));

// The fixed copy, restated here rather than imported: these strings are the feature's
// visible contract, and a test that imported them would keep passing while a typo
// rewrote what every learner reads.
const GROUNDED = "From your course";
const ASK = "Your turn";
const BEYOND = "Not in your course";
const CHECK = "Check yourself";
const DISCLAIMER =
  "Your course does not cover this. What follows is general knowledge and has not been " +
  "checked against your material.";

/** Mount one reply through ConceptTutor and hand back the region that wraps it. */
async function renderReply(message: TutorMessage): Promise<HTMLElement> {
  vi.mocked(getTutorConversation).mockResolvedValue(conversation([message]));
  render(
    <ConceptTutor conceptKey="stability" conceptLabel="Stability" open onAnnounce={() => {}} />,
  );
  return await screen.findByRole("region", { name: "Tutor reply" });
}

/**
 * The block a register heading lives in: the heading's direct parent, which for every
 * register is the bordered div. Looked up by visible text, so a heading that stops
 * rendering fails here rather than three assertions later.
 */
function blockOf(region: HTMLElement, heading: string): HTMLElement {
  const label = within(region).getByText(heading);
  const block = label.parentElement;
  if (!(block instanceof HTMLElement)) {
    throw new Error(`the "${heading}" heading has no containing block element`);
  }
  return block;
}

/** Where a block sits among the region's direct children; -1 when it is not one. */
function slot(region: HTMLElement, block: HTMLElement): number {
  return Array.from(region.children).indexOf(block);
}

/** The reachable shape the ordering exists for: a partly-covered question in guided mode. */
const partlyCovered = tutorRow({
  answer: "Stability is the number of days until recall drops to ninety percent.",
  beyond: "Some schedulers call the same quantity memory half-life.",
  ask: "So what happens to stability after a successful review?",
});

describe("tutor reply block order", () => {
  test("a reply carrying beyond and ask together renders grounded, then ask, then beyond, as siblings", async () => {
    const region = await renderReply(partlyCovered);
    const grounded = blockOf(region, GROUNDED);
    const ask = blockOf(region, ASK);
    const beyond = blockOf(region, BEYOND);

    for (const [name, block] of [
      ["grounded", grounded],
      ["ask", ask],
      ["beyond", beyond],
    ] as const) {
      expect(
        block.parentElement,
        `the ${name} block must be a direct child of the reply region, not nested inside another block`,
      ).toBe(region);
    }
    expect(
      beyond.contains(ask),
      "the ask block must not sit inside the beyond block: everything under that heading reads as unchecked general knowledge",
    ).toBe(false);
    expect(
      slot(region, grounded),
      "the grounded explanation must come first: ask hands over a move withheld from the text directly above it",
    ).toBeLessThan(slot(region, ask));
    expect(
      slot(region, ask),
      "ask must sit above beyond: the disclaimer is the reply's one boundary marker, and a grounded handover below it reads as not from the course",
    ).toBeLessThan(slot(region, beyond));
  });

  test("check keeps the last slot, below beyond, on an answer-mode reply", async () => {
    const region = await renderReply(
      tutorRow({
        answer: "Stability is the number of days until recall drops to ninety percent.",
        beyond: "Some schedulers call the same quantity memory half-life.",
        check: "What does stability count down to?",
      }),
    );
    const grounded = blockOf(region, GROUNDED);
    const beyond = blockOf(region, BEYOND);
    const check = blockOf(region, CHECK);

    expect(
      check.parentElement,
      "the check block must be a direct child of the reply region",
    ).toBe(region);
    expect(
      slot(region, grounded),
      "the grounded explanation must come before the recall question",
    ).toBeLessThan(slot(region, check));
    expect(
      slot(region, beyond),
      "check is a question about the whole reply, so it keeps the last slot, after beyond",
    ).toBeLessThan(slot(region, check));
  });

  test("the disclaimer renders inside the beyond block and nowhere else", async () => {
    const region = await renderReply(partlyCovered);
    const beyond = blockOf(region, BEYOND);

    const sightings = screen.getAllByText(DISCLAIMER);
    expect(
      sightings,
      "the reply has exactly one boundary marker; a second disclaimer would move where the boundary appears to be",
    ).toHaveLength(1);
    expect(
      beyond.contains(sightings[0]),
      "the disclaimer must sit inside the beyond block: it disclaims that block and nothing above it",
    ).toBe(true);
  });
});

describe("register distinguishability without colour", () => {
  test("the registers stay apart on a greyscale screen: border style and width carry them, not hue", async () => {
    const region = await renderReply(partlyCovered);
    const grounded = blockOf(region, GROUNDED);
    const ask = blockOf(region, ASK);
    const beyond = blockOf(region, BEYOND);

    // Beyond against grounded: dashed against solid. Drop the dash and the two blocks
    // differ only in border hue, which is invisible to exactly the reader the split is
    // for.
    expect(
      beyond,
      "the beyond block must keep its dashed border: without it, only hue separates unchecked text from course text",
    ).toHaveClass("border-dashed");
    expect(
      grounded,
      "the grounded block must stay solid-bordered so the dashed beyond block reads as different in shape",
    ).not.toHaveClass("border-dashed");

    // Ask against both: a heavy left accent bar against uniform thin borders.
    expect(
      ask,
      "the ask block must keep its thick left accent bar; it is what marks the handover without relying on its background colour",
    ).toHaveClass("border-l-4");
    expect(grounded, "the grounded block has no accent bar").not.toHaveClass("border-l-4");
    expect(beyond, "the beyond block has no accent bar").not.toHaveClass("border-l-4");

    // The headings are the first carrier, and they must be visible text, not sr-only:
    // a sighted greyscale reader relies on them as much as a screen reader user does.
    for (const [block, heading] of [
      [grounded, GROUNDED],
      [ask, ASK],
      [beyond, BEYOND],
    ] as const) {
      expect(
        within(block).getByText(heading),
        `the "${heading}" heading must stay visible, not sr-only`,
      ).not.toHaveClass("sr-only");
    }
  });
});
