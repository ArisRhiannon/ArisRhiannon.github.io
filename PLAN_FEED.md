# PLAN: Aris Feed — Personal Microblog sobre la Main Page

## Vision

Transformar la pagina principal (/) de un hero estatico a un **feed personal** — como un Twitter/X privado donde solo Aris postea. La pagina mantiene su estetica yume-kawaii pero ahora respira con contenido vivo: pensamientos, imagenes, videos, documentos, organizados en un mosaico organico que se siente como un jardin digital, no como un grid generico.

---

## 1. Arquitectura General

### Stack existente que reutilizamos
- **Auth**: Ya existe `aris_admin` cookie con HMAC-SHA256, PBKDF2 password verify, middleware que protege `/admin/*`. Lo extendemos.
- **DB**: SQLite via `bun:sqlite` (`src/lib/db.ts`). Ya tiene tables. Agregamos `posts` y `profile`.
- **Uploads**: Ya hay upload de videos con FormData a `/api/videos/upload`. Patrones de almacenamiento en `public/uploads/` y `public/thumbs/`.
- **Astro SSR** con `@astrojs/node` standalone en Docker.

### Nuevos componentes

```
data/database.sqlite
  + posts          (tabla nueva)
  + profile        (tabla nueva — 1 row, settings de Aris)

src/pages/api/feed/
  + index.ts       GET  — lista posts (paginado, con media)
  + create.ts      POST — crear post (auth required)
  + delete.ts      DELETE — borrar post (auth required)
  + upload.ts      POST — subir media para posts (auth required)

src/pages/api/auth/
  (login.ts ya existe — lo extendemos para que tambien sirva el feed)

src/pages/index.astro
  Reescrita — feed timeline con compose drawer cuando estas logeada

src/features/feed/
  + FeedGrid.astro     — mosaico organico de posts
  + PostCard.astro     — un solo post renderizado
  + ComposeDrawer.astro — formulario flotante para crear posts
  + ProfilePanel.astro — editar pfp, display name, subtitle
  + MediaViewer.astro  — lightbox para imagenes/videos fullsize
  + FeedClient.js      — client-side: infinite scroll, compose, delete

src/lib/
  + feed.ts           — queries para posts + media
  + media.ts          — procesamiento de uploads (resize, thumb)
```

---

## 2. Base de Datos — Schema

```sql
-- Perfil de Aris (1 sola row, updatable)
CREATE TABLE IF NOT EXISTS profile (
  id INTEGER PRIMARY KEY CHECK (id = 1),  -- siempre row 1
  display_name TEXT NOT NULL DEFAULT 'Aris',
  subtitle TEXT NOT NULL DEFAULT 'colecciono nitos',
  pfp_url TEXT NOT NULL DEFAULT '/uploads/pfp.webp',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Posts del feed
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  body TEXT NOT NULL,                        -- texto del post (markdown-lite)
  media_json TEXT DEFAULT '[]',             -- JSON array de {url, type, thumb, width, height, alt}
  mood TEXT DEFAULT NULL,                   -- emoji/tag de mood: ✨💭🎮😭 etc
  pinned INTEGER DEFAULT 0,                 -- 1 = pinned al top
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_pinned ON posts(pinned DESC, created_at DESC);
```

**media_json format:**
```json
[
  {"url": "/uploads/feed/abc123.webp", "type": "image", "thumb": "/thumbs/feed/abc123.webp", "width": 1200, "height": 800, "alt": ""},
  {"url": "/uploads/feed/vid456.mp4", "type": "video", "thumb": "/thumbs/feed/vid456.jpg", "width": 1920, "height": 1080, "alt": ""},
  {"url": "/uploads/feed/doc789.pdf", "type": "document", "thumb": null, "name": "notas.pdf", "size": "2.4MB"}
]
```

---

## 3. Auth — Extension del sistema existente

### Cookie actual: `aris_admin`
Ya es segura: `httpOnly`, `secure`, `sameSite: strict`, HMAC-SHA256, 8h expiry.

