/* The three-sided mirror, alive: WebGL2, no dependencies.
   Canvas space is the 1240×1400 cut-out. The wings unfold on their real hinge lines; the red glass
   ripples, the starry glass twinkles, the sky glass drifts; Alice floats, breathes, sways her
   twintails, tilts her head and blinks. Layers come from trt-rig.json (built from the key art). */
import rig from './trt-rig.json';

const W = 1240;
const H = 1400;
const BASE = '/trianthology/';
/* Hinge lines (x = a + b·y) between the wings and the centre, traced on the frame gaps. */
const HL = [346 - 0.09 * 750, 0.09];
const HR = [944 + 0.107 * 750, -0.107];
const NECK = [640, 565];
const GEM = [707, 381];
const EYES = [605, 405, 190, 130];
const TAU = Math.PI * 2;

const VS_PANE = `#version 300 es
in vec2 a_p;
uniform vec2 u_hinge; uniform float u_ang, u_f;
out vec2 v_p;
void main() {
  vec3 P = vec3(a_p, 0.);
  if (u_ang != 0.) {
    vec3 o = vec3(u_hinge.x, 0., 0.), d = normalize(vec3(u_hinge.y, 1., 0.)), r = P - o;
    vec3 along = dot(r, d) * d, perp = r - along;
    P = o + along + perp * cos(u_ang) + cross(d, perp) * sin(u_ang);
  }
  float w = (u_f - P.z) / u_f;
  vec2 c = vec2(${W / 2}., ${H / 2}.), q = c + (P.xy - c) / w;
  v_p = a_p;
  gl_Position = vec4((q.x / ${W}.) * 2. - 1., 1. - (q.y / ${H}.) * 2., 0., 1.) * w;
}`;

const FS_PANE = `#version 300 es
precision highp float;
in vec2 v_p;
uniform sampler2D u_E, u_fx, u_sky;
uniform int u_side;
uniform float u_t, u_lit, u_a, u_fxOn;
uniform vec4 u_drop[3];
uniform vec4 u_skyL, u_skyR;
out vec4 o;
const vec2 SZ = vec2(${W}., ${H}.);
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void main() {
  float xl = ${HL[0].toFixed(2)} + ${HL[1]} * v_p.y, xr = ${HR[0].toFixed(2)} + ${HR[1]} * v_p.y;
  float d = u_side == 1 ? xl - v_p.x : u_side == 2 ? v_p.x - xr : min(v_p.x - xl, xr - v_p.x);
  float edge = clamp(d / max(fwidth(d), 1e-3) + .5, 0., 1.);
  if (edge <= 0.) discard;
  vec2 uv = v_p / SZ;
  vec4 c = texture(u_E, uv);
  vec4 fx = texture(u_fx, uv);
  float m = fx.r * u_fxOn;
  if (u_side == 1 && m > 0.) {
    /* Red glass: drops fall on it like on still water; rings travel out and fade. */
    vec2 disp = vec2(0.); float crest = 0.;
    for (int i = 0; i < 3; i++) {
      vec4 dr = u_drop[i];
      float age = u_t - dr.z;
      if (age < 0. || age > 5.) continue;
      vec2 dv = v_p - dr.xy; float r = length(dv) + 1e-3;
      float x = r - age * 70.;
      float env = exp(-x * x / 1800.) * exp(-age * .75) * dr.w;
      float s = sin(x * .16);
      disp += dv / r * s * env * 4.6;
      crest += max(0., cos(x * .16)) * env;
    }
    disp += vec2(sin(v_p.y * .045 + u_t * 1.3), cos(v_p.x * .05 - u_t * 1.1)) * .45;
    vec2 uv2 = (v_p + disp) / SZ;
    float m2 = texture(u_fx, uv2).r;
    c = mix(c, texture(u_E, uv2), m * m2);
    c.rgb += vec3(1., .88, .82) * crest * .17 * m * c.a;
  } else if (u_side == 0 && u_fxOn > 0.) {
    /* Starry glass: each small star keeps its own slow pulse; a faint light crosses now and then. */
    float h = hash(floor(v_p / 5.));
    float k = .5 + .5 * sin(u_t * (1.1 + h * 1.9) + h * 60.);
    c.rgb *= 1. + fx.g * u_fxOn * (1.5 * k * k * k - .35);
    float s = dot(v_p, vec2(.94, .34)) - (mod(u_t, 11.) * 190. - 500.);
    c.rgb += vec3(1., .97, .9) * exp(-s * s / 5000.) * .1 * m * c.a;
  } else if (u_side == 2 && m > 0.) {
    /* Sky glass: the painted clouds drift along, looped seamlessly in tile space. */
    float a = u_skyL.x * v_p.y + u_skyL.y, b = u_skyR.x * v_p.y + u_skyR.y;
    vec2 tuv = vec2((v_p.x - a) / (b - a) + u_t * 4.2 / u_skyR.z, (v_p.y - u_skyL.z) / u_skyL.w);
    vec3 sky = texture(u_sky, tuv).rgb;
    c.rgb = mix(c.rgb, sky * c.a, m);
  }
  o = vec4(c.rgb * u_lit, c.a) * edge * u_a;
}`;

