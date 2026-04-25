import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

function getDb() {
  return new Database(join(process.cwd(), 'data', 'database.sqlite'));
}

export const GET: APIRoute = ({ url }) => {
  const videoId = url.searchParams.get('id');
  if (!videoId) return new Response('missing id', { status: 400 });
  try {
    const db = getDb();
    const rows = db.query(
      'SELECT id, alias, body, created_at FROM comments WHERE video_id = ? ORDER BY created_at ASC'
    ).all(videoId);
    db.close();
    return new Response(JSON.stringify(rows), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 500 });
  }
};

export const POST: APIRoute = async ({ request, url }) => {
  const videoId = url.searchParams.get('id');
  if (!videoId) return new Response('missing id', { status: 400 });
  try {
    const { alias, body } = await request.json();
    if (!alias?.trim() || !body?.trim()) {
      return new Response(JSON.stringify({ error: 'alias y comentario requeridos' }), { status: 400 });
    }
    const safeAlias = String(alias).slice(0, 32).trim();
    const safeBody  = String(body).slice(0, 500).trim();
    const db = getDb();
    db.run(
      'INSERT INTO comments (video_id, alias, body) VALUES (?, ?, ?)',
      [videoId, safeAlias, safeBody]
    );
    db.close();
    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 500 });
  }
};