### Cambios:
1. **Middleware** — agregar `/api/feed/create`, `/api/feed/delete`, `/api/feed/upload` a las rutas protegidas (o verificar token inline como hace `isAdmin()`).
2. **Cliente** — al cargar la pagina, hacer `fetch('/api/feed/auth-check')` que devuelve `{ authenticated: boolean }`. Si true, mostrar compose drawer + profile panel.
3. **Login UI** — agregar un login inline sutil en la misma pagina. Un icono de candado pequeño en el header. Al click, muestra un modal elegante con campo de password. Al logearse exitosamente, la cookie se guarda y la pagina se re-hidrata mostrando las herramientas de edicion.
4. **Session persistencia** — la cookie ya es persistente (maxAge 8h). Al visitar la pagina, si la cookie es valida, el compose drawer aparece. No necesitas logearte cada vez.

### Auth check endpoint
```
GET /api/feed/auth-check
→ { authenticated: true/false, profile: { displayName, subtitle, pfpUrl } }
```

---

## 4. Layout — Mosaico Organico

### Principio: "Jardin, no Grid"

No usamos un CSS Grid rigido de columnas iguales. Ni un masonry de columnas. Usamos algo mas organico:

**Approach: CSS Grid con `grid-row: span` variable segun contenido**

```css
.feed-mosaic {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  grid-auto-rows: 10px;          /* row unit = 10px para control fino */
  gap: 16px;
  padding: 0 var(--space-6);
}
```

Cada post calcula su `grid-row: span N` en base a su contenido:
- Solo texto corto: `span 18` (180px)
- Texto largo: `span 28`+ (280px+)
- 1 imagen horizontal: `span 32` (320px)
- 1 imagen vertical: `span 42` (420px)
- 1 imagen cuadrada: `span 30` (300px)
- Video: como imagen horizontal + 2 filas extra para el player
- Documento: `span 14` (140px, compacto)
- Multi-media: se expande proporcionalmente

**Esto se calcula en Astro frontmatter** — cada PostCard recibe su `rowSpan` como prop basado en el media_json, y lo aplica como style inline.

### Alternativa considerada: CSS Masonry nativo
`grid-template-rows: masonry` aun es experimental (solo Firefox). No lo usamos por compatibilidad.

### Alternativa considerada: JS Masonry (desandro)
Agrega complejidad y layout jumps. Nuestro approach con `grid-row: span` + `auto-rows: 10px` es puro CSS, sin JS, y se ve organico porque los posts tienen alturas naturales basadas en su contenido — no todos iguales, no todos rectangulos perfectos.

---

## 5. Diseno del Post Card

### Estructura visual:

```
┌─────────────────────────────────────────┐
│  ○ PFP   Aris          @nitting         │  ← header con pfp circular
│          colecciono nitos                │  ← subtitle en muted
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   │  ← linea sutil
│                                         │
│  Estoy tan emocionada por la Fase 4     │  ← body text
│  ya casi termino el backend...          │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │                                 │    │  ← media (imagen/video)
│  │      [imagen o video]           │    │     border-radius suave
│  │                                 │    │     aspect-ratio natural
│  └─────────────────────────────────┘    │
│                                         │
│  ✨  ·  13 abril 2026          [🗑]     │  ← footer: mood + fecha + delete (solo si auth)
└─────────────────────────────────────────┘
```

### Estilos clave:

