/**
 * src/lib/auth.ts
 * Unified authentication utilities.
 *
 * Token format: base64(payload).base64(signature)
 * Payload: { ts: number }
 * Signature: HMAC-SHA256(payload, ADMIN_JWT_SECRET)
 * Validity: 8 hours from creation
 */

const SESSION_MAX_AGE = 8 * 60 * 60 * 1000; // 8 hours

/**
 * Verify an aris_admin token (HMAC-SHA256).
 * Returns true if the token is valid and not expired.
 */
export async function verifyToken(token: string, secret: string): Promise<boolean> {
  try {
    const dot = token.lastIndexOf(".");
    if (dot < 0) return false;

    const payload = token.slice(0, dot);
    const sigB64 = token.slice(dot + 1);

    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["verify"],
    );

    const sigBytes = Uint8Array.from(atob(sigB64), (c) => c.charCodeAt(0));
    const valid = await crypto.subtle.verify(
      "HMAC",
      key,
      sigBytes,
      new TextEncoder().encode(payload),
    );
    if (!valid) return false;

    // Check expiration
    const { ts } = JSON.parse(atob(payload));
    return Date.now() - ts < SESSION_MAX_AGE;
  } catch {
    return false;
  }
}

/**
 * Extract the aris_admin token from a Request's Cookie header.
 * Returns the decoded token string, or undefined if not present.
 */
export function extractAdminToken(request: Request): string | undefined {
  const cookie = request.headers.get("cookie") ?? "";
  const raw = cookie
    .split(";")
    .find((c) => c.trim().startsWith("aris_admin="));
  if (!raw) return undefined;
  return decodeURIComponent(raw.slice(raw.indexOf("=") + 1).trim());
}

/**
 * Check if an incoming request is authenticated as admin.
 * Returns true if the token is valid.
 */
export async function isAdmin(request: Request, secret: string): Promise<boolean> {
  const token = extractAdminToken(request);
  if (!token) return false;
  return verifyToken(token, secret);
}