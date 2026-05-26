import type { APIRoute } from "astro";
import { getReadDb, getDb } from "../../../lib/db";
import { jsonResponse, errorResponse } from "../../../lib/response";

// GET /api/videos/comments?id=xxx
export const GET: APIRoute = ({ url }) => {
  const videoId = url.searchParams.get("id");
  if (!videoId) return new Response("missing id", { status: 400 });

  try {
    const db = getReadDb();
    const rows = db
      .query(
        "SELECT id, alias, body, created_at FROM comments WHERE video_id = ? ORDER BY created_at ASC"
      )
      .all(videoId);
    db.close();
    return jsonResponse(rows);
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};

// POST /api/videos/comments?id=xxx
export const POST: APIRoute = async ({ request, url }) => {
  const videoId = url.searchParams.get("id");
  if (!videoId) return new Response("missing id", { status: 400 });

  try {
    const { alias, body } = await request.json();
    if (!alias?.trim() || !body?.trim()) {
      return errorResponse("alias y comentario requeridos", 400);
    }
    const safeAlias = String(alias).slice(0, 32).trim();
    const safeBody = String(body).slice(0, 500).trim();

    const db = getDb();
    db.run(
      "INSERT INTO comments (video_id, alias, body) VALUES (?, ?, ?)",
      [videoId, safeAlias, safeBody]
    );
    db.close();
    return jsonResponse({ ok: true });
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};
