/* The three-sided mirror, alive: WebGL2, no dependencies.
   Canvas space is the 1240×1400 cut-out. The wings unfold on their hinge knuckles; the red glass takes
   drops like still water (rings drawn on the wing's own plane); the starry glass twinkles star by star
   and the clock keeps the visitor's time; the sky glass drifts. Alice floats with follow-through in her
   hair, sleeves and skirt, breathes, turns her head in slow looks, and blinks with real eyelids.
   Layers and measurements come from trt-rig.json (built from the key art). */
import rig from './trt-rig.json';

type V2 = [number, number];
type Rect = [number, number, number, number];
type Hair = { root: V2; axis: V2; len: number; nx: number; ny: number; step: number; w: number[] };
type Eye = { a: V2; ax: V2; len: number; band: [number, number, number]; lid: number[]; shine: [number, number, number, number][] };
const R = rig as unknown as {
  rects: Record<string, Rect>;
  pos: Record<string, V2>;
  atlas: V2;
  hair: Record<'hairL' | 'hairR', Hair>;
  sky: { y0: number; y1: number; l: V2; r: V2; p: number };
  axes: { L: V2; R: V2 };
  plane: { H: number[]; Hi: number[] };
  drops: V2[];
  stars: [number, number, number, number][];
  clock: { c: V2; hub: V2; r: number; patch: Rect };
  eyes: Eye[];
  body: Record<'neck' | 'neckBase' | 'face' | 'waist' | 'elbowL' | 'elbowR' | 'com' | 'gem', V2>;
};

const W = 1240;
const H = 1400;
const BASE = '/trianthology/';
const TAU = Math.PI * 2;
const f = (x: number) => (Number.isInteger(x) ? x.toFixed(1) : String(x));
const v2 = ([x, y]: V2) => `vec2(${f(x)}, ${f(y)})`;
const B = R.body;
const CLK = R.clock;
/* Face axes (the head is tilted ~29°): along the eyes, and up the face. */
const FH: V2 = [0.875, 0.483];
const FU: V2 = [0.483, -0.875];

const VS_PANE = `#version 300 es
in vec2 a_p;
uniform vec2 u_axis;
uniform float u_ang, u_f;
out vec2 v_p;
void main() {
  vec3 P = vec3(a_p, 0.);
  if (u_ang != 0.) {
    /* rotate about the hinge knuckles' axis, x = a + k*y */
    vec3 o = vec3(u_axis.x, 0., 0.), d = normalize(vec3(u_axis.y, 1., 0.)), r = P - o;
    vec3 along = dot(r, d) * d, perp = r - along;
    P = o + along + perp * cos(u_ang) + cross(d, perp) * sin(u_ang);
  }
  float w = (u_f - P.z) / u_f;
  vec2 c = vec2(${f(W / 2)}, ${f(H / 2)}), q = c + (P.xy - c) / w;
  v_p = a_p;
  gl_Position = vec4((q.x / ${f(W)}) * 2. - 1., 1. - (q.y / ${f(H)}) * 2., 0., 1.) * w;
}`;

