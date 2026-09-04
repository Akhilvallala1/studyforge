"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { ApiError, addDayOff, removeDayOff } from "@/lib/api";
import { formatDayKey } from "@/lib/copy";
import { splitDaysOff } from "@/lib/plan";
import type { DayOff } from "@/lib/types";

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

/**
 * Which control should hold focus once the request has landed.
 *
 * "day" is where Unmark sends it, because the row that button lived on is gone by then:
 * the refresh removes it from the list, so there is no control to return to. The form's
 * date field is the nearest thing the learner would act on next.
 */
type DayOffFocus = "day" | "submit";

/**
 * One row, identical in both lists, which is why it is genuinely shared rather than
 * merely claimed to be.
 *
 * AT MODULE SCOPE ON PURPOSE. Declared inside DaysOffControl it was a new function on
 * every parent render, so React compared element types by reference, found them
 * different, and unmounted and remounted every row's DOM on each keystroke in the date
 * or note field. `key` cannot prevent that: the type mismatch is settled before keys are
 * consulted. Nothing visible broke, because rows hold no state, the disclosure is a
 * sibling rather than a child so its open state survived, and the focus target after an
 * unmark is the form's date input, which sits outside the churn entirely. The cost was
 * all latent: the first row-local state anyone adds, an inline note edit or a confirm
 * step before unmarking, would have reset itself on every keystroke somewhere else on
 * the form, and the symptom would not have pointed here.
 */
