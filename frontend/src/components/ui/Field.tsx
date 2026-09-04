import { forwardRef } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";

export interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: ReactNode;
  /** Required, not optional: it is what ties `label` to the input via `htmlFor`. */
  id: string;
}

/**
 * A labelled text input. Wraps only the native <input>, not the label's block, so
 * the ref this forwards is the input itself and a caller can call `.focus()` on it
 * the same way the app's existing hand-rolled inputs are focused today.
 *
 * The border tint on hover/focus is an extra affordance on top of the app-wide
 * `:focus-visible` ring, not a replacement for it: focus-visible still supplies the
 * ring, this only adds the colour change `:focus` was doing alone before.
 */
export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, hint, id, className, ...props },
  ref,
) {
  const inputClasses = [
    "mt-1 w-full rounded-control border border-line bg-transparent px-3 py-2 text-ui text-ink",
    "placeholder:text-ink-subtle transition-colors duration-fast ease-standard",
    "hover:border-line-hover focus:border-line-hover disabled:opacity-60",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div>
      <label htmlFor={id} className="block text-small font-medium text-ink-muted">
        {label}
        {hint && <span className="font-normal text-ink-subtle"> {hint}</span>}
      </label>
      <input ref={ref} id={id} className={inputClasses} {...props} />
    </div>
  );
});
