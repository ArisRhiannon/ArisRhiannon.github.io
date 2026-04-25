#!/usr/bin/env python3
"""
apply_hotfix_v3b.py
1. Radio — reemplaza stream caído por uno funcional + fallback robusto
2. Hot reload — index.astro y now.astro usan readFileSync en lugar de import estático
3. Discord embed — og:description más rico + cache-busting hint
Uso: sudo HOME=/home/ubuntu python3 apply_hotfix_v3b.py
"""
import os, subprocess

BASE = "/home/ubuntu/misitio"

# ══════════════════════════════════════════════════════════════
# 1. RADIO — stream funcional + detección robusta del mp3 local
# ══════════════════════════════════════════════════════════════
radio = r"""---
// RadioPlayer.astro
import { existsSync } from 'fs';
import { join } from 'path';

const hasLocalSong = existsSync(join(process.cwd(), 'public', 'aris_song.mp3'));
const LOCAL_URL    = '/aris_song.mp3';
// Streams de respaldo — se prueban en orden hasta que uno funcione
const FALLBACK_STREAMS = [
  'https://streams.ilovemusic.de/iloveradio17.mp3',   // lo-fi hits
  'https://radio.plaza.one/mp3',                       // plaza.one
  'https://listen.moe/stream',                         // listen.moe J-pop
];
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
    <span class="radio-name" id="radio-name">{STATION_NAME}</span>
    <span class="radio-status" id="radio-status">pausado</span>
  </div>
  <input type="range" id="radio-volume" class="radio-volume"
    min="0" max="1" step="0.05" value="0.6" aria-label="Volumen" />
</div>

<script define:vars={{ LOCAL_URL, FALLBACK_STREAMS, IS_LOCAL, STATION_NAME }}>
if (!window.__radioInitialized) {
  window.__radioInitialized = true;
  let audio = null, playing = false, streamIndex = 0;

  function getEls() {
    return {
      btn:    document.getElementById('radio-toggle'),
      status: document.getElementById('radio-status'),
      name:   document.getElementById('radio-name'),
      vol:    document.getElementById('radio-volume'),
      player: document.getElementById('radio-player'),
    };
  }

  function setUI(isPlaying, statusText) {
    const { btn, status, player } = getEls();
    if (!btn) return;
    playing = isPlaying;
    btn.setAttribute('aria-pressed', String(isPlaying));
    player.classList.toggle('is-playing', isPlaying);
    if (status) {
      status.textContent = statusText ?? (isPlaying
        ? (IS_LOCAL ? '▶ reproduciendo' : '● en vivo')
        : 'pausado');
    }
  }

  function tryNextStream() {
    if (streamIndex >= FALLBACK_STREAMS.length) {
      setUI(false, 'sin señal');
      return;
    }
    const url = FALLBACK_STREAMS[streamIndex++];
    const { name } = getEls();
    if (name) name.textContent = 'lo-fi · buscando...';
    audio.src = url;
    audio.loop = false;
    audio.play().catch(() => tryNextStream());
  }

  function initAudio() {
    if (audio) return;
    audio = new Audio(IS_LOCAL ? LOCAL_URL : FALLBACK_STREAMS[streamIndex++]);
    if (IS_LOCAL) audio.loop = true;
    audio.volume = parseFloat(document.getElementById('radio-volume')?.value ?? '0.6');

    audio.addEventListener('playing', () => {
      const { name } = getEls();
      if (name && !IS_LOCAL) name.textContent = 'lo-fi · aris fm';
      setUI(true);
    });
    audio.addEventListener('pause',   () => setUI(false));
    audio.addEventListener('ended',   () => setUI(false));
    audio.addEventListener('error', () => {
      if (IS_LOCAL && audio.src.includes(LOCAL_URL)) {
        // Local falló → intentar streams
        tryNextStream();
      } else {
        tryNextStream();
      }
    });
  }

  function toggle() {
    initAudio();
    if (playing) {
      audio.pause();
    } else {
      setUI(false, 'conectando...');
      audio.play().catch(() => {
        // Autoplay bloqueado — el usuario debe hacer click
        setUI(false, 'click para activar');
      });
    }
  }

  function bind() {
    const { btn, vol } = getEls();
    if (!btn) return;
    btn.removeEventListener('click', toggle);
    btn.addEventListener('click', toggle);
    if (vol) vol.addEventListener('input', e => { if (audio) audio.volume = parseFloat(e.target.value); });
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
"""
with open(os.path.join(BASE, "src", "features", "radio", "RadioPlayer.astro"), "w") as f:
    f.write(radio)
