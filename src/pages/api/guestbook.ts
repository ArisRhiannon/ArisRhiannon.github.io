import type { APIRoute } from "astro";
import { getDb, getReadDb } from "../../lib/db";
import { jsonResponse, errorResponse, okResponse } from "../../lib/response";
import { isAdmin } from "../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../lib/env";

// GET /api/guestbook — return all entries, newest first, limit 50
export const GET: APIRoute = async () => {
  try {
    const db = getReadDb();
    const entries = db
      .query("SELECT id, name, message, emoji, created_at FROM guestbook ORDER BY created_at DESC LIMIT 50")
      .all();
    db.close();
    return jsonResponse({ entries });
  } catch {
    return jsonResponse({ entries: [] });
  }
};

// POST /api/guestbook — add a new entry
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { name, message, emoji } = body;

    if (!message || typeof message !== "string" || message.trim().length === 0) {
      return errorResponse("mensaje requerido");
    }
    if (message.length > 500) {
      return errorResponse("mensaje demasiado largo (max 500 caracteres)");
    }

    const entryName = (typeof name === "string" && name.trim()) ? name.trim().slice(0, 50) : "anon";
    const entryEmoji = emoji && typeof emoji === "string" ? emoji : "✨";

    // Get IP from x-forwarded-for or fallback
    const forwarded = request.headers.get("x-forwarded-for");
    const ip = forwarded ? forwarded.split(",")[0].trim() : (request.headers.get("host") ?? "unknown");

    const db = getDb();
    const insert = db.query(
      "INSERT INTO guestbook (name, message, emoji, ip) VALUES (?, ?, ?, ?)"
    );
    const info = insert.run(entryName, message.trim(), entryEmoji, ip);

    const entry = db
      .query("SELECT id, name, message, emoji, created_at FROM guestbook WHERE id = ?")
      .get(info.lastInsertRowid) as any;
    db.close();

    return jsonResponse(entry, 201);
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};

// DELETE /api/guestbook — admin only, delete entry by id
export const DELETE: APIRoute = async ({ request }) => {
  const secret = ADMIN_JWT_SECRET();
  if (!(await isAdmin(request, secret))) {
    return errorResponse("no autorizado", 403);
  }

  try {
    const body = await request.json();
    const { id } = body;

    if (!id) {
      return errorResponse("id requerido");
    }

    const db = getDb();
    db.run("DELETE FROM guestbook WHERE id = ?", [id]);
    db.close();

    return okResponse();
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};
