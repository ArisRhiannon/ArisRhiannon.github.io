# Investigación Exhaustiva: misitio (aris-sama.duckdns.org)

## Estado Actual del Proyecto

### Arquitectura
- **Framework:** Astro (SSR con @astrojs/node adapter)
- **Runtime:** Bun (SQLite nativo)
- **Deploy:** Docker + Caddy reverse proxy en Oracle A1 Flex (ARM64)
- **DB:** SQLite (`data/database.sqlite`, ~45KB)
- **Dominio:** aris-sama.duckdns.org (DuckDNS dinámico)
- **LOC:** ~12,032 líneas (src/)

### Páginas Actuales (8 + admin)
| Página | Ruta | Descripción | Estado |
|--------|------|-------------|--------|
| Feed | `/` | Post cards con mood, media, infinite scroll | Funcional |
| Jardín | `/garden` | Digital garden — links a otros módulos | Catálogo estático |
| Ahora | `/now` | Now page con items desde JSON | Funcional, manual |
| Videos | `/videos` | Grid de clips con thumbnails, comentarios | Funcional |
| Gacha | `/gacha` | Roster de GI/HSR/ZZZ via Enka API | Funcional |
| Anime | `/anime` | AniList integration, filtros por status | Funcional |
| Chat | `/chat` | Gemma 4 local via llama.cpp, streaming | Funcional |
| Onírico | `/onirico` | Motor de sueños fractal + audio p5.js | Funcional |
| Nicole | `/nicole` | Lore essay bilingüe | Funcional |
| Admin | `/admin` | Panel CRUD, módulos, stats | Funcional |

### APIs (21 endpoints)
- Auth: login, logout, auth-check
- Feed: CRUD posts, upload media, pin, profile
- Videos: CRUD, upload, comments
- Gacha: enka-gi, enka-hsr, enka-zzz (cache 1h)
- Chat: streaming a llama.cpp
- Audio: stream endpoint
- Nav: dynamic nav items
- Admin: data endpoint

### Design System Actual
- **Estética:** "Yume Kawaii Japonés" — oscuro con destellos neon
- **Paleta:** bg #1a1520, accent #ff6b9d, lavender #c4b5fd, cyan #67e8f9, gold #fbbf24
- **Tipografía:** Kaisei Decol (decorativa), Zen Maru Gothic (body), Quicksand (mono/UI)
- **Efectos:** Glassmorphism, glow shadows, backdrop-filter blur, particle canvas
- **Animaciones:** orb-drift (bg orbs), dot-pulse (status), fade-in on scroll (yume-init), page overlay transitions, hover scale/lift
- **Componentes decorativos:** ChibiOverlay SVG, celestial-line, ornamental separators, kaomoji logos

