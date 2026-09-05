"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ApiError, answerQuiz } from "@/lib/api";
import type { AttemptState, QuizItem, QuizProgress } from "@/lib/types";

interface Feedback {
  correct: boolean;
  expected: string;
}

/**
 * "validation" is the empty-answer guard in `submit`, entirely a client-side complaint
 * about the CURRENT `answer`, so it goes stale the instant the learner edits that answer
 * and is cleared on the next `onChange`. "server" is `answerQuiz` failing (network down,
 * `ApiError`), a fact about the last REQUEST, not about what is currently typed; editing
 * the field doesn't undo that the previous attempt never reached the server, so it is
 * left in place until the next submit (successful or not) decides its fate. Kept as a
 * separate field rather than inferred from the message text so clearing logic never has
 * to pattern-match app copy.
 */
type ErrorKind = "validation" | "server";

interface ItemState {
  answer: string;
  feedback: Feedback | null;
  attemptState: AttemptState;
  submitting: boolean;
  error: string | null;
  errorKind: ErrorKind | null;
  /**
   * Bumped every time `error` is set, and used as the error paragraph's `key`. `error`
   * can be set to the SAME literal twice in a row (two empty submits with no edit
   * between them), which leaves the string child unchanged, so React neither unmounts
   * nor patches the text node, and `role="alert"` has nothing to re-announce. Changing
   * the key forces the old node out and a fresh one in on every set, identical text or
   * not, so the second submit gets its own node to announce from.
   */
  errorNonce: number;
}

/**
 * Where focus goes once a submission that disabled controls finishes and they are
 * re-enabled or gone: back to the answer control for an item still open to a retry,
 * or to the "Correct" message once that is the only thing solving the item left behind.
 */
type PendingFocus = "answer" | "correct";

/** The item as the server last saw it, so a reload redraws the learner's last attempt. */
function restored(item: QuizItem): ItemState {
  const latest = item.attempt_state.latest_quiz_attempt;
  return {
    answer: latest?.answer ?? "",
    feedback: latest === null ? null : { correct: latest.correct, expected: latest.expected },
    attemptState: item.attempt_state,
    submitting: false,
    error: null,
    errorKind: null,
    errorNonce: 0,
  };
}

/** Record when an item became answerable, for the elapsed_ms timing signal. */
function markShown(shownAt: Map<number, number>, itemId: number, restart = false): void {
  if (restart || !shownAt.has(itemId)) shownAt.set(itemId, Date.now());
}

/** Undefined when the item was never stamped, so submission goes ahead untimed. */
function elapsedSince(shownAt: Map<number, number>, itemId: number): number | undefined {
  const start = shownAt.get(itemId);
  if (start === undefined) return undefined;
  const ms = Date.now() - start;
  return Number.isFinite(ms) && ms >= 0 ? ms : undefined;
}

