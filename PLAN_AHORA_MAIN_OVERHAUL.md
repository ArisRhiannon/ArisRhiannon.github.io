# PLAN: Overhaul "ahora" + "main" page — Referencia: Nicole

## Analisis de la pagina de Nicole (patron de diseno)

**Que hace Nicole bien:**
1. **Tipografia como jerarquia visual** — badge celestial, titulo Kaisei Decol grande, subtitulo mono pequeno. No hay cajitas, no hay cards. Solo texto con personalidad.
2. **Un solo flujo vertical** — contenido que fluye naturalmente hacia abajo, sin grids forzados ni cards en fila.
3. **Empleo magistral de `drop-cap`** — la primera letra del texto como acento visual, no como icono/emoji.
4. **Blockquotes con borde lateral sutil** — citaciones que respiran, sin cajas pesadas.
5. **Espacio negativo generoso** — `gap: var(--space-5)`, padding amplio, nada amontonado.
6. **Ornamentos minimos pero con significado** — una linea celestial arriba, un ornamento footer, el toggle de idioma como pill flotante.
7. **Color como acento, no como relleno** — lavender solo en momentos clave (badge, climax, drop-cap, titulo).
8. **Transicion de contenido** — fade suave al cambiar idioma, sin saltos.

**Que las paginas actuales hacen mal:**
1. **"ahora"** — grid de cards con icon/emoji + categoria + texto. Cada item es una "cajita" glass-morphism generica. Se siente como un dashboard, no como una persona.
2. **"main"** — hero con kaomoji flotante + anillos CSS + status dot + CTA button + now-preview con mas cards. Sobrecargado, sin narrativa.
3. **Overlay de transicion** — un `#page-overlay` que es un rectangulo opaco morado. Barato, sin gracia.

---

## Diseno Propuesto

### Filosofia: "Journal, no Dashboard"

Nicole funciona porque lee como una entrada de diario o un manuscrito — no como un panel de control. Las dos paginas deben seguir este principio:

- **Texto como UI** — el contenido mismo es la interfaz. No metas todo en cards.
- **Acentos tipograficos** — drop-caps, italicas, colores de enfasis, tamanos dramaticos.
- **Flujo vertical organico** — como leer una pagina, no como escanear un grid.
- **Adornos con sentido** — lineas celestiales, ornamentos, separadores que cuentan algo.
- **Menos glass-morphism, mas profundidad textual** — el glass blur esta bien para el header, pero las secciones de contenido no necesitan ser cards semitransparentes.

---

## Pagina "ahora" — Nuevo Diseno

### Layout propuesto

```
╔═══════════════════════════════════════╗
║  · · ·  (linea celestial fina)        ║
║                                       ║
║  ARCHIVO PERSONAL          [badge]    ║
║                                       ║
║  ahora                                ║  ← Kaisei Decol, enorme
║  que estoy haciendo                   ║  ← mono, pequeo, uppercase
║                                       ║
║  Guadalajara, MX                      ║  ← mono, sutil
║  actualizado el 13 de abril, 2026     ║  ← mono, aun mas sutil
║                                       ║
║  ── ── ── (separador ornamental)      ║
║                                       ║
║  ⚙️  Construyendo                     ║  ← drop-cap con icon como inicial
║      Fase 4                           ║
║                                       ║
║  📖  Leyendo                          ║  ← misma estructura fluida
║      Danganronpa V3 con Ely           ║
║                                       ║
║  💭  Pensando en                      ║
║      Nito                             ║
║                                       ║
║  😭  Gaching:                         ║
║      Ya saque a Nangong, ahora        ║
║      quiero a Linnea...               ║
║                                       ║
║  ── ── ──                             ║
║                                       ║
║  inspirado por nownownow.com          ║  ← sutil, mono
║                                       ║
║  ◆ (ornamento final)                  ║
╚═══════════════════════════════════════╝
```

### Caracteristicas clave:
- **Badge** "Archivo Personal" en vez de "chip" generico con dot pulsante
- **Titulo** en Kaisei Decol, enorme, con "ahora" como palabra clave
- **Items como bloques textuales** — NO cards. El icon funciona como drop-cap visual (grande, a la izquierda), la categoria en mono uppercase, el texto en body font con peso normal.
- **Separadores ornamentales** entre la cabecera y los items, y al final
- **Sin glass-morphism en los items** — fondo transparente, solo texto con jerarquia
- **Hover sutil** — en vez de translateY + glow, simplemente un accent-color en la categoria y un subrayado en el texto
- **Entrada animada** — los items aparecen con stagger fade-in, pero como lineas de texto, no como cards que "vuelan"

---

## Pagina "main" — Nuevo Diseno

### Layout propuesto

