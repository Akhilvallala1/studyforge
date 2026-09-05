"use client";

import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import {
  ApiError,
  SourceGenerationError,
  generateFromSources,
  getGenerationLimits,
} from "@/lib/api";
import { formatBytes, formatUsd } from "@/lib/format";
import type { GenerateResult, SourceFailure, SourceInput, SourceLimits } from "@/lib/types";

type RowKind = "text" | "url";

interface SourceRow {
  id: string;
  kind: RowKind;
  value: string;
  /** The optional label sent as `ref`. Blank means "let the server default it". */
  ref: string;
  error: string | null;
}

interface FileRow {
  id: string;
  file: File;
  error: string | null;
}

/** Why a candidate PDF from a file or folder pick was not turned into a row. */
type SkipReason = "not-pdf" | "empty" | "over-source-cap" | "over-byte-cap";

interface SkippedFile {
  name: string;
  reason: SkipReason;
}

interface IntakeNote {
  added: number;
  skipped: SkippedFile[];
}

function skipReasonLabel(reason: SkipReason): string {
  switch (reason) {
    case "not-pdf":
      return "not a PDF";
    case "empty":
      return "empty file";
    case "over-source-cap":
      return "would go over the source limit";
    case "over-byte-cap":
      return "would go over the upload size limit";
  }
}

/** A count-prefixed reason clause for the aggregate announcement, e.g. "2 not PDFs". */
function skipReasonSummaryLabel(reason: SkipReason, count: number): string {
  switch (reason) {
    case "not-pdf":
      return `${count} ${count === 1 ? "not a PDF" : "not PDFs"}`;
    case "empty":
      return `${count} ${count === 1 ? "empty file" : "empty files"}`;
    case "over-source-cap":
      return `${count} over the source limit`;
    case "over-byte-cap":
      return `${count} over the upload size limit`;
  }
}

/**
 * The reasons a batch of skipped files was skipped, folded into one clause so a
 * screen-reader learner gets them from the announced text itself rather than only from
 * the closed-by-default breakdown below it.
 */
