"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ApiError, clearCourseDeadline, setCourseDeadline } from "@/lib/api";
import type { CoursePlan } from "@/lib/types";

const FIELD_CLASS =
  "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 " +
  "focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100";

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

  async function run(action: () => Promise<unknown>) {
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
        void run(() => setCourseDeadline(plan.course_id, day, label.trim()));
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
          <input
            id="deadline-day"
            type="date"
            value={day}
            onChange={(event) => setDay(event.target.value)}
            disabled={pending}
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
            type="text"
            value={label}
            maxLength={200}
            placeholder="Midterm"
            onChange={(event) => setLabel(event.target.value)}
            disabled={pending}
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
          disabled={pending || !day}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          {saving ? "Saving…" : hasDeadline ? "Change deadline" : "Set deadline"}
        </button>
        {hasDeadline && (
          <button
            type="button"
            disabled={pending}
            onClick={() => void run(() => clearCourseDeadline(plan.course_id))}
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
