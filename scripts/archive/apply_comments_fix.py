#!/usr/bin/env python3
"""
apply_comments_fix.py
1. Fix descriptores en embed de Discord (og:description mejorado)
2. Sistema de comentarios con alias, sin auth — guardado en SQLite
3. API endpoints: GET/POST /api/videos/comments?id=...
Uso: python3 apply_comments_fix.py (en ~/misitio)
"""
import os, subprocess, textwrap

BASE = os.path.expanduser("~/misitio")

# ─── 1. Inicializar tabla comments en SQLite ──────────────────────────────────
init_db = textwrap.dedent("""\
import { Database } from 'bun:sqlite';
import { join } from 'path';
const db = new Database(join(process.cwd(), 'data', 'database.sqlite'));
db.run(`CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL,
  alias TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)`);
db.close();
console.log('✅ tabla comments lista');
""")
with open(os.path.join(BASE, "scripts", "init-comments-db.ts"), "w") as f:
    f.write(init_db)
print("✅ scripts/init-comments-db.ts creado")

# ─── 2. API endpoint: GET + POST /api/videos/comments ────────────────────────
comments_api = textwrap.dedent("""\
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
""")
os.makedirs(os.path.join(BASE, "src", "pages", "api", "videos"), exist_ok=True)
with open(os.path.join(BASE, "src", "pages", "api", "videos", "comments.ts"), "w") as f:
    f.write(comments_api)
print("✅ src/pages/api/videos/comments.ts creado")

# ─── 3. Reescribir /v/[id].astro con fix de og:description + comentarios ─────
video_page = r"""---
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

// og:description con descriptores
const descParts: string[] = [];
if (video.category) descParts.push(video.category);
const descEntries = Object.entries(descriptors).map(([k, v]) => `${k}=${v}`);
if (descEntries.length > 0) descParts.push(descEntries.join(' · '));
const ogDescription = descParts.length > 0 ? descParts.join(' · ') : 'video · aris-sama';
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
  <meta property="og:description"       content={ogDescription} />
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
  <meta name="twitter:description" content={ogDescription} />
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

    /* ── Comentarios ── */
    .comments-section {
      margin-top: 2.5rem;
      border-top: 1px solid rgba(255,255,255,0.06);
      padding-top: 2rem;
    }
    .comments-title {
      font-family: var(--font-mono); font-size: 0.7rem;
      letter-spacing: 0.12em; text-transform: uppercase;
      color: var(--color-accent); margin-bottom: 1.25rem;
    }
    .comment-form {
      display: flex; flex-direction: column; gap: 0.6rem;
      margin-bottom: 2rem;
    }
    .comment-form input, .comment-form textarea {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 8px; padding: 0.6rem 0.85rem;
      color: var(--color-ink); font-family: var(--font-body); font-size: 0.88rem;
      outline: none; transition: border-color 0.15s; resize: vertical;
    }
    .comment-form input:focus, .comment-form textarea:focus {
      border-color: rgba(168,85,247,0.4);
    }
    .comment-form textarea { min-height: 80px; }
    .comment-submit {
      align-self: flex-end;
      background: var(--color-accent); color: var(--color-bg);
      border: none; border-radius: 8px; padding: 0.5rem 1.1rem;
      font-family: var(--font-mono); font-size: 0.72rem;
      cursor: pointer; letter-spacing: 0.04em; transition: opacity 0.15s;
    }
    .comment-submit:hover { opacity: 0.85; }
    .comment-submit:disabled { opacity: 0.4; cursor: not-allowed; }
    .comment-error {
      font-family: var(--font-mono); font-size: 0.72rem;
      color: #f87171; display: none;
    }
    .comments-list { display: flex; flex-direction: column; gap: 1rem; }
    .comment-empty {
      font-family: var(--font-mono); font-size: 0.78rem;
      color: var(--color-muted-2);
    }
    .comment-card {
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 10px; padding: 0.85rem 1rem;
    }
    .comment-header {
      display: flex; align-items: baseline; gap: 0.6rem;
      margin-bottom: 0.4rem;
    }
    .comment-alias {
      font-family: var(--font-mono); font-size: 0.78rem;
      color: var(--color-accent); font-weight: 600;
    }
    .comment-date {
      font-family: var(--font-mono); font-size: 0.65rem;
      color: var(--color-muted-2);
    }
    .comment-body {
      font-size: 0.9rem; color: var(--color-ink);
      line-height: 1.55; white-space: pre-wrap; word-break: break-word;
    }
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

    <!-- Comentarios -->
    <section class="comments-section">
      <div class="comments-title">comentarios</div>

      <form class="comment-form" id="comment-form">
        <input
          type="text" id="alias-input"
          placeholder="tu nombre o alias"
          maxlength="32" autocomplete="nickname"
        />
        <textarea
          id="body-input"
          placeholder="deja un comentario..."
          maxlength="500"
        ></textarea>
        <span class="comment-error" id="comment-error"></span>
        <button type="submit" class="comment-submit" id="comment-submit">
          enviar →
        </button>
      </form>

      <div class="comments-list" id="comments-list">
        <span class="comment-empty">cargando comentarios...</span>
      </div>
    </section>
  </div>

  <script define:vars={{ videoId: id }}>
    // ── Copiar link ──
    const btn = document.getElementById('copy-btn');
    const urlEl = document.getElementById('share-url');
    btn?.addEventListener('click', () => {
      navigator.clipboard.writeText(urlEl?.textContent?.trim() ?? '').then(() => {
        if (btn) { btn.textContent = '✓ copiado'; setTimeout(() => { btn.textContent = 'copiar link'; }, 2000); }
      });
    });

    // ── Comentarios ──
    const list = document.getElementById('comments-list');
    const form = document.getElementById('comment-form');
    const aliasInput = document.getElementById('alias-input');
    const bodyInput = document.getElementById('body-input');
    const submitBtn = document.getElementById('comment-submit');
    const errorEl = document.getElementById('comment-error');

    function formatDate(str) {
      try {
        return new Date(str + 'Z').toLocaleString('es-MX', {
          day: '2-digit', month: 'short', year: 'numeric',
          hour: '2-digit', minute: '2-digit'
        });
      } catch { return str; }
    }

    function renderComments(comments) {
      if (!list) return;
      if (!comments.length) {
        list.innerHTML = '<span class="comment-empty">sin comentarios todavía. sé el primero ✨</span>';
        return;
      }
      list.innerHTML = comments.map(c => `
        <div class="comment-card">
          <div class="comment-header">
            <span class="comment-alias">${c.alias}</span>
            <span class="comment-date">${formatDate(c.created_at)}</span>
          </div>
          <div class="comment-body">${c.body.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>
        </div>
      `).join('');
    }

    async function loadComments() {
      try {
        const res = await fetch(`/api/videos/comments?id=${videoId}`);
        const data = await res.json();
        renderComments(Array.isArray(data) ? data : []);
      } catch {
        if (list) list.innerHTML = '<span class="comment-empty">error al cargar comentarios.</span>';
      }
    }

    // Restaurar alias guardado
    const savedAlias = localStorage.getItem('aris_comment_alias') ?? '';
    if (aliasInput && savedAlias) aliasInput.value = savedAlias;

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const alias = aliasInput?.value?.trim();
      const body  = bodyInput?.value?.trim();
      if (errorEl) errorEl.style.display = 'none';
      if (!alias || !body) {
        if (errorEl) { errorEl.textContent = 'nombre y comentario son requeridos'; errorEl.style.display = 'block'; }
        return;
      }
      if (submitBtn) submitBtn.disabled = true;
      try {
        const res = await fetch(`/api/videos/comments?id=${videoId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ alias, body })
        });
        const data = await res.json();
        if (data.ok) {
          localStorage.setItem('aris_comment_alias', alias);
          if (bodyInput) bodyInput.value = '';
          await loadComments();
          list?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
          if (errorEl) { errorEl.textContent = data.error ?? 'error al enviar'; errorEl.style.display = 'block'; }
        }
      } catch {
        if (errorEl) { errorEl.textContent = 'error de red'; errorEl.style.display = 'block'; }
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });

    loadComments();
  </script>
</body>
</html>
"""
with open(os.path.join(BASE, "src", "pages", "v", "[id].astro"), "w") as f:
    f.write(video_page)