const VS_ALICE = `#version 300 es
in vec2 a_p, a_uv;
in float a_w;
uniform vec2 u_move, u_root, u_axis;
uniform float u_t, u_head, u_breath, u_hair, u_len, u_ph, u_spin;
out vec2 v_uv, v_p;
vec2 rot(vec2 p, vec2 c, float a) { float s = sin(a), k = cos(a); p -= c; return c + vec2(k * p.x - s * p.y, s * p.x + k * p.y); }
void main() {
  vec2 p = a_p;
  if (u_hair > 0.) {
    /* A travelling wave down each twintail: still at the tie, freest at the tips. */
    float s = dot(p - u_root, u_axis) / u_len;
    float w = sin(u_t * 1.75 - s * 2.6 + u_ph) + .38 * sin(u_t * 2.9 - s * 4.3 + u_ph * 1.7);
    p += vec2(-u_axis.y, u_axis.x) * a_w * u_hair * w + u_axis * a_w * u_hair * .12 * sin(u_t * 1.75 - s * 2.6 + u_ph - 1.2);
  }
  /* Breath: the chest rises a touch above the waist. */
  vec2 ch = p - vec2(650., 660.);
  float wb = exp(-dot(ch, ch) / 60000.);
  p.y -= wb * u_breath * max(0., 860. - p.y) * .012;
  /* Head: turns on the neck; the weight fades out before the shoulders. */
  vec2 rel = a_p - vec2(${NECK[0]}., ${NECK[1]}.);
  float hu = dot(rel, vec2(.875, .483)), hv = dot(rel, vec2(.483, -.875));
  float wh = smoothstep(-15., 45., hv) * (1. - smoothstep(115., 165., abs(hu)));
  p = rot(p, vec2(${NECK[0]}., ${NECK[1]}.), u_head * wh);
  p = rot(p, vec2(650., 900.), u_spin) + u_move;
  v_uv = a_uv; v_p = a_p;
  gl_Position = vec4(p.x / ${W}. * 2. - 1., 1. - p.y / ${H}. * 2., 0., 1.);
}`;

const FS_ALICE = `#version 300 es
precision highp float;
in vec2 v_uv, v_p;
uniform sampler2D u_tex;
uniform float u_blink, u_a;
uniform vec4 u_eyes; /* atlas origin of the closed-eye crop (px), atlas size */
out vec4 o;
void main() {
  vec4 c = texture(u_tex, v_uv);
  if (u_blink > 0.) {
    vec2 e = v_p - vec2(${EYES[0]}., ${EYES[1]}.);
    if (e.x >= 0. && e.y >= 0. && e.x < ${EYES[2]}. && e.y < ${EYES[3]}.)
      c = mix(c, texture(u_tex, (u_eyes.xy + e) / u_eyes.zw), u_blink);
  }
  o = c * (1. - smoothstep(1290., 1400., v_p.y)) * u_a;
}`;