const FS_PANE = `#version 300 es
precision highp float;
in vec2 v_p;
uniform sampler2D u_E, u_fx, u_sky, u_dial;
uniform int u_side;
uniform float u_t, u_lit, u_a, u_fxOn, u_rest;
uniform vec4 u_drop[4];
uniform mat3 u_Hp, u_Hi;
uniform vec4 u_skyL, u_skyR;
uniform vec2 u_clk;
uniform vec4 u_met;
out vec4 o;
const vec2 SZ = vec2(${f(W)}, ${f(H)});
const vec2 DIAL = ${v2(CLK.c)}, HUB = ${v2(CLK.hub)};
const vec4 DIALP = vec4(${CLK.patch.map(f).join(', ')});
vec2 rot(vec2 p, float a) { float s = sin(a), c = cos(a); return vec2(c * p.x - s * p.y, s * p.x + c * p.y); }
float seg(vec2 p, vec2 a, vec2 b) { vec2 pa = p - a, ba = b - a; return length(pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0., 1.)); }
/* A clock hand like the painted ones: a fine tapered blade with a small open loop. */
float hand(vec2 d, float ang, float len, float wid, float at, float lr) {
  vec2 q = rot(d, -ang);
  float taper = mix(1., .7, clamp(-q.y / len, 0., 1.));
  float blade = seg(q, vec2(0., 5.), vec2(0., -len)) - wid * .5 * taper;
  float loop = abs(length(q - vec2(0., -at)) - lr) - .75;
  return 1. - smoothstep(-.6, .6, min(blade, loop));
}
vec2 proj(mat3 m, vec2 p) { vec3 q = m * vec3(p, 1.); return q.xy / q.z; }
void main() {
  vec2 uv = v_p / SZ;
  vec4 fx = texture(u_fx, uv);
  /* Which pane owns this texel (painted gaps, knuckles kept with the centre). Hard split at rest, so the
     still mirror is reproduced texel for texel; antialiased while the wings move. */
  float own = fx.b, aw = max(fwidth(own), 1e-3);
  float edge = u_side == 1 ? .25 - own : u_side == 2 ? own - .75 : min(own - .25, .75 - own);
  edge = u_rest > .5 ? step(0., edge) : clamp(edge / aw + .5, 0., 1.);
  if (edge <= 0.) discard;
  vec4 c = texture(u_E, uv);
  float m = fx.r * u_fxOn;
  if (u_side == 1 && m > 0.) {
    /* Red glass: drops ring out on the wing's own plane, so the rings follow its perspective. */
    vec2 q = proj(u_Hi, v_p), grad = vec2(0.);
    float flash = 0.;
    for (int i = 0; i < 4; i++) {
      vec4 dr = u_drop[i];
      float age = u_t - dr.z;
      if (age < 0. || age > 6.) continue;
      vec2 dv = q - dr.xy;
      float r = length(dv) + 1e-3, x = r - age * 44.;
      float env = exp(-x * x / 170.) * exp(-age * .62) * dr.w * inversesqrt(1. + r / 22.);
      float k = .42;
      grad += dv / r * (-k * sin(k * x) - x / 85. * cos(k * x)) * env;
      flash += exp(-r * r / 9.) * max(0., 1. - age / .18) * dr.w;
    }
    grad += vec2(sin(q.y * .045 + u_t * .8), cos(q.x * .05 - u_t * .65)) * .025;
    vec2 ps = proj(u_Hp, q - grad * 5.2), uv2 = ps / SZ;
    float m2 = texture(u_fx, uv2).r;
    c = mix(c, textureGrad(u_E, uv2, dFdx(uv), dFdy(uv)), m * m2);
    vec3 n = normalize(vec3(-grad * 2.4, 1.));
    float spec = pow(max(0., dot(n, vec3(-.46, -.56, .69))), 36.);
    c.rgb += (vec3(1., .9, .84) * spec * .55 + vec3(1., .95, .9) * flash * .35) * m * c.a;
  } else if (u_side == 0) {
    if (m > 0.) {
      /* Starry glass: the nebula breathes in slow drifting swells (the stars twinkle in their own pass). */
      float l = dot(c.rgb, vec3(.3, .59, .11));
      float n = sin(dot(v_p, vec2(.0105, .0165)) + u_t * .31) * sin(dot(v_p, vec2(-.0142, .0088)) - u_t * .23 + 1.3);
      c.rgb *= 1. + m * smoothstep(.22, .75, l) * .085 * n;
      /* now and then, a shooting star behind Alice */
      float age = u_t - u_met.z;
      if (age > 0. && age < .9) {
        vec2 dir = vec2(cos(u_met.w), sin(u_met.w)), head = u_met.xy + dir * age * 260.;
        float along = dot(v_p - head, -dir), side = abs(dot(v_p - head, vec2(-dir.y, dir.x)));
        float tail = 1. - smoothstep(0., 95., along);
        float s = step(-1.5, along) * tail * exp(-side * side / (.9 + along * .012)) * sin(3.1416 * age / .9);
        c.rgb += vec3(.85, .92, 1.) * s * m * .9 * c.a;
      }
    }
    if (length(v_p - DIAL) < ${f(CLK.r + 1)}) {
      /* The painted clock keeps the visitor's time: the dial is repainted without its hands (trt-dial.webp,
         filled in from the dial's own rings), and new hands in the same hand pass under the hub. */
      vec4 pt = texture(u_dial, (v_p - DIALP.xy) / DIALP.zw);
      c = c * (1. - pt.a) + pt;
      vec2 dh = v_p - HUB;
      float hh = max(hand(dh, u_clk.x, 44., 2.5, 25.8, 3.6), hand(dh, u_clk.y, 53., 2.1, 21.7, 4.2));
      vec3 hub = c.rgb;
      c.rgb = mix(mix(c.rgb, vec3(.075, .06, .085) * c.a, hh), hub, 1. - smoothstep(6.9, 8.2, length(dh)));
    }
  } else if (u_side == 2 && m > 0.) {
    /* Sky glass: the painted clouds drift along, looped seamlessly in tile space. */
    float a = u_skyL.x * v_p.y + u_skyL.y, b = u_skyR.x * v_p.y + u_skyR.y;
    vec2 tuv = vec2((v_p.x - a) / (b - a) + u_t * 4.2 / u_skyR.z, (v_p.y - u_skyL.z) / u_skyL.w);
    vec3 sky = texture(u_sky, tuv).rgb;
    c.rgb = mix(c.rgb, sky * c.a, m);
  }
  o = vec4(c.rgb * u_lit, c.a) * edge * u_a;
}`;

/* Painted stars of the centre glass: each keeps its own slow, irregular twinkle; the biggest flare now and
   then. Drawn before Alice, so she hides the ones behind her. */
const VS_STAR = `#version 300 es
in vec4 a_s;
uniform float u_t, u_px, u_a;
out float v_k, v_f;
float h1(float n) { return fract(sin(n * 91.345) * 47453.21); }
void main() {
  float id = float(gl_VertexID), ph = h1(id) * 6.2831, sp = .45 + h1(id + 7.) * .9;
  float tw = .5 + .5 * sin(u_t * sp + ph) * sin(u_t * sp * .63 + ph * 1.7);
  float fl = a_s.z >= 16. ? pow(max(0., sin(u_t * (.13 + h1(id + 3.) * .07) + ph * 3.)), 70.) : 0.;
  v_k = (.15 + .85 * tw * tw) * a_s.w * u_a;
  v_f = fl * u_a;
  gl_PointSize = (5. + sqrt(a_s.z) * 2.6 + fl * 24.) * u_px;
  gl_Position = vec4(a_s.x / ${f(W)} * 2. - 1., 1. - a_s.y / ${f(H)} * 2., 0., 1.);
}`;

const FS_STAR = `#version 300 es
precision mediump float;
in float v_k, v_f;
out vec4 o;
void main() {
  vec2 d = (gl_PointCoord - .5) * 2.;
  vec2 a = abs(d);
  float core = exp(-dot(d, d) * 10.) * v_k * .5;
  float rays = (exp(-a.x * 34.) * (1. - a.y) + exp(-a.y * 34.) * (1. - a.x)) * v_f * .85 + exp(-dot(d, d) * 5.) * v_f * .5;
  o = vec4(vec3(.88, .94, 1.) * (core + rays), 0.);
}`;

