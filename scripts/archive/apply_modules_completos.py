#!/usr/bin/env python3
"""
apply_modules_completos.py
Crea TODOS los módulos faltantes del sitio aris-sama en una sola pasada.

Módulos que crea / completa:
  1. Gacha   → /src/pages/api/enka-gi.ts   enka-hsr.ts   enka-zzz.ts
               /scripts/sync-enka-gi.ts    sync-enka-hsr.ts   (reemplaza los vacíos)
               /scripts/init-gacha-db.ts   (crea las tablas characters + videos)
  2. Videos  → /src/features/video/VideoGrid.astro
               /src/pages/videos.astro
               /src/pages/api/videos.ts
  3. Admin   → /src/pages/admin/login.astro
               /src/pages/admin/index.astro
               /src/pages/api/auth/login.ts
               /src/pages/api/auth/logout.ts

También actualiza:
  - AGENTS.md       (añade módulos nuevos)
  - STRUCTURE.json  (actualiza estados)

USO:
  scp apply_modules_completos.py usuario@servidor:~/
  python3 apply_modules_completos.py
  docker compose up -d --build
"""

import os, json, textwrap
from pathlib import Path

ROOT = Path(__file__).parent
CREATED = []
UPDATED = []

# ─────────────────────────────────────────────
#  Utilidades
# ─────────────────────────────────────────────

def write(path: str, content: str, *, update=False):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    if update:
        UPDATED.append(path)
    else:
        CREATED.append(path)
    print(f"  {'✏️ ' if update else '✅'} {path}")


# ═══════════════════════════════════════════════════════════════
#  1. GACHA — API endpoints
# ═══════════════════════════════════════════════════════════════
print("\n🎮 Creando módulo Gacha — API endpoints...")

# ── enka-gi.ts (Genshin Impact) ──────────────────────────────
write("src/pages/api/enka-gi.ts", """
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
""")

# ── enka-hsr.ts (Honkai: Star Rail) ──────────────────────────
write("src/pages/api/enka-hsr.ts", """
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
      "SELECT * FROM characters WHERE game = 'hsr' ORDER BY rarity DESC, level DESC"
    ).all();
    db.close();

    if (rows.length > 0) {
      _cache = { data: rows, ts: Date.now() };
      return new Response(JSON.stringify({ characters: rows, cached: false }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }
  } catch (e) {}

  return new Response(JSON.stringify({ characters: [], cached: false, note: 'Sin datos. Ejecuta: bun run scripts/sync-enka-hsr.ts' }), {
    headers: { 'Content-Type': 'application/json' }
  });
};
""")

# ── enka-zzz.ts (Zenless Zone Zero) ──────────────────────────
write("src/pages/api/enka-zzz.ts", """
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
""")

# ── init-gacha-db.ts — crea tablas characters + videos ────────
write("scripts/init-gacha-db.ts", """
/**
 * Inicializa la base de datos SQLite con todas las tablas necesarias.
 * Ejecutar UNA vez antes del primer sync:
 *   bun run scripts/init-gacha-db.ts
 */
import { Database } from 'bun:sqlite';

const db = new Database('data/database.sqlite');

db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id          TEXT PRIMARY KEY,
    game        TEXT NOT NULL,
    name        TEXT NOT NULL,
    level       INTEGER DEFAULT 1,
    rarity      INTEGER DEFAULT 4,
    element     TEXT,
    path        TEXT,
    constellation INTEGER DEFAULT 0,
    imageUrl    TEXT,
    synced_at   DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

db.run(`
  CREATE TABLE IF NOT EXISTS videos (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    url         TEXT NOT NULL,
    thumbnail   TEXT,
    category    TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

console.log('✅ Tablas characters y videos listas en data/database.sqlite');
db.close();
""")

