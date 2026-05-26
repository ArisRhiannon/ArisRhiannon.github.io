# PLAN ONIRICO v2.0 — Foco Onirico: Renacimiento

## Estado Actual (v17.0 "Sincronia Pluvial")

**Arquitectura actual:**
- 1 archivo monolitico: `DreamEngine.astro` (215 lineas)
- p5.js v1.9.0 (1MB, modo 2D Canvas) cargado via script tag estatico
- Audio: Web Audio API procedural con brown noise + gotas de lluvia (white noise filtrado con comb filter)
- Visual: forma organica con Perlin noise + arboles fractales recursivos + lluvia 2D basica
- UI: panel glass central con botones Sincronizar/Pausar
- Sin WebGL, sin shaders, sin respuestas a mouse/touch, sin controles de audio

**Problemas identificados:**
1. **p5.js 2D es un cuello de botella** — el render de formas organicas + arboles recursivos por CPU limita la complejidad visual. A 60fps con recursividad depth-6 ya esta en el limite.
2. **Audio simplificado** — solo brown noise + gotas. Falta: granular synthesis, reverb convolution, layers armonicos, binaural.
3. **Monolito** — todo el audio y visual en un solo `<script>` inline. Imposible testear, mantener, o extender.
4. **Sin interactividad del usuario** — el fractal no responde al mouse, no hay controles de intensidad/volumen.
5. **1MB de p5.js para usar ~5% de la API** — desperdicio masivo de bandwidth.
6. **Sin accesibilidad** — no hay teclado, no hay ARIA, no hay modo reducido para epilepsia.
7. **Rain array sin limite** — `rain.push()` sin cap, potencial memory leak en sesiones largas.
8. **Audio cleanup fragil** — el stop() usa setTimeout(3000) en vez de promesas/eventos.

---

## Vision: Foco Onirico v2.0

**Concepto:** Un espacio sonoro-visual inmersivo que responde al usuario. El fractal crece orgánicamente con shaders GPU, el audio envolvente usa granular synthesis + convolution reverb + capas armonicas que pulsan con la respiración del usuario. La lluvia es volumétrica. Todo responde al cursor.

**Influencias SOTA:**
- *The Book of Shaders* (Gonzalez Vivo) — fBM, fractales IFS, domain warping
- *Tero Parviainen* — JavaScript Systems Music, Web Audio scheduling
- *Shadertoy* — Mandelbrot/Julia distance fields, Fractal Wheel, Koch IFS
- *Granular Synthesis* (Curtis Roads, Stanford CCRMA) — grains de audio como particulas
- *p5.js WEBGL mode* — shaders nativos via createShader()/createProgram()

---

## Arquitectura Propuesta

```
src/features/onirico/
  DreamEngine.astro          ← layout + UI + orquestacion
  audio/
    OniricoAudioEngine.ts    ← motor central: context, master, scheduler
    GranularEngine.ts        ← synthesis granular: grains, windows, scatter
    ConvolutionReverb.ts     ← impulse response procedural + convolver node
    HarmonicDrone.ts         ← capas armonicas: binaural, pad, sub-bass
    RainSynth.ts             ← gotas de lluvia mejoradas: comb + resonancia
    AudioPulse.ts            ← LFO central que sincroniza audio <-> visual
  visual/
    OniricoRenderer.ts       ← setup canvas, loop, uniforms, resize
    FractalShader.ts         ← vertex + fragment shaders (fBM + IFS)
    RainSystem.ts            ← particulas de lluvia GPU (instanced)
    GlowPostProcess.ts       ← bloom/blur post-proceso
  ui/
    OniricoControls.ts       ← controles: volumen, intensidad, modo
    BreathSync.ts            ← detector de respiracion via mic / manual
  shaders/
    fractal.vert             ← vertex shader
    fractal.frag             ← fragment: fBM + domain warp + Julia set
    rain.vert                ← rain instanced vertex
    rain.frag                ← rain fragment con refraccion
    bloom.frag               ← post-proceso glow/bloom
    passthrough.vert         ← fullscreen quad vertex
```

