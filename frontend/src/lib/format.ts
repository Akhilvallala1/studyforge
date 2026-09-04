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

/** Format a byte count as a human-readable size, e.g. for upload-size limits and file rows. */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const decimals = value < 10 ? 1 : 0;
  return `${value.toFixed(decimals)} ${units[unitIndex]}`;
}
