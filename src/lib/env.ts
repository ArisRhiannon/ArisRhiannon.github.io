/**
 * src/lib/env.ts
 * Centralized environment variable access.
 *
 * In Astro SSR, import.meta.env provides the .env values at build time.
 * Each variable is a function to allow mocking in tests if needed.
 */

function getEnv(key: string): string {
  // Astro SSR context: import.meta.env
  try {
    // @ts-expect-error - import.meta.env is available at runtime in Astro SSR
    if (import.meta.env && import.meta.env[key] !== undefined) {
      // @ts-expect-error
      return import.meta.env[key];
    }
  } catch {
    // Not in Astro SSR context
  }
  // Fallback: Bun.env for scripts, process.env for Node
  return (Bun as any)?.env?.[key] ?? process.env[key] ?? "";
}

export const ADMIN_HASH = (): string => getEnv("ADMIN_HASH");
export const ADMIN_SALT = (): string => getEnv("ADMIN_SALT");
export const ADMIN_ITERATIONS = (): number =>
  parseInt(getEnv("ADMIN_ITERATIONS") || "260000", 10);
export const ADMIN_JWT_SECRET = (): string => getEnv("ADMIN_JWT_SECRET");

export const CHAT_PASSWORD = (): string => getEnv("CHAT_PASSWORD");
export const LLAMA_URL = (): string =>
  getEnv("LLAMA_URL") || "http://host.docker.internal:8080/v1/chat/completions";
