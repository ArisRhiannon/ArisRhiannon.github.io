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

const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !raf) loop();
});

let raf, t = 0;

function resize() {
  canvas.width  = innerWidth;
  canvas.height = innerHeight;
  buildOrbitSeeds();
}
resize();
const onResize = () => resize();
window.addEventListener("resize", onResize);

let CX = canvas.width*0.5, CY = canvas.height*0.5, CMAX = Math.max(canvas.width, canvas.height);
window.addEventListener("resize", () => {
  CX = canvas.width*0.5; CY = canvas.height*0.5; CMAX = Math.max(canvas.width, canvas.height);
});

const TWO_PI = Math.PI * 2;

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

// ════════════════════════════════════════════════════════════════
// CAPA 0 — Líneas orbitales animadas
// ════════════════════════════════════════════════════════════════
const offOrbit = document.createElement("canvas");
let octx = offOrbit.getContext("2d", { alpha: true });

const N_ORBIT_LINES = 90;
let orbitSeeds = [];

function buildOrbitSeeds() {
  offOrbit.width  = canvas.width;
  offOrbit.height = canvas.height;
  octx = offOrbit.getContext("2d", { alpha: true });
  orbitSeeds = [];
  for (let i = 0; i < N_ORBIT_LINES; i++) {
    const rNorm  = 0.15 + Math.pow(Math.random(), 0.7) * 0.80;
    const rBase  = rNorm * CMAX * 0.52;
    const rAmp   = rBase * (0.04 + Math.random() * 0.14);
    const phaseSpd = (0.0003 + Math.random()*0.0025) * (Math.random() < 0.15 ? -1 : 1);
    const phase0   = Math.random() * TWO_PI;
    const harmonics = [
      { freq: 2 + Math.floor(Math.random()*3), amp: 0.3 + Math.random()*0.5, ph: Math.random()*TWO_PI },
      { freq: 3 + Math.floor(Math.random()*4), amp: 0.15 + Math.random()*0.3, ph: Math.random()*TWO_PI },
      { freq: 5 + Math.floor(Math.random()*5), amp: 0.05 + Math.random()*0.15, ph: Math.random()*TWO_PI },
    ];
    const tilt       = (Math.random()-0.5) * 0.9;
    const hue        = Math.random() * 360;
    const sat        = 30 + Math.random() * 55;
    const bright     = 22 + Math.random() * 28;
    const lw         = 0.25 + Math.random() * 0.45;
    const alpha      = 0.07 + Math.random() * 0.12;
    const birthAngle = Math.random() * TWO_PI;
    const unrollSpd  = 0.0008 + Math.random() * 0.003;
    const progress   = Math.random();
    orbitSeeds.push({ rBase, rAmp, phaseSpd, phase0, harmonics, tilt,
                      hue, sat, bright, lw, alpha, birthAngle, unrollSpd, progress });
  }
}
buildOrbitSeeds();

let lastOrbitT = -999;
const ORBIT_REBUILD = 3;