const VS_GLINT = `#version 300 es
in vec4 a_g; /* x, y, strength, phase */
uniform float u_t, u_px, u_a;
uniform vec2 u_off;
out float v_k;
void main() {
  float k = pow(max(0., sin(u_t * (.55 + fract(a_g.w * 7.3) * .5) + a_g.w)), 14.);
  v_k = k * a_g.z * u_a;
  gl_PointSize = (14. + 22. * a_g.z) * u_px * (.6 + .4 * k);
  vec2 p = a_g.xy + u_off;
  gl_Position = vec4(p.x / ${W}. * 2. - 1., 1. - p.y / ${H}. * 2., 0., 1.);
}`;

const FS_GLINT = `#version 300 es
precision mediump float;
in float v_k;
out vec4 o;
void main() {
  vec2 d = abs(gl_PointCoord - .5) * 2.;
  float ray = exp(-d.x * 26.) * (1. - d.y) + exp(-d.y * 26.) * (1. - d.x);
  float s = (ray * .8 + exp(-length(d) * 7.) * .7) * v_k;
  o = vec4(vec3(1., .97, .92) * s, 0.);
}`;

type Rect = [number, number, number, number];
type Hair = { root: [number, number]; axis: [number, number]; len: number; nx: number; ny: number; step: number; w: number[] };
const R = rig as unknown as {
  rects: Record<string, Rect>;
  pos: Record<string, [number, number]>;
  atlas: [number, number];
  hair: Record<'hairL' | 'hairR', Hair>;
  glints: [number, number, number][];
  drops: [number, number][];
  sky: { y0: number; y1: number; l: [number, number]; r: [number, number]; p: number };
};

const load = (src: string) =>
  new Promise<HTMLImageElement>((ok, fail) => {
    const im = new Image();
    im.decoding = 'async';
    im.onload = () => im.decode().then(() => ok(im), () => ok(im));
    im.onerror = fail;
    im.src = BASE + src;
  });

/* Keyframes of the old CSS unfold: [time 0..1, angle°, light]. */
const OPEN: [number, number, number][] = [[0, -70, 0.15], [0.56, 3.2, 1.14], [0.76, -1, 1], [0.9, 0.3, 1], [1, 0, 1]];
const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);
const unfold = (t: number): [number, number, number] => {
  if (t <= 0) return [-70, 0.15, 0];
  if (t >= 1) return [0, 1, 1];
  let i = 0;
  while (t > OPEN[i + 1][0]) i++;
  const [t0, a0, l0] = OPEN[i];
  const [t1, a1, l1] = OPEN[i + 1];
  const k = ease((t - t0) / (t1 - t0));
  return [a0 + (a1 - a0) * k, l0 + (l1 - l0) * k, Math.min(1, t / 0.1)];
};

export interface MirrorRig {
  pointer(nx: number, ny: number): void;
}