export function QuizSection({ quiz, progress }: { quiz: QuizItem[]; progress: QuizProgress }) {
  const [answers, setAnswers] = useState<Record<number, ItemState>>({});
  /** When each item became answerable, for the elapsed_ms timing signal. */
  const shownAt = useRef<Map<number, number>>(new Map());

  /**
   * Per-item refs to the controls a submission's focus restoration might land on.
   * The radios and the text input are never unmounted (their options and their kind
   * are fixed once a lesson loads), so a plain ref per item is enough for either;
   * `mcqRefs` is keyed a second time by option because a submission's target is
   * whichever radio is CURRENTLY checked, not a fixed one. `correctRefs` is the
   * "Correct" message, the only thing left to land on once solving an item unmounts
   * its button and leaves its inputs disabled.
   */
  const inputRefs = useRef<Map<number, HTMLInputElement>>(new Map());
  const mcqRefs = useRef<Map<number, Map<string, HTMLInputElement>>>(new Map());
  const correctRefs = useRef<Map<number, HTMLParagraphElement>>(new Map());
  /**
   * Set right before `submit` starts disabling controls, consumed by the effect below
   * once the response it belongs to has rendered. A later commit for the same item
   * (an error message from the empty-answer guard, say) finds nothing armed and does
   * not touch focus, because the guard below only ever runs for a commit it set.
   */
  const pendingFocus = useRef<Map<number, PendingFocus>>(new Map());

  const stateOf = (item: QuizItem) => answers[item.id] ?? restored(item);
  /**
   * `update` may be a plain object or a function of the item's PRIOR state. The function
   * form exists for `errorNonce`, which has to increment off whatever the last render
   * actually stored, not off the `state` a caller closed over: `submit`'s catch branch
   * runs after an `await`, and a caller reading a nonce it captured before that await
   * would double-write the same next value if two submits for the same item ever raced.
   */
  const patch = (
    item: QuizItem,
    update: Partial<ItemState> | ((prev: ItemState) => Partial<ItemState>),
  ) =>
    setAnswers((prev) => {
      const base = prev[item.id] ?? restored(item);
      const next = typeof update === "function" ? update(base) : update;
      return { ...prev, [item.id]: { ...base, ...next } };
    });

  useEffect(() => {
    for (const item of quiz) markShown(shownAt.current, item.id);
  }, [quiz]);

  /**
   * Restore focus once a submission's disabling clears, the same house pattern as
   * ConceptPractice, ReteachConcept, DaysOffControl, DeadlineForm and DeleteCourseButton:
   * every path here that reaches this effect got here by disabling the control the
   * learner used to submit, which blurs it to the body, so the guard only has to ask
   * whether the learner is still there. A learner who tabbed away mid-request is where
   * they want to be, and pulling them back is worse than the problem being fixed.
   */
  useEffect(() => {
    for (const item of quiz) {
      const wanted = pendingFocus.current.get(item.id);
      if (!wanted) continue;
      pendingFocus.current.delete(item.id);
      if (document.activeElement !== document.body) continue;
      if (wanted === "correct") {
        correctRefs.current.get(item.id)?.focus();
        continue;
      }
      const answer = stateOf(item).answer;
      const target =
        item.kind === "mcq" ? mcqRefs.current.get(item.id)?.get(answer) : inputRefs.current.get(item.id);
      target?.focus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers, quiz]);

  // quiz_progress is the tally at load; items answered for the first time here move it.
  const newlyAnswered = quiz.filter(
    (item) =>
      item.attempt_state.attempts === 0 && (answers[item.id]?.attemptState.attempts ?? 0) > 0,
  ).length;
  const answeredCount = progress.answered + newlyAnswered;

  async function submit(item: QuizItem) {
    const { answer } = stateOf(item);
    if (!answer.trim()) {
      // Pressing "Check answer" again on a still-empty field re-sets the identical
      // literal; bumping errorNonce off the prior value (not a value closed over above)
      // is what forces the paragraph below to remount and re-announce.
      patch(item, (prev) => ({
        error: "Enter an answer first.",
        errorKind: "validation",
        errorNonce: prev.errorNonce + 1,
      }));
      return;
    }
    patch(item, { submitting: true, error: null, errorKind: null });
    try {
      const result = await answerQuiz(item.id, answer, elapsedSince(shownAt.current, item.id));
      // Time a retry from this attempt, not from the first time the item appeared.
      markShown(shownAt.current, item.id, true);
      // `ever_correct`, not `result.correct`: an item solved earlier that takes another
      // wrong attempt still unmounts its button, so it is solved-ness, not this
      // attempt's own verdict, that decides which control survives to land focus on.
      pendingFocus.current.set(item.id, result.attempt_state.ever_correct ? "correct" : "answer");
      patch(item, {
        feedback: { correct: result.correct, expected: result.expected },
        attemptState: result.attempt_state,
        submitting: false,
      });
    } catch (err) {
      patch(item, (prev) => ({
        error: err instanceof ApiError ? err.message : "Could not reach the server.",
        errorKind: "server",
        errorNonce: prev.errorNonce + 1,
        submitting: false,
      }));
    }
  }

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h2 className="text-subtitle">Check your understanding</h2>
        <p className="text-small tabular-nums text-ink-muted">
          {answeredCount} of {progress.items} answered
        </p>
      </div>

      <ol className="mt-4 flex flex-col gap-6">
        {quiz.map((item, index) => {
          const state = stateOf(item);
          // ever_correct spans every attempt, so an item solved earlier stays solved.
          const solved = state.attemptState.ever_correct;
          return (
            <li key={item.id}>
              {/*
                Card, not a hand-rolled border: this is the app's one card shape (see
                Card.tsx), the same primitive courses/page.tsx already nests inside its
                own <li>. `bg-surface` is new (the raw version had no fill, only the
                page's own background showing through); the two are the same colour, so
                nothing renders differently.
              */}
              <Card>
                <p id={`quiz-question-${item.id}`} className="text-ui font-medium">
                  <span className="mr-2 text-ink-subtle">{index + 1}.</span>
                  {item.question}
                </p>
                {item.concept && (
                  /*
                    text-small, not text-micro: "Concept: X" is a sentence-case caption
                    and text-micro is uppercase and tracked-out by convention (see
                    globals.css's type scale comment, and LessonMarkdown's heading
                    comment for the same reasoning applied to this same page).
                  */
                  <p className="mt-1 text-small text-ink-subtle">Concept: {item.concept}</p>
                )}

                {item.kind === "mcq" ? (
                  <div className="mt-3 flex flex-col gap-2">
                    {item.options.map((option) => (
                      <label
                        key={option}
                        className="flex cursor-pointer items-center gap-2 text-ui"
                      >
                        <input
                          type="radio"
                          name={`quiz-${item.id}`}
                          value={option}
                          checked={state.answer === option}
                          disabled={state.submitting || solved}
                          onChange={() =>
                            // A stale "Enter an answer first." no longer applies the
                            // moment an option is picked; a server error is left alone
                            // (see ErrorKind above) since picking an option doesn't undo
                            // the last request having failed.
                            patch(item, (prev) =>
                              prev.errorKind === "validation"
                                ? { answer: option, error: null, errorKind: null }
                                : { answer: option },
                            )
                          }
                          ref={(el) => {
                            // Only the checked option's node is worth keeping: it is the
                            // one the focus effect looks up by the current answer, and an
                            // unchecked sibling holding a stale entry would never be read.
                            const options = mcqRefs.current.get(item.id) ?? new Map();
                            if (state.answer === option) {
                              if (el) options.set(option, el);
                              else options.delete(option);
                              mcqRefs.current.set(item.id, options);
                            }
                          }}
                        />
                        {option}
                      </label>
                    ))}
                  </div>
                ) : (
                  <input
                    type="text"
                    value={state.answer}
                    disabled={state.submitting || solved}
                    onChange={(e) => {
                      const value = e.target.value;
                      // Same reasoning as the mcq onChange just above: a validation
                      // complaint about the answer goes stale the moment the answer
                      // changes, a server error does not.
                      patch(item, (prev) =>
                        prev.errorKind === "validation"
                          ? { answer: value, error: null, errorKind: null }
                          : { answer: value },
                      );
                    }}
                    ref={(el) => {
                      if (el) inputRefs.current.set(item.id, el);
                      else inputRefs.current.delete(item.id);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        void submit(item);
                      }
                    }}
                    placeholder="Your answer"
                    aria-labelledby={`quiz-question-${item.id}`}
                    /*
                      `border-line-strong`, which is the colour this input already had:
                      origin/main drew it in zinc-300 / zinc-700, and the bundle emits
                      --sf-line-strong as #d4d4d8 / #3f3f46, exactly those two. So this is
                      the pixel-identical migration, not a choice.

                      An earlier draft used `border-line` here, reasoning that it restated
                      ui/Field.tsx's recipe. It does restate it, token for token apart from
                      mt-3 against mt-1, but that is not an argument, because Field has no
                      consumers: `grep -rn "ui/Field\|<Field" src tests` returns nothing.
                      It is unadopted code, so it is not the app's recipe for anything. The
                      inputs that actually render (DaysOffControl and DeadlineForm's
                      FIELD_CLASS, ReviewSession:322) all use `border-line-strong`. Using
                      `border-line` would have dropped this one input alone to 1.27:1 light
                      and 1.33:1 dark, from 1.48 and 1.90. That is a different question
                      from whether line-strong itself clears WCAG 1.4.11's 3:1, which it
                      does not, and which is filed separately as one token change across
                      every form.

                      `aria-labelledby` rather than a wrapping <label>: the question above
                      IS this input's name, but sitting next to it does not make it one.
                      Until now the element had no labelling relationship at all and fell
                      back to its placeholder, which stops being readable the moment the
                      learner types. An earlier version of this comment defended that by
                      saying a second <label> would give the input "two accessible names";
                      an element has exactly one, and this one had none worth having.

                      No `outline-none` here, where the raw version had one: globals.css's
                      app-wide `:focus-visible` rule is unlayered, and Tailwind wraps its
                      own utilities in `@layer utilities`, so an unlayered rule always wins
                      over a layered one regardless of either side's specificity (same
                      reasoning, and the same removal, as ReviewSession's answer input).
                      Dropping it changes no rendered pixel. It does not stop the rule
                      shipping either, since six other components still use that utility;
                      it only stops THIS element carrying a class that could never win.
                    */
                    className="mt-3 w-full rounded-control border border-line-strong bg-transparent px-3 py-2 text-ui text-ink placeholder:text-ink-subtle transition-colors duration-fast ease-standard hover:border-line-hover focus:border-line-hover disabled:opacity-60"
                  />
                )}

                {/* role="alert" (implicitly assertive) rather than sitting inside the
                    polite region below, for two reasons. This is a response to something
                    the learner just did, so it should interrupt rather than queue behind
                    the result announcement; and the region below is documented as
                    carrying the RESULT, so folding a validation error into it would make
                    that comment false. Same shape as DeleteCourseButton's error. */}
                {state.error && (
                  <p
                    key={state.errorNonce}
                    role="alert"
                    className="mt-3 text-small text-danger"
                  >
                    {state.error}
                  </p>
                )}

                {/* aria-live so the result is announced regardless of where focus lands.
                    Focus does NOT stay on the submit button: checking an answer disables
                    the control that made the request, which blurs it to the body, and the
                    effect above returns focus deliberately, to the answer control while the
                    item is still open to a retry, or to the message below once solving it
                    has taken the button and left the inputs disabled. */}
                <div aria-live="polite">
                  {/* `solved` covers an item answered correctly at some point, including
                      from a source whose latest attempt was wrong (possible once review
                      sessions exist), so a solved item always reads as solved. */}
                  {solved && (
                    <p
                      ref={(el) => {
                        if (el) correctRefs.current.set(item.id, el);
                        else correctRefs.current.delete(item.id);
                      }}
                      tabIndex={-1}
                      /*
                        No `outline-none` here either, for the same reason as the text
                        input above, with one addition worth spelling out: this is exactly
                        the case globals.css's own comment on the app-wide focus rule
                        calls out by name, a `tabIndex={-1}` node that receives `.focus()`
                        after a mutation rather than a native focusable element, which is
                        why that rule is unscoped instead of targeting only
                        button/a/input. The ring still has to show up here, and it does,
                        for the same unlayered-beats-layered reason.
                      */
                      className="mt-3 rounded-control bg-success-surface px-3 py-2 text-small font-medium text-success"
                    >
                      Correct
                    </p>
                  )}

                  {state.feedback && !state.feedback.correct && (
                    <p className="mt-3 rounded-control bg-danger-surface px-3 py-2 text-small text-danger">
                      {solved
                        ? "Last answer was incorrect, expected: "
                        : "Incorrect, expected: "}
                      <span className="font-medium">{state.feedback.expected}</span>
                    </p>
                  )}
                </div>

                {!solved && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => void submit(item)}
                    disabled={state.submitting}
                    className="mt-3"
                  >
                    {state.submitting ? "Checking…" : state.feedback ? "Try again" : "Check answer"}
                  </Button>
                )}
              </Card>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
