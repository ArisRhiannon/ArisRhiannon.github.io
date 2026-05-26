/**
 * PATCH /api/feed/pin
 * Fija/desfija un post. Auth required.
 */
import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { togglePin } from "../../../lib/feed";

export const PATCH: APIRoute = async ({ request, cookies }) => {
  const token = cookies.get("aris_admin")?.value;
  if (!token || !(await isAdmin(request, ADMIN_JWT_SECRET()))) {
    return new Response("unauthorized", { status: 401 });
  }

  let body: { id?: number; pinned?: boolean };
  try {
    body = await request.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  if (!body.id) return new Response("id required", { status: 400 });

  togglePin(body.id, body.pinned ?? true);
  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
};