**Data flow:**
```
[Usuario: click/respiracion/mouse]
  |
  v
[AudioPulse] -- LFO 0.05-0.2Hz --> [OniricoAudioEngine] --> [GranularEngine]
  |                                      |                    [HarmonicDrone]
  |                                      v                    [RainSynth]
  |                               [OniricoRenderer]          [ConvolutionReverb]
  |                                      |                          |
  |                                      v                          v
  |                               [FractalShader] <-- uniforms --> [masterGain]
  |                               [RainSystem]               --> [destination]
  |                               [GlowPostProcess]
  v
[OniricoControls: volumen, intensidad, modo, respiracion]
```

---

## FASE 1 — Refactor Modular + WebGL Basico

### Objetivo
Romper el monolito, migrar a WebGL con shaders custom, mantener la experiencia actual funcional.

### Tareas

**1.1 Extraer audio a modulos TypeScript**
- `OniricoAudioEngine.ts` — AudioContext, masterGain, scheduler, start/stop
- `RainSynth.ts` — la logica actual de `triggerSatisfyingDrop()` + brown noise base
- Tests unitarios basicos para cada modulo (mock AudioContext)

**1.2 Migrar visual a WebGL con p5.js WEBGL mode**
- Activar `p.createCanvas(w, h, p.WEBGL)` en vez de 2D
- Mover la forma organica a un `createShader()` custom con fBM noise
- Los arboles fractales pasan a ser un shader de distancia (IFS)
- La lluvia pasa a ser un sistema de particulas instanciado

**1.3 Fragment shader fBM (fractal.frag)**
```glsl
// Fragment shader central: domain-warped fBM
// Basado en The Book of Shaders cap. 13-14 + Shadertoy examples
uniform float uTime;
uniform float uPulse;
uniform vec2 uMouse;
uniform vec2 uResolution;

// Simplex noise 3D (Ashima)
// fBM con 6 octavas, lacunarity=2.0, gain=0.5
// Domain warping: pos = fbm(pos + fbm(pos + uTime))
// Color mapping: HSB con pulse -> hue shift
```

**1.4 Rain system GPU**
- Instanced rendering: 1 draw call para todas las gotas
- Cada gota: posicion, velocidad, longitud (attributes)
- Vertex shader: offset por tiempo + gravedad
- Fragment shader: alpha degradado, refraccion sutil

**1.5 UI mejorada**
- Agregar slider de volumen (0-100)
- Agregar slider de intensidad visual (0.1-2.0)
- Agregar toggle "Respiracion" (on/off)
- Accesibilidad: ARIA labels, focus-visible, keyboard nav

**Duracion estimada:** 2-3 dias

---

## FASE 2 — Granular Synthesis + Convolution Reverb

### Objetivo
Evolucionar el audio de "lluvia simple" a un paisaje sonoro envolvente con granular synthesis y reverb procedural.

### Tareas

**2.1 GranularEngine.ts**
- Grains: pequeños fragmentos de audio (20-100ms) con envelopes (Hann, Gaussian)
- 4 texturas de grain:
  - *Lluvia fina* — grains cortos (20-40ms), high density (50-80 grains/s), pitch scatter alto
  - *Niebla* — grains medios (50-150ms), medium density, pitch muy bajo
  - *Campanas* — grains largos (200-500ms), low density, tonales (frecuencias armonicas)
  - *Sub-grave* — grains muy largos (500ms+), frecuencias 40-80Hz, densidad baja
- Scheduling via AudioWorklet (ideal) o lookahead scheduler (fallback)
- Cada grain: BufferSource -> Gain (envelope) -> Filter -> Panner -> master

