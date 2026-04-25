import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';
import { mkdirSync, writeFileSync } from 'fs';
import { randomUUID } from 'crypto';
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);
const UPLOADS_DIR = join(process.cwd(), 'public', 'uploads');
const THUMBS_DIR  = join(process.cwd(), 'public', 'thumbs');

export const POST: APIRoute = async ({ request }) => {
  const cookie = request.headers.get('cookie') ?? '';
  const raw = cookie.split(';').find(c => c.trim().startsWith('aris_admin='));
  const token = raw ? decodeURIComponent(raw.slice(raw.indexOf('=') + 1).trim()) : undefined;
  if (!token || !(await verifyToken(token, import.meta.env.ADMIN_JWT_SECRET))) {
    return new Response('unauthorized', { status: 401 });
  }

  try {
    mkdirSync(UPLOADS_DIR, { recursive: true });
    mkdirSync(THUMBS_DIR,  { recursive: true });

    const form = await request.formData();
    const file        = form.get('video') as File | null;
    const title       = (form.get('title') as string) ?? 'Sin título';
    const category    = (form.get('category') as string) ?? 'general';
    const descriptors = (form.get('descriptors') as string) ?? '{}';

    if (!file || file.size === 0) {
      return new Response(JSON.stringify({ error: 'No se recibió archivo' }), {
        status: 400, headers: { 'Content-Type': 'application/json' }
      });
    }
    if (file.size > 500 * 1024 * 1024) {
      return new Response(JSON.stringify({ error: 'Archivo demasiado grande (máx 500MB)' }), {
        status: 413, headers: { 'Content-Type': 'application/json' }
      });
    }

    const ext      = file.name.split('.').pop()?.toLowerCase() ?? 'mp4';
    const id       = randomUUID();
    const filename = `${id}.${ext}`;
    const filePath = join(UPLOADS_DIR, filename);

    const buffer = await file.arrayBuffer();
    writeFileSync(filePath, Buffer.from(buffer));

    // Generar thumbnail con ffmpeg
    let thumbnailUrl: string | null = null;
    let width = 1920, height = 1080;
    const thumbFile = `${id}.jpg`;
    const thumbPath = join(THUMBS_DIR, thumbFile);
    try {
      // Extraer frame en el segundo 1 (o 0 si el video es muy corto)
      await execFileAsync('ffmpeg', [
        '-y', '-i', filePath,
        '-ss', '00:00:01',
        '-vframes', '1',
        '-vf', 'scale=640:-1',
        '-q:v', '3',
        thumbPath
      ]);
      thumbnailUrl = `/thumbs/${thumbFile}`;

      // Obtener dimensiones reales
      const probe = await execFileAsync('ffprobe', [
        '-v', 'quiet', '-print_format', 'json', '-show_streams', filePath
      ]);
      const info = JSON.parse(probe.stdout);
      const vs = info.streams?.find((s: any) => s.codec_type === 'video');
      if (vs) { width = vs.width ?? 1920; height = vs.height ?? 1080; }
    } catch {
      // ffmpeg no disponible o falló — thumbnail queda null
    }

    const db = new Database(join(process.cwd(), 'data', 'database.sqlite'));
    db.run(`CREATE TABLE IF NOT EXISTS videos (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, filename TEXT,
      url TEXT NOT NULL, thumbnail TEXT, category TEXT,
      descriptors TEXT DEFAULT '{}',
      width INTEGER DEFAULT 1920, height INTEGER DEFAULT 1080,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
    try { db.run("ALTER TABLE videos ADD COLUMN filename TEXT"); }     catch {}
    try { db.run("ALTER TABLE videos ADD COLUMN descriptors TEXT DEFAULT '{}'"); } catch {}
    try { db.run("ALTER TABLE videos ADD COLUMN width INTEGER DEFAULT 1920"); }    catch {}
    try { db.run("ALTER TABLE videos ADD COLUMN height INTEGER DEFAULT 1080"); }   catch {}

    db.run(
      `INSERT INTO videos (id, title, filename, url, thumbnail, category, descriptors, width, height)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, title, filename, `/uploads/${filename}`, thumbnailUrl, category, descriptors, width, height]
    );
    db.close();

    return new Response(JSON.stringify({ ok: true, id, url: `/uploads/${filename}`, thumbnail: thumbnailUrl }), {
      status: 200, headers: { 'Content-Type': 'application/json' }
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'Content-Type': 'application/json' }
    });
  }
};

async function verifyToken(token: string, secret: string): Promise<boolean> {
  try {
    const dot = token.lastIndexOf('.');
    if (dot < 0) return false;
    const payload = token.slice(0, dot);
    const sigB64  = token.slice(dot + 1);
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
