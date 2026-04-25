#!/usr/bin/env python3
"""
apply_visual_nier.py
Rework visual completo inspirado en NieR: Automata — adaptado al tema Stellar Terminal
1. Transición de página: scanlines + hex text + boot sequence
2. Cursor custom: crosshair brackets + trail de partículas
3. Fondo: grid de puntos + orbs reactivos al scroll
4. Items: animación de "inicialización" al entrar al viewport
5. Hover en cards/links: glitch sutil + scan line
6. Nav: indicador de ruta activa animado
Uso: sudo HOME=/home/ubuntu python3 apply_visual_nier.py
"""
import os, subprocess

BASE = "/home/ubuntu/misitio"

# ══════════════════════════════════════════════════════════════
# Base.astro — todo el sistema visual va aquí
# ══════════════════════════════════════════════════════════════
base_astro = r"""---
import RadioPlayer from '../features/radio/RadioPlayer.astro';
import { ClientRouter } from 'astro:transitions';
export interface Props { title?: string; description?: string; }
const { title = 'aris-sama', description = 'dev · coleccionista de ideas · habitante digital' } = Astro.props;
---
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content={description} />
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500&family=JetBrains+Mono:wght@400;500&family=Playfair+Display:wght@700&display=swap" />
  <link rel="stylesheet" href="/design-tokens.css" />
  <ClientRouter />
</head>
<body>

  <!-- ── Fondo cósmico ── -->
  <div class="bg-nebula" aria-hidden="true">
    <canvas id="bg-grid" class="bg-grid-canvas"></canvas>
    <div class="nebula-orb orb-1"></div>
    <div class="nebula-orb orb-2"></div>
    <div class="nebula-orb orb-3"></div>
  </div>

  <!-- ── Overlay de transición NieR ── -->
  <div id="nier-overlay" aria-hidden="true">
    <div class="nier-scanlines"></div>
    <div class="nier-corner nier-tl"></div>
    <div class="nier-corner nier-tr"></div>
    <div class="nier-corner nier-bl"></div>
    <div class="nier-corner nier-br"></div>
    <div class="nier-hud-lines">
      <div class="nier-hline nier-hline-top"></div>
      <div class="nier-hline nier-hline-bot"></div>
    </div>
    <div class="nier-boot-text" id="nier-boot-text"></div>
    <div class="nier-progress-bar" id="nier-progress"></div>
  </div>

  <!-- ── Cursor custom ── -->
  <div id="cursor-ring" aria-hidden="true"></div>
  <div id="cursor-dot"  aria-hidden="true"></div>
  <canvas id="cursor-trail" aria-hidden="true"></canvas>

  <nav class="site-nav">
    <a href="/" class="nav-logo" aria-label="Inicio">
      <span class="nav-logo-prompt">~/</span>aris
    </a>
    <div class="nav-links">
      <a href="/garden"    class="nav-link"><span class="lb">[</span>jardín<span class="lb">]</span></a>
      <a href="/now"       class="nav-link"><span class="lb">[</span>ahora<span class="lb">]</span></a>
      <a href="/videos"    class="nav-link"><span class="lb">[</span>videos<span class="lb">]</span></a>
      <a href="/gacha"     class="nav-link"><span class="lb">[</span>gacha<span class="lb">]</span></a>
      <a href="/bookshelf" class="nav-link"><span class="lb">[</span>libros<span class="lb">]</span></a>
    </div>
  </nav>

  <main><slot /></main>

  <footer class="site-footer">
    <span class="footer-prompt">~ $</span>
    <span>astro · bun · oracle arm · guadalajara mx</span>
    <span class="footer-blink">▋</span>
  </footer>

  <RadioPlayer />
</body>
</html>

<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; color-scheme: dark; cursor: none; }

  body {
    font-family: var(--font-body);
    background: var(--color-bg);
    color: var(--color-ink);
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
    cursor: none;
  }

  /* ── Fondo ── */
  .bg-nebula {
    position: fixed; inset: 0; z-index: 0;
    pointer-events: none; overflow: hidden;
  }
  .bg-grid-canvas {
    position: absolute; inset: 0;
    width: 100%; height: 100%;
    opacity: 0.18;
  }
  .nebula-orb {
    position: absolute; border-radius: 50%;
    filter: blur(80px); opacity: 0.12;
    will-change: transform;
  }
  .orb-1 {
    width: 700px; height: 700px;
    background: radial-gradient(circle, #9333EA, transparent 70%);
    top: -200px; left: -150px;
    animation: orb-drift 22s ease-in-out infinite alternate;
  }
  .orb-2 {
    width: 500px; height: 500px;
    background: radial-gradient(circle, #22D3EE, transparent 70%);
    bottom: -100px; right: -100px; opacity: 0.07;
    animation: orb-drift 28s ease-in-out infinite alternate-reverse;
  }
  .orb-3 {
    width: 350px; height: 350px;
    background: radial-gradient(circle, #A855F7, transparent 70%);
    top: 50%; left: 55%; opacity: 0.06;
    animation: orb-drift 18s ease-in-out infinite alternate;
  }
  @keyframes orb-drift {
    from { transform: translate(0,0) scale(1); }
    to   { transform: translate(40px,25px) scale(1.1); }
  }

  /* ── NieR Overlay ── */
  #nier-overlay {
    position: fixed; inset: 0; z-index: 9999;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
  }
  #nier-overlay.active { opacity: 1; pointer-events: all; }

  .nier-scanlines {
    position: absolute; inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,0,0,0.35) 2px,
      rgba(0,0,0,0.35) 4px
    );
    animation: scanlines-move 0.08s linear infinite;
  }
  @keyframes scanlines-move {
    from { background-position: 0 0; }
    to   { background-position: 0 4px; }
  }

  /* Corners HUD */
  .nier-corner {
    position: absolute; width: 24px; height: 24px;
  }
  .nier-tl { top: 12px; left: 12px;
    border-top: 1px solid rgba(168,85,247,0.8);
    border-left: 1px solid rgba(168,85,247,0.8); }
  .nier-tr { top: 12px; right: 12px;
    border-top: 1px solid rgba(168,85,247,0.8);
    border-right: 1px solid rgba(168,85,247,0.8); }
  .nier-bl { bottom: 12px; left: 12px;
    border-bottom: 1px solid rgba(168,85,247,0.8);
    border-left: 1px solid rgba(168,85,247,0.8); }
  .nier-br { bottom: 12px; right: 12px;
    border-bottom: 1px solid rgba(168,85,247,0.8);
    border-right: 1px solid rgba(168,85,247,0.8); }

  /* Líneas horizontales de escaneo */
  .nier-hud-lines { position: absolute; inset: 0; }
  .nier-hline {
    position: absolute; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(168,85,247,0.4) 20%, rgba(168,85,247,0.4) 80%, transparent);
  }
  .nier-hline-top { top: 40px; }
  .nier-hline-bot { bottom: 40px; }

  /* Texto de boot */
  .nier-boot-text {
    position: absolute;
    bottom: 60px; left: 50%;
    transform: translateX(-50%);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: rgba(168,85,247,0.7);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    white-space: nowrap;
    text-align: center;
  }

  /* Barra de progreso */
  .nier-progress-bar {
    position: absolute; bottom: 50px; left: 50%;
    transform: translateX(-50%);
    width: 200px; height: 1px;
    background: rgba(168,85,247,0.15);
    overflow: hidden;
  }
  .nier-progress-bar::after {
    content: '';
    display: block; height: 100%;
    background: rgba(168,85,247,0.8);
    width: 0%;
    animation: progress-fill 0.45s var(--ease-out) forwards;
    animation-play-state: paused;
  }
  .nier-progress-bar.run::after { animation-play-state: running; }

  @keyframes progress-fill {
    from { width: 0%; }
    to   { width: 100%; }
  }

  /* ── Cursor ── */
  #cursor-dot {
    position: fixed; z-index: 99999;
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--color-accent);
    pointer-events: none;
    transform: translate(-50%, -50%);
    transition: transform 0.05s, background 0.2s;
    mix-blend-mode: screen;
  }
  #cursor-ring {
    position: fixed; z-index: 99998;
    width: 28px; height: 28px;
    pointer-events: none;
    transform: translate(-50%, -50%);
    transition: width 0.2s var(--ease-out),
                height 0.2s var(--ease-out),
                border-color 0.2s,
                opacity 0.3s;
  }
  #cursor-ring::before,
  #cursor-ring::after {
    content: '';
    position: absolute;
    border-color: rgba(168,85,247,0.6);
    border-style: solid;
  }
  /* bracket corners */
  #cursor-ring::before {
    top: 0; left: 0;
    width: 8px; height: 8px;
    border-width: 1px 0 0 1px;
  }
  #cursor-ring::after {
    bottom: 0; right: 0;
    width: 8px; height: 8px;
    border-width: 0 1px 1px 0;
  }
  /* Extra corners via box-shadow hack usando pseudo del wrapper */
  #cursor-ring {
    --cr: rgba(168,85,247,0.6);
  }

  #cursor-trail {
    position: fixed; inset: 0; z-index: 99997;
    pointer-events: none;
    opacity: 0.6;
  }

  /* hover state del cursor */
  body.cursor-hover #cursor-ring {
    width: 40px; height: 40px;
    --cr: rgba(168,85,247,0.9);
  }
  body.cursor-hover #cursor-dot {
    background: #fff;
    transform: translate(-50%, -50%) scale(0.5);
  }

  /* ── Nav ── */
  .site-nav {
    display: flex; align-items: center; justify-content: space-between;
    padding: var(--space-4) var(--space-6);
    border-bottom: var(--glass-border);
    position: sticky; top: 0; z-index: 10;
    background: rgba(5,5,10,0.8);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
  }
  .nav-logo {
    font-family: var(--font-mono); font-size: var(--text-base); font-weight: 500;
    color: var(--color-accent); text-decoration: none; letter-spacing: 0.02em;
    transition: text-shadow var(--duration) var(--ease-out);
    position: relative;
  }
  .nav-logo:hover { text-shadow: var(--glow-sm); }
  .nav-logo-prompt { color: var(--color-muted-2); margin-right: 2px; }

  .nav-links { display: flex; gap: var(--space-5); }
  .nav-link {
    font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.06em;
    color: var(--color-muted-2); text-decoration: none;
    transition: color var(--duration) var(--ease-out);
    position: relative;
  }
  .lb { color: var(--color-border-accent); transition: color var(--duration); }
  .nav-link:hover { color: var(--color-ink); }
  .nav-link:hover .lb { color: var(--color-accent); }
  .nav-link.active { color: var(--color-accent); }
  .nav-link.active .lb { color: var(--color-accent); }
  /* underline scan */
  .nav-link::after {
    content: '';
    position: absolute; bottom: -2px; left: 0; right: 0;
    height: 1px; background: var(--color-accent);
    transform: scaleX(0); transform-origin: left;
    transition: transform 0.25s var(--ease-out);
  }
  .nav-link.active::after,
  .nav-link:hover::after { transform: scaleX(1); }

  /* ── Main ── */
  main {
    flex: 1; max-width: 72rem; margin: 0 auto; width: 100%;
    padding: var(--space-8) var(--space-4);
    position: relative; z-index: 1;
  }

  /* ── Footer ── */
  .site-footer {
    padding: var(--space-5) var(--space-6);
    display: flex; align-items: center; gap: var(--space-3);
    font-family: var(--font-mono); font-size: var(--text-xs);
    color: var(--color-muted-2);
    border-top: var(--glass-border);
    position: relative; z-index: 1;
  }
  .footer-prompt { color: var(--color-accent); }
  .footer-blink { color: var(--color-accent); opacity: 0.5; animation: blink 1.2s step-end infinite; }
  @keyframes blink { 0%,100% { opacity: 0.5; } 50% { opacity: 0; } }

  /* ── Init animation para items ── */
  .nier-init {
    opacity: 0;
    /* no transform — el contenido no se mueve, solo aparece */
  }
  .nier-init.booted { opacity: 1; }

  @media (max-width: 640px) {
    .nav-links { gap: var(--space-3); }
    main { padding: var(--space-6) var(--space-4); }
    #cursor-dot, #cursor-ring, #cursor-trail { display: none; }
    html, body { cursor: auto; }
  }
</style>

<script>
// ══════════════════════════════════════════════════════════════
// SISTEMA VISUAL NIER · Stellar Terminal
// ══════════════════════════════════════════════════════════════

// ── Utilidades ────────────────────────────────────────────────
const HEX_CHARS = '0123456789ABCDEF';
const SYS_MSGS = [
  'INITIALIZING...', 'LOADING ASSETS...', 'SYNCING DATA...',
  'RENDERING PAGE...', 'CONNECTING...', 'REBOOTING MODULE...',
  'ACCESSING DATABASE...', 'CALIBRATING SENSORS...',
];

function randHex(len: number) {
  let s = '';
  for (let i = 0; i < len; i++) s += HEX_CHARS[Math.floor(Math.random() * 16)];
  return s;
}
function rand(a: number, b: number) { return a + Math.random() * (b - a); }

// ── 1. TRANSICIÓN NIER ────────────────────────────────────────
function runNierTransition(cb?: () => void) {
  const overlay = document.getElementById('nier-overlay');
  const bootText = document.getElementById('nier-boot-text');
  const progress = document.getElementById('nier-progress');
  if (!overlay) { cb?.(); return; }

  overlay.classList.add('active');
  if (progress) progress.classList.add('run');

  // Texto scramble
  let frame = 0;
  const msg = SYS_MSGS[Math.floor(Math.random() * SYS_MSGS.length)];
  const scramble = setInterval(() => {
    if (!bootText) return;
    if (frame < 8) {
      bootText.textContent = randHex(24);
    } else {
      const revealed = msg.slice(0, Math.floor((frame - 8) / 2));
      const rest = randHex(Math.max(0, 16 - revealed.length));
      bootText.textContent = revealed + rest;
    }
    frame++;
    if (frame > 20) {
      clearInterval(scramble);
      if (bootText) bootText.textContent = msg;
    }
  }, 22);

  setTimeout(() => {
    overlay.classList.remove('active');
    if (progress) progress.classList.remove('run');
    setTimeout(() => { cb?.(); }, 80);
  }, 480);
}

// ── 2. CURSOR ─────────────────────────────────────────────────
(function initCursor() {
  if (window.matchMedia('(max-width: 640px)').matches) return;

  const dot   = document.getElementById('cursor-dot')   as HTMLElement;
  const ring  = document.getElementById('cursor-ring')  as HTMLElement;
  const canvas = document.getElementById('cursor-trail') as HTMLCanvasElement;
  if (!dot || !ring || !canvas) return;

  const ctx = canvas.getContext('2d')!;
  let mx = -100, my = -100, rx = -100, ry = -100;

  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  // Partículas
  const particles: {x:number;y:number;vx:number;vy:number;life:number;size:number}[] = [];
  let lastX = -100, lastY = -100;

  document.addEventListener('mousemove', e => {
    mx = e.clientX; my = e.clientY;
    dot.style.left = mx + 'px';
    dot.style.top  = my + 'px';

    // Spawn partícula si hay movimiento suficiente
    const dx = mx - lastX, dy = my - lastY;
    if (dx*dx + dy*dy > 12) {
      particles.push({
        x: mx, y: my,
        vx: (Math.random()-0.5)*0.8,
        vy: (Math.random()-0.5)*0.8,
        life: 1,
        size: Math.random() * 2 + 1,
      });
      lastX = mx; lastY = my;
    }
  });

  // Hover interactivo
  document.addEventListener('mouseover', e => {
    const el = e.target as HTMLElement;
    if (el.closest('a,button,[data-hover]')) {
      document.body.classList.add('cursor-hover');
    }
  });
  document.addEventListener('mouseout', e => {
    const el = e.target as HTMLElement;
    if (el.closest('a,button,[data-hover]')) {
      document.body.classList.remove('cursor-hover');
    }
  });

  // RAF loop
  function loop() {
    // Ring sigue al cursor con lag suave
    rx += (mx - rx) * 0.12;
    ry += (my - ry) * 0.12;
    ring.style.left = rx + 'px';
    ring.style.top  = ry + 'px';

    // Trail canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x  += p.vx; p.y += p.vy;
      p.life -= 0.045;
      if (p.life <= 0) { particles.splice(i, 1); continue; }
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(168,85,247,${p.life * 0.5})`;
      ctx.fill();
    }

    requestAnimationFrame(loop);
  }
  loop();
})();

// ── 3. FONDO — grid de puntos ─────────────────────────────────
(function initGrid() {
  const canvas = document.getElementById('bg-grid') as HTMLCanvasElement;
  if (!canvas) return;
  const ctx = canvas.getContext('2d')!;
  let W = 0, H = 0;
  const SPACING = 32;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    draw();
  }

  let scrollY = 0;
  window.addEventListener('scroll', () => { scrollY = window.scrollY; }, { passive: true });

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const offsetY = (scrollY * 0.08) % SPACING;
    ctx.fillStyle = 'rgba(168,85,247,0.35)';
    for (let x = 0; x < W + SPACING; x += SPACING) {
      for (let y = -SPACING; y < H + SPACING; y += SPACING) {
        const py = y + offsetY;
        // Fade hacia los bordes
        const dx = (x / W - 0.5) * 2;
        const dy = (py / H - 0.5) * 2;
        const dist = Math.sqrt(dx*dx + dy*dy);
        const alpha = Math.max(0, 1 - dist * 1.1);
        ctx.globalAlpha = alpha * 0.4;
        ctx.beginPath();
        ctx.arc(x, py, 1, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
  }

  let rafId: number;
  function tick() { draw(); rafId = requestAnimationFrame(tick); }
  resize();
  window.addEventListener('resize', resize);
  tick();
})();

// ── 4. INIT ANIMATION — items que "bootean" al entrar ─────────
function initNierItems() {
  const targets = document.querySelectorAll<HTMLElement>(
    'article, .video-card, .now-item, .now-card, li.now-card, ' +
    '.stat, .stat-card, .module-card, .va-card, .comment-card, ' +
    '.item-card, .gacha-card, [data-nier]'
  );

  if (!targets.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target as HTMLElement;
      observer.unobserve(el);
      el.classList.add('nier-init');
      bootElement(el);
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

  targets.forEach(el => {
    el.classList.add('nier-init');
    observer.observe(el);
  });
}

function bootElement(el: HTMLElement) {
  const delay = parseFloat(el.dataset.nierDelay ?? '0');

  setTimeout(() => {
    // Flash rápido de borde
    const origBorder = el.style.outline;
    el.style.outline = '1px solid rgba(168,85,247,0.6)';
    el.style.transition = 'opacity 0.25s var(--ease-out), outline 0.15s';

    setTimeout(() => {
      el.style.outline = origBorder;
      el.classList.add('booted');
    }, 80);

  }, delay);
}

// Añadir delays escalonados a listas de items
function staggerItems() {
  document.querySelectorAll<HTMLElement>(
    '.now-list .now-item, .now-grid .now-card, .video-grid .video-card, ' +
    '.items-list .item-card, .videos-admin-list .va-card, .stat-grid .stat-card'
  ).forEach((el, i) => {
    el.dataset.nierDelay = String(i * 60);
  });
}

// ── 5. NAV ACTIVA ──────────────────────────────────────────────
function markActiveNav() {
  const path = location.pathname;
  document.querySelectorAll<HTMLElement>('.nav-link').forEach(a => {
    const href = a.getAttribute('href') ?? '';
    const isActive = href === '/' ? path === '/' : path.startsWith(href);
    a.classList.toggle('active', isActive);
  });
}

// ── 6. ORBS REACTIVOS AL SCROLL ───────────────────────────────
function initOrbScroll() {
  const orb1 = document.querySelector<HTMLElement>('.orb-1');
  const orb2 = document.querySelector<HTMLElement>('.orb-2');
  if (!orb1 || !orb2) return;
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const s = window.scrollY;
      const factor = Math.min(s / window.innerHeight, 1);
      orb1.style.transform = `translate(${factor * 30}px, ${factor * 20}px) scale(${1 + factor * 0.1})`;
      orb2.style.transform = `translate(${-factor * 20}px, ${-factor * 15}px) scale(${1 + factor * 0.08})`;
      ticking = false;
    });
  }, { passive: true });
}

// ── HOOKS DE ASTRO ─────────────────────────────────────────────
function onPageLoad() {
  markActiveNav();
  staggerItems();
  initNierItems();
}

// Transición entre páginas con ClientRouter
document.addEventListener('astro:before-preparation', () => {
  runNierTransition();
});

document.addEventListener('astro:page-load', onPageLoad);

// Primera carga — boot suave
document.addEventListener('DOMContentLoaded', () => {
  initOrbScroll();
  onPageLoad();
  // Boot de primera carga
  const overlay = document.getElementById('nier-overlay');
  const bootText = document.getElementById('nier-boot-text');
  const progress = document.getElementById('nier-progress');
  if (!overlay) return;

  overlay.classList.add('active');
  if (progress) progress.classList.add('run');
  if (bootText) {
    let f = 0;
    const msg = 'SYSTEM ONLINE';
    const t = setInterval(() => {
      if (f < 6) { bootText.textContent = randHex(20); }
      else {
        const r = msg.slice(0, Math.floor((f-6)/1.5));
        bootText.textContent = r + randHex(Math.max(0, 14 - r.length));
      }
      f++;
      if (f > 18) { clearInterval(t); bootText.textContent = msg; }
    }, 25);
  }
  setTimeout(() => {
    overlay.classList.remove('active');
    if (progress) progress.classList.remove('run');
  }, 520);
});
</script>
"""