const VS_ALICE = `#version 300 es
in vec2 a_p, a_uv;
in float a_w;
uniform sampler2D u_W;
uniform vec2 u_move, u_moveLag, u_root, u_axis;
uniform vec3 u_head;
uniform vec4 u_limb;
uniform float u_t, u_breath, u_hair, u_len, u_ph, u_spin, u_spinLag, u_isHair;
out vec2 v_uv, v_p;
const vec2 NECK = ${v2(B.neck)}, NB = ${v2(B.neckBase)}, FACE = ${v2(B.face)}, WAIST = ${v2(B.waist)};
const vec2 ELL = ${v2(B.elbowL)}, ELR = ${v2(B.elbowR)}, COM = ${v2(B.com)};
const vec2 FH = ${v2(FH)}, FU = ${v2(FU)};
vec2 rotA(vec2 p, vec2 c, float a) { float s = sin(a), k = cos(a); p -= c; return c + vec2(k * p.x - s * p.y, s * p.x + k * p.y); }
void main() {
  vec2 p = a_p;
  float lag = 0.;
  if (u_isHair > 0.) {
    /* A travelling wave down each twintail: still at the tie, freest at the tips. */
    float s = dot(p - u_root, u_axis) / u_len;
    float w = sin(u_t * 1.35 - s * 2.3 + u_ph) + .33 * sin(u_t * 2.2 - s * 3.9 + u_ph * 1.7) + .12 * sin(u_t * 3.7 - s * 6. + u_ph * .4);
    p += vec2(-u_axis.y, u_axis.x) * a_w * u_hair * w + u_axis * a_w * u_hair * .1 * sin(u_t * 1.35 - s * 2.3 + u_ph - 1.2);
    p -= FH * u_head.y * .3 * (1. - a_w);
    lag = a_w;
  } else {
    /* Forearms swing a hair on the elbows, the skirt on the waist; lace and hem ripple. */
    vec3 wt = texture(u_W, a_p / vec2(${f(W)}, ${f(H)})).rgb;
    p = rotA(p, WAIST, u_limb.x * wt.r);
    p = rotA(p, ELL, u_limb.y * wt.g);
    p = rotA(p, ELR, u_limb.z * wt.b);
    float fl = max(smoothstep(.5, 1., max(wt.g, wt.b)), smoothstep(.55, .95, wt.r) * (1. - smoothstep(1170., 1225., a_p.y)));
    p += fl * u_limb.w * vec2(sin(dot(a_p, vec2(.021, .013)) - u_t * 1.7), cos(dot(a_p, vec2(-.017, .024)) - u_t * 1.3));
    lag = max(max(wt.r * .85, max(wt.g, wt.b) * .6), fl);
    /* Breath: the chest rises a touch above the waist. */
    vec2 ch = a_p - vec2(650., 660.);
    p.y -= exp(-dot(ch, ch) / 60000.) * u_breath * max(0., 860. - a_p.y) * .012;
    /* Face: a fake-3D turn and nod, strongest on the features, nothing at the contour. */
    vec2 fr = a_p - FACE;
    float wf = 1. - smoothstep(16., 104., length(vec2(dot(fr, FH), dot(fr, FU) * 1.08)));
    p += (FH * u_head.y + FU * u_head.z) * wf;
  }
  /* Neck: the roll spreads over two joints, the neck base and the skull. */
  vec2 r1 = a_p - NB;
  float w1 = smoothstep(-70., -5., dot(r1, FU)) * (1. - smoothstep(125., 175., abs(dot(r1, FH))));
  vec2 r2 = a_p - NECK;
  float w2 = smoothstep(-15., 45., dot(r2, FU)) * (1. - smoothstep(115., 165., abs(dot(r2, FH))));
  p = rotA(p, NB, u_head.x * .35 * w1);
  p = rotA(p, rotA(NECK, NB, u_head.x * .35), u_head.x * .65 * w2);
  /* Float, with follow-through: the extremities ride a lagged copy of the body's motion. */
  p = rotA(p, COM, mix(u_spin, u_spinLag, lag)) + mix(u_move, u_moveLag, lag);
  v_uv = a_uv;
  v_p = a_p;
  gl_Position = vec4(p.x / ${f(W)} * 2. - 1., 1. - p.y / ${f(H)} * 2., 0., 1.);
}`;

