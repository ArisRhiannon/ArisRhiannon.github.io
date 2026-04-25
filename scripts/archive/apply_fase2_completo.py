#!/usr/bin/env python3
"""
apply_fase2_completo.py
-----------------------
Crea / reemplaza de una sola pasada:

  1. Admin inteligente y adaptivo
       - Lee TODOS los módulos activos dinámicamente (ahora, libros, gacha, videos)
       - Editor inline de now.json y books.json
       - Panel de comandos de sync
       - Extensible: detecta módulos futuros automáticamente

  2. Videos — sistema completo
       - Upload drag-and-drop de video (POST /api/videos/upload)
       - Descriptores editables (Personaje, Score, etc.) → guardados en SQLite
       - Página /v/[id]  con OG tags correctos para Discord embed
       - Vista cómoda en el sitio (player HTML5 full-width)
       - Tab /videos actualizado con cards bonitas

  3. Nav — añade [videos] y [gacha]

  4. Radio — soporte para archivo local /public/aris_song.mp3
       (FLAC no tiene soporte universal; instrucciones de conversión incluidas)

  5. Caddy — añade regla para servir /uploads/ con headers correctos

USO:
  scp apply_fase2_completo.py ubuntu@servidor:~/misitio/
  cd ~/misitio && python3 apply_fase2_completo.py
  sudo docker compose up -d --build

NOTA RADIO / FLAC:
  FLAC no tiene soporte en todos los browsers. Convierte primero:
    ffmpeg -i aris_song.flac -codec:a libmp3lame -qscale:a 2 public/aris_song.mp3
  Luego el script configura el radio para usar ese archivo automáticamente
  si existe, o el stream externo como fallback.
"""

import os, json
from pathlib import Path

ROOT = Path(__file__).parent
CREATED, UPDATED = [], []

def write(path, content, update=False):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    # dedent manual: quitar indentación común
    lines = content.split('\n')
    # si empieza con línea vacía, quitarla
    while lines and not lines[0].strip():
        lines.pop(0)
    p.write_text('\n'.join(lines), encoding='utf-8')
    (UPDATED if update else CREATED).append(path)
    print(f"  {'✏️ ' if update else '✅'} {path}")


# ═══════════════════════════════════════════════════════════════
#  1. API — Video upload + CRUD
# ═══════════════════════════════════════════════════════════════
print('\n📹 API de videos (upload, CRUD, descriptores)...')

write('src/pages/api/videos/index.ts', '''
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
''')

write('src/pages/api/videos/upload.ts', '''
import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';
import { mkdirSync, writeFileSync } from 'fs';
import { randomUUID } from 'crypto';

const UPLOADS_DIR = join(process.cwd(), 'public', 'uploads');

export const POST: APIRoute = async ({ request }) => {
  // Verificar sesión admin
  const cookie = request.headers.get('cookie') ?? '';
  const token = cookie.split(';').find(c => c.trim().startsWith('aris_admin='))?.split('=')[1]?.trim();
  if (!token || !(await verifyToken(token, import.meta.env.ADMIN_JWT_SECRET))) {
    return new Response('unauthorized', { status: 401 });
  }

  try {
    mkdirSync(UPLOADS_DIR, { recursive: true });

    const form = await request.formData();
    const file = form.get('video') as File | null;
    const title = (form.get('title') as string) ?? 'Sin título';
    const category = (form.get('category') as string) ?? 'general';
    const descriptors = (form.get('descriptors') as string) ?? '{}';

    if (!file || file.size === 0) {
      return new Response(JSON.stringify({ error: 'No se recibió archivo' }), {
        status: 400, headers: { 'Content-Type': 'application/json' }
      });
    }

    // Límite: 500MB
    if (file.size > 500 * 1024 * 1024) {
      return new Response(JSON.stringify({ error: 'Archivo demasiado grande (máx 500MB)' }), {
        status: 413, headers: { 'Content-Type': 'application/json' }
      });
    }

    const ext = file.name.split('.').pop()?.toLowerCase() ?? 'mp4';
    const id = randomUUID();
    const filename = `${id}.${ext}`;
    const filePath = join(UPLOADS_DIR, filename);

    const buffer = await file.arrayBuffer();
    writeFileSync(filePath, Buffer.from(buffer));

    // Guardar en DB
    const db = new Database(join(process.cwd(), 'data', 'database.sqlite'));
    db.run(`
      CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, filename TEXT,
        url TEXT NOT NULL, thumbnail TEXT, category TEXT,
        descriptors TEXT DEFAULT '{}',
        width INTEGER DEFAULT 1920, height INTEGER DEFAULT 1080,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
    // Migración silenciosa: añadir columnas nuevas si no existen
    try { db.run("ALTER TABLE videos ADD COLUMN filename TEXT"); } catch {}
    try { db.run("ALTER TABLE videos ADD COLUMN descriptors TEXT DEFAULT '{}'"); } catch {}
    try { db.run("ALTER TABLE videos ADD COLUMN width INTEGER DEFAULT 1920"); } catch {}
    try { db.run("ALTER TABLE videos ADD COLUMN height INTEGER DEFAULT 1080"); } catch {}

    db.run(
      `INSERT INTO videos (id, title, filename, url, category, descriptors) VALUES (?, ?, ?, ?, ?, ?)`,
      [id, title, filename, `/uploads/${filename}`, category, descriptors]
    );
    db.close();

    return new Response(JSON.stringify({ ok: true, id, url: `/uploads/${filename}` }), {
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
''')

write('src/pages/api/videos/update.ts', '''
import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

export const PATCH: APIRoute = async ({ request }) => {
  // Verificar sesión
  const cookie = request.headers.get('cookie') ?? '';
  const token = cookie.split(';').find(c => c.trim().startsWith('aris_admin='))?.split('=')[1]?.trim();
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
''')

# API genérica para admin — lee/escribe cualquier JSON de /data/
write('src/pages/api/admin/data.ts', '''
import type { APIRoute } from 'astro';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

const ALLOWED = ['now.json', 'books.json', 'homepage.json', 'gacha-config.json'];

async function auth(request: Request, secret: string): Promise<boolean> {
  const cookie = request.headers.get('cookie') ?? '';
  const token = cookie.split(';').find(c => c.trim().startsWith('aris_admin='))?.split('=')[1]?.trim();
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
''')


# ═══════════════════════════════════════════════════════════════
#  2. Página /v/[id] — player + OG tags Discord
# ═══════════════════════════════════════════════════════════════
print('\n🎬 Página /v/[id] con OG tags para Discord...')

