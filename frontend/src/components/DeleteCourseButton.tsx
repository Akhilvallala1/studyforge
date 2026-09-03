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
  const confirmRef = useRef<HTMLButtonElement>(null);

  if (!ctx) throw new Error("DeleteCourseButton must be rendered inside CourseDeletionProvider");
  const { onDeleted, refreshing } = ctx;
  const pending = busy || refreshing;

  async function openConfirm() {
    if (pending) return;
    setOpen(true);
    setError(null);
    setBusy(true);
    try {
      setPreview(await getDeletionPreview(courseId));
    } catch (err) {
      // A 404 arrives here as its bare-string detail, already turned into a message by
      // `request`, so this branch does not care which shape the server used.
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  // Move to the confirming button once the panel is open, so a keyboard learner is not
  // left on a control that has just changed meaning underneath them.
  useEffect(() => {
    if (open && preview) confirmRef.current?.focus();
  }, [open, preview]);

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
        <p className="mt-1.5 text-[13px] text-zinc-500 dark:text-zinc-400">
          Checking what this would delete…
        </p>
      )}
      <div className="mt-3.5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            setPreview(null);
            setError(null);
          }}
          className="rounded-lg border border-zinc-300 px-3.5 py-1.5 text-xs font-medium transition-colors hover:border-zinc-500 dark:border-zinc-700 dark:hover:border-zinc-500"
        >
          Cancel
        </button>
        <button
          type="button"
          ref={confirmRef}
          onClick={() => void confirmDelete()}
          className="rounded-lg bg-red-700 px-3.5 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-800 dark:bg-red-800 dark:hover:bg-red-700"
        >
          {busy && preview ? "Deleting…" : "Delete permanently"}
        </button>
      </div>
    </div>
  );
}