# ── sync-enka-gi.ts — versión completa (reemplaza el stub) ────
write("scripts/sync-enka-gi.ts", """
/**
 * Sincroniza personajes de Genshin Impact desde Enka Network.
 * Ejecutar después de actualizar tu showcase:
 *   bun run scripts/sync-enka-gi.ts
 */
import { Database } from 'bun:sqlite';

const UID  = '603731692';
const GAME = 'gi';

const db = new Database('data/database.sqlite');

// Asegurar tabla existe
db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, game TEXT NOT NULL, name TEXT NOT NULL,
    level INTEGER DEFAULT 1, rarity INTEGER DEFAULT 4, element TEXT,
    path TEXT, constellation INTEGER DEFAULT 0, imageUrl TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

async function syncGenshin() {
  console.log(`⏳ Sincronizando Genshin Impact UID ${UID}...`);

  const res = await fetch(`https://enka.network/api/uid/${UID}`, {
    headers: { 'User-Agent': 'aris-sama-site/1.0 (personal portfolio)' }
  });

  if (!res.ok) throw new Error(`Enka respondió ${res.status}`);
  const data = await res.json() as any;

  const avatarList: any[] = data.avatarInfoList ?? [];
  if (!avatarList.length) {
    console.warn('⚠️  No hay personajes en el showcase (máximo 8-9). Agrega personajes en el juego.');
    return;
  }

  const stmt = db.prepare(`
    INSERT INTO characters (id, game, name, level, rarity, element, constellation, imageUrl, synced_at)
    VALUES ($id, $game, $name, $level, $rarity, $element, $constellation, $imageUrl, datetime('now'))
    ON CONFLICT(id) DO UPDATE SET
      level = excluded.level, constellation = excluded.constellation, synced_at = excluded.synced_at
  `);

  // Mapa de elementos de GI
  const ELEMENTS: Record<number, string> = {
    1: 'Pyro', 2: 'Hydro', 3: 'Dendro', 4: 'Electro', 5: 'Anemo', 6: 'Cryo', 7: 'Geo'
  };

  let count = 0;
  for (const av of avatarList) {
    const id = `gi_${av.avatarId}`;
    const name: string = data.playerInfo?.showAvatarInfoList?.find((a: any) => a.avatarId === av.avatarId)?.name
      ?? `Personaje ${av.avatarId}`;
    const level = av.propMap?.[4001]?.val ? parseInt(av.propMap[4001].val) : 1;
    const element = ELEMENTS[av.skillDepotId >> 9 & 0xF] ?? '';
    const constellation = (av.talentIdList ?? []).length;
    const rarity = av.rarity ?? 4;
    const imageUrl = `https://enka.network/ui/UI_AvatarIcon_${av.avatarId}.png`;

    stmt.run({ $id: id, $game: GAME, $name: name, $level: level, $rarity: rarity,
      $element: element, $constellation: constellation, $imageUrl: imageUrl });
    count++;
  }

  console.log(`✅ ${count} personajes de Genshin sincronizados.`);
}

syncGenshin()
  .catch(e => console.error('❌', e))
  .finally(() => db.close());
""", update=True)

# ── sync-enka-hsr.ts — versión completa ───────────────────────
write("scripts/sync-enka-hsr.ts", """
/**
 * Sincroniza personajes de Honkai: Star Rail desde Enka Network.
 *   bun run scripts/sync-enka-hsr.ts
 */
import { Database } from 'bun:sqlite';

const UID  = '600180174';
const GAME = 'hsr';

const db = new Database('data/database.sqlite');

db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, game TEXT NOT NULL, name TEXT NOT NULL,
    level INTEGER DEFAULT 1, rarity INTEGER DEFAULT 4, element TEXT,
    path TEXT, constellation INTEGER DEFAULT 0, imageUrl TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

async function syncHSR() {
  console.log(`⏳ Sincronizando Honkai: Star Rail UID ${UID}...`);

  const res = await fetch(`https://enka.network/api/hsr/uid/${UID}`, {
    headers: { 'User-Agent': 'aris-sama-site/1.0 (personal portfolio)' }
  });

  if (!res.ok) throw new Error(`Enka respondió ${res.status}`);
  const data = await res.json() as any;

  const avatarList: any[] = data.detailInfo?.avatarDetailList ?? [];
  if (!avatarList.length) {
    console.warn('⚠️  No hay personajes en el showcase de HSR.');
    return;
  }

  const stmt = db.prepare(`
    INSERT INTO characters (id, game, name, level, rarity, element, path, constellation, imageUrl, synced_at)
    VALUES ($id, $game, $name, $level, $rarity, $element, $path, $constellation, $imageUrl, datetime('now'))
    ON CONFLICT(id) DO UPDATE SET
      level = excluded.level, constellation = excluded.constellation, synced_at = excluded.synced_at
  `);

  let count = 0;
  for (const av of avatarList) {
    const id = `hsr_${av.avatarId}`;
    const name: string = av.avatarName ?? `Personaje ${av.avatarId}`;
    const level: number = av.level ?? 1;
    const rarity: number = av.rarity ?? 4;
    const element: string = av.element ?? '';
    const path: string = av.baseType ?? '';
    const constellation: number = av.rank ?? 0;
    const imageUrl = `https://enka.network/ui/hsr/SpriteOutput/AvatarRoundIcon/${av.avatarId}.png`;

    stmt.run({ $id: id, $game: GAME, $name: name, $level: level, $rarity: rarity,
      $element: element, $path: path, $constellation: constellation, $imageUrl: imageUrl });
    count++;
  }

  console.log(`✅ ${count} personajes de HSR sincronizados.`);
}

syncHSR()
  .catch(e => console.error('❌', e))
  .finally(() => db.close());
""", update=True)

