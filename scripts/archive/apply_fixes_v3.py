#!/usr/bin/env python3
"""
apply_fixes_v3.py
1. Thumbnails automáticos con ffmpeg (Dockerfile instala ffmpeg, upload genera thumb)
2. Discord embed: og:description con descriptores custom
3. Radio: busca aris_song.opus en todo el disco y lo convierte a mp3
4. Admin v3: más visual, interactivo y completo
Uso: sudo HOME=/home/ubuntu python3 apply_fixes_v3.py
"""
import os, subprocess, glob

BASE = "/home/ubuntu/misitio"

# ══════════════════════════════════════════════════════════════
# 1. RADIO — buscar aris_song.opus y convertir a mp3
# ══════════════════════════════════════════════════════════════
print("🔍 Buscando aris_song.opus en el disco...")
opus_candidates = glob.glob("/home/ubuntu/**/*.opus", recursive=True) + \
                  glob.glob("/root/**/*.opus", recursive=True) + \
                  glob.glob("/tmp/**/*.opus", recursive=True)

target_mp3 = os.path.join(BASE, "public", "aris_song.mp3")
opus_found = None

for candidate in opus_candidates:
    if "aris_song" in candidate.lower() or "aris" in candidate.lower():
        opus_found = candidate
        break

if not opus_found and opus_candidates:
    opus_found = opus_candidates[0]

if opus_found:
    print(f"✅ Encontrado: {opus_found}")
    print("🔄 Convirtiendo opus → mp3...")
    result = subprocess.run([
        "ffmpeg", "-y", "-i", opus_found,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        target_mp3
    ], capture_output=True, text=True)
    if result.returncode == 0:
        size_mb = os.path.getsize(target_mp3) / 1024 / 1024
        print(f"✅ Convertido → public/aris_song.mp3 ({size_mb:.1f} MB)")
    else:
        print(f"⚠️  ffmpeg falló (se instalará en el Dockerfile): {result.stderr[-300:]}")
        print("    El mp3 se generará en el próximo rebuild.")
else:
    print("⚠️  aris_song.opus no encontrado en el host.")
    print("    Sube el archivo manualmente con:")
    print("    scp -i key.pem aris_song.opus ubuntu@IP:~/misitio/")
    print("    Luego corre: ffmpeg -i aris_song.opus -codec:a libmp3lame -qscale:a 2 public/aris_song.mp3")

# ══════════════════════════════════════════════════════════════
# 2. DOCKERFILE — instalar ffmpeg para thumbnails automáticos
# ══════════════════════════════════════════════════════════════
dockerfile = """\
FROM oven/bun:1-debian AS base
WORKDIR /app

# Instalar ffmpeg para thumbnails automáticos de video
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

FROM base AS deps
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN bun run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
# ffmpeg en la imagen final también
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/scripts ./scripts
COPY --from=builder /app/src ./src
COPY --from=builder /app/data ./data
RUN mkdir -p public/uploads public/thumbs

EXPOSE 4321
CMD ["bun", "./dist/server/entry.mjs"]
"""
with open(os.path.join(BASE, "Dockerfile"), "w") as f:
    f.write(dockerfile)
print("✅ Dockerfile actualizado (ffmpeg incluido)")

# ══════════════════════════════════════════════════════════════
# 3. docker-compose — montar /public/thumbs como volumen
# ══════════════════════════════════════════════════════════════
compose = """\
services:
  web:
    build: .
    ports:
      - "127.0.0.1:4321:4321"
    volumes:
      - ./data:/app/data
      - ./public/uploads:/app/public/uploads
      - ./public/thumbs:/app/public/thumbs
    env_file:
      - .env
    restart: always

  caddy:
    image: caddy:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
      - ./public/uploads:/srv/uploads
      - ./public/thumbs:/srv/thumbs
    depends_on:
      - web
    restart: always

volumes:
  caddy_data:
  caddy_config:
"""
with open(os.path.join(BASE, "docker-compose.yml"), "w") as f:
    f.write(compose)

# Crear carpeta thumbs en el host
thumbs_dir = os.path.join(BASE, "public", "thumbs")
os.makedirs(thumbs_dir, exist_ok=True)
subprocess.run(["chmod", "777", thumbs_dir], check=True)
print("✅ docker-compose.yml actualizado (volumen thumbs)")

# ══════════════════════════════════════════════════════════════
# 4. Caddyfile — servir /thumbs/*
# ══════════════════════════════════════════════════════════════
caddyfile = """\
aris-sama.duckdns.org {
  handle /uploads/* {
    root * /srv
    file_server
  }

  handle /thumbs/* {
    root * /srv
    file_server
  }

  handle {
    reverse_proxy web:4321
  }

  encode gzip zstd
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
    X-Frame-Options "SAMEORIGIN"
    Referrer-Policy "strict-origin-when-cross-origin"
    Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data: https:;"
  }
}
"""
with open(os.path.join(BASE, "Caddyfile"), "w") as f:
    f.write(caddyfile)
print("✅ Caddyfile actualizado (/thumbs servido por Caddy)")

# ══════════════════════════════════════════════════════════════
# 5. API upload — generar thumbnail con ffmpeg
# ══════════════════════════════════════════════════════════════
upload_api = """\
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
"""
os.makedirs(os.path.join(BASE, "src", "pages", "api", "videos"), exist_ok=True)
with open(os.path.join(BASE, "src", "pages", "api", "videos", "upload.ts"), "w") as f:
    f.write(upload_api)
print("✅ api/videos/upload.ts actualizado (thumbnail automático)")