function drawOrbitLine(seed, tt) {
  const { rBase, rAmp, phaseSpd, phase0, harmonics, tilt, hue, sat, bright, lw, alpha, birthAngle, progress } = seed;
  const STEPS = 180;
  const drawSteps = Math.ceil(progress * STEPS);
  if (drawSteps < 2) return;

  octx.beginPath();
  let first = true;
  for (let s = 0; s < drawSteps; s++) {
    const theta = birthAngle + (s / STEPS) * TWO_PI;
    let rm = rBase + rAmp * Math.sin(theta + tt * phaseSpd + phase0);
    for (const h of harmonics) {
      rm += rAmp * h.amp * Math.sin(theta * h.freq + tt * phaseSpd * h.freq * 0.7 + h.ph);
    }
    const tw  = theta + tilt * Math.sin(theta * 1.5 + tt * phaseSpd * 0.8);
    const ecc = 0.80 + 0.20 * Math.cos(theta * 0.5 + tt * phaseSpd * 0.3);
    const x = CX + Math.cos(tw) * rm;
    const y = CY + Math.sin(tw) * rm * ecc;
    if (first) { octx.moveTo(x, y); first = false; }
    else         octx.lineTo(x, y);
  }

  const speedBoost = Math.min(Math.abs(seed.phaseSpd) / 0.003, 1);
  octx.strokeStyle = `hsl(${hue|0},${(sat + speedBoost*20)|0}%,${(bright + speedBoost*15)|0}%)`;
  octx.globalAlpha = alpha + speedBoost * 0.06;
  octx.lineWidth   = lw;
  octx.stroke();

  // Punta: micro-punto, tamaño máximo fijo y pequeño
  if (progress > 0.02) {
    const lastTheta = birthAngle + progress * TWO_PI;
    let rm2 = rBase + rAmp * Math.sin(lastTheta + tt * phaseSpd + phase0);
    for (const h of harmonics) {
      rm2 += rAmp * h.amp * Math.sin(lastTheta * h.freq + tt * phaseSpd * h.freq * 0.7 + h.ph);
    }
    const tw2  = lastTheta + tilt * Math.sin(lastTheta * 1.5 + tt * phaseSpd * 0.8);
    const ecc2 = 0.80 + 0.20 * Math.cos(lastTheta * 0.5 + tt * phaseSpd * 0.3);
    const tx = CX + Math.cos(tw2) * rm2;
    const ty = CY + Math.sin(tw2) * rm2 * ecc2;
    octx.globalAlpha = alpha * 3.5;
    octx.fillStyle   = `hsl(${hue|0},90%,${(bright+25)|0}%)`;
    octx.beginPath(); octx.arc(tx, ty, Math.min(lw * 2.5, 1.8), 0, TWO_PI); octx.fill();
    octx.globalAlpha = alpha * 0.8;
    octx.beginPath(); octx.arc(tx, ty, Math.min(lw * 6, 3.5), 0, TWO_PI); octx.fill();
  }
}

function rebuildOrbits(tt) {
  lastOrbitT = tt;
  offOrbit.width  = canvas.width;
  offOrbit.height = canvas.height;
  octx.clearRect(0, 0, offOrbit.width, offOrbit.height);
  for (const seed of orbitSeeds) {
    seed.progress = Math.min(1, seed.progress + seed.unrollSpd * ORBIT_REBUILD);
    if (seed.progress >= 1) {
      seed.progress   = 0;
      seed.birthAngle = Math.random() * TWO_PI;
      seed.hue        = (seed.hue + 15 + Math.random()*30) % 360;
    }
    drawOrbitLine(seed, tt);
  }
}

function drawOrbits() {
  if (t - lastOrbitT >= ORBIT_REBUILD) rebuildOrbits(t);
  ctx.globalCompositeOperation = "screen";
  ctx.globalAlpha = 0.6;
  ctx.drawImage(offOrbit, 0, 0);
}

// ════════════════════════════════════════════════════════════════
// CAPA 1 — Bullets principales
// ════════════════════════════════════════════════════════════════
const N = 2400;
const bR=new Float32Array(N), bAngle=new Float32Array(N);
const bSpin=new Float32Array(N), bSpeed=new Float32Array(N);
const bPhase=new Float32Array(N), bX=new Float32Array(N), bY=new Float32Array(N);
const bPX=new Float32Array(N), bPY=new Float32Array(N);

for (let i = 0; i < N; i++) {
  bR[i]     = Math.random() * CMAX * 0.5;
  bAngle[i] = Math.random() * TWO_PI;
  bSpin[i]  = (Math.random()-0.5) * 0.055;
  bSpeed[i] = 0.8 + Math.random() * 2.2;
  bPhase[i] = Math.random() * TWO_PI * 3;
  bX[i] = CX + Math.cos(bAngle[i])*bR[i];
  bY[i] = CY + Math.sin(bAngle[i])*bR[i];
  bPX[i] = bX[i]; bPY[i] = bY[i];
}