# ── sync-enka-zzz.ts (stub funcional — API en beta) ───────────
write("scripts/sync-enka-zzz.ts", """
/**
 * Zenless Zone Zero — Enka aún no expone endpoint público estable para ZZZ.
 * Este script inserta personajes manualmente como placeholder.
 * Cuando Enka lo soporte, actualizar a fetch como GI/HSR.
 *
 *   bun run scripts/sync-enka-zzz.ts
 */
import { Database } from 'bun:sqlite';

const GAME = 'zzz';

const db = new Database('data/database.sqlite');
db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, game TEXT NOT NULL, name TEXT NOT NULL,
    level INTEGER DEFAULT 1, rarity INTEGER DEFAULT 4, element TEXT,
    path TEXT, constellation INTEGER DEFAULT 0, imageUrl TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Agrega aquí tus personajes de ZZZ manualmente por ahora
const ZZZ_MANUAL = [
  // { id: 'zzz_belle', name: 'Belle', level: 60, rarity: 5, element: 'Electric', imageUrl: '' },
];

if (!ZZZ_MANUAL.length) {
  console.log('ℹ️  No hay personajes ZZZ definidos. Agrega tus personajes en el array ZZZ_MANUAL de este script.');
  db.close();
  process.exit(0);
}

const stmt = db.prepare(`
  INSERT INTO characters (id, game, name, level, rarity, element, constellation, imageUrl, synced_at)
  VALUES ($id, $game, $name, $level, $rarity, $element, $constellation, $imageUrl, datetime('now'))
  ON CONFLICT(id) DO UPDATE SET level = excluded.level, synced_at = excluded.synced_at
`);

for (const c of ZZZ_MANUAL) {
  stmt.run({ $id: c.id, $game: GAME, $name: c.name, $level: c.level,
    $rarity: c.rarity, $element: c.element, $constellation: 0, $imageUrl: c.imageUrl ?? '' });
}

console.log(`✅ ${ZZZ_MANUAL.length} personajes ZZZ guardados.`);
db.close();
""")


# ═══════════════════════════════════════════════════════════════
#  2. VIDEOS — feature + página + API
# ═══════════════════════════════════════════════════════════════
print("\n🎬 Creando módulo Videos...")

write("src/features/video/VideoGrid.astro", """
---
// VideoGrid.astro — lista de videos desde /api/videos
---
<div class="video-module" id="video-module">
  <div class="video-loading font-mono text-sm">Cargando videos…</div>
</div>

<script>
  async function loadVideos() {
    const container = document.getElementById('video-module');
    if (!container) return;

    try {
      const res = await fetch('/api/videos');
      const data = await res.json();
      const videos: any[] = data.videos ?? [];

      if (!videos.length) {
        container.innerHTML = `
          <div class="video-empty">
            <p class="font-mono text-sm" style="color:var(--color-muted);padding:2rem;text-align:center;">
              Sin videos todavía. Añade entradas a la tabla <code>videos</code> de la DB.
            </p>
          </div>`;
        return;
      }

      const grid = document.createElement('div');
      grid.className = 'video-grid';

      for (const v of videos) {
        // Detectar si es YouTube embed o URL directa
        const ytMatch = v.url?.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/))([\\w-]{11})/);
        const embedUrl = ytMatch ? `https://www.youtube.com/embed/${ytMatch[1]}` : null;

        grid.innerHTML += `
          <article class="video-card">
            <div class="video-thumb">
              ${embedUrl
                ? `<iframe src="${embedUrl}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen style="width:100%;height:100%;border:0;"></iframe>`
                : v.thumbnail
                  ? `<img src="${v.thumbnail}" alt="${v.title}" loading="lazy" style="width:100%;height:100%;object-fit:cover;" />`
                  : `<div class="video-placeholder">▶</div>`
              }
            </div>
            <div class="video-info">
              <span class="video-category font-mono">${v.category ?? 'general'}</span>
              <h3 class="video-title">${v.title}</h3>
            </div>
          </article>
        `;
      }

      container.innerHTML = '';
      container.appendChild(grid);
    } catch (e) {
      if (container) container.innerHTML = `<p style="color:#F87171;font-family:monospace;padding:1rem;">Error: ${e}</p>`;
    }
  }

  document.addEventListener('DOMContentLoaded', loadVideos);
  document.addEventListener('astro:page-load', loadVideos);
</script>

<style>
  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.25rem;
  }
  .video-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
  }
  .video-card:hover { transform: translateY(-3px); border-color: rgba(168,85,247,0.4); }
  .video-thumb {
    aspect-ratio: 16/9;
    background: rgba(168,85,247,0.06);
    overflow: hidden;
    position: relative;
  }
  .video-placeholder {
    display: flex; align-items: center; justify-content: center;
    width: 100%; height: 100%;
    font-size: 2rem; opacity: 0.3; color: var(--color-accent);
  }
  .video-info { padding: 0.75rem 1rem; }
  .video-category {
    font-size: 0.65rem; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--color-accent); display: block; margin-bottom: 0.25rem;
  }
  .video-title {
    font-size: 0.875rem; color: var(--color-ink); font-weight: 500; line-height: 1.4;
    overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  }
  .video-loading { color: var(--color-muted); padding: 2rem; text-align: center; font-size: 0.875rem; }
</style>
""")

