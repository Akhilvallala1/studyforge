"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ApiError, completeLesson, uncompleteLesson } from "@/lib/api";

export function MarkCompleteButton({
  lessonId,
  completed,
}: {
  lessonId: number;
  completed: boolean;
}) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const pending = saving || refreshing;

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
    <div className="flex shrink-0 flex-col items-end gap-1">
      {completed ? (
        <button
          type="button"
          onClick={() => void run(() => uncompleteLesson(lessonId))}
          disabled={pending}
          aria-label="Mark this lesson as not complete"
          className="group rounded-lg bg-emerald-100 px-4 py-2 text-sm font-medium text-emerald-800 transition-colors hover:bg-emerald-200 disabled:opacity-60 dark:bg-emerald-950 dark:text-emerald-300 dark:hover:bg-emerald-900"
        >
          {pending ? (
            "Reopening…"
          ) : (
            <>
              ✓ Completed
              <span className="ml-2 text-xs font-normal opacity-0 transition-opacity group-hover:opacity-80 group-focus-visible:opacity-80">
                Undo
              </span>
            </>
          )}
        </button>
      ) : (
        <button
          type="button"
          onClick={() => void run(() => completeLesson(lessonId))}
          disabled={pending}
          className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium transition-colors hover:border-zinc-500 disabled:opacity-60 dark:border-zinc-700 dark:hover:border-zinc-500"
        >
          {pending ? "Saving…" : "Mark complete"}
        </button>
      )}
      {error && <p className="text-xs text-red-700 dark:text-red-400">{error}</p>}
    </div>
  );
}