const FS_ALICE = `#version 300 es
precision highp float;
in vec2 v_uv, v_p;
uniform sampler2D u_tex;
uniform float u_a, u_t, u_isHair;
uniform vec4 u_eyeA[2], u_eyeB[2], u_lid[32], u_shine[4];
uniform vec4 u_lids; /* upper closure, lower closure */
uniform vec4 u_gaze; /* eye content shift (px), sparkle */
uniform vec2 u_bodyOff, u_atlas;
out vec4 o;
const vec2 LIDSKIN = ${v2([R.pos.eyes[0] - R.rects.eyes[0], R.pos.eyes[1] - R.rects.eyes[1]])};
vec4 lidAt(int e, float u) {
  float x = clamp(u, 0., 1.) * 15.;
  int i = int(min(floor(x), 14.));
  return mix(u_lid[e * 16 + i], u_lid[e * 16 + i + 1], x - float(i));
}
vec4 tx(vec2 q, vec2 gx, vec2 gy) { return textureGrad(u_tex, (q + u_bodyOff) / u_atlas, gx, gy); }
/* Real eyelids, per pixel, layered like a Live2D model: the lid skin (the art's own closed-eye repaint)
   lies under the eye; the upper lash line slides down over it, lashes and all, to the closing line, and
   the lower one rises a little to meet it. The eye inside the opening is covered, never squashed, and at
   rest every texel is the untouched art. */
vec4 eyeCol(int e, vec2 p, vec2 gx, vec2 gy, out float open) {
  vec2 A = u_eyeA[e].xy, ax = u_eyeA[e].zw, n = vec2(-ax.y, ax.x);
  float len = u_eyeB[e].x, S = u_eyeB[e].y, Tl = u_eyeB[e].z, Sl = u_eyeB[e].w;
  vec2 d = p - A;
  float u = dot(d, ax) / len, v = dot(d, n);
  open = 0.;
  vec4 c = tx(p, gx, gy);
  if (u <= 0. || u >= 1.) return c;
  vec4 L = lidAt(e, u); /* upper margin, lash thickness, closing line, lower margin */
  float dU = (L.z + .6 - L.x) * u_lids.x, dL = (L.w - L.z + .6) * u_lids.y;
  float mU = L.x + dU, mL = L.w - dL, tU = L.x - L.y - S, bL = L.w + Tl + Sl;
  if (v < tU - 1. || v > bL + 1.) return c;
  /* the edges get antialiased only once a lid has moved, so the open eye stays texel-exact */
  float kU = max(smoothstep(0., 1., dU), 1e-3), kL = max(smoothstep(0., 1., dL), 1e-3);
  vec4 skin = textureGrad(u_tex, (p + LIDSKIN) / u_atlas, gx, gy);
  vec2 o = A + ax * (u * len);
  if (v < (mU + mL) * .5) {
    c = mix(c, skin, smoothstep(tU - 1., tU + 1., v) * smoothstep(0., 1.5, dU));
    c = mix(c, tx(o + n * min(v - dU, L.x - kU), gx, gy), smoothstep(tU + dU - 1., tU + dU + 1., v));
  } else {
    c = mix(c, skin, (1. - smoothstep(bL - 1., bL + 1., v)) * smoothstep(0., 1.5, dL));
    c = mix(c, tx(o + n * max(v + dL, L.w + .9 * kL), gx, gy), 1. - smoothstep(bL - dL - 1., bL - dL + 1., v));
  }
  float inside = clamp((v - mU) / kU + .5, 0., 1.) * clamp((mL - v) / kL + .5, 0., 1.);
  open = smoothstep(mU, mU + 1.4, v) * (1. - smoothstep(mL - 1.4, mL, v));
  return inside > 0. ? mix(c, tx(p - u_gaze.xy * open, gx, gy), inside) : c;
}
void main() {
  vec4 c;
  int eye = -1;
  float open = 0.;
  vec2 gx = dFdx(v_uv), gy = dFdy(v_uv);
  if (u_isHair == 0.) {
    for (int e = 0; e < 2; e++) {
      vec2 d = v_p - (u_eyeA[e].xy + u_eyeA[e].zw * (u_eyeB[e].x * .5));
      if (dot(d, d) < 1700.) { eye = e; break; }
    }
  }
  /* remapped samples keep the mesh's own gradients: no mip seams at the lids */
  c = eye >= 0 ? eyeCol(eye, v_p, gx, gy, open) : texture(u_tex, v_uv);
  if (eye >= 0 && open > 0.) {
    /* Idle shine: the catchlight trembles and breathes like a wet eye; a tiny glint now and then. */
    vec4 s0 = u_shine[eye * 2], s1 = u_shine[eye * 2 + 1];
    float fe = float(eye);
    vec2 wig = vec2(sin(u_t * 1.9 + fe) + .4 * sin(u_t * 4.1 + 2. * fe), cos(u_t * 1.4 + 1.3 + fe)) * .3 + u_gaze.xy;
    vec2 d0 = v_p - s0.xy - wig, d1 = v_p - s1.xy - wig * 1.5;
    float g0 = exp(-dot(d0, d0) / (s0.z * s0.z)) * (.6 + .4 * sin(u_t * 1.05 + fe * 2.)) * s0.w;
    float g1 = exp(-dot(d1, d1) / (s1.z * s1.z)) * (.5 + .5 * sin(u_t * .53 + 1. + fe)) * s1.w;
    vec2 q = abs(d0);
    float sp = u_gaze.z * (exp(-q.x * 1.5 - q.y * .38) + exp(-q.y * 1.5 - q.x * .38)) * .55;
    c.rgb += vec3(1., .97, 1.) * (g0 + g1 + sp) * open * c.a;
  }
  o = c * (1. - smoothstep(1290., 1400., v_p.y)) * u_a;
}`;

/* Magic around Alice, as an accent only: slow motes drifting up in two depths, and three faint sparks on a
   tilted orbit that pass behind her and in front, each with a short tail. */
const NMOTE = 96;
const NORB = 3;
const TAIL = 7;
const VS_DUST = `#version 300 es
uniform float u_t, u_px, u_a, u_front;
uniform vec2 u_move;
out float v_k;
out vec3 v_c;
out float v_star;
float h(float n) { return fract(sin(n * 78.233) * 43758.5453); }
const vec2 FACE = ${v2(B.face)};
void main() {
  float id = float(gl_VertexID);
  vec2 p;
  float k, size, star = 0.;
  vec3 col;
  if (id < ${f(NMOTE)}) {
    float front = step(.62, h(id + 11.));
    if (front != u_front) { gl_Position = vec4(2., 2., 0., 1.); gl_PointSize = 0.; v_k = 0.; return; }
    float life = 9. + h(id + 3.) * 7., ph = h(id + 5.);
    float x = fract(u_t / life + ph);
    float ang = h(id) * 6.2831, rad = .55 + .45 * sqrt(h(id + 1.));
    vec2 base = vec2(640., 780.) + vec2(cos(ang) * 470., sin(ang) * 560.) * rad;
    p = base + vec2(sin(u_t * (.23 + h(id + 2.) * .2) + ph * 9.) * 26., -x * (70. + h(id + 4.) * 80.));
    float fade = smoothstep(0., .18, x) * (1. - smoothstep(.7, 1., x));
    float tw = .55 + .45 * sin(u_t * (1.3 + h(id + 6.) * 2.2) + ph * 20.);
    size = mix(2.2, 4.6, h(id + 8.)) * (front > .5 ? 1.5 : 1.);
    k = fade * tw * (front > .5 ? .38 : .5);
    float away = smoothstep(95., 170., length(p - FACE));
    k *= front > .5 ? away : 1.;
    float hue = h(id + 9.);
    col = hue < .55 ? vec3(1., .86, .58) : hue < .8 ? vec3(1., .78, .9) : vec3(.78, .88, 1.);
    p += u_move * (front > .5 ? 1.2 : .6);
  } else {
    float j = id - ${f(NMOTE)}, o = floor(j / ${f(TAIL)}), tl = mod(j, ${f(TAIL)});
    float sp = .045 + o * .012, a = u_t * sp * 6.2831 + o * 2.1 - tl * .03;
    vec2 e = vec2(cos(a) * (430. + o * 40.), sin(a) * (120. + o * 25.));
    float tilt = -.42 + o * .3;
    p = vec2(640., 760. - o * 60.) + vec2(e.x * cos(tilt) - e.y * sin(tilt), e.x * sin(tilt) + e.y * cos(tilt));
    float front = step(0., sin(a));
    if (front != u_front) { gl_Position = vec4(2., 2., 0., 1.); gl_PointSize = 0.; v_k = 0.; return; }
    float head = 1. - tl / ${f(TAIL)};
    size = mix(2., 9., head * head) * (tl < .5 ? 1.6 : 1.);
    k = head * head * .55 * (.75 + .25 * sin(u_t * 3. + o * 2.));
    star = tl < .5 ? 1. : 0.;
    col = vec3(1., .93, .8);
    k *= u_front > .5 ? smoothstep(95., 170., length(p - FACE)) : 1.;
    p += u_move * .8;
  }
  v_k = k * u_a;
  v_c = col;
  v_star = star;
  gl_PointSize = size * u_px * (star > .5 ? 3.2 : 1.);
  gl_Position = vec4(p.x / ${f(W)} * 2. - 1., 1. - p.y / ${f(H)} * 2., 0., 1.);
}`;

