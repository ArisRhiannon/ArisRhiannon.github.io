#!/bin/bash
set -e

PROJECT_DIR="/home/ubuntu/misitio"
TARGET="$PROJECT_DIR/src/features/danmaku/DanmakuVisualizer.astro"

sudo chown -R ubuntu:ubuntu "$PROJECT_DIR"
mkdir -p "$(dirname "$TARGET")"

cat << 'ASTRO' > "$TARGET"
---
---
<canvas id="danmaku"></canvas>

<script>
document.addEventListener("astro:page-load", () => {

const canvas = document.getElementById("danmaku");
if (!canvas) return;

const ctx = canvas.getContext("2d", {
  alpha: false,
  desynchronized: true,
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !raf) loop();
});

let raf, t = 0;

function resize() {
  canvas.width  = innerWidth;
  canvas.height = innerHeight;
}
resize();
const onResize = () => resize();
window.addEventListener("resize", onResize);

let CX = canvas.width*0.5, CY = canvas.height*0.5, CMAX = Math.max(canvas.width, canvas.height);
window.addEventListener("resize", () => {
  CX = canvas.width*0.5; CY = canvas.height*0.5; CMAX = Math.max(canvas.width, canvas.height);
});

// ── Helpers ───────────────────────────────────────────────────────
function timeField(x, y) {
  const dx = x - CX, dy = y - CY;
  const r = Math.sqrt(dx*dx + dy*dy);
  return t + Math.sin(r*0.02 - t*0.03)*40 + Math.cos(dx*0.01 + t*0.02)*20;
}

function warp(x, y, lt) {
  const dx = x - CX, dy = y - CY;
  const r  = Math.sqrt(dx*dx + dy*dy);
  const a  = Math.atan2(dy, dx);
  const wa = a + Math.sin(r*0.01 + lt*0.02)*0.9 + Math.cos(a*3 + lt*0.015)*0.6;
  const wr = r * (1 + Math.sin(a*2 + lt*0.02)*0.2);
  return [CX + Math.cos(wa)*wr, CY + Math.sin(wa)*wr];
}

const TWO_PI = Math.PI * 2;

// ════════════════════════════════════════════════════════════════
// CAPA 0 — Líneas orbitales de fondo (recuperadas del v5 original)
// Son curvas paramétricas que describen órbitas distorsionadas por
// campos de fase. Se dibujan en offscreen canvas cada N frames
// para no pagar su coste en cada tick. El result se blitea con
// alpha muy bajo → fondo atmosférico sin robar protagonismo.
// ════════════════════════════════════════════════════════════════
const offOrbit = document.createElement("canvas");
offOrbit.width  = canvas.width;
offOrbit.height = canvas.height;
const octx = offOrbit.getContext("2d", { alpha: true });

// Familias de órbitas: varias familias con distintos radios base,
// velocidad angular, y función de modulación de fase.
const ORBIT_FAMILIES = [
  // [radiusBase, radiusAmp, phaseSpd, angleWobble, hueOffset, lineCount]
  [CMAX*0.28, CMAX*0.07, 0.0008,  0.55, 0,   22],
  [CMAX*0.45, CMAX*0.09, 0.00055, 0.70, 40,  18],
  [CMAX*0.62, CMAX*0.10, 0.00040, 0.85, 80,  16],
  [CMAX*0.75, CMAX*0.08, 0.00030, 0.65, 140, 14],
  [CMAX*0.88, CMAX*0.06, 0.00022, 0.50, 200, 10],
];

// Precalcular seeds por línea para no recalcular cada frame
let orbitSeeds = [];
function buildOrbitSeeds() {
  orbitSeeds = [];
  for (const fam of ORBIT_FAMILIES) {
    const [,, , , hueOff, lineCount] = fam;
    for (let i = 0; i < lineCount; i++) {
      const phase0  = (i / lineCount) * TWO_PI + Math.random()*0.4;
      const phaseMod = 0.5 + Math.random()*1.5;
      const wobbleMod = 0.4 + Math.random()*0.8;
      const hue = (hueOff + i*(360/lineCount)*0.6 + Math.random()*30) % 360;
      const bright = 30 + Math.random()*35;
      const sat = 40 + Math.random()*50;
      orbitSeeds.push({ fam, phase0, phaseMod, wobbleMod, hue, bright, sat });
    }
  }
}
buildOrbitSeeds();

// Puntos luminosos a lo largo de cada línea — "glints"
// Se calculan 1 vez por rebuild y se guardan junto a t_snapshot
const GLINTS_PER_LINE = 3;
let orbitGlints = [];
let lastOrbitT = -9999;
const ORBIT_REBUILD_INTERVAL = 90; // frames

function rebuildOrbits(tt) {
  lastOrbitT = tt;
  offOrbit.width  = canvas.width;
  offOrbit.height = canvas.height;
  octx.clearRect(0, 0, offOrbit.width, offOrbit.height);

  orbitGlints = [];

  for (const seed of orbitSeeds) {
    const { fam, phase0, phaseMod, wobbleMod, hue, bright, sat } = seed;
    const [rBase, rAmp, phaseSpd, angleWobble] = fam;

    const r0   = rBase + rAmp * Math.sin(tt * phaseSpd * 0.7 + phase0 * phaseMod);
    const tilt = Math.sin(tt * phaseSpd * 1.3 + phase0) * angleWobble * wobbleMod;

    const STEPS = 200;
    octx.beginPath();
    let glintsForLine = [];

    for (let s = 0; s <= STEPS; s++) {
      const theta = (s / STEPS) * TWO_PI;
      // Modulación radial: suma de armónicos → curvas complejas no circulares
      const rm = r0
        + rAmp * 0.4 * Math.sin(theta * 2 + tt * phaseSpd * 2 + phase0)
        + rAmp * 0.25 * Math.sin(theta * 3 - tt * phaseSpd * 1.5 + phase0 * 1.3)
        + rAmp * 0.15 * Math.sin(theta * 5 + tt * phaseSpd * 0.8 + phase0 * 0.7);
      // Torsión angular: deforma la órbita elípticamente
      const tw = theta + tilt * Math.sin(theta * 1.5 + tt * phaseSpd * 0.5);
      const x = CX + Math.cos(tw) * rm;
      const y = CY + Math.sin(tw) * rm * (0.85 + 0.15 * Math.cos(theta + tilt));

      if (s === 0) octx.moveTo(x, y);
      else         octx.lineTo(x, y);

      // Marcar glints en pasos aleatorios (pero deterministas por seed)
      if (s > 0 && s < STEPS && (s % Math.floor(STEPS / GLINTS_PER_LINE)) === 0) {
        glintsForLine.push({ x, y, hue, bright: bright + 30, sat: sat + 20 });
      }
    }
    octx.closePath();
    octx.strokeStyle = `hsl(${hue|0},${sat|0}%,${bright|0}%)`;
    octx.globalAlpha = 0.12 + Math.random()*0.06;
    octx.lineWidth = 0.4 + Math.random()*0.35;
    octx.stroke();

    orbitGlints.push(...glintsForLine);
  }
}

function drawOrbits() {
  // Rebuild cada N frames
  if (t - lastOrbitT >= ORBIT_REBUILD_INTERVAL) rebuildOrbits(t);

  ctx.globalCompositeOperation = "screen";
  ctx.globalAlpha = 0.55;
  ctx.drawImage(offOrbit, 0, 0);

  // Glints: puntos brillantes que pulsan
  ctx.globalCompositeOperation = "lighter";
  for (const g of orbitGlints) {
    const pulse = 0.4 + 0.6 * Math.abs(Math.sin(t * 0.04 + g.x * 0.005));
    ctx.globalAlpha = pulse * 0.7;
    ctx.fillStyle = `hsl(${g.hue|0},${g.sat|0}%,${g.bright|0}%)`;
    const sz = 1.0 + pulse * 1.8;
    ctx.beginPath(); ctx.arc(g.x, g.y, sz, 0, TWO_PI); ctx.fill();
    // Micro halo en glint
    ctx.globalAlpha = pulse * 0.15;
    ctx.beginPath(); ctx.arc(g.x, g.y, sz * 4, 0, TWO_PI); ctx.fill();
  }
}

// ════════════════════════════════════════════════════════════════
// CAPA 1 — Bullets principales (v7, sin cambios)
// ════════════════════════════════════════════════════════════════
const N = 2400;
const bR     = new Float32Array(N);
const bAngle = new Float32Array(N);
const bSpin  = new Float32Array(N);
const bSpeed = new Float32Array(N);
const bPhase = new Float32Array(N);
const bX     = new Float32Array(N);
const bY     = new Float32Array(N);

for (let i = 0; i < N; i++) {
  bR[i]     = Math.random()*30;
  bAngle[i] = Math.random()*TWO_PI;
  bSpin[i]  = (Math.random()-0.5)*0.03;
  bSpeed[i] = 1 + Math.random()*1.5;
  bPhase[i] = Math.random()*10;
  bX[i] = CX; bY[i] = CY;
}

function resetBullet(i) {
  bR[i]     = Math.random()*30;
  bAngle[i] = Math.random()*TWO_PI;
  bSpin[i]  = (Math.random()-0.5)*0.03;
  bSpeed[i] = 1 + Math.random()*1.5;
  bPhase[i] = Math.random()*10;
}

function updateBullets() {
  for (let i = 0; i < N; i++) {
    const r = bR[i], angle = bAngle[i];
    const px = CX + Math.cos(angle)*r;
    const py = CY + Math.sin(angle)*r;
    const lt  = timeField(px, py);
    const dir = Math.sin(lt*0.01) > 0 ? 1 : -1;
    bR[i]     += bSpeed[i] * dir;
    bAngle[i] += bSpin[i]*dir + Math.sin(bR[i]*0.02+lt*0.03+bPhase[i])*0.05;
    const x2 = CX + Math.cos(bAngle[i])*bR[i];
    const y2 = CY + Math.sin(bAngle[i])*bR[i];
    const [wx, wy] = warp(x2, y2, lt);
    bX[i] = wx; bY[i] = wy;
    if (bR[i] < 0 || bR[i] > CMAX) resetBullet(i);
  }
}

function drawBullets() {
  ctx.globalCompositeOperation = "lighter";
  for (let i = 0; i < N; i++) {
    const depth = bR[i] / CMAX;
    const lt    = timeField(bX[i], bY[i]);
    const hue   = (bR[i]*0.4 + lt*2 + bPhase[i]*80) % 360;
    const sat   = 60 + Math.sin(lt*0.04+bPhase[i])*30;
    ctx.fillStyle   = `hsl(${hue|0},${sat|0}%,${(50+depth*30)|0}%)`;
    ctx.globalAlpha = 0.55 + (1-depth)*0.35;
    const sz = 0.8 + depth*3.8;
    ctx.beginPath(); ctx.arc(bX[i], bY[i], sz, 0, TWO_PI); ctx.fill();
    ctx.globalAlpha = 0.07;
    ctx.beginPath(); ctx.arc(bX[i], bY[i], sz*3.5, 0, TWO_PI); ctx.fill();
  }
}

// ════════════════════════════════════════════════════════════════
// CAPA 2 — Polvo etéreo + trails (v7, sin cambios)
// ════════════════════════════════════════════════════════════════
const N_CLUSTERS = 90;
const N_DUST     = 22;
const TRAIL_LEN  = 48;
const COLD_HUES  = [195, 215, 235, 255, 275, 205, 225, 248];

const VORTS = Array.from({length: 3}, (_, i) => ({
  phase: (i/3)*Math.PI*2,
  r:     100 + i*70,
  spd:   0.003 + i*0.0015
}));

function vortCenter(v) {
  const a = v.phase + t * v.spd;
  return [CX + Math.cos(a)*v.r, CY + Math.sin(a)*v.r];
}

function leaderField(x, y) {
  let vx = 0, vy = 0;
  for (const v of VORTS) {
    const [vox, voy] = vortCenter(v);
    const dx = x-vox, dy = y-voy;
    const r2 = dx*dx + dy*dy + 300;
    const s  = 12000 / r2;
    vx += -dy*s; vy += dx*s;
  }
  const dx = x-CX, dy = y-CY;
  const r  = Math.sqrt(dx*dx+dy*dy)+0.001;
  const a  = Math.atan2(dy,dx);
  const lt = timeField(x, y);
  const bg = Math.sin(r*0.01 + lt*0.015)*0.5 + Math.cos(a*2 + lt*0.009)*0.3;
  vx += Math.cos(a+bg)*0.7;
  vy += Math.sin(a+bg)*0.7;
  return [vx, vy];
}

class Cluster {
  constructor() { this.init(); }
  init() {
    const roll = Math.random();
    if (roll < 0.4) {
      const v = VORTS[Math.floor(Math.random()*VORTS.length)];
      const [vx,vy] = vortCenter(v);
      const a = Math.random()*TWO_PI;
      this.lx = vx + Math.cos(a)*(20+Math.random()*80);
      this.ly = vy + Math.sin(a)*(20+Math.random()*80);
    } else if (roll < 0.7) {
      const a = Math.random()*TWO_PI; const r = Math.random()*60;
      this.lx = CX+Math.cos(a)*r; this.ly = CY+Math.sin(a)*r;
    } else {
      const side = Math.floor(Math.random()*4);
      if      (side===0){ this.lx=Math.random()*canvas.width;  this.ly=-20; }
      else if (side===1){ this.lx=canvas.width+20;             this.ly=Math.random()*canvas.height; }
      else if (side===2){ this.lx=Math.random()*canvas.width;  this.ly=canvas.height+20; }
      else              { this.lx=-20;                         this.ly=Math.random()*canvas.height; }
    }
    this.vx = 0; this.vy = 0;
    this.life = 0; this.maxLife = 200 + Math.random()*300;
    this.hue = COLD_HUES[Math.floor(Math.random()*COLD_HUES.length)] + (Math.random()-0.5)*14;
    this.alpha = 0; this.ghost = Math.random() < 0.28;
    this.dt = 1; this.flipCD = 70 + Math.random()*90;
    this.history = []; this.trail = [];
    this.dust = Array.from({length: N_DUST}, () => ({
      angle: Math.random()*TWO_PI, r: 4 + Math.random()*20,
      phase: Math.random()*TWO_PI, ospd: (Math.random()-0.5)*0.035,
      drift: (Math.random()-0.5)*0.8, size: 0.6 + Math.random()*1.4,
    }));
  }
  update() {
    this.life++;
    if      (this.life < 40)              this.alpha = this.life/40;
    else if (this.life > this.maxLife-60) this.alpha = (this.maxLife-this.life)/60;
    else                                  this.alpha = 1;
    if (this.ghost) {
      this.flipCD--;
      if (this.flipCD <= 0) { this.dt = -this.dt; this.flipCD = 70 + Math.random()*90; }
    }
    if (this.ghost && this.dt < 0 && this.history.length > 1) {
      const p = this.history.pop();
      this.lx = p.x; this.ly = p.y; this.vx = p.vx; this.vy = p.vy;
    } else {
      const [fx, fy] = leaderField(this.lx, this.ly);
      this.vx = this.vx*0.85 + fx*0.15; this.vy = this.vy*0.85 + fy*0.15;
      this.history.push({x:this.lx, y:this.ly, vx:this.vx, vy:this.vy});
      if (this.history.length > 100) this.history.shift();
      this.lx += this.vx; this.ly += this.vy;
    }
    this.trail.push({x: this.lx, y: this.ly});
    if (this.trail.length > TRAIL_LEN) this.trail.shift();
    const tLocal = this.ghost && this.dt < 0 ? -t : t;
    for (const d of this.dust) {
      d.angle += d.ospd + Math.sin(tLocal*0.02+d.phase)*0.008;
      d.r = Math.max(2, d.r + Math.sin(tLocal*0.015+d.phase*2)*0.3 + d.drift*0.02);
      if (d.r > 26) d.drift = -Math.abs(d.drift);
      if (d.r < 3)  d.drift =  Math.abs(d.drift);
    }
    const m = 120;
    if (this.lx < -m || this.lx > canvas.width+m || this.ly < -m || this.ly > canvas.height+m || this.life >= this.maxLife) this.init();
  }
  draw() {
    const isRev = this.ghost && this.dt < 0;
    const hue   = isRev ? (this.hue + 145 + Math.sin(t*0.02)*12) % 360 : (this.hue + Math.sin(t*0.01)*10) % 360;
    const sat = isRev ? 95 : 72; const light = isRev ? 70 : 62;
    const n = this.trail.length;
    if (n >= 4) {
      ctx.globalCompositeOperation = "screen"; ctx.lineCap = "round"; ctx.lineJoin = "round";
      ctx.globalAlpha = this.alpha * (isRev ? 0.10 : 0.07);
      ctx.strokeStyle = `hsl(${hue|0},${sat}%,${light}%)`; ctx.lineWidth = isRev ? 0.9 : 0.6;
      ctx.beginPath();
      ctx.moveTo((this.trail[0].x+this.trail[1].x)*0.5, (this.trail[0].y+this.trail[1].y)*0.5);
      for (let i = 1; i < n-1; i++) {
        const mx = (this.trail[i].x+this.trail[i+1].x)*0.5; const my = (this.trail[i].y+this.trail[i+1].y)*0.5;
        ctx.quadraticCurveTo(this.trail[i].x, this.trail[i].y, mx, my);
      }
      ctx.stroke();
      const tail = Math.max(0, n-14);
      ctx.globalAlpha = this.alpha * (isRev ? 0.20 : 0.13); ctx.lineWidth = isRev ? 1.2 : 0.85;
      ctx.beginPath();
      ctx.moveTo((this.trail[tail].x+this.trail[tail+1].x)*0.5, (this.trail[tail].y+this.trail[tail+1].y)*0.5);
      for (let i = tail+1; i < n-1; i++) {
        const mx = (this.trail[i].x+this.trail[i+1].x)*0.5; const my = (this.trail[i].y+this.trail[i+1].y)*0.5;
        ctx.quadraticCurveTo(this.trail[i].x, this.trail[i].y, mx, my);
      }
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "screen"; ctx.fillStyle = `hsl(${hue|0},${sat}%,${light}%)`;
    for (const d of this.dust) {
      const px = this.lx + Math.cos(d.angle)*d.r; const py = this.ly + Math.sin(d.angle)*d.r;
      ctx.globalAlpha = this.alpha * (0.18 + d.size*0.08) * (isRev ? 1.35 : 1.0);
      ctx.beginPath(); ctx.arc(px, py, d.size, 0, TWO_PI); ctx.fill();
    }
    if (this.alpha > 0.3) {
      ctx.globalAlpha = this.alpha * (isRev ? 0.07 : 0.05);
      const grad = ctx.createRadialGradient(this.lx,this.ly,0, this.lx,this.ly,16);
      grad.addColorStop(0, `hsl(${hue|0},${sat}%,${light}%)`); grad.addColorStop(1, "transparent");
      ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(this.lx, this.ly, 16, 0, TWO_PI); ctx.fill();
    }
  }
}

const clusters = Array.from({length: N_CLUSTERS}, () => new Cluster());

// ════════════════════════════════════════════════════════════════
// CAPA 3 — Partículas fluidas de agua orbiting protagonistas
// Simulación SPH-lite: cada partícula tiene posición, velocidad y
// responde a:
//   - Atracción hacia los vórtices activos (los mismos de capa 2)
//   - Repulsión de vecinas próximas (evita colapso) usando grid hash
//   - Campo de vorticidad local suave → movimiento tipo agua
//   - Un poco de drag (viscosidad) → flujo laminar
// TypedArrays flat para cache friendliness.
// ════════════════════════════════════════════════════════════════
const NF = 3200; // partículas fluidas
const fX  = new Float32Array(NF);
const fY  = new Float32Array(NF);
const fVX = new Float32Array(NF);
const fVY = new Float32Array(NF);
const fPh = new Float32Array(NF); // phase individual
const fHue= new Float32Array(NF);

// Distribuir alrededor de los vórtices al inicio
for (let i = 0; i < NF; i++) {
  const v   = VORTS[i % VORTS.length];
  const a   = Math.random()*TWO_PI;
  const r   = 20 + Math.random()*180;
  const [vx,vy] = vortCenter(v);
  fX[i]  = vx + Math.cos(a)*r;
  fY[i]  = vy + Math.sin(a)*r;
  fVX[i] = (Math.random()-0.5)*0.5;
  fVY[i] = (Math.random()-0.5)*0.5;
  fPh[i] = Math.random()*TWO_PI;
  fHue[i]= 170 + Math.random()*140; // cyan → violeta
}

// Grid espacial para repulsión eficiente O(N) amortizado
const CELL = 24; // tamaño de celda px
let gridW = 0, gridH = 0;
let grid; // Map<int, int[]>

function buildGrid() {
  gridW = Math.ceil(canvas.width  / CELL) + 1;
  gridH = Math.ceil(canvas.height / CELL) + 1;
  grid = new Map();
  for (let i = 0; i < NF; i++) {
    const cx = (fX[i] / CELL)|0;
    const cy = (fY[i] / CELL)|0;
    const key = cx + cy * gridW;
    if (!grid.has(key)) grid.set(key, []);
    grid.get(key).push(i);
  }
}

const REP_R  = 18;   // radio repulsión
const REP_R2 = REP_R * REP_R;
const REP_K  = 0.35; // fuerza repulsión
const ATT_K  = 0.018; // atracción vórtice
const DRAG   = 0.92;  // viscosidad (1=sin drag)
const MAX_V  = 3.8;

function updateFluid() {
  buildGrid();

  for (let i = 0; i < NF; i++) {
    let ax = 0, ay = 0;

    // Atracción / órbita hacia vórtices
    for (const v of VORTS) {
      const [vox, voy] = vortCenter(v);
      const dx = vox - fX[i], dy = voy - fY[i];
      const r2 = dx*dx + dy*dy + 1;
      const r  = Math.sqrt(r2);
      // Componente tangencial (órbita) + radial suave (atracción)
      const tang = 0.7 + 0.3*Math.sin(fPh[i] + t*0.01);
      ax += (-dy/r)*tang * ATT_K * (400/Math.max(r, 40));
      ay += ( dx/r)*tang * ATT_K * (400/Math.max(r, 40));
      ax += (dx/r) * ATT_K * 0.15;
      ay += (dy/r) * ATT_K * 0.15;
    }

    // Campo de flujo local (vorticidad tipo Perlin-lite)
    const lt = timeField(fX[i], fY[i]);
    const flowAngle = lt * 0.04 + fPh[i] * 0.5;
    ax += Math.cos(flowAngle) * 0.06;
    ay += Math.sin(flowAngle) * 0.06;

    // Repulsión de vecinas (SPH pressure)
    const cx0 = (fX[i] / CELL)|0;
    const cy0 = (fY[i] / CELL)|0;
    for (let dcx = -1; dcx <= 1; dcx++) {
      for (let dcy = -1; dcy <= 1; dcy++) {
        const key = (cx0+dcx) + (cy0+dcy)*gridW;
        const cell = grid.get(key);
        if (!cell) continue;
        for (const j of cell) {
          if (j === i) continue;
          const dx = fX[i]-fX[j], dy = fY[i]-fY[j];
          const d2 = dx*dx+dy*dy;
          if (d2 < REP_R2 && d2 > 0.01) {
            const d = Math.sqrt(d2);
            const f = REP_K * (REP_R - d) / REP_R;
            ax += (dx/d)*f;
            ay += (dy/d)*f;
          }
        }
      }
    }

    fVX[i] = (fVX[i] + ax) * DRAG;
    fVY[i] = (fVY[i] + ay) * DRAG;

    // Clamp velocidad
    const spd = Math.sqrt(fVX[i]*fVX[i] + fVY[i]*fVY[i]);
    if (spd > MAX_V) { fVX[i] *= MAX_V/spd; fVY[i] *= MAX_V/spd; }

    fX[i] += fVX[i];
    fY[i] += fVY[i];

    // Wrap al salir de pantalla (con margen)
    const M = 80;
    if (fX[i] < -M) { fX[i] = canvas.width+M-1;  }
    if (fX[i] > canvas.width+M)  { fX[i] = -M+1; }
    if (fY[i] < -M) { fY[i] = canvas.height+M-1; }
    if (fY[i] > canvas.height+M) { fY[i] = -M+1; }
  }
}

function drawFluid() {
  ctx.globalCompositeOperation = "screen";
  for (let i = 0; i < NF; i++) {
    const spd = Math.sqrt(fVX[i]*fVX[i] + fVY[i]*fVY[i]);
    const norm = Math.min(spd / MAX_V, 1);
    const hue  = (fHue[i] + norm*60 + t*0.05) % 360;
    const sat  = 55 + norm*35;
    const lgt  = 35 + norm*30;
    const sz   = 0.5 + norm*1.2;
    ctx.globalAlpha = 0.22 + norm*0.25;
    ctx.fillStyle = `hsl(${hue|0},${sat|0}%,${lgt|0}%)`;
    ctx.beginPath(); ctx.arc(fX[i], fY[i], sz, 0, TWO_PI); ctx.fill();
    // micro halo sutil
    if (norm > 0.5) {
      ctx.globalAlpha = 0.04 + norm*0.04;
      ctx.beginPath(); ctx.arc(fX[i], fY[i], sz*3.5, 0, TWO_PI); ctx.fill();
    }
  }
}

// ════════════════════════════════════════════════════════════════
// CAPA 4 — Singularidad central: flujo → colapso → implosión → retorno
//
// Máquina de estados:
//   FLOW    (300-500 frames) — partículas fluyen hacia centro, singularidad crece
//   CHARGE  (60 frames)     — singularidad pulsa, tensión máxima
//   EXPLODE (40 frames)     — implosión → explosión, todas salen volando
//   SCATTER (80 frames)     — decelera, empieza a volver
//   RETURN  (200 frames)    — todas vuelven al flujo lento al centro
//
// Las partículas son TypedArrays. El estado de cada una incluye
// posición, velocidad y un "parámetro de pertenencia" a la singularidad.
// ════════════════════════════════════════════════════════════════
const NS = 800; // partículas de singularidad
const sX   = new Float32Array(NS);
const sY   = new Float32Array(NS);
const sVX  = new Float32Array(NS);
const sVY  = new Float32Array(NS);
const sAng = new Float32Array(NS); // ángulo de espiral individual
const sR   = new Float32Array(NS); // radio actual
const sPh  = new Float32Array(NS); // phase
const sHue = new Float32Array(NS);

// Estados de la máquina
const SG_FLOW    = 0;
const SG_CHARGE  = 1;
const SG_EXPLODE = 2;
const SG_SCATTER = 3;
const SG_RETURN  = 4;

let sgState = SG_FLOW;
let sgTimer = 0;
let sgRadius = 0;        // radio visual de la singularidad (crece en FLOW)
let sgMaxR   = 0;        // radio en el momento de CHARGE
const SG_FLOW_DUR    = 380;
const SG_CHARGE_DUR  = 70;
const SG_EXPLODE_DUR = 45;
const SG_SCATTER_DUR = 90;
const SG_RETURN_DUR  = 220;

// Inicializar en espiral alrededor del centro
for (let i = 0; i < NS; i++) {
  const a = (i / NS) * TWO_PI * 7 + Math.random()*0.3;
  const r = 20 + Math.random()*260;
  sX[i]   = CX + Math.cos(a)*r;
  sY[i]   = CY + Math.sin(a)*r;
  sVX[i]  = 0; sVY[i] = 0;
  sAng[i] = a; sR[i] = r;
  sPh[i]  = Math.random()*TWO_PI;
  sHue[i] = 240 + Math.random()*120; // azul → violeta → rosa
}

// Guardar posiciones "home" (estado flow) para interpolación en RETURN
const sHomeX = new Float32Array(NS);
const sHomeY = new Float32Array(NS);
const sExplVX = new Float32Array(NS); // velocidad de explosión
const sExplVY = new Float32Array(NS);

function updateSingularity() {
  sgTimer++;

  // Transiciones de estado
  if (sgState === SG_FLOW    && sgTimer >= SG_FLOW_DUR)    { sgState = SG_CHARGE;  sgTimer = 0; sgMaxR = sgRadius; }
  if (sgState === SG_CHARGE  && sgTimer >= SG_CHARGE_DUR)  {
    sgState = SG_EXPLODE; sgTimer = 0;
    // Guardar posiciones home + calcular vectores de explosión
    for (let i = 0; i < NS; i++) {
      sHomeX[i] = sX[i]; sHomeY[i] = sY[i];
      const dx = sX[i]-CX, dy = sY[i]-CY;
      const r  = Math.sqrt(dx*dx+dy*dy)+0.001;
      const spd = 3 + Math.random()*8;
      sExplVX[i] = (dx/r)*spd + (Math.random()-0.5)*3;
      sExplVY[i] = (dy/r)*spd + (Math.random()-0.5)*3;
    }
  }
  if (sgState === SG_EXPLODE && sgTimer >= SG_EXPLODE_DUR) { sgState = SG_SCATTER; sgTimer = 0; }
  if (sgState === SG_SCATTER && sgTimer >= SG_SCATTER_DUR) { sgState = SG_RETURN;  sgTimer = 0; }
  if (sgState === SG_RETURN  && sgTimer >= SG_RETURN_DUR)  {
    sgState = SG_FLOW; sgTimer = 0; sgRadius = 0;
    // Reinicializar posiciones en espiral
    for (let i = 0; i < NS; i++) {
      const a = (i / NS)*TWO_PI*7 + Math.random()*0.3;
      const r = 20 + Math.random()*260;
      sX[i]  = CX + Math.cos(a)*r;
      sY[i]  = CY + Math.sin(a)*r;
      sVX[i] = 0; sVY[i] = 0;
      sAng[i] = a; sR[i] = r;
    }
  }

  // Radio visual de la singularidad
  if (sgState === SG_FLOW) {
    const p = sgTimer / SG_FLOW_DUR;
    sgRadius = p * p * 55; // crece cuadráticamente
  } else if (sgState === SG_CHARGE) {
    const p = sgTimer / SG_CHARGE_DUR;
    sgRadius = sgMaxR * (1 + 0.2*Math.sin(p*Math.PI*6)); // pulso
  } else if (sgState === SG_EXPLODE) {
    sgRadius = sgMaxR * (1 - sgTimer/SG_EXPLODE_DUR);
  } else {
    sgRadius = 0;
  }

  for (let i = 0; i < NS; i++) {
    const dx = CX - sX[i], dy = CY - sY[i];
    const r  = Math.sqrt(dx*dx+dy*dy)+0.1;

    if (sgState === SG_FLOW || sgState === SG_CHARGE) {
      // Espiral hacia el centro
      // Fuerza: tangencial (espiral) + radial (atracción)
      const p = sgState === SG_CHARGE ? 1.0 : sgTimer/SG_FLOW_DUR;
      const pullStrength = 0.012 + p*p*0.055;
      const swirlStrength = 0.018 + p*0.012;
      // Normalizar
      const nx = dx/r, ny = dy/r;
      // Tangente (perpendicular al radio)
      const tx = -ny, ty = nx;
      sVX[i] += nx*pullStrength*r*0.018 + tx*swirlStrength;
      sVY[i] += ny*pullStrength*r*0.018 + ty*swirlStrength;
      // Un poco de campo etéreo
      const lt = timeField(sX[i], sY[i]);
      sVX[i] += Math.cos(lt*0.03 + sPh[i])*0.015;
      sVY[i] += Math.sin(lt*0.03 + sPh[i])*0.015;
      sVX[i] *= 0.93; sVY[i] *= 0.93;

      sX[i] += sVX[i]; sY[i] += sVY[i];

      // Si llega muy cerca del centro → reiniciar desde borde
      if (r < 4) {
        const a = Math.random()*TWO_PI;
        const nr = 80 + Math.random()*200;
        sX[i] = CX + Math.cos(a)*nr;
        sY[i] = CY + Math.sin(a)*nr;
        sVX[i] = 0; sVY[i] = 0;
      }

    } else if (sgState === SG_EXPLODE) {
      const p = sgTimer / SG_EXPLODE_DUR;
      sVX[i] = sExplVX[i] * (1-p*0.3);
      sVY[i] = sExplVY[i] * (1-p*0.3);
      sX[i] += sVX[i]; sY[i] += sVY[i];

    } else if (sgState === SG_SCATTER) {
      // Decelera
      sVX[i] *= 0.88; sVY[i] *= 0.88;
      sX[i] += sVX[i]; sY[i] += sVY[i];

    } else if (sgState === SG_RETURN) {
      // Vuelven al flujo spiral — interpola hacia posición home y re-activa flujo
      const p = sgTimer / SG_RETURN_DUR;
      // Fuerza hacia el radio de su posición natural (anillo)
      const targetR = 60 + (i/NS)*220;
      const curR = r;
      const pull = (targetR - curR) * 0.002 * p;
      sVX[i] += dx/r * pull * (-1); // hacia targetR
      sVY[i] += dy/r * pull * (-1);
      // Retomar espiral suave
      const tx = -dy/r, ty = dx/r; // tangente
      sVX[i] += tx * 0.025 * p;
      sVY[i] += ty * 0.025 * p;
      sVX[i] *= 0.92; sVY[i] *= 0.92;
      sX[i] += sVX[i]; sY[i] += sVY[i];
    }
  }
}

function drawSingularity() {
  // Glow de la singularidad en el centro
  if (sgRadius > 1) {
    const pulse = sgState === SG_CHARGE
      ? 0.6 + 0.4*Math.sin(sgTimer*0.5)
      : 1.0;
    ctx.globalCompositeOperation = "screen";

    // Halo exterior
    const grad = ctx.createRadialGradient(CX,CY,0, CX,CY,sgRadius*2.5);
    const hc = (t*0.3)%360;
    grad.addColorStop(0,   `hsla(${hc|0},80%,90%,${0.18*pulse})`);
    grad.addColorStop(0.3, `hsla(${(hc+40)|0},90%,70%,${0.10*pulse})`);
    grad.addColorStop(1,   "transparent");
    ctx.fillStyle = grad;
    ctx.globalAlpha = 1;
    ctx.beginPath(); ctx.arc(CX, CY, sgRadius*2.5, 0, TWO_PI); ctx.fill();

    // Núcleo
    const grad2 = ctx.createRadialGradient(CX,CY,0, CX,CY,sgRadius);
    grad2.addColorStop(0,   `hsla(${(hc+20)|0},100%,99%,${0.9*pulse})`);
    grad2.addColorStop(0.5, `hsla(${(hc+60)|0},95%,75%,${0.5*pulse})`);
    grad2.addColorStop(1,   "transparent");
    ctx.fillStyle = grad2;
    ctx.beginPath(); ctx.arc(CX, CY, sgRadius, 0, TWO_PI); ctx.fill();

    // En CHARGE: anillo de tensión
    if (sgState === SG_CHARGE) {
      ctx.globalAlpha = 0.3*pulse;
      ctx.strokeStyle = `hsl(${hc|0},100%,85%)`;
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(CX, CY, sgRadius*1.8, 0, TWO_PI); ctx.stroke();
    }
  }

  // Partículas
  ctx.globalCompositeOperation = "screen";
  for (let i = 0; i < NS; i++) {
    const dx = sX[i]-CX, dy = sY[i]-CY;
    const r  = Math.sqrt(dx*dx+dy*dy);
    const norm = Math.min(r / 280, 1);
    const hue  = (sHue[i] + t*0.08 + norm*50) % 360;
    const spd  = Math.sqrt(sVX[i]*sVX[i]+sVY[i]*sVY[i]);
    const spdN = Math.min(spd/6, 1);

    // Más brillantes las que van rápido (explosión) o las cercanas (flujo)
    let alpha = 0.15 + (1-norm)*0.25 + spdN*0.4;
    if (sgState === SG_CHARGE) alpha *= 1.4;
    ctx.globalAlpha = Math.min(alpha, 0.9);
    const sat = 60 + spdN*35;
    const lgt = 50 + (1-norm)*25;
    ctx.fillStyle = `hsl(${hue|0},${sat|0}%,${lgt|0}%)`;
    const sz = 0.5 + (1-norm)*0.8 + spdN*0.7;
    ctx.beginPath(); ctx.arc(sX[i], sY[i], sz, 0, TWO_PI); ctx.fill();
  }
}

// ════════════════════════════════════════════════════════════════
// LOOP PRINCIPAL
// ════════════════════════════════════════════════════════════════
function loop() {
  if (document.hidden) { raf = null; return; }
  raf = requestAnimationFrame(loop);
  t++;

  // Fade fondo
  ctx.globalCompositeOperation = "source-over";
  ctx.globalAlpha = 0.055;
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Capas en orden de profundidad
  drawOrbits();         // 0 — líneas orbitales de fondo

  updateBullets();
  drawBullets();        // 1 — bullets principales

  clusters.forEach(c => { c.update(); c.draw(); }); // 2 — polvo etéreo

  updateFluid();
  drawFluid();          // 3 — partículas fluidas de agua

  updateSingularity();
  drawSingularity();    // 4 — singularidad central
}

loop();

// ── Cleanup — patrón obligatorio Astro 6 + ClientRouter ──────────
document.addEventListener("astro:before-swap", () => {
  cancelAnimationFrame(raf);
  window.removeEventListener("resize", onResize);
}, { once: true });

});
</script>

<style>
canvas {
  position: fixed;
  inset: 0;
  background: #000;
  will-change: transform;
}
</style>
ASTRO

sudo docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d --build
echo "danmaku v8 — líneas orbitales + fluido SPH-lite + singularidad con ciclo implosión/explosión/retorno"
