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
            Hand-rolled rather than Button: none of its variants is a success-tinted
            fill (primary's `fill` token is deliberately neutral, not accent and not a
            status colour; see Button.tsx and globals.css's --sf-accent comment), and
            this is the one control in the app that needs one.

            Hover uses --sf-success-surface-hover, a token added for it, rather than the
            tone's existing boundary colour. An earlier draft used that boundary colour
            as a fill, on the theory that it is just the next step in the same family,
            the way surface/surface-sunken and line/line-hover are. The analogy does not
            hold: each of those pairs stays inside one role, two fills or two borders,
            where this would have been a boundary colour used as a fill, which nothing
            else in the codebase does. It also measured badly. Emerald-300 is darker
            than the emerald-200 the raw version hovered to, so `text-success` on it
            came out at 3.57:1 light and 3.91:1 dark, under the 4.5:1 this label needs
            as normal-size text and down from 6.02 and 6.41 before the migration. The
            new token is emerald-100 light and emerald-900 dark and measures 4.78 and
            4.95. --sf-danger-fill-hover already existed for the same reason, so this
            follows the family's own pattern rather than inventing one.

            The Undo hint reveals to full opacity rather than to 80%. It is invisible
            at rest, so it is only ever read while revealed, and 80% over the hover fill
            composites to 3.35:1 light and 3.80:1 dark. Full opacity puts it at the
            label's own 4.78 and 4.95, which also closes a 3.94:1 light-mode failure that
            predates this PR. "Revealed" is not a synonym for "hovered", though: the
            group-focus-visible half of this shows the hint over the RESTING fill, where
            it measures 5.15:1 light and 7.70:1 dark. Both paths clear 4.5:1, which is the
            point, and the keyboard one was never the tighter of the two.

            What that trades away is hover strength: the fill step from resting to hover
            is 1.08:1 light and 1.56:1 dark, against 1.44 and 1.97 for the boundary
            colour it rejected. That is the band every other hover in the app sits in:
            Button's tinted variant steps 1.05 and 1.30 on this same success surface, and
            its ghost variant 1.04 in light mode. The raw version this replaced stepped
            1.13 and 1.56, so a weak hover is not something this change introduced.

            All figures are from the hexes Tailwind emits, not from globals.css and not
            from converting the OKLCH by hand: the emitted light fill is #d0fae5, not the
            v3 hex the palette name suggests, and emerald-800 emits #005f46 where a
            straight OKLCH conversion gives #006045. That last one is why three figures
            here were previously 0.03 low.
          */
          className="group rounded-control bg-success-surface px-4 py-2 text-ui font-medium text-success transition-colors duration-fast ease-standard hover:bg-success-surface-hover disabled:opacity-60"
        >
          {pending ? (
            "Reopening…"
          ) : (
            <>
              ✓ Completed
              <span className="ml-2 text-small font-normal opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
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
