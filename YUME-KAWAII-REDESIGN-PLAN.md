# Yume Kawaii Redesign — misitio

**Aesthetic:** Fairy kei / yume kawaii japonés. Khaki pastel, rosa desaturado, malva, crema. Suave, no empalagoso. Calidad de estudio de diseño.

---

## 0. Paleta

Base: khaki pastel desaturado. Rosa como acento discreto, no como grito.

```
:root {
  /* Superficies */
  --color-bg:        #F5F0E8;   /* khaki pastel — el fondo principal */
  --color-surface:   #FAF7F2;   /* cards — crema calido */
  --color-surface-2: #F0EBE1;   /* hover — khaki un tono mas profundo */
  --color-sidebar:   #EDE7DC;   /* sidebar — khaki suave */
  --color-topbar:    #F5F0E8;   /* topbar — match fondo */

  /* Tinta */
  --color-ink:       #3D3630;   /* marron tibio — nunca negro puro */
  --color-ink-soft:  #5C524A;   /* secundario */
  --color-muted:     #9E9183;   /* texto terciario, labels */
  --color-muted-2:   #B5A99C;   /* placeholder, disabled */

  /* Acentos — rosa desaturado, nunca vibrante */
  --color-accent:    #D4A5A5;   /* rosa empolvado — botones, active */
  --color-accent-2:  #E2C4C4;   /* rosa mas claro — badges, deco */
  --color-accent-hi: #C48B8B;   /* rosa un poco mas vivo — solo highlights */
  --color-lavender:  #C9B8D4;   /* malva suave — secondary accent */
  --color-sage:      #B5C2A8;   /* sage green — online status */

  /* Bordes */
  --color-border:        rgba(61,54,48,0.08);
  --color-border-accent: rgba(212,165,165,0.25);
  --color-border-card:   rgba(61,54,48,0.06);

  /* Sombras — neutras, calidas */
  --shadow-sm:  0 1px 3px rgba(61,54,48,0.06), 0 1px 6px rgba(61,54,48,0.04);
  --shadow-md:  0 2px 8px rgba(61,54,48,0.08), 0 4px 16px rgba(61,54,48,0.05);
  --shadow-card: 0 2px 12px rgba(61,54,48,0.07), 0 1px 3px rgba(61,54,48,0.05);
  --glow-sm:    0 2px 10px rgba(212,165,165,0.15);
  --glow-md:    0 4px 20px rgba(212,165,165,0.22);

  /* Tipografia */
  --font-display: 'Zen Maru Gothic', 'Quicksand', sans-serif;
  --font-body:    'Zen Maru Gothic', 'Nunito', system-ui, sans-serif;
  --font-mono:    'Quicksand', monospace;
  --font-deco:    'Kaisei Decol', serif;

  --text-xs:   0.68rem;
  --text-sm:   0.82rem;
  --text-base: 0.92rem;
  --text-lg:   1.05rem;
  --text-xl:   1.15rem;
  --text-2xl:  1.35rem;
  --text-3xl:  1.75rem;
  --text-4xl:  2.3rem;
  --text-5xl:  3rem;

  --space-1: 0.25rem;  --space-2: 0.5rem;   --space-3: 0.75rem;
  --space-4: 1rem;     --space-5: 1.25rem;  --space-6: 1.5rem;
  --space-8: 2rem;     --space-10: 2.5rem;  --space-12: 3rem;
  --space-16: 4rem;    --space-20: 5rem;

  --radius-sm: 8px;    --radius-md: 12px;   --radius-lg: 16px;
  --radius-xl: 22px;   --radius-full: 9999px;

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --duration: 180ms;
}
```

Notas de diseno:
- El khaki pastel es la personalidad. Rosa es el acento, no la base.
- Tinta marron calido en vez de negro — todo se siente mas suave.
- Sombras neutras (marron) no rosadas — las sombras rosadas se ven forzadas.
- Border-radius reducidos respecto al plan anterior — 22px es kawaii sin ser bubbly.

---

## 1. Tipografia

**Google Fonts load:**
```
Zen Maru Gothic: wght 400;500;600;700
Kaisei Decol: wght 400;700
```

Uso:
- Body y UI: Zen Maru Gothic. Redondeada, legible, personalidad kawaii sin ser infantil.
- Titulos principales (h1, nombre en sidebar, "aris-sama"): Kaisei Decol. Serif decorativa con caracter.
- Mono/labels: Quicksand. Geometrica, limpia.
- Nada de Space Mono — demasiado tecnico para este mood.

---

## 2. Layout — Base.astro

### Sidebar

