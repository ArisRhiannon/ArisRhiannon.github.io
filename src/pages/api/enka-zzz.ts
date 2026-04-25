import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

let _cache: { data: unknown; ts: number } | null = null;
const TTL = 60 * 60 * 1000;

export const GET: APIRoute = async () => {
  if (_cache && Date.now() - _cache.ts < TTL) {
    return new Response(JSON.stringify({ characters: _cache.data, cached: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const db = new Database(join(process.cwd(), 'data', 'database.sqlite'), { readonly: true });
    const rows = db.query(
      "SELECT * FROM characters WHERE game = 'zzz' ORDER BY rarity DESC, level DESC"
    ).all();
    db.close();

    if (rows.length > 0) {
      _cache = { data: rows, ts: Date.now() };
      return new Response(JSON.stringify({ characters: rows, cached: false }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }
  } catch (e) {}

  // ZZZ usa Enka pero la API aún es beta — devolvemos vacío con nota
  return new Response(JSON.stringify({ characters: [], cached: false, note: 'ZZZ pendiente de sync. Ejecuta: bun run scripts/sync-enka-zzz.ts' }), {
    headers: { 'Content-Type': 'application/json' }
  });
};
