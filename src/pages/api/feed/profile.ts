/**
 * PATCH /api/feed/profile
 * Actualiza el perfil (display_name, subtitle, pfp_url). Auth required.
 */
import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { updateProfile, getProfile } from "../../../lib/feed";

export const PATCH: APIRoute = async ({ request, cookies }) => {
  const token = cookies.get("aris_admin")?.value;
  if (!token || !(await isAdmin(request, ADMIN_JWT_SECRET()))) {
    return new Response("unauthorized", { status: 401 });
  }

  let body: { displayName?: string; subtitle?: string; pfpUrl?: string };
  try {
    body = await request.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  const updates: Record<string, string> = {};
  if (body.displayName !== undefined) updates.display_name = body.displayName;
  if (body.subtitle !== undefined) updates.subtitle = body.subtitle;
  if (body.pfpUrl !== undefined) updates.pfp_url = body.pfpUrl;

  const profile = updateProfile(updates);
  return new Response(JSON.stringify({ ok: true, profile }), {
    headers: { "Content-Type": "application/json" },
  });
};
