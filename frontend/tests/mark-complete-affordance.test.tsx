/**
 * The completed button's hover treatment, pinned because it is a contrast threshold
 * and nothing else in the suite can see one.
 *
 * The restyle first hovered this button to the success tone's boundary colour, on the
 * reasoning that it is the next step in the same family. Measured on the built bundle
 * that put the button's own label at 3.57:1 light and 3.91:1 dark, under the 4.5:1 it
 * needs as normal-size text, and the reveal-on-hover Undo hint lower still. The fix
 * added a dedicated hover surface token and took the hint to full opacity, which
 * measures 4.78:1 and 4.95:1. MarkCompleteButton.tsx carries the full derivation.
 *
 * What these tests can and cannot do. jsdom applies no stylesheet, so they cannot
 * measure anything: they assert the class names the measurement was taken against.
 * That is a real guard against the specific way this regressed, which was a swap of
 * one token for another, and it is worth nothing against a change to what the token
 * itself resolves to. A contrast change made in globals.css will not redden these.
 *
 * Both were verified by mutation rather than assumed. Pointing the hover fill back at
 * the boundary token reddens the first test; putting the hint back to 80% reddens the
 * second. Colours are described in prose below rather than written as class names,
 * because Tailwind v4's scanner reads test files too and a utility spelled out in a
 * comment emits a real rule into the shipped CSS.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { MarkCompleteButton } from "@/components/MarkCompleteButton";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

describe("MarkCompleteButton completed state", () => {
  test("hovers to the tone's own hover surface, not to any other fill", () => {
    render(<MarkCompleteButton lessonId={1} completed />);
    const button = screen.getByRole("button", { name: "Mark this lesson as not complete" });
    const hoverFills = button.className
      .split(/\s+/)
      .filter((token) => token.startsWith("hover:bg-"));

    expect(hoverFills).toEqual(["hover:bg-success-surface-hover"]);
  });

  test("reveals the Undo hint at full opacity, since hover is the only state it is read in", () => {
    render(<MarkCompleteButton lessonId={1} completed />);
    const hint = screen.getByText("Undo");
    const reveals = hint.className
      .split(/\s+/)
      .filter((token) => /^group-(hover|focus-visible):opacity-/.test(token))
      .sort();

    expect(reveals).toEqual([
      "group-focus-visible:opacity-100",
      "group-hover:opacity-100",
    ]);
  });
});