print("✅ RadioPlayer.astro — streams de fallback robustos")

# ══════════════════════════════════════════════════════════════
# 2. HOT RELOAD — index.astro reemplaza import estático por readFileSync
# ══════════════════════════════════════════════════════════════
# Leer el archivo actual y reemplazar solo el frontmatter
index_path = os.path.join(BASE, "src", "pages", "index.astro")
with open(index_path) as f:
    index_content = f.read()

old_frontmatter = """---
import Base from '../layouts/Base.astro';
import homepage from '../../data/homepage.json';
import nowData from '../../data/now.json';

const heroBlock   = homepage.blocks.find(b => b.type === 'hero');
const nowPreview  = homepage.blocks.find(b => b.type === 'now_preview');
const radioBanner = homepage.blocks.find(b => b.type === 'radio_banner');
const nowItems    = nowPreview ? nowData.items.slice(0, nowPreview.limit ?? 3) : [];
---"""

new_frontmatter = """---
import Base from '../layouts/Base.astro';
import { readFileSync } from 'fs';
import { join } from 'path';

// readFileSync = hot reload: cada request lee el JSON actualizado del disco
const homepage = JSON.parse(readFileSync(join(process.cwd(), 'data', 'homepage.json'), 'utf-8'));
const nowData  = JSON.parse(readFileSync(join(process.cwd(), 'data', 'now.json'), 'utf-8'));

const heroBlock   = homepage.blocks.find((b: any) => b.type === 'hero');
const nowPreview  = homepage.blocks.find((b: any) => b.type === 'now_preview');
const radioBanner = homepage.blocks.find((b: any) => b.type === 'radio_banner');
const nowItems    = nowPreview ? nowData.items.slice(0, nowPreview.limit ?? 3) : [];
---"""

if old_frontmatter in index_content:
    index_content = index_content.replace(old_frontmatter, new_frontmatter)
    with open(index_path, "w") as f:
        f.write(index_content)
    print("✅ index.astro — hot reload activado")
else:
    # Reemplazar cualquier variante del import estático
    import re
    index_content = re.sub(
        r"import homepage from ['\"].*homepage\.json['\"];?\n",
        "const homepage = JSON.parse(readFileSync(join(process.cwd(), 'data', 'homepage.json'), 'utf-8'));\n",
        index_content
    )
    index_content = re.sub(
        r"import nowData from ['\"].*now\.json['\"];?\n",
        "const nowData  = JSON.parse(readFileSync(join(process.cwd(), 'data', 'now.json'), 'utf-8'));\n",
        index_content
    )
    # Añadir imports de fs si no están
    if "readFileSync" in index_content and "import { readFileSync" not in index_content:
        index_content = index_content.replace(
            "import Base from '../layouts/Base.astro';",
            "import Base from '../layouts/Base.astro';\nimport { readFileSync } from 'fs';\nimport { join } from 'path';"
        )
    # Arreglar los .find sin tipo
    index_content = index_content.replace(
        "homepage.blocks.find(b => b.type",
        "homepage.blocks.find((b: any) => b.type"
    )
    with open(index_path, "w") as f:
        f.write(index_content)
    print("✅ index.astro — hot reload activado (via regex)")

# ── now.astro ─────────────────────────────────────────────────
now_path = os.path.join(BASE, "src", "pages", "now.astro")
with open(now_path) as f:
    now_content = f.read()

