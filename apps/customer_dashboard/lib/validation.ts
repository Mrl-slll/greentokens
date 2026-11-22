// Mirrors core/api/schemas.py: 1-1000 integers in [-1e9, 1e9]; upload <= 65,536 bytes.
export const MAX_VALUES = 1000, MAX_ABS = 1_000_000_000, MAX_UPLOAD_BYTES = 65_536;
export type Parsed = { ok: true; values: number[] } | { ok: false; error: string };

export function validateValues(v: unknown): Parsed {
  if (!Array.isArray(v) || v.length === 0) return { ok: false, error: "Enter at least one whole number." };
  if (v.length > MAX_VALUES) return { ok: false, error: `Use at most ${MAX_VALUES} numbers.` };
  for (const n of v) {
    if (typeof n !== "number" || !Number.isInteger(n)) return { ok: false, error: "Every value must be a whole number (no fractions, text or booleans)." };
    if (Math.abs(n) > MAX_ABS) return { ok: false, error: "Each value must be between -1,000,000,000 and 1,000,000,000." };
  }
  return { ok: true, values: v as number[] };
}

/** Parses "1, 2, 3, 4" or whitespace/newline separated integers. */
export function parseInline(text: string): Parsed {
  const parts = text.split(/[\s,]+/).filter(Boolean);
  if (parts.some((p) => !/^-?\d+$/.test(p))) return { ok: false, error: "Use whole numbers separated by commas or spaces." };
  return validateValues(parts.map(Number));
}

/** Validates raw upload text shaped {"values":[...]}. Size is bytes, not characters. */
export function parseUpload(text: string): Parsed {
  if (new TextEncoder().encode(text).length > MAX_UPLOAD_BYTES) return { ok: false, error: "File is larger than 65,536 bytes." };
  let j: unknown;
  try { j = JSON.parse(text); } catch { return { ok: false, error: "File is not valid JSON." }; }
  if (typeof j !== "object" || j === null || Array.isArray(j) || Object.keys(j).some((k) => k !== "values")) return { ok: false, error: 'Expected exactly {"values": [...]}.' };
  return validateValues((j as { values: unknown }).values);
}

export const newIdempotencyKey = () => `fe-${crypto.randomUUID()}`;