- **Fondo**: `var(--color-surface)` con blur sutil, pero MAS transparente que los cards viejos. `rgba(255,245,250, 0.025)` — apenas perceptible, como un suspiro de superficie.
- **Borde**: `1px solid var(--color-border)` — ultra sutil, casi invisible.
- **Border-radius**: `var(--radius-lg)` (16px) — suave, no cuadrado, no pill.
- **Hover**: el borde se intensifica a `var(--color-border-accent)`, un glow `var(--glow-sm)` aparece suavemente, y el post se eleva `translateY(-3px)`. Transicion con `var(--ease-out)`.
- **Click**: si tiene media, abre el MediaViewer (lightbox). Si no, un ripple sutil en el card.
- **PFP**: 32px circular con `border: 1px solid var(--color-border-accent)`, `box-shadow: var(--glow-sm)`.
- **Mood badge**: pill pequeno con el emoji del mood, `background: rgba(255,107,157,0.08)`, mono font.
- **Timestamp**: `var(--font-mono)`, `var(--text-xs)`, `var(--color-muted-2)`.
- **Delete**: icono de trash que aparece solo si `authenticated`, con `opacity: 0` que va a `0.6` en hover del card.

### Colores adaptivos por mood

Cada post puede tener un `mood` que tinta sutilmente el borde/glow del card:

| mood      | border tint                    | glow tint                       |
|-----------|--------------------------------|---------------------------------|
| ✨        | `rgba(251,191,36,0.15)`        | `rgba(251,191,36,0.10)`        |
| 💭        | `rgba(196,181,253,0.15)`       | `rgba(196,181,253,0.10)`       |
| 🎮        | `rgba(103,232,249,0.15)`       | `rgba(103,232,249,0.10)`       |
| 😭        | `rgba(255,107,157,0.20)`       | `rgba(255,107,157,0.12)`       |
| 📖        | `rgba(134,239,172,0.15)`       | `rgba(134,239,172,0.10)`       |
| (default) | `var(--color-border)`          | none                            |

Esto es ARMONIA COMPOSICIONAL — los acentos de color ya existen en el design system (`--color-gold`, `--color-lavender`, `--color-cyan`, `--color-accent`, `--color-sage`). No inventamos colores nuevos. Cada mood "tira" del color que ya pertenece a la paleta yume del sitio. El resultado: cada post tiene su propia personalidad cromatica pero todos pertenecen a la misma familia.

### Armonia compositiva aplicada

1. **Color principle**: Dominancia del fondo oscuro (`--color-bg: #1a1520`) con acentos en superficies ultra-transparentes. Los moods no "gritan" — son susurros de color que se funden con el fondo.
2. **Proportion principle**: El mosaico no es simetrico. Posts con imagenes grandes toman mas espacio visual. Posts de texto son compactos. Esto crea ritmo — como una composicion musical donde hay notas largas y cortas.
3. **Negative space principle**: Gap de 16px entre posts. No amontonado. Cada post respira. El espacio negativo es tan importante como el contenido.
4. **Visual weight**: Pinned posts tienen un borde `--color-accent` permanente y un glow sutil. Son los anclas visuales del feed.
5. **Repetition with variation**: Todos los posts comparten la misma estructura (pfp + nombre + texto + media + footer) pero varian en altura, color mood, y contenido. Esto es lo que hace que sea "sofisticado y no generico" — cada card es la misma plantilla pero se siente diferente.

---

## 6. Compose Drawer

### UI: Drawer que desliza desde abajo

Cuando Aris esta logeada, aparece un boton flotante `✦` en la esquina inferior derecha. Al click, sube un drawer:

```
┌─────────────────────────────────────────┐
│  nuevo post                         ✕   │
│  ────────────────────────────────────── │
│                                         │
│  [textarea: que estas pensando...]      │
│                                         │
│  [📎] [🎬] [📄]   mood: [✨v]          │
│                         ┌──────┐        │
│                         │✨ 💭 🎮│       │
│                         │😭 📖 ♪│       │
│                         └──────┘        │
│                                         │
│  [previews de media subida]             │
│                                         │
│                       [publicar →]      │
└─────────────────────────────────────────┘
```

- **Textarea**: minimal, sin toolbar. Markdown-lite soportado (`*italic*`, `**bold**`, `~~strike~~`, `` `code` ``).
- **Upload buttons**: iconos para imagen 📎, video 🎬, documento 📄. Cada uno abre un file picker con el accept correspondiente.
- **Mood selector**: dropdown de emojis que tinta el post.
- **Media previews**: thumbnails de lo subido, con X para quitar.
- **Publish**: POST a `/api/feed/create` con body + media_urls + mood.

