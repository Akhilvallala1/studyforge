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
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { QuizSection } from "@/components/QuizSection";

import { quizItem, quizProgress } from "./fixtures";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  answerQuiz: vi.fn(),
}));

function renderQuiz() {
  return render(
    <QuizSection quiz={[quizItem({ id: 1, kind: "short" })]} progress={quizProgress()} />,
  );
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