now_content = now_content.replace(
    "import nowData from '../../data/now.json';",
    "import { readFileSync } from 'fs';\nimport { join } from 'path';\nconst nowData = JSON.parse(readFileSync(join(process.cwd(), 'data', 'now.json'), 'utf-8'));"
)
# También por si usa comillas dobles
now_content = now_content.replace(
    'import nowData from "../../data/now.json";',
    'import { readFileSync } from "fs";\nimport { join } from "path";\nconst nowData = JSON.parse(readFileSync(join(process.cwd(), "data", "now.json"), "utf-8"));'
)
with open(now_path, "w") as f:
    f.write(now_content)
print("✅ now.astro — hot reload activado")

# ══════════════════════════════════════════════════════════════
# 3. /v/[id].astro — Discord embed más rico
# ══════════════════════════════════════════════════════════════
vid_path = os.path.join(BASE, "src", "pages", "v", "[id].astro")
with open(vid_path) as f:
    vid_content = f.read()

# Reemplazar la lógica de description para Discord
old_desc = """// Parsear descriptores
let descriptors: Record<string, string> = {};
try { descriptors = JSON.parse(video.descriptors ?? '{}'); } catch {}
const descLines = Object.entries(descriptors).map(([k, v]) => `${k}: ${v}`).join(' · ');
const description = descLines || video.category || 'video · aris-sama';"""

new_desc = """// Parsear descriptores
let descriptors: Record<string, string> = {};
try { descriptors = JSON.parse(video.descriptors ?? '{}'); } catch {}

// og:description enriquecido para Discord
// Formato: [categoria] NombreSitio · Clave: Valor · Clave: Valor
const descParts: string[] = [];
if (video.category) descParts.push(`[${video.category}]`);
descParts.push('aris-sama.duckdns.org');
const descEntries = Object.entries(descriptors).map(([k, v]) => `${k}: ${v}`);
descEntries.forEach(e => descParts.push(e));
const description = descParts.join(' · ');

// Fecha formateada
const uploadDate = new Date(video.created_at).toLocaleDateString('es-MX', {
  day: '2-digit', month: 'short', year: 'numeric'
}) || '';"""

if old_desc in vid_content:
    vid_content = vid_content.replace(old_desc, new_desc)
    print("✅ /v/[id].astro — og:description enriquecido")
else:
    print("⚠️  /v/[id].astro — patrón no encontrado exacto, aplicando via regex")
    import re
    vid_content = re.sub(
        r"const description = descLines.*?;",
        """const description = (() => {
  const parts: string[] = [];
  if (video.category) parts.push('[' + video.category + ']');
  parts.push('aris-sama.duckdns.org');
  Object.entries(descriptors).forEach(([k,v]) => parts.push(k + ': ' + v));
  return parts.join(' · ');
})();""",
        vid_content
    )
    with open(vid_path, "w") as f:
        f.write(vid_content)

# Añadir og:site_name para más contexto en Discord
if 'og:site_name' not in vid_content:
    vid_content = vid_content.replace(
        '<meta property="og:type"',
        '<meta property="og:site_name"          content="aris-sama" />\n  <meta property="og:type"'
    )
    print("✅ og:site_name añadido")

with open(vid_path, "w") as f:
    f.write(vid_content)

# ══════════════════════════════════════════════════════════════
# 4. Rebuild
# ══════════════════════════════════════════════════════════════
print("\n🔨 Rebuilding...")
result = subprocess.run(
    ["docker", "compose", "up", "-d", "--build"],
    cwd=BASE, capture_output=True, text=True
)
print(result.stdout[-2000:] if result.stdout else "")
if result.returncode != 0:
    print("❌ Error:", result.stderr[-2000:])
else:
    print("""
✅ Todo listo.

Radio: ahora prueba 3 streams de fallback en orden si el primero falla.
Hot reload: guarda un JSON desde /admin y recarga la página — los cambios
            aparecen al instante sin rebuild.
Discord: el embed ahora muestra [categoria] · sitio · Clave: Valor.
         IMPORTANTE: Discord cachea los embeds ~30 min. Para forzar refresco:
         1. Pega el link en un canal nuevo, O
         2. Añade ?v=2 al final del link una vez, O
         3. Espera ~30 min y comparte de nuevo.
""")
