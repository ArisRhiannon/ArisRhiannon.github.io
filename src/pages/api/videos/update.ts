import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

export const PATCH: APIRoute = async ({ request }) => {
  // Verificar sesión
  const cookie = request.headers.get('cookie') ?? '';
  const raw = cookie.split(';').find(c => c.trim().startsWith('aris_admin='));
  const token = raw ? decodeURIComponent(raw.slice(raw.indexOf('=') + 1).trim()) : undefined;
  if (!token || !(await verifyToken(token, import.meta.env.ADMIN_JWT_SECRET))) {
    return new Response('unauthorized', { status: 401 });
  }

  try {
    const { id, title, category, descriptors, thumbnail } = await request.json();
    if (!id) return new Response(JSON.stringify({ error: 'id requerido' }), { status: 400, headers: { 'Content-Type': 'application/json' } });

    const db = new Database(join(process.cwd(), 'data', 'database.sqlite'));
    db.run(
      `UPDATE videos SET title = COALESCE(?, title), category = COALESCE(?, category),
       descriptors = COALESCE(?, descriptors), thumbnail = COALESCE(?, thumbnail)
       WHERE id = ?`,
      [title ?? null, category ?? null,
       descriptors ? JSON.stringify(descriptors) : null,
       thumbnail ?? null, id]
    );
    db.close();
    return new Response(JSON.stringify({ ok: true }), { headers: { 'Content-Type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 500, headers: { 'Content-Type': 'application/json' } });
  }
};

async function verifyToken(token: string, secret: string): Promise<boolean> {
  try {
    const dot = token.lastIndexOf('.');
    if (dot < 0) return false;
    const payload = token.slice(0, dot);
    const sigB64 = token.slice(dot + 1);
    const key = await crypto.subtle.importKey(
      'raw', new TextEncoder().encode(secret),
      { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']
    );
    const sigBytes = Uint8Array.from(atob(sigB64), c => c.charCodeAt(0));
    return await crypto.subtle.verify('HMAC', key, sigBytes, new TextEncoder().encode(payload));
  } catch { return false; }
}
