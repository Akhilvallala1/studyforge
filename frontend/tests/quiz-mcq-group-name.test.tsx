/**
 * An MCQ's options have to say which question they belong to.
 *
 * The options rendered in a bare <div>, so a screen reader reached them as three loose
 * radios with no group and no name: "Circular, radio button 1 of 3", with the question
 * announced only if the user happened to arrow past it on the way in. On a lesson with
 * several MCQs that is several unlabelled groups in a row. The question <p> already
 * carries an id, and the short-answer input already names itself from it, so the group
 * is named the same way rather than with an sr-only legend.
 *
 * Mutation-verified, and measured rather than predicted: each of the three ways to
 * break this (drop role="radiogroup", drop the aria-labelledby, drop the id from the
 * question <p>) turns the same three tests red, every test below that queries the group
 * by name. The fourth is the short-answer one, which asserts the group's ABSENCE and so
 * correctly survives all three.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { QuizSection } from "@/components/QuizSection";

import { quizItem, quizProgress } from "./fixtures";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  answerQuiz: vi.fn(),
}));

const QUESTION = "Which orbit shape keeps a satellite's altitude constant?";

// The number is part of what a screen reader reads out, so the whole name is pinned
// rather than matched loosely: a test that looked only for the question would not notice
// the number going missing. The SPACE after it is equally pinned. This comment used to
// record its absence as pre-existing and out of scope; qa-tester then heard the result
// ("1.Which orbit shape") in a browser, so QuizSection now emits an explicit {" "} and
// this asserts it. Removing that expression turns every test below red except the last.
const NAMED = (n: number, question = QUESTION) => `${n}. ${question}`;

describe("mcq option group", () => {
  test("is a radiogroup named by its question", () => {
    render(<QuizSection quiz={[quizItem({ id: 1, kind: "mcq" })]} progress={quizProgress()} />);

    // getByRole's name option resolves the accessible name, so this fails both when the
    // role is missing and when the name does not compute, which is the pair that matters.
    expect(screen.getByRole("radiogroup", { name: NAMED(1) })).toBeInTheDocument();
  });

  test("contains the options it names, rather than naming an empty group", () => {
    render(<QuizSection quiz={[quizItem({ id: 1, kind: "mcq" })]} progress={quizProgress()} />);

    const group = screen.getByRole("radiogroup", { name: NAMED(1) });
    const options = screen.getAllByRole("radio");
    expect(options).toHaveLength(3);
    // A name on a group the radios are not inside would satisfy the first test and help
    // nobody, so assert containment rather than trusting the two queries found one thing.
    for (const option of options) expect(group).toContainElement(option);
  });

  test("gives each question its own group when a lesson has several", () => {
    const other = "What holds a geostationary satellite over one spot?";
    render(
      <QuizSection
        quiz={[
          quizItem({ id: 1, kind: "mcq" }),
          quizItem({ id: 2, kind: "mcq", question: other }),
        ]}
        progress={quizProgress({ items: 2 })}
      />,
    );

    expect(screen.getByRole("radiogroup", { name: NAMED(1) })).toBeInTheDocument();
    expect(screen.getByRole("radiogroup", { name: NAMED(2, other) })).toBeInTheDocument();
    expect(screen.getAllByRole("radiogroup")).toHaveLength(2);
  });

  test("does not wrap a short-answer item in a group", () => {
    render(<QuizSection quiz={[quizItem({ id: 1, kind: "short" })]} progress={quizProgress()} />);

    // The short-answer input names itself from the same question id. It is not a radio
    // group, and adding one around a single text field would announce a container the
    // learner cannot act on.
    expect(screen.queryByRole("radiogroup")).toBeNull();
  });
});
