# Codebase Architectural Review: misitio

## Overview

misitio es un sitio web personal tipo "digital garden" / feed social para **Aris**, construido con Astro (SSR con adaptador Node), estilizado con un tema kawaii/pastel, y desplegado con Docker + Caddy como reverse proxy con TLS automatico via Let's Encrypt. Incluye un sistema de posts/feed, guestbook, reproductor de radio lo-fi, paginas de gacha/anime/videos/garden, y un panel de admin con autenticacion JWT.

## Architecture

```
[Internet]
    |
    v
[Caddy (reverse proxy, TLS, port 80/443)]
    |
    v  (HTTP internally)
[Astro SSR Node server (port 4321)]
    |
    +-- [SQLite (database.sqlite)] -- posts, reactions, guestbook, taglines
    +-- [JSON config files] -- gacha-config.json, anime-config.json, etc.
    +-- [File system] -- uploads/, thumbs/, music/
```

### Main Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| **Astro App** | `src/` | Sitio completo SSR con 79 archivos fuente |
| **Layout Base** | `src/layouts/Base.astro` | Layout principal, meta tags, canvas de fondo |
| **Paginas** | `src/pages/` | index, garden, now, videos, gacha, anime |
| **API Routes** | `src/pages/api/` | feed, reactions, guestbook, taglines, auth, chat, upload |
| **DB Layer** | `src/lib/db.ts` | better-sqlite3 con schema migrado |
| **Auth** | `src/lib/auth.ts` | JWT + bcrypt-like hash con salt configurable |
| **Chat API** | `src/pages/api/chat.ts` | Proxy a Google Gemini para chatbot |
| **Upload API** | `src/pages/api/upload.ts` | Subida de archivos con Sharp para thumbnails |
| **Docker** | `Dockerfile` + `docker-compose.yml` | Build multi-stage + Caddy |
| **Caddy** | `Caddyfile` | Reverse proxy, TLS auto, gzip, security headers |

### Key Technologies

