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
 * imports this one), not a pixel-identical copy of it. Five visual differences from
 * that original:
 *   - the value moves from that copy's 22px/font-medium to this one's `text-title`
 *     (20px/semibold);
 *   - the value's line-height goes from inherited (that arbitrary 22px size emitted
 *     font-size and nothing else, so it set no line-height of its own) to
 *     `text-title`'s explicit 1.75rem;
 *  - the label's SIZE moves from Tailwind's `text-xs` (12px/16px) to the token
 *    `text-small` (13px/20px), the same label size used elsewhere in the
 *    redesign (e.g. the Usage page's `<dt>`s), not an accident;
 *  - the label's COLOUR moves from `text-zinc-500 dark:text-zinc-400` to
 *    `text-ink-subtle`. Light is unchanged (zinc-500 either way); dark moves
 *    from zinc-400 (`#9f9fa9`, 7.55:1 on the `#0a0a0a` page) to ink-subtle's
 *    dark value (`#82828d`, 5.21:1), which still clears the 4.5:1 AA floor at
 *    this size;
 *   - `emphasis` moves from a raw emerald-600 light / emerald-500 dark to the
 *     token-driven `text-success`, which resolves to a nearby but not identical
 *     colour.
 *
 * That 22px size is described in words above, not written as a bracketed utility, and
 * the same goes for the sentence you are reading. Tailwind scans comments, so spelling
 * it as one emitted a real rule for that size into the built bundle, matched by no
 * element on any page. globals.css names the same size in its type-scale comment and
 * emits nothing, but not because of how that line is written: globals.css is the
 * stylesheet input rather than a scan source, so no class named anywhere in it can
 * emit. Of the four sizes it lists, only 15px and 13px still have an arbitrary
 * text-size rule in the bundle, and both come from live class usage: 15px from
 * ReteachConcept, 13px from ConceptPractice, ConceptTutor, DeleteCourseButton and
 * ReteachConcept. No className under frontend/ carries 22px or 17px as an arbitrary
 * text size, so no element renders with one, which is why the rule this comment used to
 * emit matched nothing. Carrying it in a className is the test, not naming it: the only
 * line under frontend/ that spells either token is the globals.css comment named above,
 * and this comment was the second such line until this change, which is the subject
 * here. The bare numbers do survive elsewhere, and are not that claim: 17px is what
 * `--text-subtitle` resolves to, 22px is `text-ui`'s line-height, and app/page.tsx twice
 * uses 22px as horizontal padding.
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
