import Link from "next/link";

import { ApiError, getUsage } from "@/lib/api";
import { formatCount, formatUsd } from "@/lib/format";
import type { UsageSummary } from "@/lib/types";

export const dynamic = "force-dynamic";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

export default async function UsagePage() {
  let usage: UsageSummary | null = null;
  let loadError: string | null = null;
  try {
    usage = await getUsage(50);
  } catch (err) {
    loadError =
      err instanceof ApiError ? err.message : "Could not reach the server. Is the backend running?";
  }

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-12">
      <Link
        href="/"
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        &larr; All courses
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">API cost usage</h1>
      <p className="mt-1 text-zinc-600 dark:text-zinc-400">
        Estimated LLM spend across every course generation on this server. Figures on this page
        are ESTIMATES derived from token counts and provider pricing tables, not billed amounts.
      </p>

      {loadError && (
        <p
          role="alert"
          className="mt-8 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          {loadError}
        </p>
      )}

      {usage && (
        <>
          <section aria-labelledby="totals-heading" className="mt-8">
            <h2 id="totals-heading" className="text-lg font-semibold">
              Totals
            </h2>
            <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
                <dt className="text-xs text-zinc-500 dark:text-zinc-400">LLM calls</dt>
                <dd className="mt-1 text-xl font-semibold tabular-nums">
                  {formatCount(usage.totals.calls)}
                </dd>
              </div>
              <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
                <dt className="text-xs text-zinc-500 dark:text-zinc-400">Input tokens</dt>
                <dd className="mt-1 text-xl font-semibold tabular-nums">
                  {formatCount(usage.totals.input_tokens)}
                </dd>
              </div>
              <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
                <dt className="text-xs text-zinc-500 dark:text-zinc-400">Output tokens</dt>
                <dd className="mt-1 text-xl font-semibold tabular-nums">
                  {formatCount(usage.totals.output_tokens)}
                </dd>
              </div>
              <div className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
                <dt className="text-xs text-zinc-500 dark:text-zinc-400">Estimated cost (USD)</dt>
                <dd className="mt-1 text-xl font-semibold tabular-nums">
                  {formatUsd(usage.totals.estimated_cost_usd)}
                </dd>
              </div>
            </dl>
            {usage.totals.approximate && (
              <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
                Some of these figures are approximate: at least one recorded call is missing an
                exact token count and was estimated instead.
              </p>
            )}
          </section>

          <section aria-labelledby="alert-heading" className="mt-6 rounded-xl border border-zinc-200 p-4 text-sm dark:border-zinc-800">
            <h2 id="alert-heading" className="sr-only">
              Alert and spend limit configuration
            </h2>
            <p>
              Recurring spend alert threshold:{" "}
              <span className="font-medium tabular-nums">{formatUsd(usage.alert.threshold_usd)}</span>
              {usage.alert.active && (
                <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                  Active
                </span>
              )}
            </p>
            {usage.limit.configured ? (
              <p className="mt-1">
                Hard spend cap:{" "}
                <span className="font-medium tabular-nums">{formatUsd(usage.limit.limit_usd)}</span>
                {usage.limit.reached ? (
                  <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-950 dark:text-red-300">
                    Reached, further paid generations are blocked
                  </span>
                ) : (
                  <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                    Not reached
                  </span>
                )}
              </p>
            ) : (
              <p className="mt-1 text-zinc-600 dark:text-zinc-400">
                No hard spend cap is configured, generations are never blocked on cost.
              </p>
            )}
          </section>

          <section aria-labelledby="per-course-heading" className="mt-10">
            <h2 id="per-course-heading" className="text-lg font-semibold">
              Spend by course
            </h2>
            {usage.per_course.length === 0 ? (
              <p className="mt-3 rounded-lg border border-dashed border-zinc-300 px-4 py-6 text-center text-sm text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
                No course generations recorded yet.
              </p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[560px] border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Course
                      </th>
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Calls
                      </th>
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Input tokens
                      </th>
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Output tokens
                      </th>
                      <th scope="col" className="py-2 font-medium">
                        Est. cost
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {usage.per_course.map((row) => (
                      <tr
                        key={row.course_id ?? "unattributed"}
                        className="border-b border-zinc-100 last:border-0 dark:border-zinc-900"
                      >
                        <td className="py-2 pr-4">
                          {row.course_id === null ? (
                            <Link
                              href="#unattributed-note"
                              className="text-zinc-600 underline decoration-dotted underline-offset-2 dark:text-zinc-400"
                            >
                              Unattributed
                            </Link>
                          ) : (
                            <Link
                              href={`/courses/${row.course_id}`}
                              className="hover:underline"
                            >
                              {row.title ?? `Course #${row.course_id}`}
                            </Link>
                          )}
                        </td>
                        <td className="py-2 pr-4 tabular-nums">{formatCount(row.calls)}</td>
                        <td className="py-2 pr-4 tabular-nums">{formatCount(row.input_tokens)}</td>
                        <td className="py-2 pr-4 tabular-nums">{formatCount(row.output_tokens)}</td>
                        <td className="py-2 tabular-nums">{formatUsd(row.estimated_cost_usd)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {usage.per_course.some((row) => row.course_id === null) && (
                  <p id="unattributed-note" className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
                    &quot;Unattributed&quot; calls come from a generation run that failed before its
                    course could be saved, so the spend has no course to attach to.
                  </p>
                )}
              </div>
            )}
          </section>

          <section aria-labelledby="recent-calls-heading" className="mt-10">
            <h2 id="recent-calls-heading" className="text-lg font-semibold">
              Recent calls
            </h2>
            {usage.recent_calls.length === 0 ? (
              <p className="mt-3 rounded-lg border border-dashed border-zinc-300 px-4 py-6 text-center text-sm text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
                No LLM calls recorded yet.
              </p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Time
                      </th>
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Provider
                      </th>
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Model
                      </th>
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Stage
                      </th>
                      <th scope="col" className="py-2 pr-4 font-medium">
                        In / out tokens
                      </th>
                      <th scope="col" className="py-2 font-medium">
                        Est. cost
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {usage.recent_calls.map((call) => (
                      <tr
                        key={call.id}
                        className="border-b border-zinc-100 last:border-0 dark:border-zinc-900"
                      >
                        <td className="py-2 pr-4 whitespace-nowrap tabular-nums">
                          {formatTimestamp(call.created_at)}
                        </td>
                        <td className="py-2 pr-4">{call.provider}</td>
                        <td className="py-2 pr-4">{call.model}</td>
                        <td className="py-2 pr-4">{call.stage}</td>
                        <td className="py-2 pr-4 tabular-nums">
                          {formatCount(call.input_tokens)} / {formatCount(call.output_tokens)}
                        </td>
                        <td className="py-2 tabular-nums">
                          {formatUsd(call.estimated_cost_usd)}
                          {call.approximate && (
                            <span className="ml-1 text-xs text-zinc-500 dark:text-zinc-400">
                              (approx.)
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
