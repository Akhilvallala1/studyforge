import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
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
        href="/courses"
        className="text-small text-ink-muted transition-colors duration-fast ease-standard hover:text-ink"
      >
        &larr; All courses
      </Link>
      <PageHeader
        className="mt-4"
        title="API cost usage"
        description="Estimated LLM spend on this server, across course generation and re-teaching alike. Figures on this page are ESTIMATES derived from token counts and provider pricing tables, not billed amounts."
      />

      {loadError && <ErrorState className="mt-8" title="" message={loadError} />}

      {usage && (
        <>
          <section aria-labelledby="totals-heading" className="mt-8">
            <h2 id="totals-heading" className="text-subtitle">
              Totals
            </h2>
            <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Card padding={4}>
                <dt className="text-small text-ink-subtle">LLM calls</dt>
                <dd className="mt-1 text-title tabular-nums">{formatCount(usage.totals.calls)}</dd>
              </Card>
              <Card padding={4}>
                <dt className="text-small text-ink-subtle">Input tokens</dt>
                <dd className="mt-1 text-title tabular-nums">
                  {formatCount(usage.totals.input_tokens)}
                </dd>
              </Card>
              <Card padding={4}>
                <dt className="text-small text-ink-subtle">Output tokens</dt>
                <dd className="mt-1 text-title tabular-nums">
                  {formatCount(usage.totals.output_tokens)}
                </dd>
              </Card>
              <Card padding={4}>
                <dt className="text-small text-ink-subtle">Estimated cost (USD)</dt>
                <dd className="mt-1 text-title tabular-nums">
                  {formatUsd(usage.totals.estimated_cost_usd)}
                </dd>
              </Card>
            </dl>
            {usage.totals.approximate_note && (
              <p className="mt-2 text-small text-ink-subtle">{usage.totals.approximate_note}</p>
            )}
          </section>

          <section
            aria-labelledby="alert-heading"
            className="mt-6 rounded-surface border border-line p-4 text-ui"
          >
            <h2 id="alert-heading" className="sr-only">
              Alert and spend limit configuration
            </h2>
            <p>
              Recurring spend alert threshold:{" "}
              <span className="font-medium tabular-nums">{formatUsd(usage.alert.threshold_usd)}</span>
              {usage.alert.active && (
                <Badge tone="warning" className="ml-2">
                  Active
                </Badge>
              )}
            </p>
            {usage.limit.configured ? (
              <p className="mt-1">
                Hard spend cap:{" "}
                <span className="font-medium tabular-nums">{formatUsd(usage.limit.limit_usd)}</span>
                {usage.limit.reached ? (
                  <Badge tone="danger" className="ml-2">
                    Reached, further paid generations are blocked
                  </Badge>
                ) : (
                  <Badge tone="success" className="ml-2">
                    Not reached
                  </Badge>
                )}
              </p>
            ) : (
              <p className="mt-1 text-ink-muted">
                No hard spend cap is configured, generations are never blocked on cost.
              </p>
            )}
          </section>

          <section aria-labelledby="per-course-heading" className="mt-10">
            <h2 id="per-course-heading" className="text-subtitle">
              Where the spend went
            </h2>
            {usage.per_course.length === 0 ? (
              <p className="mt-3 rounded-surface border border-dashed border-line-strong px-4 py-6 text-center text-small text-ink-muted">
                No LLM spend recorded yet.
              </p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[560px] border-collapse text-left text-ui">
                  <thead>
                    <tr className="border-b border-line text-micro uppercase text-ink-subtle">
                      <th scope="col" className="py-2 pr-4 font-medium">
                        Attributed to
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
                      <tr key={`${row.group}:${row.course_id ?? ""}`} className="border-b border-line last:border-0">
                        <td className="py-2 pr-4">
                          {row.group === "course" && row.course_id !== null ? (
                            <Link
                              href={`/courses/${row.course_id}`}
                              className="hover:underline"
                            >
                              {row.label}
                            </Link>
                          ) : (
                            <Link
                              href={`#note-${row.group}`}
                              className="text-ink-muted underline decoration-dotted underline-offset-2"
                            >
                              {row.label}
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
                {/* One note per non-course group actually present. The server writes
                    these sentences, because which one is true of a row is decided by
                    the same code that decided the row's group. */}
                {usage.per_course
                  .filter((row) => row.note !== null)
                  .map((row) => (
                    <p key={row.group} id={`note-${row.group}`} className="mt-2 text-small text-ink-subtle">
                      {row.note}
                    </p>
                  ))}
              </div>
            )}
          </section>

          <section aria-labelledby="recent-calls-heading" className="mt-10">
            <h2 id="recent-calls-heading" className="text-subtitle">
              Recent calls
            </h2>
            {usage.recent_calls.length === 0 ? (
              <p className="mt-3 rounded-surface border border-dashed border-line-strong px-4 py-6 text-center text-small text-ink-muted">
                No LLM calls recorded yet.
              </p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[720px] border-collapse text-left text-ui">
                  <thead>
                    <tr className="border-b border-line text-micro uppercase text-ink-subtle">
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
                      <tr key={call.id} className="border-b border-line last:border-0">
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
                            <span className="ml-1 text-small text-ink-subtle">(approx.)</span>
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
