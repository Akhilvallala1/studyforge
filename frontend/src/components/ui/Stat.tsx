import { forwardRef } from "react";
import type { HTMLAttributes } from "react";

export interface StatProps extends HTMLAttributes<HTMLDivElement> {
  value: string;
  label: string;
  emphasis?: boolean;
  title?: string;
  /** Announced alongside `value`; see the comment below on why it duplicates `title`. */
  note?: string;
}

/**
 * A promotion of the private `Stat` in app/page.tsx, unchanged in every way that
 * page's tests or eyes depend on: page.tsx keeps its own copy for now, and the task
 * that owns that file is the one that switches it over to this import.
 */
export const Stat = forwardRef<HTMLDivElement, StatProps>(function Stat(
  { value, label, emphasis, title, note, className, ...props },
  ref,
) {
  const classes = ["flex flex-col-reverse", className].filter(Boolean).join(" ");
  const valueClasses = [
    "font-mono text-title tabular-nums",
    emphasis ? "text-success" : "",
    title ? "cursor-help" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div ref={ref} className={classes} {...props}>
      <dt className="mt-0.5 text-small text-text-subtle">{label}</dt>
      <dd title={title} className={valueClasses}>
        {value}
        {/* `title` alone is not reliably announced, so the same explanation is in the
            accessibility tree as text. */}
        {note && <span className="sr-only"> {note}</span>}
      </dd>
    </div>
  );
});
