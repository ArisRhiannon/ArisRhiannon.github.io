#!/bin/bash
set -e

PROJECT_DIR="/home/ubuntu/misitio"

sudo chown -R ubuntu:ubuntu "$PROJECT_DIR"

# ── 1. Instalar yt-dlp en el contenedor (via Dockerfile) ──────────
# Añadimos yt-dlp al Dockerfile si no está ya
DOCKERFILE="$PROJECT_DIR/Dockerfile"

# Patch: añadir instalación de yt-dlp en la stage base
python3 - << 'PYEOF'
import re, sys

path = "/home/ubuntu/misitio/Dockerfile"
with open(path, "r") as f:
    content = f.read()

# Si ya tiene yt-dlp, no tocar
if "yt-dlp" in content:
    print("yt-dlp ya está en Dockerfile, sin cambios")
    sys.exit(0)

# Buscar la línea de apt-get con ffmpeg y añadir yt-dlp + python3 (yt-dlp lo necesita)
old = "RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg"
new = "RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg python3 python3-pip && pip3 install --break-system-packages yt-dlp"

if old in content:
    content = content.replace(old, new, 1)  # solo el primer match (stage base)
    with open(path, "w") as f:
        f.write(content)
    print("Dockerfile actualizado con yt-dlp")
else:
    print("WARN: patrón no encontrado, revisar Dockerfile manualmente")
    sys.exit(1)
PYEOF

# ── 2. Endpoint API: /src/pages/api/audio-stream.ts ───────────────
mkdir -p "$PROJECT_DIR/src/pages/api"

cat << 'TSEOF' > "$PROJECT_DIR/src/pages/api/audio-stream.ts"
import type { APIRoute } from "astro";
import { spawn } from "child_process";

// Cache de URLs directas para no llamar a yt-dlp en cada request
// TTL 4 horas (las URLs de YouTube expiran, pero duran varias horas)
const urlCache = new Map<string, { url: string; ts: number }>();
const CACHE_TTL = 4 * 60 * 60 * 1000;

async function getDirectAudioUrl(ytUrl: string): Promise<string> {
  const cached = urlCache.get(ytUrl);
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return cached.url;
  }

  return new Promise((resolve, reject) => {
    // -f bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio
    // -g = solo imprimir la URL, sin descargar
    // --no-playlist = solo el video, no la playlist completa
    const proc = spawn("yt-dlp", [
      "-f", "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio",
      "-g",
      "--no-playlist",
      "--no-warnings",
      ytUrl,
    ]);

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d: Buffer) => (stdout += d.toString()));
    proc.stderr.on("data", (d: Buffer) => (stderr += d.toString()));

    proc.on("close", (code: number) => {
      if (code !== 0) {
        reject(new Error(`yt-dlp failed (${code}): ${stderr.trim()}`));
        return;
      }
      const url = stdout.trim().split("\n")[0];
      if (!url || !url.startsWith("http")) {
        reject(new Error("yt-dlp returned no valid URL"));
        return;
      }
      urlCache.set(ytUrl, { url, ts: Date.now() });
      resolve(url);
    });
  });
}

