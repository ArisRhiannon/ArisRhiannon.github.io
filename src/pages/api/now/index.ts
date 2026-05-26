import type { APIRoute } from "astro";
import { getNowItems, createNowItem, updateNowItem, deleteNowItem } from "../../../lib/now";
import { jsonResponse, errorResponse, okResponse } from "../../../lib/response";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";

// GET /api/now — return all now items
export const GET: APIRoute = async () => {
  const items = getNowItems();
  return jsonResponse({ items });
};

// POST /api/now — create now item (admin only)
export const POST: APIRoute = async ({ request }) => {
  const secret = ADMIN_JWT_SECRET();
  if (!(await isAdmin(request, secret))) {
    return errorResponse("no autorizado", 403);
  }

  try {
    const body = await request.json();
    const { icon, category, text, sort_order } = body;

    if (!category || !text) return errorResponse("category y text requeridos");

    const item = createNowItem({ icon, category, text, sort_order });
    return jsonResponse(item, 201);
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};

// PUT /api/now — update now item (admin only)
export const PUT: APIRoute = async ({ request }) => {
  const secret = ADMIN_JWT_SECRET();
  if (!(await isAdmin(request, secret))) {
    return errorResponse("no autorizado", 403);
  }

  try {
    const body = await request.json();
    const { id, ...data } = body;
    if (!id) return errorResponse("id requerido");

    updateNowItem(id, data);
    return okResponse();
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};

// DELETE /api/now — delete now item (admin only)
export const DELETE: APIRoute = async ({ request }) => {
  const secret = ADMIN_JWT_SECRET();
  if (!(await isAdmin(request, secret))) {
    return errorResponse("no autorizado", 403);
  }

  try {
    const body = await request.json();
    const { id } = body;
    if (!id) return errorResponse("id requerido");

    deleteNowItem(id);
    return okResponse();
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};
