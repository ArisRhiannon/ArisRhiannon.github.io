#!/usr/bin/env python3
import os

BASE_DIR = "/home/ubuntu/misitio"
FEATURE_PATH = os.path.join(BASE_DIR, "src/features/danmaku/DanmakuVisualizer.astro")
PAGE_PATH = os.path.join(BASE_DIR, "src/pages/danmaku.astro")

# 1. El Componente con Motor de Spell Cards y UI [cite: 44, 554]
feature_content = """
---
// src/features/danmaku/DanmakuVisualizer.astro
---
<div class="w-full h-[85vh] relative flex items-center justify-center overflow-hidden bg-black rounded-2xl border border-[var(--color-border-accent)]" id="danmaku-viewer">
  <canvas id="danmaku-canvas" class="absolute inset-0 z-0"></canvas>
  
  <div class="absolute top-6 right-6 z-20 w-80 p-5 rounded-2xl border border-white/10 flex flex-col gap-4 font-mono text-white shadow-[var(--shadow-lg)]" 
       style="background: rgba(5, 5, 8, 0.85); backdrop-filter: blur(var(--glass-blur));">
    <h3 class="text-xl font-bold tracking-tighter text-[var(--color-cyan)]" style="text-shadow: var(--glow-cyan);">SPELL CARD ENGINE</h3>
    
    <label class="flex flex-col gap-1.5">
      <span class="text-[10px] uppercase text-[var(--color-muted)] tracking-widest">Seleccionar Manuscrito</span>
      <select id="pattern-selector" class="bg-black text-white border border-white/20 rounded-lg px-3 py-2 focus:outline-none focus:border-[var(--color-accent)] cursor-pointer">
        <option value="0">Saigyou Ayakashi: Ethereal Bloom</option>
        <option value="1">Hidden Seasons: Okina's Backdoor</option>
        <option value="2">Butterfly Rain: Border of Life</option>
        <option value="3">Non-Euclidean Abyss (Koishi)</option>
      </select>
    </label>

    <div id="phase-status" class="text-[10px] text-[var(--color-accent)] uppercase tracking-widest animate-pulse">
      Estado: Sincronizando...
    </div>
  </div>
</div>

<script is:inline>
  (function() {
    let canvas, ctx, animationId;
    let particles = [];
    let currentPattern = 0;
    let frame = 0;
    const MAX = 4000;

    const colors = { sakura: '#fbcfe8', cyan: '#22d3ee', violet: '#a855f7', gold: '#fbbf24' };

    class Bullet {
      constructor() { this.reset(); }
      reset() {
        this.life = 1.0;
        this.size = Math.random() * 2 + 1;
        this.color = colors.sakura;
        const angle = Math.random() * Math.PI * 2;
        
        if (currentPattern == 0) { // Saigyou Ayakashi (Etereo)
          this.x = canvas.width / 2;
          this.y = canvas.height * 0.9;
          const fa = -Math.PI/2 + (Math.random()-0.5) * 1.2;
          const spd = Math.random() * 4 + 2;
          this.vx = Math.cos(fa) * spd;
          this.vy = Math.sin(fa) * spd;
          this.decay = 0.005;
        } else if (currentPattern == 1) { // Okina (Puertas)
          this.x = Math.random() * canvas.width;
          this.y = Math.random() * canvas.height;
          this.vx = (Math.random()-0.5) * 2;
          this.vy = (Math.random()-0.5) * 2;
          this.decay = 0.01;
          this.color = colors.gold;
        } else { // Fallback / Otros
          this.x = canvas.width / 2; this.y = canvas.height / 2;
          this.vx = Math.cos(angle) * 3; this.vy = Math.sin(angle) * 3;
          this.decay = 0.008;
          this.color = colors.cyan;
        }
      }
      update() {
        this.x += this.vx; this.y += this.vy;
        if (currentPattern == 0) this.vy -= 0.02; // Crecimiento
        this.life -= this.decay;
        if (this.life <= 0) this.reset();
      }
      draw() {
        ctx.globalAlpha = this.life;
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    const init = () => {
      canvas = document.getElementById('danmaku-canvas');
      if (!canvas) return;
      ctx = canvas.getContext('2d');
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      
      const selector = document.getElementById('pattern-selector');
      selector.addEventListener('change', (e) => {
        currentPattern = parseInt(e.target.value);
        particles = [];
      });

      particles = [];
      animate();
    };

    const animate = () => {
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.globalCompositeOperation = 'lighter';

      if (particles.length < MAX) {
        for(let i=0; i<10; i++) particles.push(new Bullet());
      }
      particles.forEach(p => { p.update(); p.draw(); });
      animationId = requestAnimationFrame(animate);
    };

    document.addEventListener('astro:page-load', init);
    document.addEventListener('astro:before-swap', () => cancelAnimationFrame(animationId));
  })();
</script>
"""

page_content = """
---
import Base from '../layouts/Base.astro';
import DanmakuVisualizer from '../features/danmaku/DanmakuVisualizer.astro';
---
<Base title="Danmaku Engine | SOTA v3.0">
  <main class="max-w-6xl mx-auto p-8">
    <header class="mb-8 border-b border-white/10 pb-6">
      <h1 class="text-4xl font-display text-[var(--color-ink)] shadow-[var(--glow-sm)]">Danmaku Synesthesia</h1>
      <p class="text-[var(--color-muted)] font-mono text-xs uppercase tracking-[0.2em] mt-2">Protocolo de Visualización SOTA v3.0 // Guadalajara MX</p>
    </header>
    
    <DanmakuVisualizer />
    
    <footer class="mt-8 flex justify-between font-mono text-[10px] text-[var(--color-muted-2)]">
      <span>Render: Canvas 2D / Web APIs</span>
      <span>Status: 200 OK</span>
    </footer>
  </main>
</Base>
"""

os.makedirs(os.path.dirname(FEATURE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(PAGE_PATH), exist_ok=True)
with open(FEATURE_PATH, 'w') as f: f.write(feature_content.strip())
with open(PAGE_PATH, 'w') as f: f.write(page_content.strip())
print("Ecosistema restaurado correctamente, Señorita Aris.")
