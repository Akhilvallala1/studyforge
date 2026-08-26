/** Shared display formatting for money and token counts used across the usage UI. */

/**
 * Format a USD amount for display, always with enough precision to be useful
 * even for very small per-call amounts (e.g. $0.0573). These are estimates,
 * never billed amounts, so callers should pair this with an "estimated" label.
 */
export function formatUsd(amount: number | null | undefined): string {
  const value = typeof amount === "number" && Number.isFinite(amount) ? amount : 0;
  const abs = Math.abs(value);
  let decimals = 2;
  if (abs > 0 && abs < 1) decimals = 4;
  if (abs > 0 && abs < 0.0001) decimals = 6;
  return `$${value.toFixed(decimals)}`;
}

/** Format an integer count (tokens, calls) with thousands separators. */
export function formatCount(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "0";
  return value.toLocaleString("en-US");
}
