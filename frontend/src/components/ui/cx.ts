/**
 * Minimal class-name joiner.
 *
 * The kit deliberately does not pull in `clsx`/`tailwind-merge`: the only thing
 * every component needs is "drop the falsy branches and flatten", which is six
 * lines. Later classes still win in the DOM, so `className` overrides passed by
 * callers behave the way they read.
 */
export type ClassValue =
  | string
  | number
  | bigint
  | boolean
  | null
  | undefined
  | ClassValue[];

export function cx(...parts: ClassValue[]): string {
  const out: string[] = [];
  for (const part of parts) {
    if (!part) continue;
    if (Array.isArray(part)) {
      const nested = cx(...part);
      if (nested) out.push(nested);
    } else {
      out.push(String(part));
    }
  }
  return out.join(' ');
}
