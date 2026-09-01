"use client";

import { useState, useTransition } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { ApiError, addDayOff, removeDayOff } from "@/lib/api";
import { formatDayKey } from "@/lib/copy";
import type { DayOff } from "@/lib/types";

const FIELD_CLASS =
  "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 " +
  "focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100";

/**
 * Marking and unmarking the days the learner will not be studying.
 *
 * DAYS OFF ARE GLOBAL. The table has no course id, so a day marked here disappears from
 * the study days counted for every course. That is stated in the copy rather than left
 * to be discovered, because the discovery is confusing: mark two days from this course,
 * open another one, and its required rate has moved with nothing on that screen to
 * explain why. There is no settings page in this app for the control to live on
 * instead, so it lives here and says what it is.
 *
 * A DAY OFF MOVES NO REVIEW. It shrinks the denominator the weekly rate is computed
 * over, which pushes that rate up. It does not defer a card, and the copy must never
 * suggest a learner can take a day off from their reviews by marking one here.
 *
 * MARKING A DAY TWICE IS A SUCCESS, not a conflict: the server returns the existing row
 * unchanged and does not overwrite its note. Since the response looks identical either
 * way, this component decides which happened by checking the list it already has, which
 * is the only place that fact exists.
 */
export function DaysOffControl({ daysOff }: { daysOff: DayOff[] }) {
  const router = useRouter();
  const [day, setDay] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const pending = saving || refreshing;

  /** Returns whether the call succeeded, so a caller can clear its inputs only then. */
  async function run(action: () => Promise<unknown>, afterMessage: string | null) {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(afterMessage);
      // A state update after await is not automatically part of a transition.
      startTransition(() => router.refresh());
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!day) return;
    const already = daysOff.some((entry) => entry.day === day);
    const ok = await run(
      () => addDayOff(day, note.trim()),
      already
        ? `${formatDayKey(day)} was already marked off, so nothing changed. Its note is left as it was.`
        : null,
    );
    // Keep what the learner typed when the call failed, so they can simply press again.
    if (ok && !already) setNote("");
  }

  return (
    <div className="mt-4 rounded-lg border border-zinc-200 px-5 py-4 dark:border-zinc-800">
      <form onSubmit={(event) => void submit(event)}>
        <div className="flex flex-wrap gap-4">
          <div className="min-w-[10rem] flex-1">
            <label
              htmlFor="day-off-day"
              className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300"
            >
              Date
            </label>
            <input
              id="day-off-day"
              type="date"
              value={day}
              onChange={(event) => setDay(event.target.value)}
              disabled={pending}
              className={`mt-1 ${FIELD_CLASS}`}
            />
          </div>
          <div className="min-w-[10rem] flex-1">
            <label
              htmlFor="day-off-note"
              className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300"
            >
              Why{" "}
              <span className="font-normal text-zinc-500 dark:text-zinc-400">(optional)</span>
            </label>
            <input
              id="day-off-note"
              type="text"
              value={note}
              maxLength={200}
              placeholder="Travelling"
              onChange={(event) => setNote(event.target.value)}
              disabled={pending}
              className={`mt-1 ${FIELD_CLASS}`}
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={pending || !day}
          className="mt-3.5 rounded-lg border border-zinc-300 px-4 py-2 text-[13px] font-medium transition-colors hover:border-zinc-500 disabled:opacity-60 dark:border-zinc-700 dark:hover:border-zinc-500"
        >
          {saving ? "Saving…" : "Mark day off"}
        </button>
      </form>

      {error && (
        <p role="alert" className="mt-3 text-[13px] text-red-700 dark:text-red-400">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="mt-3 text-[13px] text-zinc-600 dark:text-zinc-400">
          {notice}
        </p>
      )}

      {daysOff.length === 0 ? (
        <p className="mt-4 border-t border-zinc-200 pt-4 text-[13px] text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
          No days marked off. Every day between now and a deadline counts as a day you could
          study on.
        </p>
      ) : (
        <ul className="mt-4 flex flex-col divide-y divide-zinc-200 border-t border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {daysOff.map((entry) => (
            <li key={entry.day} className="flex items-center justify-between gap-4 py-2.5">
              <div className="min-w-0">
                <div className="text-[13px]">{formatDayKey(entry.day)}</div>
                {entry.note && (
                  <div className="truncate text-xs text-zinc-500 dark:text-zinc-400">
                    {entry.note}
                  </div>
                )}
              </div>
              <button
                type="button"
                disabled={pending}
                onClick={() =>
                  void run(
                    () => removeDayOff(entry.day),
                    `${formatDayKey(entry.day)} counts as a study day again.`,
                  )
                }
                aria-label={`Unmark ${formatDayKey(entry.day)} as a day off`}
                className="shrink-0 rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium transition-colors hover:border-zinc-500 disabled:opacity-60 dark:border-zinc-700 dark:hover:border-zinc-500"
              >
                Unmark
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
