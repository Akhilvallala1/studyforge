"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
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
  const buttonRef = useRef<HTMLButtonElement>(null);
  const toggledRef = useRef(false);

  // router.refresh() drops focus to the body even though React reuses this node, so a
  // keyboard user who toggles by mistake cannot immediately toggle back. Restore focus
  // once the refreshed state lands, but only after an actual toggle: focusing on first
  // render would steal focus from wherever the reader actually is.
  useEffect(() => {
    if (!toggledRef.current || pending) return;
    toggledRef.current = false;
    buttonRef.current?.focus();
  }, [completed, pending]);

  async function run(action: () => Promise<unknown>) {
    setSaving(true);
    setError(null);
    toggledRef.current = true;
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
          ref={buttonRef}
          onClick={() => void run(() => uncompleteLesson(lessonId))}
          disabled={pending}
          aria-label="Mark this lesson as not complete"
          /*
            Hand-rolled rather than Button: none of its four variants are a success-
            tinted fill (primary's `fill` token is deliberately neutral, not accent or
            a status colour; see Button.tsx and globals.css's --sf-accent comment), and
            this is the one control in the app that needs one. `success-border`, one
            step past `success-surface` in the same family, stands in for the fill-hover
            token neither this tone nor Badge's has: the same "next step in the same
            family" relationship `surface`/`surface-sunken` and `line`/`line-hover` use
            elsewhere for exactly this purpose.
          */
          className="group rounded-control bg-success-surface px-4 py-2 text-ui font-medium text-success transition-colors duration-fast ease-standard hover:bg-success-border disabled:opacity-60"
        >
          {pending ? (
            "Reopening…"
          ) : (
            <>
              ✓ Completed
              <span className="ml-2 text-small font-normal opacity-0 transition-opacity group-hover:opacity-80 group-focus-visible:opacity-80">
                Undo
              </span>
            </>
          )}
        </button>
      ) : (
        <Button
          ref={buttonRef}
          variant="secondary"
          onClick={() => void run(() => completeLesson(lessonId))}
          disabled={pending}
        >
          {pending ? "Saving…" : "Mark complete"}
        </Button>
      )}
      {error && <p className="text-small text-danger">{error}</p>}
    </div>
  );
}
