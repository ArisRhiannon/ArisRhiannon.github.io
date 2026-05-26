/**
 * GET /api/feed/auth-check
 * Verifica si el usuario esta autenticado y devuelve el profile.
 */
import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { getProfile } from "../../../lib/feed";

export const GET: APIRoute = async ({ request }) => {
  const authenticated = await isAdmin(request, ADMIN_JWT_SECRET());
  const profile = getProfile();

  return new Response(JSON.stringify({ authenticated, profile }), {
    headers: { "Content-Type": "application/json" },
  });
};
