"use client";

import { createContext, useContext, useEffect, useRef, useState, useTransition } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";

import { ApiError, deleteCourse, getDeletionPreview } from "@/lib/api";
import type { CourseDeletion } from "@/lib/types";

/**
 * The ids the post-delete focus lands on, one of which always exists on this page.
 *
 * Looked up in the DOM rather than held in a ref, which is forced rather than lazy: both
 * are rendered by the courses page, which is an async SERVER component, so it cannot be
 * handed a ref and cannot pass a callback down. An id is the only handle a client
 * component has on them.
 *
 * They are also mutually exclusive by construction, and that is the whole reason focus
 * cannot simply "go back to the New course button". Deleting the last course swaps the
 * header control for the empty state's, so the element the learner would return to stops
 * existing precisely when the list empties.
 */
const NEW_COURSE_ID = "new-course";
const FIRST_COURSE_ID = "create-first-course";

interface DeletionContext {
  /** Called once the server has confirmed the delete. Owns the refresh and the announcement. */
  onDeleted: (title: string) => void;
  /** True while the list is being refreshed, so a second delete cannot start mid-flight. */
  refreshing: boolean;
}

const Ctx = createContext<DeletionContext | null>(null);

/**
 * Owns everything about a deletion that has to OUTLIVE THE ROW BEING DELETED.
 *
 * THE ROW UNMOUNTS ON THE REFRESH, which is what makes this component necessary rather
 * than tidy. DeleteCourseButton disappears with its card the moment the list comes back,
 * so it cannot be the thing that restores focus afterwards, and an aria-live region
 * inside the card would be removed before a screen reader ever read it. Both concerns
 * therefore live here, above the list, where the delete cannot destroy them. It is the
 * same problem DaysOffControl solved by sending focus to the form's date field instead of
 * the vanished row, one level up: there the surviving target was a sibling, here the
 * surviving target is the page header.
 *
 * The provider also owns the refresh itself, rather than the button starting one, because
 * whoever starts the transition is the only one who knows when it has landed. The button
 * awaits the request; this awaits the re-render.
 */
export function CourseDeletionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [refreshing, startTransition] = useTransition();
  const [announcement, setAnnouncement] = useState("");
  const wantsFocus = useRef(false);

  function onDeleted(title: string) {
    wantsFocus.current = true;
    setAnnouncement(`${title} deleted.`);
    startTransition(() => router.refresh());
  }

  /**
   * Put focus somewhere real once the refreshed list has committed.
   *
   * THE INTENT IS CONSUMED BEFORE THE GUARD IS CONSULTED, which is the ordering that
   * matters and the one that is easy to get backwards. If the learner has moved on, this
   * declines to take focus AND still clears the flag; leaving it armed would mean the
   * next unrelated render that happened to find focus on the body would yank them into
   * the header, long after the deletion they had already moved past.
   */
  useEffect(() => {
    if (refreshing) return;
    if (!wantsFocus.current) return;
    wantsFocus.current = false;
    // Only when the unmounting row left focus nowhere. A learner who moved on during the
    // request is where they want to be, and hauling them back is worse than the problem.
    if (document.activeElement !== document.body) return;
    const target =
      document.getElementById(NEW_COURSE_ID) ?? document.getElementById(FIRST_COURSE_ID);
    target?.focus();
  }, [refreshing]);

  return (
    <Ctx.Provider value={{ onDeleted, refreshing }}>
      {children}
      {/*
        Outside the list on purpose, so deleting the last course does not remove the
        element that has to announce it. Assertive rather than polite: the thing being
        announced is that the row the learner was standing on has gone.
      */}
      <div role="status" aria-live="assertive" className="sr-only">
        {announcement}
      </div>
    </Ctx.Provider>
  );
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

/**
 * What is about to be destroyed, in the learner's terms, from the server's own counts.
 *
 * The last two lines are the honest parts a generic confirmation hides: the derived
 * figures on the Today screen are computed from history this delete removes, and the
 * spend is the one thing that survives. Both are true and neither is reassurance for its
 * own sake, which is why the Usage line stays even though it is the only comforting
 * sentence here.
 */
function previewLines(preview: CourseDeletion): string[] {
  const lines = [
    `${plural(preview.lessons, "lesson", "lessons")}, ${preview.lessons_completed} of them completed, and ${plural(preview.attempts, "answer", "answers")} you have given are deleted permanently.`,
  ];
  const retired = `${plural(preview.concepts_retired, "concept stops", "concepts stop")} being reviewed and their review history goes with them`;
  // The "also taught elsewhere" clause is omitted rather than rendered as "0 more",
  // because a learner with no shared concepts should not be told about a category that
  // is empty for them.
  lines.push(
    preview.concepts_kept > 0
      ? `${retired}; ${preview.concepts_kept} more are also taught by another course and keep theirs.`
      : `${retired}.`,
  );
  lines.push(
    "Your retention, streak and pace are measured from your history, so they may change.",
  );
  lines.push("What this course cost you is kept in Usage.");
  return lines;
}

