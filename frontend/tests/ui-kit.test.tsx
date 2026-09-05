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
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { Button } from "@/components/ui/Button";
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

/**
 * `type = "button"` is a load-bearing default, not a tidiness one. HTML's own default
 * for a <button> with no type is "submit", so dropping that word from Button's
 * destructure turns every unadorned Button inside a <form> into a submit control. The
 * migration this PR performs replaces raw <button> elements with this primitive across
 * GenerateForm, which is one large form, so the blast radius is that whole page.
 *
 * The second test catches the regression, and it leans on a negative assertion, which
 * is worth nothing on its own: if this primitive silently stopped rendering, or the
 * click never landed, `not.toHaveBeenCalled()` would pass for the wrong reason. The
 * first test is its control. Same form, same click, same handler, differing only in the
 * prop under test, so a broken harness fails both instead of quietly passing one.
 *
 * Run, not assumed: rewriting the destructure to a bare `type` fails the second test on
 * "Number of calls: 1" while the first still passes. The behaviour assertion is checked
 * before the attribute one deliberately, so that failure lands on the submit that
 * actually happened rather than on a missing attribute.
 */
describe("Button type default", () => {
  function FormHarness({ onSubmit, type }: { onSubmit: () => void; type?: "submit" }) {
    return (
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <Button type={type}>Go</Button>
      </form>
    );
  }

  test('type="submit" submits the surrounding form (control for the test below)', () => {
    const onSubmit = vi.fn();
    render(<FormHarness onSubmit={onSubmit} type="submit" />);

    fireEvent.click(screen.getByRole("button", { name: "Go" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Go" })).toHaveAttribute("type", "submit");
  });

  test("an unadorned Button does not submit the surrounding form", () => {
    const onSubmit = vi.fn();
    render(<FormHarness onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: "Go" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Go" })).toHaveAttribute("type", "button");
  });
});

/**
 * The `tinted` variant works by INHERITING its colour: it is meant for an outlined
 * button inside a status-tinted `Callout`, and `border-current` picks up whichever
 * `text-danger` / `text-success` / `text-warning` the Callout put on its wrapper. So
 * the one thing that must stay true of it is a negative: it must not set a colour of
 * its own. Adding `text-ink` to it, which is what every other bordered variant does
 * and so is the natural edit, silently severs the inheritance and takes the border
 * back to a neutral grey on a tinted background, which is the exact contrast
 * regression this variant exists to avoid.
 *
 * Be honest about what this test is: it reads a class STRING. jsdom loads no
 * stylesheet, so nothing here can prove a rendered colour, and the contrast figures
 * behind the variant live in its comment in Button.tsx where they were measured off
 * the built bundle. What this catches is only the edit described above.
 *
 * It pins an exact SET rather than asserting that `border-current` is present and a
 * text colour is absent. Ran both ways, not assumed: those two weaker checks catch the
 * `text-ink` edit above but sail straight past a tone-specific border colour written
 * next to `border-current`, and past a resting background added alongside the hover
 * one. Those are the two shapes the severing edit actually takes, because nobody
 * deletes `border-current`, they add a colour beside it and it wins on source order.
 *
 * Note the colours above and below are named in prose, not as literal utility strings.
 * Tailwind v4 scans this file too, and an earlier draft of this very comment shipped a
 * dead border rule into the bundle by spelling one out. See Button.tsx's variant block.
 */
describe("Button tinted variant", () => {
  test("sets no colour of its own, so the enclosing tone shows through", () => {
    render(<Button variant="tinted">Generate another</Button>);
    const tokens = screen
      .getByRole("button", { name: "Generate another" })
      .className.split(/\s+/)
      .filter(Boolean);

    // Variant prefixes are stripped before matching so a colour cannot hide behind a
    // `hover:` or a `dark:`. `text-ui` is the SIZE token, not a colour, and is expected.
    const colour = tokens.filter((token) =>
      /^(bg|text|border|ring|fill|stroke|outline)-/.test(token.replace(/^.*:/, "")),
    );

    expect(colour.sort()).toEqual(["border-current", "hover:bg-surface", "text-ui"]);
  });
});
