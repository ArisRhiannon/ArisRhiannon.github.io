/*! TRianThology: the living mirror, a Live2D-style rig of Alice and the three-sided mirror.
    Copyright (C) 2026 Aris Rhiannon
    SPDX-License-Identifier: AGPL-3.0-only

    This program is free software: you can redistribute it and/or modify it under the terms of the GNU
    Affero General Public License as published by the Free Software Foundation, version 3 of the License
    only. It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
    implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
    Public License (LICENSES/AGPL-3.0-only.txt, https://www.gnu.org/licenses/agpl-3.0.html).
    Source: https://github.com/ArisRhiannon/ArisRhiannon.github.io

    Covered: this file, trt-rig.json and the rig maps trt-w.webp and trt-fx.webp. Not covered: the artwork
    and every texture cut or repainted from it (trt-key*, trt-alice, trt-mirror, trt-sky, trt-dial, trt-lid),
    which remain the property of their rights holders (TRianThology, © 07th Expansion). */
/* The three-sided mirror, alive: WebGL2, no dependencies.
   Canvas space is the 1240×1400 cut-out. The wings unfold on their hinge knuckles, then breathe in a night
   wind; the red glass takes drops like still water (rings drawn on the wing's own plane); the starry glass
   twinkles star by star and the clock keeps the visitor's time; the sky glass drifts. Alice floats with
   follow-through in her hair and sleeves, her skirt sways and ripples like cloth, she breathes, turns her
   head in slow looks, blinks with real eyelids, and her irises tremble like wet eyes; once in a while a
   shooting star crosses them. Layers and measurements come from trt-rig.json (built from the key art). */
import rig from './trt-rig.json';

type V2 = [number, number];
type Rect = [number, number, number, number];
type Hair = { root: V2; axis: V2; len: number; nx: number; ny: number; step: number; w: number[] };
type Eye = { a: V2; E: V2; band: [number, number, number]; lid: number[]; shine: [number, number, number, number][]; iris: number[] };
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
/* canvas -> the red glass's own plane (its perspective), where the rings are drawn */
const toPlane = (x: number, y: number): V2 => {
  const h = R.plane.Hi;
  const Z = h[2] * x + h[5] * y + h[8];
  return [(h[0] * x + h[3] * y + h[6]) / Z, (h[1] * x + h[4] * y + h[7]) / Z];
};
/* Face axes (the head is tilted ~29°): along the eyes, and up the face. */
const FH: V2 = [0.875, 0.483];
const FU: V2 = [0.483, -0.875];

const VS_PANE = `#version 300 es
in vec2 a_p;
uniform vec2 u_axis;
uniform float u_ang, u_f, u_sway, u_wside;
out vec2 v_p;
const vec2 C = vec2(${f(W / 2)}, ${f(H / 2)});
/* turn P about the hinge knuckles' axis (through o, along d) */
vec3 hinge(vec3 P, vec3 o, vec3 d, float a) {
  vec3 r = P - o, along = dot(r, d) * d, perp = r - along;
  return o + along + perp * cos(a) + cross(d, perp) * sin(a);
}
void main() {
  vec3 P = vec3(a_p, 0.), o = vec3(u_axis.x, 0., 0.), d = normalize(vec3(u_axis.y, 1., 0.));
  float s = 1.;
  if (u_ang != 0.) {
    /* the unfold: the wing, flat in the picture, turns on its hinge (x = a + k*y) */
    P = hinge(P, o, d, u_ang);
  } else if (u_sway != 0.) {
    /* the night wind: the painted wing stands turned ~45° toward us, so each texel is lifted onto that panel
       (where the ray through it meets it), the panel turns a little on its hinge and is looked at again. The
       wing's width breathes, as a door's does. Plane to plane is one homography, carried exactly by the
       corners' clip w; at rest it is the identity. */
    vec3 E = vec3(C, u_f), e = normalize(vec3(1., -u_axis.y, 0.)) * u_wside;
    vec3 n = cross(d, e + vec3(0., 0., 1.));
    float N = dot(n, o - E), D = dot(n, P - E);
    P = hinge(E + (P - E) * (N / D), o, d, u_sway);
    s = D / N;
  }
  float w = (u_f - P.z) / u_f;
  vec2 q = C + (P.xy - C) / w;
  v_p = a_p;
  gl_Position = vec4((q.x / ${f(W)}) * 2. - 1., 1. - (q.y / ${f(H)}) * 2., 0., 1.) * w * s;
}`;