/**
 * Delete, as a two-step on the card itself.
 *
 * NOT a browser confirm() and not a typed-the-title gate. Two deliberate presses is the
 * right weight for something irreversible; making a learner type the name of their own
 * course, in an app they are running on their own machine, is a dialog performing
 * seriousness rather than conveying it. What carries the weight is the counts, which are
 * real and specific, and which a fixed "are you sure" could not show.
 */
export function DeleteCourseButton({ courseId, title }: { courseId: number; title: string }) {
  const ctx = useContext(Ctx);
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<CourseDeletion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  /*
   * Tracks the PREVIEW fetch specifically, not "something is in flight".
   *
   * `busy` covers both the preview and the delete, and the confirming button has to
   * treat those two opposite ways: refuse presses during the first, keep accepting
   * them during the second. Deriving the loading window from `busy && !preview &&
   * !error` looks equivalent and is not, because confirmDelete clears the error on
   * entry: retrying after a failed preview would land on busy true, preview null,
   * error null, and re-disable the button in the middle of the delete, which is the
   * focus-dropping behaviour the button is deliberately built to avoid.
   */
  const [loadingPreview, setLoadingPreview] = useState(false);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  /*
   * Set only by Cancel, and read once by the effect below.
   *
   * `open` going false is not by itself a reason to take focus: it is also the
   * initial state of every card on the page, and focusing on that would have each
   * row in the list grab focus as it mounts. Only the cancel path has somewhere the
   * learner actually came from.
   */
  const wantsTriggerFocus = useRef(false);
  /*
   * Bumped on every openConfirm call and on Cancel, so a preview response can tell
   * whether it is still the one anyone is waiting for.
   *
   * Cancel cannot simply clear `busy`/`loadingPreview` itself: the abandoned fetch is
   * still in flight, and when it eventually settles its own `finally` would clear
   * those flags again, re-disabling the confirm button (or worse, re-enabling it out
   * from under a newer request) at a time nothing on screen explains. A response
   * whose generation no longer matches is ignored in full, including its `finally`,
   * which is what lets Cancel clear the busy state immediately without racing it.
   */
  const generationRef = useRef(0);

  if (!ctx) throw new Error("DeleteCourseButton must be rendered inside CourseDeletionProvider");
  const { onDeleted, refreshing } = ctx;
  const pending = busy || refreshing;

  async function openConfirm() {
    if (pending) return;
    const generation = ++generationRef.current;
    setOpen(true);
    setError(null);
    setBusy(true);
    setLoadingPreview(true);
    try {
      const result = await getDeletionPreview(courseId);
      if (generationRef.current !== generation) return;
      setPreview(result);
    } catch (err) {
      if (generationRef.current !== generation) return;
      // A 404 arrives here as its bare-string detail, already turned into a message by
      // `request`, so this branch does not care which shape the server used.
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      if (generationRef.current === generation) {
        setBusy(false);
        setLoadingPreview(false);
      }
    }
  }

  /*
   * Move to the confirming button once the panel is open AND the preview has landed,
   * so a keyboard learner is not left on a control that has just changed meaning
   * underneath them.
   *
   * Gated on `!loadingPreview` as defence in depth, NOT because a reachable path needs
   * it today. The case it reads as guarding against, a stale fetch's `setPreview`
   * landing after the panel is reopened, is already prevented one level up by Cancel's
   * `generationRef.current++`: the abandoned request returns before `setPreview(result)`,
   * so `preview` is null on reopen and the `preview` check alone declines.
   *
   * Measured, do not restate this without re-running it: dropping the `!loadingPreview`
   * gate and throwing if the effect ever focuses a disabled button leaves the whole
   * suite green, so the throw never fires. An earlier version of this comment called the
   * opposite "verified"; it described the world before Cancel's bump existed, and the
   * bump and that comment landed in the same commit. Keep the gate if Cancel's bump is
   * ever removed, but it is redundant while both are here.
   */
  useEffect(() => {
    if (open && preview && !loadingPreview) confirmRef.current?.focus();
  }, [open, preview, loadingPreview]);

  // Cancel unmounts the panel that holds the focused Cancel button, so without this
  // focus falls to the body and a keyboard learner loses their place in the list.
  // The trigger is where they pressed Enter, so it is where they get put back.
  useEffect(() => {
    if (open) return;
    if (!wantsTriggerFocus.current) return;
    wantsTriggerFocus.current = false;
    // Same guard as the provider's restore (and in the same order relative to
    // consuming the flag above: consume first, decline after, so a decline cannot
    // leave the intent armed for a later, unrelated commit). Mouse clicks do not
    // move focus onto the button they hit in Safari and Firefox, so a learner who was
    // typing in another field when they clicked Cancel never left it; without this,
    // they would be pulled out of it into the trigger.
    if (document.activeElement !== document.body) return;
    triggerRef.current?.focus();
  }, [open]);

  async function confirmDelete() {
    // The re-entry guard, which is why the confirming button below is NOT disabled while
    // the request is in flight: disabling the focused control blurs it to the body, and
    // this handler already refuses a second press.
    if (pending) return;
    setBusy(true);
    setError(null);
    try {
      await deleteCourse(courseId);
      onDeleted(title);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
      setBusy(false);
    }
    // No setBusy(false) on success: this component is about to unmount with its row, and
    // setting state on the way out is a no-op at best.
  }

  /*
   * The trigger sits in its own full-width block rather than beside the title, so that
   * opening it can expand the card downwards. A button tucked into a flex row next to the
   * link has nowhere to put four lines of consequences: the panel would be squeezed into
   * the narrow column the button occupied.
   */
  if (!open) {
    return (
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          ref={triggerRef}
          onClick={() => void openConfirm()}
          className="rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-600 transition-colors hover:border-zinc-500 hover:text-zinc-900 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-500 dark:hover:text-zinc-100"
        >
          Delete
        </button>
      </div>
    );
  }

  return (
    <div className="mt-3 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3.5 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-[13px] font-medium">Delete &ldquo;{title}&rdquo;?</p>
      {error ? (
        <p role="alert" className="mt-1.5 text-[13px] text-red-700 dark:text-red-400">
          {error}
        </p>
      ) : preview ? (
        <div className="mt-1.5 text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400">
          {previewLines(preview).map((line) => (
            <p key={line} className="mt-1 first:mt-0">
              {line}
            </p>
          ))}
        </div>
      ) : (
        // aria-live so a screen reader user learns something is happening: with the
        // confirming button disabled and focus still on body at this point (the focus
        // effect above declines until the preview lands), nothing else here speaks.
        <p aria-live="polite" className="mt-1.5 text-[13px] text-zinc-500 dark:text-zinc-400">
          Checking what this would delete…
        </p>
      )}
      <div className="mt-3.5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => {
            // Invalidates the in-flight preview fetch (see generationRef above) so its
            // response cannot resurface after this closes the loading window: without
            // this, clearing busy/loadingPreview here would let a press that reopens
            // the panel start a second preview that the first one's `finally` could
            // still clobber.
            generationRef.current++;
            wantsTriggerFocus.current = true;
            setOpen(false);
            setPreview(null);
            setError(null);
            // Cleared here, not left for the abandoned fetch's `finally`: that finally
            // is now a no-op for a stale generation, and without clearing these the
            // trigger's `if (pending) return` would swallow the very next press for as
            // long as the abandoned fetch happens to take, with no feedback on screen.
            setBusy(false);
            setLoadingPreview(false);
          }}
          // Enabled during the preview load (a slow preview must stay cancellable) and
          // once it lands, disabled only while the delete itself is running: cancelling
          // then would park focus on this row's own trigger (see wantsTriggerFocus)
          // while the delete is still in flight, and that trigger's `if (pending)
          // return` would swallow the press with no feedback. `!loadingPreview` is the
          // same "am I mid-delete" test the confirming button's disabled prop is not
          // allowed to use (see confirmDelete's comment), stated the other way round.
          disabled={busy && !loadingPreview}
          className="rounded-lg border border-zinc-300 px-3.5 py-1.5 text-xs font-medium transition-colors hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:border-zinc-500"
        >
          Cancel
        </button>
        <button
          type="button"
          ref={confirmRef}
          onClick={() => void confirmDelete()}
          /*
           * Disabled ONLY while the preview loads. Until it lands this button cannot
           * honour a press (confirmDelete returns early on `pending`), and it used to
           * say "Delete permanently" throughout that window and drop the click in
           * silence: no delete, no error, nothing on screen. It is never disabled
           * during the delete itself, because by then it holds focus and disabling a
           * focused control blurs it to the body.
           */
          disabled={loadingPreview}
          className="rounded-lg bg-red-700 px-3.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-800 dark:bg-red-800 dark:hover:bg-red-700"
        >
          {busy && !loadingPreview ? "Deleting…" : "Delete permanently"}
        </button>
      </div>
    </div>
  );
}
