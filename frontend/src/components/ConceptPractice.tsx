"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, getPractice, submitPractice } from "@/lib/api";
import { formatDay, noLongerMissed } from "@/lib/copy";
import type { PracticeConflict, PracticeResult, PracticeState } from "@/lib/types";

/** A run that still has a question to ask. */
type ActiveRun = Extract<PracticeState, { status: "ready" | "in_progress" }>;
/** A run that has none, whether it finished or never started. */
type TerminalRun = Extract<PracticeState, { status: "done" | "unavailable" }>;

/** The answer just graded, held until the learner asks for the next question. */
interface Feedback {
  question: string;
  submitted: string;
  expected: string;
  correct: boolean;
  kind: "mcq" | "short";
}

/** Where focus belongs once a response has landed and the DOM has caught up. */
type FocusTarget = "answer" | "next" | "terminal" | "submit";

/**
 * What practising cannot do, said out loud.
 *
 * The one thing a learner might reasonably assume from getting questions right here is
 * that they have moved the needle, and they have not: this writes an attempt row and
 * nothing else. No review log, no rescheduling, no mastery bucket, no attention flag,
 * no retention figure. Saying so is not a disclaimer bolted on afterwards, it is the
 * feature's actual promise, and the learner is entitled to it before they draw a
 * conclusion from two right answers.
 */
const SCHEDULE_NOTE =
  "Practising here changes nothing about your schedule. This concept comes back on " +
  "its usual date, and how you do then is what counts.";

function errorMessage(err: unknown): string {
  return err instanceof ApiError
    ? err.message
    : "Could not reach the server. Is the backend running?";
}

/**
 * The headline and the explanation for a run that is over, per reason.
 *
 * Switched inside each status rather than across the pair, because the server
 * partitions the two reason vocabularies and the union carries that partition: a
 * `done` run cannot be `no_items` and an `unavailable` one cannot be `target_reached`.
 * "You finished" and "there was nothing here" are different sentences, and a component
 * that conflated them would congratulate a learner on a run that never happened.
 */
function terminalCopy(run: TerminalRun, conceptLabel: string): { headline: string; body: string } {
  if (run.status === "done") {
    switch (run.reason) {
      case "target_reached":
        return {
          headline: "That is this concept done for today",
          body: `You reached ${run.target_correct} right answers, which is what this run was after.`,
        };
      case "attempts_spent":
        return {
          headline: `That is today's ${run.max_answers} questions`,
          body: "A short run is the whole idea, so this stops rather than turning into a drill.",
        };
      case "pool_exhausted":
        return {
          headline: "That is every question this concept has",
          body: "You have answered all of them, so there is nothing left to ask today.",
        };
    }
  }
  switch (run.reason) {
    case "no_note":
      // Good news, and it reads as good news. The note underneath this panel was
      // retired because the concept stopped being one the learner keeps missing, which
      // is something their own reviews did, so it is attributed to them and never
      // phrased as something taken away. Same clause the re-teach button uses for
      // not_flagged: one fact, one wording, however the learner arrived at it.
      return {
        headline: "You are past this one",
        body: `Your recent reviews cleared this up, so ${noLongerMissed(conceptLabel)}.`,
      };
    case "no_items":
      return {
        headline: "No questions to practise with",
        body:
          "This concept has no quiz questions yet, so there is nothing to ask. The " +
          "explanation above is still yours to re-read.",
      };
  }
}

/** One answered question, as the terminal panel lists it. */
function ResultRow({ result }: { result: PracticeResult }) {
  return (
    <li className="border-t border-amber-200/70 pt-2.5 first:border-t-0 first:pt-0 dark:border-amber-900/70">
      {/* Blank when the item has since been regenerated away. The attempt outlives the
          question it was asked from, and dropping the row would lose an answer the
          learner actually gave. */}
      <p className="text-[13px] text-zinc-700 dark:text-zinc-300">
        {result.question || "This question is no longer in the course."}
      </p>
      <p className="mt-1 text-[13px] text-zinc-600 dark:text-zinc-400">
        <span className="text-zinc-500 dark:text-zinc-500">You wrote: </span>
        {result.submitted}
        {result.correct ? (
          <span className="ml-2 text-emerald-700 dark:text-emerald-500">Right</span>
        ) : (
          <>
            <span className="text-zinc-500 dark:text-zinc-500"> · Reference answer: </span>
            {result.expected}
          </>
        )}
      </p>
    </li>
  );
}