const FS_DUST = `#version 300 es
precision mediump float;
in float v_k;
in vec3 v_c;
in float v_star;
out vec4 o;
void main() {
  vec2 d = (gl_PointCoord - .5) * 2.;
  float r2 = dot(d, d);
  float s;
  if (v_star > .5) {
    vec2 a = abs(d);
    s = (exp(-a.x * 16. - a.y * 2.2) + exp(-a.y * 16. - a.x * 2.2)) * .8 + exp(-r2 * 14.) * .9;
  } else {
    s = exp(-r2 * 4.) * .75 + exp(-r2 * 16.) * .6;
  }
  o = vec4(v_c * s * v_k, 0.);
}`;

const VS_GLINT = `#version 300 es
in vec4 a_g;
uniform float u_t, u_px, u_a;
uniform vec2 u_off;
out float v_k;
void main() {
  float k = pow(max(0., sin(u_t * (.55 + fract(a_g.w * 7.3) * .5) + a_g.w)), 14.);
  v_k = k * a_g.z * u_a;
  gl_PointSize = (14. + 22. * a_g.z) * u_px * (.6 + .4 * k);
  vec2 p = a_g.xy + u_off;
  gl_Position = vec4(p.x / ${f(W)} * 2. - 1., 1. - p.y / ${f(H)} * 2., 0., 1.);
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

const load = (src: string) =>
  new Promise<HTMLImageElement>((ok, fail) => {
    const im = new Image();
    im.decoding = 'async';
    im.onload = () => im.decode().then(() => ok(im), () => ok(im));
    im.onerror = fail;
    im.src = BASE + src;
  });

/* Keyframes of the unfold: [time 0..1, angle°, light]. */
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

/* Layered sines with incommensurate periods [amplitude, period s, phase]: never repeats, never jerks. */
const wave = (t: number, spec: number[][]) => spec.reduce((s, [a, p, ph]) => s + a * Math.sin((t * TAU) / p + ph), 0);
type Spring = { x: number; v: number };
const spring = (s: Spring, target: number, w: number, zeta: number, dt: number) => {
  s.v += (w * w * (target - s.x) - 2 * zeta * w * s.v) * dt;
  s.x += s.v * dt;
};
const smooth = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

/* One blink, shaped after high-speed recordings (fast close, short hold, quick then slow reopening) and
   Live2D's default timing (close 0.1 s, closed 0.05 s, open 0.15 s). Returns the lid closure 0..1. */
type Blink = { t0: number; close: number; hold: number; open: number };
const lidOf = (b: Blink, t: number) => {
  const x = t - b.t0;
  if (x <= 0) return 0;
  if (x < b.close) return smooth(x / b.close);
  if (x < b.close + b.hold) return 1;
  const y = x - b.close - b.hold;
  if (y < b.open) return 1 - 0.965 * (1 - (1 - y / b.open) ** 2.1);
  return 0.035 * Math.exp(-(y - b.open) / 0.09);
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
  const star = program(VS_STAR, FS_STAR);
  const dust = program(VS_DUST, FS_DUST);
  const glint = program(VS_GLINT, FS_GLINT);

  const [mirrorIm, aliceIm, fxIm, skyIm, wIm, dialIm] = await Promise.all(
    ['trt-mirror.webp', 'trt-alice.webp', 'trt-fx.webp', 'trt-sky.webp', 'trt-w.webp', 'trt-dial.webp'].map(load),
  );

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
  texture(wIm, 4, { premul: false, mip: false });
  texture(dialIm, 5, { mip: false });

  const buffer = (data: Float32Array, attribs: [number, number][]) => {
    const vao = gl.createVertexArray()!;
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    const stride = attribs.reduce((s, a) => s + a[1], 0) * 4;
    let off = 0;
    for (const [loc, size] of attribs) {
      if (loc >= 0) {
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, size, gl.FLOAT, false, stride, off);
      }
      off += size * 4;
    }
    return vao;
  };
  const quad = (x0: number, x1: number) => buffer(new Float32Array([x0, 0, x1, 0, x0, H, x1, H]), [[gl.getAttribLocation(pane.p, 'a_p'), 2]]);
  const panes = [
    { side: 1, vao: quad(0, 470), axis: R.axes.L, dir: 1, delay: 0.2 },
    { side: 2, vao: quad(810, W), axis: R.axes.R, dir: -1, delay: 0.38 },
    { side: 0, vao: quad(240, 1020), axis: [0, 0] as V2, dir: 0, delay: 0 },
  ];

  const [AW, AH] = R.atlas;
  const aP = gl.getAttribLocation(alice.p, 'a_p');
  const aUV = gl.getAttribLocation(alice.p, 'a_uv');
  const aW = gl.getAttribLocation(alice.p, 'a_w');
  const mesh = (name: string, step: number, weights?: number[], wstep = step) => {
    const [x0, y0, w, h] = R.rects[name];
    const [ax, ay] = R.pos[name];
    const nx = Math.ceil(w / step) + 1;
    const ny = Math.ceil(h / step) + 1;
    const wx = weights ? Math.ceil(w / wstep) + 1 : 0;
    const wy = weights ? Math.ceil(h / wstep) + 1 : 0;
    const wAt = (px: number, py: number) => {
      if (!weights) return 0;
      /* bilinear in the coarser weight grid */
      const gx = Math.min(px / wstep, wx - 1.001);
      const gy = Math.min(py / wstep, wy - 1.001);
      const i = Math.floor(gx);
      const j = Math.floor(gy);
      const fx = gx - i;
      const fy = gy - j;
      const q = (a: number, b: number) => weights[Math.min(b, wy - 1) * wx + Math.min(a, wx - 1)];
      return ((q(i, j) * (1 - fx) + q(i + 1, j) * fx) * (1 - fy) + (q(i, j + 1) * (1 - fx) + q(i + 1, j + 1) * fx) * fy) / 100;
    };
    const v = new Float32Array(nx * ny * 5);
    for (let j = 0; j < ny; j++)
      for (let i = 0; i < nx; i++) {
        const px = Math.min(i * step, w);
        const py = Math.min(j * step, h);
        v.set([x0 + px, y0 + py, (ax + px) / AW, (ay + py) / AH, wAt(px, py)], (j * nx + i) * 5);
      }
    const idx = new Uint32Array((nx - 1) * (ny - 1) * 6);
    let n = 0;
    for (let j = 0; j < ny - 1; j++)
      for (let i = 0; i < nx - 1; i++) {
        const a = j * nx + i;
        idx.set([a, a + 1, a + nx, a + 1, a + nx + 1, a + nx], n);
        n += 6;
      }
    const vao = buffer(v, [[aP, 2], [aUV, 2], [aW, 1]]);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
    return { vao, count: idx.length };
  };
  const body = mesh('body', 10);
  const hairs = (['hairL', 'hairR'] as const).map((k, i) => ({ ...R.hair[k], m: mesh(k, 10, R.hair[k].w, R.hair[k].step), amp: i ? 7 : 9, ph: i * 2.1 }));

  const starVao = buffer(new Float32Array(R.stars.flat()), [[gl.getAttribLocation(star.p, 'a_s'), 4]]);
  const gemVao = buffer(new Float32Array([B.gem[0], B.gem[1], 0.8, 0]), [[gl.getAttribLocation(glint.p, 'a_g'), 4]]);
  const dustVao = gl.createVertexArray()!;
  const NDUST = NMOTE + NORB * TAIL;

  /* Eyes: static uniforms. */
  const eyeA = new Float32Array(8);
  const eyeB = new Float32Array(8);
  const lids = new Float32Array(128);
  const shine = new Float32Array(16);
  R.eyes.forEach((e, i) => {
    eyeA.set([e.a[0], e.a[1], e.ax[0], e.ax[1]], i * 4);
    eyeB.set([e.len, ...e.band], i * 4);
    lids.set(e.lid, i * 64);
    e.shine.forEach((s, k) => shine.set(s, (i * 2 + k) * 4));
  });

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

  const Hi = R.plane.Hi;
  const toPlane = (x: number, y: number): V2 => {
    const X = Hi[0] * x + Hi[3] * y + Hi[6];
    const Y = Hi[1] * x + Hi[4] * y + Hi[7];
    const Z = Hi[2] * x + Hi[5] * y + Hi[8];
    return [X / Z, Y / Z];
  };
  const par = { x: 0, y: 0, tx: 0, ty: 0 };
  const drops = [0, 0, 0, 0].map(() => [0, 0, -99, 0]);
  let nextDrop = 2.9;
  let dropI = 0;
  let lastSpot = -1;
  const met = [0, 0, -99, 0];
  let nextMet = 9 + Math.random() * 6;

  const blinks: Blink[] = [];
  const newBlink = (t0: number, quick = false): Blink => ({
    t0,
    close: (quick ? 0.07 : 0.08) + Math.random() * 0.025,
    hold: 0.035 + Math.random() * 0.03,
    open: (quick ? 0.14 : 0.16) + Math.random() * 0.04,
  });
  let nextBlink = 3.4;
  const blinkNow = (t: number) => {
    const b = newBlink(t);
    blinks.push(b);
    /* sometimes a second one right behind, when the lid is nearly up again */
    if (Math.random() < 0.2) blinks.push(newBlink(t + b.close + b.hold + b.open * 0.85, true));
    nextBlink = t + 1.8 + 5.2 * Math.random() ** 1.3;
  };
  let sparkAt = 6 + Math.random() * 5;

  /* Looks: every few seconds the head eases to a new small pose; the eyes lead, a blink often rides along. */
  const look = { roll: 0, tx: 0, ty: 0 };
  const lookS = { roll: { x: 0, v: 0 }, tx: { x: 0, v: 0 }, ty: { x: 0, v: 0 } };
  let nextLook = 5 + Math.random() * 4;
  const gaze = { x: 0, y: 0, tx: 0, ty: 0, lead: { x: 0, y: 0 } };
  let nextSacc = 1.2;
  const lagS = { x: { x: 0, v: 0 }, y: { x: 0, v: 0 }, s: { x: 0, v: 0 } };

  const t0 = performance.now() - (opts.skipOpen() ? 4200 : 0);
  let last = t0;
  let raf = 0;
  let visible = true;
  let shown = false;
  let debug: { blink?: number; lower?: number } | undefined;

  const drawPanes = (t: number) => {
    gl.useProgram(pane.p);
    const u = pane.u;
    gl.uniform1i(u.u_E, 0);
    gl.uniform1i(u.u_fx, 2);
    gl.uniform1i(u.u_sky, 3);
    gl.uniform1i(u.u_dial, 5);
    gl.uniform1f(u.u_t, t);
    gl.uniform1f(u.u_f, 2500);
    gl.uniform4fv(u.u_drop, drops.flat());
    gl.uniformMatrix3fv(u.u_Hp, false, R.plane.H);
    gl.uniformMatrix3fv(u.u_Hi, false, R.plane.Hi);
    const s = R.sky;
    gl.uniform4f(u.u_skyL, s.l[0], s.l[1], s.y0, s.y1 - s.y0);
    gl.uniform4f(u.u_skyR, s.r[0], s.r[1], s.p, 0);
    gl.uniform1f(u.u_fxOn, Math.min(1, Math.max(0, (t - 2.6) / 1.2)));
    gl.uniform4fv(u.u_met, met);
    /* the visitor's time; the minute hand steps each minute with a small mechanical overshoot */
    const d = new Date();
    const sec = d.getSeconds() + d.getMilliseconds() / 1000;
    const k = Math.min(1, sec / 0.5);
    const step = k < 1 ? 1 + 2.4 * (k - 1) ** 3 + 1.4 * (k - 1) ** 2 : 1;
    const min = d.getMinutes() - 1 + step;
    gl.uniform2f(u.u_clk, (((d.getHours() % 12) + d.getMinutes() / 60) / 12) * TAU, (min / 60) * TAU);
    const state = panes.map((p) => (p.side ? unfold((t - p.delay) / 2.8) : [0, 1, Math.min(1, t / 0.9)]));
    gl.uniform1f(u.u_rest, state.every((s) => s[0] === 0) ? 1 : 0);
    for (const [i, p] of panes.entries()) {
      const [ang, lit, a] = state[i];
      gl.uniform1i(u.u_side, p.side);
      gl.uniform2f(u.u_axis, p.axis[0], p.axis[1]);
      gl.uniform1f(u.u_ang, (ang * p.dir * Math.PI) / 180);
      gl.uniform1f(u.u_lit, lit);
      gl.uniform1f(u.u_a, a);
      gl.bindVertexArray(p.vao);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
  };

  const drawDust = (t: number, front: number, a: number, mv: V2) => {
    gl.useProgram(dust.p);
    gl.uniform1f(dust.u.u_t, t);
    gl.uniform1f(dust.u.u_px, canvas.width / W);
    gl.uniform1f(dust.u.u_a, a);
    gl.uniform1f(dust.u.u_front, front);
    gl.uniform2f(dust.u.u_move, mv[0], mv[1]);
    gl.bindVertexArray(dustVao);
    gl.drawArrays(gl.POINTS, 0, NDUST);
  };

  const frame = (now: number) => {
    raf = 0;
    if (!visible) return;
    const t = (now - t0) / 1000;
    const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
    last = now;
    if (import.meta.env.DEV) debug = (window as unknown as { __trt?: typeof debug }).__trt;

    /* drops on the red glass: open spots, never the same twice running */
    if (t > nextDrop) {
      let i = Math.floor(Math.random() * R.drops.length);
      if (i === lastSpot) i = (i + 1) % R.drops.length;
      lastSpot = i;
      const [x, y] = R.drops[i];
      const [qx, qy] = toPlane(x + (Math.random() - 0.5) * 8, y + (Math.random() - 0.5) * 8);
      drops[dropI] = [qx, qy, t, 0.75 + Math.random() * 0.45];
      dropI = (dropI + 1) % 4;
      nextDrop = t + 2.1 + Math.random() * 2.8;
    }
    if (t > nextMet) {
      met[0] = 470 + Math.random() * 360;
      met[1] = 300 + Math.random() * 260;
      met[2] = t;
      met[3] = (Math.random() < 0.5 ? 0.45 : Math.PI - 0.45) + (Math.random() - 0.5) * 0.3;
      nextMet = t + 16 + Math.random() * 14;
    }

    /* head: slow layered drift plus looks */
    if (t > nextLook) {
      const pr = [look.roll, look.tx, look.ty];
      look.roll = (Math.random() - 0.5) * 0.024;
      look.tx = (Math.random() - 0.5) * 2.6;
      look.ty = (Math.random() - 0.5) * 1.6;
      gaze.lead.x = Math.max(-0.9, Math.min(0.9, (look.tx - pr[1]) * 0.45)) * FH[0];
      gaze.lead.y = Math.max(-0.9, Math.min(0.9, (look.tx - pr[1]) * 0.45)) * FH[1] + (look.ty - pr[2]) * 0.3;
      if (Math.random() < 0.55 && t - (blinks.length ? blinks[blinks.length - 1].t0 : -9) > 1.2) blinkNow(t + 0.05);
      nextLook = t + 6 + Math.random() * 7;
    }
    spring(lookS.roll, look.roll, 1.9, 0.86, dt);
    spring(lookS.tx, look.tx, 1.9, 0.86, dt);
    spring(lookS.ty, look.ty, 1.9, 0.86, dt);
    const roll = wave(t, [[0.011, 13.1, 0.4], [0.006, 7.9, 2.1], [0.0028, 4.3, 4]]) + lookS.roll.x;
    const turn = wave(t, [[0.9, 11.7, 1.3], [0.45, 6.1, 0.2]]) + lookS.tx.x;
    const nod = wave(t, [[0.55, 9.3, 2.6], [0.28, 5.2, 1.1]]) + lookS.ty.x;

    /* eyes: fixational micro-saccades, plus the lead into each look (decays as the head arrives) */
    if (t > nextSacc) {
      const a = Math.random() * TAU;
      const r = 0.12 + Math.random() * 0.25;
      gaze.tx = Math.cos(a) * r;
      gaze.ty = Math.sin(a) * r;
      nextSacc = t + 0.9 + Math.random() * 2.2;
    }
    const sk = 1 - Math.exp(-dt * 40);
    gaze.x += (gaze.tx - gaze.x) * sk;
    gaze.y += (gaze.ty - gaze.y) * sk;
    const lk = Math.exp(-dt * 1.4);
    gaze.lead.x *= lk;
    gaze.lead.y *= lk;

    /* blinks */
    if (t > nextBlink) blinkNow(t);
    let lid = 0;
    for (const b of blinks) lid = Math.max(lid, lidOf(b, t));
    while (blinks.length && t - blinks[0].t0 > 1.2) blinks.shift();
    let lower = lid ** 1.6;
    if (debug?.blink !== undefined) {
      lid = debug.blink;
      lower = debug.lower ?? lid ** 1.6;
    }
    if (t > sparkAt + 0.5) sparkAt = t + 5 + Math.random() * 6;
    const sparkle = t > sparkAt ? Math.sin((Math.PI * (t - sparkAt)) / 0.5) ** 2 : 0;

    /* float: buoyant and slow; the lean follows the drift, the extremities follow late */
    const fx = wave(t, [[2.1, 12.9, 0.7], [0.8, 7.7, 2.9]]);
    const fy = wave(t, [[4.2, 8.3, 0], [1.3, 13.7, 1.2], [0.5, 5.1, 2.3]]);
    const vx = wave(t + 0.25, [[2.1, 12.9, 0.7], [0.8, 7.7, 2.9]]) - wave(t - 0.25, [[2.1, 12.9, 0.7], [0.8, 7.7, 2.9]]);
    const spin = 0.0045 * vx + wave(t, [[0.0012, 17.3, 1.9]]);
    const k = 1 - Math.exp(-dt * 3);
    par.x += (par.tx - par.x) * k;
    par.y += (par.ty - par.y) * k;
    const ta = Math.min(1, Math.max(0, (t - 1.6) / 0.75));
    const rise = (1 - ta) ** 3 * 34;
    const mx = par.x * 7 + fx;
    const my = par.y * 5 + fy + rise;
    spring(lagS.x, mx, 3.4, 1, dt);
    spring(lagS.y, my, 3.4, 1, dt);
    spring(lagS.s, spin, 3.4, 1, dt);
    const breath = 0.5 + 0.5 * Math.sin((t * TAU) / 4.2);
    const limbs = [
      wave(t, [[0.0022, 5.9, 1], [0.0012, 3.3, 2.5]]) + (mx - lagS.x.x) * 0.0006,
      wave(t, [[0.0048, 6.7, 0.3], [0.0021, 3.9, 1.7]]) - breath * 0.0018,
      wave(t, [[0.0042, 7.3, 2.2], [0.0019, 4.4, 0.4]]) + breath * 0.0012,
      1.05,
    ];

    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    drawPanes(t);

    /* painted stars, behind Alice */
    gl.blendFunc(gl.ONE, gl.ONE);
    gl.useProgram(star.p);
    gl.uniform1f(star.u.u_t, t);
    gl.uniform1f(star.u.u_px, canvas.width / W);
    gl.uniform1f(star.u.u_a, Math.min(1, Math.max(0, (t - 2.8) / 1.5)));
    gl.bindVertexArray(starVao);
    gl.drawArrays(gl.POINTS, 0, R.stars.length);
    const dustA = Math.min(1, Math.max(0, (t - 3.2) / 2.5));
    drawDust(t, 0, dustA, [mx, my]);

    /* Alice arrives once the wings are open, then floats. */
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(alice.p);
    const u = alice.u;
    gl.uniform1i(u.u_tex, 1);
    gl.uniform1i(u.u_W, 4);
    gl.uniform1f(u.u_t, t);
    gl.uniform3f(u.u_head, roll, turn, nod);
    gl.uniform4fv(u.u_limb, limbs);
    gl.uniform1f(u.u_breath, breath);
    gl.uniform1f(u.u_spin, spin);
    gl.uniform1f(u.u_spinLag, lagS.s.x);
    gl.uniform2f(u.u_move, mx, my);
    gl.uniform2f(u.u_moveLag, lagS.x.x, lagS.y.x);
    gl.uniform1f(u.u_a, ta);
    gl.uniform4fv(u.u_eyeA, eyeA);
    gl.uniform4fv(u.u_eyeB, eyeB);
    gl.uniform4fv(u.u_lid, lids);
    gl.uniform4fv(u.u_shine, shine);
    gl.uniform4f(u.u_lids, lid, lower, 0, 0);
    gl.uniform4f(u.u_gaze, gaze.x + gaze.lead.x, gaze.y + gaze.lead.y, sparkle, 0);
    gl.uniform2f(u.u_bodyOff, R.pos.body[0] - R.rects.body[0], R.pos.body[1] - R.rects.body[1]);
    gl.uniform2f(u.u_atlas, AW, AH);
    gl.uniform1f(u.u_isHair, 0);
    gl.uniform1f(u.u_hair, 0);
    gl.bindVertexArray(body.vao);
    gl.drawElements(gl.TRIANGLES, body.count, gl.UNSIGNED_INT, 0);
    gl.uniform1f(u.u_isHair, 1);
    for (const h of hairs) {
      gl.uniform2f(u.u_root, h.root[0], h.root[1]);
      gl.uniform2f(u.u_axis, h.axis[0], h.axis[1]);
      gl.uniform1f(u.u_len, h.len);
      gl.uniform1f(u.u_hair, h.amp * Math.min(1, ta * 1.5));
      gl.uniform1f(u.u_ph, h.ph);
      gl.bindVertexArray(h.m.vao);
      gl.drawElements(gl.TRIANGLES, h.m.count, gl.UNSIGNED_INT, 0);
    }

    /* the gem on Alice's brow catches the light (it rides the head) */
    gl.blendFunc(gl.ONE, gl.ONE);
    gl.useProgram(glint.p);
    gl.uniform1f(glint.u.u_t, t);
    gl.uniform1f(glint.u.u_px, canvas.width / W);
    gl.uniform1f(glint.u.u_a, ta);
    const rotP = (p: V2, c: V2, a: number): V2 => {
      const s = Math.sin(a);
      const q = Math.cos(a);
      return [c[0] + q * (p[0] - c[0]) - s * (p[1] - c[1]), c[1] + s * (p[0] - c[0]) + q * (p[1] - c[1])];
    };
    let g = rotP(B.gem, B.neckBase, roll * 0.35);
    g = rotP(g, rotP(B.neck, B.neckBase, roll * 0.35), roll * 0.65);
    g = rotP(g, B.com, spin);
    gl.uniform2f(glint.u.u_off, g[0] - B.gem[0] + mx, g[1] - B.gem[1] + my);
    gl.bindVertexArray(gemVao);
    gl.drawArrays(gl.POINTS, 0, 1);
    drawDust(t, 1, dustA, [mx, my]);

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
