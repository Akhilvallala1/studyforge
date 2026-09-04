"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { ApiError, clearCourseDeadline, setCourseDeadline } from "@/lib/api";
import type { CoursePlan } from "@/lib/types";

/*
 * No `focus:outline-none` here, where the raw version had one: globals.css's app-wide
 * `:focus-visible` rule is unlayered, and Tailwind wraps its own utilities in
 * `@layer utilities`, so an unlayered rule always wins over a layered one regardless of
 * either side's specificity. Dropping the utility changes no rendered pixel; it only
 * stops shipping a rule that could never have won.
 */
const FIELD_CLASS =
  "w-full rounded-control border border-line-strong bg-transparent px-3 py-2 text-ui text-ink " +
  "transition-colors duration-fast ease-standard hover:border-line-hover focus:border-line-hover";

/** Which control should hold focus once the request has landed and the tree is committed. */
type DeadlineFocus = "day" | "label" | "submit";

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
  const pendingFocus = useRef<DeadlineFocus | null>(null);

  /*
   * Reseed the inputs when the SAVED deadline changes, so clearing a date empties them
   * rather than leaving the learner staring at the value they just removed.
   *
   * This is the behaviour the page used to get by keying this component on
   * `plan.deadline`, and it is deliberately no longer implemented that way. A key
   * implements a reset by DESTROYING the component, which meant every successful save
   * unmounted the instance that had just made the request, taking its refs with it and
   * forcing the focus intent into a module variable that outlived every instance that
   * could clear it. Adjusting state during render is React's own answer to exactly this
   * and gives the identical reset with the component left alive, so a plain ref works
   * and dies with its own instance.
   *
   * COMPARES PROPS TO PROPS, never props to input state. Marking a day off refreshes
   * this route too, so this component is re-rendered with an unchanged deadline while
   * the learner may be part-way through typing a new one. Only a change in what the
   * SERVER holds resets anything.
   */
  const [saved, setSaved] = useState({ day: plan.deadline, label: plan.deadline_label });
  if (saved.day !== plan.deadline || saved.label !== plan.deadline_label) {
    setSaved({ day: plan.deadline, label: plan.deadline_label });
    setDay(plan.deadline ?? "");
    setLabel(plan.deadline_label ?? "");
    // The deadline moved, so whatever this said is about a request that is now history.
    setError(null);
  }

  /**
   * Put focus back once the response has landed and React has committed the new tree.
   *
   * GATED ON `pending`, which is the part that is easy to get wrong. A successful save
   * starts a transition, and this instance keeps rendering while the tree it is being
   * updated into is built. Acting then would place focus against a half-updated screen
   * and clear the intent before the render that needs it. So nothing happens until both
   * flags are down.
   */
  useEffect(() => {
    if (pending) return;
    const wanted = pendingFocus.current;
    if (!wanted) return;
    pendingFocus.current = null;
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
    // The explicit re-entry check the inputs' comment relies on. The disabled submit
    // button already stops a second Enter, but a guarantee stated in a comment should
    // not depend on the reader reconstructing that argument, and should survive the
    // refactor that changes how the button is disabled. Same shape as ConceptTutor.send.
    if (pending) return;
    pendingFocus.current = after;
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
      className="mt-4 rounded-surface border border-line px-5 py-4"
    >
      <div className="flex flex-wrap gap-4">
        <div className="min-w-[10rem] flex-1">
          <label htmlFor="deadline-day" className="block text-small font-medium text-ink-muted">
            Date
          </label>
          {/* Never disabled, mid-request included. Disabling the focused control blurs
              it to the body, and a second submit from here is refused by the `pending`
              check at the top of `run`. Same rule the tutor's composer follows. */}
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
          <label htmlFor="deadline-label" className="block text-small font-medium text-ink-muted">
            What to call it <span className="font-normal text-ink-subtle">(optional)</span>
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

      <p className="mt-2.5 text-xs text-ink-muted">
        The name is what shows up in your calendar. The date is the day you need to know the
        material by, so the day itself is not counted as study time.
      </p>

      <div className="mt-3.5 flex flex-wrap items-center gap-3">
        <Button type="submit" ref={submitRef} disabled={pending || !day} size="sm">
          {saving ? "Saving…" : hasDeadline ? "Change deadline" : "Set deadline"}
        </Button>
        {hasDeadline && (
          // Focus goes to the date field rather than back here, because on the path that
          // succeeds this button does not exist afterwards: the deadline is gone, so
          // `hasDeadline` is false and the whole control is unmounted. The date field is
          // the nearest thing the learner would act on next.
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={pending}
            onClick={() => void run(() => clearCourseDeadline(plan.course_id), "day")}
          >
            Clear deadline
          </Button>
        )}
      </div>

      {error && (
        <Callout tone="danger" role="alert" className="mt-3">
          {error}
        </Callout>
      )}
    </form>
  );
}
