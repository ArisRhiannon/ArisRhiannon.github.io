/**
 * GET /api/taglines — return all active taglines
 * POST /api/taglines — add a new tagline (admin)
 * DELETE /api/taglines — remove a tagline by id (admin)
 */
import type { APIRoute } from "astro";
import { getDb, getReadDb } from "../../lib/db";
import { jsonResponse, errorResponse, okResponse } from "../../lib/response";
import { isAdmin } from "../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../lib/env";

// GET — return all active taglines
export const GET: APIRoute = async () => {
  try {
    const db = getReadDb();
    const taglines = db
      .query("SELECT id, text, active FROM taglines WHERE active = 1 ORDER BY id")
      .all();
    db.close();
    return jsonResponse({ taglines });
  } catch {
    return jsonResponse({ taglines: [] });
  }
};

// POST — add a new tagline (admin only)
export const POST: APIRoute = async ({ request }) => {
  const secret = ADMIN_JWT_SECRET();
  if (!(await isAdmin(request, secret))) {
    return errorResponse("no autorizado", 403);
  }

  try {
    const body = await request.json();
    const { text } = body;

    if (!text || typeof text !== "string" || text.trim().length === 0) {
      return errorResponse("texto requerido");
    }
    if (text.length > 100) {
      return errorResponse("texto demasiado largo (max 100 caracteres)");
    }

    const db = getDb();
    const insert = db.query("INSERT INTO taglines (text) VALUES (?)");
    const info = insert.run(text.trim());
    const entry = db.query("SELECT id, text, active FROM taglines WHERE id = ?").get(info.lastInsertRowid) as any;
    db.close();

    return jsonResponse(entry, 201);
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};

// DELETE — remove a tagline (admin only)
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
    db.run("DELETE FROM taglines WHERE id = ?", [id]);
    db.close();

    return okResponse();
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};