export const GET: APIRoute = async ({ url, request }) => {
  const ytUrl = url.searchParams.get("url");

  // Endpoint de resolución: solo devuelve la URL directa (el cliente hace el proxy)
  // Esto evita que el servidor descargue el stream completo
  if (url.searchParams.get("resolve") === "1") {
    if (!ytUrl) {
      return new Response(JSON.stringify({ error: "Missing url param" }), {
        status: 400,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }

    // Sanitizar: solo permitir URLs de YouTube
    const allowed = /^https?:\/\/(www\.)?(youtube\.com\/watch|youtu\.be\/)/;
    if (!allowed.test(ytUrl)) {
      return new Response(JSON.stringify({ error: "Solo se permiten URLs de YouTube" }), {
        status: 400,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }

    try {
      const directUrl = await getDirectAudioUrl(ytUrl);
      return new Response(JSON.stringify({ url: directUrl }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store",
        },
      });
    } catch (err: any) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }
  }

  // Endpoint de proxy: stream del audio al browser
  // Así el browser recibe audio del mismo origen → createMediaElementSource funciona
  if (!ytUrl) {
    return new Response(JSON.stringify({ error: "Missing url param" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const allowed = /^https?:\/\/(www\.)?(youtube\.com\/watch|youtu\.be\/)/;
  if (!allowed.test(ytUrl)) {
    return new Response("Forbidden", { status: 403 });
  }

  try {
    const directUrl = await getDirectAudioUrl(ytUrl);

    // Leer range header si existe (para seeking)
    const rangeHeader = request.headers.get("range");

    const upstreamHeaders: Record<string, string> = {
      "User-Agent": "Mozilla/5.0 (compatible; audio-proxy/1.0)",
    };
    if (rangeHeader) upstreamHeaders["Range"] = rangeHeader;

    const upstream = await fetch(directUrl, { headers: upstreamHeaders });

    const headers: Record<string, string> = {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    };

    const ct = upstream.headers.get("content-type");
    if (ct) headers["Content-Type"] = ct;
    const cl = upstream.headers.get("content-length");
    if (cl) headers["Content-Length"] = cl;
    const cr = upstream.headers.get("content-range");
    if (cr) headers["Content-Range"] = cr;
    headers["Accept-Ranges"] = "bytes";

    return new Response(upstream.body, {
      status: upstream.status,
      headers,
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};
TSEOF

echo "✓ /api/audio-stream.ts creado"

# ── 3. DanmakuVisualizer.astro — v8 + synthesia ───────────────────
TARGET="$PROJECT_DIR/src/features/danmaku/DanmakuVisualizer.astro"
mkdir -p "$(dirname "$TARGET")"

cat << 'ASTRO' > "$TARGET"
---
---
<canvas id="danmaku"></canvas>

<!-- UI de Synthesia: input URL + estado -->
<div id="synth-ui">
  <input id="synth-input" type="text" placeholder="https://youtube.com/watch?v=..." spellcheck="false" autocomplete="off" />
  <button id="synth-btn">▶</button>
  <span id="synth-status"></span>
  <audio id="synth-audio" crossorigin="anonymous" preload="none"></audio>
</div>

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

const TWO_PI = Math.PI * 2;

// ════════════════════════════════════════════════════════════════
// SYNTHESIA — Web Audio API analyser
// Exporta 4 valores normalizados [0..1] que el danmaku consume:
//   audio.bass   — graves (20-250 Hz)  → afecta speed/warp bullets
//   audio.mid    — medios (250-2kHz)   → afecta spin clusters
//   audio.treble — agudos (2k-20kHz)   → afecta tamaño partículas
//   audio.energy — energía total       → afecta fade del fondo
// Sin música todos valen 0 y el danmaku funciona exactamente igual
// ════════════════════════════════════════════════════════════════
const audio = { bass: 0, mid: 0, treble: 0, energy: 0 };
let analyser = null;
let freqData = null;

// Smoothing: los valores no saltan abruptamente
const audioSmooth = { bass: 0, mid: 0, treble: 0, energy: 0 };
const SMOOTH = 0.15; // lerp factor

function updateAudio() {
  if (!analyser || !freqData) {
    // Sin audio: decay suave hacia 0
    audioSmooth.bass   *= 0.92;
    audioSmooth.mid    *= 0.92;
    audioSmooth.treble *= 0.92;
    audioSmooth.energy *= 0.92;
    audio.bass   = audioSmooth.bass;
    audio.mid    = audioSmooth.mid;
    audio.treble = audioSmooth.treble;
    audio.energy = audioSmooth.energy;
    return;
  }

  analyser.getByteFrequencyData(freqData);

  const len = freqData.length;
  // Mapeo de bins a Hz: sampleRate/2 / len Hz por bin
  // A 44100Hz con 2048 FFT: ~21.5 Hz/bin
  // Bass: bins 1-11 (~20-250Hz)
  // Mid:  bins 12-93 (~250-2kHz)
  // Treble: bins 94+ (~2kHz+)
  const bassEnd   = Math.floor(len * 0.06);
  const midEnd    = Math.floor(len * 0.45);

  let bassSum = 0, midSum = 0, trebSum = 0;
  for (let i = 1; i < bassEnd; i++)  bassSum += freqData[i];
  for (let i = bassEnd; i < midEnd; i++) midSum += freqData[i];
  for (let i = midEnd; i < len; i++) trebSum += freqData[i];

  const bassN   = bassSum  / (bassEnd * 255);
  const midN    = midSum   / ((midEnd - bassEnd) * 255);
  const trebN   = trebSum  / ((len - midEnd) * 255);
  const energyN = (bassSum + midSum + trebSum) / (len * 255);

  // Lerp suave
  audioSmooth.bass   += (bassN   - audioSmooth.bass)   * SMOOTH;
  audioSmooth.mid    += (midN    - audioSmooth.mid)    * SMOOTH;
  audioSmooth.treble += (trebN   - audioSmooth.treble) * SMOOTH;
  audioSmooth.energy += (energyN - audioSmooth.energy) * SMOOTH;

  audio.bass   = audioSmooth.bass;
  audio.mid    = audioSmooth.mid;
  audio.treble = audioSmooth.treble;
  audio.energy = audioSmooth.energy;
}

// ── Setup del proxy de audio ──────────────────────────────────────
const audioEl = document.getElementById("synth-audio");
const synthInput = document.getElementById("synth-input");
const synthBtn   = document.getElementById("synth-btn");
const synthStatus = document.getElementById("synth-status");

let audioCtx = null;
let sourceNode = null;
let isLoading = false;

async function initAudioChain() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === "suspended") await audioCtx.resume();

  if (!sourceNode) {
    sourceNode = audioCtx.createMediaElementSource(audioEl);
    analyser   = audioCtx.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.8;
    freqData   = new Uint8Array(analyser.frequencyBinCount);
    sourceNode.connect(analyser);
    analyser.connect(audioCtx.destination); // para que se escuche
  }
}

async function loadYouTube(ytUrl) {
  if (isLoading) return;
  isLoading = true;
  synthBtn.textContent = "…";
  synthStatus.textContent = "resolviendo...";
  synthStatus.style.color = "#aaa";

  try {
    const res  = await fetch(`/api/audio-stream?resolve=1&url=${encodeURIComponent(ytUrl)}`);
    const data = await res.json();

    if (data.error) {
      synthStatus.textContent = "✗ " + data.error;
      synthStatus.style.color = "#f66";
      synthBtn.textContent = "▶";
      isLoading = false;
      return;
    }

    // Usar el proxy para que sea same-origin
    const proxyUrl = `/api/audio-stream?url=${encodeURIComponent(ytUrl)}`;
    audioEl.src = proxyUrl;
    audioEl.load();

    await initAudioChain();

    synthStatus.textContent = "cargando...";

    await new Promise((resolve, reject) => {
      audioEl.addEventListener("canplay", resolve, { once: true });
      audioEl.addEventListener("error",   reject,  { once: true });
    });

    await audioEl.play();
    synthBtn.textContent = "■";
    synthStatus.textContent = "♪ reproduciendo";
    synthStatus.style.color = "#a855f7";

  } catch (err) {
    synthStatus.textContent = "✗ error: " + (err.message || err);
    synthStatus.style.color = "#f66";
    synthBtn.textContent = "▶";
  }
  isLoading = false;
}

synthBtn.addEventListener("click", async () => {
  if (synthBtn.textContent === "■") {
    // Pausar
    audioEl.pause();
    synthBtn.textContent = "▶";
    synthStatus.textContent = "pausado";
    synthStatus.style.color = "#aaa";
    return;
  }
  const url = synthInput.value.trim();
  if (!url) return;
  await loadYouTube(url);
});

synthInput.addEventListener("keydown", async (e) => {
  if (e.key === "Enter") synthBtn.click();
});

audioEl.addEventListener("ended", () => {
  synthBtn.textContent = "▶";
  synthStatus.textContent = "terminó";
  synthStatus.style.color = "#aaa";
});

// ── Helpers ───────────────────────────────────────────────────────
function timeField(x, y) {
  const dx = x - CX, dy = y - CY;
  const r = Math.sqrt(dx*dx + dy*dy);
  // Bass modula la frecuencia del campo temporal → pulsos rítmicos
  const bassBoost = 1 + audio.bass * 1.8;
  return t + Math.sin(r*0.02*bassBoost - t*0.03)*40 + Math.cos(dx*0.01 + t*0.02)*20;
}

function warp(x, y, lt) {
  const dx = x - CX, dy = y - CY;
  const r  = Math.sqrt(dx*dx + dy*dy);
  const a  = Math.atan2(dy, dx);
  // Bass amplifica el warp → más distorsión en los graves
  const warpAmp = 0.9 + audio.bass * 1.2;
  const wa = a + Math.sin(r*0.01 + lt*0.02)*warpAmp + Math.cos(a*3 + lt*0.015)*0.6;
  const wr = r * (1 + Math.sin(a*2 + lt*0.02)*0.2);
  return [CX + Math.cos(wa)*wr, CY + Math.sin(wa)*wr];
}

// ════════════════════════════════════════════════════════════════
// CAPA 1 — Bullets (v8 original)
// Synthesia: bass → speed, treble → tamaño
// ════════════════════════════════════════════════════════════════
const N = 1600;
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
  // Bass acelera las balas (máximo 2x)
  const speedMult = 1 + audio.bass * 1.0;
  for (let i = 0; i < N; i++) {
    const r = bR[i], angle = bAngle[i];
    const px = CX + Math.cos(angle)*r;
    const py = CY + Math.sin(angle)*r;
    const lt  = timeField(px, py);
    const dir = Math.sin(lt*0.01) > 0 ? 1 : -1;
    bR[i]     += bSpeed[i] * dir * speedMult;
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
  // Treble aumenta el tamaño de las partículas
  const sizeBoost = 1 + audio.treble * 1.5;
  for (let i = 0; i < N; i++) {
    const depth = bR[i] / CMAX;
    const lt    = timeField(bX[i], bY[i]);
    const hue   = (bR[i]*0.4 + lt*2 + bPhase[i]*80) % 360;
    const sat   = 60 + Math.sin(lt*0.04+bPhase[i])*30;
    ctx.fillStyle   = `hsl(${hue|0},${sat|0}%,${(50+depth*30)|0}%)`;
    ctx.globalAlpha = 0.55 + (1-depth)*0.35;
    const sz = (0.8 + depth*3.8) * sizeBoost;
    ctx.beginPath(); ctx.arc(bX[i], bY[i], sz, 0, TWO_PI); ctx.fill();
    ctx.globalAlpha = 0.07;
    ctx.beginPath(); ctx.arc(bX[i], bY[i], sz*3.5, 0, TWO_PI); ctx.fill();
  }
}

// ════════════════════════════════════════════════════════════════
// CAPA 2 — Polvo etéreo + clusters (v8 original)
// Synthesia: mid → velocidad de flip de ghosts, spin de dust
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
  // Mid amplifica el campo vectorial → clusters más activos en medios
  const midBoost = 1 + audio.mid * 0.8;
  vx += Math.cos(a+bg)*0.7*midBoost;
  vy += Math.sin(a+bg)*0.7*midBoost;
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
      if      (side===0){ this.lx=Math.random()*canvas.width; this.ly=-20; }
      else if (side===1){ this.lx=canvas.width+20; this.ly=Math.random()*canvas.height; }
      else if (side===2){ this.lx=Math.random()*canvas.width; this.ly=canvas.height+20; }
      else              { this.lx=-20; this.ly=Math.random()*canvas.height; }
    }
    this.vx=0; this.vy=0; this.life=0; this.maxLife=200+Math.random()*300;
    this.hue=COLD_HUES[Math.floor(Math.random()*COLD_HUES.length)]+(Math.random()-0.5)*14;
    this.alpha=0; this.ghost=Math.random()<0.28; this.dt=1;
    this.flipCD=70+Math.random()*90; this.history=[]; this.trail=[];
    this.dust=Array.from({length:N_DUST},()=>({
      angle:Math.random()*TWO_PI, r:4+Math.random()*20,
      phase:Math.random()*TWO_PI, ospd:(Math.random()-0.5)*0.035,
      drift:(Math.random()-0.5)*0.8, size:0.6+Math.random()*1.4,
    }));
  }
  update() {
    this.life++;
    if      (this.life<40)              this.alpha=this.life/40;
    else if (this.life>this.maxLife-60) this.alpha=(this.maxLife-this.life)/60;
    else                                this.alpha=1;
    if (this.ghost) {
      this.flipCD--;
      if (this.flipCD<=0) {
        this.dt=-this.dt;
        // Mid reduce el cooldown de flip → más caos rítmico
        this.flipCD=(70+Math.random()*90) * (1 - audio.mid * 0.5);
      }
    }
    if (this.ghost&&this.dt<0&&this.history.length>1) {
      const p=this.history.pop(); this.lx=p.x; this.ly=p.y; this.vx=p.vx; this.vy=p.vy;
    } else {
      const [fx,fy]=leaderField(this.lx,this.ly);
      this.vx=this.vx*0.85+fx*0.15; this.vy=this.vy*0.85+fy*0.15;
      this.history.push({x:this.lx,y:this.ly,vx:this.vx,vy:this.vy});
      if (this.history.length>100) this.history.shift();
      this.lx+=this.vx; this.ly+=this.vy;
    }
    this.trail.push({x:this.lx,y:this.ly});
    if (this.trail.length>TRAIL_LEN) this.trail.shift();
    const tLocal=this.ghost&&this.dt<0?-t:t;
    for (const d of this.dust) {
      // Treble acelera la rotación del polvo
      d.angle += d.ospd*(1+audio.treble*1.5) + Math.sin(tLocal*0.02+d.phase)*0.008;
      d.r=Math.max(2,d.r+Math.sin(tLocal*0.015+d.phase*2)*0.3+d.drift*0.02);
      if (d.r>26) d.drift=-Math.abs(d.drift);
      if (d.r<3)  d.drift= Math.abs(d.drift);
    }
    const m=120;
    if (this.lx<-m||this.lx>canvas.width+m||this.ly<-m||this.ly>canvas.height+m||this.life>=this.maxLife) this.init();
  }
  draw() {
    const isRev=this.ghost&&this.dt<0;
    const hue=isRev?(this.hue+145+Math.sin(t*0.02)*12)%360:(this.hue+Math.sin(t*0.01)*10)%360;
    const sat=isRev?95:72; const light=isRev?70:62;
    const n=this.trail.length;
    if (n>=4) {
      ctx.globalCompositeOperation="screen"; ctx.lineCap="round"; ctx.lineJoin="round";
      ctx.globalAlpha=this.alpha*(isRev?0.10:0.07);
      ctx.strokeStyle=`hsl(${hue|0},${sat}%,${light}%)`; ctx.lineWidth=isRev?0.9:0.6;
      ctx.beginPath();
      ctx.moveTo((this.trail[0].x+this.trail[1].x)*0.5,(this.trail[0].y+this.trail[1].y)*0.5);
      for (let i=1;i<n-1;i++) {
        const mx=(this.trail[i].x+this.trail[i+1].x)*0.5;
        const my=(this.trail[i].y+this.trail[i+1].y)*0.5;
        ctx.quadraticCurveTo(this.trail[i].x,this.trail[i].y,mx,my);
      }
      ctx.stroke();
      const tail=Math.max(0,n-14);
      ctx.globalAlpha=this.alpha*(isRev?0.20:0.13); ctx.lineWidth=isRev?1.2:0.85;
      ctx.beginPath();
      ctx.moveTo((this.trail[tail].x+this.trail[tail+1].x)*0.5,(this.trail[tail].y+this.trail[tail+1].y)*0.5);
      for (let i=tail+1;i<n-1;i++) {
        const mx=(this.trail[i].x+this.trail[i+1].x)*0.5;
        const my=(this.trail[i].y+this.trail[i+1].y)*0.5;
        ctx.quadraticCurveTo(this.trail[i].x,this.trail[i].y,mx,my);
      }
      ctx.stroke();
    }
    ctx.globalCompositeOperation="screen";
    ctx.fillStyle=`hsl(${hue|0},${sat}%,${light}%)`;
    for (const d of this.dust) {
      const px=this.lx+Math.cos(d.angle)*d.r;
      const py=this.ly+Math.sin(d.angle)*d.r;
      ctx.globalAlpha=this.alpha*(0.18+d.size*0.08)*(isRev?1.35:1.0);
      ctx.beginPath(); ctx.arc(px,py,d.size,0,TWO_PI); ctx.fill();
    }
    if (this.alpha>0.3) {
      ctx.globalAlpha=this.alpha*(isRev?0.07:0.05);
      const grad=ctx.createRadialGradient(this.lx,this.ly,0,this.lx,this.ly,16);
      grad.addColorStop(0,`hsl(${hue|0},${sat}%,${light}%)`);
      grad.addColorStop(1,"transparent");
      ctx.fillStyle=grad; ctx.beginPath(); ctx.arc(this.lx,this.ly,16,0,TWO_PI); ctx.fill();
    }
  }
}

const clusters = Array.from({length: N_CLUSTERS}, () => new Cluster());

// ════════════════════════════════════════════════════════════════
// CAPA 3 — Singularidad (v8 original, estados como números planos)
// ════════════════════════════════════════════════════════════════
const SG_FLOW=0, SG_CHARGE=1, SG_EXPLODE=2, SG_SCATTER=3, SG_RETURN=4;
const SG_DUR_FLOW=380, SG_DUR_CHARGE=70, SG_DUR_EXPLODE=45, SG_DUR_SCATTER=90, SG_DUR_RETURN=220;

function sgDur(state) {
  if (state===SG_FLOW)    return SG_DUR_FLOW;
  if (state===SG_CHARGE)  return SG_DUR_CHARGE;
  if (state===SG_EXPLODE) return SG_DUR_EXPLODE;
  if (state===SG_SCATTER) return SG_DUR_SCATTER;
  return SG_DUR_RETURN;
}

const NS=800;
const sX=new Float32Array(NS),sY=new Float32Array(NS);
const sVX=new Float32Array(NS),sVY=new Float32Array(NS);
const sPh=new Float32Array(NS),sHue=new Float32Array(NS);
const sExplVX=new Float32Array(NS),sExplVY=new Float32Array(NS);

let sgState=SG_FLOW, sgTimer=0, sgRadius=0, sgMaxR=0;

function initSGParticles() {
  for (let i=0;i<NS;i++) {
    const a=(i/NS)*TWO_PI*9+Math.random()*0.5, r=15+Math.random()*280;
    sX[i]=CX+Math.cos(a)*r; sY[i]=CY+Math.sin(a)*r;
    sVX[i]=0; sVY[i]=0;
    sPh[i]=Math.random()*TWO_PI; sHue[i]=220+Math.random()*140;
  }
}
initSGParticles();

function updateSingularity() {
  sgTimer++;
  const dur=sgDur(sgState);
  const p=Math.min(sgTimer/dur,1);

  if (sgTimer>=dur) {
    if (sgState===SG_FLOW) {
      sgState=SG_CHARGE; sgTimer=0; sgMaxR=sgRadius;
    } else if (sgState===SG_CHARGE) {
      sgState=SG_EXPLODE; sgTimer=0;
      for (let i=0;i<NS;i++) {
        const dx=sX[i]-CX,dy=sY[i]-CY,r=Math.sqrt(dx*dx+dy*dy)+0.1;
        const prox=1+Math.max(0,(80-r)/80)*2.5;
        const spd=(5+Math.random()*14)*prox;
        sExplVX[i]=(dx/r)*spd+(Math.random()-0.5)*4;
        sExplVY[i]=(dy/r)*spd+(Math.random()-0.5)*4;
      }
    } else if (sgState===SG_EXPLODE) {
      sgState=SG_SCATTER; sgTimer=0;
    } else if (sgState===SG_SCATTER) {
      sgState=SG_RETURN; sgTimer=0;
    } else {
      sgState=SG_FLOW; sgTimer=0; sgRadius=0; initSGParticles();
    }
  }

  if (sgState===SG_FLOW) {
    sgRadius=p*p*p*60;
  } else if (sgState===SG_CHARGE) {
    sgRadius=sgMaxR*(1+0.35*Math.sin(p*Math.PI*8));
  } else if (sgState===SG_EXPLODE) {
    sgRadius=sgMaxR*(1-p)*0.5;
  } else {
    sgRadius=0;
  }

  for (let i=0;i<NS;i++) {
    if (sgState===SG_FLOW||sgState===SG_CHARGE) {
      const dx=CX-sX[i],dy=CY-sY[i],r=Math.sqrt(dx*dx+dy*dy)+0.1;
      const pp=sgState===SG_CHARGE?1.0:p;
      const pull=0.025+pp*pp*0.09, swirl=0.022+pp*0.018;
      const nx=dx/r,ny=dy/r,tx=-ny,ty=nx;
      sVX[i]+=nx*pull*Math.sqrt(r)*0.12+tx*swirl;
      sVY[i]+=ny*pull*Math.sqrt(r)*0.12+ty*swirl;
      const lt=timeField(sX[i],sY[i]),turb=0.04+pp*0.06;
      sVX[i]+=Math.cos(lt*0.05+sPh[i]*2.1)*turb;
      sVY[i]+=Math.sin(lt*0.05+sPh[i]*1.7)*turb;
      sVX[i]*=0.90; sVY[i]*=0.90;
      sX[i]+=sVX[i]; sY[i]+=sVY[i];
      if (r<5) {
        const a=Math.random()*TWO_PI,nr=100+Math.random()*180;
        sX[i]=CX+Math.cos(a)*nr; sY[i]=CY+Math.sin(a)*nr;
        sVX[i]=0; sVY[i]=0;
      }
    } else if (sgState===SG_EXPLODE) {
      const boom=Math.max(0,1-p*0.7);
      sVX[i]=sExplVX[i]*boom; sVY[i]=sExplVY[i]*boom;
      sX[i]+=sVX[i]; sY[i]+=sVY[i];
    } else if (sgState===SG_SCATTER) {
      sVX[i]*=0.86; sVY[i]*=0.86;
      for (const v of VORTS) {
        const [vx,vy]=vortCenter(v);
        const dx=vx-sX[i],dy=vy-sY[i],r=Math.sqrt(dx*dx+dy*dy)+1;
        sVX[i]+=(dx/r)*0.08; sVY[i]+=(dy/r)*0.08;
      }
      sX[i]+=sVX[i]; sY[i]+=sVY[i];
    } else {
      const dx=CX-sX[i],dy=CY-sY[i],r=Math.sqrt(dx*dx+dy*dy)+0.1;
      const tgt=50+(i/NS)*240,nx=dx/r,ny=dy/r,tx=-ny,ty=nx;
      sVX[i]+=nx*(tgt-r)*0.0015+tx*0.018*p;
      sVY[i]+=ny*(tgt-r)*0.0015+ty*0.018*p;
      const lt=timeField(sX[i],sY[i]);
      sVX[i]+=Math.cos(lt*0.03+sPh[i])*(0.02*(1-p));
      sVY[i]+=Math.sin(lt*0.03+sPh[i])*(0.02*(1-p));
      sVX[i]*=0.91; sVY[i]*=0.91;
      sX[i]+=sVX[i]; sY[i]+=sVY[i];
    }
  }
}

function drawSingularity() {
  ctx.globalCompositeOperation="screen";
  if (sgRadius>1) {
    const pulse=sgState===SG_CHARGE?0.55+0.45*Math.sin(sgTimer*0.9):1.0;
    const hc=(t*0.4)%360;
    const g2=ctx.createRadialGradient(CX,CY,0,CX,CY,sgRadius);
    g2.addColorStop(0,`hsla(${hc|0},100%,99%,${0.95*pulse})`);
    g2.addColorStop(0.4,`hsla(${(hc+40)|0},95%,75%,${0.55*pulse})`);
    g2.addColorStop(1,"transparent");
    ctx.fillStyle=g2; ctx.globalAlpha=1;
    ctx.beginPath(); ctx.arc(CX,CY,sgRadius,0,TWO_PI); ctx.fill();
    const g1=ctx.createRadialGradient(CX,CY,0,CX,CY,sgRadius*3);
    g1.addColorStop(0,`hsla(${(hc+20)|0},80%,70%,${0.12*pulse})`);
    g1.addColorStop(1,"transparent");
    ctx.fillStyle=g1; ctx.beginPath(); ctx.arc(CX,CY,sgRadius*3,0,TWO_PI); ctx.fill();
    if (sgState===SG_CHARGE) {
      ctx.globalAlpha=0.4*pulse;
      ctx.strokeStyle=`hsl(${(hc+60)|0},100%,88%)`;
      ctx.lineWidth=1.0+pulse*1.5;
      ctx.beginPath(); ctx.arc(CX,CY,sgRadius*2.2,0,TWO_PI); ctx.stroke();
    }
  }
  ctx.globalCompositeOperation="screen";
  for (let i=0;i<NS;i++) {
    const dx=sX[i]-CX,dy=sY[i]-CY,r=Math.sqrt(dx*dx+dy*dy),norm=Math.min(r/290,1);
    const hue=(sHue[i]+t*0.09+norm*60)%360,spd=Math.sqrt(sVX[i]*sVX[i]+sVY[i]*sVY[i]),spdN=Math.min(spd/12,1);
    let alpha=0.12+(1-norm)*0.30+spdN*0.5;
    if (sgState===SG_CHARGE) alpha*=1.6;
    ctx.globalAlpha=Math.min(alpha,0.95);
    ctx.fillStyle=`hsl(${hue|0},${(62+spdN*35)|0}%,${(48+spdN*35+(1-norm)*20)|0}%)`;
    ctx.beginPath(); ctx.arc(sX[i],sY[i],0.5+(1-norm)*0.9+spdN*1.2,0,TWO_PI); ctx.fill();
  }
}

// ════════════════════════════════════════════════════════════════
// LOOP
// Synthesia: energy afecta el fade del fondo
// Sin música: fade = 0.055 (v8 original exacto)
// Con música: fade sube hasta 0.08 en momentos de mucha energía
// ════════════════════════════════════════════════════════════════
function loop() {
  if (document.hidden) { raf = null; return; }
  raf = requestAnimationFrame(loop);
  t++;

  updateAudio();

  const fadeBg = 0.055 + audio.energy * 0.025;
  ctx.globalCompositeOperation = "source-over";
  ctx.globalAlpha = fadeBg;
  ctx.fillStyle   = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  updateBullets();
  drawBullets();
  clusters.forEach(c => { c.update(); c.draw(); });
  updateSingularity();
  drawSingularity();
}

loop();

document.addEventListener("astro:before-swap", () => {
  cancelAnimationFrame(raf);
  window.removeEventListener("resize", onResize);
  if (audioEl) { audioEl.pause(); audioEl.src = ""; }
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

#synth-ui {
  position: fixed;
  bottom: 4rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  z-index: 100;
  background: rgba(5,5,10,0.75);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(168,85,247,0.25);
  border-radius: 2rem;
  padding: 0.4rem 0.8rem 0.4rem 1rem;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

#synth-input {
  background: transparent;
  border: none;
  outline: none;
  color: #e2e8f0;
  font-family: inherit;
  font-size: 0.75rem;
  width: 22rem;
  caret-color: #a855f7;
}
#synth-input::placeholder { color: rgba(167,139,250,0.4); }

#synth-btn {
  background: rgba(168,85,247,0.2);
  border: 1px solid rgba(168,85,247,0.4);
  border-radius: 1rem;
  color: #a855f7;
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  transition: background 0.2s;
}
#synth-btn:hover { background: rgba(168,85,247,0.35); }

#synth-status {
  font-size: 0.7rem;
  color: #a78bfa;
  min-width: 8rem;
  white-space: nowrap;
}
</style>
ASTRO

echo "✓ DanmakuVisualizer.astro creado"

# ── 4. Deploy ─────────────────────────────────────────────────────
sudo docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d --build
echo ""
echo "danmaku v8+synth — proxy YouTube via yt-dlp + Web Audio analyser"
echo "Pega una URL de YouTube en el input de /danmaku y presiona ▶"
