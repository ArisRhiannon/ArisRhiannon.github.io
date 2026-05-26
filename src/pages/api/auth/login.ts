import type { APIRoute } from "astro";
import { ADMIN_HASH, ADMIN_SALT, ADMIN_ITERATIONS, ADMIN_JWT_SECRET } from "../../../lib/env";

/**
 * POST /api/auth/login
 * Body: { password: string }
 *
 * Verifies against ADMIN_HASH (PBKDF2-SHA256 + salt from .env).
 * On success, emits aris_admin cookie with HMAC-signed token.
 */

async function pbkdf2Verify(
  password: string,
  saltHex: string,
  storedHashB64: string,
  iterations: number
): Promise<boolean> {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"]
  );
  const salt = new Uint8Array(
    saltHex.match(/.{2}/g)!.map((b) => parseInt(b, 16))
  );
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations },
    keyMaterial,
    256
  );
  const derived = btoa(String.fromCharCode(...new Uint8Array(bits)));
  return derived === storedHashB64;
}

async function makeToken(secret: string): Promise<string> {
  const payload = btoa(JSON.stringify({ ts: Date.now() }));
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(payload)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)));
  return `${payload}.${sigB64}`;
}

export const POST: APIRoute = async ({ request, cookies }) => {
  let body: { password?: string };
  try {
    body = await request.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  const { password } = body;
  if (!password) return new Response("missing password", { status: 400 });

  const hash = ADMIN_HASH();
  const salt = ADMIN_SALT();
  const iterations = ADMIN_ITERATIONS();
  const secret = ADMIN_JWT_SECRET();

  if (!hash || !salt || !secret) {
    return new Response("server misconfigured", { status: 500 });
  }

  const ok = await pbkdf2Verify(password, salt, hash, iterations);
  if (!ok) return new Response("unauthorized", { status: 401 });

  const token = await makeToken(secret);
  cookies.set("aris_admin", token, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 8 * 60 * 60, // 8h
  });

  return new Response("ok", { status: 200 });
};