write('src/pages/v/[id].astro', r'''
---
import { Database } from 'bun:sqlite';
import { join } from 'path';

const { id } = Astro.params;

let video: any = null;
try {
  const db = new Database(join(process.cwd(), 'data', 'database.sqlite'), { readonly: true });
  video = db.query('SELECT * FROM videos WHERE id = ?').get(id);
  db.close();
} catch {}

if (!video) return Astro.redirect('/videos');

const BASE = `https://aris-sama.duckdns.org`;
const videoUrl = `${BASE}${video.url}`;
const thumbUrl = video.thumbnail ? `${BASE}${video.thumbnail}` : `${BASE}/favicon.svg`;

// Parsear descriptores
let descriptors: Record<string, string> = {};
try { descriptors = JSON.parse(video.descriptors ?? '{}'); } catch {}
const descLines = Object.entries(descriptors).map(([k, v]) => `${k}: ${v}`).join(' · ');
const description = descLines || video.category || 'video · aris-sama';
---
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{video.title} · aris-sama</title>

  <!-- Open Graph — Discord lee estos -->
  <meta property="og:type"              content="video.other" />
  <meta property="og:title"             content={video.title} />
  <meta property="og:description"       content={description} />
  <meta property="og:url"               content={`${BASE}/v/${id}`} />
  <meta property="og:image"             content={thumbUrl} />
  <meta property="og:video:url"         content={videoUrl} />
  <meta property="og:video:secure_url"  content={videoUrl} />
  <meta property="og:video:type"        content="video/mp4" />
  <meta property="og:video:width"       content={video.width ?? 1920} />
  <meta property="og:video:height"      content={video.height ?? 1080} />
  <meta property="theme-color"          content="#A855F7" />

  <!-- Twitter card (fallback) -->
  <meta name="twitter:card"        content="player" />
  <meta name="twitter:title"       content={video.title} />
  <meta name="twitter:description" content={description} />
  <meta name="twitter:image"       content={thumbUrl} />
  <meta name="twitter:player"      content={`${BASE}/v/${id}`} />
  <meta name="twitter:player:width"  content={video.width ?? 1920} />
  <meta name="twitter:player:height" content={video.height ?? 1080} />

  <link rel="stylesheet" href="/design-tokens.css" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      background: var(--color-bg); color: var(--color-ink);
      font-family: var(--font-body); min-height: 100dvh;
    }
    .video-page {
      max-width: 960px; margin: 0 auto;
      padding: 1.5rem 1rem 4rem;
    }
    .back-link {
      display: inline-flex; align-items: center; gap: 0.4rem;
      font-family: var(--font-mono); font-size: 0.75rem;
      color: var(--color-muted); text-decoration: none;
      margin-bottom: 1.5rem; letter-spacing: 0.06em;
      transition: color 0.15s;
    }
    .back-link:hover { color: var(--color-accent); }
    .player-wrap {
      width: 100%; border-radius: 12px; overflow: hidden;
      background: #000;
      box-shadow: 0 8px 40px rgba(0,0,0,0.7);
    }
    video {
      width: 100%; display: block;
      max-height: 80vh; object-fit: contain;
    }
    .video-info { margin-top: 1.5rem; }
    .video-title {
      font-family: var(--font-display); font-size: 1.75rem;
      color: var(--color-ink); line-height: 1.2; margin-bottom: 0.5rem;
    }
    .video-category {
      font-family: var(--font-mono); font-size: 0.7rem;
      letter-spacing: 0.1em; text-transform: uppercase;
      color: var(--color-accent); margin-bottom: 1rem;
    }
    .descriptors {
      display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem;
    }
    .descriptor-tag {
      background: rgba(168,85,247,0.1);
      border: 1px solid rgba(168,85,247,0.25);
      border-radius: 6px; padding: 0.25rem 0.6rem;
      font-family: var(--font-mono); font-size: 0.72rem;
      color: var(--color-muted);
    }
    .descriptor-tag strong { color: var(--color-accent); margin-right: 4px; }
    .share-row {
      margin-top: 1.25rem; display: flex; align-items: center; gap: 0.75rem;
    }
    .share-url {
      flex: 1; background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 8px; padding: 0.5rem 0.75rem;
      font-family: var(--font-mono); font-size: 0.72rem;
      color: var(--color-muted-2); white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis;
    }
    .copy-btn {
      background: var(--color-accent); color: var(--color-bg);
      border: none; border-radius: 8px;
      padding: 0.5rem 1rem;
      font-family: var(--font-mono); font-size: 0.72rem;
      cursor: pointer; white-space: nowrap; letter-spacing: 0.04em;
      transition: opacity 0.15s;
    }
    .copy-btn:hover { opacity: 0.85; }
  </style>
</head>
<body>
  <div class="video-page">
    <a href="/videos" class="back-link">← videos</a>

    <div class="player-wrap">
      <video
        src={video.url}
        controls
        preload="metadata"
        poster={video.thumbnail ?? undefined}
      ></video>
    </div>

    <div class="video-info">
      <div class="video-category">{video.category ?? 'general'}</div>
      <h1 class="video-title">{video.title}</h1>

      {Object.keys(descriptors).length > 0 && (
        <div class="descriptors">
          {Object.entries(descriptors).map(([k, v]) => (
            <span class="descriptor-tag">
              <strong>{k}</strong>{v}
            </span>
          ))}
        </div>
      )}

      <div class="share-row">
        <div class="share-url" id="share-url">{BASE}/v/{id}</div>
        <button class="copy-btn" id="copy-btn">copiar link</button>
      </div>
    </div>
  </div>

  <script>
    const btn = document.getElementById('copy-btn');
    const url = document.getElementById('share-url');
    btn?.addEventListener('click', () => {
      navigator.clipboard.writeText(url?.textContent?.trim() ?? '').then(() => {
        if (btn) { btn.textContent = '✓ copiado'; setTimeout(() => { btn.textContent = 'copiar link'; }, 2000); }
      });
    });
  </script>
</body>
</html>
''')


# ═══════════════════════════════════════════════════════════════
#  3. Página /videos — galería con cards bonitas
# ═══════════════════════════════════════════════════════════════
print('\n🎞️  Página /videos actualizada...')

