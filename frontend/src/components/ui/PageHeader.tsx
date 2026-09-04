import { forwardRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";

export interface PageHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: ReactNode;
  /** A button or link, right-aligned next to the title on wide screens. */
  actions?: ReactNode;
}

/** The page-level `<h1>` plus its one-line description and an optional action. */
export const PageHeader = forwardRef<HTMLDivElement, PageHeaderProps>(function PageHeader(
  { title, description, actions, className, ...props },
  ref,
) {
  const classes = ["flex flex-wrap items-start justify-between gap-4", className]
    .filter(Boolean)
    .join(" ");
  return (
    <div ref={ref} className={classes} {...props}>
      <div>
        <h1 className="text-display">{title}</h1>
        {description && <p className="mt-1.5 text-ui text-text-muted">{description}</p>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
});