function summarizeSkips(skipped: SkippedFile[]): string {
  const counts = new Map<SkipReason, number>();
  for (const entry of skipped) {
    counts.set(entry.reason, (counts.get(entry.reason) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([reason, count]) => skipReasonSummaryLabel(reason, count))
    .join(", ");
}

function isPdfFile(file: File): boolean {
  if (file.type === "application/pdf") return true;
  return file.name.toLowerCase().endsWith(".pdf");
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

let nextRowId = 0;
/** A stable id for a row's lifetime, never re-derived from its content or position. */
function newRowId(prefix: string): string {
  nextRowId += 1;
  return `${prefix}-${nextRowId}`;
}

/*
 * No `outline-none` here. What main carried was the bare, unconditional `outline-none`,
 * not `focus:outline-none`. The bare form is the broader of the two: it emits
 * `outline-style: none` in every state, not only on focus. It was inert either way,
 * because globals.css's app-wide `:focus-visible` rule is unlayered and an unlayered
 * declaration always beats Tailwind's own layered utilities whatever the specificity.
 * DaysOffControl's and DeadlineForm's FIELD_CLASS already state that reasoning.
 *
 * Removing it changes no rendered pixel. Scope that sentence to the removal, not to the
 * constant: this string is NOT pixel-identical to main's, because it newly carries
 * `transition-colors duration-fast ease-standard`, which main's two input constants did
 * not have. So the hover and focus border-colour change now animates over 120ms instead
 * of snapping. The focus RING is unaffected either way: outline-color is in the built
 * transition-colors property list, but outline-style is not, so the ring still appears at
 * full width the instant :focus-visible matches. The added utilities match the FIELD_CLASS
 * string DaysOffControl and DeadlineForm already carry on main, and globals.css zeroes
 * transition-duration under prefers-reduced-motion.
 */
const inputClasses =
  "mt-2 w-full rounded-control border border-line-strong bg-transparent p-2.5 text-ui text-ink " +
  "placeholder:text-ink-subtle transition-colors duration-fast ease-standard " +
  "hover:border-line-hover focus:border-line-hover disabled:opacity-60";

/** The smaller "Label (optional)" field nested inside each source row. */
const labelInputClasses =
  "mt-1 w-full rounded-control border border-line-strong bg-transparent px-2.5 py-1.5 text-small text-ink " +
  "placeholder:text-ink-subtle transition-colors duration-fast ease-standard " +
  "hover:border-line-hover focus:border-line-hover disabled:opacity-60";

export function GenerateForm() {
  const router = useRouter();
  const [rows, setRows] = useState<SourceRow[]>([]);
  const [fileRows, setFileRows] = useState<FileRow[]>([]);
  const [limits, setLimits] = useState<SourceLimits | null>(null);
  const [intakeNote, setIntakeNote] = useState<IntakeNote | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  // Bumped alongside every summaryError announcement, including a repeat of the exact
  // same message: a state update to an unchanged string is a no-op React bails out of,
  // which would otherwise leave a second identical failure silently un-announced and
  // focus stuck on the submit button. The focus effect keys off this, not summaryError.
  const [summaryErrorSeq, setSummaryErrorSeq] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [success, setSuccess] = useState<GenerateResult | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const summaryRef = useRef<HTMLDivElement>(null);
  const focusSummaryNext = useRef(false);
  // Captured at the top of handleSubmit, before the submit button disables itself, so
  // the summary-focus effect below can tell "nothing has taken focus away since this
  // submit" from "the learner tabbed off somewhere during the request" once the result
  // (which can take 1 to 3 minutes) lands.
  const focusAtSend = useRef<Element | null>(null);
  const addTextButtonRef = useRef<HTMLButtonElement>(null);
  // Live DOM handles for controls that need to be re-focused after a state change
  // unmounts or repositions whatever previously held focus: a row's main input (added)
  // and a row's Remove button (the successor after a removal). Keyed by row id, which
  // outlives any one render, unlike an index into rows/fileRows.
  const inputRefs = useRef(new Map<string, HTMLTextAreaElement | HTMLInputElement>());
  const removeButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const focusInputIdNext = useRef<string | null>(null);
  const focusRemoveIdNext = useRef<string | null>(null);
  const focusAddTextNext = useRef(false);

  function registerInputRef(id: string, el: HTMLTextAreaElement | HTMLInputElement | null) {
    if (el) inputRefs.current.set(id, el);
    else inputRefs.current.delete(id);
  }

  function registerRemoveButtonRef(id: string, el: HTMLButtonElement | null) {
    if (el) removeButtonRefs.current.set(id, el);
    else removeButtonRefs.current.delete(id);
  }

  // `webkitdirectory` has no React prop and is not part of HTMLInputElement's type, so it
  // is set imperatively as a plain attribute here rather than smuggled onto the JSX
  // element with an `any` cast or a directive suppressing the type error that attribute
  // would otherwise raise. Chromium and Firefox both honour it as a plain attribute;
  // browsers that don't just show their ordinary file picker instead, which still lets
  // someone pick PDFs one at a time.
  useEffect(() => {
    const el = folderInputRef.current;
    if (!el) return;
    el.setAttribute("webkitdirectory", "");
    el.setAttribute("directory", "");
  }, []);

  useEffect(() => {
    let cancelled = false;
    getGenerationLimits()
      .then((result) => {
        if (!cancelled) setLimits(result);
      })
      .catch(() => {
        // Limits are an optimistic guardrail, not a gate. If the server cannot be asked,
        // the add controls just stay enabled and the server's own refusal is the backstop.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!submitting) return;
    const started = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [submitting]);

  // Move to the summary alert whenever a submit attempt produced a fresh one, so a
  // keyboard or screen-reader learner is not left on the just-re-enabled submit button
  // with no indication anything happened. Keyed on the seq, not the message itself, so
  // two submits in a row that fail the same way both move focus.
  //
  // Only when the learner has not moved since they sent. Two things satisfy that and
  // they are not the same thing: the body, which is where focus lands once the submit
  // button unmounts for the spinner while the request is in flight, and focusAtSend,
  // wherever focus actually was the moment they submitted. Testing only the body is not
  // merely weaker, it is wrong: the empty-list and blank-row checks return before
  // anything unmounts, so on those paths the button still holds focus and a body-only
  // test would never open, which is the everyday failure rather than a corner. Testing
  // both also covers a learner who tabbed off during the 1 to 3 minutes this form's own
  // copy quotes; they match neither and are left where they went, told by the alert's
  // assertive live region rather than yanked to it.
  useEffect(() => {
    if (!focusSummaryNext.current) return;
    focusSummaryNext.current = false;
    const active = document.activeElement;
    if (active === document.body || active === focusAtSend.current) summaryRef.current?.focus();
  }, [summaryErrorSeq]);

  // A freshly added row's input takes focus, the same way opening any new field would.
  // Guarded by the intent ref so this does not fire on every keystroke that produces a
  // new `rows` array, only on the commit that actually added a row.
  useEffect(() => {
    const id = focusInputIdNext.current;
    if (!id) return;
    focusInputIdNext.current = null;
    inputRefs.current.get(id)?.focus();
  }, [rows]);

  // After a row is removed, focus follows it: to the row that slid into its place, or
  // the previous row if it was last, or the text-adding button if the list emptied out.
  // Keyed on both arrays, since the successor of a removed text row can be a PDF row.
  useEffect(() => {
    if (focusAddTextNext.current) {
      focusAddTextNext.current = false;
      addTextButtonRef.current?.focus();
      return;
    }
    const id = focusRemoveIdNext.current;
    if (!id) return;
    focusRemoveIdNext.current = null;
    removeButtonRefs.current.get(id)?.focus();
  }, [rows, fileRows]);

  const totalSources = rows.length + fileRows.length;
  // Text rows only, never URL rows: a URL row's `value` is the address, not the page's
  // content, so counting it toward this figure would read as "40 characters" for a link
  // to an 80,000-character article. There is no fraction to show against max_total_chars
  // here, on purpose - the total the server enforces also includes whatever URLs and PDFs
  // extract to, and that is unknowable before the request is sent.
  const pastedChars = rows.reduce((sum, row) => (row.kind === "text" ? sum + row.value.length : sum), 0);
  const uploadedBytes = fileRows.reduce((sum, row) => sum + row.file.size, 0);
  const atSourceCap = limits !== null && totalSources >= limits.max_sources;
  const locked = submitting || success !== null;

  function addRow(kind: RowKind) {
    const id = newRowId(kind);
    focusInputIdNext.current = id;
    setRows((prev) => [...prev, { id, kind, value: "", ref: "", error: null }]);
  }

  function updateRow(id: string, patch: Partial<Pick<SourceRow, "value" | "ref">>) {
    // Editing a row clears only that row's own failure, and only that: no other row's
    // error, and nothing beyond the one field being typed into.
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch, error: null } : row)));
  }

  /**
   * Arm the post-removal focus target before the row is actually gone, since finding a
   * "next" or "previous" row only makes sense against the list as it stands right now.
   * `rows` and `fileRows` render as one sequence, text/url rows first, so the successor
   * has to be computed against them combined: doing it against just the array the id
   * came out of loses the PDF rows entirely when the last text row is the one removed.
   */
  function armFocusAfterRemoval(id: string) {
    const combined = [...rows, ...fileRows];
    const index = combined.findIndex((row) => row.id === id);
    if (index === -1) return;
    const successor = combined[index + 1] ?? combined[index - 1];
    if (successor) {
      focusRemoveIdNext.current = successor.id;
    } else {
      focusAddTextNext.current = true;
    }
  }

  function removeRow(id: string) {
    armFocusAfterRemoval(id);
    setRows((prev) => prev.filter((row) => row.id !== id));
  }

  function removeFileRow(id: string) {
    armFocusAfterRemoval(id);
    setFileRows((prev) => prev.filter((row) => row.id !== id));
  }

  /**
   * Filter, sort and cap a batch of picked files, whether from the plain file input or a
   * folder pick, and fold whatever survives into fileRows.
   *
   * Sorted by name before either cap is applied, so which files land and which are
   * reported as skipped does not depend on the order the OS or browser handed them back
   * in, which a folder pick leaves unspecified.
   */
  function ingestFiles(picked: FileList) {
    const candidates = Array.from(picked).sort((a, b) => a.name.localeCompare(b.name));

    // The accept/skip decision runs inside the setFileRows updater, against `prev`,
    // rather than against `uploadedBytes`/`totalSources` closed over from render: two
    // picks fired back to back (the file input and the folder input, say, before either
    // has re-rendered) would otherwise both budget against the same stale total and let
    // both waves through the cap together. `outcome` is filled in as a side channel so
    // the intake note can still be set once, right after, from what actually landed.
    const outcome: IntakeNote = { added: 0, skipped: [] };
    setFileRows((prev) => {
      const skipped: SkippedFile[] = [];
      const accepted: File[] = [];
      let remainingSlots = limits ? limits.max_sources - rows.length - prev.length : Infinity;
      let remainingBytes = limits
        ? limits.max_upload_bytes - prev.reduce((sum, row) => sum + row.file.size, 0)
        : Infinity;

      for (const file of candidates) {
        if (!isPdfFile(file)) {
          skipped.push({ name: file.name, reason: "not-pdf" });
          continue;
        }
        if (file.size === 0) {
          skipped.push({ name: file.name, reason: "empty" });
          continue;
        }
        if (remainingSlots <= 0) {
          skipped.push({ name: file.name, reason: "over-source-cap" });
          continue;
        }
        if (file.size > remainingBytes) {
          skipped.push({ name: file.name, reason: "over-byte-cap" });
          continue;
        }
        accepted.push(file);
        remainingSlots -= 1;
        remainingBytes -= file.size;
      }

      outcome.added = accepted.length;
      outcome.skipped = skipped;
      if (accepted.length === 0) return prev;
      return [...prev, ...accepted.map((file) => ({ id: newRowId("pdf"), file, error: null }))];
    });
    setIntakeNote(outcome);
  }

  function handleFilePick(event: ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files;
    if (picked && picked.length > 0) ingestFiles(picked);
    // Cleared so picking the exact same file (or folder) again still fires a change event.
    event.target.value = "";
  }

  function resetForm() {
    setSuccess(null);
    setSummaryError(null);
    setRows([]);
    setFileRows([]);
    setIntakeNote(null);
    setElapsed(0);
  }

  /**
   * Map a 422 source_failed response back onto the rows that produced it.
   *
   * PRIMARY KEY IS `index`, into the same [...rows, ...fileRows] order the request was
   * built in: that is the combined send order the backend counts from. `kind`/`ref`
   * matching is a defensive fallback only, for an index that somehow lands outside the
   * sent range, since two rows can legitimately share a ref (two PDFs both named
   * notes.pdf, or two blank-labelled text rows).
   */
  function applyFailures(failures: SourceFailure[]) {
    const combinedIds = [...rows.map((row) => row.id), ...fileRows.map((row) => row.id)];
    const messageByRowId = new Map<string, string>();
    const unmatched: SourceFailure[] = [];

    for (const failure of failures) {
      const id = combinedIds[failure.index];
      if (id !== undefined) {
        messageByRowId.set(id, failure.message);
      } else {
        unmatched.push(failure);
      }
    }
    for (const failure of unmatched) {
      // A url row's `ref` is blank whenever the learner left the label empty, which is
      // the common case, and the server then defaults `ref` to the row's own URL - so
      // matching only `row.ref` would silently miss exactly the rows most likely to need
      // this fallback. `row.value` is checked too for that kind.
      const fallbackRow =
        failure.kind === "pdf"
          ? fileRows.find((row) => row.file.name === failure.ref)
          : rows.find(
              (row) =>
                row.kind === failure.kind &&
                (row.ref === failure.ref || (row.kind === "url" && row.value === failure.ref)),
            );
      if (fallbackRow) messageByRowId.set(fallbackRow.id, failure.message);
    }

    setRows((prev) =>
      prev.map((row) =>
        messageByRowId.has(row.id) ? { ...row, error: messageByRowId.get(row.id)! } : row,
      ),
    );
    setFileRows((prev) =>
      prev.map((row) =>
        messageByRowId.has(row.id) ? { ...row, error: messageByRowId.get(row.id)! } : row,
      ),
    );
  }

  /**
   * Announce a summary failure and move focus to it. A plain `setSummaryError` would
   * silently no-op on a second submit that fails with the exact same message, since
   * React bails out of a state update to an unchanged value: the seq bump makes every
   * announcement, repeat or not, a real commit the focus effect reacts to.
   */
  function announceSummaryError(message: string) {
    setSummaryError(message);
    setSummaryErrorSeq((seq) => seq + 1);
    focusSummaryNext.current = true;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    // Taken before anything else runs, which is the only moment it is still guaranteed
    // to be wherever the learner actually sent from: the submit button for a click, or
    // wherever a keyboard submit left it.
    focusAtSend.current = document.activeElement;
    setSummaryError(null);
    setRows((prev) => prev.map((row) => ({ ...row, error: null })));
    setFileRows((prev) => prev.map((row) => ({ ...row, error: null })));

    if (totalSources === 0) {
      announceSummaryError("Add some pasted text, a URL, or a PDF first.");
      return;
    }
    const blankRow = rows.find((row) => !row.value.trim());
    if (blankRow) {
      const message = blankRow.kind === "text" ? "This is empty." : "Enter a URL.";
      setRows((prev) => prev.map((row) => (row.id === blankRow.id ? { ...row, error: message } : row)));
      announceSummaryError("Fix the highlighted source before generating.");
      return;
    }

    const sources: SourceInput[] = rows.map((row) => ({
      kind: row.kind,
      value: row.value,
      ...(row.ref.trim() ? { ref: row.ref.trim() } : {}),
    }));
    const files = fileRows.map((row) => row.file);

    setElapsed(0);
    setSubmitting(true);
    try {
      const result = await generateFromSources(sources, files);
      setSubmitting(false);
      setSuccess(result);
    } catch (err) {
      setSubmitting(false);
      if (err instanceof SourceGenerationError) {
        applyFailures(err.sources);
        announceSummaryError(
          `${err.message} ${plural(err.sources.length, "source is", "sources are")} marked below.`,
        );
      } else if (err instanceof ApiError) {
        announceSummaryError(err.message);
      } else {
        announceSummaryError("Could not reach the server. Is the backend running?");
      }
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-5">
      {!success && (
        <>
          <div className="flex flex-col gap-3">
            {rows.length === 0 && fileRows.length === 0 && (
              <p className="rounded-surface border border-dashed border-line-strong px-4 py-6 text-center text-ui text-ink-muted">
                Add pasted text, web pages, or PDFs below, in any mix.
              </p>
            )}
            {rows.map((row) => (
              <SourceRowField
                key={row.id}
                row={row}
                disabled={locked}
                onChange={(patch) => updateRow(row.id, patch)}
                onRemove={() => removeRow(row.id)}
                inputRef={(el) => registerInputRef(row.id, el)}
                removeButtonRef={(el) => registerRemoveButtonRef(row.id, el)}
              />
            ))}
            {fileRows.map((row) => (
              <FileRowField
                key={row.id}
                row={row}
                disabled={locked}
                onRemove={() => removeFileRow(row.id)}
                removeButtonRef={(el) => registerRemoveButtonRef(row.id, el)}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              ref={addTextButtonRef}
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => addRow("text")}
              disabled={locked || atSourceCap}
            >
              + Add text
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => addRow("url")}
              disabled={locked || atSourceCap}
            >
              + Add URL
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={locked || atSourceCap}
            >
              + Add PDF(s)
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => folderInputRef.current?.click()}
              disabled={locked || atSourceCap}
            >
              + Add folder of PDFs
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              onChange={handleFilePick}
              className="hidden"
            />
            <input
              ref={folderInputRef}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              onChange={handleFilePick}
              className="hidden"
            />
          </div>

          <p className="text-xs text-ink-muted">
            {limits
              ? `${totalSources}/${limits.max_sources} sources · ${pastedChars.toLocaleString("en-US")} characters pasted, plus whatever the links and PDFs contain · ${formatBytes(uploadedBytes)}/${formatBytes(limits.max_upload_bytes)} uploaded`
              : plural(totalSources, "source", "sources")}
          </p>

          {intakeNote && (
            <div
              role="status"
              className="rounded-surface border border-line bg-surface-sunken px-3 py-2 text-xs text-ink-muted"
            >
              <p>
                {intakeNote.added === 0 && intakeNote.skipped.length === 0
                  ? "No PDFs were found."
                  : intakeNote.skipped.length > 0
                    ? `${plural(intakeNote.added, "file", "files")} added, ${
                        intakeNote.skipped.length
                      } skipped: ${summarizeSkips(intakeNote.skipped)}.`
                    : `${plural(intakeNote.added, "file", "files")} added.`}
              </p>
              {intakeNote.skipped.length > 0 && (
                <details className="mt-1">
                  <summary className="cursor-pointer text-ink-muted transition-colors duration-fast ease-standard hover:text-ink">
                    Why files were skipped
                  </summary>
                  <ul className="mt-1 list-disc pl-4">
                    {intakeNote.skipped.map((entry, index) => (
                      <li key={`${entry.name}-${index}`}>
                        {entry.name}: {skipReasonLabel(entry.reason)}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </>
      )}

      {summaryError && (
        <Callout ref={summaryRef} tabIndex={-1} role="alert" tone="danger">
          {summaryError}
        </Callout>
      )}

      {success ? (
        <Callout tone="success" role="status">
          <p className="font-medium">Course generated: {success.title}</p>
          <p className="mt-1">
            This run cost an estimated {formatUsd(success.usage.run_cost_usd)}. Total API spend so
            far: {formatUsd(success.usage.total_cost_usd)}
            {success.usage.alert_active && ", which has crossed the cost alert threshold"}.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button type="button" onClick={() => router.push(`/courses/${success.id}`)}>
              Open course
            </Button>
            <Button type="button" variant="tinted" onClick={resetForm}>
              Generate another
            </Button>
          </div>
        </Callout>
      ) : submitting ? (
        <div className="flex items-center gap-3 rounded-surface border border-line px-4 py-3">
          <span
            aria-hidden
            className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-line-strong border-t-ink"
          />
          <div className="text-ui">
            <p className="font-medium">
              Generating your course, this usually takes 1 to 3 minutes. Keep this tab open.
            </p>
            <p className="mt-0.5 tabular-nums text-ink-muted">Elapsed: {formatElapsed(elapsed)}</p>
          </div>
        </div>
      ) : (
        <Button type="submit">Generate course</Button>
      )}
    </form>
  );
}

interface SourceRowFieldProps {
  row: SourceRow;
  disabled: boolean;
  onChange: (patch: Partial<Pick<SourceRow, "value" | "ref">>) => void;
  onRemove: () => void;
  /** Reaches the row's main control (textarea or url input), so a newly added row can
   * be focused, and a row restored by state can still be found by id after re-render. */
  inputRef: (el: HTMLTextAreaElement | HTMLInputElement | null) => void;
  /** Reaches this row's Remove button, so removing a neighbouring row can land focus here. */
  removeButtonRef: (el: HTMLButtonElement | null) => void;
}

function SourceRowField({
  row,
  disabled,
  onChange,
  onRemove,
  inputRef,
  removeButtonRef,
}: SourceRowFieldProps) {
  const errorId = `source-${row.id}-error`;
  const label = row.kind === "text" ? "Pasted text" : "URL";

  /* Adopting Card here (and in FileRowField) is not colour-neutral: Card hardcodes
     border-line, where this row previously drew its own line-strong boundary, so the
     border goes from #d4d4d8 / #3f3f46 (1.48:1 light, 1.90:1 dark) to #e4e4e7 / #27272a
     (1.27:1, 1.33:1). Those are the same four figures the secondary-variant note in
     Button.tsx cites, reaching the opposite decision: that variant's border IS the
     control's only boundary, so it holds line-strong, where this one encloses a group and
     takes the step. LessonMarkdown's comment draws the same divider-not-boundary
     distinction for the gridlines of a table inside a lesson. That note arrives with
     PR #37, so it is absent from main until that PR lands, which is why this names the
     file instead of describing it.
     No WCAG floor applies to either case, and not because 1.4.11 is only about controls.
     It has two bullets and each is separately satisfied here. User Interface Components:
     the text inputs draw their own line-strong boundary, and the row's one other control
     is a text-only Remove button, borderless by design and identified by its label, so
     the hairline identifies no control and no state. That button is the ONLY control in
     FileRowField, which is why this is worth spelling out rather than asserting every
     control draws a boundary. Graphical Objects: what groups a row visually is its
     PASTED TEXT / URL / PDF caption and the gap between rows in the list container, not
     the hairline, so nothing needed to understand the content rests on it either. */
  return (
    <Card padding={4}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-micro uppercase text-ink-muted">{label}</span>
        <button
          ref={removeButtonRef}
          type="button"
          onClick={onRemove}
          disabled={disabled}
          className="text-xs text-ink-muted transition-colors duration-fast ease-standard hover:text-danger disabled:pointer-events-none disabled:opacity-60"
        >
          Remove
        </button>
      </div>

      {row.kind === "text" ? (
        <textarea
          ref={inputRef}
          value={row.value}
          onChange={(event) => onChange({ value: event.target.value })}
          disabled={disabled}
          rows={6}
          aria-invalid={row.error ? true : undefined}
          aria-describedby={row.error ? errorId : undefined}
          placeholder="Paste lecture notes, an article, documentation - anything you want to learn."
          className={inputClasses}
        />
      ) : (
        <input
          ref={inputRef}
          type="url"
          value={row.value}
          onChange={(event) => onChange({ value: event.target.value })}
          disabled={disabled}
          aria-invalid={row.error ? true : undefined}
          aria-describedby={row.error ? errorId : undefined}
          placeholder="https://example.com/article"
          className={inputClasses}
        />
      )}

      <label className="mt-2 block text-xs text-ink-muted">
        Label (optional)
        <input
          type="text"
          value={row.ref}
          onChange={(event) => onChange({ ref: event.target.value })}
          disabled={disabled}
          placeholder={row.kind === "url" ? "Defaults to the URL" : "Defaults to a numbered label"}
          className={labelInputClasses}
        />
      </label>

      {row.error && (
        <p id={errorId} className="mt-1.5 text-xs text-danger">
          {row.error}
        </p>
      )}
    </Card>
  );
}

interface FileRowFieldProps {
  row: FileRow;
  disabled: boolean;
  onRemove: () => void;
  /** Reaches this row's Remove button, so removing a neighbouring row can land focus here. */
  removeButtonRef: (el: HTMLButtonElement | null) => void;
}

function FileRowField({ row, disabled, onRemove, removeButtonRef }: FileRowFieldProps) {
  const errorId = `source-${row.id}-error`;

  return (
    <Card
      // `role="group"` names the row for a screen reader; `aria-invalid` is deliberately
      // omitted here, since it is not a supported attribute on this role and this row has
      // no single form control to put it on instead. `aria-describedby` is a global
      // attribute and carries the error either way.
      padding={4}
      role="group"
      aria-label={`PDF: ${row.file.name}`}
      aria-describedby={row.error ? errorId : undefined}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <span className="text-micro uppercase text-ink-muted">PDF</span>
          {/* The filename came off the user's own file system and is rendered as plain
              text, never as markup, the same as every other untrusted string in this form. */}
          <p className="truncate text-ui text-ink" title={row.file.name}>
            {row.file.name}
          </p>
          <p className="text-xs text-ink-muted">{formatBytes(row.file.size)}</p>
        </div>
        <button
          ref={removeButtonRef}
          type="button"
          onClick={onRemove}
          disabled={disabled}
          className="shrink-0 text-xs text-ink-muted transition-colors duration-fast ease-standard hover:text-danger disabled:pointer-events-none disabled:opacity-60"
        >
          Remove
        </button>
      </div>
      {row.error && (
        <p id={errorId} className="mt-1.5 text-xs text-danger">
          {row.error}
        </p>
      )}
    </Card>
  );
}
