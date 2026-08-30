"use client";

import { useEffect, useRef, useState } from "react";

import { LessonMarkdown } from "@/components/LessonMarkdown";
import { ApiError, requestRemediation } from "@/lib/api";
import type { NeedsAttentionEntry, RemediationNote } from "@/lib/types";

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

/** A fixed locale, so a date rendered on the server survives hydration unchanged. */
function formatDay(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
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
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [availableFrom, setAvailableFrom] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const wantsFocus = useRef(false);

  const panelId = `reteach-panel-${entry.card_id}`;
  const hasNote = note !== null;

  // The call is one model round trip that reports no progress, so the honest signal
  // is that time is passing. Same choice GenerateForm makes, and for the same reason:
  // a percentage here would be invented.
  useEffect(() => {
    if (!pending) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [pending]);

  // Focus lands on the explanation once it is on screen, so a keyboard or screen
  // reader user ends up at the thing they asked for rather than back at the body.
  useEffect(() => {
    if (!open || !wantsFocus.current) return;
    wantsFocus.current = false;
    panelRef.current?.focus();
  }, [open, note]);

  async function generate() {
    setPending(true);
    setElapsed(0);
    setError(null);
    setNotice(null);
    setAnnouncement(`Writing an explanation of ${entry.concept_label}.`);
    try {
      const outcome = await requestRemediation(entry.card_id);
      if (outcome.kind === "note") {
        setNote(outcome.note);
        setAvailableFrom(null);
        wantsFocus.current = true;
        setOpen(true);
        setAnnouncement(`An explanation of ${entry.concept_label} is ready.`);
        return;
      }
      const { error: code, note: existing } = outcome.conflict;
      if (existing) {
        // note_active and cooldown_active both mean "you already have one of these".
        // Only the cooldown needs to say when another could be written; an active note
        // is simply the current one.
        setNote(existing);
        setAvailableFrom(code === "cooldown_active" ? existing.cooldown_until : null);
        wantsFocus.current = true;
        setOpen(true);
        setAnnouncement(`Showing the explanation of ${entry.concept_label} you already have.`);
        return;
      }
      // not_flagged, reachable when the list was drawn before the concept recovered.
      // It is good news, so it reads as good news rather than as a refusal.
      const recovered =
        `${entry.concept_label} is no longer one of the concepts you keep missing, ` +
        "so there is nothing to re-teach. It stays in your review queue on its usual schedule.";
      setNotice(recovered);
      setAnnouncement(recovered);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Is the backend running?",
      );
      setAnnouncement("");
    } finally {
      setPending(false);
    }
  }

  function handleClick() {
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

  const label = pending
    ? "Writing…"
    : hasNote
      ? open
        ? "Hide explanation"
        : "Show explanation"
      : "Re-teach";
  const accessibleName = pending
    ? `Writing an explanation of ${entry.concept_label}`
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
          <div className="mt-0.5 text-[13px] text-zinc-500 dark:text-zinc-400">
            Missed {entry.missed} of {entry.of} times
            {entry.is_due && " · due now"}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <RecallBar retrievability={entry.retrievability} />
          <button
            type="button"
            ref={buttonRef}
            onClick={handleClick}
            disabled={pending}
            aria-label={accessibleName}
            aria-expanded={hasNote ? open : undefined}
            aria-controls={hasNote && open ? panelId : undefined}
            className="rounded-lg border border-zinc-300 px-3.5 py-1.5 text-[13px] font-medium transition-colors hover:border-zinc-500 disabled:cursor-progress disabled:opacity-60 dark:border-zinc-700 dark:hover:border-zinc-500"
          >
            {label}
          </button>
        </div>
      </div>

      {/* Mounted unconditionally and empty until there is something to say. A live
          region has to be in the accessibility tree BEFORE its content arrives: if the
          attribute and the text appear in the same render, screen readers routinely
          miss the announcement. The explanation itself is too long to announce, so
          this says it has arrived and focus moves to it. */}
      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      {pending && (
        <div className="mt-3 flex items-center gap-3 rounded-lg border border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <span
            aria-hidden
            className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100"
          />
          <div className="text-[13px]">
            <p className="font-medium">Writing an explanation of this concept.</p>
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

      {error && (
        <p
          role="alert"
          className="mt-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-[13px] text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
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

          <p className="mt-4 border-t border-amber-200 pt-3 text-[13px] text-amber-900/80 dark:border-amber-900 dark:text-amber-200/80">
            This concept stays in your review queue on its usual schedule. Nothing here
            reschedules it or marks it learned.
            {availableFrom && ` A new explanation can be written from ${formatDay(availableFrom)}.`}
          </p>
        </div>
      )}
    </li>
  );
}
