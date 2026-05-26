/**
 * POST /api/feed/create
 * Crea un nuevo post. Auth required.
 */
import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { createPost } from "../../../lib/feed";

function json(data: any, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export const POST: APIRoute = async ({ request }) => {
  if (!(await isAdmin(request, ADMIN_JWT_SECRET()))) {
    return json({ ok: false, error: "sesión expirada" }, 401);
  }

  let body: { body?: string; media?: any[]; mood?: string | null; pinned?: boolean };
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "JSON inválido" }, 400);
  }

  if (!body.body?.trim()) {
    return json({ ok: false, error: "el post no puede estar vacío" }, 400);
  }

  try {
    const post = createPost({
      body: body.body.trim(),
      media: body.media ?? [],
      mood: body.mood ?? null,
      pinned: body.pinned ?? false,
    });
    return json({ ok: true, post });
  } catch (e: any) {
    return json({ ok: false, error: e.message || "error al crear post" }, 500);
  }
};
