/**
 * RegimeX Web — Class Name Concatenation Utility
 *
 * Lightweight helper for joining conditional CSS class names safely.
 * Avoids extra third-party dependencies while providing predictable behavior.
 */

type ClassValue = string | number | boolean | undefined | null;

export function cn(...classes: (ClassValue | Record<string, boolean | undefined | null>)[]): string {
  const result: string[] = [];

  for (const item of classes) {
    if (!item) continue;

    if (typeof item === "string" || typeof item === "number") {
      result.push(String(item));
    } else if (typeof item === "object") {
      for (const [key, value] of Object.entries(item)) {
        if (value) {
          result.push(key);
        }
      }
    }
  }

  return result.join(" ").trim();
}