### Upload flow:
1. Seleccionas archivo(s) en el drawer.
2. Cada archivo se sube inmediatamente a `/api/feed/upload` (FormData).
3. El server lo guarda en `public/uploads/feed/`, genera thumbnail en `public/thumbs/feed/`.
4. Devuelve `{ url, thumb, type, width, height }`.
5. El drawer muestra el preview y acumula los media objects.
6. Al publicar, se envian las URLs ya confirmadas.

---

## 7. Profile Panel

### Acceso: click en tu pfp en el header del drawer, o icono de settings

Panel lateral deslizante:

```
┌─────────────────────────────┐
│  perfil                     │
│  ────────────────────────── │
│                             │
│  ┌─────┐                    │
│  │ PFP │  [cambiar foto]    │
│  └─────┘                    │
│                             │
│  nombre:  [Aris        ]    │
│  sub:     [colecciono..]    │
│                             │
│  [guardar]                  │
│                             │
│  ────────────────────────── │
│  [cerrar sesion]            │
└─────────────────────────────┘
```

- **PFP upload**: click en "cambiar foto" → file picker → upload a `/api/feed/upload` con type `pfp` → server la redimensiona a 128x128 WebP → guarda como `public/uploads/pfp.webp` → actualiza profile table.
- **Display name / subtitle**: inputs que hacen PATCH a `/api/feed/profile`.
- **Logout**: POST a `/api/auth/logout` (ya existe), redirige a `/`.

---

## 8. Pagina Index — Reescritura completa

### Estructura:

```
/ (index.astro)
│
├── <section class="feed-hero">
│   ├── celestial-line
│   ├── kaomoji (sutil)
│   ├── "Aris" (Kaisei Decol)
│   ├── subtitle del profile
│   └── ornamental dots + line
│
├── <section class="feed-body">
│   ├── Pinned posts (si hay)
│   │   └── PostCard con border accent permanente
│   │
│   └── <div class="feed-mosaic">
│       └── PostCard × N (infinite scroll)
│
├── <div class="feed-sentinel">   ← intersection observer para infinite scroll
│
└── <footer> ornamento final
```

### Header del feed (feed-hero):
Mismo estilo que el hero actual que ya redesignamos — kaomoji sutil, titulo Kaisei Decol, subtitle. Pero ahora el subtitle viene del **profile table** en vez de homepage.json.

### Compose Drawer + Profile Panel:
Solo visibles si `authenticated`. Se detecta via `/api/feed/auth-check` al cargar.

### Infinite scroll:
- Cargar los ultimos 20 posts inicialmente.
- Un sentinel element al final del feed dispara `fetch('/api/feed/?cursor=...')`.
- Los nuevos posts se appenden al mosaic con fade-in animation.

### Login flow (para visitantes que son Aris):
- Icono de candado `⛨` en el header (o en el footer, junto al status).
- Click → modal elegante con: titulo "acceso", campo de password, boton "entrar".
- POST a `/api/auth/login` → cookie se guarda → pagina se rehidrata mostrando compose drawer.

---

## 9. API Endpoints

### GET /api/feed/
```
Query params: cursor (post id), limit (default 20)
Response: {
  posts: Post[],
  next_cursor: number | null,
  profile: { displayName, subtitle, pfpUrl }
}
```
Posts ordenados por: pinned DESC, created_at DESC.

### POST /api/feed/create
```
Auth: required (aris_admin cookie)
Body: { body: string, media: MediaObj[], mood: string|null, pinned: boolean }
Response: { ok: true, post: Post }
```

### DELETE /api/feed/delete
```
Auth: required
Body: { id: number }
Response: { ok: true }
```
Tambien borra archivos media asociados del filesystem.

