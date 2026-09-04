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
 * A promotion of the private `Stat` that used to live in app/page.tsx (which now
 * imports this one), not a pixel-identical copy of it. Four visual differences from
 * that original:
 *   - the value moves from that copy's 22px/font-medium to this one's `text-title`
 *     (20px/semibold);
 *   - the value's line-height goes from inherited (unset on `text-[22px]`) to
 *     `text-title`'s explicit 1.75rem;
 *   - the label moves from Tailwind's `text-xs` (12px/16px) to the token
 *     `text-small` (13px/20px), a deliberate move onto the same label size used
 *     elsewhere in this redesign (e.g. the Usage page's `<dt>`s), not an accident;
 *   - `emphasis` moves from a raw `text-emerald-600 dark:text-emerald-500` to the
 *     token-driven `text-success`, which resolves to a nearby but not identical
 *     colour.
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