function resetBullet(i) {
  bR[i]=Math.random()*30; bAngle[i]=Math.random()*TWO_PI;
  bSpin[i]=(Math.random()-0.5)*0.055; bSpeed[i]=0.8+Math.random()*2.2;
  bPhase[i]=Math.random()*TWO_PI*3;
}

function updateBullets() {
  for (let i = 0; i < N; i++) {
    bPX[i]=bX[i]; bPY[i]=bY[i];
    const lt = timeField(CX+Math.cos(bAngle[i])*bR[i], CY+Math.sin(bAngle[i])*bR[i]);
    const flow = Math.sin(lt*0.012+bPhase[i]*0.3)*Math.cos(lt*0.007-bPhase[i]*0.2);
    const dir = flow > 0 ? 1 : -1;
    bR[i]    += bSpeed[i] * dir;
    bAngle[i]+= bSpin[i]*dir
               + Math.sin(bR[i]*0.025+lt*0.04+bPhase[i])*0.07
               + Math.cos(bR[i]*0.011-lt*0.02+bPhase[i]*1.3)*0.04;
    const x2=CX+Math.cos(bAngle[i])*bR[i], y2=CY+Math.sin(bAngle[i])*bR[i];
    const [wx,wy]=warp(x2,y2,lt);
    bX[i]=wx; bY[i]=wy;
    if (bR[i]<0||bR[i]>CMAX) resetBullet(i);
  }
}

function drawBullets() {
  ctx.globalCompositeOperation="lighter";
  for (let i = 0; i < N; i++) {
    const depth=bR[i]/CMAX;
    const lt=timeField(bX[i],bY[i]);
    const hue=(bR[i]*0.4+lt*2+bPhase[i]*80)%360;
    const sat=65+Math.sin(lt*0.04+bPhase[i])*30;
    const sz=0.7+depth*3.6;
    const dx=bX[i]-bPX[i], dy=bY[i]-bPY[i];
    const spd=Math.sqrt(dx*dx+dy*dy);
    if (spd>0.5) {
      ctx.globalAlpha=(0.25+(1-depth)*0.2)*Math.min(spd*0.12,1);
      ctx.strokeStyle=`hsl(${hue|0},${sat|0}%,${(45+depth*25)|0}%)`;
      ctx.lineWidth=sz*0.7; ctx.lineCap="round";
      ctx.beginPath(); ctx.moveTo(bPX[i],bPY[i]); ctx.lineTo(bX[i],bY[i]); ctx.stroke();
    }
    ctx.fillStyle=`hsl(${hue|0},${sat|0}%,${(55+depth*25)|0}%)`;
    ctx.globalAlpha=0.6+(1-depth)*0.3;
    ctx.beginPath(); ctx.arc(bX[i],bY[i],sz,0,TWO_PI); ctx.fill();
    ctx.globalAlpha=0.06+(1-depth)*0.04;
    ctx.beginPath(); ctx.arc(bX[i],bY[i],sz*3.2,0,TWO_PI); ctx.fill();
  }
}

// ════════════════════════════════════════════════════════════════
// CAPA 2 — Polvo etéreo + trails
// ════════════════════════════════════════════════════════════════
const N_CLUSTERS=90, N_DUST=22, TRAIL_LEN=52;
const COLD_HUES=[195,215,235,255,275,205,225,248];
const VORTS=Array.from({length:3},(_,i)=>({phase:(i/3)*Math.PI*2,r:100+i*70,spd:0.003+i*0.0015}));

function vortCenter(v) {
  const a=v.phase+t*v.spd; return [CX+Math.cos(a)*v.r, CY+Math.sin(a)*v.r];
}

function leaderField(x,y) {
  let vx=0,vy=0;
  for(const v of VORTS){
    const [vox,voy]=vortCenter(v); const dx=x-vox,dy=y-voy;
    const r2=dx*dx+dy*dy+300; const s=12000/r2;
    vx+=-dy*s; vy+=dx*s;
  }
  const dx=x-CX,dy=y-CY,r=Math.sqrt(dx*dx+dy*dy)+0.001,a=Math.atan2(dy,dx);
  const lt=timeField(x,y),bg=Math.sin(r*0.01+lt*0.015)*0.5+Math.cos(a*2+lt*0.009)*0.3;
  return [vx+Math.cos(a+bg)*0.7, vy+Math.sin(a+bg)*0.7];
}