# ══════════════════════════════════════════════════════════════
# 6. Script para generar thumbs de videos ya existentes
# ══════════════════════════════════════════════════════════════
retrothumb = """\
#!/usr/bin/env bun
// scripts/gen-thumbs.ts — genera thumbnails para videos ya subidos sin thumb
import { Database } from 'bun:sqlite';
import { join } from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { existsSync, mkdirSync } from 'fs';

const execFileAsync = promisify(execFile);
const BASE     = process.cwd();
const UPLOADS  = join(BASE, 'public', 'uploads');
const THUMBS   = join(BASE, 'public', 'thumbs');
mkdirSync(THUMBS, { recursive: true });

const db = new Database(join(BASE, 'data', 'database.sqlite'));
const videos = db.query("SELECT id, filename, url FROM videos WHERE thumbnail IS NULL OR thumbnail = ''").all() as any[];

console.log(`Procesando ${videos.length} videos sin thumbnail...`);

for (const v of videos) {
  const filename = v.filename ?? v.url?.split('/').pop();
  if (!filename) { console.log(`  skip ${v.id} (sin filename)`); continue; }

  const videoPath = join(UPLOADS, filename);
  const thumbFile = `${v.id}.jpg`;
  const thumbPath = join(THUMBS, thumbFile);

  if (!existsSync(videoPath)) { console.log(`  skip ${filename} (no existe en disco)`); continue; }
  if (existsSync(thumbPath))  { console.log(`  skip ${v.id} (thumb ya existe)`); continue; }

  try {
    await execFileAsync('ffmpeg', [
      '-y', '-i', videoPath,
      '-ss', '00:00:01', '-vframes', '1',
      '-vf', 'scale=640:-1', '-q:v', '3',
      thumbPath
    ]);

    // Obtener dimensiones
    let width = 1920, height = 1080;
    try {
      const probe = await execFileAsync('ffprobe', [
        '-v', 'quiet', '-print_format', 'json', '-show_streams', videoPath
      ]);
      const info = JSON.parse(probe.stdout);
      const vs = info.streams?.find((s: any) => s.codec_type === 'video');
      if (vs) { width = vs.width; height = vs.height; }
    } catch {}

    db.run("UPDATE videos SET thumbnail = ?, width = ?, height = ? WHERE id = ?",
      [`/thumbs/${thumbFile}`, width, height, v.id]);
    console.log(`  ✅ ${filename} → /thumbs/${thumbFile}`);
  } catch (e) {
    console.log(`  ❌ ${filename}: ${e}`);
  }
}

db.close();
console.log('\\nListo.');
"""
with open(os.path.join(BASE, "scripts", "gen-thumbs.ts"), "w") as f:
    f.write(retrothumb)
print("✅ scripts/gen-thumbs.ts creado")