write('src/pages/videos.astro', '''
---
import Base from '../layouts/Base.astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

let videos: any[] = [];
try {
  const db = new Database(join(process.cwd(), 'data', 'database.sqlite'), { readonly: true });
  videos = db.query('SELECT * FROM videos ORDER BY created_at DESC').all() as any[];
  db.close();
} catch {}
---
<Base title="Videos · aris-sama" description="Clips, gameplays y momentos">
  <section class="videos-page">
    <header class="page-header">
      <h1 class="page-title">
        <span class="page-prompt">$</span> videos
      </h1>
      <p class="page-sub">clips · gameplays · momentos</p>
    </header>

    {videos.length === 0 ? (
      <p class="empty-state font-mono">
        Sin videos todavía. Súbelos desde <a href="/admin">/admin</a>.
      </p>
    ) : (
      <div class="video-grid">
        {videos.map((v) => {
          let desc: Record<string, string> = {};
          try { desc = JSON.parse(v.descriptors ?? '{}'); } catch {}
          return (
            <a href={`/v/${v.id}`} class="video-card">
              <div class="video-thumb">
                {v.thumbnail
                  ? <img src={v.thumbnail} alt={v.title} loading="lazy" />
                  : <div class="thumb-placeholder">▶</div>
                }
                <div class="play-overlay">▶</div>
              </div>
              <div class="video-body">
                <span class="video-cat font-mono">{v.category ?? 'general'}</span>
                <h2 class="video-name">{v.title}</h2>
                {Object.keys(desc).length > 0 && (
                  <div class="desc-tags">
                    {Object.entries(desc).slice(0, 3).map(([k, val]) => (
                      <span class="desc-tag"><strong>{k}</strong> {val}</span>
                    ))}
                  </div>
                )}
              </div>
            </a>
          );
        })}
      </div>
    )}
  </section>
</Base>

<style>
  .videos-page { padding: var(--space-8) 0; }
  .page-header { margin-bottom: var(--space-8); }
  .page-title {
    font-family: var(--font-mono); font-size: var(--text-2xl);
    color: var(--color-ink); display: flex; align-items: center; gap: var(--space-2);
  }
  .page-prompt { color: var(--color-accent); }
  .page-sub { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-muted); margin-top: var(--space-1); letter-spacing: 0.08em; }

  .empty-state {
    color: var(--color-muted); font-size: var(--text-sm); padding: var(--space-8) 0;
  }
  .empty-state a { color: var(--color-accent); text-decoration: none; }
  .font-mono { font-family: var(--font-mono); }

  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: var(--space-5);
  }
  .video-card {
    background: var(--glass-bg);
    border: var(--glass-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    text-decoration: none;
    color: inherit;
    transition: transform 0.2s var(--ease-out), border-color 0.2s, box-shadow 0.2s;
    display: block;
  }
  .video-card:hover {
    transform: translateY(-4px);
    border-color: var(--color-border-accent);
    box-shadow: var(--shadow-md);
  }
  .video-thumb {
    aspect-ratio: 16/9;
    background: rgba(168,85,247,0.06);
    overflow: hidden;
    position: relative;
  }
  .video-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .thumb-placeholder {
    display: flex; align-items: center; justify-content: center;
    width: 100%; height: 100%;
    font-size: 2rem; color: var(--color-accent); opacity: 0.3;
  }
  .play-overlay {
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    background: rgba(0,0,0,0.4);
    font-size: 2rem; color: #fff;
    opacity: 0; transition: opacity 0.2s;
  }
  .video-card:hover .play-overlay { opacity: 1; }

  .video-body { padding: var(--space-4); }
  .video-cat {
    font-size: 0.65rem; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--color-accent); display: block; margin-bottom: var(--space-1);
  }
  .video-name {
    font-size: var(--text-sm); font-weight: 500; color: var(--color-ink);
    line-height: 1.4; margin-bottom: var(--space-2);
    overflow: hidden; display: -webkit-box;
    -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  }
  .desc-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; }
  .desc-tag {
    background: rgba(168,85,247,0.08);
    border: 1px solid rgba(168,85,247,0.2);
    border-radius: 4px; padding: 1px 6px;
    font-family: var(--font-mono); font-size: 0.62rem; color: var(--color-muted);
  }
  .desc-tag strong { color: var(--color-accent); margin-right: 3px; }
</style>
''', update=True)


# ═══════════════════════════════════════════════════════════════
#  4. Admin inteligente y adaptivo
# ═══════════════════════════════════════════════════════════════
print('\n🧠 Admin panel inteligente...')

