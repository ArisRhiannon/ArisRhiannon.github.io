import type { APIRoute } from 'astro';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

const ALLOWED = ['now.json', 'books.json', 'homepage.json', 'gacha-config.json'];

async function auth(request: Request, secret: string): Promise<boolean> {
  const cookie = request.headers.get('cookie') ?? '';
  const raw = cookie.split(';').find(c => c.trim().startsWith('aris_admin='));
  const token = raw ? decodeURIComponent(raw.slice(raw.indexOf('=') + 1).trim()) : undefined;
  if (!token) return false;
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
    const valid = await crypto.subtle.verify('HMAC', key, sigBytes, new TextEncoder().encode(payload));
    if (!valid) return false;
    const { ts } = JSON.parse(atob(payload));
    return Date.now() - ts < 8 * 60 * 60 * 1000;
  } catch { return false; }
}

// GET /api/admin/data?file=now.json
export const GET: APIRoute = async ({ request, url }) => {
  if (!(await auth(request, import.meta.env.ADMIN_JWT_SECRET))) return new Response('unauthorized', { status: 401 });
  const file = url.searchParams.get('file');
  if (!file || !ALLOWED.includes(file)) return new Response('not allowed', { status: 403 });
  try {
    const content = readFileSync(join(process.cwd(), 'data', file), 'utf-8');
    return new Response(content, { headers: { 'Content-Type': 'application/json' } });
  } catch { return new Response('{}', { headers: { 'Content-Type': 'application/json' } }); }
};

// POST /api/admin/data?file=now.json  body: JSON
export const POST: APIRoute = async ({ request, url }) => {
  if (!(await auth(request, import.meta.env.ADMIN_JWT_SECRET))) return new Response('unauthorized', { status: 401 });
  const file = url.searchParams.get('file');
  if (!file || !ALLOWED.includes(file)) return new Response('not allowed', { status: 403 });
  try {
    const body = await request.text();
    JSON.parse(body); // validar JSON
    writeFileSync(join(process.cwd(), 'data', file), body, 'utf-8');
    return new Response(JSON.stringify({ ok: true }), { headers: { 'Content-Type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), { status: 400, headers: { 'Content-Type': 'application/json' } });
  }
};
