import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "tinted" | "danger";
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
  /*
   * For an outlined button sitting INSIDE a status-tinted container, which is the one
   * place `secondary` must not be used. `secondary`'s border was tuned against the
   * neutral page surface: `line-strong` is #d4d4d8 light and #3f3f46 dark, which
   * measures 1.48:1 and 1.90:1 there, but drop it onto `success-surface` (#ecfdf5 /
   * #002c22) and the same colour measures 1.40:1 and 1.45:1. The raw button this
   * replaced in GenerateForm's success banner drew its border in emerald-700 light and
   * emerald-600 dark, which measure 5.21:1 and 4.03:1 on those two surfaces, so using
   * `secondary` there would have taken a control boundary from comfortably past WCAG
   * 1.4.11's 3:1 to nowhere near it, in both modes.
   *
   * `border-current`, not a success-specific token, because the tone is already on the
   * container: `Callout` puts `text-success` / `text-danger` / `text-warning` on its
   * wrapper, so `currentColor` here IS whichever tone encloses this button, and one
   * variant covers those THREE without a variant per tone. Callout's fourth tone is not
   * covered, it is excluded: `info` sets `text-ink`, so a `tinted` button inside an info
   * Callout inherits near-black and draws a 17.17:1 light / 15.14:1 dark hairline. That
   * is legible, not a contrast bug, but it is `secondary` in all but name and carries
   * none of the reason this variant exists, so use `secondary` there. Same for a
   * `tinted` button outside a Callout altogether: nothing tinted sets `currentColor` for
   * it to pick up and it inherits whatever ink surrounds it.
   *
   * In the success case `currentColor` resolves to #007956 light and #00d294 dark,
   * 5.15:1 and 7.70:1 against the surface behind it, the closest match to what the raw
   * version had. Hovering swaps the fill to `bg-surface`, and the border against THAT
   * measures 5.43:1 and 10.04:1, so the boundary stays past 3:1 in both states and both
   * modes.
   *
   * Hover goes to the plain page `surface` rather than a deeper tint. A deeper tint
   * would have to be a per-tone hover surface, and this variant does not know its tone:
   * not knowing is the entire point of inheriting through `currentColor`, and a static
   * class list cannot branch on what encloses it. So this is not waiting on a token to
   * be added. Even once a status surface gains a hover value for one tone, this variant
   * still could not reach for it. The real choice was between this and a 10%-opacity
   * currentColor fill. That was tried first and rejected on the BUILT output, not on taste:
   * Tailwind can pre-multiply an opacity into a NAMED colour (ConceptTutor's amber-100
   * at 70% emits #fef3c699 directly) but cannot for `currentColor`, so it emits a
   * full-opacity currentColor background as the pre-color-mix fallback and only reaches
   * 10% inside `@supports (color: color-mix(...))`. On a browser missing that @supports,
   * hovering would paint the button's background in exactly its own text colour and the
   * label would vanish. Unlikely, but "text disappears" is a worse failure than "hover
   * tint goes the other way", and `bg-surface` has no fallback branch to get wrong. It
   * also animates, since `transition-colors` on BASE covers background-color where an
   * opacity change would not have been covered at all.
   *
   * What that hover does NOT buy is a strong signal. The fill step measures 1.05:1 light
   * and 1.30:1 dark on the success surface (warning 1.04 and 1.32, danger 1.09 and 1.22),
   * and since preflight here leaves buttons on the default arrow cursor, that step is the
   * whole hover affordance. Recorded because it is easy to mistake for something this
   * migration broke, and it is not: the raw button this replaced stepped 1.08:1 light and
   * 1.56:1 dark, the same band, and `ghost` above moves 1.04:1 in light mode too, though
   * that one at least shifts its text colour as well. Fixing it properly needs a hover
   * token per status surface, which is the same "new token, not a swap between the ones
   * that exist" conclusion the `secondary` note above reaches about the 3:1 boundary, and
   * it is filed with that rather than improvised here for one button.
   *
   * Why this comment describes those two rejected classes in prose instead of naming
   * them: Tailwind v4's scanner is a plain text extractor with no idea what a comment
   * is, so any complete utility string written here is a candidate and gets a real rule
   * in the shipped bundle. An earlier draft of this block named both of them the obvious
   * way and put four dead rules into the CSS, two for the currentColor fill and two for
   * the emerald border this variant exists to replace. Verified by grepping the built
   * chunk before and after. Utilities the code actually uses are safe to name, and are
   * named above; ones it deliberately does not use are not.
   */
  tinted: "border border-current hover:bg-surface",
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
