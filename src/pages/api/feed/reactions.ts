import type { APIRoute } from "astro";
import { getDb, getReadDb } from "../../../lib/db";
import { jsonResponse, errorResponse, okResponse } from "../../../lib/response";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";

const VALID_EMOJIS = ["💖", "😂", "😭", "🤯", "✨", "🔥"];

function getClientIP(request: Request): string {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  return request.headers.get("host") ?? "unknown";
}

// GET /api/feed/reactions?post_id=N
export const GET: APIRoute = async ({ url, request }) => {
  const postId = url.searchParams.get("post_id");
  if (!postId) return errorResponse("post_id requerido");

  try {
    const db = getReadDb();
    const rows = db.query(
      "SELECT emoji, COUNT(*) as count FROM reactions WHERE post_id = ? GROUP BY emoji"
    ).all(postId) as any[];

    const ip = getClientIP(request);
    const userRow = db.query(
      "SELECT emoji FROM reactions WHERE post_id = ? AND ip = ?"
    ).get(postId, ip) as any;

    db.close();

    const reactions = rows.map(r => ({ emoji: r.emoji, count: r.count }));
    return jsonResponse({ reactions, userReaction: userRow?.emoji ?? null });
  } catch {
    return jsonResponse({ reactions: [], userReaction: null });
  }
};

// POST /api/feed/reactions — react or update reaction
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { post_id, emoji } = body;

    if (!post_id) return errorResponse("post_id requerido");
    if (!VALID_EMOJIS.includes(emoji)) return errorResponse("emoji invalido");

    const ip = getClientIP(request);
    const db = getDb();

    // Upsert: if IP already reacted, update; otherwise insert
    const existing = db.query(
      "SELECT id FROM reactions WHERE post_id = ? AND ip = ?"
    ).get(post_id, ip) as any;

    if (existing) {
      db.run("UPDATE reactions SET emoji = ?, created_at = CURRENT_TIMESTAMP WHERE id = ?", emoji, existing.id);
    } else {
      db.run("INSERT INTO reactions (post_id, emoji, ip) VALUES (?, ?, ?)", post_id, emoji, ip);
    }

    // Return updated counts
    const rows = db.query(
      "SELECT emoji, COUNT(*) as count FROM reactions WHERE post_id = ? GROUP BY emoji"
    ).all(post_id) as any[];
    db.close();

    const reactions = rows.map(r => ({ emoji: r.emoji, count: r.count }));
    return jsonResponse({ ok: true, reactions, userReaction: emoji });
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};

// DELETE /api/feed/reactions — remove own reaction
export const DELETE: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { post_id } = body;
    if (!post_id) return errorResponse("post_id requerido");

    const ip = getClientIP(request);
    const db = getDb();
    db.run("DELETE FROM reactions WHERE post_id = ? AND ip = ?", post_id, ip);

    const rows = db.query(
      "SELECT emoji, COUNT(*) as count FROM reactions WHERE post_id = ? GROUP BY emoji"
    ).all(post_id) as any[];
    db.close();

    const reactions = rows.map(r => ({ emoji: r.emoji, count: r.count }));
    return jsonResponse({ ok: true, reactions, userReaction: null });
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};