### Infra
- **Docker:** web (Astro) + caddy (HTTPS automático via Let's Encrypt)
- **Volúmenes:** `./data:/app/data`, `./public/uploads`, `./public/thumbs`
- **Security headers:** HSTS, X-Content-Type-Options, X-Frame-Options, CSP (bastante restrictivo)
- **Caddy:** gzip/zstd compression, HSTS preload, CSP

---

## HALLAZGOS — Problemas y Oportunidades

### CRÍTICO

**1. Sin Open Graph / SEO en páginas principales**
Solo `/v/[id]` tiene og:tags. La home, now, gacha, anime, garden — ninguna tiene OG. Cuando alguien comparte aris-sama.duckdns.org en Discord/Twitter/Telegram, sale un preview genérico sin imagen ni descripción.

**2. Sin 404 page**
No existe `/src/pages/404.astro`. Cualquier ruta inválida probablemente crashea o muestra algo feo.

**3. Sin robots.txt ni sitemap**
Nada en `public/robots.txt` ni sitemap generado. Google no puede indexar el sitio eficientemente.

**4. CSP bloquea cosas que deberían funcionar**
El CSP en Caddy tiene `script-src 'self' 'unsafe-inline'` pero no permite `connect-src` explícito, lo cual podría bloquear las API calls de Enka, AniList, y el streaming de chat si el navegador es estricto. Tampoco permite `media-src` para el audio stream.

**5. Sin RSS/Atom feed**
Los posts del feed no tienen feed sindicado. Nadie puede suscribirse.

---

### ALTA PRIORIDAD

**6. Feed/Hero falta información de perfil**
El hero muestra display_name y subtitle pero NO muestra la pfp. El perfil solo aparece como miniatura 32x32 en cada PostCard. Falta una sección de perfil con imagen grande en el hero.

**7. Now page es completamente manual**
`data/now.json` es estático — hay que editarlo a mano o vía admin. No hay forma de actualizar desde la UI del sitio sin ir al admin. Debería ser editable in-place o al menos desde un widget en la home.

**8. Garden es solo un catálogo de links**
No hay contenido real en `/garden` — solo cards que linkean a otras páginas. Un digital garden real tendría notas, essays, ideas creciendo orgánicamente con interlinking.

**9. Sin light mode / theme toggle**
El sitio es 100% dark. No hay opción de tema claro. Algunos usuarios prefieren light mode, y un toggle añade sofisticación.

**10. Mobile experience mejorable**
- Header se oculta al scrollear (bueno) pero el menú móvil es overlay básico
- No hay bottom navigation para móvil
- Los PostCards en grid de 1 columna se ven bien pero el compose drawer podría ser más accesible
- No hay swipe gestures ni pull-to-refresh

**11. Sin búsqueda global**
No hay forma de buscar entre posts, videos, personajes de gacha, o anime. Para un sitio personal con contenido creciente, esto se vuelve esencial.

**12. Sin página "About" formal**
El perfil está fragmentado: el hero muestra nombre/subtitle, el now page muestra estado actual, pero no hay una página "Sobre mí" con bio completa, intereses, contacto, links sociales.

---

### MEDIA PRIORIDAD

**13. Falta música ambiente persistente**
Existe el RadioPlayer pero solo aparece si hay `aris_song.mp3`. Es básico. Un reproductor más completo con:
- Cola de canciones (playlist)
- Visualizador de audio
- Integración con el canvas de fondo (sync BPM)
- Controles de volumen persistentes via localStorage

**14. Sin guestbook / muro de visitantes**
Un sitio personal kawaii siempre tiene un guestbook donde la gente deja mensajes. Es un clásico de la web japonesa (掲示板). Podría ser un mini-feed público con mensajes de visitantes.

**15. El chat es privado (password) pero podría ser semi-público**
El chat con Gemma 4 es password-protected. Podría haber un modo "visitor" donde visitantes pueden hacer preguntas limitadas (rate-limited) sin auth, creando engagement.

**16. Onírico está aislado**
El motor fractal/audio es un mundo aparte. Podría integrarse como:
- Fondo animado opcional en toda la app (no solo en /onirico)
- Widget de "mood actual" vinculado al audio
- Screensaver automático tras inactividad

**17. Sin animaciones de transición entre páginas**
Astro tiene ClientRouter (View Transitions) habilitado pero NO hay transiciones personalizadas. Cada navegación es un fade genérico. Se podrían hacer:
- Morph del hero de una página a otra
- Slide transitions entre secciones
- Crossfade con el overlay actual

**18. PostCards no tienen interacción social**
No hay likes, reactions, ni forma de que visitantes interactúen con los posts. Al menos reactions de emoji (kawaii, wow, etc) harían el sitio más vivo.

**19. Sin lazy loading de módulos en garden**
El garden carga todo de una vez. Si crece, necesitaría lazy loading o virtual scrolling.

**20. Falta metadata temporal en now page**
El now page muestra "actualizado el X" pero no tiene historial. Un now page evolutivo debería mostrar cambios a lo largo del tiempo (git-style diff o timeline).

**21. No hay favicon dinámico por página**
El favicon es siempre el pfp. Podría cambiar según la página: pfp en home, espada en gacha, note musical en onírico, etc.

---

### BAJA PRIORIDAD

**22. Tipografía podría refinarse**
- `--font-mono` usa Quicksand que no es realmente monospace. Debería ser JetBrains Mono o Fira Code
- Los tamaños de texto son muy específicos (0.68rem, 0.82rem) — poco convencionales
- Falta una escala tipográfica modular consistente

**23. Falta @layer en CSS**
No hay capas de CSS. Con @layer se podría organizar: reset -> tokens -> base -> components -> utilities, evitando especificidad wars.

**24. Sin container queries**
Los componentes usan media queries globales en vez de container queries, lo que los hace menos reutilizables.

**25. Animaciones no respetan prefers-reduced-motion**
No hay `@media (prefers-reduced-motion: reduce)` para desactivar animaciones. Es un issue de accesibilidad.

**26. Falta skip-to-content link**
No hay link "Skip to main content" para usuarios de teclado/lectores de pantalla.

**27. Alt texts genéricos en imágenes**
Las imágenes de posts tienen `alt=""` (vacío). Debería haber un campo de alt text en el upload.

---

## INVESTIGACIÓN DE DISEÑO — Ideas Inspiradas

### De sitios kawaii/dreamy personales

**28. Sakura / Cherry Blossom particles**
En vez de (o además de) las partículas geométricas actuales, tener pétalos de sakura cayendo suavemente. Se puede hacer con CSS `@keyframes` o un shader ligero en el canvas existente. Impacto visual enorme para la estética.

**29. Cursor personalizado con trail**
Un cursor kawaii (estrella, sparkle, o el chibi de Aris) con un trail de partículas que sigue al mouse. Los sitios japoneses usan esto MUCHO. Se implementa con un event listener en mousemove + canvas overlay.

**30. Typing animation en el hero**
El "colecciono nitos" del hero podría tener un efecto typewriter que escribe la frase letra por letra, como una terminal. Combina con la estética "mono/UI" de Quicksand.

**31. Parallax sutil en scroll**
Los bg-orbs ya flotan, pero podrían tener parallax sutil al hacer scroll — moverse a diferente velocidad que el contenido. Se logra con `transform: translateY(var(--scroll-y))` y un scroll listener pasivo.

**32. Decoraciones de línea japonesa (罫線)**
Las separadoras celestiales actuales son minimalistas. Se podría enriquecer con patrones de líneas decorativas japonesas: ──◇──, ✧･ﾟ: *✧･ﾟ:* , ondas, etc. SVG inline o CSS borders.

**33. Hover effects kawaii en cards**
Cuando hover sobre un PostCard, en vez de solo translateY(-3px), agregar:
- Sparkle particles que emanan del card
- Border que "respira" (glow pulsante)
- Imagen que hace un sutil tilt 3D (perspective + rotateX/Y)

### De sitios de portfolio creativos (Brittany Chiang, etc.)

**34. Sección de "timeline" visual**
Un timeline vertical que muestra la historia del sitio / la persona. Cuando aparece en viewport, los nodos se animan con un fade-in secuencial. Se usa IntersectionObserver + stagger.

**35. Number counter animado para stats**
Las stats del gacha (número de personajes, 5-stars, etc.) podrían animarse con un counter que va de 0 al valor cuando entra en viewport. Se hace con `requestAnimationFrame` + easing.

**36. Reveal animations con clip-path**
En vez de simple opacity fade, los elementos podrían revelarse con `clip-path: inset()` animando de 100% a 0. Da un efecto de "cortina" muy limpio.

**37. Magnetic buttons**
Los botones del nav podrían tener un efecto "magnético" — cuando el mouse se acerca, el botón se desplaza sutilmente hacia el cursor. Se calcula la distancia y se aplica un transform proporcional.

### De la cultura web japonesa / otaku

**38. Ranking/wishlist de personajes gacha**
El gacha page muestra el roster pero no hay forma de marcar favoritos, wishlist, o "main". Un sistema de:
- ★5 stars marcados como "main"
- Wishlist: "siguiente pull objetivo"
- Rating personal (S/A/B/C)

**39. Stamps/merch collection display**
Un showcase visual de merchandise física — figuras, nendoroids, keychains. Grid con fotos y etiquetas. El "colecciono nitos" del subtitle grita por esto.

**40. Mood widget persistente**
Un widget que muestra el mood actual (el emoji de los posts) pero como un indicador global del estado de ánimo, persistente en el sidebar o footer. Cambia con el último post o se puede setear manualmente.

**41. BBS / 掲示board estilo retro**
Un tablón de mensajes con estética retro-japonesa — bordes pixelados, font mono, colores neón sobre negro. Como los BBS de 2ch/5ch pero kawaii.

### De modern CSS (2024-2026)

**42. Scroll-driven animations (CSS puro)**
Con `animation-timeline: scroll()` se pueden hacer animaciones vinculadas al scroll SIN JavaScript:
- Barra de progreso que avanza al scrollear
- Header que se compacta al bajar
- Elementos que se revelan con parallax natural

**43. View Transitions API (mejorada)**
Astro ya usa ClientRouter pero las transiciones son fades básicos. Con la View Transitions API se puede:
- Morph del logo al navegar
- Crossfade del hero entre páginas
- Animación personalizada del page overlay actual (que ya existe pero es simple)

**44. CSS @scope para componentes**
En vez de scoped styles de Astro, se puede usar `@scope` nativo para estilos más predecibles y menos specificity hacks.

**45. CSS `color-mix()` para mood theming**
Con `color-mix(in srgb, var(--mood-color) 15%, transparent)` se puede generar automáticamente los borders/glows de cada mood sin hardcodear cada color en el moodMap.

**46. `@starting-style` para entry animations**
Nueva CSS feature que permite definir el estilo inicial de un elemento cuando se agrega al DOM — reemplaza las clases `.yume-init` / `.booted` actuales con CSS puro.

### De sitios link-in-bio (Bento, Linktree)

**47. Widget de status dinámico**
Un widget "Ahora mismo" que se actualiza en tiempo real — qué juego está jugando (via Rich Presence de Discord), qué anime está viendo (via AniList), qué música escucha (via Last.fm). Se actualiza automáticamente sin intervención.

**48. Spotify/Listen.moe "Now Playing" widget**
Mostrar la canción que está sonando actualmente, con artwork y progress bar. Los sites kawaii siempre tienen esto. Se integra con el RadioPlayer existente.

**49. Calendar/activity heatmap**
Como el contribution graph de GitHub pero para actividad personal — días con posts, días viendo anime, días jugando gacha. Un "Year in Review" constante.

**50. Social links con rich previews**
En vez de links planos, mostrar previews con favicon, título y descripción del sitio linkeado. Para los links sociales (Discord, Twitter, etc).

---

## PLAN DE ACCIÓN PRIORITADO

### Fase 1 — Fundamentos críticos (1-2 días)
1. Open Graph tags en TODAS las páginas
2. Página 404 con estética del sitio
3. robots.txt + sitemap.xml
4. CSP fix (agregar connect-src, media-src, img-src blob:)
5. RSS feed para posts

### Fase 2 — Identidad y perfil (2-3 días)
6. Hero section mejorado con pfp grande + bio
7. Página "About" formal
8. Now page editable desde la UI (in-place editing cuando authenticated)
9. Perfil persistente en sidebar (desktop) o bottom bar (mobile)

### Fase 3 — Estética y micro-interacciones (3-4 días)
10. Sakura particles en el canvas de fondo (toggle o season-based)
11. Cursor trail kawaii
12. Typing animation en hero
13. Hover effects mejorados en PostCards (3D tilt, sparkles)
14. Scroll-driven animations para header y reveal
15. View transitions personalizadas entre páginas
16. prefers-reduced-motion respect
17. CSS @layer organizado

### Fase 4 — Contenido y features (3-4 días)
18. Nendo/merch collection page
19. Gacha wishlist/favorites system
20. Guestbook / BBS
21. Now Playing widget (Listen.moe / Spotify)
22. Status dinámico (Discord Rich Presence / AniList watching)
23. Reactions de emoji en posts
24. Búsqueda global

### Fase 5 — PWA y performance (2-3 días)
25. Service worker + offline support
26. manifest.json (PWA installable)
27. Container queries para componentes
28. Lazy loading de módulos en garden
29. Image optimization (Avif/WebP con <picture>)

### Fase 6 — Siguiente nivel (ongoing)
30. Activity heatmap / calendar
31. Onírico como screensaver global
32. Chat semi-público para visitors
33. Garden con contenido real (notes, essays, interlinking)
34. Theme toggle (light mode yume)
35. Dynamic favicon por página
36. Skip-to-content + accessibility audit completo

---

## NOTAS DE DISEÑO FILOSÓFICAS

### La línea de pensamiento de misitio
El sitio es una **casa personal en internet** — no un portfolio, no un blog, no una landing page. Es un espacio íntimo donde Aris colecciona nitos, juega gacha, ve anime, escribe, y comparte su mundo. La estética "yume kawaii oscuro" no es accidental — es un **espacio onírico**, un cuarto decorado con posters y figuras y luces de neón, donde lo digital se siente tangible.

### Lo que FORTALECE esta identidad
- El BgCanvas con partículas flotantes
- Los glow effects y glassmorphism
- El chibi SVG decorativo
- Los kaomoji como branding
- Los mood emojis en posts
- El RadioPlayer con canción personal
- El Foco Onírico (experiencia envolvente)

### Lo que DEBILITA esta identidad
- El garden es solo un índice — falta la sensación de "cuarto lleno de cosas"
- No hay colección visual de figures/nendoroids (el "colecciono nitos" del subtitle)
- Las transiciones entre páginas son genéricas (fade)
- No hay sorpresas ni eastereggs
- El chat está completamente cerrado — el sitio se siente "habitado" solo cuando Aris está logged in
- Falta música ambiente persistente

### Principio rector
Cada feature nueva debe hacer que el sitio se sienta más **habitado**, más **vivo**, más **personal**. No features por features — sino capas que hacen que visitarlo se sienta como entrar al cuarto de alguien que te importa.