function DayOffRow({
  entry,
  pending,
  onUnmark,
}: {
  entry: DayOff;
  pending: boolean;
  onUnmark: (entry: DayOff) => void;
}) {
  return (
    <li className="flex items-center justify-between gap-4 py-2.5">
      <div className="min-w-0">
        <div className="text-[13px]">{formatDayKey(entry.day)}</div>
        {entry.note && <div className="truncate text-xs text-ink-muted">{entry.note}</div>}
      </div>
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled={pending}
        onClick={() => onUnmark(entry)}
        aria-label={`Unmark ${formatDayKey(entry.day)} as a day off`}
        className="shrink-0"
      >
        Unmark
      </Button>
    </li>
  );
}

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
export function DaysOffControl({
  daysOff,
  today,
}: {
  /** Every day off the server holds, which is what the idempotence check has to consult. */
  daysOff: DayOff[];
  /** The server's study day, or null when this course has no deadline to derive it from. */
  today: string | null;
}) {
  const router = useRouter();
  const [day, setDay] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const pending = saving || refreshing;
  const dayRef = useRef<HTMLInputElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const pendingFocus = useRef<DayOffFocus | null>(null);

  /**
   * Put focus back once the response has landed and React has committed the new tree.
   *
   * A ref is enough here, unlike the deadline form: nothing keys this component, so it
   * survives its own mutations and the ref survives with it. The `pending` gate is still
   * needed for the same reason, though. Unmarking removes a row from a list that only
   * changes when the refresh commits, so acting before then would place focus while the
   * row the learner was standing on is still there.
   */
  useEffect(() => {
    if (pending) return;
    const wanted = pendingFocus.current;
    if (!wanted) return;
    pendingFocus.current = null;
    // Only when the blur left focus nowhere. A learner who moved on during the request
    // is where they want to be, and yanking them back is worse than the problem.
    if (document.activeElement !== document.body) return;
    const target = wanted === "day" ? dayRef.current : submitRef.current;
    target?.focus();
  }, [pending, error, notice]);

  /** Returns whether the call succeeded, so a caller can clear its inputs only then. */
  async function run(
    action: () => Promise<unknown>,
    afterMessage: string | null,
    after: DayOffFocus,
  ) {
    // The explicit re-entry check the inputs' comment relies on. The disabled submit
    // button already stops a second Enter, but a guarantee stated in a comment should
    // not depend on the reader reconstructing that argument, and should survive the
    // refactor that changes how the button is disabled. Same shape as ConceptTutor.send.
    if (pending) return false;
    pendingFocus.current = after;
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
      "submit",
    );
    // Keep what the learner typed when the call failed, so they can simply press again.
    if (ok && !already) setNote("");
  }

  const { upcoming, past } = splitDaysOff(daysOff, today);

  /** Focus goes to the date field, not back to the row: the row is gone by then. */
  function unmark(entry: DayOff) {
    void run(
      () => removeDayOff(entry.day),
      `${formatDayKey(entry.day)} counts as a study day again.`,
      "day",
    );
  }

  return (
    <div className="mt-4 rounded-surface border border-line px-5 py-4">
      <form onSubmit={(event) => void submit(event)}>
        <div className="flex flex-wrap gap-4">
          <div className="min-w-[10rem] flex-1">
            <label htmlFor="day-off-day" className="block text-small font-medium text-ink-muted">
              Date
            </label>
            {/* Never disabled, mid-request included. Disabling the focused control
                blurs it to the body, and a second submit from here is refused by the
                `pending` check at the top of `run`. Same rule the tutor's composer
                follows. */}
            <input
              id="day-off-day"
              ref={dayRef}
              type="date"
              value={day}
              onChange={(event) => setDay(event.target.value)}
              className={`mt-1 ${FIELD_CLASS}`}
            />
          </div>
          <div className="min-w-[10rem] flex-1">
            <label htmlFor="day-off-note" className="block text-small font-medium text-ink-muted">
              Why <span className="font-normal text-ink-subtle">(optional)</span>
            </label>
            <input
              id="day-off-note"
              type="text"
              value={note}
              maxLength={200}
              placeholder="Travelling"
              onChange={(event) => setNote(event.target.value)}
              className={`mt-1 ${FIELD_CLASS}`}
            />
          </div>
        </div>
        {/*
          `secondary`, and one size up from the Unmark buttons in the list above. This
          submit was an outline button on main, matching those siblings, and a filled
          primary here would rank marking a day off above the page's real primary
          actions. Dropping `size="sm"` keeps it a visible step larger than Unmark,
          which is the hierarchy the raw classes had, rather than pixel-identical to it.
        */}
        <Button
          type="submit"
          ref={submitRef}
          variant="secondary"
          disabled={pending || !day}
          className="mt-3.5"
        >
          {saving ? "Saving…" : "Mark day off"}
        </Button>
      </form>

      {error && (
        <Callout tone="danger" role="alert" className="mt-3">
          {error}
        </Callout>
      )}
      {notice && (
        <p role="status" className="mt-3 text-small text-ink-muted">
          {notice}
        </p>
      )}

      {daysOff.length === 0 ? (
        <p className="mt-4 border-t border-line pt-4 text-small text-ink-muted">
          No days marked off. Every day between now and a deadline counts as a day you could
          study on.
        </p>
      ) : (
        <div className="mt-4 border-t border-line">
          {upcoming.length === 0 ? (
            <p className="pt-4 text-small text-ink-muted">No days off coming up.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-line">
              {upcoming.map((entry) => (
                <DayOffRow key={entry.day} entry={entry} pending={pending} onUnmark={unmark} />
              ))}
            </ul>
          )}

          {past.length > 0 && (
            /*
             * COLLAPSED, NEVER DROPPED. A day the learner marked stays reachable; it is
             * only out of the way, because a list that grows without bound is what made
             * the count above hard to read in the first place.
             *
             * A native <details>, deliberately, rather than a button and a piece of state.
             * The browser makes the summary focusable, toggles it on Enter and Space, and
             * exposes its expanded state to a screen reader without any of that being
             * this component's code to get wrong. It also cannot lose focus when it
             * toggles, since nothing unmounts: the summary the learner is standing on is
             * the same element before and after.
             */
            <details className="mt-1 border-t border-line pt-2.5">
              <summary className="cursor-pointer text-xs text-ink-muted hover:text-ink">
                {past.length === 1 ? "1 earlier day off" : `${past.length} earlier days off`}
              </summary>
              <ul className="mt-1 flex flex-col divide-y divide-line">
                {past.map((entry) => (
                  <DayOffRow key={entry.day} entry={entry} pending={pending} onUnmark={unmark} />
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
