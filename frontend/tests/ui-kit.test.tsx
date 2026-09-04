/**
 * ErrorState's role override, locked in because it was a real defect.
 *
 * The component announces itself as `role="alert"` by default, since it is usually
 * the only thing on screen worth announcing. A caller nesting one inside a region
 * that is ALREADY a live region has to be able to turn that off, or the message is
 * announced twice.
 *
 * The first implementation wrote `role = "alert"` in the destructure. That reads as
 * a default and is not one: a destructuring default fires on `undefined`, so a
 * caller passing `role={undefined}` got "alert" handed back rather than the
 * attribute removed, and a destructured prop never reaches `...props` either, so
 * there was no second path for the caller's value to arrive by. The override was
 * unreachable by construction while looking, in the source, exactly like it worked.
 *
 * The fix is to keep `role` OUT of the destructure so it stays in `...props`, and to
 * write the default on the element before the spread. React then omits an attribute
 * whose spread value is `undefined`, which is what makes suppression possible at all.
 *
 * The middle test is the one that matters. Asserting only the default and a
 * replacement role would still pass against the broken version; passing `undefined`
 * explicitly is the only case that distinguishes them.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ErrorState } from "@/components/ui/ErrorState";

describe("ErrorState role", () => {
  test("announces itself as an alert by default", () => {
    render(<ErrorState message="The backend is unreachable." />);

    expect(screen.getByRole("alert")).toHaveTextContent("The backend is unreachable.");
  });

  test("role={undefined} removes the attribute rather than restoring the default", () => {
    const { container } = render(
      <ErrorState role={undefined} message="Nested in a live region already." />,
    );

    expect(container.firstElementChild?.hasAttribute("role")).toBe(false);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("a caller can substitute its own role", () => {
    render(<ErrorState role="status" message="Quieter announcement." />);

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

/**
 * The Today and Usage pages both pass `title=""` to suppress the heading paragraph,
 * relying on `{title && <p>...}` treating an empty string as falsy. Tightening that
 * check to `{title !== undefined && <p>...}` (a natural-looking edit: it reads as
 * "only skip this when the caller didn't pass a title at all") renders an empty,
 * bold paragraph above the message instead, and nothing else in this suite catches
 * it because every other test either omits `title` or passes a non-empty one.
 */
describe("ErrorState title suppression", () => {
  test('title="" renders only the message paragraph, no heading', () => {
    const { container } = render(<ErrorState title="" message="x" />);

    expect(container.querySelectorAll("p")).toHaveLength(1);
    expect(screen.getByText("x")).toBeInTheDocument();
  });
});