**2.2 ConvolutionReverb.ts**
- Generar impulse response procedural (no cargar WAV externo):
  - Exponential decay noise burst
  - Longitud: 2-4 segundos
  - Pre-delay: 20-50ms
  - Damping: lowpass que decrece con el tiempo
- ConvolverNode con el IR generado
- Wet/dry mix configurable (0-30% wet por defecto)

**2.3 HarmonicDrone.ts**
- 3 osciladores sinusoidales en relacion armonica (fundamental + 5ta + octava)
- Frecuencia base: 55-110Hz, modulada lentamente por LFO
- Binaural: canal L = base, canal R = base + 4-7Hz (delta/theta beat)
- Gain sub-bass: filtrado a <80Hz, volumen muy bajo (complemento, no feature)
- Envelope: fade-in de 8s, sostenido con tremolo sutil

**2.4 AudioPulse.ts — LFO central**
- Oscilador virtual (no audio node) a 0.05-0.2Hz
- Valor de -1 a +1 disponible para:
  - Modular densidad de grains
  - Modular frecuencia del drone
  - Enviarse como uniform al shader
  - Sincronizar intensidad de lluvia visual
- Modo "respiracion": LFO se sincroniza con clicks del usuario (4s inhale, 4s exhale)

**Duracion estimada:** 3-4 dias

---

## FASE 3 — Fractal Shader Avanzado + Post-Proceso

### Objetivo
Visualmente: domain-warped fractal con Julia set, bloom post-proceso, respuesta al mouse.

### Tareas

**3.1 FractalShader.ts — shader principal mejorado**
- **Capa 1: fBM domain-warped** (fondo organico)
  - 6-8 octavas de noise
  - Domain warping a 2 niveles: `fbm(p + fbm(p + time))`
  - Colores: paleta yume-kawaii mapeada al valor fBM
  - Pulso: uPulse modula la amplitud del warp

- **Capa 2: Julia set fractal** (forma central)
  - Iteraciones: 32-64 (ajustable por intensidad)
  - c parameter animado suavemente por uTime
  - Coloring: orbit trap con gradiente lavender -> cyan -> rosa
  - Distance field para glow en los bordes

- **Capa 3: IFS branching** (estructuras arbolinas)
  - Simplified IFS en fragment shader (no recursion en GLSL)
  - 4 ramas principales, rotadas 90° entre si
  - Profundidad simulada con acumulacion de transparencia
  - Respuesta al mouse: las ramas se curvan hacia uMouse

**3.2 GlowPostProcess.ts — bloom**
- 2-pass gaussian blur (horizontal + vertical)
- Brightness threshold: solo brilla lo >0.7 luminancia
- Blend: screen/additive sobre el render base
- Intensidad proporcional a uPulse

**3.3 Rain system mejorado**
- Lluvia volumetrica: las gotas tienen grosor, no solo lineas
- Splash particles al llegar al borde inferior
- Niebla de fondo: plano de noise semi-transparente que se mueve lentamente
- Densidad modulada por AudioPulse

**3.4 Mouse interactividad**
- El fractal se "distorsiona" donde esta el cursor (domain warp local)
- Las ramas IFS crecen hacia el cursor
- Hover sutil: glow incrementa cerca del cursor
- Touch support: mismo efecto con touch position

**Duracion estimada:** 3-4 dias

---

## FASE 4 — Respiracion + Inmersion + Pulido

### Objetivo
Experiencia completa: sincronizacion respiratoria, optimizacion, pulido visual.

### Tareas

**4.1 BreathSync.ts**
- Modo manual: usuario hace click en "inhalar" y "exhalar"
- Modo guiado: ciclo automatico de 4s inhale / 4s exhale / 4s hold
- El LFO del AudioPulse se sobrescribe con el ciclo respiratorio
- Visual: el fractal "respira" — expande/contrae con cada ciclo
- Audio: los grains se intensifican en exhale, se calman en inhale