class Cluster {
  constructor(){this.init();}
  init(){
    const roll=Math.random();
    if(roll<0.4){const v=VORTS[Math.floor(Math.random()*3)];const[vx,vy]=vortCenter(v);const a=Math.random()*TWO_PI;this.lx=vx+Math.cos(a)*(20+Math.random()*80);this.ly=vy+Math.sin(a)*(20+Math.random()*80);}
    else if(roll<0.7){const a=Math.random()*TWO_PI,r=Math.random()*60;this.lx=CX+Math.cos(a)*r;this.ly=CY+Math.sin(a)*r;}
    else{const s=Math.floor(Math.random()*4);if(s===0){this.lx=Math.random()*canvas.width;this.ly=-20;}else if(s===1){this.lx=canvas.width+20;this.ly=Math.random()*canvas.height;}else if(s===2){this.lx=Math.random()*canvas.width;this.ly=canvas.height+20;}else{this.lx=-20;this.ly=Math.random()*canvas.height;}}
    this.vx=0;this.vy=0;this.life=0;this.maxLife=200+Math.random()*300;
    this.hue=COLD_HUES[Math.floor(Math.random()*8)]+(Math.random()-0.5)*14;
    this.alpha=0;this.ghost=Math.random()<0.28;this.dt=1;this.flipCD=70+Math.random()*90;
    this.history=[];this.trail=[];
    this.dust=Array.from({length:N_DUST},()=>({angle:Math.random()*TWO_PI,r:4+Math.random()*20,phase:Math.random()*TWO_PI,ospd:(Math.random()-0.5)*0.035,drift:(Math.random()-0.5)*0.8,size:0.6+Math.random()*1.4}));
  }
  update(){
    this.life++;
    if(this.life<40)this.alpha=this.life/40;
    else if(this.life>this.maxLife-60)this.alpha=(this.maxLife-this.life)/60;
    else this.alpha=1;
    if(this.ghost){this.flipCD--;if(this.flipCD<=0){this.dt=-this.dt;this.flipCD=70+Math.random()*90;}}
    if(this.ghost&&this.dt<0&&this.history.length>1){const p=this.history.pop();this.lx=p.x;this.ly=p.y;this.vx=p.vx;this.vy=p.vy;}
    else{const[fx,fy]=leaderField(this.lx,this.ly);this.vx=this.vx*0.85+fx*0.15;this.vy=this.vy*0.85+fy*0.15;this.history.push({x:this.lx,y:this.ly,vx:this.vx,vy:this.vy});if(this.history.length>100)this.history.shift();this.lx+=this.vx;this.ly+=this.vy;}
    this.trail.push({x:this.lx,y:this.ly});if(this.trail.length>TRAIL_LEN)this.trail.shift();
    const tL=this.ghost&&this.dt<0?-t:t;
    for(const d of this.dust){d.angle+=d.ospd+Math.sin(tL*0.02+d.phase)*0.008;d.r=Math.max(2,d.r+Math.sin(tL*0.015+d.phase*2)*0.3+d.drift*0.02);if(d.r>26)d.drift=-Math.abs(d.drift);if(d.r<3)d.drift=Math.abs(d.drift);}
    const m=120;if(this.lx<-m||this.lx>canvas.width+m||this.ly<-m||this.ly>canvas.height+m||this.life>=this.maxLife)this.init();
  }
  draw(){
    const isRev=this.ghost&&this.dt<0;
    const hue=isRev?(this.hue+145+Math.sin(t*0.02)*12)%360:(this.hue+Math.sin(t*0.01)*10)%360;
    const sat=isRev?95:72,light=isRev?70:62,n=this.trail.length;
    if(n>=4){
      ctx.globalCompositeOperation="screen";ctx.lineCap="round";ctx.lineJoin="round";
      ctx.globalAlpha=this.alpha*(isRev?0.10:0.07);ctx.strokeStyle=`hsl(${hue|0},${sat}%,${light}%)`;ctx.lineWidth=isRev?0.9:0.6;
      ctx.beginPath();ctx.moveTo((this.trail[0].x+this.trail[1].x)*0.5,(this.trail[0].y+this.trail[1].y)*0.5);
      for(let i=1;i<n-1;i++){const mx=(this.trail[i].x+this.trail[i+1].x)*0.5,my=(this.trail[i].y+this.trail[i+1].y)*0.5;ctx.quadraticCurveTo(this.trail[i].x,this.trail[i].y,mx,my);}
      ctx.stroke();
      const tail=Math.max(0,n-14);ctx.globalAlpha=this.alpha*(isRev?0.20:0.13);ctx.lineWidth=isRev?1.2:0.85;
      ctx.beginPath();ctx.moveTo((this.trail[tail].x+this.trail[tail+1].x)*0.5,(this.trail[tail].y+this.trail[tail+1].y)*0.5);
      for(let i=tail+1;i<n-1;i++){const mx=(this.trail[i].x+this.trail[i+1].x)*0.5,my=(this.trail[i].y+this.trail[i+1].y)*0.5;ctx.quadraticCurveTo(this.trail[i].x,this.trail[i].y,mx,my);}
      ctx.stroke();
    }
    ctx.globalCompositeOperation="screen";ctx.fillStyle=`hsl(${hue|0},${sat}%,${light}%)`;
    for(const d of this.dust){const px=this.lx+Math.cos(d.angle)*d.r,py=this.ly+Math.sin(d.angle)*d.r;ctx.globalAlpha=this.alpha*(0.18+d.size*0.08)*(isRev?1.35:1.0);ctx.beginPath();ctx.arc(px,py,d.size,0,TWO_PI);ctx.fill();}
    if(this.alpha>0.3){ctx.globalAlpha=this.alpha*(isRev?0.07:0.05);const g=ctx.createRadialGradient(this.lx,this.ly,0,this.lx,this.ly,16);g.addColorStop(0,`hsl(${hue|0},${sat}%,${light}%)`);g.addColorStop(1,"transparent");ctx.fillStyle=g;ctx.beginPath();ctx.arc(this.lx,this.ly,16,0,TWO_PI);ctx.fill();}
  }
}

