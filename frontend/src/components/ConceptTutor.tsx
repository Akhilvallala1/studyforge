"use client";

import { useEffect, useId, useRef, useState } from "react";

import { LessonMarkdown } from "@/components/LessonMarkdown";
import { ApiError, getTutorConversation, sendTutorMessage } from "@/lib/api";
import { formatDay } from "@/lib/copy";
import type { TutorConflict, TutorLimits, TutorMessage } from "@/lib/types";

/**
 * The two register headings, and the sentence that stands between them.
 *
 * Fixed copy, kept together at the top of the file because they are the feature. The
 * design's claim is that the boundary between what the course says and what the model
 * knows lives in the SCHEMA rather than in prose the model was asked to write: the
 * server sends `answer` and `beyond` as separate fields, and these headings are what
 * turns that separation into something a learner can see. Inline `beyond` into the
 * answer's paragraph, or drop the disclaimer, and the schema is still split while the
 * screen is not, which is the whole guarantee gone with nothing failing.
 *
 * "your course", never "your document" and never "the source". The upload is not kept,
 * so there is no document left for a claim about one to be checked against.
 */
const GROUNDED_HEADING = "From your course";
const BEYOND_HEADING = "Not in your course";
const BEYOND_DISCLAIMER =
  "Your course does not cover this. What follows is general knowledge and has not been " +
  "checked against your material.";

/** Where focus belongs once the response has landed and React has committed the tree. */
type FocusTarget = "reply" | "composer" | "send";

function errorMessage(err: unknown): string {
  return err instanceof ApiError
    ? err.message
    : "Could not reach the server. Is the backend running?";
}

/**
 * What the caps have taken, as a count and never as a refusal.
 *
 * Deliberately not a sentence about being out of turns. When a cap is actually reached
 * the words shown are the server's, off the 409, and they carry advice this component
 * could not write: which of the two caps bit decides whether the learner should go and
 * ask about another concept or stop for the day. A second wording of that here is the
 * failure lib/copy exists to prevent, one screen further along.
 */
function usageLine(limits: TutorLimits): string {
  return (
    `${limits.concept_used} of ${limits.concept_limit} questions on this concept today, ` +
    `${limits.day_used} of ${limits.day_limit} across all of them.`
  );
}

/** The day a message was sent, or null when it is unreadable. */
function dayOf(iso: string): string | null {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date.toISOString().slice(0, 10);
}

/**
 * One reply, split into the registers the server sent it in.
 *
 * `answer` and `beyond` are two blocks that do not look alike, and the difference is
 * carried three ways over: by their headings, by their borders, and by the disclaimer.
 * Never by colour alone, because the one reader who most needs to know which half is
 * unchecked is the one who cannot see a hue change.
 */
function TutorReply({
  message,
  conceptLabel,
  blockRef,
}: {
  message: Extract<TutorMessage, { role: "tutor" }>;
  conceptLabel: string;
  blockRef?: React.RefObject<HTMLDivElement | null>;
}) {
  const headingId = useId();

  return (
    <div
      ref={blockRef}
      tabIndex={-1}
      role="region"
      aria-labelledby={headingId}
      className="flex flex-col gap-3 outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
    >
      {/* The region needs a name of its own, and neither register heading can be it:
          calling the whole reply "From your course" would label the ungrounded half as
          grounded at exactly the moment a screen reader user is being told where they
          have landed. */}
      <h5 id={headingId} className="sr-only">
        Tutor reply
      </h5>

      <div className="rounded-lg border border-amber-200 bg-white/70 px-4 py-3 dark:border-amber-900 dark:bg-zinc-900/40">
        <p className="text-[12px] font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-400">
          {GROUNDED_HEADING}
        </p>
        {/* Through LessonMarkdown, which runs react-markdown without rehype-raw: this is
            model output derived from an uploaded document, so raw HTML in it stays
            escaped text. The concept label is passed as the title so a reply that opens
            by restating the concept as a heading does not draw a second one. */}
        <div className="mt-2 text-[13px]">
          <LessonMarkdown content={message.answer} title={conceptLabel} />
        </div>
      </div>

      {message.beyond && (
        /* A DIFFERENT block, never a paragraph appended to the one above. Dashed and
           neutral where the grounded half is solid and amber, so the two do not read as
           one card that happens to have a subheading in it. */
        <div className="rounded-lg border border-dashed border-zinc-400 bg-zinc-50 px-4 py-3 dark:border-zinc-600 dark:bg-zinc-900/60">
          <p className="text-[12px] font-semibold uppercase tracking-wide text-zinc-600 dark:text-zinc-400">
            {BEYOND_HEADING}
          </p>
          <p className="mt-1.5 text-[12px] leading-[1.5] text-zinc-600 dark:text-zinc-400">
            {BEYOND_DISCLAIMER}
          </p>
          {/* No title to strip here: `beyond` is at most three sentences and has no
              heading of its own, and passing the concept label would let it eat a first
              line that only happened to match. */}
          <div className="mt-2 text-[13px]">
            <LessonMarkdown content={message.beyond} title="" />
          </div>
        </div>
      )}

      {message.check && (
        <div className="rounded-lg border border-amber-200/70 px-4 py-2.5 dark:border-amber-900/70">
          <p className="text-[12px] font-semibold uppercase tracking-wide text-amber-800/80 dark:text-amber-400/80">
            Check yourself
          </p>
          {/* Plain text, not markdown. It is one question, and a text node is escaped by
              React on its own, which is the least this untrusted string can be given. */}
          <p className="mt-1.5 text-[13px] text-zinc-700 dark:text-zinc-300">{message.check}</p>
        </div>
      )}
    </div>
  );
}

