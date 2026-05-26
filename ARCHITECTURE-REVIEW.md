# Architectural Review: misitio (aris-sama)

**Date:** April 26, 2026
**Reviewer:** Hermes Agent
**Status:** Review complete, fixes applied

---

## Overview

misitio is a personal portfolio site built with Astro 6 + Bun + Tailwind v4 on Oracle Cloud ARM. It features a Steam-kawaii themed UI with modules for gacha showcase (Genshin/HSR/ZZZ), video gallery with Discord OG embeds, danmaku music visualizer, AniList integration, llama.cpp chat, and a full admin panel. SQLite for persistence, Caddy for TLS.

---

## Architecture

### Main Components

```
src/
  layouts/Base.astro        -- Shell (sidebar, topbar, audio bus)
  pages/                     -- Routes + API endpoints (14 files)
  features/                  -- Reusable UI components (10 modules)
  lib/                       -- Shared utilities (NEW: auth, db, data, env, response, types)
  blocks/registry.ts         -- Dynamic page composition
data/                        -- JSON configs + SQLite database
scripts/                     -- DB init, Enka sync, maintenance
public/uploads/ + thumbs/    -- User-uploaded videos + auto-thumbnails
```

### Data Flow

```
Browser --> Caddy:443 --> web:4321 (Astro SSR)
                              |
                     +--------+--------+
                     |        |        |
                  SQLite   JSON      External
                 (characters,  (data/*.json)  (AniList,
                  videos,                      llama.cpp,
                  comments)                    yt-dlp)
```

### Key Technologies

- **Runtime:** Bun (standalone Astro SSR via @astrojs/node)
- **Database:** SQLite via bun:sqlite (data/database.sqlite)
- **Auth:** PBKDF2-SHA256 login + HMAC-SHA256 session tokens
- **LLM Backend:** llama.cpp (Gemma 4) via host Docker
- **Deployment:** Docker Compose (web + Caddy), Oracle Cloud ARM64

---

## Findings

### Critical Issues (FIXED)

1. **XSS in GachaGrid.astro** -- The `loadPanel()` function built character cards via `innerHTML` with raw API data (`c.name`, `c.imageUrl`, `c.element`). A malicious DB value could inject arbitrary HTML/JS. **Fixed:** Replaced all `innerHTML +=` with `document.createElement()` + `textContent` (DOM-safe APIs).

2. **Hardcoded CHAT_PASSWORD in chat.ts** -- Password was a string literal in source code. **Fixed:** Now reads from `CHAT_PASSWORD()` via `lib/env.ts`.

3. **Corrupted env.ts function signatures** -- Lines 29-31 had `***` instead of `(): string`, breaking the module at import time. **Fixed:** Restored proper `(): string =>` syntax.

### High Priority (FIXED)

4. **Duplicated auth logic in 3 files** -- `verifyToken()` + cookie extraction was copy-pasted across `login.ts`, `upload.ts`, `update.ts`, and `admin/data.ts` (4 separate implementations, each slightly different). **Fixed:** All now import from `lib/auth.ts` (`isAdmin()`).

5. **Duplicated DB connection in 6 files** -- Each endpoint created its own `new Database(join(...))` inline. **Fixed:** All now import `getDb()` / `getReadDb()` from `lib/db.ts`. Read-only connections use `readonly: true` to avoid write lock contention.

6. **Duplicated JSON response construction** -- `new Response(JSON.stringify(...), { headers: {'Content-Type': 'application/json'} })` repeated everywhere. **Fixed:** Created `lib/response.ts` with `jsonResponse()`, `errorResponse()`, `okResponse()` helpers.

7. **Inline CREATE TABLE in upload.ts** -- Schema migrations ran on every upload request (ALTER TABLE in try/catch). **Fixed:** Removed from upload.ts. Schema management belongs in `scripts/init-db.ts`.

8. **Dead variable in enka-gi.ts** -- Line 6: `const CACHE: { data: unknown; ts: number } | null = null as any;` was unused (only `_cache` was used). **Fixed:** Removed in refactor.

9. **Missing .env.example** -- No template for required environment variables. **Fixed:** Created `.env.example` with all vars documented.

### Medium Priority (FIXED)