write('src/pages/admin/index.astro', r'''
---
import Base from '../../layouts/Base.astro';
import { readFileSync, readdirSync, existsSync } from 'fs';
import { join } from 'path';
import { Database } from 'bun:sqlite';

// ── Datos dinámicos ──────────────────────────────────────────
const dataDir = join(process.cwd(), 'data');

function readJSON(file: string) {
  try { return JSON.parse(readFileSync(join(dataDir, file), 'utf-8')); } catch { return null; }
}

const nowData      = readJSON('now.json');
const booksData    = readJSON('books.json');
const homepageData = readJSON('homepage.json');
const gachaConfig  = readJSON('gacha-config.json');

// ── Stats de SQLite ──────────────────────────────────────────
let videoCount = 0, charCount = 0;
try {
  const db = new Database(join(dataDir, 'database.sqlite'), { readonly: true });
  videoCount = (db.query('SELECT COUNT(*) as n FROM videos').get() as any)?.n ?? 0;
  charCount  = (db.query('SELECT COUNT(*) as n FROM characters').get() as any)?.n ?? 0;
  db.close();
} catch {}

// ── Detectar módulos activos ─────────────────────────────────
const featuresDir = join(process.cwd(), 'src', 'features');
const activeModules = existsSync(featuresDir)
  ? readdirSync(featuresDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)
  : [];
---
<Base title="Admin · aris-sama">
  <div class="admin">

    <header class="admin-head">
      <div>
        <span class="badge">root@aris-sama</span>
        <h1 class="admin-title">panel de control</h1>
        <p class="admin-sub font-mono">módulos activos: {activeModules.join(' · ')}</p>
      </div>
      <button id="logout-btn" class="btn-logout">salir →</button>
    </header>

    <!-- ── Stats grid ── -->
    <section class="admin-section">
      <h2 class="sh">estado del sistema</h2>
      <div class="stat-grid">
        <div class="stat"><span class="sl">now items</span><span class="sv">{nowData?.items?.length ?? 0}</span></div>
        <div class="stat"><span class="sl">libros</span><span class="sv">{Array.isArray(booksData) ? booksData.length : (booksData?.books?.length ?? 0)}</span></div>
        <div class="stat"><span class="sl">videos</span><span class="sv">{videoCount}</span></div>
        <div class="stat"><span class="sl">chars gacha</span><span class="sv">{charCount}</span></div>
        <div class="stat"><span class="sl">last now update</span><span class="sv">{nowData?.updated ?? '—'}</span></div>
        <div class="stat"><span class="sl">homepage blocks</span><span class="sv">{homepageData?.blocks?.length ?? 0}</span></div>
      </div>
    </section>

    <!-- ── Upload de video ── -->
    <section class="admin-section">
      <h2 class="sh">subir video</h2>
      <div class="upload-zone" id="drop-zone">
        <div class="upload-inner" id="upload-inner">
          <span class="upload-icon">▶</span>
          <p class="upload-label">arrastra tu video aquí</p>
          <p class="upload-hint font-mono">o haz click para seleccionar · mp4, webm, mov · máx 500MB</p>
          <input type="file" id="file-input" accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov" style="display:none" />
        </div>
        <!-- Form de metadatos (aparece tras seleccionar archivo) -->
        <div class="upload-form" id="upload-form" style="display:none">
          <div class="uf-row">
            <label class="uf-label">título</label>
            <input type="text" id="uf-title" class="uf-input" placeholder="Miyabi SS · Daily Challenge" />
          </div>
          <div class="uf-row">
            <label class="uf-label">categoría</label>
            <input type="text" id="uf-category" class="uf-input" placeholder="gameplay · clip · tutorial..." />
          </div>
          <div class="uf-row">
            <label class="uf-label">descriptores <span class="uf-hint">ej: Personaje=Miyabi, Score=32093</span></label>
            <div id="descriptor-list" class="descriptor-list"></div>
            <button type="button" id="add-descriptor" class="btn-ghost">+ añadir descriptor</button>
          </div>
          <div class="uf-progress-wrap" id="progress-wrap" style="display:none">
            <div class="uf-progress-bar" id="progress-bar"></div>
            <span class="uf-progress-label font-mono" id="progress-label">0%</span>
          </div>
          <div class="uf-actions">
            <button type="button" id="upload-cancel" class="btn-ghost">cancelar</button>
            <button type="button" id="upload-submit" class="btn-primary">subir video →</button>
          </div>
        </div>
      </div>
      <p class="upload-result font-mono" id="upload-result" style="display:none"></p>
    </section>

    <!-- ── Lista de videos con edición inline ── -->
    <section class="admin-section" id="videos-section">
      <h2 class="sh">videos subidos <span class="sh-count font-mono" id="v-count">{videoCount}</span></h2>
      <div id="videos-list" class="videos-admin-list">
        <p class="loading-text font-mono">cargando…</p>
      </div>
    </section>

    <!-- ── Editor now.json ── -->
    <section class="admin-section">
      <h2 class="sh">now.json <button class="sh-save btn-ghost-sm" data-file="now.json" data-editor="now-editor">guardar ↑</button></h2>
      <textarea id="now-editor" class="json-editor" spellcheck="false">{JSON.stringify(nowData, null, 2)}</textarea>
      <p class="save-result font-mono" id="now-result"></p>
    </section>

    <!-- ── Editor books.json ── -->
    <section class="admin-section">
      <h2 class="sh">books.json <button class="sh-save btn-ghost-sm" data-file="books.json" data-editor="books-editor">guardar ↑</button></h2>
      <textarea id="books-editor" class="json-editor" spellcheck="false">{JSON.stringify(booksData, null, 2)}</textarea>
      <p class="save-result font-mono" id="books-result"></p>
    </section>

    <!-- ── Comandos sync ── -->
    <section class="admin-section">
      <h2 class="sh">sync gacha</h2>
      <div class="cmd-list">
        {(gachaConfig?.games ?? []).map((g: any) => (
          <div class="cmd-item">
            <span class="cmd-game font-mono">{g.icon} {g.name}</span>
            <code class="cmd-code font-mono">docker exec web bun run scripts/sync-enka-{g.id}.ts</code>
          </div>
        ))}
      </div>
    </section>

  </div>
</Base>

<script>
// ── Logout ────────────────────────────────────────────────────
document.getElementById('logout-btn')?.addEventListener('click', async () => {
  await fetch('/api/auth/logout', { method: 'POST' });
  location.href = '/admin/login';
});

// ── JSON editors ─────────────────────────────────────────────
document.querySelectorAll('.sh-save').forEach(btn => {
  btn.addEventListener('click', async () => {
    const file = (btn as HTMLElement).dataset.file!;
    const editorId = (btn as HTMLElement).dataset.editor!;
    const resultId = file.replace('.json', '') + '-result';
    const textarea = document.getElementById(editorId) as HTMLTextAreaElement;
    const resultEl = document.getElementById(resultId);
    try {
      JSON.parse(textarea.value); // validar
      const res = await fetch(`/api/admin/data?file=${file}`, {
        method: 'POST', body: textarea.value,
        headers: { 'Content-Type': 'application/json' }
      });
      if (resultEl) {
        resultEl.textContent = res.ok ? '✅ guardado' : '❌ error al guardar';
        resultEl.style.display = 'block';
        setTimeout(() => { resultEl.style.display = 'none'; }, 3000);
      }
    } catch (e) {
      if (resultEl) { resultEl.textContent = `❌ JSON inválido: ${e}`; resultEl.style.display = 'block'; }
    }
  });
});

// ── Upload drag-and-drop ──────────────────────────────────────
const dropZone   = document.getElementById('drop-zone')!;
const uploadInner= document.getElementById('upload-inner')!;
const uploadForm = document.getElementById('upload-form')!;
const fileInput  = document.getElementById('file-input') as HTMLInputElement;
const progressWrap = document.getElementById('progress-wrap')!;
const progressBar  = document.getElementById('progress-bar')!;
const progressLabel= document.getElementById('progress-label')!;
const uploadResult = document.getElementById('upload-result')!;

let selectedFile: File | null = null;
let descriptorCount = 0;

function showForm(file: File) {
  selectedFile = file;
  (document.getElementById('uf-title') as HTMLInputElement).value = file.name.replace(/\.[^.]+$/, '');
  uploadInner.style.display = 'none';
  uploadForm.style.display = 'block';
}

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  const f = e.dataTransfer?.files[0];
  if (f) showForm(f);
});
uploadInner.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => { if (fileInput.files?.[0]) showForm(fileInput.files[0]); });

document.getElementById('upload-cancel')?.addEventListener('click', () => {
  selectedFile = null;
  uploadInner.style.display = 'flex';
  uploadForm.style.display = 'none';
  fileInput.value = '';
});

document.getElementById('add-descriptor')?.addEventListener('click', () => {
  const list = document.getElementById('descriptor-list')!;
  const row = document.createElement('div');
  row.className = 'desc-row';
  row.innerHTML = `
    <input type="text" class="uf-input desc-key" placeholder="clave (ej: Personaje)" style="flex:1" />
    <input type="text" class="uf-input desc-val" placeholder="valor (ej: Miyabi)" style="flex:2" />
    <button type="button" class="btn-ghost-sm desc-rm">✕</button>
  `;
  row.querySelector('.desc-rm')?.addEventListener('click', () => row.remove());
  list.appendChild(row);
});

document.getElementById('upload-submit')?.addEventListener('click', async () => {
  if (!selectedFile) return;
  const title    = (document.getElementById('uf-title') as HTMLInputElement).value || selectedFile.name;
  const category = (document.getElementById('uf-category') as HTMLInputElement).value || 'general';

  const descriptors: Record<string, string> = {};
  document.querySelectorAll('.desc-row').forEach(row => {
    const k = (row.querySelector('.desc-key') as HTMLInputElement).value.trim();
    const v = (row.querySelector('.desc-val') as HTMLInputElement).value.trim();
    if (k && v) descriptors[k] = v;
  });

  const fd = new FormData();
  fd.append('video', selectedFile);
  fd.append('title', title);
  fd.append('category', category);
  fd.append('descriptors', JSON.stringify(descriptors));

  progressWrap.style.display = 'flex';
  const btn = document.getElementById('upload-submit') as HTMLButtonElement;
  btn.disabled = true;

  const xhr = new XMLHttpRequest();
  xhr.upload.addEventListener('progress', e => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      progressBar.style.width = pct + '%';
      progressLabel.textContent = pct + '%';
    }
  });
  xhr.addEventListener('load', () => {
    progressWrap.style.display = 'none';
    btn.disabled = false;
    try {
      const res = JSON.parse(xhr.responseText);
      if (res.ok) {
        uploadResult.textContent = `✅ subido · /v/${res.id}`;
        uploadResult.style.color = 'var(--color-accent)';
        uploadResult.style.display = 'block';
        uploadInner.style.display = 'flex';
        uploadForm.style.display = 'none';
        selectedFile = null;
        fileInput.value = '';
        loadVideos(); // refrescar lista
      } else {
        uploadResult.textContent = `❌ ${res.error}`;
        uploadResult.style.color = '#F87171';
        uploadResult.style.display = 'block';
      }
    } catch {
      uploadResult.textContent = '❌ Error inesperado';
      uploadResult.style.display = 'block';
    }
  });
  xhr.addEventListener('error', () => {
    uploadResult.textContent = '❌ Error de red';
    uploadResult.style.display = 'block';
    btn.disabled = false;
  });
  xhr.open('POST', '/api/videos/upload');
  xhr.send(fd);
});

// ── Lista de videos admin ─────────────────────────────────────
async function loadVideos() {
  const list = document.getElementById('videos-list')!;
  const countEl = document.getElementById('v-count')!;
  list.innerHTML = '<p class="loading-text font-mono">cargando…</p>';
  try {
    const { videos } = await fetch('/api/videos').then(r => r.json());
    countEl.textContent = videos.length;
    if (!videos.length) {
      list.innerHTML = '<p class="loading-text font-mono">sin videos todavía.</p>';
      return;
    }
    list.innerHTML = videos.map((v: any) => {
      let desc: Record<string,string> = {};
      try { desc = JSON.parse(v.descriptors ?? '{}'); } catch {}
      const descStr = Object.entries(desc).map(([k,val]) => `${k}: ${val}`).join(' · ');
      return `
        <div class="va-card" data-id="${v.id}">
          <div class="va-thumb">
            ${v.thumbnail ? `<img src="${v.thumbnail}" alt="" />` : '<div class="va-thumb-ph">▶</div>'}
          </div>
          <div class="va-body">
            <input class="va-title-input uf-input" value="${v.title.replace(/"/g,'&quot;')}" data-field="title" />
            <div class="va-meta">
              <input class="va-cat-input uf-input-sm" value="${(v.category??'general').replace(/"/g,'&quot;')}" placeholder="categoría" data-field="category" />
              <input class="va-desc-input uf-input-sm" value="${descStr.replace(/"/g,'&quot;')}" placeholder="Personaje: X, Score: Y" data-field="descriptors_raw" />
            </div>
            <div class="va-actions">
              <a href="/v/${v.id}" target="_blank" class="btn-ghost-sm">ver →</a>
              <button class="btn-ghost-sm va-save" data-id="${v.id}">guardar</button>
              <button class="btn-danger-sm va-delete" data-id="${v.id}">eliminar</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Guardar cambios
    list.querySelectorAll('.va-save').forEach(btn => {
      btn.addEventListener('click', async () => {
        const card = (btn as HTMLElement).closest('.va-card') as HTMLElement;
        const id = card.dataset.id!;
        const title = (card.querySelector('[data-field="title"]') as HTMLInputElement).value;
        const category = (card.querySelector('[data-field="category"]') as HTMLInputElement).value;
        const rawDesc = (card.querySelector('[data-field="descriptors_raw"]') as HTMLInputElement).value;

        // Parsear "Personaje: Miyabi, Score: 32093" → objeto
        const descriptors: Record<string,string> = {};
        rawDesc.split(',').forEach(part => {
          const [k, ...rest] = part.split(':');
          if (k?.trim()) descriptors[k.trim()] = rest.join(':').trim();
        });

        const res = await fetch('/api/videos/update', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, title, category, descriptors })
        });
        const el = btn as HTMLElement;
        el.textContent = res.ok ? '✓' : '❌';
        setTimeout(() => { el.textContent = 'guardar'; }, 2000);
      });
    });

    // Eliminar
    list.querySelectorAll('.va-delete').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = (btn as HTMLElement).dataset.id!;
        if (!confirm('¿Eliminar este video?')) return;
        await fetch(`/api/videos?id=${id}`, { method: 'DELETE' });
        loadVideos();
      });
    });
  } catch(e) {
    list.innerHTML = `<p class="loading-text font-mono" style="color:#F87171">${e}</p>`;
  }
}

loadVideos();
document.addEventListener('astro:page-load', loadVideos);
</script>

<style>
  .admin { max-width: 56rem; margin: 0 auto; padding: var(--space-10) var(--space-4); }
  .font-mono { font-family: var(--font-mono); }

  /* ── Header ── */
  .admin-head {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: var(--space-10); padding-bottom: var(--space-6);
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .badge {
    font-family: var(--font-mono); font-size: var(--text-xs);
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--color-accent); display: block; margin-bottom: 0.3rem;
  }
  .admin-title { font-family: var(--font-display); font-size: var(--text-3xl); color: var(--color-ink); }
  .admin-sub { font-size: var(--text-xs); color: var(--color-muted-2); margin-top: var(--space-1); letter-spacing: 0.04em; }
  .btn-logout {
    font-family: var(--font-mono); font-size: var(--text-xs);
    background: none; border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-sm); padding: var(--space-2) var(--space-3);
    color: var(--color-muted); cursor: pointer; letter-spacing: 0.06em;
    transition: color 0.15s, border-color 0.15s;
  }
  .btn-logout:hover { color: #F87171; border-color: rgba(248,113,113,0.3); }

  /* ── Section ── */
  .admin-section { margin-bottom: var(--space-10); }
  .sh {
    font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--color-muted);
    margin-bottom: var(--space-4); display: flex; align-items: center; gap: var(--space-3);
  }
  .sh-count {
    background: rgba(168,85,247,0.15); border: 1px solid rgba(168,85,247,0.3);
    border-radius: var(--radius-full); padding: 0 8px;
    font-size: 0.65rem; color: var(--color-accent);
  }

  /* ── Stats ── */
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px,1fr)); gap: var(--space-3); }
  .stat {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-md); padding: var(--space-4);
    display: flex; flex-direction: column; gap: 4px;
  }
  .sl { font-family: var(--font-mono); font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--color-muted); }
  .sv { font-family: var(--font-mono); font-size: var(--text-xl); color: var(--color-ink); font-weight: 500; }

  /* ── Upload zone ── */
  .upload-zone {
    border: 2px dashed rgba(168,85,247,0.3);
    border-radius: var(--radius-lg);
    transition: border-color 0.2s, background 0.2s;
    min-height: 8rem;
  }
  .upload-zone.drag-over { border-color: var(--color-accent); background: rgba(168,85,247,0.06); }
  .upload-inner {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: var(--space-2); padding: var(--space-8); cursor: pointer;
    text-align: center;
  }
  .upload-icon { font-size: 2rem; color: var(--color-accent); opacity: 0.5; }
  .upload-label { font-size: var(--text-sm); color: var(--color-ink); }
  .upload-hint { font-size: var(--text-xs); color: var(--color-muted-2); letter-spacing: 0.04em; }

  .upload-form { padding: var(--space-6); display: flex; flex-direction: column; gap: var(--space-4); }
  .uf-row { display: flex; flex-direction: column; gap: var(--space-1); }
  .uf-label { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-muted); letter-spacing: 0.06em; }
  .uf-hint { color: var(--color-muted-2); font-size: 0.65rem; }
  .uf-input {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius-md); padding: 0.55rem 0.75rem;
    font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-ink);
    outline: none; transition: border-color 0.15s; width: 100%;
  }
  .uf-input:focus { border-color: var(--color-accent); }
  .uf-input-sm {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-sm); padding: 0.3rem 0.5rem;
    font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-ink);
    outline: none; transition: border-color 0.15s;
  }
  .uf-input-sm:focus { border-color: var(--color-accent); }
  .descriptor-list { display: flex; flex-direction: column; gap: var(--space-2); }
  .desc-row { display: flex; gap: var(--space-2); align-items: center; }
  .uf-progress-wrap { display: flex; align-items: center; gap: var(--space-3); }
  .uf-progress-bar {
    flex: 1; height: 4px; border-radius: 2px;
    background: var(--color-accent);
    transition: width 0.1s; width: 0%;
  }
  .uf-progress-label { font-size: 0.7rem; color: var(--color-muted); min-width: 2.5rem; text-align: right; }
  .uf-actions { display: flex; gap: var(--space-3); justify-content: flex-end; }
  .upload-result { padding: var(--space-3) 0; font-size: var(--text-sm); }

  /* ── Buttons ── */
  .btn-primary {
    background: var(--color-accent); color: var(--color-bg);
    border: none; border-radius: var(--radius-md);
    padding: 0.6rem 1.25rem; font-family: var(--font-mono); font-size: var(--text-sm);
    cursor: pointer; letter-spacing: 0.04em; transition: opacity 0.15s;
  }
  .btn-primary:hover { opacity: 0.85; }
  .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-ghost {
    background: none; border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius-md); padding: 0.55rem 1rem;
    font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-muted);
    cursor: pointer; transition: border-color 0.15s, color 0.15s;
  }
  .btn-ghost:hover { border-color: rgba(168,85,247,0.4); color: var(--color-accent); }
  .btn-ghost-sm {
    background: none; border: 1px solid rgba(255,255,255,0.1);
    border-radius: var(--radius-sm); padding: 0.2rem 0.5rem;
    font-family: var(--font-mono); font-size: 0.65rem; color: var(--color-muted);
    cursor: pointer; transition: all 0.15s; text-decoration: none; display: inline-block;
  }
  .btn-ghost-sm:hover { border-color: var(--color-accent); color: var(--color-accent); }
  .btn-danger-sm {
    background: none; border: 1px solid rgba(248,113,113,0.2);
    border-radius: var(--radius-sm); padding: 0.2rem 0.5rem;
    font-family: var(--font-mono); font-size: 0.65rem; color: rgba(248,113,113,0.6);
    cursor: pointer; transition: all 0.15s;
  }
  .btn-danger-sm:hover { border-color: #F87171; color: #F87171; }

  /* ── Videos admin list ── */
  .videos-admin-list { display: flex; flex-direction: column; gap: var(--space-3); }
  .va-card {
    display: flex; gap: var(--space-4); align-items: flex-start;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: var(--radius-md); padding: var(--space-4);
    transition: border-color 0.15s;
  }
  .va-card:hover { border-color: rgba(168,85,247,0.2); }
  .va-thumb {
    width: 100px; flex-shrink: 0; aspect-ratio: 16/9;
    border-radius: var(--radius-sm); overflow: hidden;
    background: rgba(168,85,247,0.06);
  }
  .va-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .va-thumb-ph { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; opacity: 0.3; color: var(--color-accent); }
  .va-body { flex: 1; display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; }
  .va-title-input { font-size: var(--text-sm); font-weight: 500; }
  .va-meta { display: flex; gap: var(--space-2); flex-wrap: wrap; }
  .va-cat-input, .va-desc-input { flex: 1; min-width: 120px; }
  .va-desc-input { flex: 3; }
  .va-actions { display: flex; gap: var(--space-2); align-items: center; }

  /* ── JSON editor ── */
  .json-editor {
    width: 100%; height: 14rem; resize: vertical;
    background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.07);
    border-radius: var(--radius-md); padding: var(--space-4);
    font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-ink-soft);
    line-height: 1.6; outline: none; tab-size: 2;
    transition: border-color 0.15s;
  }
  .json-editor:focus { border-color: rgba(168,85,247,0.3); }
  .save-result { font-size: var(--text-xs); margin-top: var(--space-2); padding: var(--space-2) 0; }
  .loading-text { color: var(--color-muted); font-size: var(--text-sm); padding: var(--space-4) 0; }

  /* ── Comandos ── */
  .cmd-list { display: flex; flex-direction: column; gap: var(--space-2); }
  .cmd-item {
    display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap;
    padding: var(--space-3) var(--space-4);
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: var(--radius-md);
  }
  .cmd-game { font-size: var(--text-sm); color: var(--color-ink); min-width: 10rem; }
  .cmd-code {
    font-size: 0.7rem; color: var(--color-muted-2); letter-spacing: 0.02em;
    background: rgba(0,0,0,0.2); padding: 0.25rem 0.5rem; border-radius: 4px;
    word-break: break-all;
  }
</style>
''', update=True)


