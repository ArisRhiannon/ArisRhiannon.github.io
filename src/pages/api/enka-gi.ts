import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

const DB_PATH = join(process.cwd(), 'data', 'database.sqlite');
const CACHE: { data: unknown; ts: number } | null = null as any;
let _cache: { data: unknown; ts: number } | null = null;
const TTL = 60 * 60 * 1000; // 1h

export const GET: APIRoute = async () => {
  // 1. Cache en memoria
  if (_cache && Date.now() - _cache.ts < TTL) {
    return new Response(JSON.stringify({ characters: _cache.data, cached: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // 2. Leer de SQLite
  try {
    const db = new Database(DB_PATH, { readonly: true });
    const rows = db.query(
      "SELECT * FROM characters WHERE game = 'gi' ORDER BY rarity DESC, level DESC"
    ).all();
    db.close();

    if (rows.length > 0) {
      _cache = { data: rows, ts: Date.now() };
      return new Response(JSON.stringify({ characters: rows, cached: false }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }
  } catch (e) {
    // DB no existe aún — devolver vacío
  }

  return new Response(JSON.stringify({ characters: [], cached: false, note: 'Sin datos. Ejecuta: bun run scripts/sync-enka-gi.ts' }), {
    headers: { 'Content-Type': 'application/json' }
  });
};
