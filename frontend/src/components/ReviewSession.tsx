"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ApiError, answerReviewCard, rateReviewCard } from "@/lib/api";
import type { RatingName, RatingPreview, ReviewCard, ReviewQueue } from "@/lib/types";

/** The four buttons, in rating order, with the colour each carries in the design. */
const RATING_STYLES: Record<RatingName, { title: string; className: string }> = {
  again: { title: "Again", className: "text-red-700 dark:text-red-400" },
  hard: { title: "Hard", className: "text-amber-700 dark:text-amber-500" },
  good: { title: "Good", className: "" },
  easy: { title: "Easy", className: "text-emerald-700 dark:text-emerald-500" },
};

/**
 * What the learner has done with the current card.
 *
 * "rating" is reached either by answering or by a 409, which means this item was
 * already answered earlier in the same exposure. In that case there is no reference
 * answer to show and no attempt to attribute the rating to, but the card is still
 * due and still needs rating, so the buttons stay.
 */
type Phase =
  | { kind: "answering" }
  | {
      kind: "rating";
      submitted: string | null;
      expected: string | null;
      suggested: number | null;
      attemptIds: number[];
      preview: RatingPreview[];
      alreadyAnswered: boolean;
    };

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Could not reach the server.";
}

export function ReviewSession({ queue }: { queue: ReviewQueue }) {
  /**
   * The session runs over this snapshot and never refetches. Every answer and every
   * rating is its own durable POST, so ending mid-session and coming back simply
   * pulls a fresh queue of whatever is still due. There is no session to resume.
   *
   * A card whose concept no longer has any quiz item cannot be asked, so it is
   * dropped here rather than rendered as an empty card.
   */
  const [cards] = useState<ReviewCard[]>(() => queue.cards.filter((card) => card.item !== null));
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>({ kind: "answering" });
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const card = cards[index];
  const item = card?.item ?? null;
  const finished = index >= cards.length;

  /** When the current question rendered, for the elapsed_ms timing signal. */
  const shownAt = useRef<number>(0);
  const ratingRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    shownAt.current = Date.now();
  }, [index]);

  // Put the keyboard on the suggested rating as soon as the buttons appear, so the
  // common case is one keystroke and an override is an arrow key away.
  useEffect(() => {
    if (phase.kind === "rating") ratingRef.current?.focus();
  }, [phase.kind, index]);

  function advance() {
    setPhase({ kind: "answering" });
    setAnswer("");
    setError(null);
    setIndex((prev) => prev + 1);
  }

  async function submitAnswer() {
    if (!card || !item || busy) return;
    if (!answer.trim()) {
      setError("Enter an answer first.");
      return;
    }
    const elapsed = Date.now() - shownAt.current;
    setBusy(true);
    setError(null);
    try {
      const result = await answerReviewCard(
        card.card_id,
        item.id,
        answer,
        Number.isFinite(elapsed) && elapsed >= 0 ? elapsed : undefined,
      );
      setPhase({
        kind: "rating",
        submitted: result.submitted,
        expected: result.expected,
        suggested: result.suggested_rating,
        attemptIds: [result.attempt_id],
        // The answer response recomputes the preview at submit time, so prefer it
        // over the one the queue was rendered with.
        preview: result.preview,
        alreadyAnswered: false,
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setPhase({
          kind: "rating",
          submitted: answer,
          expected: null,
          suggested: null,
          attemptIds: [],
          preview: card.preview,
          alreadyAnswered: true,
        });
      } else {
        setError(errorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  }

  async function rate(rating: number) {
    if (!card || busy || phase.kind !== "rating") return;
    setBusy(true);
    setError(null);
    try {
      await rateReviewCard(card.card_id, rating, phase.suggested, phase.attemptIds);
      advance();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const total = cards.length;
  const position = Math.min(index + 1, total);
  const done = finished ? total : index;
  const percent = total === 0 ? 0 : Math.round((done / total) * 100);

  // The queue limit trims what is handed to the client but reschedules nothing, and
  // a card with no question left cannot be asked. Both are said out loud rather than
  // quietly folded into a smaller number.
  const notes: string[] = [];
  if (queue.due_total > queue.cards.length) {
    notes.push(`${queue.due_total} due, showing ${queue.cards.length}`);
  }
  const skipped = queue.cards.length - total;
  if (skipped > 0) {
    notes.push(
      `${skipped} skipped: ${skipped === 1 ? "its concept has" : "their concepts have"} no quiz question left`,
    );
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <div className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-5 px-6 py-3">
          <Link
            href="/"
            className="text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
          >
            End session
          </Link>
          <div
            role="progressbar"
            aria-label="Review session progress"
            aria-valuemin={0}
            aria-valuemax={total}
            aria-valuenow={done}
            aria-valuetext={`${done} of ${total} cards reviewed`}
            className="h-1 max-w-[420px] flex-1 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800"
          >
            <div
              className="h-full bg-zinc-900 transition-[width] dark:bg-zinc-100"
              style={{ width: `${percent}%` }}
            />
          </div>
          <span className="whitespace-nowrap font-mono text-[13px] tabular-nums text-zinc-500 dark:text-zinc-400">
            {total === 0 ? "0 / 0" : `${position} / ${total}`}
          </span>
        </div>
      </div>

      {notes.length > 0 && (
        <p className="mx-auto w-full max-w-4xl px-6 pt-3 text-[13px] text-zinc-500 dark:text-zinc-400">
          {notes.join(" · ")}
        </p>
      )}

      <div className="mx-auto w-full max-w-[720px] flex-1 px-6 py-14">
        {total === 0 && (
          <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center dark:border-zinc-800 dark:bg-zinc-900">
            <p className="text-lg font-medium">Nothing to review right now</p>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
              Concepts come back as their recall probability drops. Finish a lesson to put new
              ones into the schedule.
            </p>
            <Link
              href="/"
              className="mt-6 inline-block rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              Back to Today
            </Link>
          </div>
        )}

        {total > 0 && finished && (
          <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center dark:border-zinc-800 dark:bg-zinc-900">
            <p className="text-lg font-medium">Session complete</p>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
              {total} {total === 1 ? "concept" : "concepts"} reviewed and rescheduled.
              {queue.due_total > queue.cards.length &&
                ` ${queue.due_total - queue.cards.length} more are still due: start another session when you are ready.`}
            </p>
            <Link
              href="/"
              className="mt-6 inline-block rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              Back to Today
            </Link>
          </div>
        )}

        {card && item && !finished && (
          <>
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-zinc-500 dark:text-zinc-400">
                Concept
              </span>
              <span className="text-[13px] text-zinc-700 dark:text-zinc-300">
                {card.concept_label}
              </span>
              {card.lapses > 0 && (
                <span className="rounded-full bg-amber-100 px-2.5 py-[3px] text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                  Missed last time
                </span>
              )}
            </div>

            <div className="mt-3.5 rounded-lg border border-zinc-200 bg-white p-8 dark:border-zinc-800 dark:bg-zinc-900">
              <p className="text-xl font-medium leading-[1.45]">{item.question}</p>

              {phase.kind === "answering" ? (
                <div className="mt-6">
                  {item.kind === "mcq" ? (
                    <fieldset className="flex flex-col gap-2">
                      <legend className="sr-only">Choose an answer</legend>
                      {item.options.map((option) => (
                        <label key={option} className="flex cursor-pointer items-center gap-2 text-sm">
                          <input
                            type="radio"
                            name={`review-${card.card_id}`}
                            value={option}
                            checked={answer === option}
                            disabled={busy}
                            onChange={() => setAnswer(option)}
                          />
                          {option}
                        </label>
                      ))}
                    </fieldset>
                  ) : (
                    <>
                      <label htmlFor={`answer-${card.card_id}`} className="sr-only">
                        Your answer
                      </label>
                      <input
                        id={`answer-${card.card_id}`}
                        type="text"
                        autoFocus
                        value={answer}
                        disabled={busy}
                        onChange={(e) => setAnswer(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            void submitAnswer();
                          }
                        }}
                        placeholder="Your answer"
                        className="w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-500 disabled:opacity-60 dark:border-zinc-700"
                      />
                    </>
                  )}

                  <button
                    type="button"
                    onClick={() => void submitAnswer()}
                    disabled={busy}
                    className="mt-4 rounded-lg bg-zinc-900 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
                  >
                    {busy ? "Checking…" : "Show answer"}
                  </button>
                </div>
              ) : (
                // Announced, because focus moves to the rating buttons while the
                // reference answer renders above them.
                <div aria-live="polite">
                  {phase.alreadyAnswered ? (
                    <div className="mt-6 border-t border-zinc-100 pt-5 dark:border-zinc-800">
                      <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                        You already answered this question earlier in this review, so it was not
                        recorded again. Rate how well you recalled it and the card will be
                        rescheduled.
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="mt-6 border-t border-zinc-100 pt-5 dark:border-zinc-800">
                        <p className="mb-2.5 font-mono text-xs uppercase tracking-[0.06em] text-zinc-500 dark:text-zinc-400">
                          Your answer
                        </p>
                        <p className="text-[15px] leading-relaxed text-zinc-800 dark:text-zinc-200">
                          {phase.submitted}
                        </p>
                      </div>
                      <div className="mt-5 border-t border-zinc-100 pt-5 dark:border-zinc-800">
                        <p className="mb-2.5 font-mono text-xs uppercase tracking-[0.06em] text-zinc-500 dark:text-zinc-400">
                          Reference answer
                        </p>
                        <p className="text-[15px] leading-relaxed text-zinc-600 dark:text-zinc-400">
                          {phase.expected}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            {error && (
              <p
                role="alert"
                className="mt-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
              >
                {error}
              </p>
            )}

            {phase.kind === "rating" && (
              <>
                <p className="mb-3 mt-6 text-center text-[13px] text-zinc-500 dark:text-zinc-400">
                  How well did you recall it?
                </p>
                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                  {phase.preview.map((option) => {
                    const style = RATING_STYLES[option.name];
                    const suggested = option.rating === phase.suggested;
                    return (
                      <button
                        key={option.rating}
                        type="button"
                        ref={suggested ? ratingRef : undefined}
                        disabled={busy}
                        onClick={() => void rate(option.rating)}
                        aria-label={`${style.title}, next review in ${option.label}${
                          suggested ? ", suggested" : ""
                        }`}
                        className={`rounded-lg bg-white text-center transition-colors disabled:opacity-60 dark:bg-zinc-900 ${
                          suggested
                            ? "border-2 border-zinc-900 px-2.5 py-[13px] dark:border-zinc-100"
                            : "border border-zinc-200 px-2.5 py-3.5 hover:border-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-600"
                        }`}
                      >
                        <span className={`block text-sm font-semibold ${style.className}`}>
                          {style.title}
                        </span>
                        {/* Rendered verbatim: the server computes it from the real
                            scheduler transition with fuzzing off, so two buttons
                            showing the same label are both telling the truth. */}
                        <span
                          aria-hidden
                          className="mt-1 block font-mono text-[11px] text-zinc-500 dark:text-zinc-400"
                        >
                          {option.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
                <p className="mt-4.5 text-center text-xs leading-relaxed text-zinc-400 dark:text-zinc-500">
                  Intervals come from FSRS using your own history on this concept, and bunch
                  closer together than you might expect.
                  <br />
                  Rate honestly: a generous rating today costs you a forgotten concept later.
                </p>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
