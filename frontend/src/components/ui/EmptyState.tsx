import { forwardRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";

export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: ReactNode;
  /**
   * Rendered as-is, not cloned: a caller that needs to focus this after a mutation
   * (a course list that just emptied, say) puts its own `id` and `ref` straight on
   * the element it passes in here.
   */
  action?: ReactNode;
}

/**
 * The "nothing here yet" placeholder: a dashed border reads as an absence rather
 * than a broken card, which is what a solid border on an empty box would suggest.
 */
export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(function EmptyState(
  { title, description, action, className, ...props },
  ref,
) {
  const classes = [
    "rounded-surface border border-dashed border-line-strong px-6 py-16 text-center",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div ref={ref} className={classes} {...props}>
      <p className="text-subtitle">{title}</p>
      {description && <p className="mt-1 text-ui text-ink-muted">{description}</p>}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
});