write("src/pages/videos.astro", """
---
import Base from '../layouts/Base.astro';
---
<Base title="Videos · aris-sama" description="Videos que he creado o que me gustan">
  <main class="max-w-4xl mx-auto px-4 py-12">
    <header class="mb-8">
      <h1 class="font-mono text-2xl" style="color:var(--color-accent)">VIDEOS</h1>
      <p class="text-sm mt-1" style="color:var(--color-muted)">
        Contenido visual — tutoriales, clips, favoritos
      </p>
    </header>

    <div id="video-root">
      <div class="video-grid-shell"></div>
    </div>
  </main>
</Base>

<script>
  import('/api/videos'); // pre-warm
</script>

<style>
  .max-w-4xl { max-width: 56rem; }
  .mx-auto { margin-inline: auto; }
  .px-4 { padding-inline: 1rem; }
  .py-12 { padding-block: 3rem; }
  .mb-8 { margin-bottom: 2rem; }
  .mt-1 { margin-top: 0.25rem; }
  .font-mono { font-family: var(--font-mono); }
  .text-2xl { font-size: var(--text-2xl); }
  .text-sm { font-size: var(--text-sm); }
</style>

<!-- Cargar el feature component por script dinámico -->
<div id="video-feature-mount"></div>
<script type="module">
  // Renderizamos la grilla directamente aquí en vez de importar el .astro
  async function init() {
    const root = document.getElementById('video-root');
    if (!root) return;

    try {
      const res = await fetch('/api/videos');
      const { videos = [] } = await res.json();

      if (!videos.length) {
        root.innerHTML = `<p style="font-family:var(--font-mono);color:var(--color-muted);padding:2rem 0;font-size:0.875rem;">
          Sin videos todavía. Agrega videos a la base de datos con <code>bun run scripts/init-gacha-db.ts</code>.
        </p>`;
        return;
      }

      const grid = document.createElement('div');
      grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.25rem;';

      for (const v of videos) {
        const ytMatch = v.url?.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/))([\\w-]{11})/);
        const embedUrl = ytMatch ? `https://www.youtube.com/embed/${ytMatch[1]}` : null;
        const card = document.createElement('article');
        card.style.cssText = 'background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;transition:transform 0.2s,border-color 0.2s;';
        card.innerHTML = `
          <div style="aspect-ratio:16/9;background:rgba(168,85,247,0.06);overflow:hidden;">
            ${embedUrl
              ? `<iframe src="${embedUrl}" loading="lazy" allow="autoplay;encrypted-media" allowfullscreen style="width:100%;height:100%;border:0;"></iframe>`
              : `<div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;font-size:2rem;opacity:0.3;color:var(--color-accent);">▶</div>`}
          </div>
          <div style="padding:0.75rem 1rem;">
            <span style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--color-accent);">${v.category ?? 'general'}</span>
            <h3 style="font-size:0.875rem;color:var(--color-ink);font-weight:500;margin-top:0.25rem;line-height:1.4;">${v.title}</h3>
          </div>
        `;
        grid.appendChild(card);
      }

      root.innerHTML = '';
      root.appendChild(grid);
    } catch(e) {
      root.innerHTML = `<p style="color:#F87171;font-family:monospace;">${e}</p>`;
    }
  }

  init();
  document.addEventListener('astro:page-load', init);
</script>
""")

write("src/pages/api/videos.ts", """
import type { APIRoute } from 'astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

export const GET: APIRoute = async () => {
  try {
    const db = new Database(join(process.cwd(), 'data', 'database.sqlite'), { readonly: true });
    const videos = db.query('SELECT * FROM videos ORDER BY created_at DESC').all();
    db.close();
    return new Response(JSON.stringify({ videos }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch {
    return new Response(JSON.stringify({ videos: [], note: 'DB no inicializada. Ejecuta init-gacha-db.ts' }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
""")


# ═══════════════════════════════════════════════════════════════
#  3. ADMIN — login + panel + auth endpoints
# ═══════════════════════════════════════════════════════════════
print("\n🔐 Creando módulo Admin + Login...")

