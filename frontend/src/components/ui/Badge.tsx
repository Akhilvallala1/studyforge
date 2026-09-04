import { forwardRef } from "react";
import type { HTMLAttributes } from "react";

export type BadgeTone = "neutral" | "success" | "warning" | "danger";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: "border border-line bg-surface-sunken text-ink-muted",
  success: "bg-success-surface text-success",
  warning: "bg-warning-surface text-warning",
  danger: "bg-danger-surface text-danger",
};

/**
 * A short status pill: "Active", "Reached", "Mastered". Rounded-full, not
 * rounded-control, per the radius scale: badges and status dots are the one thing
 * that gets the pill shape, chips with more text in them get the smaller radius.
 */
export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { tone = "neutral", className, ...props },
  ref,
) {
  const classes = [
    "inline-flex items-center rounded-full px-2 py-0.5 text-micro uppercase font-medium",
    TONE_CLASSES[tone],
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return <span ref={ref} className={classes} {...props} />;
});
