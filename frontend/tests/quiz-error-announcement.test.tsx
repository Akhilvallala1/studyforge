/**
 * The client-side validation error has to be announced.
 *
 * Pressing "Check answer" with an empty input never reaches the server: `submit`
 * returns early and sets `error` to "Enter an answer first.". That message rendered
 * in a bare <p> sitting OUTSIDE the aria-live region a few lines below it, so a
 * screen reader user pressed the button, nothing was announced, and the reason their
 * answer had not been checked was on screen where only a sighted user would find it.
 *
 * The region below is deliberately not the fix: it is documented as carrying the
 * RESULT, and it is polite, so a validation error folded into it would queue behind
 * the result announcement instead of interrupting for something the learner just did.
 *
 * Mutation-verified: removing role="alert" from the <p> makes the first test red,
 * and moving the <p> inside the polite region makes the second red.
 */
import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { QuizSection } from "@/components/QuizSection";
import { ApiError, answerQuiz } from "@/lib/api";

import { deferred, quizItem, quizProgress } from "./fixtures";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  answerQuiz: vi.fn(),
}));

function renderQuiz(kind: "mcq" | "short" = "short") {
  const item = quizItem({ id: 1, kind });
  const view = render(<QuizSection quiz={[item]} progress={quizProgress()} />);
  return { ...view, item };
}

describe("empty-answer validation message", () => {
  test("is exposed as an alert, so it is announced", () => {
    renderQuiz();

    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Enter an answer first.");
  });

  test("is assertive rather than folded into the polite result region", () => {
    const { container } = renderQuiz();

    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));

    const alert = screen.getByRole("alert");
    // role="alert" carries an implicit assertive live region. Nesting it inside the
    // polite one would downgrade it to that container's politeness.
    expect(
      container.querySelector('[aria-live="polite"]')?.contains(alert),
      "the validation error must not live inside the polite result region",
    ).toBe(false);
  });
});

/**
 * Editing the answer after a validation complaint about it.
 *
 * "Enter an answer first." is a claim about the CURRENT answer, so it goes stale the
 * moment that answer changes; leaving it on screen (and, since the earlier suite, in an
 * ASSERTIVE role) after the learner has already fixed the thing it complained about
 * means a screen reader user is told their valid answer is still empty.
 *
 * A server error is a different claim: it is about the last REQUEST, not about what is
 * currently typed, and editing the field does not undo a failed request. So it is left
 * in place on edit and only resolved by the next submit. See the ErrorKind comment in
 * QuizSection.tsx for the same reasoning at the source.
 *
 * Mutation-verified: dropping the errorKind check in the text input's onChange (always
 * clearing on edit) makes the "leaves a server error in place" test fail, quoted below
 * next to the change.
 */
describe("editing the answer clears a stale validation error", () => {
  test("clears it when a short-answer input changes", () => {
    renderQuiz("short");
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter an answer first.");

    fireEvent.change(screen.getByPlaceholderText("Your answer"), {
      target: { value: "Circular" },
    });

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  test("clears it when an mcq option is picked", () => {
    const { item } = renderQuiz("mcq");
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter an answer first.");

    fireEvent.click(screen.getByRole("radio", { name: item.options[0] }));

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  test("leaves a server error in place, since editing the answer does not undo a failed request", async () => {
    renderQuiz("short");
    const failure = deferred<never>();
    vi.mocked(answerQuiz).mockReturnValue(failure.promise);
    fireEvent.change(screen.getByPlaceholderText("Your answer"), {
      target: { value: "Circular" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    await act(async () => failure.reject(new ApiError(500, "Could not reach the server.")));
    expect(screen.getByRole("alert")).toHaveTextContent("Could not reach the server.");

    fireEvent.change(screen.getByPlaceholderText("Your answer"), {
      target: { value: "Ellipse" },
    });

    expect(
      screen.getByRole("alert"),
      "a server error describes the last request, not the current answer, so editing must not silently drop it",
    ).toHaveTextContent("Could not reach the server.");
  });

  /*
   * The mcq half of the same rule. The two onChange handlers carry the identical
   * `errorKind === "validation"` guard, but only the text input above was pinned:
   * making the mcq handler clear every error kind unconditionally left the whole
   * suite green. It reds this test on the assertion below.
   */
  test("leaves a server error in place when another mcq option is picked", async () => {
    const { item } = renderQuiz("mcq");
    const failure = deferred<never>();
    vi.mocked(answerQuiz).mockReturnValue(failure.promise);
    fireEvent.click(screen.getByRole("radio", { name: item.options[0] }));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    await act(async () => failure.reject(new ApiError(500, "Could not reach the server.")));
    expect(screen.getByRole("alert")).toHaveTextContent("Could not reach the server.");

    fireEvent.click(screen.getByRole("radio", { name: item.options[1] }));

    expect(
      screen.getByRole("alert"),
      "a server error describes the last request, not the current answer, so picking another option must not silently drop it",
    ).toHaveTextContent("Could not reach the server.");
  });
});

/**
 * Re-announcing an unchanged validation error.
 *
 * `role="alert"` announces on the node being INSERTED or its text CHANGING. Pressing
 * "Check answer" twice on a field that is still empty sets `error` to the identical
 * literal both times, so with no key change the paragraph is the same DOM node before
 * and after the second click, its text unchanged, and a MutationObserver on it records
 * nothing: an assistive-tech user hears the message once and then silence on the
 * second, identical press. Keying the paragraph on an incrementing nonce forces React
 * to tear the old node down and mount a fresh one on every submit, identical text or
 * not, which is what this test measures directly on the node reference (the same
 * technique the PR review used with a MutationObserver, applied to node identity
 * instead of watching for a mutation record).
 *
 * Mutation-verified: removing the `key={state.errorNonce}` prop from the alert
 * paragraph in QuizSection.tsx makes "gets a new DOM node" fail with
 * `expect(second).not.toBe(first) // second is first`, since the two clicks then
 * commit into the very same <p>.
 */
describe("a repeated identical validation error re-announces", () => {
  test("gets a new DOM node on the second identical empty submit", () => {
    renderQuiz("short");
    const button = screen.getByRole("button", { name: "Check answer" });

    fireEvent.click(button);
    const first = screen.getByRole("alert");
    fireEvent.click(button);
    const second = screen.getByRole("alert");

    expect(second, "a role=\"alert\" node reused across two identical submits never re-announces").not.toBe(first);
    expect(second).toHaveTextContent("Enter an answer first.");
  });

  test("does not move focus off the button across two identical empty submits", () => {
    renderQuiz("short");
    const button = screen.getByRole("button", { name: "Check answer" });
    // fireEvent.click does not focus its target in jsdom, so focus has to be placed
    // explicitly for the assertions below to be about focus at all. Removing this line
    // does NOT leave the test vacuously green, as an earlier version of this comment
    // claimed: focus starts on <body>, so the first toHaveFocus() fails outright and
    // the test reds. Measured, not reasoned.
    act(() => button.focus());
    expect(button).toHaveFocus();

    fireEvent.click(button);
    expect(
      button,
      "the empty-answer guard returns before submitting is ever set, so nothing here should disable or blur the button",
    ).toHaveFocus();
    fireEvent.click(button);
    expect(button).toHaveFocus();
  });
});