write("src/pages/admin/login.astro", """
---
// /admin/login — formulario de acceso. No usa Base.astro (layout propio minimal).
// El middleware redirige aquí cuando la sesión no es válida.

// Si ya tiene sesión válida, redirigir al panel
const session = Astro.cookies.get('aris_admin');
if (session?.value) {
  return Astro.redirect('/admin');
}
---
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>aris · acceso</title>
  <link rel="stylesheet" href="/design-tokens.css" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      min-height: 100dvh;
      font-family: var(--font-mono);
      background: var(--color-bg);
      color: var(--color-ink);
      display: flex; align-items: center; justify-content: center;
    }
    .login-box {
      width: 100%; max-width: 22rem;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: var(--radius-xl);
      padding: 2.5rem 2rem;
      backdrop-filter: blur(16px);
    }
    .login-header { margin-bottom: 2rem; }
    .login-prompt {
      font-size: var(--text-xs); color: var(--color-accent);
      letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.5rem;
    }
    .login-title { font-size: var(--text-xl); color: var(--color-ink); }
    label { display: block; font-size: var(--text-xs); color: var(--color-muted); margin-bottom: 0.4rem; letter-spacing: 0.06em; }
    .field { margin-bottom: 1.25rem; }
    input[type="password"] {
      width: 100%; background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: var(--radius-md);
      padding: 0.65rem 0.875rem;
      font-family: var(--font-mono); font-size: var(--text-sm);
      color: var(--color-ink);
      outline: none;
      transition: border-color 0.15s;
    }
    input[type="password"]:focus { border-color: var(--color-accent); }
    button[type="submit"] {
      width: 100%;
      background: var(--color-accent); color: var(--color-bg);
      border: none; border-radius: var(--radius-md);
      padding: 0.7rem 1rem;
      font-family: var(--font-mono); font-size: var(--text-sm); font-weight: 500;
      cursor: pointer; letter-spacing: 0.04em;
      transition: opacity 0.15s, transform 0.15s;
    }
    button[type="submit"]:hover { opacity: 0.88; transform: translateY(-1px); }
    .error-msg {
      color: #F87171; font-size: var(--text-xs);
      margin-top: 1rem; text-align: center; display: none;
    }
    .error-msg.visible { display: block; }
  </style>
</head>
<body>
  <div class="login-box">
    <div class="login-header">
      <p class="login-prompt">~/admin</p>
      <h1 class="login-title">acceso restringido</h1>
    </div>
    <div class="field">
      <label for="pwd">contraseña</label>
      <input type="password" id="pwd" autocomplete="current-password" autofocus />
    </div>
    <button type="submit" id="login-btn">entrar →</button>
    <p class="error-msg" id="err-msg">contraseña incorrecta</p>
  </div>

  <script>
    const btn = document.getElementById('login-btn');
    const pwd = document.getElementById('pwd');
    const err = document.getElementById('err-msg');

    async function doLogin() {
      btn.textContent = '…';
      btn.disabled = true;
      err.classList.remove('visible');

      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: pwd.value })
        });

        if (res.ok) {
          window.location.href = '/admin';
        } else {
          err.classList.add('visible');
          pwd.value = '';
          pwd.focus();
        }
      } catch {
        err.textContent = 'error de conexión';
        err.classList.add('visible');
      } finally {
        btn.textContent = 'entrar →';
        btn.disabled = false;
      }
    }

    btn.addEventListener('click', doLogin);
    pwd.addEventListener('keydown', (e) => { if (e.key === 'Enter') doLogin(); });
  </script>
</body>
</html>
""")

