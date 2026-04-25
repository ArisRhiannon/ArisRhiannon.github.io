#!/usr/bin/env python3
import os

content = """
---
// src/features/danmaku/DanmakuVisualizer.astro
---
<div class="w-full h-screen relative flex items-center justify-center overflow-hidden bg-black" id="danmaku-viewer">
  <canvas id="danmaku-canvas" class="absolute inset-0 z-0 pointer-events-none"></canvas>
  <div class="absolute inset-0 z-10 pointer-events-none" style="background: radial-gradient(circle at center, transparent 0%, #000000 100%); opacity: 0.85;"></div>

  <div class="absolute top-6 right-6 z-20 w-80 p-5 rounded-2xl border border-[var(--color-border-accent)] flex flex-col gap-4 font-mono text-white" 
       style="background: rgba(5, 5, 10, 0.85); backdrop-filter: blur(16px); box-shadow: var(--shadow-lg);">
    <h3 class="text-xl font-bold tracking-tighter text-[var(--color-cyan)]" style="text-shadow: var(--glow-cyan);">SAIGYOU AYAKASHI v3.2</h3>
    
    <div class="flex flex-col gap-1">
      <span class="text-[10px] uppercase text-[var(--color-muted)] tracking-widest">Estado del Sello</span>
      <div id="phase-indicator" class="text-[var(--color-accent)] font-bold text-sm">Inicializando...</div>
    </div>

    <div id="particle-count" class="text-[10px] text-[var(--color-muted-2)]">Partículas: 0</div>
  </div>
</div>

<script is:inline>
  let canvas, ctx, animationId;
  let particles = [];
  let frame = 0;
  const MAX_PARTICLES = 5000;
  
  // Regla A: Ciclo de vida para Astro 6 + ClientRouter
  const init = () => {
    canvas = document.getElementById('danmaku-canvas');
    if (!canvas) return; // Guard
    ctx = canvas.getContext('2d');
    
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    
    resize();
    window.addEventListener('resize', resize);
    
    particles = [];
    frame = 0;
    animate();
  };

  class Petal {
    constructor() {
      this.reset();
    }
    reset() {
      this.x = window.innerWidth / 2;
      this.y = window.innerHeight / 2;
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 2 + 1;
      this.vx = Math.cos(angle) * speed;
      this.vy = Math.sin(angle) * speed;
      this.life = 1.0;
      this.decay = Math.random() * 0.01 + 0.005;
      this.color = Math.random() > 0.5 ? '#fbcfe8' : '#a855f7'; // Sakura / Violeta
      this.size = Math.random() * 2 + 1;
    }
    update() {
      // Movimiento fluido hacia arriba (formando el árbol etéreo)
      this.x += this.vx;
      this.y += this.vy;
      this.vy -= 0.05; // Gravedad invertida para el "crecimiento"
      this.vx *= 0.99;
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

  const animate = () => {
    if (!ctx) return;
    
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = 'rgba(0, 0, 0, 0.15)'; // Trail fluido
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.globalCompositeOperation = 'lighter'; // Efecto de brillo acumulativo

    if (particles.length < MAX_PARTICLES) {
      for(let i=0; i<10; i++) particles.push(new Petal());
    }

    particles.forEach(p => {
      p.update();
      p.draw();
    });

    frame++;
    if (frame % 30 === 0) {
        document.getElementById('particle-count').innerText = `Partículas: ${particles.length}`;
        const phases = ["Invocación", "Crecimiento Etéreo", "Florecimiento", "Sello Final"];
        document.getElementById('phase-indicator').innerText = phases[Math.floor(frame/600) % 4];
    }

    animationId = requestAnimationFrame(animate);
  };

  // Gestión de eventos según Regla A del manual SOTA
  document.addEventListener('astro:page-load', init);
  document.addEventListener('astro:before-swap', () => {
    cancelAnimationFrame(animationId);
  });
</script>
"""

path = os.path.expanduser("~/misitio/src/features/danmaku/DanmakuVisualizer.astro")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w') as f:
    f.write(content.strip())
print(f"Módulo Danmaku SOTA v3.2 desplegado en {path}")
