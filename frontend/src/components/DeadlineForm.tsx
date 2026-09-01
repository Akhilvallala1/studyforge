"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ApiError, clearCourseDeadline, setCourseDeadline } from "@/lib/api";
import type { CoursePlan } from "@/lib/types";

const FIELD_CLASS =
  "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 " +
  "focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100";

/** Which control should hold focus once the request has landed and the tree is committed. */
type DeadlineFocus = "day" | "label" | "submit";

/**
 * Where focus belongs after this form has been rebuilt, held OUTSIDE the component.
 *
 * A ref would be the house pattern and it cannot work here. The page keys this form on
 * the saved deadline, so that clearing a date empties the inputs rather than leaving the
 * learner staring at the value they just removed. That key is correct, and it means
 * every successful save and every clear UNMOUNTS this component and mounts a new one:
 * the instance that made the request is gone by the time focus needs placing, and any
 * ref it was holding died with it.
 *
 * One module variable is the smallest thing that survives that, and it is safe because
 * there is never more than one of these mounted. It is one form, on one course's plan
 * page. The failure path does not remount, and reads the same variable from the same
 * instance, so both routes share one mechanism instead of two.
 */
let focusAfterRebuild: DeadlineFocus | null = null;

/**
 * Setting, moving and clearing the one date this feature knows about.
 *
 * WHAT SAVING A DEADLINE DOES, so the control is not read as more than it is: it writes
 * a date on the course and recomputes a rate. No review card moves, no lesson changes
 * state, and clearing it puts the course back exactly where it was. The copy around
 * this form says so; the form must not quietly imply otherwise by, say, offering to
 * "prepare" anything.
 *
 * THERE IS DELIBERATELY NO `min` ON THE DATE INPUT. The server rejects a past date
 * against the learner's study day, which carries a 04:00 boundary and the configured
 * timezone; the browser only knows its own local midnight. A `min` computed here would
 * disagree with the server for everyone between midnight and 04:00, and would block a
 * date the server would happily accept. The server owns the question, so it answers it,
 * and its sentence is what the learner reads.
 */
export function DeadlineForm({ plan }: { plan: CoursePlan }) {
  const router = useRouter();
  const [day, setDay] = useState(plan.deadline ?? "");
  const [label, setLabel] = useState(plan.deadline_label ?? "");
  const [saving, setSaving] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const pending = saving || refreshing;
  const hasDeadline = plan.deadline !== null;
  const dayRef = useRef<HTMLInputElement>(null);
  const labelRef = useRef<HTMLInputElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);

  /**
   * Put focus back once the response has landed and React has committed the new tree.
   *
   * GATED ON `pending`, which is the part that is easy to get wrong. A successful save
   * starts a transition, and during it this instance is still mounted while the tree
   * that replaces it is being built. Placing focus then would land it on a node about to
   * be thrown away, and clearing the variable would leave the instance that actually
   * needs it with nothing to read. So nothing happens until both flags are down, which
   * on the success path is the first render of the rebuilt form.
   */
  useEffect(() => {
    if (pending) return;
    const wanted = focusAfterRebuild;
    if (!wanted) return;
    focusAfterRebuild = null;
    // Only when the blur left focus nowhere. A learner who tabbed away mid-request is
    // where they want to be, and yanking them back is worse than the problem being
    // fixed. Same guard, and the same reason, as ReteachConcept's recovered branch.
    if (document.activeElement !== document.body) return;
    const target =
      wanted === "day" ? dayRef.current : wanted === "label" ? labelRef.current : submitRef.current;
    target?.focus();
  }, [pending, error]);

  /** Where the learner already is, so a save returns them to it rather than relocating them. */
  function activeField(): DeadlineFocus {
    const active = document.activeElement;
    if (active === dayRef.current) return "day";
    if (active === labelRef.current) return "label";
    return "submit";
  }

  async function run(action: () => Promise<unknown>, after: DeadlineFocus) {
    focusAfterRebuild = after;
    setSaving(true);
    setError(null);
    try {
      await action();
      // A state update after await is not automatically part of a transition.
      startTransition(() => router.refresh());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!day) return;
        void run(() => setCourseDeadline(plan.course_id, day, label.trim()), activeField());
      }}
      className="mt-4 rounded-lg border border-zinc-200 px-5 py-4 dark:border-zinc-800"
    >
      <div className="flex flex-wrap gap-4">
        <div className="min-w-[10rem] flex-1">
          <label
            htmlFor="deadline-day"
            className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300"
          >
            Date
          </label>
          {/* Never disabled, mid-request included. Disabling the focused control blurs
              it to the body, and pressing Enter here again is already refused by the
              pending flag in `run`. Same rule the tutor's composer follows. */}
          <input
            id="deadline-day"
            ref={dayRef}
            type="date"
            value={day}
            onChange={(event) => setDay(event.target.value)}
            className={`mt-1 ${FIELD_CLASS}`}
          />
        </div>
        <div className="min-w-[10rem] flex-1">
          <label
            htmlFor="deadline-label"
            className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300"
          >
            What to call it{" "}
            <span className="font-normal text-zinc-500 dark:text-zinc-400">(optional)</span>
          </label>
          <input
            id="deadline-label"
            ref={labelRef}
            type="text"
            value={label}
            maxLength={200}
            placeholder="Midterm"
            onChange={(event) => setLabel(event.target.value)}
            className={`mt-1 ${FIELD_CLASS}`}
          />
        </div>
      </div>

      <p className="mt-2.5 text-xs text-zinc-500 dark:text-zinc-400">
        The name is what shows up in your calendar. The date is the day you need to know the
        material by, so the day itself is not counted as study time.
      </p>

      <div className="mt-3.5 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          ref={submitRef}
          disabled={pending || !day}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          {saving ? "Saving…" : hasDeadline ? "Change deadline" : "Set deadline"}
        </button>
        {hasDeadline && (
          // Focus goes to the date field rather than back here, because on the path that
          // succeeds this button does not exist afterwards: the deadline is gone, so
          // `hasDeadline` is false and the whole control is unmounted. The date field is
          // the nearest thing the learner would act on next.
          <button
            type="button"
            disabled={pending}
            onClick={() => void run(() => clearCourseDeadline(plan.course_id), "day")}
            className="rounded-lg border border-zinc-300 px-4 py-2 text-[13px] font-medium transition-colors hover:border-zinc-500 disabled:opacity-60 dark:border-zinc-700 dark:hover:border-zinc-500"
          >
            Clear deadline
          </button>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-3 text-[13px] text-red-700 dark:text-red-400">
          {error}
        </p>
      )}
    </form>
  );
}