- Fondo solido `var(--color-sidebar)` — sin gradiente. Solido = calidad. Gradientes laterales se ven amateur.
- Ancho: 220px.
- Avatar: circulo con borde `1.5px solid var(--color-border-accent)`, sin sombra. Simple.
- Nombre: `--font-deco`, `font-size: 15px`.
- Nav links: sin borde lateral. Hover: fondo `rgba(212,165,165,0.08)`, texto a `var(--color-accent-hi)`. Activo: fondo `rgba(212,165,165,0.12)`, borde-izquierdo `2px solid var(--color-accent)`.
- Section labels: `font-size: 9px`, `letter-spacing: 0.1em`, `text-transform: lowercase`, `color: var(--color-muted-2)`.
- Footer: borde superior `1px dashed var(--color-border)` en vez de solido. El dashed es el unico detalle decorativo sutil.
- Kaomoji en `var(--color-accent-2)`.

### Panel principal

- Topbar: `var(--color-topbar)`, borde inferior `1px solid var(--color-border)`.
- Bar dot: circulo `6px` en `var(--color-accent)`. Simple. No corazones CSS.
- Bar title: `--font-deco`.
- Content: fondo `var(--color-bg)`. Sin gradientes radiales escondidos — limpio.
- Scrollbar: `rgba(158,145,131,0.2)` — neutra, no rosa.
- Footer: borde punteado como el sidebar. Texto en `var(--color-muted)`.

### Fondo (orbs)

Tres orbs suaves con colores de la paleta:
- A: `radial-gradient(circle, #E2C4C4 0%, transparent 70%)` — rosa desaturado
- B: `radial-gradient(circle, #C9B8D4 0%, transparent 70%)` — malva
- C: `radial-gradient(circle, #E8DFD0 0%, transparent 70%)` — khaki calido

Opacidad: 0.08-0.14. Animaciones lentas 30-50s. Efecto de capas de color sin ser obvio.

### Overlay de transicion

`rgba(245,240,232,0.92)` — khaki crema que tapa todo suavemente.

---

## 3. BgCanvas — Reemplazo total

El icosaedro amatista con wisps/combo/rings es demasiado agresivo para este aesthetic. Reemplazar con:

**Particulas decorativas flotantes:**
- 40-60 particulas: estrellitas de 4 puntas, circulos diminutos, lineas finas curvas
- Movimiento: Lissajous lento, cada particula con fase y frecuencia diferente
- Colores: `var(--color-accent-2)`, `var(--color-lavender)`, `var(--color-muted-2)` — rotando
- Opacidad: 0.04-0.10. Casi subliminal. Estan ahi pero no molestan.
- Tamano: 2-6px. Pequenas.
- Interactividad: suave repulsion del cursor (las particulas se alejan un poco cuando el mouse pasa cerca, vuelven despues). Sin combo, sin rings, sin drag agresivo.
- Performance: canvas 2D simple, sin shadowBlur (caro), sin glow por particula.

---

## 4. Cursor

- Dot: circulo `5px`, `background: var(--color-accent)`, `opacity: 0.6`.
- Ring: `20px`, `border: 1px solid rgba(212,165,165,0.3)`.
- Trail: particulas diminutas circulares en `rgba(158,145,131,0.25)`. Se desvanecen rapido.
- Hover: ring crece a 30px, border se hace mas visible.
- Sin formas de corazon ni estrellitas en el cursor — eso es cliché.

---

## 5. Chibi Overlay

Nuevo componente: `src/features/deco/ChibiOverlay.astro`

- Posicion: fixed, bottom-right, z-index 0 (detrás del shell).
- SVG inline: personaje chibi con mono grande, lineas finas, colores `#3D3630` (contorno), `#D4A5A5` (detalles rosa), `#FAF7F2` (relleno blanco crema).
- Tamano: ~160px alto.
- Opacidad: 0.08-0.12. Marca de agua, no ilustracion.
- Sin animacion. Estatico. Las animaciones en marcas de agua se ven mal.
- `pointer-events: none`.
- Ocultar en mobile.

---

## 6. Tarjetas (todas)

Estilo unificado para: now-card, video-card, gacha-card, status-item, item-card, stat-card.

```css
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-card);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-5);
  transition: transform var(--duration) var(--ease-out),
              box-shadow var(--duration) var(--ease-out);
}
.card:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-card);
}
```

Sin glassmorphism. Sin blur. Fondo solido. Borde sutil. Sombra en hover. Nada mas. La calidad esta en la simplicidad.

---

## 7. Botones

```css
.btn-primary {
  background: var(--color-accent);
  color: #FAF7F2;
  border: none;
  border-radius: var(--radius-full);
  padding: 6px 18px;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0.02em;
  transition: background var(--duration), box-shadow var(--duration), transform var(--duration);
}
.btn-primary:hover {
  background: var(--color-accent-hi);
  box-shadow: var(--glow-sm);
  transform: translateY(-1px);
}
```

Pill suave. Rosa empolvado. Sin iconos decorativos dentro. El texto basta.

---

## 8. Banner Homepage

```css
.page-banner {
  background: linear-gradient(160deg, #E2C4C4 0%, #E8DFD0 40%, #F0EBE1 75%, #F5F0E8 100%);
  /* rosa empolvado -> khaki -> crema -> fondo */
}
```