const clusters=Array.from({length:N_CLUSTERS},()=>new Cluster());

// ════════════════════════════════════════════════════════════════
// CAPA 3 — Fluido SPH-lite
// ════════════════════════════════════════════════════════════════
const NF=3200;
const fX=new Float32Array(NF),fY=new Float32Array(NF);
const fVX=new Float32Array(NF),fVY=new Float32Array(NF);
const fPh=new Float32Array(NF),fHue=new Float32Array(NF);

for(let i=0;i<NF;i++){
  const v=VORTS[i%3],a=Math.random()*TWO_PI,r=20+Math.random()*180;
  const[vx,vy]=vortCenter(v);
  fX[i]=vx+Math.cos(a)*r;fY[i]=vy+Math.sin(a)*r;
  fVX[i]=(Math.random()-0.5)*0.5;fVY[i]=(Math.random()-0.5)*0.5;
  fPh[i]=Math.random()*TWO_PI;fHue[i]=170+Math.random()*140;
}

const CELL=24;let gridW=0,gridH=0,fGrid;
function buildGrid(){
  gridW=Math.ceil(canvas.width/CELL)+1;gridH=Math.ceil(canvas.height/CELL)+1;
  fGrid=new Map();
  for(let i=0;i<NF;i++){const cx=(fX[i]/CELL)|0,cy=(fY[i]/CELL)|0,key=cx+cy*gridW;if(!fGrid.has(key))fGrid.set(key,[]);fGrid.get(key).push(i);}
}

