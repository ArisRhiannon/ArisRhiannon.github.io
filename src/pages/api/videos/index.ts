import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

const DB = () => new Database(join(process.cwd(), 'data', 'database.sqlite'));

// GET /api/videos — lista todos
export const GET: APIRoute = async () => {
  try {
    const db = DB();
    const videos = db.query('SELECT * FROM videos ORDER BY created_at DESC').all();
    db.close();
    return json({ videos });
  } catch {
    return json({ videos: [] });
  }
};

// DELETE /api/videos?id=xxx — elimina un video
export const DELETE: APIRoute = async ({ url }) => {
  const id = url.searchParams.get('id');
  if (!id) return json({ error: 'id requerido' }, 400);
  try {
    const db = DB();
    // Obtener filename para borrar el archivo
    const row = db.query('SELECT filename FROM videos WHERE id = ?').get(id) as any;
    db.run('DELETE FROM videos WHERE id = ?', [id]);
    db.close();
    if (row?.filename) {
      const filePath = join(process.cwd(), 'public', 'uploads', row.filename);
      try { await Bun.file(filePath).exists() && (await import('fs')).promises.unlink(filePath); } catch {}
    }
    return json({ ok: true });
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });
}
