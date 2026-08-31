"use client";

import { useEffect, useRef, useState } from "react";

import { ConceptPractice } from "@/components/ConceptPractice";
import { LessonMarkdown } from "@/components/LessonMarkdown";
import { ApiError, getRemediation, requestRemediation } from "@/lib/api";
import { formatDay, noLongerMissed, SCHEDULE_PROMISE } from "@/lib/copy";
import type { NeedsAttentionEntry, RemediationNote } from "@/lib/types";

/* How a request that lost the race waits for the winner. The refusal carries no
   note, so the only way to learn the outcome is to ask again. GET is the thing to
   poll: it costs nothing, it cannot claim the slot, and it answers null until the
   note is genuinely finished. */
const POLL_INTERVAL_MS = 3000;

/* The ceiling is the server's, not a guess. The provider reads with timeout=600
   (llm/ollama_provider.py), and both main.py and remediation.py reason against that
   number, so a generation is entitled to take this long. A shorter bound abandons a
   call that is still perfectly healthy and, worse, tells the learner it is slow when
   it is not: the course-generation flow waits out the full call without a client
   timeout at all, and there is no reason this one should be less patient. */
const POLL_CEILING_MS = 600_000;
const POLL_ATTEMPTS = Math.ceil(POLL_CEILING_MS / POLL_INTERVAL_MS);

/** Recall probability as a bar. Empty, not full, when the card has never been scheduled. */
function RecallBar({ retrievability }: { retrievability: number | null }) {
  const percent = retrievability === null ? 0 : Math.round(retrievability * 100);
  return (
    <div
      role="img"
      aria-label={
        retrievability === null
          ? "Recall probability not known yet"
          : `Recall probability ${percent} percent`
      }
      className="h-[5px] w-[84px] overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800"
    >
      <div className="h-full bg-amber-600" style={{ width: `${percent}%` }} />
    </div>
  );
}

/**
 * When the next explanation of this concept could be written, or null if that moment
 * has passed. Derived from the note rather than remembered from the click that
 * revealed it, so the line survives a reload: the note carries the field either way,
 * and a fact about the note should not depend on how the learner got to it.
 */