const REP_R=18,REP_R2=324,REP_K=0.35,ATT_K=0.018,DRAG_F=0.92,MAX_V=3.8;
function updateFluid(){
  buildGrid();
  for(let i=0;i<NF;i++){
    let ax=0,ay=0;
    for(const v of VORTS){const[vox,voy]=vortCenter(v);const dx=vox-fX[i],dy=voy-fY[i],r=Math.sqrt(dx*dx+dy*dy)+1,tang=0.7+0.3*Math.sin(fPh[i]+t*0.01);ax+=(-dy/r)*tang*ATT_K*(400/Math.max(r,40));ay+=(dx/r)*tang*ATT_K*(400/Math.max(r,40));ax+=(dx/r)*ATT_K*0.15;ay+=(dy/r)*ATT_K*0.15;}
    const lt=timeField(fX[i],fY[i]),fa=lt*0.04+fPh[i]*0.5;ax+=Math.cos(fa)*0.06;ay+=Math.sin(fa)*0.06;
    const cx0=(fX[i]/CELL)|0,cy0=(fY[i]/CELL)|0;
    for(let dcx=-1;dcx<=1;dcx++)for(let dcy=-1;dcy<=1;dcy++){const cell=fGrid.get((cx0+dcx)+(cy0+dcy)*gridW);if(!cell)continue;for(const j of cell){if(j===i)continue;const dx=fX[i]-fX[j],dy=fY[i]-fY[j],d2=dx*dx+dy*dy;if(d2<REP_R2&&d2>0.01){const d=Math.sqrt(d2),f=REP_K*(REP_R-d)/REP_R;ax+=(dx/d)*f;ay+=(dy/d)*f;}}}
    fVX[i]=(fVX[i]+ax)*DRAG_F;fVY[i]=(fVY[i]+ay)*DRAG_F;
    const spd=Math.sqrt(fVX[i]*fVX[i]+fVY[i]*fVY[i]);if(spd>MAX_V){fVX[i]*=MAX_V/spd;fVY[i]*=MAX_V/spd;}
    fX[i]+=fVX[i];fY[i]+=fVY[i];
    const M=80;if(fX[i]<-M)fX[i]=canvas.width+M-1;if(fX[i]>canvas.width+M)fX[i]=-M+1;if(fY[i]<-M)fY[i]=canvas.height+M-1;if(fY[i]>canvas.height+M)fY[i]=-M+1;
  }
}
function drawFluid(){
  ctx.globalCompositeOperation="screen";
  for(let i=0;i<NF;i++){
    const spd=Math.sqrt(fVX[i]*fVX[i]+fVY[i]*fVY[i]),norm=Math.min(spd/MAX_V,1),hue=(fHue[i]+norm*60+t*0.05)%360;
    ctx.globalAlpha=0.22+norm*0.25;ctx.fillStyle=`hsl(${hue|0},${(55+norm*35)|0}%,${(35+norm*30)|0}%)`;
    const sz=0.5+norm*1.2;ctx.beginPath();ctx.arc(fX[i],fY[i],sz,0,TWO_PI);ctx.fill();
    if(norm>0.5){ctx.globalAlpha=0.04+norm*0.04;ctx.beginPath();ctx.arc(fX[i],fY[i],sz*3.5,0,TWO_PI);ctx.fill();}
  }
}

// ════════════════════════════════════════════════════════════════
// CAPA 4 — Singularidad central
// Estados como números planos — sin objeto SG para evitar
// el bug de inicialización léxica en esbuild
// ════════════════════════════════════════════════════════════════
const SG_FLOW=0, SG_CHARGE=1, SG_EXPLODE=2, SG_SCATTER=3, SG_RETURN=4;
const SG_DUR_FLOW=220, SG_DUR_CHARGE=45, SG_DUR_EXPLODE=30, SG_DUR_SCATTER=60, SG_DUR_RETURN=150;

function sgDur(state) {
  if(state===SG_FLOW)    return SG_DUR_FLOW;
  if(state===SG_CHARGE)  return SG_DUR_CHARGE;
  if(state===SG_EXPLODE) return SG_DUR_EXPLODE;
  if(state===SG_SCATTER) return SG_DUR_SCATTER;
  return SG_DUR_RETURN;
}

