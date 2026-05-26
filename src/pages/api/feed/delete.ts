/**
 * DELETE /api/feed/delete
 * Borra un post y sus media. Auth required.
 */
import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { deletePost } from "../../../lib/feed";
import { deleteMediaFiles } from "../../../lib/media";

export const DELETE: APIRoute = async ({ request, cookies }) => {
  const token = cookies.get("aris_admin")?.value;
  if (!token || !(await isAdmin(request, ADMIN_JWT_SECRET()))) {
    return new Response("unauthorized", { status: 401 });
  }

  let body: { id?: number };
  try {
    body = await request.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  if (!body.id) return new Response("id required", { status: 400 });

  const media = deletePost(body.id);
  deleteMediaFiles(media);

  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
};
