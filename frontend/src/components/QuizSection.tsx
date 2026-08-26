"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, answerQuiz } from "@/lib/api";
import type { AttemptState, QuizItem, QuizProgress } from "@/lib/types";

interface Feedback {
  correct: boolean;
  expected: string;
}

interface ItemState {
  answer: string;
  feedback: Feedback | null;
  attemptState: AttemptState;
  submitting: boolean;
  error: string | null;
}

/** The item as the server last saw it, so a reload redraws the learner's last attempt. */
function restored(item: QuizItem): ItemState {
  const latest = item.attempt_state.latest_quiz_attempt;
  return {
    answer: latest?.answer ?? "",
    feedback: latest === null ? null : { correct: latest.correct, expected: latest.expected },
    attemptState: item.attempt_state,
    submitting: false,
    error: null,
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

  useEffect(() => {
    for (const item of quiz) markShown(shownAt.current, item.id);
  }, [quiz]);

  const stateOf = (item: QuizItem) => answers[item.id] ?? restored(item);
  const patch = (item: QuizItem, update: Partial<ItemState>) =>
    setAnswers((prev) => ({ ...prev, [item.id]: { ...(prev[item.id] ?? restored(item)), ...update } }));

  // quiz_progress is the tally at load; items answered for the first time here move it.
  const newlyAnswered = quiz.filter(
    (item) =>
      item.attempt_state.attempts === 0 && (answers[item.id]?.attemptState.attempts ?? 0) > 0,
  ).length;
  const answeredCount = progress.answered + newlyAnswered;

  async function submit(item: QuizItem) {
    const { answer } = stateOf(item);
    if (!answer.trim()) {
      patch(item, { error: "Enter an answer first." });
      return;
    }
    patch(item, { submitting: true, error: null });
    try {
      const result = await answerQuiz(item.id, answer, elapsedSince(shownAt.current, item.id));
      // Time a retry from this attempt, not from the first time the item appeared.
      markShown(shownAt.current, item.id, true);
      patch(item, {
        feedback: { correct: result.correct, expected: result.expected },
        attemptState: result.attempt_state,
        submitting: false,
      });
    } catch (err) {
      patch(item, {
        error: err instanceof ApiError ? err.message : "Could not reach the server.",
        submitting: false,
      });
    }
  }

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-semibold">Check your understanding</h2>
        <p className="text-sm tabular-nums text-zinc-600 dark:text-zinc-400">
          {answeredCount} of {progress.items} answered
        </p>
      </div>

      <ol className="mt-4 flex flex-col gap-6">
        {quiz.map((item, index) => {
          const state = stateOf(item);
          // ever_correct spans every attempt, so an item solved earlier stays solved.
          const solved = state.attemptState.ever_correct;
          return (
            <li
              key={item.id}
              className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800"
            >
              <p className="font-medium">
                <span className="mr-2 text-zinc-500 dark:text-zinc-400">{index + 1}.</span>
                {item.question}
              </p>
              {item.concept && (
                <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                  Concept: {item.concept}
                </p>
              )}

              {item.kind === "mcq" ? (
                <div className="mt-3 flex flex-col gap-2">
                  {item.options.map((option) => (
                    <label
                      key={option}
                      className="flex cursor-pointer items-center gap-2 text-sm"
                    >
                      <input
                        type="radio"
                        name={`quiz-${item.id}`}
                        value={option}
                        checked={state.answer === option}
                        disabled={state.submitting || solved}
                        onChange={() => patch(item, { answer: option })}
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
                  onChange={(e) => patch(item, { answer: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void submit(item);
                    }
                  }}
                  placeholder="Your answer"
                  className="mt-3 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-500 disabled:opacity-60 dark:border-zinc-700"
                />
              )}

              {state.error && (
                <p className="mt-3 text-sm text-red-700 dark:text-red-400">{state.error}</p>
              )}

              {/* aria-live so the result is announced: focus stays on the submit
                  button while the feedback renders elsewhere in the DOM. */}
              <div aria-live="polite">
                {/* `solved` covers an item answered correctly at some point, including
                    from a source whose latest attempt was wrong (possible once review
                    sessions exist), so a solved item always reads as solved. */}
                {solved && (
                  <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                    Correct
                  </p>
                )}

                {state.feedback && !state.feedback.correct && (
                  <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-300">
                    {solved ? "Last answer was incorrect, expected: " : "Incorrect, expected: "}
                    <span className="font-medium">{state.feedback.expected}</span>
                  </p>
                )}
              </div>

              {!solved && (
                <button
                  type="button"
                  onClick={() => void submit(item)}
                  disabled={state.submitting}
                  className="mt-3 rounded-lg border border-zinc-300 px-4 py-1.5 text-sm font-medium transition-colors hover:border-zinc-500 disabled:opacity-60 dark:border-zinc-700 dark:hover:border-zinc-500"
                >
                  {state.submitting ? "Checking…" : state.feedback ? "Try again" : "Check answer"}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
