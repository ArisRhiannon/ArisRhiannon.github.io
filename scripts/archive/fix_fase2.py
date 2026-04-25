import os
from pathlib import Path

BASE = Path("/home/ubuntu/misitio")

def fix():
    # 1. Eliminar la ruta duplicada para evitar la colisión detectada por Astro
    old_api = BASE / "src/pages/api/videos.ts"
    if old_api.exists():
        old_api.unlink()
        print("✅ Archivo duplicado /api/videos.ts eliminado.")

    # 2. Corregir videos.astro (Mover la lógica al Frontmatter para evitar error de esbuild)
    videos_page = BASE / "src/pages/videos.astro"
    if videos_page.exists():
        content = """---
import Base from '../layouts/Base.astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';

let videos: any[] = [];
try {
  const db = new Database(join(process.cwd(), 'data', 'database.sqlite'), { readonly: true });
  const rawVideos = db.query('SELECT * FROM videos ORDER BY created_at DESC').all() as any[];
  videos = rawVideos.map(v => ({
    ...v,
    parsedDesc: JSON.parse(v.descriptors ?? '{}')
  }));
  db.close();
} catch {}
---
<Base title="Videos · aris-sama" description="Clips, gameplays y momentos">
  <section class="videos-page">
    <header class="page-header">
      <h1 class="page-title"><span class="page-prompt">$</span> videos</h1>
      <p class="page-sub">clips · gameplays · momentos</p>
    </header>

    {videos.length === 0 ? (
      <p class="empty-state font-mono">Sin videos todavía.</p>
    ) : (
      <div class="video-grid">
        {videos.map((v) => (
          <a href={`/v/${v.id}`} class="video-card">
            <div class="video-thumb">
              {v.thumbnail ? <img src={v.thumbnail} alt={v.title} /> : <div class="thumb-placeholder">▶</div>}
            </div>
            <div class="video-body">
              <span class="video-cat font-mono">{v.category ?? 'general'}</span>
              <h2 class="video-name">{v.title}</h2>
              <div class="desc-tags">
                {Object.entries(v.parsedDesc).slice(0, 3).map(([k, val]) => (
                  <span class="desc-tag"><strong>{k}</strong> {val}</span>
                ))}
              </div>
            </div>
          </a>
        ))}
      </div>
    )}
  </section>
</Base>

<style>
  .videos-page { padding: 2rem 0; }
  .page-header { margin-bottom: 2rem; }
  .page-title { font-family: var(--font-mono); font-size: 1.5rem; color: var(--color-ink); display: flex; gap: 0.5rem; }
  .page-prompt { color: var(--color-accent); }
  .video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1.25rem; }
  .video-card { background: var(--glass-bg); border: var(--glass-border); border-radius: 12px; overflow: hidden; text-decoration: none; color: inherit; transition: transform 0.2s; }
  .video-card:hover { transform: translateY(-4px); border-color: var(--color-accent); }
  .video-thumb { aspect-ratio: 16/9; background: rgba(168,85,247,0.06); position: relative; }
  .video-thumb img { width: 100%; height: 100%; object-fit: cover; }
  .video-body { padding: 1rem; }
  .video-cat { font-size: 0.65rem; color: var(--color-accent); text-transform: uppercase; }
  .video-name { font-size: 0.9rem; margin: 0.25rem 0; color: var(--color-ink); }
  .desc-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; }
  .desc-tag { background: rgba(168,85,247,0.08); font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; color: var(--color-muted); }
</style>"""
        videos_page.write_text(content.strip(), encoding='utf-8')
        print("✅ src/pages/videos.astro corregido.")

fix()