/** One thing the learner asked, as it sits in the transcript. */
function LearnerMessage({ text }: { text: string }) {
  return (
    <div className="rounded-lg bg-amber-100/60 px-4 py-2.5 dark:bg-amber-950/50">
      <p className="text-[12px] font-semibold uppercase tracking-wide text-amber-900/70 dark:text-amber-200/70">
        You asked
      </p>
      {/* A text node, so whatever was typed is escaped rather than parsed. */}
      <p className="mt-1 whitespace-pre-wrap text-[13px] text-zinc-800 dark:text-zinc-200">
        {text}
      </p>
    </div>
  );
}

/**
 * A conversation with the tutor about one concept the learner keeps missing.
 *
 * Mounted inside the note panel beside ConceptPractice, and that placement is the
 * precondition made structural in the same way practice's is: this subtree only exists
 * when an explanation exists AND is open in front of the learner, so "read the
 * explanation before arguing with it" cannot be broken by a reordering. Nothing on the
 * review route mounts this, which keeps the tutor out of a review session.
 *
 * It is a conversation, not an assessment. The only rows it writes are two
 * tutor_messages per turn; the schedule, the mastery buckets, the attention flag and the
 * retention figure are all untouched, and the panel's promise below says so.
 *
 * The conversation is keyed on the concept and persists: closing this panel, reloading
 * the page, or coming back next month all reopen the same transcript.
 */
