"use client";

import { useState } from "react";

import { ApiError, answerQuiz } from "@/lib/api";
import type { AnswerResult, QuizItem } from "@/lib/types";

interface ItemState {
  answer: string;
  result: AnswerResult | null;
  submitting: boolean;
  error: string | null;
}

const EMPTY: ItemState = { answer: "", result: null, submitting: false, error: null };

export function QuizSection({ quiz }: { quiz: QuizItem[] }) {
  const [states, setStates] = useState<Record<number, ItemState>>({});

  const stateOf = (id: number) => states[id] ?? EMPTY;
  const patch = (id: number, update: Partial<ItemState>) =>
    setStates((prev) => ({ ...prev, [id]: { ...(prev[id] ?? EMPTY), ...update } }));

  const answeredCount = quiz.filter((item) => stateOf(item.id).result !== null).length;

  async function submit(item: QuizItem) {
    const { answer } = stateOf(item.id);
    if (!answer.trim()) {
      patch(item.id, { error: "Enter an answer first." });
      return;
    }
    patch(item.id, { submitting: true, error: null });
    try {
      const result = await answerQuiz(item.id, answer);
      patch(item.id, { result, submitting: false });
    } catch (err) {
      patch(item.id, {
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
          {answeredCount} of {quiz.length} answered
        </p>
      </div>

      <ol className="mt-4 flex flex-col gap-6">
        {quiz.map((item, index) => {
          const state = stateOf(item.id);
          const wrong = state.result !== null && !state.result.correct;
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
                        disabled={state.submitting || state.result?.correct === true}
                        onChange={() => patch(item.id, { answer: option })}
                      />
                      {option}
                    </label>
                  ))}
                </div>
              ) : (
                <input
                  type="text"
                  value={state.answer}
                  disabled={state.submitting || state.result?.correct === true}
                  onChange={(e) => patch(item.id, { answer: e.target.value })}
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

              {state.result?.correct ? (
                <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                  Correct
                </p>
              ) : (
                <>
                  {wrong && state.result && (
                    <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-300">
                      Incorrect, expected: <span className="font-medium">{state.result.expected}</span>
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={() => void submit(item)}
                    disabled={state.submitting}
                    className="mt-3 rounded-lg border border-zinc-300 px-4 py-1.5 text-sm font-medium transition-colors hover:border-zinc-500 disabled:opacity-60 dark:border-zinc-700 dark:hover:border-zinc-500"
                  >
                    {state.submitting ? "Checking…" : wrong ? "Try again" : "Check answer"}
                  </button>
                </>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