export async function startMirror(canvas: HTMLCanvasElement, opts: { skipOpen: () => boolean; onShow: () => void; onLost: () => void }): Promise<MirrorRig> {
  const gl = canvas.getContext('webgl2', { premultipliedAlpha: true, antialias: true, alpha: true });
  if (!gl) throw new Error('webgl2');

  const shader = (type: number, src: string) => {
    const s = gl.createShader(type)!;
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'shader');
    return s;
  };
  const program = (vs: string, fs: string) => {
    const p = gl.createProgram()!;
    gl.attachShader(p, shader(gl.VERTEX_SHADER, vs));
    gl.attachShader(p, shader(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) || 'link');
    const u: Record<string, WebGLUniformLocation | null> = {};
    const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) {
      const name = gl.getActiveUniform(p, i)!.name.replace('[0]', '');
      u[name] = gl.getUniformLocation(p, name);
    }
    return { p, u };
  };
  const pane = program(VS_PANE, FS_PANE);
  const alice = program(VS_ALICE, FS_ALICE);
  const glint = program(VS_GLINT, FS_GLINT);

  const [mirrorIm, aliceIm, fxIm, skyIm] = await Promise.all(['trt-mirror.webp', 'trt-alice.webp', 'trt-fx.webp', 'trt-sky.webp'].map(load));

  const texture = (im: HTMLImageElement, unit: number, { premul = true, mip = true, repeat = false } = {}) => {
    const t = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, premul);
    gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, premul ? gl.BROWSER_DEFAULT_WEBGL : gl.NONE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, im);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, repeat ? gl.REPEAT : gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mip ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR);
    if (mip) gl.generateMipmap(gl.TEXTURE_2D);
  };
  texture(mirrorIm, 0);
  texture(aliceIm, 1);
  texture(fxIm, 2, { premul: false, mip: false });
  texture(skyIm, 3, { mip: false, repeat: true });

  /* Geometry: one quad per pane (rigid, perspective-correct), a grid mesh per Alice layer. */
  const buffer = (data: Float32Array, attribs: [number, number, number][]) => {
    const vao = gl.createVertexArray()!;
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    const stride = attribs.reduce((s, a) => s + a[1], 0) * 4;
    let off = 0;
    for (const [loc, size] of attribs) {
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, stride, off);
      off += size * 4;
    }
    return vao;
  };
  const quad = (x0: number, x1: number) => buffer(new Float32Array([x0, 0, x1, 0, x0, H, x1, H]), [[gl.getAttribLocation(pane.p, 'a_p'), 2, 0]]);
  const panes = [
    { side: 1, vao: quad(0, 460), hinge: HL, dir: 1, delay: 0.2 },
    { side: 2, vao: quad(820, W), hinge: HR, dir: -1, delay: 0.38 },
    { side: 0, vao: quad(240, 1020), hinge: [0, 0], dir: 0, delay: 0 },
  ];

  const [AW, AH] = R.atlas;
  const aP = gl.getAttribLocation(alice.p, 'a_p');
  const aUV = gl.getAttribLocation(alice.p, 'a_uv');
  const aW = gl.getAttribLocation(alice.p, 'a_w');
  const mesh = (name: string, step: number, weights?: number[]) => {
    const [x0, y0, w, h] = R.rects[name];
    const [ax, ay] = R.pos[name];
    const nx = Math.ceil(w / step) + 1;
    const ny = Math.ceil(h / step) + 1;
    const v = new Float32Array(nx * ny * 5);
    for (let j = 0; j < ny; j++)
      for (let i = 0; i < nx; i++) {
        const px = Math.min(i * step, w);
        const py = Math.min(j * step, h);
        const k = (j * nx + i) * 5;
        v.set([x0 + px, y0 + py, (ax + px) / AW, (ay + py) / AH, weights ? weights[j * nx + i] / 100 : 0], k);
      }
    const idx = new Uint16Array((nx - 1) * (ny - 1) * 6);
    let n = 0;
    for (let j = 0; j < ny - 1; j++)
      for (let i = 0; i < nx - 1; i++) {
        const a = j * nx + i;
        idx.set([a, a + 1, a + nx, a + 1, a + nx + 1, a + nx], n);
        n += 6;
      }
    const vao = buffer(v, [[aP, 2, 0], [aUV, 2, 0], [aW, 1, 0]]);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
    return { vao, count: idx.length };
  };
  const body = mesh('body', 20);
  const hairs = (['hairL', 'hairR'] as const).map((k, i) => ({ ...R.hair[k], m: mesh(k, R.hair[k].step, R.hair[k].w), amp: i ? 7 : 9, ph: i * 2.1 }));

  const glints = R.glints.map(([x, y, s], i) => [x, y, s, i * 2.39996]).flat();
  glints.push(GEM[0], GEM[1], 0.8, 0);
  const aG = gl.getAttribLocation(glint.p, 'a_g');
  const glintVao = buffer(new Float32Array(glints), [[aG, 4, 0]]);
  const nGlints = R.glints.length;

  /* State */
  let dpr = 1;
  const resize = () => {
    const r = canvas.getBoundingClientRect();
    dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(r.width * dpr));
    canvas.height = Math.max(1, Math.round(r.height * dpr));
  };
  resize();
  new ResizeObserver(resize).observe(canvas);

  const par = { x: 0, y: 0, tx: 0, ty: 0 };
  const drops = [0, 0, 0].map(() => [0, 0, -99, 0]);
  let nextDrop = 2.6;
  let dropI = 0;
  let blinkAt = 3.5;
  let blinkTwice = false;
  const t0 = performance.now() - (opts.skipOpen() ? 4200 : 0);
  let last = t0;
  let raf = 0;
  let visible = true;
  let shown = false;

  const drawPanes = (t: number) => {
    gl.useProgram(pane.p);
    const u = pane.u;
    gl.uniform1i(u.u_E, 0);
    gl.uniform1i(u.u_fx, 2);
    gl.uniform1i(u.u_sky, 3);
    gl.uniform1f(u.u_t, t);
    gl.uniform1f(u.u_f, 2500);
    gl.uniform4fv(u.u_drop, drops.flat());
    const s = R.sky;
    gl.uniform4f(u.u_skyL, s.l[0], s.l[1], s.y0, s.y1 - s.y0);
    gl.uniform4f(u.u_skyR, s.r[0], s.r[1], s.p, 0);
    gl.uniform1f(u.u_fxOn, Math.min(1, Math.max(0, (t - 2.6) / 1.2)));
    for (const p of panes) {
      let ang = 0;
      let lit = 1;
      let a = 1;
      if (p.side) {
        [ang, lit, a] = unfold((t - p.delay) / 2.8);
      } else {
        a = Math.min(1, t / 0.9);
      }
      gl.uniform1i(u.u_side, p.side);
      gl.uniform2f(u.u_hinge, p.hinge[0], p.hinge[1]);
      gl.uniform1f(u.u_ang, (ang * p.dir * Math.PI) / 180);
      gl.uniform1f(u.u_lit, lit);
      gl.uniform1f(u.u_a, a);
      gl.bindVertexArray(p.vao);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
  };

  const frame = (now: number) => {
    raf = 0;
    if (!visible) return;
    const t = (now - t0) / 1000;
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;

    /* drops on the red glass: random spots inside it, every few seconds */
    if (t > nextDrop) {
      const [x, y] = R.drops[Math.floor(Math.random() * R.drops.length)];
      drops[dropI] = [x + Math.random() * 10, y + Math.random() * 10, t, 0.7 + Math.random() * 0.5];
      dropI = (dropI + 1) % 3;
      nextDrop = t + 2.2 + Math.random() * 2.6;
    }
    /* blinks: every 2.5–6 s, sometimes twice */
    let blink = 0;
    const bt = t - blinkAt;
    if (bt > 0) {
      blink = bt < 0.05 ? bt / 0.05 : bt < 0.11 ? 1 : Math.max(0, 1 - (bt - 0.11) / 0.07);
      if (bt > 0.2) {
        blinkAt = t + (blinkTwice ? 0.18 : 2.5 + Math.random() * 3.5);
        blinkTwice = !blinkTwice && Math.random() < 0.22;
      }
    }
    const k = 1 - Math.exp(-dt * 3);
    par.x += (par.tx - par.x) * k;
    par.y += (par.ty - par.y) * k;

    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    drawPanes(t);

    /* Alice arrives once the wings are open, then floats. */
    const ta = Math.min(1, Math.max(0, (t - 1.6) / 0.75));
    const rise = (1 - ta) ** 3 * 34;
    const head = 0.021 * Math.sin((t * TAU) / 7.3) + 0.008 * Math.sin((t * TAU) / 3.1 + 1);
    const bob = 4 * Math.sin((t * TAU) / 5.6);
    const spin = 0.0035 * Math.sin((t * TAU) / 9.4 + 0.6);
    const mx = par.x * 7;
    const my = par.y * 5 + bob + rise;
    gl.useProgram(alice.p);
    const u = alice.u;
    gl.uniform1i(u.u_tex, 1);
    gl.uniform1f(u.u_t, t);
    gl.uniform1f(u.u_head, head);
    gl.uniform1f(u.u_breath, 0.5 + 0.5 * Math.sin((t * TAU) / 4.4));
    gl.uniform1f(u.u_spin, spin);
    gl.uniform2f(u.u_move, mx, my);
    gl.uniform1f(u.u_a, ta);
    gl.uniform1f(u.u_hair, 0);
    gl.uniform1f(u.u_blink, blink);
    gl.uniform4f(u.u_eyes, R.pos.eyes[0], R.pos.eyes[1], AW, AH);
    gl.bindVertexArray(body.vao);
    gl.drawElements(gl.TRIANGLES, body.count, gl.UNSIGNED_SHORT, 0);
    gl.uniform1f(u.u_blink, 0);
    for (const h of hairs) {
      gl.uniform2f(u.u_root, h.root[0], h.root[1]);
      gl.uniform2f(u.u_axis, h.axis[0], h.axis[1]);
      gl.uniform1f(u.u_len, h.len);
      gl.uniform1f(u.u_hair, h.amp * Math.min(1, ta * 1.5));
      gl.uniform1f(u.u_ph, h.ph);
      gl.bindVertexArray(h.m.vao);
      gl.drawElements(gl.TRIANGLES, h.m.count, gl.UNSIGNED_SHORT, 0);
    }

    /* Glints: stars of the centre glass, then the gem on Alice's brow (follows the head). */
    gl.useProgram(glint.p);
    gl.blendFunc(gl.ONE, gl.ONE);
    gl.uniform1f(glint.u.u_t, t);
    gl.uniform1f(glint.u.u_px, (canvas.width / W) * 1.0);
    gl.uniform1f(glint.u.u_a, Math.min(1, Math.max(0, (t - 3) / 1.5)));
    gl.uniform2f(glint.u.u_off, 0, 0);
    gl.bindVertexArray(glintVao);
    gl.drawArrays(gl.POINTS, 0, nGlints);
    const c = Math.cos(head);
    const s = Math.sin(head);
    const gx = GEM[0] - NECK[0];
    const gy = GEM[1] - NECK[1];
    gl.uniform2f(glint.u.u_off, NECK[0] + c * gx - s * gy - GEM[0] + mx, NECK[1] + s * gx + c * gy - GEM[1] + my);
    gl.uniform1f(glint.u.u_a, ta);
    gl.drawArrays(gl.POINTS, nGlints, 1);

    if (!shown) {
      shown = true;
      opts.onShow();
    }
    raf = requestAnimationFrame(frame);
  };

  const wake = () => {
    if (!raf && visible) {
      last = performance.now();
      raf = requestAnimationFrame(frame);
    }
  };
  new IntersectionObserver(([e]) => {
    visible = e.isIntersecting && !document.hidden;
    wake();
  }).observe(canvas);
  document.addEventListener('visibilitychange', () => {
    visible = !document.hidden;
    wake();
  });
  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    cancelAnimationFrame(raf);
    opts.onLost();
  });
  wake();

  return {
    pointer(nx, ny) {
      par.tx = nx;
      par.ty = ny;
    },
  };
}
