import type { APIRoute } from "astro";
import { getReadDb } from "../../lib/db";
import { jsonResponse } from "../../lib/response";

let _cache: { data: unknown; ts: number } | null = null;
const TTL = 60 * 60 * 1000;

export const GET: APIRoute = async () => {
  if (_cache && Date.now() - _cache.ts < TTL) {
    return jsonResponse({ characters: _cache.data, cached: true });
  }

  try {
    const db = getReadDb();
    const rows = db
      .query(
        "SELECT * FROM characters WHERE game = 'zzz' ORDER BY rarity DESC, level DESC"
      )
      .all();
    db.close();

    if (rows.length > 0) {
      _cache = { data: rows, ts: Date.now() };
      return jsonResponse({ characters: rows, cached: false });
    }
  } catch {}

  return jsonResponse({
    characters: [],
    cached: false,
    note: "ZZZ pendiente de sync. Ejecuta: bun run scripts/sync-enka-zzz.ts",
  });
};