**4.2 Micro-interacciones UI**
- Los botones pulsan con el AudioPulse
- Hover effects: glow en los controles
- Slider de volumen con visual feedback
- Transicion suave al entrar/salir de la pagina (fade audio + visual)

**4.3 Optimizacion**
- Eliminar p5.js dependency completa (1MB saved)
- Usar raw WebGL2 + glsl shaders (p5 solo usaba ~5% de la API)
- Canvas resize con devicePixelRatio correcto
- Rain particle cap: max 500 particulas activas
- RequestAnimationFrame con throttle si tab no visible
- Lazy load del motor solo cuando el usuario navega a /onirico

**4.4 Accesibilidad**
- `prefers-reduced-motion`: desactivar fractal animado, mostrar estatico
- `prefers-reduced-motion`: audio sin binaural beats, volumen reducido
- ARIA: role="application", aria-label, controles accesibles
- Keyboard: Space = sync/stop, flechas = volumen/intensidad

**4.5 Cleanup robusto**
- Audio: usar AudioContext.onstatechange en vez de setTimeout
- Visual: cancelAnimationFrame + gl.deleteProgram/deleteShader
- Memory: todas las fuentes de audio se desconectan, rain array se vacia
- Page transition: fade-out de 1s antes de astro:before-swap

**Duracion estimada:** 2-3 dias

---

## Resumen de Technologies SOTA

| Componente | Tecnologia Actual | Tecnologia Propuesta | Razon |
|---|---|---|---|
| Render | p5.js 2D Canvas | WebGL2 + GLSL custom shaders | GPU-accelerado, 10x mas complejidad visual |
| Fractal | Perlin noise + recursion CPU | fBM + domain warp + Julia set (fragment shader) | Tiempo real sin overhead CPU |
| Lluvia | Array de lineas 2D | Instanced particles + splash + niebla | Volumetrica, cientos de gotas a 60fps |
| Post-proceso | Ninguno | Bloom/glow (2-pass blur) | Efecto cinematico, depth |
| Audio base | Brown noise + white noise drops | Granular synthesis (4 texturas) | Paisaje sonoro rico, organico |
| Reverb | Delay comb filter simple | Convolution reverb procedural | Espacio acustico realista |
| Drone | Ninguno | Harmonic + binaural beats | Profundidad, relajacion |
| Sincronizacion | Math.sin pulse basico | LFO central + respiracion sync | Audio-visual coherente, biologico |
| Interactividad | Ninguna | Mouse/touch + controles + respiracion | Experiencia participativa |
| Bundle | p5.min.js 1MB | WebGL2 nativo + GLSL (~5KB shaders) | -99.5% JS, GPU hace el trabajo |

---

## Prioridades de Implementacion

1. **FASE 1** (refactor + WebGL basico) — fundacion sin la cual nada funciona
2. **FASE 2** (granular + reverb) — mayor impacto en experiencia auditiva
3. **FASE 3** (fractal avanzado + bloom) — mayor impacto en experiencia visual
4. **FASE 4** (respiracion + pulido) — diferencia entre "demo" y "producto"

Las fases 2 y 3 son parcialmente paralelizables (audio y visual son independientes).

---

## Consideraciones

- **No usar p5.js en v2.** El 1MB de p5 para usar noise() y createCanvas() no se justifica. WebGL2 esta en 97%+ de navegadores modernos. Los shaders se escriben directo.
- **AudioWorklet para granular synthesis** seria ideal pero requiere un archivo JS separado (security model del browser). Fallback: lookahead scheduler con BufferSource.
- **Convolution reverb procedural** evita cargar un impulse response WAV (ahorra bandwidth). Se genera una vez al inicio.
- **Sin dependencias npm nuevas.** Todo se implementa con APIs nativas del navegador (WebGL2, Web Audio API, requestAnimationFrame).
- **Progressive enhancement.** Si WebGL2 no esta disponible, fallback al render 2D actual (mantener DreamEngine v17 como fallback).