export function ConceptTutor({
  conceptKey,
  conceptLabel,
  open,
  onAnnounce,
}: {
  /** Keyed on the concept, not the card. Slashes and spaces are ordinary here. */
  conceptKey: string;
  conceptLabel: string;
  /**
   * Whether the note panel around this is open. The fetch waits for the first true, for
   * the reason ConceptPractice gives: the laziness belongs to this component rather than
   * to where it happens to be rendered, so moving the mount out of that conditional
   * cannot silently turn the panel into a per-concept request on every Today load.
   */
  open: boolean;
  /**
   * Routed into the live region ReteachConcept already mounts empty. No second region is
   * mounted here: the row would then have two announcing about the same concept and a
   * screen reader would read whichever won the race, which is a bug this component tree
   * has shipped three times.
   */
  onAnnounce: (message: string) => void;
}) {
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const [limits, setLimits] = useState<TutorLimits | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  /** A refusal, in the server's words. Separate from `error`, which is a failure. */
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const baseId = useId();
  const requested = useRef(false);
  const pendingFocus = useRef<FocusTarget | null>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const sendRef = useRef<HTMLButtonElement>(null);
  const latestReplyRef = useRef<HTMLDivElement>(null);

  function load() {
    setLoading(true);
    setLoadError(null);
    getTutorConversation(conceptKey)
      .then((conversation) => {
        setMessages(conversation.messages);
        setLimits(conversation.limits);
      })
      .catch((err) => {
        const message = errorMessage(err);
        setLoadError(message);
        onAnnounce(message);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!open || requested.current) return;
    requested.current = true;
    load();
    // `load` closes over conceptKey and onAnnounce, both stable for this row's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, conceptKey]);

  /**
   * Focus, once the response has landed and React has committed the new tree.
   *
   * Every path through here starts with the send button becoming a real `disabled`,
   * which blurs it to the body, so focus is never where the learner left it and always
   * has to be placed. Where it goes says what to do next: onto the reply when there is
   * one to read, back into the box when the text in it can be edited and sent again, and
   * onto the send button when it cannot.
   */
  useEffect(() => {
    const wanted = pendingFocus.current;
    if (!wanted) return;
    pendingFocus.current = null;
    const target =
      wanted === "reply"
        ? latestReplyRef.current
        : wanted === "composer"
          ? composerRef.current
          : sendRef.current;
    // Only when the blur left focus nowhere. A learner who tabbed away mid-request is
    // where they want to be, and yanking them back is worse than the problem being
    // fixed. Same guard, and the same reason, as ReteachConcept's recovered branch.
    if (document.activeElement === document.body) target?.focus();
  }, [messages, notice, error, sending]);

  async function send() {
    if (sending) return;
    const question = draft.trim();
    if (!question) {
      // Announced as well as shown. Focus never leaves the box on this path, and a
      // paragraph appearing next to where you already are is not an event, so without
      // the announcement a screen reader user presses Send and nothing happens at all.
      const empty = "Type a question first.";
      setError(empty);
      onAnnounce(empty);
      return;
    }
    setSending(true);
    setError(null);
    setNotice(null);
    onAnnounce(`Sending your question about ${conceptLabel}.`);
    try {
      const outcome = await sendTutorMessage(conceptKey, question);
      if (outcome.kind === "turn") {
        const { learner, reply, limits: fresh } = outcome.turn;
        // Appended to what is already on screen. The endpoint hands back only the two
        // rows it wrote, deliberately, so there is no second copy of the transcript that
        // could disagree with the one being held here.
        setMessages((current) => [...current, learner, reply]);
        setLimits(fresh);
        // Cleared ONLY here. The box is emptied when the question has actually been
        // delivered and is visible in the transcript above it, and on no other path.
        setDraft("");
        pendingFocus.current = "reply";
        // The reply itself is far too long to announce, so this says one arrived and
        // focus moves to it. Whether it has an ungrounded half is worth carrying,
        // because that is the one thing about a reply that changes how to read it, and
        // moving focus to a region announces the region's name and not its contents.
        onAnnounce(
          reply.role === "tutor" && reply.beyond
            ? `The tutor answered your question about ${conceptLabel}, including a part that is not from your course.`
            : `The tutor answered your question about ${conceptLabel}.`,
        );
        return;
      }

      const conflict: TutorConflict = outcome.conflict;
      // Read before the switch narrows `conflict` away, for the unreachable default.
      const serverMessage = conflict.message;
      setLimits(conflict.limits);
      // The transcript is deliberately NOT touched. This refusal did not change it, and
      // it carries no copy of it to redraw from; that is the point of the 409 being
      // shaped the way it is.
      //
      // Switched on the code, exhaustively, and never on the numbers in `limits`. Its
      // own union and its own switch: RemediationConflict and PracticeConflict are each
      // switched exhaustively elsewhere, and folding these codes into either would leave
      // that switch handling codes its endpoint can never send, which turns a real
      // guarantee into a formality.
      switch (conflict.error) {
        case "concept_turn_limit":
        case "daily_turn_limit":
          // Both are the learner being out of turns, and both are shown in the server's
          // own words rather than in a wording from here. The difference between them is
          // advice, "go and ask about something else" against "you are done for today",
          // and only the endpoint knows which of its two caps actually bit.
          setNotice(serverMessage);
          onAnnounce(serverMessage);
          break;
        default: {
          // Unreachable while the union is exhaustive, and that is the point: a third
          // code becomes a compile error here rather than silently landing on the branch
          // above. The runtime arm still matters, because the server can ship a new code
          // before this file knows about it, and every one of them carries a human
          // message worth showing.
          const unhandled: never = conflict;
          void unhandled;
          setNotice(serverMessage);
          onAnnounce(serverMessage);
        }
      }
      // Nothing was sent and nothing can be until the turns come back, so the box is not
      // where the learner should be put. The notice below the button explains why.
      pendingFocus.current = "send";
    } catch (err) {
      const message = errorMessage(err);
      setError(message);
      onAnnounce(message);
      // The question is STILL IN THE BOX, on every one of these paths. A 502 writes
      // nothing at all, the learner's own message included, and a 422 never got as far
      // as the model, so the text they typed is the only copy in existence and throwing
      // it away would make them write it again to find out whether it was the message or
      // the server. Focus goes back to it, which is both where the retry happens and how
      // a screen reader user finds out it survived.
      pendingFocus.current = "composer";
    } finally {
      setSending(false);
    }
  }

  if (!open) return null;

  const headingId = `${baseId}-heading`;
  const composerId = `${baseId}-composer`;

  return (
    <section
      aria-labelledby={headingId}
      className="mt-4 border-t border-amber-200 pt-4 dark:border-amber-900"
    >
      <h4 id={headingId} className="text-[14px] font-semibold">
        Ask about this concept
      </h4>
      {/* The register contract, said once and before the first reply, so the two
          headings below are not the first the learner hears of it. */}
      <p className="mt-0.5 text-[13px] text-amber-900/80 dark:text-amber-200/80">
        Answers come from your course. Anything the tutor adds from outside it is kept
        under its own heading.
      </p>

      {loading && messages.length === 0 && (
        <p className="mt-3 text-[13px] text-amber-900/70 dark:text-amber-200/70">
          Loading your conversation&hellip;
        </p>
      )}

      {loadError && (
        <div className="mt-3">
          <p className="text-[13px] text-red-800 dark:text-red-300">{loadError}</p>
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

      {messages.length > 0 && (
        <ol className="mt-3.5 flex flex-col gap-3.5">
          {messages.map((message, index) => {
            // A day label whenever the conversation crosses one. These transcripts are
            // kept for good and reopened months later, so "you asked this in March" is
            // the difference between reading your own history and reading a wall.
            const day = dayOf(message.created_at);
            const previous = index === 0 ? null : dayOf(messages[index - 1].created_at);
            return (
              <li key={message.id} className="flex flex-col gap-3.5">
                {day && day !== previous && (
                  <p className="text-[12px] text-zinc-500 dark:text-zinc-500">
                    {formatDay(message.created_at)}
                  </p>
                )}
                {message.role === "learner" ? (
                  <LearnerMessage text={message.content} />
                ) : (
                  <TutorReply
                    message={message}
                    conceptLabel={conceptLabel}
                    /* Only the newest reply is ever a focus target, because focus only
                       moves here on a turn that just landed. */
                    blockRef={index === messages.length - 1 ? latestReplyRef : undefined}
                  />
                )}
              </li>
            );
          })}
        </ol>
      )}

      <div className="mt-3.5">
        <label htmlFor={composerId} className="sr-only">
          Ask about {conceptLabel}
        </label>
        {/* Never disabled, mid-request included. Disabling the focused control blurs it
            to the body, and a second send is already refused by the handler and by the
            button beneath it. Same rule the practice answer field follows. */}
        <textarea
          id={composerId}
          ref={composerRef}
          rows={3}
          value={draft}
          aria-invalid={error ? true : undefined}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            // Enter inserts a newline, because a question can be a paragraph. The
            // shortcut is the modifier, and the hint below says so rather than leaving
            // it to be discovered.
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              void send();
            }
          }}
          placeholder={`Ask anything about ${conceptLabel}`}
          className="w-full resize-y rounded-lg border border-amber-300 bg-transparent px-3 py-2 text-[13px] leading-[1.5] outline-none focus:border-amber-500 dark:border-amber-800"
        />

        {error && <p className="mt-2 text-[13px] text-red-800 dark:text-red-300">{error}</p>}

        {/* The server's own refusal, shown where the send it refused happened. */}
        {notice && (
          <p className="mt-2 rounded-lg bg-white/70 px-3 py-2 text-[13px] text-zinc-700 dark:bg-zinc-900/40 dark:text-zinc-300">
            {notice}
          </p>
        )}

        <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
          {/*
            A real `disabled` while a question is in flight, and that is load-bearing
            beyond this file: the endpoint takes no generation slot and no lock, on the
            reasoning that a double-clicked button cannot buy a second turn because React
            commits this attribute before a second real click can land. Remove it and the
            server has nothing left holding that line.
          */}
          <button
            type="button"
            ref={sendRef}
            onClick={() => void send()}
            disabled={sending}
            className={`rounded-lg bg-amber-800 px-4 py-1.5 text-[13px] font-medium text-white transition-colors dark:bg-amber-200 dark:text-amber-950 ${
              sending
                ? "cursor-progress opacity-60"
                : "hover:bg-amber-700 dark:hover:bg-amber-100"
            }`}
          >
            {sending ? "Asking…" : "Ask"}
          </button>
          <p className="text-[12px] text-zinc-500 dark:text-zinc-500">
            Ctrl or Cmd and Enter sends.
            {/* Only once the server has said what they are. Nothing here invents the
                numbers, and until the conversation has loaded there are none to show. */}
            {limits && ` ${usageLine(limits)}`}
          </p>
        </div>
      </div>
      {/* No schedule promise here. The note panel this is mounted inside carries it,
          widened to name the tutor, and it renders below: a second wording of the same
          fact a few lines apart is the failure lib/copy exists to stop. */}
    </section>
  );
}