- Sin polka dots. Sin shimmer. Sin texto con text-shadow.
- Nombre: `--font-deco`, `color: var(--color-ink)`, sin sombra. Tipografia fuerte por si sola.
- Kaomoji: `color: var(--color-muted)`, `opacity: 0.5`.
- CTA: boton pill rosa, flecha simple.
- Shimmer eliminado — era ruido visual.

---

## 9. Chat

Reemplazar toda la paleta morada (#A855F7) por la paleta del sitio:

- User bubble: `background: rgba(212,165,165,0.15)`, `border: 1px solid rgba(212,165,165,0.20)`.
- Assistant bubble: `background: var(--color-surface)`, `border: 1px solid var(--color-border-card)`.
- Send button: pill `var(--color-accent)`.
- Input focus: `border-color: var(--color-accent)`, `box-shadow: 0 0 0 2px rgba(212,165,165,0.12)`.
- Auth icon: un candado simple, no trebol.
- Streaming cursor: `color: var(--color-accent)`.

---

## 10. Radio Player

- Fondo: `var(--color-surface)`, borde `1px solid var(--color-border)`.
- Boton play: circulo, `border: 1px solid var(--color-border-accent)`, icono de play/pause limpio.
- Barras: `var(--color-accent-2)`.
- Volume: track `var(--color-border)`, thumb `var(--color-accent)`.

---

## 11. Gacha

- Tabs: botones pill con texto simple (sin iconos de flores/estrellas).
- Cards: `border-radius: var(--radius-lg)`, fondo `var(--color-surface)`.
- Rarity: circulos pequenos de color segun rareza, sin estrellas decorativas.
- Constellation: badge `background: var(--color-lavender)`, texto en `var(--color-ink-soft)`.
- Loading: "Cargando..." — sin sufijos decorativos.

---

## 12. Video Grid

- Cards: mismo estilo base de tarjetas.
- Placeholder: icono de play simple, `color: var(--color-muted-2)`, `opacity: 0.4`.
- Category: `font-size: var(--text-xs)`, `letter-spacing: 0.06em`, `color: var(--color-muted)`, lowercase.

---

## 13. Paginas restantes

- `/anime`: cards con estilo base, score como numero simple.
- `/danmaku`: ajustar colores al nuevo token system.
- `/bookshelf`: si tiene cards, mismo estilo base.
- `/admin`: funcional, usar la paleta. Sin adornos extras.

---

## 14. Decoraciones CSS

Minimalistas. Unico detalle: linea punteada en dividers y footer borders.

```css
.deco-divider {
  border: none;
  border-top: 1px dashed var(--color-border);
}
```

Nada de campos de estrellitas CSS, nada de ::before/::after con caracteres decorativos. Eso se ve amateur. Las particulas del canvas ya dan el toque sonador. El chibi SVG ya da personalidad. El resto es tipografia y color.

---

## 15. Responsive

- Mobile body: `background: var(--color-bg)`.
- Nav pills: `background: var(--color-surface)`, `border: 1px solid var(--color-border)`, `border-radius: var(--radius-full)`.
- Chibi: oculto.
- Canvas: mantener pero reducir particulas a 20.

---

## 16. Orden de implementacion

| # | Archivo | Que | Tiempo |
|---|---------|-----|--------|
| 1 | `public/design-tokens.css` | Paleta, fuentes, radios, sombras | 10m |
| 2 | `src/layouts/Base.astro` | Layout completo: sidebar, panel, orbs, overlay, cursor, transiciones | 35m |
| 3 | `src/features/background/BgCanvas.astro` | Particulas flotantes reemplazando icosaedro | 40m |
| 4 | `src/features/deco/ChibiOverlay.astro` | Nuevo — SVG chibi overlay | 25m |
| 5 | `src/pages/index.astro` | Banner + homepage | 15m |
| 6 | `src/features/now/index.astro` | Cards + labels | 8m |
| 7 | `src/features/gacha/GachaGrid.astro` | Tabs + estructura | 10m |
| 8 | `src/features/gacha/GachaCard.astro` | Card styling | 8m |
| 9 | `src/features/video/VideoGrid.astro` | Cards + placeholder | 8m |
| 10 | `src/features/chat/ChatBox.astro` | Paleta rosa reemplazando morado | 12m |
| 11 | `src/features/radio/RadioPlayer.astro` | Colores | 8m |
| 12 | Paginas/features restantes | anime, danmaku, bookshelf, etc | 15m |

Total: ~3.5 horas

---

## Principios

1. Khaki es la base. Rosa es el acento. No al reves.
2. Solido sobre transparente. Fondos solidos, no glassmorphism.
3. Tipografia hace el trabajo. No depender de iconos decorativos.
4. Menos es mas. Las particulas del canvas y el chibi son los unicos elementos "extra". Todo lo demas es color + tipo + espacio.
5. Calidad de estudio. Cada decision tiene que verse como hecha por alguien que hace esto por vivir.
6. Nada de cliches kawaii. No corazones en cursores, no estrellitas en labels, no emojis en UI. El aesthetic viene de la paleta, la tipografia y las proporciones — no de pegar simbolos en todo.
