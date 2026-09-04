import { forwardRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";

export interface ErrorStateProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  message: ReactNode;
  action?: ReactNode;
}

/**
 * A page- or section-level failure: the backend is unreachable, a course failed to
 * load, and so on. `role="alert"` by default since this is usually the only thing
 * on the screen worth announcing, but a caller nesting one inside a region that is
 * already a live region can override it via `role={undefined}` through ...props
 * (props spread after the default, so an explicit prop always wins).
 */
export const ErrorState = forwardRef<HTMLDivElement, ErrorStateProps>(function ErrorState(
  { title = "Something went wrong", message, action, className, role = "alert", ...props },
  ref,
) {
  const classes = [
    "rounded-surface border border-danger-border bg-danger-surface px-4 py-3 text-danger",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div ref={ref} role={role} className={classes} {...props}>
      {title && <p className="text-ui font-medium">{title}</p>}
      <p className="mt-1 text-ui">{message}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
});