write("src/pages/admin/index.astro", """
---
import Base from '../../layouts/Base.astro';
import { readFileSync } from 'fs';
import { join } from 'path';

// El middleware ya verificó la sesión — si llegamos aquí, estamos autenticados.

let nowData: any = {}, homepageData: any = {}, booksData: any[] = [];
try { nowData      = JSON.parse(readFileSync(join(process.cwd(), 'data', 'now.json'), 'utf-8')); } catch {}
try { homepageData = JSON.parse(readFileSync(join(process.cwd(), 'data', 'homepage.json'), 'utf-8')); } catch {}
try { booksData    = JSON.parse(readFileSync(join(process.cwd(), 'data', 'books.json'), 'utf-8')); } catch {}
---
<Base title="Admin · aris-sama">
  <div class="admin-shell">
    <header class="admin-header">
      <div>
        <span class="admin-badge">root@aris</span>
        <h1 class="admin-title">panel de control</h1>
      </div>
      <button id="logout-btn" class="logout-btn">cerrar sesión</button>
    </header>

    <!-- Estado del sitio -->
    <section class="admin-section">
      <h2 class="section-heading">estado del sitio</h2>
      <div class="stat-grid">
        <div class="stat-card">
          <span class="stat-label">now items</span>
          <span class="stat-value">{nowData.items?.length ?? 0}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">libros</span>
          <span class="stat-value">{Array.isArray(booksData) ? booksData.length : 0}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">última actualización now</span>
          <span class="stat-value">{nowData.updated ?? '—'}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">homepage blocks</span>
          <span class="stat-value">{homepageData.blocks?.length ?? 0}</span>
        </div>
      </div>
    </section>

    <!-- Comandos rápidos -->
    <section class="admin-section">
      <h2 class="section-heading">comandos rápidos</h2>
      <div class="cmd-grid">
        <a href="/now" class="cmd-card cmd-link">
          <span class="cmd-icon">⚡</span>
          <div><strong>ver /now</strong><p>página de estado actual</p></div>
        </a>
        <a href="/gacha" class="cmd-card cmd-link">
          <span class="cmd-icon">✦</span>
          <div><strong>ver /gacha</strong><p>roster de personajes</p></div>
        </a>
        <a href="/videos" class="cmd-card cmd-link">
          <span class="cmd-icon">▶</span>
          <div><strong>ver /videos</strong><p>galería de videos</p></div>
        </a>
        <div class="cmd-card">
          <span class="cmd-icon">🔃</span>
          <div>
            <strong>sync gacha</strong>
            <p class="cmd-hint font-mono">docker exec web bun run scripts/sync-enka-gi.ts</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Now.json editor rápido -->
    <section class="admin-section">
      <h2 class="section-heading">now.json <span class="section-badge">datos actuales</span></h2>
      <pre class="json-preview">{JSON.stringify(nowData, null, 2)}</pre>
      <p class="admin-hint">Para editar: <code>pide a Claude que actualice /data/now.json</code> o edita el archivo y haz rebuild.</p>
    </section>
  </div>
</Base>

<script>
  document.getElementById('logout-btn')?.addEventListener('click', async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/admin/login';
  });
</script>

<style>
  .admin-shell { max-width: 52rem; margin: 0 auto; padding: var(--space-10) var(--space-4); }

  .admin-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: var(--space-10);
    padding-bottom: var(--space-6);
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .admin-badge {
    font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.1em;
    color: var(--color-accent); text-transform: uppercase; display: block; margin-bottom: 0.4rem;
  }
  .admin-title {
    font-family: var(--font-display); font-size: var(--text-3xl);
    color: var(--color-ink); line-height: 1.1;
  }
  .logout-btn {
    font-family: var(--font-mono); font-size: var(--text-xs);
    color: var(--color-muted); background: none;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-sm); padding: var(--space-2) var(--space-3);
    cursor: pointer; letter-spacing: 0.06em;
    transition: color 0.15s, border-color 0.15s;
  }
  .logout-btn:hover { color: #F87171; border-color: rgba(248,113,113,0.4); }

  .admin-section { margin-bottom: var(--space-10); }
  .section-heading {
    font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--color-muted); margin-bottom: var(--space-4);
    display: flex; align-items: center; gap: var(--space-3);
  }
  .section-badge {
    font-size: 0.6rem; background: rgba(168,85,247,0.15);
    border: 1px solid rgba(168,85,247,0.3);
    border-radius: var(--radius-full); padding: 1px 8px;
    color: var(--color-accent); text-transform: lowercase; letter-spacing: 0.04em;
  }

  .stat-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: var(--space-3);
  }
  .stat-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-md); padding: var(--space-4) var(--space-5);
    display: flex; flex-direction: column; gap: var(--space-1);
  }
  .stat-label { font-family: var(--font-mono); font-size: 0.65rem; color: var(--color-muted); letter-spacing: 0.08em; text-transform: uppercase; }
  .stat-value { font-family: var(--font-mono); font-size: var(--text-xl); color: var(--color-ink); font-weight: 500; }

  .cmd-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-3); }
  .cmd-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-md); padding: var(--space-4);
    display: flex; align-items: flex-start; gap: var(--space-3);
    transition: background 0.15s, border-color 0.15s;
  }
  .cmd-link { text-decoration: none; color: inherit; }
  .cmd-link:hover { background: rgba(168,85,247,0.08); border-color: rgba(168,85,247,0.3); }
  .cmd-icon { font-size: var(--text-xl); flex-shrink: 0; }
  .cmd-card strong { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-ink); display: block; margin-bottom: 2px; }
  .cmd-card p { font-size: var(--text-xs); color: var(--color-muted); line-height: 1.4; }
  .cmd-hint { font-size: 0.65rem !important; color: var(--color-muted-2) !important; word-break: break-all; margin-top: 4px; }

  .json-preview {
    background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.06);
    border-radius: var(--radius-md); padding: var(--space-5);
    font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-ink-soft);
    overflow-x: auto; line-height: 1.6; max-height: 280px; overflow-y: auto;
  }
  .admin-hint {
    margin-top: var(--space-3); font-size: var(--text-xs); color: var(--color-muted-2); line-height: 1.5;
  }
  .admin-hint code {
    background: rgba(168,85,247,0.12); border-radius: 3px;
    padding: 1px 5px; font-family: var(--font-mono); font-size: 0.7rem; color: var(--color-accent);
  }
  .font-mono { font-family: var(--font-mono); }
</style>
""")

