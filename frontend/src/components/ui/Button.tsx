import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

/*
 * Fill and border colour differ by variant; everything else (radius, weight, the
 * disabled and focus treatment) is shared, so those live once on BASE rather than
 * being repeated per variant.
 *
 * `primary` stays the existing inverse-ink fill (zinc-900 on zinc-100 in dark), not
 * the accent: the accent is reserved for focus rings, inline links and the active
 * nav/tab indicator, never a large fill.
 */
const BASE =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium " +
  "transition-colors duration-fast ease-standard disabled:pointer-events-none disabled:opacity-60";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-zinc-900 text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300",
  secondary:
    "border border-border text-text hover:border-border-hover dark:hover:border-border-hover",
  ghost: "text-text-muted hover:bg-surface-sunken hover:text-text",
  danger: "bg-red-700 text-white hover:bg-red-800 dark:bg-red-800 dark:hover:bg-red-700",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-small",
  md: "px-4 py-2 text-ui",
};

/**
 * Thin wrapper over a native <button>. No variant here reaches for its own focus
 * ring: the app-wide `:focus-visible` rule in globals.css already covers every
 * focusable element, this one included.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", className, type = "button", ...props },
  ref,
) {
  const classes = [BASE, VARIANT_CLASSES[variant], SIZE_CLASSES[size], className]
    .filter(Boolean)
    .join(" ");
  return <button ref={ref} type={type} className={classes} {...props} />;
});