os.makedirs(os.path.join(BASE, "src", "layouts"), exist_ok=True)
with open(os.path.join(BASE, "src", "layouts", "Base.astro"), "w") as f:
    f.write(base_astro)
print("✅ Base.astro — sistema visual NieR completo")

# ══════════════════════════════════════════════════════════════
# design-tokens.css — añadir tokens para hover glitch
# ══════════════════════════════════════════════════════════════
tokens_addition = """
/* ── Efectos NieR / interactivos ── */
:root {
  --nier-scan-color: rgba(168,85,247,0.15);
  --nier-boot-duration: 0.25s;
}

/* Hover glitch sutil en cards */
.video-card,
.now-item,
.now-card,
.va-card,
.stat-card,
.module-card,
.comment-card {
  transition: border-color 0.2s var(--ease-out),
              transform 0.2s var(--ease-out),
              box-shadow 0.2s var(--ease-out);
  position: relative;
  overflow: hidden;
}

/* Scan line que pasa al hover */
.video-card::after,
.now-item::after,
.now-card::after,
.va-card::after,
.stat-card::after {
  content: '';
  position: absolute;
  left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(168,85,247,0.5), transparent);
  top: -1px;
  transform: translateY(0);
  transition: transform 0s;
  opacity: 0;
  pointer-events: none;
}

.video-card:hover::after,
.now-item:hover::after,
.now-card:hover::after,
.va-card:hover::after,
.stat-card:hover::after {
  opacity: 1;
  transform: translateY(200%);
  transition: transform 0.4s linear, opacity 0s;
}

.video-card:hover,
.now-item:hover,
.now-card:hover {
  border-color: rgba(168,85,247,0.35) !important;
  box-shadow: 0 0 20px rgba(168,85,247,0.08), inset 0 0 20px rgba(168,85,247,0.03);
}

/* Boot animation */
.nier-init {
  opacity: 0;
  transition: opacity 0.25s var(--ease-out);
}
.nier-init.booted {
  opacity: 1;
}
"""

tokens_path = os.path.join(BASE, "public", "design-tokens.css")
with open(tokens_path) as f:
    tokens = f.read()

if "nier-scan-color" not in tokens:
    with open(tokens_path, "a") as f:
        f.write(tokens_addition)
    print("✅ design-tokens.css — efectos hover y boot añadidos")
else:
    print("✅ design-tokens.css — ya tiene los tokens NieR")

# ══════════════════════════════════════════════════════════════
# Rebuild
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
✅ Rework visual completo:

  Transiciones  → overlay NieR con scanlines + texto hex scramble + barra de progreso
                  en cada cambio de página y en la carga inicial
  Cursor        → crosshair bracket + dot + trail de partículas violeta
                  (se oculta en móvil automáticamente)
  Fondo         → grid de puntos que hace parallax con el scroll + orbs reactivos
  Items         → aparecen con flash de borde violeta al entrar al viewport (escalonado)
  Hover         → scan line que barre las cards al pasar el cursor
  Nav           → link activo marcado con underline animado
  Footer        → cursor parpadeante añadido
""")
