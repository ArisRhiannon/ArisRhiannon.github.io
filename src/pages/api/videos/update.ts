import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { getDb } from "../../../lib/db";
import { jsonResponse, errorResponse } from "../../../lib/response";

export const PATCH: APIRoute = async ({ request }) => {
  if (!(await isAdmin(request, ADMIN_JWT_SECRET())))
    return new Response("unauthorized", { status: 401 });

  try {
    const { id, title, category, descriptors, thumbnail } =
      await request.json();
    if (!id) return errorResponse("id requerido", 400);

    const db = getDb();
    db.run(
      `UPDATE videos SET title = COALESCE(?, title), category = COALESCE(?, category),
       descriptors = COALESCE(?, descriptors), thumbnail = COALESCE(?, thumbnail)
       WHERE id = ?`,
      [
        title ?? null,
        category ?? null,
        descriptors ? JSON.stringify(descriptors) : null,
        thumbnail ?? null,
        id,
      ]
    );
    db.close();
    return jsonResponse({ ok: true });
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};