write("src/pages/api/auth/login.ts", """
import type { APIRoute } from 'astro';

/**
 * POST /api/auth/login
 * Body: { password: string }
 *
 * Verifica contra ADMIN_HASH (PBKDF2-SHA256 + salt almacenado en .env)
 * Si es correcto, emite cookie aris_admin con token HMAC firmado.
 */

async function pbkdf2Verify(
  password: string,
  saltHex: string,
  storedHashB64: string,
  iterations: number
): Promise<boolean> {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']
  );
  const salt = new Uint8Array(saltHex.match(/.{2}/g)!.map(b => parseInt(b, 16)));
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-256', salt, iterations },
    keyMaterial,
    256
  );
  const derived = btoa(String.fromCharCode(...new Uint8Array(bits)));
  return derived === storedHashB64;
}

async function makeToken(secret: string): Promise<string> {
  const payload = btoa(JSON.stringify({ ts: Date.now() }));
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payload));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)));
  return `${payload}.${sigB64}`;
}

export const POST: APIRoute = async ({ request, cookies }) => {
  let body: { password?: string };
  try { body = await request.json(); } catch { return new Response('bad request', { status: 400 }); }

  const { password } = body;
  if (!password) return new Response('missing password', { status: 400 });

  const hash       = import.meta.env.ADMIN_HASH;
  const salt       = import.meta.env.ADMIN_SALT;
  const iterations = parseInt(import.meta.env.ADMIN_ITERATIONS ?? '260000', 10);
  const secret     = import.meta.env.ADMIN_JWT_SECRET;

  if (!hash || !salt || !secret) {
    return new Response('server misconfigured', { status: 500 });
  }

  const ok = await pbkdf2Verify(password, salt, hash, iterations);
  if (!ok) return new Response('unauthorized', { status: 401 });

  const token = await makeToken(secret);
  cookies.set('aris_admin', token, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    path: '/',
    maxAge: 8 * 60 * 60  // 8h
  });

  return new Response('ok', { status: 200 });
};
""")

write("src/pages/api/auth/logout.ts", """
import type { APIRoute } from 'astro';

export const POST: APIRoute = ({ cookies }) => {
  cookies.delete('aris_admin', { path: '/' });
  return new Response('ok', { status: 200 });
};
""")


# ═══════════════════════════════════════════════════════════════
#  4. Actualizar AGENTS.md y STRUCTURE.json
# ═══════════════════════════════════════════════════════════════
print("\n📄 Actualizando AGENTS.md y STRUCTURE.json...")

write("AGENTS.md", """
# AGENTS.md
Última actualización: Marzo 2026 · Fase 2 activa

## Stack
Astro 6 + Bun + Tailwind v4 + Zod + Motion
Self-hosted: Oracle Cloud ARM (aarch64), Caddy reverse proxy
Deploy: `docker compose up -d --build`
Servidor de producción: `bun ./dist/server/entry.mjs` (NO astro preview)

## Reglas invariables
1. NUNCA modificar `/src/blocks/` sin autorización explícita
2. SIEMPRE validar JSONs contra esquema Zod en `content.config.ts`
3. Para contenido: editar `/data/*.json` o `/content/*.md`
4. Para módulo nuevo: crear carpeta en `/src/features/[nombre]/`
5. Actualizar este archivo y `STRUCTURE.json` al crear módulos
6. Para modificar archivos en servidor: generar script `apply_*.py`

## Infra crítica (lecciones del deploy)
- Caddy usa `reverse_proxy web:4321` (nombre de servicio Docker, NO localhost)
- El adaptador es `@astrojs/node` en modo `standalone`
- `docker-compose.override.yml` lanza: `bun ./dist/server/entry.mjs`
- Sharp falla en ARM: usar `@unpic/astro` para imágenes
- Siempre `--platform linux/arm64` en Dockerfiles
- SQLite en volumen Docker `/data/` — NUNCA dentro de la imagen
- Variables de entorno en `.env`: ADMIN_HASH, ADMIN_SALT, ADMIN_ITERATIONS, ADMIN_JWT_SECRET

## Módulos activos
- [x] Base.astro — layout, nav, fuentes, View Transitions (ClientRouter)
- [x] design-tokens.css — paleta Stellar Terminal (cosmic void + glass)
- [x] now — /now + preview en homepage, datos en /data/now.json
- [x] radio — RadioPlayer.astro fixed bottom-right, persiste entre páginas
- [x] gacha — /gacha + /api/enka-gi /api/enka-hsr /api/enka-zzz + SQLite
- [x] videos — /videos + /api/videos + SQLite tabla videos
- [x] admin — /admin (panel protegido) + /admin/login
- [ ] garden / bookshelf / portfolio / blog / gallery

## Archivos clave
| Archivo | Propósito |
|---|---|
| `AGENTS.md` | Este archivo — memoria de Claude |
| `STRUCTURE.json` | Mapa vivo del sistema |
| `public/design-tokens.css` | Todas las variables CSS |
| `src/middleware.ts` | Protección de rutas /admin/* |
| `data/*.json` | Contenido editable por Claude |
| `data/database.sqlite` | SQLite: tablas characters + videos |

## Rutas de API
| Endpoint | Método | Descripción |
|---|---|---|
| `/api/enka-gi` | GET | Personajes Genshin Impact de SQLite |
| `/api/enka-hsr` | GET | Personajes Honkai: Star Rail de SQLite |
| `/api/enka-zzz` | GET | Personajes Zenless Zone Zero de SQLite |
| `/api/videos` | GET | Lista de videos de SQLite |
| `/api/auth/login` | POST | Login admin — emite cookie aris_admin |
| `/api/auth/logout` | POST | Logout — borra cookie |

## Scripts de mantenimiento
| Script | Descripción |
|---|---|
| `bun run scripts/init-gacha-db.ts` | Inicializa tablas characters + videos (ejecutar 1 vez) |
| `bun run scripts/sync-enka-gi.ts` | Sync personajes Genshin desde Enka Network |
| `bun run scripts/sync-enka-hsr.ts` | Sync personajes HSR desde Enka Network |
| `bun run scripts/sync-enka-zzz.ts` | Personajes ZZZ (manual hasta que Enka lo soporte) |
""", update=True)