10. **CSS syntax error in GachaCard.astro** -- Line 122: `color: #//color-muted;` is invalid CSS (double slash comment doesn't exist in CSS). **Fixed:** Changed to `color: #94A3B8;`.

11. **Fragmented DB init scripts** -- 3 separate scripts (`init-gacha-db.ts`, `init-videos-db.ts`, `init-comments-db.ts`) with inconsistent schemas. **Fixed:** Created unified `scripts/init-db.ts` with all 3 tables + idempotent column additions.

12. **Missing `writeJsonString` in lib/data.ts** -- Admin data endpoint needed to write pre-validated JSON strings. **Fixed:** Added `writeJsonString()` and `writeJson()` to `lib/data.ts`.

### Remaining Items (Not Fixed, Advisory)

13. **No @types/bun in devDependencies** -- tsc reports ~40 errors for `bun:sqlite`, `process`, `Bun`, etc. These are false positives at runtime (Bun provides these globals), but IDE tooling would benefit from `@types/bun`. Add to devDependencies.

14. **SQLite write concurrency** -- bun:sqlite opens a new connection per request. Under concurrent writes, this can cause `SQLITE_BUSY`. Consider using a shared connection with a write lock (similar to the aiosqlite pattern from other projects). Low risk currently since write endpoints are admin-only.

15. **Dockerfile copies src/ into production image** -- The builder stage copies all source files into the runner. Only `dist/`, `node_modules/`, `package.json`, `scripts/`, and `data/` are needed at runtime. Reducing the image size by excluding `src/` from the runner stage would be a minor optimization.

16. **audio-stream.ts not refactored** -- This endpoint uses `child_process.spawn` for yt-dlp and has its own inline logic. It's functionally correct but doesn't use the lib/ modules. Low priority since it's self-contained.

17. **anime.ts not refactored** -- Similar to audio-stream, it's self-contained with its own cache. Could use `lib/response.ts` for consistency but it's not urgent.

---

## Files Modified

| File | Change |
|------|--------|
| `src/lib/env.ts` | Fixed corrupted function signatures |
| `src/lib/data.ts` | Added `writeJsonString()`, `writeJson()` |
| `src/lib/response.ts` | NEW -- JSON response helpers |
| `src/lib/index.ts` | NEW -- Barrel exports |
| `src/lib/types.ts` | Already existed (unchanged) |
| `src/pages/api/auth/login.ts` | Uses `lib/env` (removed inline env access) |
| `src/pages/api/auth/logout.ts` | Minor cleanup |
| `src/pages/api/admin/data.ts` | Uses `lib/auth` + `lib/env` + `lib/data` + `lib/response` |
| `src/pages/api/videos/index.ts` | Uses `lib/db` + `lib/response` |
| `src/pages/api/videos/upload.ts` | Uses `lib/auth` + `lib/db` + `lib/env` + `lib/response` (removed inline CREATE TABLE) |
| `src/pages/api/videos/update.ts` | Uses `lib/auth` + `lib/db` + `lib/env` + `lib/response` |
| `src/pages/api/videos/comments.ts` | Uses `lib/db` + `lib/response` |
| `src/pages/api/enka-gi.ts` | Uses `lib/db` + `lib/response` (removed dead CACHE var) |
| `src/pages/api/enka-hsr.ts` | Uses `lib/db` + `lib/response` |
| `src/pages/api/enka-zzz.ts` | Uses `lib/db` + `lib/response` |
| `src/pages/api/chat.ts` | Uses `lib/env` (removed hardcoded password) |
| `src/pages/api/nav.ts` | Uses `lib/data` + `lib/response` |
| `src/features/gacha/GachaGrid.astro` | XSS fix: innerHTML -> DOM APIs |
| `src/features/gacha/GachaCard.astro` | Fixed CSS `#//color-muted` -> `#94A3B8` |
| `scripts/init-db.ts` | NEW -- Unified schema init |
| `.env.example` | NEW -- Environment variable template |

---

## Recommendations

1. **Immediate:** Add `@types/bun` to devDependencies for IDE support
2. **Short-term:** Consider a shared DB connection with write lock for production concurrency
3. **Short-term:** Slim the Docker runner stage (exclude `src/`)
4. **Ongoing:** Refactor `audio-stream.ts` and `anime.ts` to use `lib/response.ts` for consistency
5. **Future:** Consider rate limiting on the comments endpoint (currently unauthenticated writes)

---

## To Run This Codebase

Required environment variables:
- `ADMIN_HASH`, `ADMIN_SALT`, `ADMIN_ITERATIONS`, `ADMIN_JWT_SECRET`
- `CHAT_PASSWORD`, `LLAMA_URL` (optional, has defaults)

Steps:
```bash
cp .env.example .env   # Fill in values
bun install
bun run scripts/init-db.ts   # Initialize SQLite tables
docker compose up -d --build  # Production
# OR
bun run dev                    # Development
```

Blockers: None. All env vars are documented in `.env.example`.