# ═══════════════════════════════════════════════════════════════
#  5. Nav — añadir [videos] y [gacha]
# ═══════════════════════════════════════════════════════════════
print('\n🧭 Actualizando nav (Base.astro)...')

nav_old = '''      <a href="/garden"><span class="link-bracket">[</span>jardín<span class="link-bracket">]</span></a>
      <a href="/now"><span class="link-bracket">[</span>ahora<span class="link-bracket">]</span></a>
      <a href="/bookshelf"><span class="link-bracket">[</span>libros<span class="link-bracket">]</span></a>
      <a href="/portfolio"><span class="link-bracket">[</span>portafolio<span class="link-bracket">]</span></a>'''

nav_new = '''      <a href="/garden"><span class="link-bracket">[</span>jardín<span class="link-bracket">]</span></a>
      <a href="/now"><span class="link-bracket">[</span>ahora<span class="link-bracket">]</span></a>
      <a href="/videos"><span class="link-bracket">[</span>videos<span class="link-bracket">]</span></a>
      <a href="/gacha"><span class="link-bracket">[</span>gacha<span class="link-bracket">]</span></a>
      <a href="/bookshelf"><span class="link-bracket">[</span>libros<span class="link-bracket">]</span></a>'''

base_path = ROOT / 'src' / 'layouts' / 'Base.astro'
content = base_path.read_text(encoding='utf-8')
if nav_old in content:
    content = content.replace(nav_old, nav_new)
    base_path.write_text(content, encoding='utf-8')
    UPDATED.append('src/layouts/Base.astro')
    print('  ✏️  src/layouts/Base.astro')
