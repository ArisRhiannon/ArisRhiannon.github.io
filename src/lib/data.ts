/**
 * src/lib/data.ts
 * Type-safe JSON data file readers/writers.
 *
 * All data files live in /data/*.json.
 * Reads happen synchronously at Astro render time.
 */

import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

function dataPath(filename: string): string {
  return join(process.cwd(), "data", filename);
}

export function readJson<T = unknown>(filename: string): T {
  const raw = readFileSync(dataPath(filename), "utf-8");
  return JSON.parse(raw) as T;
}

/**
 * Try to read a JSON file, returning null if it doesn't exist.
 */
export function tryReadJson<T = unknown>(filename: string): T | null {
  try {
    return readJson<T>(filename);
  } catch {
    return null;
  }
}

/**
 * Write a pre-validated JSON string to a data file.
 * The caller is responsible for validating the JSON.
 */
export function writeJsonString(filename: string, jsonBody: string): void {
  writeFileSync(dataPath(filename), jsonBody, "utf-8");
}

/**
 * Write a JS value as JSON to a data file.
 */
export function writeJson(filename: string, data: unknown): void {
  writeFileSync(dataPath(filename), JSON.stringify(data, null, 2), "utf-8");
}
