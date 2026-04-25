#!/usr/bin/env python3
import os

# Ruta absoluta REAL en producción según el manual 
BASE_DIR = "/home/ubuntu/misitio"
FEATURE_PATH = os.path.join(BASE_DIR, "src/features/danmaku/DanmakuVisualizer.astro")
PAGE_PATH = os.path.join(BASE_DIR, "src/pages/danmaku.astro")

# Componente con Lógica Etérea y Ciclo de Vida Astro 6 [cite: 847, 850]
feature_content = """
---
// src/features/danmaku/DanmakuVisualizer.astro
---
<div class="relative w-full h-[80vh] bg-[#05050a] overflow-hidden rounded-xl border border-[var(--color-border-accent)]" id="danmaku-container">
  <canvas id="danmaku-canvas" class="absolute inset-0"></canvas>
  <div class="absolute bottom-4 left-4 z-20 font-mono text-[var(--color-cyan)] text-[10px] opacity-50 tracking-widest">
    SAIGYOU AYAKASHI // ETHEREAL FLOW v4.0
  </div>
</div>

<script is:inline>
  (function() {
    let canvas, ctx, animationId;
    let particles = [];
    const MAX = 4000;

    const init = () => {
      canvas = document.getElementById('danmaku-canvas');
      if (!canvas) return;
      ctx = canvas.getContext('2d');
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      particles = [];
      animate();
    };

    class Petal {
      constructor() { this.reset(); }
      reset() {
        this.x = canvas.width / 2;
        this.y = canvas.height * 0.85;
        const angle = -Math.PI / 2 + (Math.random() - 0.5) * 1.5;
        const force = Math.random() * 4 + 2;
        this.vx = Math.cos(angle) * force;
        this.vy = Math.sin(angle) * force;
        this.life = 1.0;
        this.size = Math.random() * 1.8 + 0.5;
        this.color = Math.random() > 0.4 ? '#fbcfe8' : '#a855f7';
      }
      update() {
        this.x += this.vx;
        this.y += this.vy;
        this.vy -= 0.03; // Crecimiento ascendente
        this.vx *= 0.98;
        this.life -= 0.006;
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

    const animate = () => {
      if (!ctx) return;
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = 'rgba(5, 5, 10, 0.15)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.globalCompositeOperation = 'lighter';

      if (particles.length < MAX) {
        for(let i=0; i<8; i++) particles.push(new Petal());
      }
      particles.forEach(p => { p.update(); p.draw(); });
      animationId = requestAnimationFrame(animate);
    };

    // Aplicación estricta de Regla A (Astro 6 Lifecycle) [cite: 852, 856]
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
<Base title="Danmaku Synesthesia">
  <main class="max-w-6xl mx-auto p-8">
    <header class="mb-12">
      <h1 class="text-4xl font-display text-[var(--color-ink)] mb-2 shadow-[var(--glow-sm)]">True Saigyou Ayakashi</h1>
      <p class="text-[var(--color-muted)] font-mono text-xs uppercase tracking-widest">Protocolo de Visualización SOTA v3.0</p>
    </header>
    
    <DanmakuVisualizer />
    
    <div class="mt-8 p-6 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg font-mono text-xs text-[var(--color-muted-2)]">
      <p>// Los vectores se generan desde el núcleo con gravedad invertida[cite: 309].</p>
      <p>// Renderizado aditivo habilitado para evitar la rigidez estructural.</p>
    </div>
  </main>
</Base>
"""

# Asegurar que existan los directorios [cite: 259, 261]
os.makedirs(os.path.dirname(FEATURE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(PAGE_PATH), exist_ok=True)

with open(FEATURE_PATH, 'w') as f: f.write(feature_content.strip())
with open(PAGE_PATH, 'w') as f: f.write(page_content.strip())

print("Módulos actualizados con éxito en /home/ubuntu/misitio, Señorita Aris.")
