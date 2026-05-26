/**
 * src/lib/response.ts
 * JSON response helpers to eliminate duplication across API endpoints.
 */

export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function errorResponse(message: string, status = 400): Response {
  return jsonResponse({ error: message }, status);
}

export function okResponse(extra?: Record<string, unknown>): Response {
  return jsonResponse({ ok: true, ...extra });
}