const NS=800;
const sX=new Float32Array(NS),sY=new Float32Array(NS);
const sVX=new Float32Array(NS),sVY=new Float32Array(NS);
const sPh=new Float32Array(NS),sHue=new Float32Array(NS);
const sExplVX=new Float32Array(NS),sExplVY=new Float32Array(NS);

let sgState=SG_FLOW, sgTimer=0, sgRadius=0, sgMaxR=0;
let shockR=0, shockAlpha=0;

function initSGParticles(){
  for(let i=0;i<NS;i++){
    const a=(i/NS)*TWO_PI*9+Math.random()*0.5, r=15+Math.random()*280;
    sX[i]=CX+Math.cos(a)*r; sY[i]=CY+Math.sin(a)*r;
    sVX[i]=0; sVY[i]=0;
    sPh[i]=Math.random()*TWO_PI; sHue[i]=220+Math.random()*140;
  }
}
initSGParticles();

function updateSingularity(){
  sgTimer++;
  const dur=sgDur(sgState);
  const p=Math.min(sgTimer/dur, 1);

  if(sgTimer>=dur){
    if(sgState===SG_FLOW){
      sgState=SG_CHARGE; sgTimer=0; sgMaxR=sgRadius;
    } else if(sgState===SG_CHARGE){
      sgState=SG_EXPLODE; sgTimer=0;
      for(let i=0;i<NS;i++){
        const dx=sX[i]-CX,dy=sY[i]-CY,r=Math.sqrt(dx*dx+dy*dy)+0.1;
        const prox=1+Math.max(0,(80-r)/80)*2.5;
        const spd=(5+Math.random()*14)*prox;
        sExplVX[i]=(dx/r)*spd+(Math.random()-0.5)*4;
        sExplVY[i]=(dy/r)*spd+(Math.random()-0.5)*4;
      }
      shockR=sgMaxR; shockAlpha=1.0;
    } else if(sgState===SG_EXPLODE){
      sgState=SG_SCATTER; sgTimer=0;
    } else if(sgState===SG_SCATTER){
      sgState=SG_RETURN; sgTimer=0;
    } else {
      sgState=SG_FLOW; sgTimer=0; sgRadius=0; initSGParticles();
    }
  }

  if(sgState===SG_FLOW){
    sgRadius=p*p*p*60;
  } else if(sgState===SG_CHARGE){
    sgRadius=sgMaxR*(1+0.35*Math.sin(p*Math.PI*8));
  } else if(sgState===SG_EXPLODE){
    sgRadius=sgMaxR*(1-p)*0.5;
  } else {
    sgRadius=0;
  }

  if(shockAlpha>0){ shockR+=14; shockAlpha=Math.max(0,shockAlpha-0.025); }

  for(let i=0;i<NS;i++){
    if(sgState===SG_FLOW||sgState===SG_CHARGE){
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
      if(r<5){const a=Math.random()*TWO_PI,nr=100+Math.random()*180;sX[i]=CX+Math.cos(a)*nr;sY[i]=CY+Math.sin(a)*nr;sVX[i]=0;sVY[i]=0;}
    } else if(sgState===SG_EXPLODE){
      const boom=Math.max(0,1-p*0.7);
      sVX[i]=sExplVX[i]*boom; sVY[i]=sExplVY[i]*boom;
      sX[i]+=sVX[i]; sY[i]+=sVY[i];
    } else if(sgState===SG_SCATTER){
      sVX[i]*=0.86; sVY[i]*=0.86;
      for(const v of VORTS){const[vx,vy]=vortCenter(v);const dx=vx-sX[i],dy=vy-sY[i],r=Math.sqrt(dx*dx+dy*dy)+1;sVX[i]+=(dx/r)*0.08;sVY[i]+=(dy/r)*0.08;}
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

function drawSingularity(){
  ctx.globalCompositeOperation="screen";

  if(shockAlpha>0.01){
    ctx.globalAlpha=shockAlpha*0.35;
    ctx.strokeStyle=`hsl(${(t*0.5)%360|0},90%,80%)`;
    ctx.lineWidth=2.5;
    ctx.beginPath();ctx.arc(CX,CY,shockR,0,TWO_PI);ctx.stroke();
    ctx.globalAlpha=shockAlpha*0.10;
    ctx.lineWidth=8;
    ctx.beginPath();ctx.arc(CX,CY,shockR*0.92,0,TWO_PI);ctx.stroke();
  }

  if(sgRadius>1){
    const pulse=sgState===SG_CHARGE?0.55+0.45*Math.sin(sgTimer*0.9):1.0;
    const hc=(t*0.4)%360;
    const g2=ctx.createRadialGradient(CX,CY,0,CX,CY,sgRadius);
    g2.addColorStop(0,`hsla(${hc|0},100%,99%,${0.95*pulse})`);
    g2.addColorStop(0.4,`hsla(${(hc+40)|0},95%,75%,${0.55*pulse})`);
    g2.addColorStop(1,"transparent");
    ctx.fillStyle=g2;ctx.globalAlpha=1;
    ctx.beginPath();ctx.arc(CX,CY,sgRadius,0,TWO_PI);ctx.fill();
    const g1=ctx.createRadialGradient(CX,CY,0,CX,CY,sgRadius*3);
    g1.addColorStop(0,`hsla(${(hc+20)|0},80%,70%,${0.12*pulse})`);
    g1.addColorStop(1,"transparent");
    ctx.fillStyle=g1;ctx.beginPath();ctx.arc(CX,CY,sgRadius*3,0,TWO_PI);ctx.fill();
    if(sgState===SG_CHARGE){
      ctx.globalAlpha=0.4*pulse;ctx.strokeStyle=`hsl(${(hc+60)|0},100%,88%)`;
      ctx.lineWidth=1.0+pulse*1.5;ctx.beginPath();ctx.arc(CX,CY,sgRadius*2.2,0,TWO_PI);ctx.stroke();
    }
  }

  ctx.globalCompositeOperation="screen";
  for(let i=0;i<NS;i++){
    const dx=sX[i]-CX,dy=sY[i]-CY,r=Math.sqrt(dx*dx+dy*dy),norm=Math.min(r/290,1);
    const hue=(sHue[i]+t*0.09+norm*60)%360,spd=Math.sqrt(sVX[i]*sVX[i]+sVY[i]*sVY[i]),spdN=Math.min(spd/12,1);
    let alpha=0.12+(1-norm)*0.30+spdN*0.5;
    if(sgState===SG_CHARGE)alpha*=1.6;
    ctx.globalAlpha=Math.min(alpha,0.95);
    ctx.fillStyle=`hsl(${hue|0},${(62+spdN*35)|0}%,${(48+spdN*35+(1-norm)*20)|0}%)`;
    ctx.beginPath();ctx.arc(sX[i],sY[i],0.5+(1-norm)*0.9+spdN*1.2,0,TWO_PI);ctx.fill();
  }
}

// ════════════════════════════════════════════════════════════════
// LOOP
// ════════════════════════════════════════════════════════════════
function loop(){
  if(document.hidden){raf=null;return;}
  raf=requestAnimationFrame(loop);
  t++;
  ctx.globalCompositeOperation="source-over";
  ctx.globalAlpha=0.038;
  ctx.fillStyle="#000";
  ctx.fillRect(0,0,canvas.width,canvas.height);
  drawOrbits();
  updateBullets();drawBullets();
  clusters.forEach(c=>{c.update();c.draw();});
  updateFluid();drawFluid();
  updateSingularity();drawSingularity();
}

loop();

document.addEventListener("astro:before-swap",()=>{
  cancelAnimationFrame(raf);
  window.removeEventListener("resize",onResize);
},{once:true});

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
echo "danmaku v9b — fix ReferenceError: SG como constantes planas, no objeto"