/**
 * A bounded run at one concept the learner keeps missing, after they have read the
 * explanation of it.
 *
 * Mounted inside the note panel and nowhere else, which is the precondition made
 * structural: practice is only reachable when an explanation exists AND is open in
 * front of the learner, so "explanation before practice" cannot be broken by a layout
 * change. Nothing on the review route mounts this, which is what keeps practice out of
 * a review session.
 *
 * It is a study event, not an assessment. The only row it writes is an attempt under
 * its own source; the schedule, the mastery buckets, the attention flag and the
 * retention figure are all untouched, and the copy says so rather than leaving the
 * learner to infer it.
 */
export function ConceptPractice({
  cardId,
  conceptLabel,
  open,
  onAnnounce,
}: {
  cardId: number;
  conceptLabel: string;
  /**
   * Whether the note panel around this is open. The fetch waits for the first true.
   *
   * Today's mount site only renders this subtree while the panel is open, so this
   * arrives already true and the fetch fires on mount. It is a prop anyway because the
   * laziness belongs to this component rather than to where it happens to be rendered:
   * moving the mount outside that conditional, to keep run state across a close and
   * reopen, would otherwise silently turn the panel into a second per-concept request
   * on every Today load.
   */
  open: boolean;
  /**
   * Routed into the live region ReteachConcept already mounts empty. This component
   * deliberately mounts no second one: the row would then have two regions announcing
   * about the same concept, and a screen reader would read whichever won the race.
   */
  onAnnounce: (message: string) => void;
}) {
  const [run, setRun] = useState<PracticeState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [busy, setBusy] = useState(false);

  // The fetch is lazy and fires once. Today already runs one getRemediation per
  // flagged concept and that fan-out is the slowest thing on the screen; this panel is
  // closed by default and most learners will never open it, so it must not join it.
  const requested = useRef(false);
  /**
   * Where focus should land once React has committed the tree the last response
   * produced. A ref and not state, so the effect below reads it without a second
   * render to clear it; same shape as ReteachConcept's `wantsFocus`.
   */
  const pendingFocus = useRef<FocusTarget | null>(null);
  const answerRef = useRef<HTMLInputElement>(null);
  const nextRef = useRef<HTMLButtonElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const terminalRef = useRef<HTMLDivElement>(null);
  /** When the current question rendered, for the elapsed_ms timing signal. */
  const shownAt = useRef(0);

  const baseId = `practice-${cardId}`;
  const currentItemId = run?.item?.id ?? null;

  function load() {
    setLoading(true);
    setError(null);
    getPractice(cardId)
      .then(setRun)
      .catch((err) => {
        const message = errorMessage(err);
        setError(message);
        onAnnounce(message);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!open || requested.current) return;
    requested.current = true;
    load();
    // `load` closes over cardId and onAnnounce, both stable for this row's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, cardId]);

  useEffect(() => {
    shownAt.current = Date.now();
  }, [currentItemId]);

  /**
   * Focus, once the response has landed and React has committed the new tree.
   *
   * Every path through here ends with the control the learner was using gone: the
   * submit button is a real `disabled` while a request is in flight, and disabling the
   * focused element blurs it to the body. That is the same focus loss ReteachConcept's
   * recovered branch handles, so it is handled the same way rather than reinvented, and
   * whatever replaced the control takes the focus deliberately.
   */
  useEffect(() => {
    const wanted = pendingFocus.current;
    if (!wanted) return;
    pendingFocus.current = null;
    if (wanted === "submit") {
      // Only when the blur left focus nowhere. A learner who moved on during the
      // request is where they want to be, and yanking them back is worse than the
      // problem being fixed.
      if (document.activeElement === document.body) submitRef.current?.focus();
      return;
    }
    const target =
      wanted === "next"
        ? nextRef.current
        : wanted === "terminal"
          ? terminalRef.current
          : answerRef.current;
    target?.focus();
    // The three pieces of state a response can move. Whichever of them changed, the
    // tree carrying the new control is on screen by the time this runs.
  }, [run, feedback, busy]);

  /** Take the run the server just described and land the learner in the right place. */
  function adopt(next: PracticeState) {
    setRun(next);
    if (next.status === "done" || next.status === "unavailable") {
      // The terminal state REPLACES the question. There is no dismissing it and no
      // practising anyway, so the only thing left to do with it is read it.
      pendingFocus.current = "terminal";
    } else {
      pendingFocus.current = "next";
    }
  }

  async function submit() {
    if (busy || !run || run.item === null) return;
    const item = run.item;
    if (!answer.trim()) {
      setError("Enter an answer first.");
      return;
    }
    const elapsed = Date.now() - shownAt.current;
    setBusy(true);
    setError(null);
    try {
      const outcome = await submitPractice(
        cardId,
        item.id,
        answer,
        Number.isFinite(elapsed) && elapsed >= 0 ? elapsed : undefined,
      );

      if (outcome.kind === "answer") {
        const result = outcome.answer;
        setAnswer("");
        // Announced because focus is about to move to a control that does not carry
        // the grading result, and the result is the point of having answered.
        //
        // Both branches carry something that changes between answers, the tally or the
        // reference answer, and that is load-bearing rather than decorative: a live
        // region whose text is byte-identical to what it already held does not
        // re-announce, so a bare "Correct." twice running would be read once.
        onAnnounce(
          result.correct
            ? `Correct. That is ${result.state.correct} of ${result.state.target_correct} right.`
            : `Not an exact match. The reference answer is: ${result.expected}`,
        );
        // Read from state.status, never from the 200 itself. A note retired underneath
        // this panel ends the run on a SUCCESSFUL response: the answer already in the
        // learner's hands is still graded and kept, and the terminal state arrives on
        // the response that carries it.
        const ended = result.state.status === "done" || result.state.status === "unavailable";
        setFeedback(
          ended
            ? null
            : {
                question: item.question,
                submitted: result.submitted,
                expected: result.expected,
                correct: result.correct,
                kind: item.kind,
              },
        );
        adopt(result.state);
        return;
      }

      const conflict: PracticeConflict = outcome.conflict;
      // Read before the switch narrows `conflict` away, for the unreachable default.
      const serverMessage = conflict.message;
      setFeedback(null);
      // Switched on the code, exhaustively, and never on the shape of the state that
      // came with it. Its own union and its own switch: RemediationConflict is switched
      // exhaustively one component up, and folding these codes into that one would
      // leave it handling codes its endpoint can never send, which turns a real
      // guarantee into a formality.
      switch (conflict.error) {
        case "item_already_answered":
          // Reachable from a second tab, or a click that landed twice. The run itself
          // is fine and cannot be terminal here, because a run with nothing left to
          // serve is a finished one and answers `session_complete` instead. The next
          // question is therefore already in the state below, and this only explains
          // the jump to it.
          onAnnounce("You already answered that one today. Here is the next question.");
          break;
        case "session_complete":
        case "no_note":
        case "no_items":
          // All three arrive with a terminal state, and `adopt` moves focus onto the
          // panel that spells it out. Announcing here as well would put the same news
          // in two places a screen reader reads, which is the bug this row has shipped
          // before.
          break;
        default: {
          // Unreachable while the union is exhaustive, and that is the point: a fifth
          // code becomes a compile error here rather than silently landing on whichever
          // branch happened to be last. The runtime arm still matters, because the
          // server can ship a new code before this file knows about it, and every one
          // of them carries a human message worth showing.
          const unhandled: never = conflict;
          void unhandled;
          setError(serverMessage);
          onAnnounce(serverMessage);
        }
      }
      adopt(conflict.state);
    } catch (err) {
      const message = errorMessage(err);
      setError(message);
      onAnnounce(message);
      pendingFocus.current = "submit";
    } finally {
      setBusy(false);
    }
  }

  function showNextQuestion() {
    setFeedback(null);
    pendingFocus.current = "answer";
  }

  if (!open) return null;

  return (
    <section
      aria-labelledby={`${baseId}-heading`}
      className="mt-4 border-t border-amber-200 pt-4 dark:border-amber-900"
    >
      {loading && !run && (
        <p className="text-[13px] text-amber-900/70 dark:text-amber-200/70">
          Loading today&rsquo;s practice…
        </p>
      )}

      {error && !run && (
        <div>
          <p className="text-[13px] text-red-800 dark:text-red-300">{error}</p>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="mt-2 rounded-lg border border-amber-300 px-3 py-1 text-[13px] font-medium text-amber-900 transition-colors hover:border-amber-500 disabled:opacity-60 dark:border-amber-800 dark:text-amber-200 dark:hover:border-amber-600"
          >
            Try again
          </button>
        </div>
      )}

      {run !== null && (run.status === "ready" || run.status === "in_progress") && (
        <ActivePanel
          run={run}
          baseId={baseId}
          answer={answer}
          setAnswer={setAnswer}
          feedback={feedback}
          busy={busy}
          error={error}
          onSubmit={() => void submit()}
          onNext={showNextQuestion}
          answerRef={answerRef}
          nextRef={nextRef}
          submitRef={submitRef}
        />
      )}

      {run !== null && (run.status === "done" || run.status === "unavailable") && (
        <TerminalPanel run={run} baseId={baseId} conceptLabel={conceptLabel} panelRef={terminalRef} />
      )}
    </section>
  );
}

/** The question, or the answer just graded. Never both: one thing to do at a time. */
function ActivePanel({
  run,
  baseId,
  answer,
  setAnswer,
  feedback,
  busy,
  error,
  onSubmit,
  onNext,
  answerRef,
  nextRef,
  submitRef,
}: {
  run: ActiveRun;
  baseId: string;
  answer: string;
  setAnswer: (value: string) => void;
  feedback: Feedback | null;
  busy: boolean;
  error: string | null;
  onSubmit: () => void;
  onNext: () => void;
  answerRef: React.RefObject<HTMLInputElement | null>;
  nextRef: React.RefObject<HTMLButtonElement | null>;
  submitRef: React.RefObject<HTMLButtonElement | null>;
}) {
  const item = run.item;
  // Two members of the union rather than one, because the copy genuinely differs.
  // Deriving this from `answered > 0` would be exactly the shape test the union exists
  // to forbid, and it would be one refactor away from being wrong.
  const heading = run.status === "ready" ? "Practise this" : "Continue";
  const lede =
    run.status === "ready"
      ? `Get ${run.target_correct} right and this is done. You have at most ${run.max_answers} questions.`
      : `${run.answered} of ${run.max_answers} answers used, ${run.correct} of ${run.target_correct} right so far.`;

  return (
    <>
      <h4 id={`${baseId}-heading`} className="text-[14px] font-semibold">
        {heading}
      </h4>
      <p className="mt-0.5 text-[13px] text-amber-900/80 dark:text-amber-200/80">{lede}</p>

      {feedback ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-white/70 px-4 py-3 dark:border-amber-900 dark:bg-zinc-900/40">
          <p className="text-[13px] text-zinc-700 dark:text-zinc-300">{feedback.question}</p>
          <p className="mt-2 text-[13px] font-medium">
            {feedback.correct ? (
              <span className="text-emerald-700 dark:text-emerald-500">Correct</span>
            ) : feedback.kind === "short" ? (
              /* Not "wrong". The grader is an exact, case-insensitive string comparison,
                 so a learner who understands the concept and words it differently lands
                 here, and unlike a review session there is no rating button to overrule
                 it. Calling that wrong would be the component asserting something it
                 does not know. */
              <span className="text-amber-800 dark:text-amber-400">Not an exact match</span>
            ) : (
              <span className="text-amber-800 dark:text-amber-400">Not the right option</span>
            )}
          </p>
          <p className="mt-1.5 text-[13px] text-zinc-600 dark:text-zinc-400">
            <span className="text-zinc-500 dark:text-zinc-500">You wrote: </span>
            {feedback.submitted}
          </p>
          {!feedback.correct && (
            <>
              <p className="mt-1 text-[13px] text-zinc-600 dark:text-zinc-400">
                <span className="text-zinc-500 dark:text-zinc-500">Reference answer: </span>
                {feedback.expected}
              </p>
              {feedback.kind === "short" && (
                <p className="mt-2 text-[12px] text-zinc-500 dark:text-zinc-500">
                  Answers here are compared word for word, so a different wording can miss
                  even when you have the idea.
                </p>
              )}
            </>
          )}
          <button
            type="button"
            ref={nextRef}
            onClick={onNext}
            className="mt-3 rounded-lg border border-amber-300 px-3.5 py-1.5 text-[13px] font-medium text-amber-900 transition-colors hover:border-amber-500 dark:border-amber-800 dark:text-amber-200 dark:hover:border-amber-600"
          >
            Next question
          </button>
        </div>
      ) : (
        <div className="mt-3 rounded-lg border border-amber-200 bg-white/70 px-4 py-3 dark:border-amber-900 dark:bg-zinc-900/40">
          <p className="text-[14px] font-medium leading-[1.45]">{item.question}</p>

          {/* Neither the input nor the radios are ever disabled, even mid-request.
              Disabling the focused control blurs it to the body, and a second submit is
              already refused in the handler and again by the server. */}
          <div className="mt-3">
            {item.kind === "mcq" ? (
              <fieldset className="flex flex-col gap-1.5">
                <legend className="sr-only">Choose an answer</legend>
                {item.options.map((option) => (
                  <label key={option} className="flex cursor-pointer items-center gap-2 text-[13px]">
                    <input
                      type="radio"
                      name={`${baseId}-answer`}
                      value={option}
                      checked={answer === option}
                      onChange={() => setAnswer(option)}
                    />
                    {option}
                  </label>
                ))}
              </fieldset>
            ) : (
              <>
                <label htmlFor={`${baseId}-answer-input`} className="sr-only">
                  Your answer
                </label>
                <input
                  id={`${baseId}-answer-input`}
                  ref={answerRef}
                  type="text"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      onSubmit();
                    }
                  }}
                  placeholder="Your answer"
                  className="w-full rounded-lg border border-amber-300 bg-transparent px-3 py-1.5 text-[13px] outline-none focus:border-amber-500 dark:border-amber-800"
                />
              </>
            )}
          </div>

          {error && <p className="mt-2 text-[13px] text-red-800 dark:text-red-300">{error}</p>}

          <button
            type="button"
            ref={submitRef}
            onClick={onSubmit}
            disabled={busy}
            className="mt-3 rounded-lg bg-amber-800 px-4 py-1.5 text-[13px] font-medium text-white transition-colors hover:bg-amber-700 disabled:opacity-60 dark:bg-amber-200 dark:text-amber-950 dark:hover:bg-amber-100"
          >
            {busy ? "Checking…" : "Check answer"}
          </button>
        </div>
      )}

      <p className="mt-3 text-[12px] text-amber-900/70 dark:text-amber-200/70">{SCHEDULE_NOTE}</p>
    </>
  );
}