### POST /api/feed/upload
```
Auth: required
Body: FormData con archivo(s)
Response: { ok: true, media: MediaObj }
```
- **Imagenes**: convierte a WebP, resize max 1920px, genera thumbnail 400px.
- **Videos**: guarda original, genera thumbnail con ffmpeg (primer frame).
- **Documentos**: guarda original, no genera thumbnail.
- Guarda en `public/uploads/feed/` y `public/thumbs/feed/`.

### GET /api/feed/auth-check
```
Response: { authenticated: boolean, profile: ProfileObj | null }
```

### PATCH /api/feed/profile
```
Auth: required
Body: { displayName?: string, subtitle?: string, pfpUrl?: string }
Response: { ok: true, profile: ProfileObj }
```

---

## 10. Interactividad

### Hover en PostCard:
```css
.post-card {
  transition:
    border-color 0.3s var(--ease-out),
    box-shadow 0.3s var(--ease-out),
    transform 0.3s var(--ease-out);
}

.post-card:hover {
  border-color: var(--mood-border, var(--color-border-accent));
  box-shadow: var(--mood-glow, var(--glow-sm));
  transform: translateY(-3px);
}
```

### Click en PostCard:
- Si tiene media → abre MediaViewer (lightbox full-screen con blur de fondo).
- Si es solo texto → ripple sutil en la superficie del card.

### Scroll reveal:
- Posts aparecen con `opacity: 0 → 1` y `translateY(12px) → 0` cuando entran al viewport.
- Stagger de 60ms entre posts visibles simultaneamente.

### Pinned post:
- Borde permanente con `--color-accent`.
- Badge "fijado" en mono font.
- Siempre al top del mosaic, no respeta el orden cronologico.

### Compose drawer:
- Slides up desde abajo con `transform: translateY(100%) → 0`.
- Backdrop blur oscuro detras.
- Textarea auto-resize.
- Upload con progress bar.
- Publicar con boton que muestra "✓" animado al exito.

### MediaViewer:
- Full-screen overlay con backdrop blur.
- Imagen centrada con zoom on click.
- Video con player nativo.
- Documento con preview o link de descarga.
- Cerrar con click fuera, Escape, o X.

---

## 11. Media Layout dentro del Post

Un post puede tener multiples media. Se layean asi:

### 1 imagen:
- Full width del card, aspect-ratio natural.
- Border-radius abajo.

### 2 imagenes:
- Grid 2 columnas iguales.

### 3 imagenes:
- 1 grande arriba (2 cols), 2 pequenas abajo (1 col cada una).

### 4+ imagenes:
- Grid 2x2 con la posibilidad de "ver mas".

### 1 video:
- Full width, con play button overlay. Click → MediaViewer.

### 1 documento:
- Card compacta con icono de tipo (PDF, DOC, etc), nombre, size, link de descarga.

### Mixto (imagen + documento):
- Imagen arriba full, documento abajo compacto.

---

## 12. Seguridad

### Cookie `aris_admin`:
Ya es: `httpOnly`, `secure`, `sameSite: strict`, HMAC-SHA256.

### Mejoras propuestas:
1. **CSRF protection**: agregar un header custom `X-Session-Verify` que el cliente envia con el valor de la cookie. El middleware verifica ambos. Esto previene CSRF even con `sameSite: strict` (defensa en profundidad).
2. **Rate limiting**: en `/api/auth/login`, max 5 intentos por IP en 10 minutos. Implementar con un simple `Map<ip, {count, resetAt}>` en memoria.
3. **Upload validation**: verificar MIME type real (no solo extension), limitar sizes (imagen 10MB, video 100MB, doc 20MB), sanitizar nombres de archivo.
4. **Path traversal**: nombres de archivo generados con `randomUUID()`, nunca usar el nombre original del usuario.
5. **Content Security**: el body del post se renderiza como texto con markdown-lite basico. No HTML raw. Sanitizar cualquier input.

