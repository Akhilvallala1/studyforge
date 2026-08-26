"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, generateFromPdf, generateFromText, generateFromUrl } from "@/lib/api";
import { formatUsd } from "@/lib/format";
import type { GenerateResult } from "@/lib/types";

type Mode = "text" | "url" | "pdf";

/** How long to show the run's cost before moving on to the generated course. */

const TABS: { mode: Mode; label: string }[] = [
  { mode: "text", label: "Paste text" },
  { mode: "url", label: "From URL" },
  { mode: "pdf", label: "Upload PDF" },
];

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function GenerateForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [success, setSuccess] = useState<GenerateResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!submitting) return;
    const started = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [submitting]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (mode === "text" && !text.trim()) {
      setError("Paste some text first.");
      return;
    }
    if (mode === "url" && !url.trim()) {
      setError("Enter a URL first.");
      return;
    }
    if (mode === "pdf" && !file) {
      setError("Choose a PDF file first.");
      return;
    }

    setElapsed(0);
    setSubmitting(true);
    try {
      const result =
        mode === "text"
          ? await generateFromText(text)
          : mode === "url"
            ? await generateFromUrl(url.trim())
            : await generateFromPdf(file as File);
      setSubmitting(false);
      setSuccess(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server. Is the backend running?");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div role="tablist" className="flex gap-1 rounded-lg bg-zinc-100 p-1 dark:bg-zinc-900">
        {TABS.map((tab) => (
          <button
            key={tab.mode}
            type="button"
            role="tab"
            aria-selected={mode === tab.mode}
            disabled={submitting || success !== null}
            onClick={() => {
              setMode(tab.mode);
              setError(null);
            }}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === tab.mode
                ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-50"
                : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {mode === "text" && (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={submitting || success !== null}
          rows={12}
          placeholder="Paste lecture notes, an article, documentation - anything you want to learn."
          className="w-full rounded-lg border border-zinc-300 bg-transparent p-3 text-sm outline-none focus:border-zinc-500 disabled:opacity-60 dark:border-zinc-700"
        />
      )}

      {mode === "url" && (
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={submitting || success !== null}
          placeholder="https://example.com/article"
          className="w-full rounded-lg border border-zinc-300 bg-transparent p-3 text-sm outline-none focus:border-zinc-500 disabled:opacity-60 dark:border-zinc-700"
        />
      )}

      {mode === "pdf" && (
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          disabled={submitting || success !== null}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full rounded-lg border border-zinc-300 p-3 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-zinc-900 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white disabled:opacity-60 dark:border-zinc-700 dark:file:bg-zinc-100 dark:file:text-zinc-900"
        />
      )}

      {error && (
        <p role="alert" className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
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
          <button
            type="button"
            onClick={() => router.push(`/courses/${success.id}`)}
            className="mt-3 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-500"
          >
            Open course
          </button>
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