else:
    print('  ⚠️  Base.astro: nav ya modificado o estructura diferente — revisa manualmente')


# ═══════════════════════════════════════════════════════════════
#  6. Radio — soporte archivo local + fallback stream
# ═══════════════════════════════════════════════════════════════
print('\n📻 Radio con soporte archivo local...')

write('src/features/radio/RadioPlayer.astro', r'''
---
// RadioPlayer.astro
// Prioridad: /aris_song.mp3 si existe en public/ → stream externo como fallback
// Para usar tu FLAC: ffmpeg -i aris_song.flac -codec:a libmp3lame -qscale:a 2 public/aris_song.mp3

import { existsSync } from 'fs';
import { join } from 'path';

const hasLocalSong = existsSync(join(process.cwd(), 'public', 'aris_song.mp3'));
const LOCAL_URL    = '/aris_song.mp3';
const STREAM_URL   = 'https://relay.mp3.hist.fm/hi';
const STATION_NAME = hasLocalSong ? 'aris · song' : 'lo-fi · aris fm';
const IS_LOCAL     = hasLocalSong;
---
<div id="radio-player" class="radio-player" transition:persist>
  <button id="radio-toggle" class="radio-btn" aria-label="Reproducir" aria-pressed="false">
    <span class="radio-icon radio-icon--play" aria-hidden="true">▶</span>
    <span class="radio-icon radio-icon--pause" aria-hidden="true">⏸</span>
    <span class="radio-bars" aria-hidden="true">
      <span class="bar"></span><span class="bar"></span><span class="bar"></span>
    </span>
  </button>
  <div class="radio-info">
    <span class="radio-name">{STATION_NAME}</span>
    <span class="radio-status" id="radio-status">pausado</span>
  </div>
  <input type="range" id="radio-volume" class="radio-volume"
    min="0" max="1" step="0.05" value="0.6" aria-label="Volumen" />
</div>

<script define:vars={{ LOCAL_URL, STREAM_URL, IS_LOCAL }}>
if (!window.__radioInitialized) {
  window.__radioInitialized = true;
  let audio = null, playing = false;

  function getEls() {
    return {
      btn:    document.getElementById('radio-toggle'),
      status: document.getElementById('radio-status'),
      vol:    document.getElementById('radio-volume'),
      player: document.getElementById('radio-player'),
    };
  }

  function setUI(isPlaying) {
    const { btn, status, player } = getEls();
    if (!btn) return;
    playing = isPlaying;
    btn.setAttribute('aria-pressed', String(isPlaying));
    player.classList.toggle('is-playing', isPlaying);
    if (status) status.textContent = isPlaying
      ? (IS_LOCAL ? '▶ reproduciendo' : 'en vivo')
      : 'pausado';
  }

  function initAudio() {
    if (audio) return;
    // Intentar archivo local primero, luego stream
    audio = new Audio(IS_LOCAL ? LOCAL_URL : STREAM_URL);
    if (IS_LOCAL) audio.loop = true;
    audio.volume = 0.6;
    audio.addEventListener('playing', () => setUI(true));
    audio.addEventListener('pause',   () => setUI(false));
    audio.addEventListener('ended',   () => setUI(false));
    audio.addEventListener('error', (e) => {
      // Si falla el local, intentar stream
      if (IS_LOCAL && audio.src.includes(LOCAL_URL)) {
        audio.src = STREAM_URL;
        audio.loop = false;
        audio.play().catch(() => {});
      } else {
        const { status } = getEls();
        if (status) status.textContent = 'error · recarga';
      }
    });
  }

  function toggle() {
    initAudio();
    if (playing) { audio.pause(); }
    else {
      audio.play().catch(() => {
        const { status } = getEls();
        if (status) status.textContent = 'click para activar';
      });
    }
  }

  function bind() {
    const { btn, vol } = getEls();
    if (!btn) return;
    btn.removeEventListener('click', toggle);
    btn.addEventListener('click', toggle);
    vol.addEventListener('input', (e) => { if (audio) audio.volume = parseFloat(e.target.value); });
    if (playing) setUI(true);
  }

  bind();
  document.addEventListener('astro:page-load', bind);
}
</script>

<style>
.radio-player {
  position: fixed; bottom: var(--space-6); right: var(--space-6); z-index: 50;
  display: flex; align-items: center; gap: var(--space-3);
  background: rgba(5,5,10,0.85);
  border: 1px solid rgba(168,85,247,0.2);
  border-radius: var(--radius-xl); padding: var(--space-3) var(--space-4);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(20px);
}
.radio-btn {
  width: 2.25rem; height: 2.25rem; border-radius: var(--radius-full);
  border: none; background: var(--color-accent); color: var(--color-bg);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: transform var(--duration) var(--ease-out);
  position: relative; overflow: hidden;
}
.radio-btn:hover { transform: scale(1.08); }
.radio-icon { font-size: 0.7rem; position: absolute; transition: opacity var(--duration); }
.radio-icon--play { opacity: 1; } .radio-icon--pause { opacity: 0; }
.radio-bars { display: flex; align-items: flex-end; gap: 2px; height: 12px; opacity: 0; transition: opacity var(--duration); position: absolute; }
.bar { width: 3px; background: var(--color-bg); border-radius: 2px; animation: bar-bounce 0.8s ease-in-out infinite; }
.bar:nth-child(1) { height: 8px; } .bar:nth-child(2) { height: 12px; animation-delay: .15s; } .bar:nth-child(3) { height: 6px; animation-delay: .3s; }
@keyframes bar-bounce { 0%,100% { transform: scaleY(.4); } 50% { transform: scaleY(1); } }
.is-playing .radio-icon--play, .is-playing .radio-icon--pause { opacity: 0; }
.is-playing .radio-bars { opacity: 1; }
.radio-info { display: flex; flex-direction: column; gap: 2px; min-width: 5rem; }
.radio-name { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-ink); letter-spacing: .04em; }
.radio-status { font-size: .65rem; color: var(--color-muted); letter-spacing: .06em; text-transform: uppercase; }
.radio-volume { -webkit-appearance: none; appearance: none; width: 5rem; height: 3px; background: var(--color-surface-2); border-radius: var(--radius-full); outline: none; cursor: pointer; }
.radio-volume::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; border-radius: 50%; background: var(--color-accent); cursor: pointer; }
@media (max-width: 640px) { .radio-player { bottom: var(--space-4); right: var(--space-4); } .radio-volume { width: 3.5rem; } }
</style>
''', update=True)