/**
 * A run that is over. This REPLACES the question rather than sitting beside it: there
 * is no dismissing it and no practising anyway, because the bound is the pedagogy and
 * an escape hatch would quietly remove it.
 */
function TerminalPanel({
  run,
  baseId,
  conceptLabel,
  panelRef,
}: {
  run: TerminalRun;
  baseId: string;
  conceptLabel: string;
  panelRef: React.RefObject<HTMLDivElement | null>;
}) {
  const { headline, body } = terminalCopy(run, conceptLabel);

  return (
    <div
      ref={panelRef}
      tabIndex={-1}
      className="rounded-lg border border-amber-200 bg-white/70 px-4 py-3.5 outline-none focus-visible:ring-2 focus-visible:ring-amber-500 dark:border-amber-900 dark:bg-zinc-900/40"
    >
      <h4 id={`${baseId}-heading`} className="text-[14px] font-semibold">
        {headline}
      </h4>
      <p className="mt-1 text-[13px] text-zinc-700 dark:text-zinc-300">{body}</p>

      {/* Those attempts are recorded permanently, and a terminal screen that quietly
          dropped them would make good news feel like a lost session. Held back only
          when there is nothing to report, where "0 of 0 right" is worse than silence. */}
      {run.answered > 0 && (
        <p className="mt-2.5 text-[13px] font-medium">
          You got {run.correct} of {run.answered} right.
        </p>
      )}

      {run.results.length > 0 && (
        <ul className="mt-2.5 flex flex-col gap-2.5">
          {run.results.map((result) => (
            <ResultRow key={`${result.item_id}-${result.created_at}`} result={result} />
          ))}
        </ul>
      )}

      {run.status === "done" && run.resets_at && (
        <p className="mt-3 text-[13px] text-amber-900/80 dark:text-amber-200/80">
          Practice opens again on {formatDay(run.resets_at)}.
        </p>
      )}

      <p className="mt-3 text-[12px] text-amber-900/70 dark:text-amber-200/70">{SCHEDULE_NOTE}</p>
    </div>
  );
}