print("✅ src/pages/v/[id].astro actualizado")

# ─── 4. Inicializar la tabla comments en la DB existente ─────────────────────
result = subprocess.run(
    ["docker", "exec", "misitio-web-1", "bun", "-e",
     "import {Database} from 'bun:sqlite'; import {join} from 'path';"
     "const db = new Database(join(process.cwd(),'data','database.sqlite'));"
     "db.run(`CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, video_id TEXT NOT NULL, alias TEXT NOT NULL, body TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)`);"
     "db.close(); console.log('ok');"],
    capture_output=True, text=True
)
if "ok" in result.stdout:
    print("✅ tabla comments creada en DB")
else:
    print("⚠️  crear tabla manualmente después del rebuild con:")
    print("   sudo docker exec misitio-web-1 bun run scripts/init-comments-db.ts")

# ─── 5. Rebuild ───────────────────────────────────────────────────────────────
print("\n🔨 Rebuilding...")
result = subprocess.run(
    ["docker", "compose", "up", "-d", "--build"],
    cwd=BASE, capture_output=True, text=True
)
print(result.stdout[-2000:] if result.stdout else "")
if result.returncode != 0:
    print("❌ Error:", result.stderr[-2000:])
else:
    print("✅ Listo.")
    print("\nSi los descriptores no aparecen en Discord, corre:")
    print("  curl 'https://discord.com/api/v9/unfurl?url=https://aris-sama.duckdns.org/v/TU_ID'")
    print("  (Discord cachea embeds — comparte el link en un canal nuevo o edita el mensaje)")