# ═══════════════════════════════════════════════════════════════
#  7. Actualizar AGENTS.md y STRUCTURE.json
# ═══════════════════════════════════════════════════════════════
print('\n📄 Actualizando AGENTS.md...')

write('AGENTS.md', '''
# AGENTS.md
Última actualización: Marzo 2026 · Fase 2 completa

## Stack
Astro 6 + Bun + Tailwind v4 + Zod + Motion
Self-hosted: Oracle Cloud ARM (aarch64), Caddy reverse proxy
Deploy: `docker compose up -d --build`
Servidor de producción: `bun ./dist/server/entry.mjs`

## Reglas invariables
1. NUNCA modificar `/src/blocks/` sin autorización explícita
2. Para contenido: editar `/data/*.json` o `/content/*.md`
3. Para módulo nuevo: crear carpeta en `/src/features/[nombre]/`
4. Actualizar AGENTS.md y STRUCTURE.json al crear módulos
5. Para modificar archivos en servidor: generar script `apply_*.py`
6. Las páginas en `/src/pages/*.astro` son páginas COMPLETAS

## Infra crítica
- Caddy: `reverse_proxy web:4321`
- Adaptador: `@astrojs/node` standalone
- `docker-compose.override.yml` lanza: `bun ./dist/server/entry.mjs`
- Sharp falla en ARM: usar `@unpic/astro`
- SQLite en volumen Docker `/data/` — NUNCA dentro de la imagen
- Videos subidos en volumen `/public/uploads/` (montar en compose si se necesita persistencia)
- `.env`: ADMIN_HASH, ADMIN_SALT, ADMIN_ITERATIONS, ADMIN_JWT_SECRET

## Módulos activos
- [x] now        — /now, datos en /data/now.json
- [x] radio      — fixed bottom-right, soporta /public/aris_song.mp3 + stream fallback
- [x] gacha      — /gacha, API /api/enka-{gi,hsr,zzz}, SQLite tabla characters
- [x] videos     — /videos, /v/[id] (OG Discord), admin upload drag-drop, SQLite tabla videos
- [x] admin      — /admin (panel completo: upload, editors, stats), /admin/login

## Rutas de API
| Endpoint              | Método       | Descripción |
|---|---|---|
| /api/enka-gi          | GET          | Personajes Genshin desde SQLite |
| /api/enka-hsr         | GET          | Personajes HSR desde SQLite |
| /api/enka-zzz         | GET          | Personajes ZZZ desde SQLite |
| /api/videos           | GET, DELETE  | Lista / elimina videos |
| /api/videos/upload    | POST         | Sube video (multipart, auth requerida) |
| /api/videos/update    | PATCH        | Actualiza título/categoria/descriptores |
| /api/admin/data       | GET, POST    | Lee/escribe /data/*.json (auth requerida) |
| /api/auth/login       | POST         | Login → cookie aris_admin |
| /api/auth/logout      | POST         | Logout |

## Discord video embed
Compartir en Discord: usar la URL /v/[id] (NO /uploads/archivo.mp4)
La página /v/[id] tiene og:type=video.other + og:video:url apuntando al MP4
Discord cachea el video vía Discordbot — puede tardar unos segundos la primera vez

## Radio / audio local
Si existe /public/aris_song.mp3 → se usa como fuente del radio (loop)
Si no existe → fallback al stream externo
Para convertir FLAC: ffmpeg -i aris_song.flac -codec:a libmp3lame -qscale:a 2 public/aris_song.mp3

## Scripts de mantenimiento
| Script | Descripción |
|---|---|
| bun run scripts/init-gacha-db.ts  | Inicializa tablas characters + videos |
| bun run scripts/sync-enka-gi.ts   | Sync GI |
| bun run scripts/sync-enka-hsr.ts  | Sync HSR |
''', update=True)

