# AGENTS.md
Última actualización: Marzo 2026 · Fase 2 completa

## Stack
Astro 6 + Bun + Tailwind v4 + Zod + Motion
Self-hosted: Oracle Cloud ARM (aarch64), Caddy reverse proxy
Deploy: `docker compose up -d --build`
Servidor de producción: `bun ./dist/server/entry.mjs`

## Reglas invariables
1. NUNCA modificar `/src/blocks/` sin autorización explícita
2. Para contenido: editar `/data/*.json` o `/content/*.md`
3. Para módulo nuevo: crear carpeta en `/src/features/[nombre]/`
4. Actualizar AGENTS.md y STRUCTURE.json al crear módulos
5. Para modificar archivos en servidor: generar script `apply_*.py`
6. Las páginas en `/src/pages/*.astro` son páginas COMPLETAS

## Infra crítica
- Caddy: `reverse_proxy web:4321`
- Adaptador: `@astrojs/node` standalone
- `docker-compose.override.yml` lanza: `bun ./dist/server/entry.mjs`
- Sharp falla en ARM: usar `@unpic/astro`
- SQLite en volumen Docker `/data/` — NUNCA dentro de la imagen
- Videos subidos en volumen `/public/uploads/` (montar en compose si se necesita persistencia)
- `.env`: ADMIN_HASH, ADMIN_SALT, ADMIN_ITERATIONS, ADMIN_JWT_SECRET

## Módulos activos
- [x] now        — /now, datos en /data/now.json
- [x] radio      — fixed bottom-right, soporta /public/aris_song.mp3 + stream fallback
- [x] gacha      — /gacha, API /api/enka-{gi,hsr,zzz}, SQLite tabla characters
- [x] videos     — /videos, /v/[id] (OG Discord), admin upload drag-drop, SQLite tabla videos
- [x] admin      — /admin (panel completo: upload, editors, stats), /admin/login

## Rutas de API
| Endpoint              | Método       | Descripción |
|---|---|---|
| /api/enka-gi          | GET          | Personajes Genshin desde SQLite |
| /api/enka-hsr         | GET          | Personajes HSR desde SQLite |
| /api/enka-zzz         | GET          | Personajes ZZZ desde SQLite |
| /api/videos           | GET, DELETE  | Lista / elimina videos |
| /api/videos/upload    | POST         | Sube video (multipart, auth requerida) |
| /api/videos/update    | PATCH        | Actualiza título/categoria/descriptores |
| /api/admin/data       | GET, POST    | Lee/escribe /data/*.json (auth requerida) |
| /api/auth/login       | POST         | Login → cookie aris_admin |
| /api/auth/logout      | POST         | Logout |

## Discord video embed
Compartir en Discord: usar la URL /v/[id] (NO /uploads/archivo.mp4)
La página /v/[id] tiene og:type=video.other + og:video:url apuntando al MP4
Discord cachea el video vía Discordbot — puede tardar unos segundos la primera vez

## Radio / audio local
Si existe /public/aris_song.mp3 → se usa como fuente del radio (loop)
Si no existe → fallback al stream externo
Para convertir FLAC: ffmpeg -i aris_song.flac -codec:a libmp3lame -qscale:a 2 public/aris_song.mp3

## Scripts de mantenimiento
| Script | Descripción |
|---|---|
| bun run scripts/init-gacha-db.ts  | Inicializa tablas characters + videos |
| bun run scripts/sync-enka-gi.ts   | Sync GI |
| bun run scripts/sync-enka-hsr.ts  | Sync HSR |
