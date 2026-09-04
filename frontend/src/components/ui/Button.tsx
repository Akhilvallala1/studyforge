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
 * `primary` and `danger` route through the token layer's fill/on-fill pairs
 * rather than a raw Tailwind colour, same as everything else here: a raw
 * `bg-red-700` next to a token-driven `text-danger` elsewhere in a composite
 * (an ErrorState's action slot, say) is exactly the kind of near-but-not-quite
 * match a shared token catches and a hand-picked hex does not.
 *
 * `primary` is the neutral `fill` token (the existing inverse-ink pairing: dark
 * ink in light mode, light ink in dark mode), not the accent: the accent is
 * reserved for focus rings, inline links and the active nav/tab indicator,
 * never a large fill.
 *
 * `primary` and `danger` each get their own `fill-hover` token rather than a
 * `brightness()` filter: globals.css's motion policy only ever animates colour,
 * border-colour, opacity and transform, and a filter transition is none of those.
 * A hover token also keeps a solid button's hover state exact and pickable, the
 * same way its resting fill is, instead of "whatever brightness(1.25) happens to
 * land on" for a colour nobody chose on purpose.
 */
const BASE =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium " +
  "transition-colors duration-fast ease-standard disabled:pointer-events-none disabled:opacity-60";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-fill text-on-fill hover:bg-fill-hover",
  // `line-strong`, not `line`. This variant's border IS the control's only boundary, so
  // it is doing more work here than a divider rule does. Measured on the built bundle:
  // line #e4e4e7/#27272a is 1.27:1 light and 1.33:1 dark, line-strong #d4d4d8/#3f3f46 is
  // 1.48:1 and 1.90:1, and the raw classes these buttons carried before the token
  // migration were zinc-300/zinc-700, which IS line-strong. Using `line` here quietly
  // made the only outlined control in the app fainter than it used to be.
  // Both values are still short of the 3:1 WCAG 1.4.11 wants for a control boundary.
  // Closing that needs a new token rather than a swap between these two, so it is filed
  // separately; this line only stops the migration from making it worse.
  secondary: "border border-line-strong text-ink hover:border-line-hover",
  ghost: "text-ink-muted hover:bg-surface-sunken hover:text-ink",
  danger: "bg-danger-fill text-danger-on-fill hover:bg-danger-fill-hover",
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
