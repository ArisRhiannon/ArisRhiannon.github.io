import type { APIRoute } from "astro";
import { getDb, getReadDb } from "../../../lib/db";
import { jsonResponse, errorResponse, okResponse } from "../../../lib/response";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { join } from "path";

// GET /api/videos
export const GET: APIRoute = async () => {
  try {
    const db = getReadDb();
    const videos = db
      .query("SELECT * FROM videos ORDER BY created_at DESC")
      .all();
    db.close();
    return jsonResponse({ videos });
  } catch {
    return jsonResponse({ videos: [] });
  }
};

// DELETE /api/videos?id=xxx
export const DELETE: APIRoute = async ({ url, request }) => {
  const secret = ADMIN_JWT_SECRET();
  if (!(await isAdmin(request, secret))) {
    return errorResponse("no autorizado", 403);
  }

  const id = url.searchParams.get("id");
  if (!id) return errorResponse("id requerido", 400);

  try {
    const db = getDb();
    const row = db
      .query("SELECT filename FROM videos WHERE id = ?")
      .get(id) as any;
    db.run("DELETE FROM videos WHERE id = ?", [id]);
    db.close();

    if (row?.filename) {
      const filePath = join(process.cwd(), "public", "uploads", row.filename);
      try {
        const { unlink } = await import("fs/promises");
        await unlink(filePath);
      } catch {}
    }
    return okResponse();
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};