structure = {
  "version": "2.0.0",
  "fase": 2,
  "stack": {
    "framework": "astro@6",
    "runtime": "bun",
    "styles": "tailwindcss@4",
    "validation": "zod",
    "animation": "motion@11",
    "adapter": "@astrojs/node standalone"
  },
  "infra": {
    "server": "Oracle Cloud ARM aarch64",
    "proxy": "Caddy 2",
    "deploy": "Docker Compose",
    "db": "SQLite via bun:sqlite (tablas: characters, videos)"
  },
  "modulos": {
    "now":       { "ruta": "/src/features/now/",       "estado": "activo",   "datos": "/data/now.json" },
    "radio":     { "ruta": "/src/features/radio/",     "estado": "activo",   "datos": "stream URL en componente" },
    "gacha":     { "ruta": "/src/features/gacha/",     "estado": "activo",   "datos": "SQLite /data/database.sqlite tabla characters",
                   "api": ["/api/enka-gi", "/api/enka-hsr", "/api/enka-zzz"] },
    "video":     { "ruta": "/src/features/video/",     "estado": "activo",   "datos": "SQLite /data/database.sqlite tabla videos",
                   "api": ["/api/videos"] },
    "admin":     { "ruta": "/src/pages/admin/",        "estado": "activo",   "datos": "cookie aris_admin (HMAC-SHA256, 8h)",
                   "api": ["/api/auth/login", "/api/auth/logout"] },
    "garden":    { "ruta": "/src/features/garden/",    "estado": "pendiente","datos": "/content/garden/*.md" },
    "bookshelf": { "ruta": "/src/features/bookshelf/", "estado": "pendiente","datos": "/data/books.json" },
    "portfolio": { "ruta": "/src/features/portfolio/", "estado": "pendiente","datos": "/data/portfolio.json" },
    "blog":      { "ruta": "/src/features/blog/",      "estado": "pendiente","datos": "/content/blog/*.md" },
    "gallery":   { "ruta": "/src/features/gallery/",   "estado": "pendiente","datos": "/content/gallery/" }
  },
  "api_routes": {
    "/api/enka-gi":       "GET — personajes GI desde SQLite",
    "/api/enka-hsr":      "GET — personajes HSR desde SQLite",
    "/api/enka-zzz":      "GET — personajes ZZZ desde SQLite",
    "/api/videos":        "GET — lista de videos desde SQLite",
    "/api/auth/login":    "POST — login admin (PBKDF2 verify + cookie HMAC)",
    "/api/auth/logout":   "POST — logout (borra cookie)"
  }
}

p = ROOT / "STRUCTURE.json"
p.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")
UPDATED.append("STRUCTURE.json")
print("  ✏️  STRUCTURE.json")


# ═══════════════════════════════════════════════════════════════
#  Resumen
# ═══════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("✅ SCRIPT COMPLETADO")
print("═"*60)

print(f"\n📁 {len(CREATED)} archivos CREADOS:")
for f in CREATED:
    print(f"   + {f}")

print(f"\n✏️  {len(UPDATED)} archivos ACTUALIZADOS:")
for f in UPDATED:
    print(f"   ~ {f}")

print("""
─────────────────────────────────────────────────────────
PASOS SIGUIENTES (en orden):

  1. Inicializar la base de datos SQLite (1 sola vez):
       docker exec web bun run scripts/init-gacha-db.ts

  2. Rebuild y redeploy:
       docker compose up -d --build

  3. (Opcional) Sincronizar personajes gacha:
       docker exec web bun run scripts/sync-enka-gi.ts
       docker exec web bun run scripts/sync-enka-hsr.ts

  4. Acceder al panel admin:
       https://aris-sama.duckdns.org/admin/login
       (contraseña: la que ya tenías configurada en .env)

RUTAS NUEVAS ACTIVAS:
  /gacha          → roster de personajes (tabs: GI / HSR / ZZZ)
  /videos         → galería de videos
  /admin/login    → acceso protegido
  /admin          → panel de control
─────────────────────────────────────────────────────────
""")