- **Framework:** Astro 5.x (SSR mode, @astrojs/node adapter)
- **Runtime:** Node.js 22 (bookworm-slim)
- **Database:** SQLite (better-sqlite3) con schema auto-migration
- **Image Processing:** Sharp (thumbnails WebP)
- **LLM Backend:** Google Gemini (chat API proxy)
- **Reverse Proxy:** Caddy (auto-TLS via Let's Encrypt)
- **Domain:** aris-sama.duckdns.org (DuckDNS dynamic DNS)
- **Container:** Docker Compose (2 servicios: web + caddy)

### Data Flow

1. **Request** -> Caddy (TLS termination, gzip, security headers)
2. **Caddy** -> Astro Node server (HTTP :4321)
3. **Astro** -> SQLite (posts, reactions, guestbook, taglines)
4. **Astro** -> JSON files (gacha config, anime config, nav, now)
5. **Uploads** -> Sharp -> `/public/uploads/` + `/public/thumbs/` (served by Caddy directly for /uploads/*, /thumbs/*)
6. **Chat** -> `/api/chat` -> Google Gemini API (streaming SSE)

### Stats

- **Source files:** 79 (29 .astro, 43 .ts/.tsx, 7 other)
- **Lines of code:** ~5,134
- **Docker image:** 2.6 GB
- **Project size:** 2.0 GB (includes node_modules, uploads, etc.)
- **SQLite DB:** 64 KB (lightweight)

## Findings

### Critical Issues

1. **CHAT API KEY EXPOSED IN BROWSER** -- `/api/chat.ts` forwards the Gemini API key in server-side calls, which is correct. However, the endpoint has no rate limiting or CORS restrictions, meaning anyone can proxy requests through the chat endpoint to consume the Gemini API quota. **Recommendation:** Add rate limiting (per-IP) and consider requiring admin auth for chat usage.

2. **SQLite DB = 0 bytes on host** -- `data/misitio.db` is 0 bytes while `data/database.sqlite` is 64 KB. This suggests either a stale/unused DB file or a naming inconsistency. The actual DB used is `database.sqlite`. The empty `misitio.db` can be removed.

### High Priority

1. **No rate limiting on any API endpoint** -- Guestbook posts, reactions, tagline management, and chat all have zero rate limiting. Vulnerable to spam/abuse.

2. **Guestbook has no CAPTCHA or bot protection** -- Anyone can submit guestbook entries programmatically. The only protection is maxlength on fields.

3. **Upload endpoint lacks file type validation beyond extension** -- While Sharp will reject non-images, the upload handler should validate MIME types and enforce size limits server-side before processing.

4. **Docker image is 2.6 GB** -- The multi-stage build copies the entire Astro output plus node_modules. Could be reduced with a leaner production image (copy only dist + production deps).

5. **No HTTPS health check in docker-compose** -- The web service has no healthcheck defined. Docker can't detect if the Astro server becomes unresponsive.

### Medium Priority

1. **Inconsistent DB naming** -- `misitio.db` (empty) vs `database.sqlite` (active). Remove the empty one to avoid confusion.

2. **No database backups** -- SQLite file is the only data store with no backup mechanism. If corrupted, all posts/reactions/guestbook entries are lost.

3. **No CSRF protection** -- POST/DELETE API endpoints rely only on JWT auth. No CSRF tokens for form submissions.

4. **Hardcoded stream URLs in radio player** -- Radio streams are hardcoded in the server-rendered HTML. Should be configurable via a JSON file or API.

5. **CSP header is permissive** -- `script-src 'self' 'unsafe-inline'` allows inline scripts, weakening XSS protection. Astro's View Transitions require this, but consider using nonce-based CSP in the future.

6. **No logging/monitoring** -- No structured logging, error tracking, or uptime monitoring. Failures are silent.

### Low Priority

1. **gacha-characters.json is empty** (3 bytes = `{}`) -- The gacha page has no character data loaded.

2. **books.json is minimal** (68 bytes) -- Only placeholder data.

3. **Some CSS is inlined in Astro components** rather than in separate stylesheets -- minor maintainability concern.

4. **Favicon exists in 5 formats** (svg, 32px, 16px, 180px, ico) -- slightly redundant but not harmful.

## Recommendations

### Immediate
1. Add rate limiting to `/api/chat` and `/api/guestbook` endpoints
2. Remove the empty `data/misitio.db` file
3. Set up a cron job for SQLite backups (`cp database.sqlite database.sqlite.bak`)

### Short-term
1. Add bot protection to guestbook (simple honeypot field + timestamp check)
2. Add MIME type validation to upload endpoint
3. Add a Docker healthcheck for the web service
4. Reduce Docker image size by using a leaner production stage

### Ongoing
1. Implement structured logging (pino or similar)
2. Move hardcoded radio streams to a config file
3. Add CSRF tokens for state-changing endpoints
4. Consider nonce-based CSP instead of unsafe-inline

### Future
1. Add WebSocket support for real-time guestbook updates
2. Implement image optimization pipeline (automatic WebP conversion on upload)
3. Add a "now playing" display for the radio player by scraping stream metadata
4. Consider migrating from DuckDNS to a proper domain for better reliability

## To Run This Codebase

### Required
- Docker + Docker Compose
- `.env` file with: `ADMIN_HASH`, `ADMIN_SALT`, `ADMIN_ITERATIONS`, `ADMIN_JWT_SECRET`
- Google Gemini API key (for chat feature)
- Port 80 and 443 available on the host

### Steps
1. `cd /home/ubuntu/misitio`
2. Configure `.env` with admin credentials
3. `docker compose up -d --build`
4. Caddy will auto-provision TLS for `aris-sama.duckdns.org`

### Blockers
- DuckDNS must point to the server's public IP (currently configured: 140.84.189.100)
- Port 80/443 must be open in the firewall (OCI security list + iptables)

## Deployment Status

- **Web container:** Running (Astro SSR on port 4321)
- **Caddy container:** Running (ports 80/443, TLS active via Let's Encrypt)
- **All pages:** HTTP 200 (/, /garden, /now, /videos, /gacha, /anime)
- **All APIs:** HTTP 200 (/api/taglines, /api/feed/reactions, etc.)
- **Domain:** aris-sama.duckdns.org -> 140.84.189.100 (resolves correctly)
- **TLS certificate:** Valid, auto-renewed by Caddy
