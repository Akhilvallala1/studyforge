import { forwardRef } from "react";
import type { HTMLAttributes } from "react";

export type CardPadding = 4 | 5 | 6;

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: CardPadding;
}

const PADDING_CLASSES: Record<CardPadding, string> = {
  4: "p-4",
  5: "p-5",
  6: "p-6",
};

/**
 * The app's one card shape: a border on a flat surface, never a lighter fill. There
 * is no elevated variant that swaps in a shadow, because --shadow-raise resolves to
 * `none` in dark mode; a caller that wants elevation adds `shadow-raise` itself and
 * gets nothing extra in dark mode, which is the point.
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { padding = 5, className, ...props },
  ref,
) {
  const classes = [
    "rounded-surface border border-border bg-surface-raised",
    PADDING_CLASSES[padding],
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return <div ref={ref} className={classes} {...props} />;
});