### No cambiamos:
- El password hash ya es PBKDF2-SHA256 con 260k iterations. Es seguro.
- La cookie ya tiene 8h expiry. Podriamos extender a 30 dias con un refresh mechanism, pero 8h esta bien para seguridad.

---

## 13. Eliminacion de "inspirado por nownownow.com"

Simplemente quitamos el parrafo de `/now`. Ya no se menciona.

---

## 14. Archivos a Crear/Modificar

### Crear:
1. `src/lib/feed.ts` — queries SQLite para posts + profile
2. `src/lib/media.ts` — procesamiento de uploads (resize, thumb, MIME check)
3. `src/pages/api/feed/index.ts` — GET posts
4. `src/pages/api/feed/create.ts` — POST crear post
5. `src/pages/api/feed/delete.ts` — DELETE borrar post
6. `src/pages/api/feed/upload.ts` — POST subir media
7. `src/pages/api/feed/auth-check.ts` — GET auth status
8. `src/pages/api/feed/profile.ts` — PATCH actualizar profile
9. `src/features/feed/FeedGrid.astro` — mosaico organico
10. `src/features/feed/PostCard.astro` — card de un post
11. `src/features/feed/ComposeDrawer.astro` — formulario de compose
12. `src/features/feed/ProfilePanel.astro` — panel de perfil
13. `src/features/feed/MediaViewer.astro` — lightbox
14. `src/features/feed/FeedClient.ts` — logica cliente (infinite scroll, compose, delete)
15. `scripts/init-feed-tables.ts` — migracion para crear tables

### Modificar:
1. `src/pages/index.astro` — reescribir como feed
2. `src/pages/now.astro` — quitar "inspirado por nownownow.com"
3. `src/middleware.ts` — agregar rutas `/api/feed/*` protegidas
4. `src/layouts/Base.astro` — agregar clases CSS para feed components

---

## 15. Orden de Implementacion

### Fase 1: Backend (fundacion)
1. Crear `scripts/init-feed-tables.ts` y correrlo para crear las tables.
2. Crear `src/lib/feed.ts` con todas las queries.
3. Crear `src/lib/media.ts` con procesamiento de uploads.
4. Crear todos los API endpoints.

### Fase 2: Frontend (visual)
5. Crear `PostCard.astro` con todos los estilos.
6. Crear `FeedGrid.astro` con el mosaico CSS.
7. Reescribir `index.astro` como feed page.
8. Crear `MediaViewer.astro`.

### Fase 3: Interactividad (compose + auth)
9. Crear `ComposeDrawer.astro`.
10. Crear `ProfilePanel.astro`.
11. Crear `FeedClient.ts` con infinite scroll + compose logic.
12. Actualizar middleware.
13. Quitar nownownow de `/now`.

### Fase 4: Polish
14. Animaciones de entrada (stagger, scroll reveal).
15. Mood colors en bordes/glow.
16. Responsive mobile.
17. Testing manual.

---

## 16. Consideraciones de Performance

- **Imagenes**: siempre WebP, max 1920px. Thumbnails de 400px para el mosaic. El mosaic carga thumbnails, no originales.
- **Infinite scroll**: cargar 20 posts por pagina. El sentinel usa IntersectionObserver.
- **DB queries**: `posts` con indice en `created_at DESC`. Las queries son simples y rapidas en SQLite.
- **Upload processing**: sincrono en el request (Bun es rapido). Si el video es muy grande, podriamos hacerlo async con un status poll, pero para un blog personal de una persona, sync esta bien.
- **Cache**: no necesitamos cache de CDN para un sitio personal. El SSR de Astro ya genera el HTML.

---

## Nota sobre estetica

Este feed NO se ve como Twitter. Se ve como el jardin de Aris — oscuro, onirico, con destellos de color. Cada post es una ventana a un pensamiento, no un tweet en un timeline. El mosaico organico respira. Los moods tiñen el ambiente. La pfp circular con glow rosa es el ancla visual que conecta todo. No hay notificaciones, no hay likes, no hay retweets. Es un monologo personal, hermoso y privado.