const FS_PANE = `#version 300 es
precision highp float;
in vec2 v_p;
uniform sampler2D u_E, u_fx, u_sky, u_dial;
uniform int u_side;
uniform float u_t, u_lit, u_a, u_fxOn, u_sway, u_wside;
uniform vec2 u_axis;
uniform vec4 u_drop[4];
uniform mat3 u_Hp, u_Hi;
uniform vec4 u_skyL, u_skyR;
uniform vec2 u_clk;
uniform vec4 u_met;
out vec4 o;
const vec2 SZ = vec2(${f(W)}, ${f(H)});
const vec2 DIAL = ${v2(CLK.c)}, HUB = ${v2(CLK.hub)};
const vec4 DIALP = vec4(${CLK.patch.map(f).join(', ')});
const vec2 TOUCH = ${v2(toPlane(209, 600))}; /* the painted ripple on the moon's reflection */
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
  /* Which pane owns this texel (painted gaps, knuckles kept with the centre), antialiased: the wings are
     always moving a little. Each wing reaches one ramp further, under the centre's (drawn last), so the
     seam never lets the page show through. */
  float own = fx.b, aw = max(fwidth(own), 1e-3);
  float edge = u_side == 1 ? .25 - own : u_side == 2 ? own - .75 : min(own - .25, .75 - own);
  edge = clamp(edge / aw + (u_side == 0 ? .5 : 1.5), 0., 1.);
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
    /* The painted ripple never settles: it is where the glass was touched, and slow rings keep leaving it as
       on a magic surface, while its heart draws in and out a little, as if something were passing into the
       picture, with a faint light. Its rings bend the image strongly and catch the light softly. */
    vec2 tv = q - TOUCH;
    float tr = length(tv) + 1e-3, beat = sin(u_t * 2.4);
    float tw = smoothstep(0., 10., tr) * (1. - smoothstep(64., 104., tr)) * inversesqrt(1. + tr / 18.) * (.8 + .2 * sin(u_t * .83));
    vec2 gt = tv / tr * (cos(tr * .35 - u_t * 2.4) * .34 * tw + tr * exp(-tr * tr / 160.) * .03 * (.75 + .25 * beat));
    vec2 ps = proj(u_Hp, q - (grad + gt) * 5.2), uv2 = ps / SZ;
    float m2 = texture(u_fx, uv2).r;
    c = mix(c, textureGrad(u_E, uv2, dFdx(uv), dFdy(uv)), m * m2);
    grad += gt * .3;
    c.rgb += vec3(1., .86, .93) * exp(-tr * tr / 90.) * (.05 + .03 * beat) * m * c.a;
    /* and the rings catch the evening light: slopes facing it brighten, the far sides dim. Worked out on
       the plane too, so on the smooth orange sky they read as rings lying in the glass. */
    float sh = dot(grad, vec2(.63, .77)) * 2.4;
    c.rgb *= 1. + m * sh / (1. + abs(sh) * 2.2);
    vec3 n = normalize(vec3(-grad * 2.4, 1.));
    float spec = pow(max(0., dot(n, vec3(-.46, -.56, .69))), 36.);
    c.rgb += (vec3(1., .9, .84) * spec * .55 + vec3(1., .95, .9) * flash * .35) * m * c.a;
  } else if (u_side == 0) {
    if (m > 0.) {
      /* Starry glass, alive as a cluster: every painted speck scintillates on its own phase, slow waves of
         light roll through the field so neighbours brighten together, the nebula breathes in drifting swells
         and the galaxy gives off a soft blue glow (the big stars twinkle as sprites in their own pass). */
      const vec3 LUM = vec3(.3, .59, .11);
      float l = dot(c.rgb, LUM);
      vec3 halo = textureLod(u_E, uv, 4.5).rgb;
      float speck = smoothstep(.03, .14, l - dot(textureLod(u_E, uv, 2.5).rgb, LUM));
      float h = fract(sin(dot(floor(v_p / 3.), vec2(12.9898, 78.233))) * 43758.5453), h2 = fract(h * 17.13 + .37);
      float wave = .5 + .5 * sin(dot(v_p, vec2(.043, .025)) - u_t * .8) * sin(dot(v_p, vec2(-.02, .037)) + u_t * .55);
      float tw = sin(u_t * (1.1 + 2.6 * h) + h2 * 6.2831), up = max(tw, 0.);
      c.rgb *= 1. + m * speck * ((.35 + 1.15 * wave * wave) * up * up * up - .25 * max(-tw, 0.));
      float n = sin(dot(v_p, vec2(.0105, .0165)) + u_t * .31) * sin(dot(v_p, vec2(-.0142, .0088)) - u_t * .23 + 1.3);
      c.rgb *= 1. + m * smoothstep(.22, .75, l) * .085 * n;
      float g = dot(halo, LUM) * clamp((halo.b - max(halo.r, halo.g)) * 4., 0., 1.);
      c.rgb += vec3(.55, .66, 1.) * g * g * m * (.26 + .08 * n) * c.a;
      /* now and then, a shooting star behind Alice */
      float age = u_t - u_met.z;
      if (age > 0. && age < .9) {
        vec2 dir = vec2(cos(u_met.w), sin(u_met.w)), head = u_met.xy + dir * age * 260.;
        float along = dot(v_p - head, -dir), side = abs(dot(v_p - head, vec2(-dir.y, dir.x)));
        float tail = 1. - smoothstep(0., 95., along);
        /* the width only grows behind the head: ahead of it a negative width overflowed to NaN (black glass) */
        float s = step(-1.5, along) * tail * exp(-side * side / (.9 + max(along, 0.) * .012)) * sin(3.1416 * age / .9);
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
  if (u_side != 0 && m > 0.) {
    /* As a wing turns the light slides over its glass: a faint sheen that moves out from the hinge as the
       wing opens and back as it closes; nothing at rest. */
    float a = u_sway * u_wside * 57.3;
    float sw = abs(v_p.x - u_axis.x - u_axis.y * v_p.y) + (v_p.y - 700.) * .22 - 150. - a * 50.;
    c.rgb += vec3(1., .96, .92) * exp(-sw * sw / 9000.) * min(abs(a) * .02, .045) * m * c.a;
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
uniform sampler2D u_W, u_fx;
uniform vec2 u_move, u_moveLag, u_root, u_axis;
uniform vec3 u_head;
uniform vec4 u_limb, u_skirt;
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
    /* Forearms swing a hair on the elbows, the skirt on the waist; the lace ripples. */
    vec2 uv = a_p / vec2(${f(W)}, ${f(H)});
    vec3 wt = texture(u_W, uv).rgb;
    p = rotA(p, WAIST, u_limb.x * wt.r);
    p = rotA(p, ELL, u_limb.y * wt.g);
    p = rotA(p, ELR, u_limb.z * wt.b);
    float fl = max(smoothstep(.5, 1., max(wt.g, wt.b)), smoothstep(.55, .95, wt.r) * (1. - smoothstep(1170., 1225., a_p.y)));
    /* The skirt is cloth of its own (fx.g: skirt and petticoat, zero on and around the legs, sleeves and
       hand, which keep their motion): it swings on the waist as a soft pendulum, slow waves run down it,
       out of step from side to side, and the hem frills ripple along; still at the waist, freest at the hem
       (the swing weight). It takes over from the lace ripple there. */
    float sk = texture(u_fx, uv).g;
    p += fl * (1. - sk) * u_limb.w * vec2(sin(dot(a_p, vec2(.021, .013)) - u_t * 1.7), cos(dot(a_p, vec2(-.017, .024)) - u_t * 1.3));
    if (sk > 0.) {
      vec2 r = a_p - WAIST;
      float d = max(length(r), 1.), g = wt.r * sqrt(wt.r), ph = atan(r.x, r.y) * 2.2;
      float wv = sin(u_t * 1.85 - d * .0115 + ph) + .45 * sin(u_t * 2.9 - d * .021 + ph * 1.6 + 1.3);
      float hem = sin(a_p.x * .045 - u_t * 2.3) * smoothstep(.55, 1., wt.r);
      p += sk * g * (rotA(a_p, WAIST, u_skirt.x) - a_p + (vec2(r.y, -r.x) * wv * u_skirt.y + r * hem * u_skirt.z) / d);
    }
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
uniform sampler2D u_tex, u_skin;
uniform float u_a, u_t, u_isHair;
uniform vec2 u_close; /* upper lid, lower lid */
uniform vec4 u_eyeA[2], u_eyeB[2], u_lid[32], u_shine[4];
uniform vec4 u_gaze; /* eye content shift (px), sparkle */
uniform vec4 u_iris[2]; /* iris centre, radii along its axes */
uniform vec2 u_irisR[2], u_trem; /* iris axis; iris tremble (px) */
uniform vec4 u_emet; /* shooting star in the eyes: head progress, head, -, tail */
uniform vec2 u_bodyOff, u_atlas;
out vec4 o;
const vec2 FD = ${v2([-FU[0], -FU[1]])};
const vec4 EYES = vec4(${R.rects.eyes.map(f).join(', ')});
vec4 lidAt(int e, float u) {
  float x = clamp(u, 0., 1.) * 15.;
  int i = int(min(floor(x), 14.));
  return mix(u_lid[e * 16 + i], u_lid[e * 16 + i + 1], x - float(i));
}
vec4 tx(vec2 q, vec2 gx, vec2 gy) { return textureGrad(u_tex, (q + u_bodyOff) / u_atlas, gx, gy); }
/* on the iris ellipse: 0 at its centre, 1 on the rim */
vec2 irisL(int e, vec2 q) {
  vec2 r = u_irisR[e], d = q - u_iris[e].xy;
  return vec2(dot(d, r), dot(d, vec2(-r.y, r.x))) / u_iris[e].zw;
}
/* The iris trembles as Live2D riggers make 瞳揺れ: the pupil and inner iris move by a fraction of a pixel
   while the rim stays put, so one side stretches as the other gives; the whites and lashes never move. */
vec2 tremble(int e, vec2 q) { return (1. - smoothstep(.3, .88, length(irisL(e, q)))) * u_trem; }
/* A shooting star crosses her eyes now and then: one streak of one sky, so the same in both irises (the same
   path across each iris, drawn on the iris's own ellipse, at the same moment), clipped by the iris and hidden
   by the lids. It comes in over one rim and leaves by the other: a small bright head and a fine tail that
   thins and fades behind it. Widths never drop under a screen pixel, so it stays clean when the canvas is small. */
const vec2 EM_A = vec2(1.08, -.42), EM_B = vec2(-1.08, .24);
vec2 irisP(int e, vec2 u) { vec2 r = u_irisR[e]; u *= u_iris[e].zw; return u_iris[e].xy + r * u.x + vec2(-r.y, r.x) * u.y; }
vec3 eyeStar(int e, vec2 p, float fw) {
  float clip = 1. - smoothstep(.82, .96, length(irisL(e, p)));
  vec2 A = irisP(e, EM_A), B = irisP(e, EM_B), dir = normalize(B - A), h = mix(A, B, u_emet.x), r = p - h;
  float along = -dot(r, dir), side = dot(r, vec2(-dir.y, dir.x)), sg = max(.45, .55 * fw);
  float L = min(length(B - A) * .5, length(h - A)) + 1e-3, k = clamp(along / L, 0., 1.), w = sg * (1. - .45 * k);
  float tail = step(0., along) * (1. - k) * (1. - k) * exp(-side * side / (2. * w * w)) * .55 / sg;
  vec2 a = abs(r);
  float fr = 2.4 / max(1., fw);
  float head = exp(-dot(r, r) / (2. * sg * sg)) * .6 / sg + exp(-dot(r, r) / 6.) * .2 + (exp(-a.x * fr - a.y * 1.1) + exp(-a.y * fr - a.x * 1.1)) * .12 / max(1., fw);
  return (vec3(.84, .88, 1.) * tail * u_emet.w + vec3(1., .98, 1.) * head * u_emet.y) * clip;
}
/* Eyelids per pixel, built the way Live2D riggers build a blink: the upper lash line, lashes and all, comes
   straight down the face onto the art's own closed-eye stroke; the lower lid rises to meet it and its lash
   hides under the upper one. The eye is covered, never squashed, and sinks a touch with the lid; the skin the
   lids uncover is the art's closed-eye repaint cleaned of its strokes (top of trt-lid.webp), and in the last
   frames of the close the lids settle into that closed eye itself (bottom half), the stroke as drawn. With the
   lids open the art is untouched but for the gaze. */
vec4 eyeCol(int e, vec2 p, vec2 gx, vec2 gy, out float open) {
  vec2 A = u_eyeA[e].xy, E = u_eyeA[e].zw, d = p - A;
  /* columns run down the face, rows follow the line between the corners */
  float u = (d.x * FD.y - d.y * FD.x) / (E.x * FD.y - E.y * FD.x);
  vec2 o = A + E * u;
  float v = dot(p - o, FD);
  open = 0.;
  vec4 c = tx(p, gx, gy);
  if (u <= 0. || u >= 1.) return c;
  vec4 L = lidAt(e, u); /* upper margin, lash thickness, closing line, lower margin */
  float S = u_eyeB[e].x, Tl = u_eyeB[e].y, Sl = u_eyeB[e].z;
  float dU = (L.z + .6 - L.x) * u_close.x, dL = max(0., L.w + Tl - L.z - .6) * u_close.y;
  float mU = L.x + dU, mL = L.w - dL, tU = L.x - L.y - S, bL = L.w + Tl + Sl;
  if (v < tU - 1. || v > bL + 1.) return c;
  /* edges are antialiased only once a lid moves, so the open eye stays texel-exact */
  float kU = max(smoothstep(0., 1., dU), 1e-3), kL = max(smoothstep(0., 1., dL), 1e-3);
  float bu = clamp((v - mU) / kU + .5, 0., 1.), ab = clamp((mL - v) / kL + .5, 0., 1.);
  vec2 lq = (p - EYES.xy) / EYES.zw * vec2(1., .5);
  vec4 skin = texture(u_skin, lq);
  /* lower lid: skin where its lash has left, then the lash line */
  c = mix(c, skin, (1. - smoothstep(bL - 1., bL + 1., v)) * smoothstep(0., 1.5, dL) * (1. - ab));
  c = mix(c, tx(o + FD * max(v + dL, L.w + .9 * kL), gx, gy), (1. - smoothstep(bL - dL - 1., bL - dL + 1., v)) * (1. - ab));
  /* the eye in the opening */
  open = smoothstep(mU, mU + 1.4, v) * (1. - smoothstep(mL - 1.4, mL, v));
  if (bu * ab > 0.) {
    /* as the lids meet, what shows of the eye falls into the lashes' shadow (a dark slit, not a white one) */
    vec2 q = p - (u_gaze.xy + FD * 1.2 * u_close.x) * open;
    vec4 ec = tx(q - tremble(e, q) * open, gx, gy);
    c = mix(c, vec4(ec.rgb * (1. - .45 * smoothstep(.55, 1., u_close.x)), ec.a), bu * ab);
  }
  /* upper lid on top: its lash thins as it rolls down over the eye (the closed keyform's lash is slimmer)
     and the lid skin above rides on it */
  float th = L.y * .45 * u_close.x, dS = dU + th;
  float sv = v > mU - L.y + th ? L.x - (mU - v) * L.y / (L.y - th) : v - dS;
  c = mix(c, skin, smoothstep(tU - 1., tU + 1., v) * smoothstep(0., 1.5, dS) * (1. - bu));
  c = mix(c, tx(o + FD * min(sv, L.x - kU), gx, gy), smoothstep(tU + dS - 1., tU + dS + 1., v) * (1. - bu));
  float shut = smoothstep(.9, 1., u_close.x) * smoothstep(tU - 1., tU, v) * (1. - smoothstep(bL, bL + 1., v));
  return shut > 0. ? mix(c, texture(u_skin, lq + vec2(0., .5)), shut) : c;
}
void main() {
  vec4 c;
  int eye = -1;
  float open = 0.;
  vec2 gx = dFdx(v_uv), gy = dFdy(v_uv);
  float fw = max(fwidth(v_p).x, fwidth(v_p).y);
  if (u_isHair == 0.) {
    for (int e = 0; e < 2; e++) {
      vec2 d = v_p - (u_eyeA[e].xy + u_eyeA[e].zw * .5);
      if (dot(d, d) < 1700.) { eye = e; break; }
    }
  }
  /* remapped samples keep the mesh's own gradients: no mip seams at the lids */
  c = eye >= 0 ? eyeCol(eye, v_p, gx, gy, open) : texture(u_tex, v_uv);
  if (eye >= 0 && open > 0.) {
    /* Idle shine: the catchlight trembles and breathes like a wet eye, riding the iris tremble a touch
       further than the pupil does (Live2D's ハイライトゆれ); a tiny glint now and then. */
    vec4 s0 = u_shine[eye * 2], s1 = u_shine[eye * 2 + 1];
    float fe = float(eye);
    vec2 wig = vec2(sin(u_t * 1.9 + fe) + .4 * sin(u_t * 4.1 + 2. * fe), cos(u_t * 1.4 + 1.3 + fe)) * .3 + u_gaze.xy + FD * 1.2 * u_close.x + u_trem * 1.25;
    vec2 d0 = v_p - s0.xy - wig, d1 = v_p - s1.xy - wig * 1.5;
    float g0 = exp(-dot(d0, d0) / (s0.z * s0.z)) * (.6 + .4 * sin(u_t * 1.05 + fe * 2.)) * s0.w;
    float g1 = exp(-dot(d1, d1) / (s1.z * s1.z)) * (.5 + .5 * sin(u_t * .53 + 1. + fe)) * s1.w;
    vec2 q = abs(d0);
    float sp = u_gaze.z * (exp(-q.x * 1.5 - q.y * .38) + exp(-q.y * 1.5 - q.x * .38)) * .55;
    c.rgb += vec3(1., .97, 1.) * (g0 + g1 + sp) * open * c.a;
    if (u_emet.y + u_emet.w > 0.) c.rgb += eyeStar(eye, v_p - u_gaze.xy - u_trem, fw) * open * c.a;
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

  const [mirrorIm, aliceIm, fxIm, skyIm, wIm, dialIm, lidIm] = await Promise.all(
    ['trt-mirror.webp', 'trt-alice.webp', 'trt-fx.webp', 'trt-sky.webp', 'trt-w.webp', 'trt-dial.webp', 'trt-lid.webp'].map(load),
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
  texture(lidIm, 6, { mip: false });

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
  const iris = new Float32Array(8);
  const irisR = new Float32Array(4);
  R.eyes.forEach((e, i) => {
    eyeA.set([e.a[0], e.a[1], e.E[0], e.E[1]], i * 4);
    eyeB.set([...e.band, 0], i * 4);
    lids.set(e.lid, i * 64);
    e.shine.forEach((s, k) => shine.set(s, (i * 2 + k) * 4));
    iris.set(e.iris.slice(0, 4), i * 4);
    irisR.set([Math.cos(e.iris[4]), Math.sin(e.iris[4])], i * 2);
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
  /* A shooting star in her eyes, once a cycle (every 19-26 s); no blink ever cuts across it. */
  const EM_T = 1.3;
  let emAt = 11 + Math.random() * 3;
  const blinkNow = (t: number) => {
    if (t > emAt - 0.6 && t < emAt + EM_T + 0.1) {
      nextBlink = emAt + EM_T + 0.25 + Math.random() * 0.8;
      return;
    }
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

  /* Night wind: a slow swell that never repeats, and every 8-15 s a soft gust that reaches the left wing
     first and the right one 0.45 s later. Each wing answers on its hinge like a light door on a soft
     spring (opening a few degrees: its outer edge travels ~5-10 px); the skirt feels the same air a moment
     later. */
  const gusts: V2[] = [];
  let nextGust = 6 + Math.random() * 4;
  const windAt = (t: number) =>
    wave(t, [[0.8, 10.3, 0.4], [0.42, 6.7, 2.2], [0.14, 3.9, 4.4]]) +
    gusts.reduce((s, [g0, a]) => {
      const x = (t - g0) / 1.3;
      return x > 0 ? s + a * x * x * Math.exp(2 - 2 * x) : s;
    }, 0);
  const wingS = [{ x: 0, v: 0 }, { x: 0, v: 0 }];
  const WING = 1.5; /* the wings open by this many degrees per unit of wind */
  const skirtS = { x: 0, v: 0 };

  /* Iris tremble (px, along the face and up it): soft pendulums the lids kick as they reopen and the head
     drags as it turns, over an idle quiver that swells and fades: about a tenth of a pixel, a quarter at
     most when idle, half a pixel just after a blink. */
  const tremS = [{ x: 0, v: 0 }, { x: 0, v: 0 }];
  let lidWas = 0;
  let headWas: V2 | undefined;

  const t0 = performance.now() - (opts.skipOpen() ? 4200 : 0);
  let last = t0;
  let raf = 0;
  let visible = true;
  let shown = false;
  /* dev-only hooks for captures: hold the lids, the wings, the eye star; drop a drop; still the skirt */
  let debug: { blink?: number; wind?: number; emet?: number; trem?: V2; drop?: V2; noSkirt?: boolean; out?: number[] } | undefined;

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
    const state = panes.map((p) => {
      if (!p.side) return [0, 0, 1, Math.min(1, t / 0.9)];
      const [ang, lit, a] = unfold((t - p.delay) / 2.8);
      /* once open, the wing sways in the night wind (eased in), catching a little more light as it opens */
      const sway = (debug?.wind ?? wingS[p.side - 1].x) * smooth((t - p.delay - 2.8) / 3);
      return [ang, sway, lit * (1 + 0.01 * sway), a];
    });
    for (const [i, p] of panes.entries()) {
      const [ang, sway, lit, a] = state[i];
      gl.uniform1i(u.u_side, p.side);
      gl.uniform2f(u.u_axis, p.axis[0], p.axis[1]);
      gl.uniform1f(u.u_ang, (ang * p.dir * Math.PI) / 180);
      gl.uniform1f(u.u_wside, -p.dir);
      gl.uniform1f(u.u_sway, (sway * -p.dir * Math.PI) / 180);
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
    if (debug?.drop) {
      const [qx, qy] = toPlane(debug.drop[0], debug.drop[1]);
      drops[dropI] = [qx, qy, t, 1];
      dropI = (dropI + 1) % 4;
      debug.drop = undefined;
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
    if (debug?.blink !== undefined) lid = debug.blink;
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

    /* the night wind on the wings and the skirt */
    if (t > nextGust) {
      gusts.push([t, 0.6 + Math.random() * 0.6]);
      nextGust = t + 8 + Math.random() * 7;
    }
    while (gusts.length && t - gusts[0][0] > 14) gusts.shift();
    spring(wingS[0], windAt(t) * WING, 2.1, 0.4, dt);
    spring(wingS[1], windAt(t - 0.45) * 0.9 * WING, 2.35, 0.4, dt);
    /* skirt: a soft pendulum on the waist, trailing the float and pushed by the wind (a gust from the left
       swings the hem right); its waves run fuller while the wind blows */
    const air = windAt(t - 0.2);
    spring(skirtS, 0.0014 * (mx - lagS.x.x) - 0.0012 * air, 2.6, 0.3, dt);
    const skirt = debug?.noSkirt ? [0, 0, 0, 0] : [skirtS.x, 1.15 + 0.45 * Math.max(0, air), 0.6, 0];

    /* iris tremble: sub-stepped (the pendulums ring at ~2.7 Hz) */
    const inv = 1 / Math.max(dt, 1e-3);
    const lidV = (lid - lidWas) * inv;
    const headV: V2 = headWas ? [(turn - headWas[0]) * inv, (nod - headWas[1]) * inv] : [0, 0];
    lidWas = lid;
    headWas = [turn, nod];
    const steps = Math.min(12, Math.ceil(dt / 0.008));
    for (let i = 0; i < steps; i++) {
      spring(tremS[0], -0.12 * headV[0], 17, 0.14, dt / steps);
      spring(tremS[1], 0.12 * headV[1] + 0.055 * Math.max(0, -lidV), 17, 0.14, dt / steps);
    }
    const qv = 0.6 + 0.4 * Math.sin((t * TAU) / 7.3);
    const th = tremS[0].x + qv * wave(t, [[0.1, 0.37, 0], [0.07, 0.29, 1.3], [0.045, 0.23, 2.9]]);
    const tu = tremS[1].x + qv * wave(t, [[0.09, 0.33, 0.7], [0.065, 0.41, 2.2], [0.045, 0.26, 4.1]]);
    const trem: V2 = debug?.trem ?? [FH[0] * th + FU[0] * tu, FH[1] * th + FU[1] * tu];

    /* the shooting star in her eyes: in over one rim, out by the other at an even pace; the tail thins out before the head is gone */
    if (t > emAt + EM_T) emAt = t + 19 + Math.random() * 7;
    const ek = debug?.emet ?? (t - emAt) / EM_T;
    const emet = ek > 0 && ek < 1 ? [ek, smooth(ek / 0.06) * (1 - smooth((ek - 0.94) / 0.06)), 0, smooth(ek / 0.12) * (1 - smooth((ek - 0.78) / 0.22))] : [0, 0, 0, 0];
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
    gl.uniform1i(u.u_fx, 2);
    gl.uniform1i(u.u_skin, 6);
    gl.uniform1f(u.u_t, t);
    gl.uniform3f(u.u_head, roll, turn, nod);
    gl.uniform4fv(u.u_limb, limbs);
    gl.uniform4fv(u.u_skirt, skirt);
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
    gl.uniform4fv(u.u_iris, iris);
    gl.uniform2fv(u.u_irisR, irisR);
    gl.uniform2f(u.u_trem, trem[0], trem[1]);
    gl.uniform4fv(u.u_emet, emet);
    gl.uniform2f(u.u_close, lid, lid ** 1.6);
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

    if (import.meta.env.DEV && debug) debug.out = [t, trem[0], trem[1], wingS[0].x, wingS[1].x, skirtS.x, lid, ek];
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