```
╔═══════════════════════════════════════╗
║                                       ║
║  (o-ᴗ-)                               ║  ← kaomoji, pero mas sutil
║                                       ║
║  Aris                                 ║  ← Kaisei Decol, enorme
║  colecciono nitos                     ║  ← mono, subtone
║                                       ║
║  ·  ·  ·  (puntos decorativos)        ║
║                                       ║
║  ──────────────────────               ║  ← linea ornamental
║                                       ║
║  que estoy haciendo                   ║  ← sub-titulo, mono
║                                       ║
║  ⚙️  Construyendo Fase 4              ║  ← items inline, compactos
║  📖  Leyendo Danganronpa V3           ║     sin cards, sin cajas
║  💭  Pensando en Nito                 ║
║  😭  Gaching: Linnea...              ║
║                                       ║
║  ver todo →                           ║  ← link sutil
║                                       ║
║  ──────────────────────               ║
║                                       ║
║  online · gdl.mx                      ║  ← status, mono, sutil
║                                       ║
║  ◇ (ornamento final)                  ║
╚═══════════════════════════════════════╝
```

### Caracteristicas clave:
- **Hero minimalista** — kaomoji sutil (sin animacion exagerada), titulo enorme, subtitulo. SIN anillos CSS, SIN glow radial, SIN scroll indicator, SIN CTA button forzado.
- **Now preview como lista textual** — NO cards. Items inline, cada uno en una linea: icon + categoria + texto. Compacto, como una lista de actividades.
- **Adornos ornamentales** — puntos y lineas decorativas como Nicole, no anillos geometricos.
- **Todo centrado** — como Nicole, todo fluye desde el centro. Max-width estrecho (42rem como Nicole).
- **Eliminar exceso visual** — quitar: hero-ring animations, scroll-line, hero-glow, CTA button (el sitio es personal, no un SaaS).

---

## Overlay de Transicion — Nuevo Diseno

### Actual:
```css
#page-overlay {
  position: fixed; inset: 0;
  z-index: 9999;
  background: rgba(26, 21, 32, 0.95);
  opacity: 0;
  transition: opacity 0.2s ease;
}
```
Un rectangulo morado opaco. Aburrido.

### Propuesto: "Curtain Reveal"

En vez de un fade opaco, un efecto de cortina que se desliza:

```css
#page-overlay {
  position: fixed; inset: 0;
  z-index: 9999;
  /* Dos capas: una que baja y una que sube */
  background: var(--color-bg);
  transform: scaleY(0);
  transform-origin: top;
  transition: transform 0.35s cubic-bezier(0.7, 0, 0.3, 1);
}

#page-overlay.active {
  transform: scaleY(1);
}

/* Un inner con ornamento */
#page-overlay::after {
  content: '◇';
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  font-size: 24px;
  color: var(--color-accent);
  opacity: 0.4;
}
```

**O alternativamente: "Radial Wipe"** — un circulo que se expande desde el centro:

```css
#page-overlay {
  clip-path: circle(0% at 50% 50%);
  transition: clip-path 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

#page-overlay.active {
  clip-path: circle(150% at 50% 50%);
}
```

Ambos son mas interesantes que un fade recto. El radial wipe es mas dramatico y se siente como "entrar en el sitio" de Aris. El curtain reveal es mas elegante. Propongo **radial wipe** para la main page (donde aterriza el usuario) y **curtain** para las paginas internas.

---

## Resumen de Cambios

### /now (ahora)
1. Eliminar el hero section generico (page-hero con glow/chip/dot)
2. Header tipo Nicole: badge + titulo Kaisei Decol + subtitulo mono
3. Items como bloques textuales con drop-cap-icon, sin cards glass
4. Agregar separadores ornamentales y ornamento final
5. Hover sutil en items (accent color, no transform/glow)

### / (main)
1. Hero minimalista: kaomoji sutil + titulo + subtitulo. Sin anillos, sin glow, sin scroll indicator
2. Now preview como lista textual compacta, sin cards
3. Adornos ornamentales (puntos, lineas)
4. Centrado con max-width estrecho (42rem)
5. Status como detalle, no como feature

### Base.astro (overlay)
1. Reemplazar fade recto por radial wipe (clip-path circle expand)
2. Agregar ornamento sutil en el overlay
3. Duracion 0.4s con cubic-bezier

### Compartido entre ambas
- Separadores ornamentales reutilizables (clase .celestial-separator)
- Ornamento final (clase .page-ornament)
- Drop-cap icon (clase .icon-drop-cap)
- Entrada stagger pero como opacidad, no como translate de cards

---

## Archivos a Modificar

1. `src/pages/now.astro` — reescribir completo
2. `src/pages/index.astro` — reescribir completo
3. `src/layouts/Base.astro` — overlay + agregar clases compartidas al <style>
4. `data/now.json` — sin cambios (los datos son los mismos)
5. `data/homepage.json` — sin cambios