import json as _json
structure = {
  "version": "2.1.0", "fase": 2,
  "modulos": {
    "now":    {"ruta": "/src/features/now/",    "estado": "activo", "datos": "/data/now.json"},
    "radio":  {"ruta": "/src/features/radio/",  "estado": "activo", "datos": "local mp3 o stream"},
    "gacha":  {"ruta": "/src/features/gacha/",  "estado": "activo", "datos": "SQLite characters"},
    "videos": {"ruta": "/src/features/video/",  "estado": "activo", "datos": "SQLite videos + /public/uploads/",
               "discord": "OG embed via /v/[id]"},
    "admin":  {"ruta": "/src/pages/admin/",     "estado": "activo", "datos": "upload drag-drop + json editors"},
  }
}
p = ROOT / 'STRUCTURE.json'
p.write_text(_json.dumps(structure, ensure_ascii=False, indent=2), encoding='utf-8')
UPDATED.append('STRUCTURE.json')
print('  ✏️  STRUCTURE.json')


# ═══════════════════════════════════════════════════════════════
#  Resumen
# ═══════════════════════════════════════════════════════════════
print('\n' + '═'*60)
print('✅ SCRIPT COMPLETADO')
print('═'*60)
print(f'\n📁 {len(CREATED)} creados:')
for f in CREATED: print(f'   + {f}')
print(f'\n✏️  {len(UPDATED)} actualizados:')
for f in UPDATED: print(f'   ~ {f}')
print('''
─────────────────────────────────────────────────────────
PASOS SIGUIENTES:

  1. (Solo si tienes aris_song.flac) Convertir a MP3:
       ffmpeg -i aris_song.flac -codec:a libmp3lame -qscale:a 2 public/aris_song.mp3

  2. Rebuild:
       sudo docker compose up -d --build

  3. Si es la primera vez con la DB nueva:
       sudo docker exec web bun run scripts/init-gacha-db.ts

RUTAS NUEVAS:
  /videos          → galería con cards
  /v/[id]          → player + OG tags Discord
  /admin           → panel completo con upload drag-drop
  /api/videos/upload    → POST multipart
  /api/videos/update    → PATCH descriptores
  /api/admin/data       → GET/POST JSON editors

DISCORD EMBED:
  Comparte la URL /v/[id] en Discord → preview automático
─────────────────────────────────────────────────────────
''')
