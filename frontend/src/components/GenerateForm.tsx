"use client";

import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";

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

const inputClasses =
  "mt-2 w-full rounded-md border border-zinc-300 bg-transparent p-2.5 text-sm outline-none focus:border-zinc-500 disabled:opacity-60 dark:border-zinc-700";

export function GenerateForm() {
  const router = useRouter();
  const [rows, setRows] = useState<SourceRow[]>([]);
  const [fileRows, setFileRows] = useState<FileRow[]>([]);
  const [limits, setLimits] = useState<SourceLimits | null>(null);
  const [intakeNote, setIntakeNote] = useState<IntakeNote | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [success, setSuccess] = useState<GenerateResult | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const summaryRef = useRef<HTMLDivElement>(null);
  const focusSummaryNext = useRef(false);

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
  // with no indication anything happened.
  useEffect(() => {
    if (!focusSummaryNext.current) return;
    focusSummaryNext.current = false;
    summaryRef.current?.focus();
  }, [summaryError]);

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
    setRows((prev) => [...prev, { id: newRowId(kind), kind, value: "", ref: "", error: null }]);
  }

  function updateRow(id: string, patch: Partial<Pick<SourceRow, "value" | "ref">>) {
    // Editing a row clears only that row's own failure, and only that: no other row's
    // error, and nothing beyond the one field being typed into.
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch, error: null } : row)));
  }

  function removeRow(id: string) {
    setRows((prev) => prev.filter((row) => row.id !== id));
  }

  function removeFileRow(id: string) {
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
    const skipped: SkippedFile[] = [];
    const accepted: File[] = [];

    let remainingSlots = limits ? limits.max_sources - totalSources : Infinity;
    let remainingBytes = limits ? limits.max_upload_bytes - uploadedBytes : Infinity;

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

    if (accepted.length > 0) {
      setFileRows((prev) => [
        ...prev,
        ...accepted.map((file) => ({ id: newRowId("pdf"), file, error: null })),
      ]);
    }
    setIntakeNote({ added: accepted.length, skipped });
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
      const fallbackRow =
        failure.kind === "pdf"
          ? fileRows.find((row) => row.file.name === failure.ref)
          : rows.find((row) => row.kind === failure.kind && row.ref === failure.ref);
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

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSummaryError(null);
    setRows((prev) => prev.map((row) => ({ ...row, error: null })));
    setFileRows((prev) => prev.map((row) => ({ ...row, error: null })));

    if (totalSources === 0) {
      setSummaryError("Add some pasted text, a URL, or a PDF first.");
      focusSummaryNext.current = true;
      return;
    }
    const blankRow = rows.find((row) => !row.value.trim());
    if (blankRow) {
      const message = blankRow.kind === "text" ? "This is empty." : "Enter a URL.";
      setRows((prev) => prev.map((row) => (row.id === blankRow.id ? { ...row, error: message } : row)));
      setSummaryError("Fix the highlighted source before generating.");
      focusSummaryNext.current = true;
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
        setSummaryError(`${err.message} ${plural(err.sources.length, "source is", "sources are")} marked below.`);
      } else if (err instanceof ApiError) {
        setSummaryError(err.message);
      } else {
        setSummaryError("Could not reach the server. Is the backend running?");
      }
      focusSummaryNext.current = true;
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-5">
      {!success && (
        <>
          <div className="flex flex-col gap-3">
            {rows.length === 0 && fileRows.length === 0 && (
              <p className="rounded-lg border border-dashed border-zinc-300 px-4 py-6 text-center text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-400">
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
              />
            ))}
            {fileRows.map((row) => (
              <FileRowField
                key={row.id}
                row={row}
                disabled={locked}
                onRemove={() => removeFileRow(row.id)}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => addRow("text")}
              disabled={locked || atSourceCap}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium transition-colors hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:border-zinc-500"
            >
              + Add text
            </button>
            <button
              type="button"
              onClick={() => addRow("url")}
              disabled={locked || atSourceCap}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium transition-colors hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:border-zinc-500"
            >
              + Add URL
            </button>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={locked || atSourceCap}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium transition-colors hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:border-zinc-500"
            >
              + Add PDF(s)
            </button>
            <button
              type="button"
              onClick={() => folderInputRef.current?.click()}
              disabled={locked || atSourceCap}
              className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium transition-colors hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:border-zinc-500"
            >
              + Add folder of PDFs
            </button>
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

          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            {limits
              ? `${totalSources}/${limits.max_sources} sources · ${pastedChars.toLocaleString("en-US")} characters pasted, plus whatever the links and PDFs contain · ${formatBytes(uploadedBytes)}/${formatBytes(limits.max_upload_bytes)} uploaded`
              : plural(totalSources, "source", "sources")}
          </p>

          {intakeNote && (
            <div
              role="status"
              className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400"
            >
              <p>
                {intakeNote.added === 0 && intakeNote.skipped.length === 0
                  ? "No PDFs were found."
                  : `${plural(intakeNote.added, "file", "files")} added${
                      intakeNote.skipped.length > 0
                        ? `, ${plural(intakeNote.skipped.length, "file", "files")} skipped`
                        : ""
                    }.`}
              </p>
              {intakeNote.skipped.length > 0 && (
                <details className="mt-1">
                  <summary className="cursor-pointer">Why files were skipped</summary>
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
        <div
          ref={summaryRef}
          tabIndex={-1}
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 outline-none focus-visible:ring-2 focus-visible:ring-red-500 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          {summaryError}
        </div>
      )}

      {success ? (
        <div
          role="status"
          className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
        >
          <p className="font-medium">Course generated: {success.title}</p>
          <p className="mt-1">
            This run cost an estimated {formatUsd(success.usage.run_cost_usd)}. Total API spend so
            far: {formatUsd(success.usage.total_cost_usd)}
            {success.usage.alert_active && ", which has crossed the cost alert threshold"}.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => router.push(`/courses/${success.id}`)}
              className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500"
            >
              Open course
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="rounded-lg border border-emerald-700 px-4 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-100 dark:border-emerald-600 dark:text-emerald-200 dark:hover:bg-emerald-900"
            >
              Generate another
            </button>
          </div>
        </div>
      ) : submitting ? (
        <div className="flex items-center gap-3 rounded-lg border border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <span
            aria-hidden
            className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100"
          />
          <div className="text-sm">
            <p className="font-medium">
              Generating your course, this usually takes 1 to 3 minutes. Keep this tab open.
            </p>
            <p className="mt-0.5 tabular-nums text-zinc-600 dark:text-zinc-400">
              Elapsed: {formatElapsed(elapsed)}
            </p>
          </div>
        </div>
      ) : (
        <button
          type="submit"
          className="rounded-lg bg-zinc-900 px-5 py-2.5 font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Generate course
        </button>
      )}
    </form>
  );
}

interface SourceRowFieldProps {
  row: SourceRow;
  disabled: boolean;
  onChange: (patch: Partial<Pick<SourceRow, "value" | "ref">>) => void;
  onRemove: () => void;
}

function SourceRowField({ row, disabled, onChange, onRemove }: SourceRowFieldProps) {
  const errorId = `source-${row.id}-error`;
  const label = row.kind === "text" ? "Pasted text" : "URL";

  return (
    <div className="rounded-lg border border-zinc-300 p-3 dark:border-zinc-700">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          {label}
        </span>
        <button
          type="button"
          onClick={onRemove}
          disabled={disabled}
          className="text-xs text-zinc-500 transition-colors hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-zinc-400 dark:hover:text-red-400"
        >
          Remove
        </button>
      </div>

      {row.kind === "text" ? (
        <textarea
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

      <label className="mt-2 block text-xs text-zinc-500 dark:text-zinc-400">
        Label (optional)
        <input
          type="text"
          value={row.ref}
          onChange={(event) => onChange({ ref: event.target.value })}
          disabled={disabled}
          placeholder={row.kind === "url" ? "Defaults to the URL" : "Defaults to a numbered label"}
          className="mt-1 w-full rounded-md border border-zinc-300 bg-transparent p-1.5 text-xs outline-none focus:border-zinc-500 disabled:opacity-60 dark:border-zinc-700"
        />
      </label>

      {row.error && (
        <p id={errorId} className="mt-1.5 text-xs text-red-700 dark:text-red-400">
          {row.error}
        </p>
      )}
    </div>
  );
}

interface FileRowFieldProps {
  row: FileRow;
  disabled: boolean;
  onRemove: () => void;
}

function FileRowField({ row, disabled, onRemove }: FileRowFieldProps) {
  const errorId = `source-${row.id}-error`;

  return (
    <div
      // `role="group"` names the row for a screen reader; `aria-invalid` is deliberately
      // omitted here, since it is not a supported attribute on this role and this row has
      // no single form control to put it on instead. `aria-describedby` is a global
      // attribute and carries the error either way.
      role="group"
      aria-label={`PDF: ${row.file.name}`}
      aria-describedby={row.error ? errorId : undefined}
      className="rounded-lg border border-zinc-300 p-3 dark:border-zinc-700"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <span className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            PDF
          </span>
          {/* The filename came off the user's own file system and is rendered as plain
              text, never as markup, the same as every other untrusted string in this form. */}
          <p className="truncate text-sm" title={row.file.name}>
            {row.file.name}
          </p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">{formatBytes(row.file.size)}</p>
        </div>
        <button
          type="button"
          onClick={onRemove}
          disabled={disabled}
          className="shrink-0 text-xs text-zinc-500 transition-colors hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-zinc-400 dark:hover:text-red-400"
        >
          Remove
        </button>
      </div>
      {row.error && (
        <p id={errorId} className="mt-1.5 text-xs text-red-700 dark:text-red-400">
          {row.error}
        </p>
      )}
    </div>
  );
}
