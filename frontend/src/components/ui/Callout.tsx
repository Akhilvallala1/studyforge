import { forwardRef } from "react";
import type { HTMLAttributes } from "react";

export type CalloutTone = "info" | "success" | "warning" | "danger";

export interface CalloutProps extends HTMLAttributes<HTMLDivElement> {
  tone?: CalloutTone;
}

/*
 * `info` is deliberately neutral (surface-sunken, no accent), not blue: the accent
 * is reserved for focus rings, inline links and the active nav/tab indicator, never
 * a fill, and an info box big enough to hold a paragraph is exactly the fill this
 * rule rules out.
 */
const TONE_CLASSES: Record<CalloutTone, string> = {
  info: "border-line bg-surface-sunken text-ink",
  success: "border-success-border bg-success-surface text-success",
  warning: "border-warning-border bg-warning-surface text-warning",
  danger: "border-danger-border bg-danger-surface text-danger",
};

/**
 * The one alert-box shape, replacing five hand-rolled versions of the same thing.
 * Several of those are live regions (`role="status"` / `role="alert"`) or the
 * target a `ref.current?.focus()` call moves keyboard focus to after a mutation, so
 * this forwards its ref and spreads every prop rather than only accepting children:
 * `role`, `aria-live`, `tabIndex` and `id` all have to reach the DOM node unchanged.
 */
export const Callout = forwardRef<HTMLDivElement, CalloutProps>(function Callout(
  { tone = "info", className, ...props },
  ref,
) {
  const classes = ["rounded-surface border px-4 py-3 text-ui", TONE_CLASSES[tone], className]
    .filter(Boolean)
    .join(" ");
  return <div ref={ref} className={classes} {...props} />;
});
