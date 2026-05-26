/**
 * GET /api/feed/
 * Lista posts paginados.
 */
import type { APIRoute } from "astro";
import { getPosts } from "../../../lib/feed";

export const GET: APIRoute = async ({ url }) => {
  const cursor = parseInt(url.searchParams.get("cursor") ?? "0") || undefined;
  const limit = Math.min(parseInt(url.searchParams.get("limit") ?? "20") || 20, 50);

  const result = getPosts(cursor, limit);
  return new Response(JSON.stringify(result), {
    headers: { "Content-Type": "application/json" },
  });
};
