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
 * A promotion of the private `Stat` in app/page.tsx, not a pixel-identical copy of
 * it: the value moves from that copy's 22px/font-medium to this one's `text-title`
 * (20px/semibold), and `emphasis` moves from a raw `text-emerald-600
 * dark:text-emerald-500` to the token-driven `text-success`, which resolves to a
 * nearby but not identical colour. page.tsx keeps its own copy for now and is
 * unaffected either way; the task that migrates it onto this import should expect
 * those two differences rather than a drop-in swap.
 *
 * MUST BE RENDERED INSIDE A `<dl>`. The `<dt>`/`<dd>` pair below is only valid HTML,
 * and only maps to the description-list roles that make the label and value read as
 * one term-definition unit, when an ancestor supplies the list. This component does
 * not supply its own, because a `<dl>` per stat would make each one a separate list
 * and defeat the grouping. The wrapper `<div>` is permitted between `<dl>` and its
 * pairs. Every caller owns that `<dl>`; app/page.tsx does supply one.
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
      <dt className="mt-0.5 text-small text-ink-subtle">{label}</dt>
      <dd title={title} className={valueClasses}>
        {value}
        {/* `title` alone is not reliably announced, so the same explanation is in the
            accessibility tree as text. */}
        {note && <span className="sr-only"> {note}</span>}
      </dd>
    </div>
  );
});