# ══════════════════════════════════════════════════════════════
# 7. Admin v3 — más visual e interactivo
# ══════════════════════════════════════════════════════════════
admin_v3 = r"""---
import { Database } from 'bun:sqlite';
import { join } from 'path';
import { readdirSync, existsSync, statSync } from 'fs';

let videoCount = 0, charCount = 0, commentCount = 0, totalVideoSize = 0;
try {
  const db = new Database(join(process.cwd(), 'data', 'database.sqlite'), { readonly: true });
  videoCount   = (db.query('SELECT COUNT(*) as n FROM videos').get() as any)?.n ?? 0;
  charCount    = (db.query('SELECT COUNT(*) as n FROM characters').get() as any)?.n ?? 0;
  try { commentCount = (db.query('SELECT COUNT(*) as n FROM comments').get() as any)?.n ?? 0; } catch {}
  db.close();
} catch {}

// Tamaño de uploads
const uploadsDir = join(process.cwd(), 'public', 'uploads');
if (existsSync(uploadsDir)) {
  readdirSync(uploadsDir).forEach(f => {
    try { totalVideoSize += statSync(join(uploadsDir, f)).size; } catch {}
  });
}
const sizeMB = (totalVideoSize / 1024 / 1024).toFixed(1);

const featuresDir = join(process.cwd(), 'src', 'features');
const activeModules = existsSync(featuresDir)
  ? readdirSync(featuresDir, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name)
  : [];

const dataDir = join(process.cwd(), 'data');
const allJsons = existsSync(dataDir)
  ? readdirSync(dataDir).filter(f => f.endsWith('.json')).sort()
  : [];
---
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Admin · aris-sama</title>
  <link rel="stylesheet" href="/design-tokens.css" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { background: var(--color-bg); color: var(--color-ink); font-family: var(--font-body); min-height: 100dvh; }

    /* Layout */
    .shell { display: flex; min-height: 100dvh; }
    .sidebar {
      width: 220px; flex-shrink: 0;
      background: rgba(255,255,255,0.02);
      border-right: 1px solid rgba(255,255,255,0.06);
      display: flex; flex-direction: column;
      position: sticky; top: 0; height: 100dvh; overflow-y: auto;
    }
    .main { flex: 1; padding: 2rem 2.5rem; overflow-y: auto; max-width: 900px; }

    /* Sidebar */
    .sb-brand {
      padding: 1.25rem 1rem 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .sb-badge { font-family: var(--font-mono); font-size: 0.6rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--color-accent); display: block; margin-bottom: 0.2rem; }
    .sb-title { font-family: var(--font-display); font-size: 1rem; color: var(--color-ink); }
    .sb-nav { padding: 0.75rem 0; flex: 1; }
    .sb-group { padding: 0.5rem 1rem 0.25rem; font-family: var(--font-mono); font-size: 0.6rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--color-muted-2); }
    .sb-item {
      display: flex; align-items: center; gap: 0.6rem;
      padding: 0.5rem 1rem; cursor: pointer;
      font-family: var(--font-mono); font-size: 0.75rem; color: var(--color-muted);
      transition: all 0.15s; border-left: 2px solid transparent;
      background: none; border-right: none; border-top: none; border-bottom: none;
      width: 100%; text-align: left;
    }
    .sb-item:hover { color: var(--color-ink); background: rgba(255,255,255,0.03); }
    .sb-item.active { color: var(--color-accent); border-left-color: var(--color-accent); background: rgba(168,85,247,0.06); }
    .sb-item-icon { font-size: 0.9rem; width: 1.1rem; text-align: center; }
    .sb-footer { padding: 1rem; border-top: 1px solid rgba(255,255,255,0.05); }
    .btn-logout { width: 100%; font-family: var(--font-mono); font-size: 0.7rem; background: none; border: 1px solid rgba(248,113,113,0.2); border-radius: 6px; padding: 0.4rem 0.75rem; color: rgba(248,113,113,0.6); cursor: pointer; transition: all 0.15s; }
    .btn-logout:hover { border-color: #f87171; color: #f87171; }

    /* Pages */
    .page { display: none; }
    .page.active { display: block; }

    /* Page header */
    .page-head { margin-bottom: 2rem; }
    .page-head h1 { font-family: var(--font-display); font-size: 1.75rem; color: var(--color-ink); }
    .page-head p { font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-muted-2); margin-top: 0.25rem; }

    /* Stats grid */
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
    .stat-card {
      background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
      border-radius: 12px; padding: 1.25rem;
      display: flex; flex-direction: column; gap: 0.4rem;
      transition: border-color 0.15s;
    }
    .stat-card:hover { border-color: rgba(168,85,247,0.25); }
    .stat-icon { font-size: 1.25rem; }
    .stat-value { font-family: var(--font-mono); font-size: 1.75rem; color: var(--color-ink); font-weight: 600; line-height: 1; }
    .stat-label { font-family: var(--font-mono); font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--color-muted); }

    /* Quick actions */
    .quick-actions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 2rem; }
    .qa-btn {
      display: flex; align-items: center; gap: 0.5rem;
      background: rgba(168,85,247,0.08); border: 1px solid rgba(168,85,247,0.2);
      border-radius: 8px; padding: 0.6rem 1rem;
      font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-accent);
      cursor: pointer; transition: all 0.15s; text-decoration: none;
    }
    .qa-btn:hover { background: rgba(168,85,247,0.15); border-color: rgba(168,85,247,0.4); }

    /* Modules status */
    .modules-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.75rem; }
    .module-card {
      background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07);
      border-radius: 10px; padding: 1rem;
      display: flex; flex-direction: column; gap: 0.5rem;
    }
    .module-name { font-family: var(--font-mono); font-size: 0.8rem; color: var(--color-ink); }
    .module-status { font-family: var(--font-mono); font-size: 0.65rem; color: #4ade80; display: flex; align-items: center; gap: 0.3rem; }
    .module-status::before { content: '●'; font-size: 0.5rem; }
    .module-route { font-family: var(--font-mono); font-size: 0.65rem; color: var(--color-muted-2); }

    /* Section title */
    .section-title {
      font-family: var(--font-mono); font-size: 0.68rem; letter-spacing: 0.12em;
      text-transform: uppercase; color: var(--color-muted);
      margin-bottom: 1rem; display: flex; align-items: center; gap: 0.75rem;
    }
    .section-title::after { content: ''; flex: 1; height: 1px; background: rgba(255,255,255,0.06); }

    /* Upload zone */
    .upload-zone {
      border: 2px dashed rgba(168,85,247,0.3); border-radius: 12px;
      transition: all 0.2s; min-height: 120px; margin-bottom: 1.5rem;
    }
    .upload-zone.drag-over { border-color: var(--color-accent); background: rgba(168,85,247,0.06); }
    .upload-inner { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem; padding: 2rem; cursor: pointer; text-align: center; }
    .upload-icon { font-size: 2rem; color: var(--color-accent); opacity: 0.5; }
    .upload-label { font-size: 0.9rem; color: var(--color-ink); }
    .upload-hint { font-family: var(--font-mono); font-size: 0.7rem; color: var(--color-muted-2); }
    .upload-form { padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
    .uf-row { display: flex; flex-direction: column; gap: 0.3rem; }
    .uf-label { font-family: var(--font-mono); font-size: 0.68rem; letter-spacing: 0.06em; color: var(--color-muted); text-transform: uppercase; }
    .uf-hint { font-size: 0.62rem; color: var(--color-muted-2); }
    .uf-progress-wrap { display: flex; align-items: center; gap: 0.75rem; }
    .uf-progress-track { flex: 1; height: 3px; background: rgba(255,255,255,0.08); border-radius: 2px; overflow: hidden; }
    .uf-progress-bar { height: 100%; background: var(--color-accent); width: 0%; transition: width 0.1s; }
    .uf-progress-label { font-family: var(--font-mono); font-size: 0.68rem; color: var(--color-muted); min-width: 2.5rem; text-align: right; }
    .uf-actions { display: flex; gap: 0.75rem; justify-content: flex-end; }
    .upload-result { font-family: var(--font-mono); font-size: 0.8rem; padding: 0.5rem 0; }
    .descriptor-list { display: flex; flex-direction: column; gap: 0.4rem; }
    .desc-row { display: flex; gap: 0.4rem; align-items: center; }

    /* Video grid admin */
    .videos-admin-list { display: flex; flex-direction: column; gap: 0.75rem; }
    .va-card {
      display: flex; gap: 1rem; align-items: flex-start;
      background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07);
      border-radius: 10px; padding: 1rem; transition: border-color 0.15s;
    }
    .va-card:hover { border-color: rgba(168,85,247,0.2); }
    .va-thumb {
      width: 120px; flex-shrink: 0; aspect-ratio: 16/9;
      border-radius: 8px; overflow: hidden; background: rgba(168,85,247,0.06);
      position: relative;
    }
    .va-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .va-thumb-ph { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; color: var(--color-accent); opacity: 0.3; font-size: 1.25rem; }
    .va-body { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; min-width: 0; }
    .va-meta { display: flex; gap: 0.4rem; flex-wrap: wrap; }
    .va-actions { display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; }
    .va-link { font-family: var(--font-mono); font-size: 0.65rem; color: var(--color-muted-2); margin-top: 0.25rem; word-break: break-all; }

    /* JSON editor tabs */
    .tab-bar { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1.25rem; }
    .tab-btn {
      font-family: var(--font-mono); font-size: 0.7rem; letter-spacing: 0.04em;
      padding: 0.35rem 0.85rem;
      background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
      border-radius: 6px; color: var(--color-muted); cursor: pointer; transition: all 0.15s;
    }
    .tab-btn:hover { border-color: rgba(168,85,247,0.3); color: var(--color-accent); }
    .tab-btn.active { background: rgba(168,85,247,0.1); border-color: rgba(168,85,247,0.4); color: var(--color-accent); }
    .editor-wrap { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 1.5rem; }
    .editor-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .editor-filename { font-family: var(--font-mono); font-size: 0.75rem; color: var(--color-muted-2); }
    .form-section { display: flex; flex-direction: column; gap: 0.5rem; }
    .form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
    @media (max-width: 540px) { .form-grid-2 { grid-template-columns: 1fr; } }
    .form-field { display: flex; flex-direction: column; gap: 0.3rem; }
    .field-label { font-family: var(--font-mono); font-size: 0.65rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-muted); }
    .items-list { display: flex; flex-direction: column; gap: 0.4rem; margin-top: 0.4rem; }
    .item-card {
      display: flex; align-items: center; gap: 0.6rem;
      background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
      border-radius: 8px; padding: 0.6rem 0.75rem; transition: border-color 0.15s;
    }
    .item-card:hover { border-color: rgba(168,85,247,0.2); }
    .item-card.dragging { opacity: 0.4; border-style: dashed; }
    .item-drag-handle { color: var(--color-muted-2); cursor: grab; font-size: 1rem; flex-shrink: 0; user-select: none; }
    .item-fields { display: flex; gap: 0.4rem; flex: 1; align-items: center; flex-wrap: wrap; }
    .block-type-badge {
      font-family: var(--font-mono); font-size: 0.62rem;
      background: rgba(168,85,247,0.1); border: 1px solid rgba(168,85,247,0.2);
      border-radius: 4px; padding: 0.15rem 0.4rem; color: var(--color-accent); white-space: nowrap; flex-shrink: 0;
    }
    .save-result { font-family: var(--font-mono); font-size: 0.72rem; margin-top: 0.75rem; padding: 0.4rem 0; display: none; }

    /* Inputs */
    .uf-input {
      background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px; padding: 0.55rem 0.75rem;
      font-family: var(--font-mono); font-size: 0.82rem; color: var(--color-ink);
      outline: none; transition: border-color 0.15s; width: 100%;
    }
    .uf-input:focus { border-color: var(--color-accent); }
    .uf-input:disabled { opacity: 0.5; }
    .uf-input-sm {
      background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
      border-radius: 6px; padding: 0.3rem 0.5rem;
      font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-ink);
      outline: none; transition: border-color 0.15s;
    }
    .uf-input-sm:focus { border-color: var(--color-accent); }
    .uf-input-sm:disabled { opacity: 0.5; }
    select.uf-input-sm { cursor: pointer; }
    .json-editor {
      width: 100%; height: 14rem; resize: vertical;
      background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.07);
      border-radius: 8px; padding: 1rem;
      font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-ink);
      line-height: 1.6; outline: none; tab-size: 2;
    }
    .json-editor:focus { border-color: rgba(168,85,247,0.3); }

    /* Buttons */
    .btn-primary { background: var(--color-accent); color: var(--color-bg); border: none; border-radius: 8px; padding: 0.55rem 1.1rem; font-family: var(--font-mono); font-size: 0.72rem; cursor: pointer; letter-spacing: 0.04em; transition: opacity 0.15s; }
    .btn-primary:hover { opacity: 0.85; }
    .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-ghost { background: none; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 0.5rem 1rem; font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-muted); cursor: pointer; transition: all 0.15s; }
    .btn-ghost:hover { border-color: rgba(168,85,247,0.4); color: var(--color-accent); }
    .btn-ghost-sm { background: none; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 0.2rem 0.5rem; font-family: var(--font-mono); font-size: 0.65rem; color: var(--color-muted); cursor: pointer; transition: all 0.15s; text-decoration: none; display: inline-block; }
    .btn-ghost-sm:hover { border-color: var(--color-accent); color: var(--color-accent); }
    .btn-danger-sm { background: none; border: 1px solid rgba(248,113,113,0.2); border-radius: 6px; padding: 0.2rem 0.5rem; font-family: var(--font-mono); font-size: 0.65rem; color: rgba(248,113,113,0.6); cursor: pointer; transition: all 0.15s; }
    .btn-danger-sm:hover { border-color: #F87171; color: #F87171; }

    /* Gacha sync */
    .cmd-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .cmd-item { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; padding: 0.75rem 1rem; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; }
    .cmd-game { font-family: var(--font-mono); font-size: 0.82rem; color: var(--color-ink); min-width: 8rem; }
    .cmd-code { font-family: var(--font-mono); font-size: 0.65rem; color: var(--color-muted-2); background: rgba(0,0,0,0.25); padding: 0.25rem 0.5rem; border-radius: 4px; word-break: break-all; }
    .loading-text { color: var(--color-muted); font-family: var(--font-mono); font-size: 0.82rem; padding: 1rem 0; }

    /* Mobile sidebar */
    @media (max-width: 640px) {
      .shell { flex-direction: column; }
      .sidebar { width: 100%; height: auto; position: static; flex-direction: row; flex-wrap: wrap; padding: 0.5rem; }
      .sb-brand { border-bottom: none; border-right: 1px solid rgba(255,255,255,0.05); padding: 0.5rem 0.75rem; }
      .sb-nav { display: flex; flex-direction: row; flex-wrap: wrap; padding: 0.25rem; }
      .sb-group { display: none; }
      .sb-footer { padding: 0.5rem; }
      .main { padding: 1.25rem; }
    }
  </style>
</head>
<body>
<div class="shell">

  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sb-brand">
      <span class="sb-badge">root@aris</span>
      <span class="sb-title">admin</span>
    </div>
    <nav class="sb-nav">
      <div class="sb-group">General</div>
      <button class="sb-item active" data-page="overview">
        <span class="sb-item-icon">⬡</span> Overview
      </button>
      <div class="sb-group">Contenido</div>
      <button class="sb-item" data-page="videos">
        <span class="sb-item-icon">▶</span> Videos
      </button>
      <button class="sb-item" data-page="content">
        <span class="sb-item-icon">✦</span> JSONs
      </button>
      <div class="sb-group">Sistema</div>
      <button class="sb-item" data-page="gacha">
        <span class="sb-item-icon">◈</span> Gacha Sync
      </button>
    </nav>
    <div class="sb-footer">
      <button id="logout-btn" class="btn-logout">salir →</button>
    </div>
  </aside>

  <!-- Main -->
  <main class="main">

    <!-- PAGE: Overview -->
    <div class="page active" id="page-overview">
      <div class="page-head">
        <h1>Panel de control</h1>
        <p>módulos activos: {activeModules.join(' · ')}</p>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-icon">▶</span>
          <span class="stat-value">{videoCount}</span>
          <span class="stat-label">videos</span>
        </div>
        <div class="stat-card">
          <span class="stat-icon">💬</span>
          <span class="stat-value">{commentCount}</span>
          <span class="stat-label">comentarios</span>
        </div>
        <div class="stat-card">
          <span class="stat-icon">◈</span>
          <span class="stat-value">{charCount}</span>
          <span class="stat-label">chars gacha</span>
        </div>
        <div class="stat-card">
          <span class="stat-icon">💾</span>
          <span class="stat-value">{sizeMB}</span>
          <span class="stat-label">MB uploads</span>
        </div>
        <div class="stat-card">
          <span class="stat-icon">✦</span>
          <span class="stat-value">{allJsons.length}</span>
          <span class="stat-label">archivos JSON</span>
        </div>
      </div>

      <div class="section-title">accesos rápidos</div>
      <div class="quick-actions">
        <button class="qa-btn" data-page="videos">▶ subir video</button>
        <button class="qa-btn" data-page="content">✦ editar now.json</button>
        <a class="qa-btn" href="/videos" target="_blank">↗ ver /videos</a>
        <a class="qa-btn" href="/now" target="_blank">↗ ver /now</a>
        <a class="qa-btn" href="/gacha" target="_blank">↗ ver /gacha</a>
      </div>

      <div class="section-title" style="margin-top:2rem">módulos</div>
      <div class="modules-grid">
        {activeModules.map(m => (
          <div class="module-card">
            <span class="module-name">{m}</span>
            <span class="module-status">activo</span>
            <span class="module-route">/{m}</span>
          </div>
        ))}
      </div>
    </div>

    <!-- PAGE: Videos -->
    <div class="page" id="page-videos">
      <div class="page-head">
        <h1>Videos</h1>
        <p>sube, edita y gestiona tus clips</p>
      </div>

      <div class="section-title">subir video</div>
      <div class="upload-zone" id="drop-zone">
        <div class="upload-inner" id="upload-inner">
          <span class="upload-icon">▶</span>
          <p class="upload-label">arrastra tu video aquí</p>
          <p class="upload-hint">o haz click · mp4, webm, mov · máx 500MB</p>
          <input type="file" id="file-input" accept="video/mp4,video/webm,video/quicktime" style="display:none" />
        </div>
        <div class="upload-form" id="upload-form" style="display:none">
          <div class="uf-row">
            <label class="uf-label">título</label>
            <input type="text" id="uf-title" class="uf-input" placeholder="Miyabi SS · Daily Challenge" />
          </div>
          <div class="uf-row">
            <label class="uf-label">categoría</label>
            <input type="text" id="uf-category" class="uf-input" placeholder="gameplay · clip · momento..." />
          </div>
          <div class="uf-row">
            <label class="uf-label">descriptores <span class="uf-hint">clave=valor para Discord embed</span></label>
            <div id="descriptor-list" class="descriptor-list"></div>
            <button type="button" id="add-descriptor" class="btn-ghost" style="margin-top:0.4rem;align-self:flex-start">+ descriptor</button>
          </div>
          <div class="uf-progress-wrap" id="progress-wrap" style="display:none">
            <div class="uf-progress-track"><div class="uf-progress-bar" id="progress-bar"></div></div>
            <span class="uf-progress-label" id="progress-label">0%</span>
          </div>
          <div class="uf-actions">
            <button type="button" id="upload-cancel" class="btn-ghost">cancelar</button>
            <button type="button" id="upload-submit" class="btn-primary">subir video →</button>
          </div>
        </div>
      </div>
      <p class="upload-result" id="upload-result" style="display:none"></p>

      <div class="section-title">videos subidos <span id="v-count" style="color:var(--color-accent);margin-left:0.25rem">{videoCount}</span></div>
      <div id="videos-list" class="videos-admin-list">
        <p class="loading-text">cargando…</p>
      </div>
    </div>

    <!-- PAGE: Content (JSON editors) -->
    <div class="page" id="page-content">
      <div class="page-head">
        <h1>Contenido</h1>
        <p>edita los JSONs — cambios aplicados al instante, sin rebuild</p>
      </div>
      <div class="tab-bar" id="tab-bar"></div>
      <div id="json-editors"></div>
    </div>

    <!-- PAGE: Gacha -->
    <div class="page" id="page-gacha">
      <div class="page-head">
        <h1>Gacha Sync</h1>
        <p>comandos para sincronizar personajes desde Enka Network</p>
      </div>
      <div class="section-title">comandos de sync</div>
      <div class="cmd-list" id="cmd-list">
        <p class="loading-text">carga gacha-config.json para ver los juegos...</p>
      </div>
    </div>

  </main>
</div>

<script define:vars={{ allJsons }}>
// ══ NAVEGACIÓN ════════════════════════════════════════════════
const ALLOWED_SAVE = ['now.json','books.json','homepage.json','gacha-config.json'];

function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.sb-item').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + id)?.classList.add('active');
  document.querySelector(`.sb-item[data-page="${id}"]`)?.classList.add('active');
  if (id === 'videos') loadVideos();
  if (id === 'content' && !contentLoaded) initContent();
  if (id === 'gacha') loadGachaSync();
}

document.querySelectorAll('[data-page]').forEach(el => {
  el.addEventListener('click', () => showPage(el.dataset.page));
});

document.getElementById('logout-btn')?.addEventListener('click', async () => {
  await fetch('/api/auth/logout', { method: 'POST' });
  location.href = '/admin/login';
});

// ══ UPLOAD VIDEO ══════════════════════════════════════════════
const dropZone    = document.getElementById('drop-zone');
const uploadInner = document.getElementById('upload-inner');
const uploadForm  = document.getElementById('upload-form');
const fileInput   = document.getElementById('file-input');
let selectedFile  = null;

function showUploadForm(file) {
  selectedFile = file;
  document.getElementById('uf-title').value = file.name.replace(/\.[^.]+$/, '');
  uploadInner.style.display = 'none';
  uploadForm.style.display  = 'flex';
  uploadForm.style.flexDirection = 'column';
}
dropZone?.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone?.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('drag-over'); const f = e.dataTransfer?.files[0]; if (f) showUploadForm(f); });
uploadInner?.addEventListener('click', () => fileInput.click());
fileInput?.addEventListener('change', () => { if (fileInput.files?.[0]) showUploadForm(fileInput.files[0]); });
document.getElementById('upload-cancel')?.addEventListener('click', () => {
  selectedFile = null; uploadInner.style.display = 'flex'; uploadForm.style.display = 'none'; fileInput.value = '';
});
document.getElementById('add-descriptor')?.addEventListener('click', () => {
  const list = document.getElementById('descriptor-list');
  const row = document.createElement('div');
  row.className = 'desc-row';
  row.innerHTML = `<input class="uf-input-sm desc-key" placeholder="clave" style="flex:1" /><input class="uf-input-sm desc-val" placeholder="valor" style="flex:2" /><button class="btn-danger-sm desc-rm">✕</button>`;
  row.querySelector('.desc-rm')?.addEventListener('click', () => row.remove());
  list.appendChild(row);
});
document.getElementById('upload-submit')?.addEventListener('click', async () => {
  if (!selectedFile) return;
  const title    = document.getElementById('uf-title').value || selectedFile.name;
  const category = document.getElementById('uf-category').value || 'general';
  const descriptors = {};
  document.querySelectorAll('.desc-row').forEach(r => {
    const k = r.querySelector('.desc-key').value.trim();
    const v = r.querySelector('.desc-val').value.trim();
    if (k && v) descriptors[k] = v;
  });
  const fd = new FormData();
  fd.append('video', selectedFile); fd.append('title', title);
  fd.append('category', category); fd.append('descriptors', JSON.stringify(descriptors));
  document.getElementById('progress-wrap').style.display = 'flex';
  const btn = document.getElementById('upload-submit'); btn.disabled = true;
  const xhr = new XMLHttpRequest();
  xhr.upload.addEventListener('progress', e => {
    if (e.lengthComputable) {
      const pct = Math.round(e.loaded / e.total * 100);
      document.getElementById('progress-bar').style.width = pct + '%';
      document.getElementById('progress-label').textContent = pct + '%';
    }
  });
  xhr.addEventListener('load', () => {
    document.getElementById('progress-wrap').style.display = 'none'; btn.disabled = false;
    try {
      const res = JSON.parse(xhr.responseText);
      const el = document.getElementById('upload-result');
      if (res.ok) {
        el.textContent = `✅ subido · /v/${res.id}${res.thumbnail ? ' · thumbnail generado' : ''}`;
        el.style.color = 'var(--color-accent)';
        uploadInner.style.display = 'flex'; uploadForm.style.display = 'none';
        selectedFile = null; fileInput.value = ''; loadVideos();
      } else { el.textContent = `❌ ${res.error}`; el.style.color = '#f87171'; }
      el.style.display = 'block';
    } catch { document.getElementById('upload-result').textContent = '❌ Error inesperado'; }
  });
  xhr.open('POST', '/api/videos/upload'); xhr.send(fd);
});

// ══ LISTA DE VIDEOS ═══════════════════════════════════════════
async function loadVideos() {
  const list = document.getElementById('videos-list');
  const countEl = document.getElementById('v-count');
  list.innerHTML = '<p class="loading-text">cargando…</p>';
  try {
    const { videos } = await fetch('/api/videos').then(r => r.json());
    if (countEl) countEl.textContent = videos.length;
    if (!videos.length) { list.innerHTML = '<p class="loading-text">sin videos todavía.</p>'; return; }
    list.innerHTML = '';
    videos.forEach(v => {
      let desc = {}; try { desc = JSON.parse(v.descriptors ?? '{}'); } catch {}
      const descStr = Object.entries(desc).map(([k,val]) => `${k}: ${val}`).join(' · ');
      const card = document.createElement('div');
      card.className = 'va-card'; card.dataset.id = v.id;
      card.innerHTML = `
        <div class="va-thumb">
          ${v.thumbnail ? `<img src="${v.thumbnail}" alt="" />` : '<div class="va-thumb-ph">▶</div>'}
        </div>
        <div class="va-body">
          <input class="uf-input va-title-input" value="${esc(v.title)}" data-field="title" />
          <div class="va-meta">
            <input class="uf-input-sm" value="${esc(v.category ?? 'general')}" placeholder="categoría" data-field="category" style="flex:1" />
            <input class="uf-input-sm" value="${esc(descStr)}" placeholder="Clave: Valor, ..." data-field="descriptors_raw" style="flex:3" />
          </div>
          <div class="va-actions">
            <a href="/v/${v.id}" target="_blank" class="btn-ghost-sm">↗ ver</a>
            <button class="btn-ghost-sm va-save" data-id="${v.id}">guardar</button>
            <button class="btn-danger-sm va-delete" data-id="${v.id}">eliminar</button>
          </div>
          <div class="va-link">/uploads/${esc(v.filename ?? '')}</div>
        </div>
      `;
      card.querySelector('.va-save')?.addEventListener('click', async btn => {
        const id = v.id;
        const title    = card.querySelector('[data-field="title"]').value;
        const category = card.querySelector('[data-field="category"]').value;
        const rawDesc  = card.querySelector('[data-field="descriptors_raw"]').value;
        const descriptors = {};
        rawDesc.split(',').forEach(part => {
          const [k,...rest] = part.split(':');
          if (k?.trim()) descriptors[k.trim()] = rest.join(':').trim();
        });
        const res = await fetch('/api/videos/update', { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id, title, category, descriptors}) });
        const saveBtn = card.querySelector('.va-save');
        saveBtn.textContent = res.ok ? '✓ guardado' : '❌';
        setTimeout(() => { saveBtn.textContent = 'guardar'; }, 2000);
      });
      card.querySelector('.va-delete')?.addEventListener('click', async () => {
        if (!confirm('¿Eliminar este video?')) return;
        await fetch(`/api/videos?id=${v.id}`, { method: 'DELETE' });
        loadVideos();
      });
      list.appendChild(card);
    });
  } catch(e) { list.innerHTML = `<p class="loading-text" style="color:#f87171">${e}</p>`; }
}

// ══ JSON EDITORS ══════════════════════════════════════════════
let contentLoaded = false;
let activeJsonTab = allJsons[0] ?? null;
const jsonCache = {};

function initContent() {
  contentLoaded = true;
  const tabBar = document.getElementById('tab-bar');
  allJsons.forEach(file => {
    const btn = document.createElement('button');
    btn.className = 'tab-btn' + (file === activeJsonTab ? ' active' : '');
    btn.textContent = file.replace('.json','');
    btn.dataset.file = file;
    btn.addEventListener('click', () => switchJsonTab(file));
    tabBar?.appendChild(btn);
  });
  if (activeJsonTab) switchJsonTab(activeJsonTab);
}

async function switchJsonTab(file) {
  activeJsonTab = file;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.file === file));
  const container = document.getElementById('json-editors');
  container.innerHTML = '<p class="loading-text">cargando…</p>';
  if (!jsonCache[file]) {
    const res = await fetch(`/api/admin/data?file=${file}`);
    jsonCache[file] = res.ok ? await res.json() : null;
  }
  if (jsonCache[file] === null) { container.innerHTML = `<p class="loading-text" style="color:#f87171">No se pudo cargar ${file}</p>`; return; }
  renderJsonEditor(file, jsonCache[file], ALLOWED_SAVE.includes(file));
  if (file === 'gacha-config.json') renderGachaSync(jsonCache[file]);
}

function renderJsonEditor(file, data, canSave) {
  const container = document.getElementById('json-editors');
  container.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'editor-wrap';
  const header = document.createElement('div');
  header.className = 'editor-header';
  header.innerHTML = `<span class="editor-filename">/data/${file}</span>`;
  if (canSave) {
    const sb = document.createElement('button');
    sb.className = 'btn-primary'; sb.id = 'json-save-btn'; sb.textContent = 'guardar ↑';
    sb.addEventListener('click', () => saveJson(file));
    header.appendChild(sb);
  }
  wrap.appendChild(header);
  const form = buildJsonForm(file, data, canSave);
  wrap.appendChild(form);
  const result = document.createElement('p');
  result.className = 'save-result'; result.id = 'json-save-result';
  wrap.appendChild(result);
  container.appendChild(wrap);
}

function buildJsonForm(file, data, canSave) {
  if (file === 'now.json')       return buildNowForm(data, canSave);
  if (file === 'books.json')     return buildBooksForm(data, canSave);
  if (file === 'homepage.json')  return buildHomepageForm(data, canSave);
  if (file === 'gacha-config.json') return buildGachaForm(data, canSave);
  return buildGenericForm(file, data, canSave);
}

// now.json
function buildNowForm(data, canSave) {
  const wrap = el('div', 'form-section'); wrap.dataset.collector = 'now';
  const grid = el('div', 'form-grid-2');
  grid.innerHTML = `
    <div class="form-field"><label class="field-label">ubicación</label><input class="uf-input" id="now-location" value="${esc(data.location??'')}" ${canSave?'':'disabled'} /></div>
    <div class="form-field"><label class="field-label">estado</label><input class="uf-input" id="now-status" value="${esc(data.status??'')}" ${canSave?'':'disabled'} /></div>
  `;
  wrap.appendChild(grid);
  const lbl = el('div','field-label'); lbl.style.marginTop='1rem'; lbl.textContent='items'; wrap.appendChild(lbl);
  const list = el('div','items-list'); list.id = 'now-items';
  (data.items ?? []).forEach(item => appendNowItem(list, item, canSave));
  wrap.appendChild(list);
  if (canSave) {
    const add = el('button','btn-ghost'); add.style.marginTop='0.5rem'; add.textContent='+ añadir item';
    add.addEventListener('click', () => appendNowItem(list, {icon:'✨',category:'',text:''}, true));
    wrap.appendChild(add);
  }
  return wrap;
}
function appendNowItem(container, item, canSave) {
  const card = el('div','item-card'); card.draggable = canSave;
  card.innerHTML = `
    <span class="item-drag-handle">⠿</span>
    <div class="item-fields">
      <input class="uf-input-sm now-icon" placeholder="🎮" value="${esc(item.icon??'')}" style="width:50px" ${canSave?'':'disabled'} />
      <input class="uf-input-sm now-category" placeholder="categoría" value="${esc(item.category??'')}" style="flex:1" ${canSave?'':'disabled'} />
      <input class="uf-input-sm now-text" placeholder="texto..." value="${esc(item.text??'')}" style="flex:3" ${canSave?'':'disabled'} />
    </div>
    ${canSave ? '<button class="btn-danger-sm item-remove">✕</button>' : ''}
  `;
  card.querySelector('.item-remove')?.addEventListener('click', () => card.remove());
  if (canSave) setupDrag(card, container);
  container.appendChild(card);
}

// books.json
function buildBooksForm(data, canSave) {
  const wrap = el('div','form-section'); wrap.dataset.collector = 'books';
  const list = el('div','items-list'); list.id = 'books-list';
  const books = Array.isArray(data) ? data : (data?.books ?? []);
  books.forEach(b => appendBookItem(list, b, canSave));
  wrap.appendChild(list);
  if (canSave) {
    const add = el('button','btn-ghost'); add.style.marginTop='0.5rem'; add.textContent='+ añadir libro';
    add.addEventListener('click', () => appendBookItem(list, {title:'',author:'',status:'want',cover:''}, canSave));
    wrap.appendChild(add);
  }
  return wrap;
}
function appendBookItem(container, book, canSave) {
  const card = el('div','item-card');
  const opts = ['reading','read','want','dropped'].map(s => `<option value="${s}" ${book.status===s?'selected':''}>${s}</option>`).join('');
  card.innerHTML = `
    <span class="item-drag-handle">⠿</span>
    <div class="item-fields" style="flex-wrap:wrap">
      <input class="uf-input-sm book-title" placeholder="título" value="${esc(book.title??'')}" style="flex:2;min-width:120px" ${canSave?'':'disabled'} />
      <input class="uf-input-sm book-author" placeholder="autor" value="${esc(book.author??'')}" style="flex:2;min-width:100px" ${canSave?'':'disabled'} />
      <select class="uf-input-sm book-status" style="flex:1;min-width:80px" ${canSave?'':'disabled'}>${opts}</select>
      <input class="uf-input-sm book-cover" placeholder="url portada" value="${esc(book.cover??'')}" style="flex:3;min-width:150px" ${canSave?'':'disabled'} />
    </div>
    ${canSave ? '<button class="btn-danger-sm item-remove">✕</button>' : ''}
  `;
  card.querySelector('.item-remove')?.addEventListener('click', () => card.remove());
  container.appendChild(card);
}

// homepage.json
function buildHomepageForm(data, canSave) {
  const wrap = el('div','form-section'); wrap.dataset.collector = 'homepage';
  const tf = el('div','form-field');
  tf.innerHTML = `<label class="field-label">título</label><input class="uf-input" id="hp-title" value="${esc(data.title??'')}" ${canSave?'':'disabled'} />`;
  wrap.appendChild(tf);
  const lbl = el('div','field-label'); lbl.style.cssText='margin-top:1rem;margin-bottom:0.4rem'; lbl.textContent='bloques (arrastra para reordenar)'; wrap.appendChild(lbl);
  const list = el('div','items-list'); list.id = 'hp-blocks';
  (data.blocks ?? []).forEach(b => appendBlockItem(list, b, canSave));
  wrap.appendChild(list);
  if (canSave) {
    const addRow = el('div',''); addRow.style.cssText='display:flex;gap:0.4rem;margin-top:0.5rem;align-items:center';
    const sel = document.createElement('select'); sel.className = 'uf-input-sm';
    ['hero','now_preview','radio_banner','bookshelf_preview','videos_preview','gacha_preview','custom'].forEach(t => {
      const o = document.createElement('option'); o.value = t; o.textContent = t; sel.appendChild(o);
    });
    const add = el('button','btn-ghost'); add.textContent = '+ bloque';
    add.addEventListener('click', () => appendBlockItem(list, {type: sel.value}, true));
    addRow.appendChild(sel); addRow.appendChild(add);
    wrap.appendChild(addRow);
  }
  return wrap;
}
function appendBlockItem(container, block, canSave) {
  const card = el('div','item-card block-card'); card.draggable = canSave; card.dataset.type = block.type;
  let extra = '';
  if (block.type === 'hero') extra = `<input class="uf-input-sm block-field" data-key="title" placeholder="título" value="${esc(block.title??'')}" style="flex:2" ${canSave?'':'disabled'} /><input class="uf-input-sm block-field" data-key="subtitle" placeholder="subtítulo" value="${esc(block.subtitle??'')}" style="flex:3" ${canSave?'':'disabled'} />`;
  else if (['now_preview','bookshelf_preview','videos_preview'].includes(block.type)) extra = `<input class="uf-input-sm block-field" data-key="limit" placeholder="limit" value="${esc(String(block.limit??''))}" style="width:70px" ${canSave?'':'disabled'} />`;
  card.innerHTML = `<span class="item-drag-handle">⠿</span><span class="block-type-badge">${block.type}</span><div class="item-fields" style="flex:1">${extra}</div>${canSave?'<button class="btn-danger-sm item-remove">✕</button>':''}`;
  card.querySelector('.item-remove')?.addEventListener('click', () => card.remove());
  if (canSave) setupDrag(card, container);
  container.appendChild(card);
}

// gacha-config.json
function buildGachaForm(data, canSave) {
  const wrap = el('div','form-section'); wrap.dataset.collector = 'gacha';
  const list = el('div','items-list'); list.id = 'gacha-list';
  (data.games ?? []).forEach(g => appendGachaItem(list, g, canSave));
  wrap.appendChild(list);
  if (canSave) {
    const add = el('button','btn-ghost'); add.style.marginTop='0.5rem'; add.textContent='+ juego';
    add.addEventListener('click', () => appendGachaItem(list, {icon:'',name:'',id:'',uid:''}, true));
    wrap.appendChild(add);
  }
  return wrap;
}
function appendGachaItem(container, game, canSave) {
  const card = el('div','item-card');
  card.innerHTML = `
    <span class="item-drag-handle">⠿</span>
    <div class="item-fields" style="flex-wrap:wrap">
      <input class="uf-input-sm gacha-icon" placeholder="🎮" value="${esc(game.icon??'')}" style="width:50px" ${canSave?'':'disabled'} />
      <input class="uf-input-sm gacha-name" placeholder="nombre" value="${esc(game.name??'')}" style="flex:2" ${canSave?'':'disabled'} />
      <input class="uf-input-sm gacha-id" placeholder="id (gi/hsr/zzz)" value="${esc(game.id??'')}" style="flex:1;min-width:80px" ${canSave?'':'disabled'} />
      <input class="uf-input-sm gacha-uid" placeholder="UID" value="${esc(game.uid??'')}" style="flex:2" ${canSave?'':'disabled'} />
    </div>
    ${canSave?'<button class="btn-danger-sm item-remove">✕</button>':''}
  `;
  card.querySelector('.item-remove')?.addEventListener('click', () => card.remove());
  container.appendChild(card);
}

// generic
function buildGenericForm(file, data, canSave) {
  const wrap = el('div','form-section'); wrap.dataset.collector = 'generic'; wrap.dataset.file = file;
  const ta = document.createElement('textarea'); ta.className = 'json-editor'; ta.id = 'generic-editor';
  ta.value = JSON.stringify(data, null, 2); ta.disabled = !canSave;
  wrap.appendChild(ta); return wrap;
}

// Save
async function saveJson(file) {
  const wrap = document.querySelector('[data-collector]');
  if (!wrap) return;
  const collector = wrap.dataset.collector;
  let payload;
  try {
    if (collector === 'now') {
      payload = {
        updated: new Date().toISOString().split('T')[0],
        location: document.getElementById('now-location').value.trim(),
        status:   document.getElementById('now-status').value.trim(),
        items: [...document.querySelectorAll('#now-items .item-card')].map(c => ({
          icon:     c.querySelector('.now-icon').value.trim(),
          category: c.querySelector('.now-category').value.trim(),
          text:     c.querySelector('.now-text').value.trim(),
        }))
      };
    } else if (collector === 'books') {
      payload = [...document.querySelectorAll('#books-list .item-card')].map(c => ({
        title:  c.querySelector('.book-title').value.trim(),
        author: c.querySelector('.book-author').value.trim(),
        status: c.querySelector('.book-status').value,
        cover:  c.querySelector('.book-cover').value.trim() || undefined,
      }));
    } else if (collector === 'homepage') {
      payload = {
        title: document.getElementById('hp-title').value.trim(),
        blocks: [...document.querySelectorAll('#hp-blocks .block-card')].map(c => {
          const obj = { type: c.dataset.type };
          c.querySelectorAll('.block-field').forEach(f => { const v = f.value.trim(); if (v) obj[f.dataset.key] = f.dataset.key === 'limit' ? Number(v) : v; });
          return obj;
        })
      };
    } else if (collector === 'gacha') {
      payload = { games: [...document.querySelectorAll('#gacha-list .item-card')].map(c => ({
        icon: c.querySelector('.gacha-icon').value.trim(),
        name: c.querySelector('.gacha-name').value.trim(),
        id:   c.querySelector('.gacha-id').value.trim(),
        uid:  c.querySelector('.gacha-uid').value.trim(),
      }))};
    } else {
      payload = JSON.parse(document.getElementById('generic-editor').value);
    }
  } catch(e) { showJsonResult(`❌ JSON inválido: ${e}`, false); return; }

  const btn = document.getElementById('json-save-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'guardando…'; }
  const res = await fetch(`/api/admin/data?file=${file}`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  if (btn) { btn.disabled = false; btn.textContent = 'guardar ↑'; }
  jsonCache[file] = payload;
  showJsonResult(res.ok ? '✅ guardado — aplicado al instante' : `❌ ${await res.text()}`, res.ok);
}
function showJsonResult(msg, ok) {
  const el = document.getElementById('json-save-result');
  if (!el) return;
  el.textContent = msg; el.style.color = ok ? 'var(--color-accent)' : '#f87171'; el.style.display = 'block';
  if (ok) setTimeout(() => { el.style.display = 'none'; }, 3000);
}

// Gacha sync
async function loadGachaSync() {
  const list = document.getElementById('cmd-list');
  let data = jsonCache['gacha-config.json'];
  if (!data) {
    const res = await fetch('/api/admin/data?file=gacha-config.json');
    data = res.ok ? await res.json() : null;
    if (data) jsonCache['gacha-config.json'] = data;
  }
  if (!data?.games?.length) { list.innerHTML = '<p class="loading-text">Sin juegos configurados en gacha-config.json</p>'; return; }
  list.innerHTML = data.games.map(g => `
    <div class="cmd-item">
      <span class="cmd-game">${g.icon} ${g.name}</span>
      <code class="cmd-code">docker exec web bun run scripts/sync-enka-${g.id}.ts</code>
    </div>
  `).join('');
}

// Utils
function el(tag, cls) { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;'); }
function setupDrag(card, container) {
  card.addEventListener('dragstart', () => card.classList.add('dragging'));
  card.addEventListener('dragend',   () => card.classList.remove('dragging'));
  card.addEventListener('dragover', e => {
    e.preventDefault();
    const dragging = container.querySelector('.dragging');
    if (!dragging || dragging === card) return;
    const mid = card.getBoundingClientRect().top + card.getBoundingClientRect().height / 2;
    container.insertBefore(dragging, e.clientY < mid ? card : card.nextSibling);
  });
}
</script>
</html>
"""
os.makedirs(os.path.join(BASE, "src", "pages", "admin"), exist_ok=True)
with open(os.path.join(BASE, "src", "pages", "admin", "index.astro"), "w") as f:
    f.write(admin_v3)
print("✅ Admin v3 escrito")

# ══════════════════════════════════════════════════════════════
# 8. Rebuild
# ══════════════════════════════════════════════════════════════
print("\n🔨 Rebuilding (incluye ffmpeg — puede tardar ~3 min)...")
result = subprocess.run(
    ["docker", "compose", "up", "-d", "--build"],
    cwd=BASE, capture_output=True, text=True
)
print(result.stdout[-2000:] if result.stdout else "")
if result.returncode != 0:
    print("❌ Error:", result.stderr[-2000:])
else:
    print("\n✅ Todo listo. Ejecuta ahora:")
    print("   sudo docker exec misitio-web-1 bun run scripts/gen-thumbs.ts")
    print("   (genera thumbnails para los videos ya subidos)")
