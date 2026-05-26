import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { readJson, writeJsonString } from "../../../lib/data";
import { jsonResponse, errorResponse } from "../../../lib/response";

const ALLOWED = ["now.json", "books.json", "homepage.json", "gacha-config.json"];

// GET /api/admin/data?file=now.json
export const GET: APIRoute = async ({ request, url }) => {
  if (!(await isAdmin(request, ADMIN_JWT_SECRET())))
    return new Response("unauthorized", { status: 401 });

  const file = url.searchParams.get("file");
  if (!file || !ALLOWED.includes(file))
    return new Response("not allowed", { status: 403 });

  try {
    const content = readJson(file);
    return jsonResponse(content);
  } catch {
    return jsonResponse({});
  }
};

// POST /api/admin/data?file=now.json body: JSON
export const POST: APIRoute = async ({ request, url }) => {
  if (!(await isAdmin(request, ADMIN_JWT_SECRET())))
    return new Response("unauthorized", { status: 401 });

  const file = url.searchParams.get("file");
  if (!file || !ALLOWED.includes(file))
    return new Response("not allowed", { status: 403 });

  try {
    const body = await request.text();
    JSON.parse(body); // validate JSON
    writeJsonString(file, body);
    return jsonResponse({ ok: true });
  } catch (e) {
    return errorResponse(String(e), 400);
  }
};