function nextAvailable(note: RemediationNote | null): string | null {
  if (!note?.cooldown_until) return null;
  const until = new Date(note.cooldown_until);
  if (Number.isNaN(until.getTime()) || until.getTime() <= Date.now()) return null;
  return note.cooldown_until;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/**
 * One row of the needs-attention list, with the explanation it can be asked for.
 *
 * Re-teaching is offered here, never applied. Nothing this component does reschedules
 * the card, clears its lapses or takes it out of the review queue, and the copy says
 * so, because the one thing a learner might reasonably assume from a button called
 * Re-teach is that it has reset something.
 */
export function ReteachConcept({
  entry,
  initialNote,
}: {
  entry: NeedsAttentionEntry;
  initialNote: RemediationNote | null;
}) {
  const [note, setNote] = useState<RemediationNote | null>(initialNote);
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [awaiting, setAwaiting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  // Set once the server has said this concept is no longer one the learner keeps
  // missing. That answer is newer than the numbers this row was drawn from, so the row
  // stops repeating them rather than contradicting the notice printed underneath it.
  const [recovered, setRecovered] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const wantsFocus = useRef(false);
  // Kept in step with `note` so a request that resolves second can see what the first
  // already put on screen. The state variable cannot answer that question: two clicks
  // landing in one task both close over the render where there was no note.
  const noteRef = useRef<RemediationNote | null>(initialNote);

  const panelId = `reteach-panel-${entry.card_id}`;
  const hasNote = note !== null;
  const availableFrom = nextAvailable(note);
  // Our own call and someone else's look the same from here: work is happening and
  // the button must not start a second one.
  const busy = pending || awaiting;
  /**
   * When the button itself has nothing left to do, which is narrower than `recovered`.
   *
   * Two routes reach `recovered` and they want different things from the button. The
   * button's own `not_flagged` refusal only happens when there is no note, so there is
   * nothing to show and the control is genuinely spent. The practice panel's `no_note`
   * report arrives with an explanation open on screen, and that panel is inside the
   * very thing this button toggles: going inert there would strand the learner with a
   * panel they could close but never reopen. `recovered` still drops the stale miss
   * counts in both cases, which is the part both routes agree on.
   */
  const spent = recovered && !hasNote;

  /**
   * Put an explanation on screen, from wherever it came.
   *
   * Clearing `awaiting` is part of showing one: whatever produced this note, the
   * generation that was being waited for has finished. Without that, a click that lost
   * the race and was told `generation_in_progress` keeps its spinner, which then sits
   * above the finished explanation insisting it is still being written.
   */
  function showNote(next: RemediationNote) {
    noteRef.current = next;
    setNote(next);
    setAwaiting(false);
    wantsFocus.current = true;
    setOpen(true);
  }

  // The call is one model round trip that reports no progress, so the honest signal
  // is that time is passing. Same choice GenerateForm makes, and for the same reason:
  // a percentage here would be invented.
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [busy]);

  // Wait out a generation another request is already running. Only GET is polled:
  // repeating the POST would keep asking for a slot that is taken, and each reply
  // would have to be re-interpreted, where GET answers the only question here.
  useEffect(() => {
    if (!awaiting) return;
    let cancelled = false;
    let attempts = 0;
    const timer = setInterval(async () => {
      attempts += 1;
      let found: RemediationNote | null = null;
      try {
        found = await getRemediation(entry.card_id);
      } catch {
        // One failed poll is not worth telling the learner about; the next is due
        // in a few seconds and the loop is bounded either way.
      }
      if (cancelled) return;
      if (found) {
        // Written out rather than routed through showNote, which is defined in the
        // component body and would have to become a dependency of this effect.
        noteRef.current = found;
        setNote(found);
        setAwaiting(false);
        wantsFocus.current = true;
        setOpen(true);
        setAnnouncement(`An explanation of ${entry.concept_label} is ready.`);
        return;
      }
      if (attempts >= POLL_ATTEMPTS) {
        // Announced, not just shown. Giving up is a terminal state like any other,
        // and the button silently re-enabling is not something a screen reader user
        // can see happen.
        const gaveUp =
          "That explanation did not arrive. The request writing it has run out of " +
          "time, so ask again when you are ready.";
        setAwaiting(false);
        setNotice(gaveUp);
        setAnnouncement(gaveUp);
      }
    }, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [awaiting, entry.card_id, entry.concept_label]);

  // Focus lands on the explanation once it is on screen, so a keyboard or screen
  // reader user ends up at the thing they asked for rather than back at the body.
  useEffect(() => {
    if (!open || !wantsFocus.current) return;
    wantsFocus.current = false;
    panelRef.current?.focus();
  }, [open, note]);

  // The recovered path has no panel to land on, and it has already lost focus: the
  // click passed through `busy`, `busy` is a real disabled, and disabling the focused
  // element blurs it. Every other terminal state in this component puts focus
  // somewhere meaningful, so this one returns it to the trigger the learner pressed,
  // which aria-disabled keeps focusable for exactly this reason. Left alone, a
  // keyboard user was dropped to the body and tabbed onward past the notice their
  // own keypress produced.
  //
  // Keyed on `spent` rather than on `recovered`, because only the button's own route
  // loses focus this way. When the practice panel reports the same news, the learner is
  // inside that panel and it has already moved focus onto its terminal state; pulling
  // them back out to this button would undo it.
  useEffect(() => {
    if (!spent) return;
    // Only when the blur left focus nowhere. If they moved on while the request was
    // in flight, that is where they want to be.
    if (document.activeElement === document.body) buttonRef.current?.focus();
  }, [spent]);

  async function generate() {
    setPending(true);
    setElapsed(0);
    setError(null);
    setNotice(null);
    setAnnouncement(`Writing an explanation of ${entry.concept_label}.`);
    try {
      const outcome = await requestRemediation(entry.card_id);
      if (outcome.kind === "note") {
        showNote(outcome.note);
        setAnnouncement(`An explanation of ${entry.concept_label} is ready.`);
        return;
      }
      const conflict = outcome.conflict;
      // Read before the switch narrows `conflict` away, for the unreachable default.
      const serverMessage = conflict.message;
      // Switched on the code, exhaustively, never on whether a note arrived.
      // generation_in_progress and not_flagged are indistinguishable by payload and
      // opposite in meaning, so a shape test would eventually tell a learner whose
      // explanation is mid-flight that they no longer need one.
      switch (conflict.error) {
        case "note_active":
        case "cooldown_active":
          // Narrowing has proved there is a note here, so this branch cannot be
          // reached by an absent one however the union grows.
          showNote(conflict.note);
          setAnnouncement(`Showing the explanation of ${entry.concept_label} you already have.`);
          break;
        case "generation_in_progress":
          // A click that lost the race by a hair comes back to find the winner's
          // explanation already on the page. There is nothing left to wait for, so it
          // opens what is there rather than raising a spinner above it. Saying nothing
          // is what keeps the live region honest too: the winner has just announced the
          // explanation is ready, and announcing that it is being written and then that
          // it is ready again describes a sequence that did not happen.
          if (noteRef.current) {
            wantsFocus.current = true;
            setOpen(true);
            break;
          }
          setAwaiting(true);
          setAnnouncement(`An explanation of ${entry.concept_label} is already being written.`);
          break;
        case "not_flagged": {
          // Reachable when the list was drawn before the concept recovered. It is good
          // news, so it reads as good news rather than as a refusal, and the row drops
          // the miss counts it was drawn with: the server has just said they are out of
          // date, and a stale count beside this notice reads as the page disagreeing
          // with itself. Nothing replaces them, because nothing here knows the new ones.
          // The clause itself lives in lib/copy, because the practice panel below can
          // deliver the same news by a different route and one row must not carry two
          // wordings of one fact.
          const message =
            `${noLongerMissed(entry.concept_label)}, so there is nothing to re-teach. ` +
            "It stays in your review queue on its usual schedule.";
          setRecovered(true);
          setNotice(message);
          setAnnouncement(message);
          break;
        }
        default: {
          // Unreachable while the union is exhaustive, and that is the point: a fifth
          // code becomes a compile error here rather than silently landing on one of
          // the branches above. The runtime arm still matters, because the server can
          // ship a new code before this file knows about it, and every one of them
          // carries a human message worth showing.
          const unhandled: never = conflict;
          void unhandled;
          setNotice(serverMessage);
          setAnnouncement(serverMessage);
        }
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?";
      setError(message);
      // Routed through the mounted live region rather than left to a role="alert"
      // that appears with its own text, which is the announcement this project has
      // already watched go missing once.
      setAnnouncement(message);
    } finally {
      setPending(false);
    }
  }

  function handleClick() {
    // aria-disabled does not stop activation the way disabled does, so the refusal
    // has to be here. See the button for why it is aria-disabled and not disabled.
    if (spent) return;
    if (!hasNote) {
      void generate();
      return;
    }
    if (open) {
      setOpen(false);
      return;
    }
    wantsFocus.current = true;
    setOpen(true);
  }

  const label = busy
    ? "Writing…"
    : spent
      ? "Not needed"
      : hasNote
        ? open
          ? "Hide explanation"
          : "Show explanation"
        : "Re-teach";
  const accessibleName = busy
    ? `Writing an explanation of ${entry.concept_label}`
    : spent
      ? `${entry.concept_label} no longer needs re-teaching`
      : hasNote
        ? open
          ? `Hide the explanation of ${entry.concept_label}`
          : `Show the explanation of ${entry.concept_label}`
        : `Re-teach ${entry.concept_label}`;

  return (
    <li className="flex flex-col rounded-lg border border-zinc-200 px-[18px] py-3.5 dark:border-zinc-800">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-[15px] font-medium">{entry.concept_label}</div>
          {/* Dropped once the concept has recovered, whichever control found that out:
              the re-teach button being told `not_flagged`, or the practice panel below
              finding its run come back `no_note`. These counts came from the page load
              and the server has since said something newer, so leaving them up has the
              row contradict itself, "Missed 2 of 3 times, due now" sitting directly over
              a panel saying the learner is past it. Nothing replaces them, because
              nothing here knows the new ones. */}
          {!recovered && (
            <div className="mt-0.5 text-[13px] text-zinc-500 dark:text-zinc-400">
              Missed {entry.missed} of {entry.of} times
              {entry.is_due && " · due now"}
            </div>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <RecallBar retrievability={entry.retrievability} />
          <button
            type="button"
            ref={buttonRef}
            onClick={handleClick}
            /*
              Two inert states, expressed differently on purpose.

              `busy` is a real `disabled`. It is transient, and React commits it before
              a second real click can land, which is the only thing stopping a
              double-clicked button from starting two metered generations.

              `spent` is permanent for this render, and `disabled` would blur the
              button the instant it is set: a learner who pressed Enter on it dropped to
              the body and tabbed onward past the very notice their keypress produced.
              aria-disabled keeps the element focusable, so focus never moves and there
              is nothing to restore, and a keyboard user tabbing back through the row
              still meets the button and hears why it is inert. Focusing the notice
              instead would also solve the focus loss, but the notice and the live
              region carry the same words, and this component already refuses to put
              the same text in two places a screen reader will read.

              `spent`, not `recovered`: a concept that recovered while its explanation is
              open still has an explanation to show and hide, and this button is what
              shows and hides it.
            */
            disabled={busy}
            aria-disabled={spent || undefined}
            aria-label={accessibleName}
            aria-expanded={hasNote ? open : undefined}
            aria-controls={hasNote && open ? panelId : undefined}
            className={`rounded-lg border border-zinc-300 px-3.5 py-1.5 text-[13px] font-medium transition-colors dark:border-zinc-700 ${
              busy || spent
                ? `opacity-60 ${busy ? "cursor-progress" : "cursor-not-allowed"}`
                : "hover:border-zinc-500 dark:hover:border-zinc-500"
            }`}
          >
            {label}
          </button>
        </div>
      </div>

      {/* Mounted unconditionally and empty until there is something to say. A live
          region has to be in the accessibility tree BEFORE its content arrives: if the
          attribute and the text appear in the same render, screen readers routinely
          miss the announcement. Every terminal state routes through here, including
          the ones that only change what a sighted reader can see. The explanation
          itself is too long to announce, so this says it has arrived and focus moves
          to it. */}
      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      {busy && (
        <div className="mt-3 flex items-center gap-3 rounded-lg border border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <span
            aria-hidden
            className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100"
          />
          <div className="text-[13px]">
            <p className="font-medium">
              {awaiting
                ? "An explanation of this concept is already being written. Waiting for it."
                : "Writing an explanation of this concept."}
            </p>
            <p className="mt-0.5 tabular-nums text-zinc-600 dark:text-zinc-400">
              Elapsed: {formatElapsed(elapsed)}
            </p>
          </div>
        </div>
      )}

      {notice && (
        <p className="mt-3 rounded-lg bg-zinc-50 px-4 py-3 text-[13px] text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
          {notice}
        </p>
      )}

      {/* No role="alert" here: the text is announced through the live region above,
          and carrying it in both places makes a screen reader say it twice. */}
      {error && (
        <p className="mt-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-[13px] text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}

      {note && open && (
        <div
          id={panelId}
          ref={panelRef}
          tabIndex={-1}
          role="region"
          aria-labelledby={`${panelId}-heading`}
          className="mt-3.5 rounded-lg border border-amber-200 bg-amber-50/60 px-[18px] py-4 outline-none focus-visible:ring-2 focus-visible:ring-amber-500 dark:border-amber-900 dark:bg-amber-950/30"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h3 id={`${panelId}-heading`} className="text-[15px] font-semibold">
              Explained another way
            </h3>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                buttonRef.current?.focus();
              }}
              className="shrink-0 rounded-lg border border-amber-300 px-3 py-1 text-[13px] font-medium text-amber-900 transition-colors hover:border-amber-500 dark:border-amber-800 dark:text-amber-200 dark:hover:border-amber-600"
            >
              Hide
            </button>
          </div>

          {/* Through LessonMarkdown, which runs react-markdown without rehype-raw: this
              content is model output derived from an uploaded document, so any raw HTML
              in it stays escaped text. */}
          <div className="mt-3">
            <LessonMarkdown content={note.content} title={note.concept_label} />
          </div>

          {/* Practice lives INSIDE the note panel, and that placement is the
              precondition rather than a layout preference: this subtree only exists
              when an explanation exists AND is open in front of the learner, so
              "explanation before practice" cannot be broken by a reordering. Nothing
              on the review route renders this component, which is what keeps practice
              out of a review session.

              `open` is passed rather than relied on implicitly so the panel can fetch
              lazily on the first open: Today already runs one getRemediation per
              flagged concept in a fan-out, and this panel is closed by default and
              mostly never opened, so it must not become a second one. */}
          <ConceptPractice
            cardId={entry.card_id}
            conceptLabel={entry.concept_label}
            open={open}
            onAnnounce={setAnnouncement}
            /* Only the miss counts are dropped. No notice and no announcement: the
               practice panel is already saying this in its own terminal state and has
               moved focus onto it, and adding the row's `not_flagged` notice underneath
               would be the same news twice, once in a panel and once in a paragraph. */
            onRecovered={() => setRecovered(true)}
          />

          {/* The whole panel's promise, made once and covering everything inside it.
              The practice panel above deliberately carries no wording of its own: it
              renders directly against this paragraph, and two statements of one fact
              two lines apart is worse than one that names both. */}
          <p className="mt-4 border-t border-amber-200 pt-3 text-[13px] text-amber-900/80 dark:border-amber-900 dark:text-amber-200/80">
            {SCHEDULE_PROMISE}
            {availableFrom && ` A new explanation can be written from ${formatDay(availableFrom)}.`}
          </p>
        </div>
      )}
    </li>
  );
}
