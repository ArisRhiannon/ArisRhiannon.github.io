# misitio v3.0 — Full Refactor & Hardening Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.
> Each task is self-contained and 2-5 minutes. Commit after every task.

**Goal:** Refactor misitio into a hardened, well-organized, production-grade Astro 6 codebase. Eliminate all duplication, fix security bugs, clean up stale files, and establish clean patterns for the upcoming v3 rebuild.

**Architecture:** Establish `src/lib/` as the single source of truth for shared utilities (auth, db, sync, validation). Extract all duplicated logic. Hardcode nothing. Enforce auth everywhere. Remove all dead code, backup files, and unused scaffolding.

**Tech Stack:** Astro 6 + Bun + Tailwind v4 + SQLite (bun:sqlite) + TypeScript strict

**Total estimated effort:** ~45 tasks, ~2.5–3 hours

---

## Phase A — Clean Slate (housekeeping)

### Task A1: Remove stale danmaku backup files

**Objective:** Delete 6 `.bak` files cluttering `src/features/danmaku/`

**Files:**
- Delete: `src/features/danmaku/DanmakuVisualizer.astro.bak`
- Delete: `src/features/danmaku/DanmakuVisualizer.astro.bak_1774686876`
- Delete: `src/features/danmaku/DanmakuVisualizer.astro.bak_1774687209`
- Delete: `src/features/danmaku/DanmakuVisualizer.astro.bak_1774687410`
- Delete: `src/features/danmaku/DanmakuVisualizer.astro.bak_1774687677`
- Delete: `src/features/danmaku/DanmakuVisualizer.astro.bak_1774689904`
- Delete: `src/features/danmaku/DanmakuVisualizer.astro.bak_1774689972`

**Verification:**
Run: `ls src/features/danmaku/*.bak*` → "No such file"

**Commit:**
```bash
git add src/features/danmaku/
git commit -m "chore: remove stale danmaku backup files"
```

---

### Task A2: Remove orphaned root files

**Objective:** Delete files that clearly don't belong: `=` (equals sign), `unpacking`, and `aris_song.opus`

**Files:**
- Delete: `=` (orphaned named file)
- Delete: `unpacking` (empty file)
- Delete: `aris_song.opus` (2.5MB audio, likely migrated to mp3)

**Verification:**
Run: `ls = unpacking aris_song.opus 2>&1` → "No such file"

**Commit:**
```bash
git rm = unpacking aris_song.opus
git commit -m "chore: remove orphaned root files"
```

---

### Task A3: Remove unused `{public,src` directory

**Objective:** This oddly-named directory (`{public,src`) is a shell glob error artifact.

**Files:**
- Delete: `{public,src` (and all contents)

**Verification:**
Run: `ls -d '{public,src}'` → "No such file"

**Commit:**
```bash
git rm -r '{public,src}'
git commit -m "chore: remove artifact directory {public,src}"
```

---

### Task A4: Remove stale `apply_*.py` scripts

**Objective:** These 14 Python scripts in root were used for v2 deployment patching. Not needed as source files.

**Files to move to `scripts/archive/` or delete:**
- `apply_admin_v2.py`, `apply_comments_fix.py`, `apply_danmaku.py`, `apply_danmaku_v4.py`
- `apply_fase2_completo.py`, `apply_fix_uploads.py`, `apply_fixes_v3.py`, `apply_hotfix_v3b.py`
- `apply_modules_completos.py`, `apply_visual_nier.py`
- `fix_cursor.py`, `fix_cursor_v2.py`, `fix_fase2.py`, `restore_danmaku_v5.py`

**Step 1:** Create `scripts/archive/` directory
**Step 2:** Move all apply/fix/restore Python files there
**Step 3:** Move all `deploy_*.sh` files there too (they're historical)

**Verification:**
Run: `ls *.py deploy_*.sh 2>&1 | head -5` → "No such file" (root is clean)

**Commit:**
```bash
mkdir -p scripts/archive
git mv apply_*.py fix_*.py restore_*.py deploy_*.sh stellar_diag.sh scripts/archive/
git commit -m "chore: archive historical deployment scripts"
```

---

### Task A5: Rewrite README.md

**Objective:** Replace the default Astro starter template with a real project README.

**File:**
- Replace: `README.md`

```markdown
# misitio — aris-sama

Personal portfolio site. Steam-kawaii UI with sidebar nav, radio player,
gacha showcase (Genshin/HSR/ZZZ), video gallery with Discord embeds,
danmaku music visualizer, AniList integration, and admin panel.

## Stack

Astro 6 · Bun · Tailwind v4 · SQLite · Caddy · Docker · Oracle Cloud ARM

## Quick Start

```bash
# Clone and set .env
cp .env.example .env
# Fill in ADMIN_HASH, ADMIN_SALT, ADMIN_ITERATIONS, ADMIN_JWT_SECRET

# Dev
bun install
bun run dev          # http://localhost:4321

# Production
docker compose up -d --build
```

## Project Layout

```
src/
  layouts/Base.astro       # Shell layout (sidebar, topbar, audio analysis bus)
  pages/                    # Route pages and API endpoints
  features/                 # Reusable UI components
  lib/                      # Shared utilities (auth, db, sync, validation)
  blocks/                   # Dynamic page composition block registry
data/                       # JSON configs + SQLite database
scripts/                    # DB init, data sync, maintenance
public/uploads/             # User-uploaded videos
public/thumbs/              # Auto-generated video thumbnails
```

## Modules

| Module   | Route        | Description |
|----------|-------------|-------------|
| homepage | /           | Dynamic blocks from data/homepage.json |
| now      | /now        | What I'm doing right now |
| videos   | /videos     | Video gallery with comments |
| v/[id]   | /v/[id]     | Single video with Discord OG embed |
| gacha    | /gacha      | Genshin/HSR/ZZZ character roster |
| danmaku  | /danmaku    | Audio-reactive music visualizer |
| anime    | /anime      | AniList anime list viewer |
| chat     | /chat       | llama.cpp chat interface |
| onirico  | /onirico    | Generative focus mode |
| admin    | /admin      | Full admin panel (upload, edit, stats) |

## Deployment

```bash
docker compose up -d --build
```

Caddy handles auto-HTTPS via duckdns.org. SQLite and uploads are volume-mounted.

See `AGENTS.md` for detailed architecture and operational rules.
```

**Commit:**
```bash
git add README.md
git commit -m "docs: rewrite README with real project info"
```

---

## Phase B — Extract Shared Library (src/lib/)

### Task B1: Create `src/lib/auth.ts` — unified auth utilities

**Objective:** Extract the `verifyToken` function (duplicated in 4 places) into a single shared module, plus a factory function for extracting the admin token from cookie headers.

**Files:**
- Create: `src/lib/auth.ts`

```typescript
/**
 * src/lib/auth.ts
 * Unified authentication utilities.
 *
 * Token format: base64(payload).base64(signature)
 * Payload: { ts: number }
 * Signature: HMAC-SHA256(payload, ADMIN_JWT_SECRET)
 * Validity: 8 hours from creation
 */

const SESSION_MAX_AGE = 8 * 60 * 60 * 1000; // 8 hours

/**
 * Verify an aris_admin token (HMAC-SHA256).
 * Returns true if the token is valid and not expired.
 */
export async function verifyToken(token: string, secret: string): Promise<boolean> {
  try {
    const dot = token.lastIndexOf(".");
    if (dot < 0) return false;

    const payload = token.slice(0, dot);
    const sigB64 = token.slice(dot + 1);

    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["verify"],
    );

    const sigBytes = Uint8Array.from(atob(sigB64), (c) => c.charCodeAt(0));
    const valid = await crypto.subtle.verify(
      "HMAC",
      key,
      sigBytes,
      new TextEncoder().encode(payload),
    );
    if (!valid) return false;

    // Check expiration
    const { ts } = JSON.parse(atob(payload));
    return Date.now() - ts < SESSION_MAX_AGE;
  } catch {
    return false;
  }
}

/**
 * Extract the aris_admin token from a Request's Cookie header.
 * Returns the decoded token string, or undefined if not present.
 */
export function extractAdminToken(request: Request): string | undefined {
  const cookie = request.headers.get("cookie") ?? "";
  const raw = cookie
    .split(";")
    .find((c) => c.trim().startsWith("aris_admin="));
  if (!raw) return undefined;
  return decodeURIComponent(raw.slice(raw.indexOf("=") + 1).trim());
}

/**
 * Check if an incoming request is authenticated as admin.
 * Returns true if the token is valid.
 */
export async function isAdmin(request: Request, secret: string): Promise<boolean> {
  const token = extractAdminToken(request);
  if (!token) return false;
  return verifyToken(token, secret);
}
```

**Verification:**
Run: `wc -l src/lib/auth.ts` → ~70 lines

**Commit:**
```bash
git add src/lib/auth.ts
git commit -m "feat(lib): extract unified auth utilities to src/lib/auth.ts"
```

---

### Task B2: Create `src/lib/db.ts` — unified database connection

**Objective:** Eliminate scattered `new Database(...)` calls. Single factory with read-only option.

**Files:**
- Create: `src/lib/db.ts`

```typescript
/**
 * src/lib/db.ts
 * Unified SQLite database connection factory.
 *
 * Always connects to data/database.sqlite from process.cwd().
 * Use readonly=true for read operations (avoids write locks).
 */

import { Database } from "bun:sqlite";
import { join } from "path";

const DB_FILENAME = "database.sqlite";

function dbPath(): string {
  return join(process.cwd(), "data", DB_FILENAME);
}

export function getDb(options?: { readonly?: boolean }): Database {
  return new Database(dbPath(), {
    readonly: options?.readonly ?? false,
  });
}

/**
 * Shorthand for read-only DB connections.
 */
export function getReadDb(): Database {
  return getDb({ readonly: true });
}
```

**Verification:**
Run: `wc -l src/lib/db.ts` → ~32 lines

**Commit:**
```bash
git add src/lib/db.ts
git commit -m "feat(lib): extract db connection factory to src/lib/db.ts"
```

---

### Task B3: Create `src/lib/data.ts` — unified JSON data reader

**Objective:** Replace scattered `readFileSync(join(...), 'utf-8')` with type-safe data readers.

**Files:**
- Create: `src/lib/data.ts`

```typescript
/**
 * src/lib/data.ts
 * Type-safe JSON data file readers.
 *
 * All data files live in /data/*.json.
 * Reads happen synchronously at Astro render time.
 */

import { readFileSync } from "fs";
import { join } from "path";

function dataPath(filename: string): string {
  return join(process.cwd(), "data", filename);
}

export function readJson<T = unknown>(filename: string): T {
  const raw = readFileSync(dataPath(filename), "utf-8");
  return JSON.parse(raw) as T;
}

/**
 * Try to read a JSON file, returning null if it doesn't exist.
 */
export function tryReadJson<T = unknown>(filename: string): T | null {
  try {
    return readJson<T>(filename);
  } catch {
    return null;
  }
}
```

**Verification:**
Run: `wc -l src/lib/data.ts` → ~32 lines

**Commit:**
```bash
git add src/lib/data.ts
git commit -m "feat(lib): extract JSON data reader to src/lib/data.ts"
```

---

### Task B4: Create `src/lib/env.ts` — environment variable access

**Objective:** Centralize all `import.meta.env.*` access so there's one place to check for missing variables.

**Files:**
- Create: `src/lib/env.ts`

```typescript
/**
 * src/lib/env.ts
 * Centralized environment variable access with fallback defaults.
 *
 * In Astro SSR, import.meta.env provides the .env values.
 * In scripts running via `bun run`, use Bun.env instead.
 */

// Astro SSR context
function getEnv(key: string): string {
  // @ts-expect-error - import.meta.env is available at runtime in Astro SSR
  if (typeof import.meta !== "undefined" && import.meta.env) {
    // @ts-expect-error
    return import.meta.env[key] ?? "";
  }
  // Fallback for scripts
  return (Bun as any).env[key] ?? process.env[key] ?? "";
}

export const ADMIN_HASH = (): string => getEnv("ADMIN_HASH");
export const ADMIN_SALT = (): string => getEnv("ADMIN_SALT");
export const ADMIN_ITERATIONS = (): number =>
  parseInt(getEnv("ADMIN_ITERATIONS") || "260000", 10);
export const ADMIN_JWT_SECRET = (): string => getEnv("ADMIN_JWT_SECRET");

export const CHAT_PASSWORD = (): string => getEnv("CHAT_PASSWORD");
export const LLAMA_URL = (): string =>
  getEnv("LLAMA_URL") || "http://host.docker.internal:8080/v1/chat/completions";
```

**Verification:**
Run: `wc -l src/lib/env.ts` → ~34 lines

**Commit:**
```bash
git add src/lib/env.ts
git commit -m "feat(lib): centralize env var access in src/lib/env.ts"
```

---

### Task B5: Create `src/lib/index.ts` — barrel export

**Objective:** Single import point for all shared utilities.

**Files:**
- Create: `src/lib/index.ts`

```typescript
export { verifyToken, extractAdminToken, isAdmin } from "./auth";
export { getDb, getReadDb } from "./db";
export { readJson, tryReadJson } from "./data";
export {
  ADMIN_HASH,
  ADMIN_SALT,
  ADMIN_ITERATIONS,
  ADMIN_JWT_SECRET,
  CHAT_PASSWORD,
  LLAMA_URL,
} from "./env";
```

**Commit:**
```bash
git add src/lib/index.ts
git commit -m "feat(lib): add barrel export"
```

---

## Phase C — Refactor API Endpoints

### Task C1: Refactor `src/pages/api/auth/login.ts` to use lib

**Objective:** Replace direct `import.meta.env.*` with centralized env + add rate limiting consideration (at minimum, validate env is configured).

**Files:**
- Modify: `src/pages/api/auth/login.ts`

Changes:
1. Remove `import.meta.env.ADMIN_*` lines
2. Import from `src/lib/env.ts` and `src/lib/index.ts`
3. Keep crypto logic (it's unique to this file, not duplicated)

```typescript
import type { APIRoute } from "astro";
import { ADMIN_HASH, ADMIN_SALT, ADMIN_ITERATIONS, ADMIN_JWT_SECRET } from "../../../lib/env";

// ... pbkdf2Verify and makeToken stay the same ...

export const POST: APIRoute = async ({ request, cookies }) => {
  let body: { password?: string };
  try { body = await request.json(); } catch { return new Response("bad request", { status: 400 }); }

  const { password } = body;
  if (!password) return new Response("missing password", { status: 400 });

  const hash = ADMIN_HASH();
  const salt = ADMIN_SALT();
  const iterations = ADMIN_ITERATIONS();
  const secret = ADMIN_JWT_SECRET();

  if (!hash || !salt || !secret) {
    return new Response("server misconfigured", { status: 500 });
  }

  const ok = await pbkdf2Verify(password, salt, hash, iterations);
  if (!ok) return new Response("unauthorized", { status: 401 });

  const token = await makeToken(secret);
  cookies.set("aris_admin", token, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/",
    maxAge: 8 * 60 * 60,
  });

  return new Response("ok", { status: 200 });
};
```

**Verification:**
Run: `grep "import.meta.env" src/pages/api/auth/login.ts` → no matches

**Commit:**
```bash
git add src/pages/api/auth/login.ts
git commit -m "refactor: login endpoint uses centralized env"
```

---

### Task C2: Refactor `src/middleware.ts` to use `src/lib/auth.ts`

**Objective:** Replace inline `verifySession` with the shared `verifyToken`.

**Files:**
- Modify: `src/middleware.ts`

```typescript
import { defineMiddleware } from "astro:middleware";
import { verifyToken } from "../lib/auth";
import { ADMIN_JWT_SECRET } from "../lib/env";

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Protected routes: all /admin/* except /admin/login
  if (pathname.startsWith("/admin") && pathname !== "/admin/login") {
    const session = context.cookies.get("aris_admin");
    const secret = ADMIN_JWT_SECRET();

    if (!session?.value || !(await verifyToken(session.value, secret))) {
      return context.redirect("/admin/login");
    }
  }

  return next();
});
```

**Verification:**
Run: `grep "crypto.subtle" src/middleware.ts` → no matches (crypto moved to lib)
Run: `wc -l src/middleware.ts` → ~20 lines (down from 39)

**Commit:**
```bash
git add src/middleware.ts
git commit -m "refactor: middleware uses shared auth lib"
```

---

### Task C3: Refactor `src/pages/api/videos/upload.ts`

**Objective:** Replace duplicated `verifyToken` + use shared `isAdmin`, `getDb`, and `getEnv`.

**Files:**
- Modify: `src/pages/api/videos/upload.ts`

Changes:
1. Remove the inline `verifyToken` function
2. Import `isAdmin` from lib/auth
3. Import `getDb` from lib/db
4. Import `ADMIN_JWT_SECRET` from lib/env
5. Replace `new Database(...)` with `getDb()`

The auth check becomes:
```typescript
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { getDb } from "../../../lib/db";

export const POST: APIRoute = async ({ request }) => {
  if (!(await isAdmin(request, ADMIN_JWT_SECRET()))) {
    return new Response("unauthorized", { status: 401 });
  }
  // ... rest stays the same ...
  const db = getDb();
  // ...
};
```

**Verification:**
Run: `grep "verifyToken\|verifySession" src/pages/api/videos/upload.ts` → no local definition

**Commit:**
```bash
git add src/pages/api/videos/upload.ts
git commit -m "refactor: video upload uses shared auth/db lib"
```

---

### Task C4: Refactor `src/pages/api/videos/update.ts`

**Objective:** Same treatment as upload — shared auth + db.

**Files:**
- Modify: `src/pages/api/videos/update.ts`

Same pattern: replace inline `verifyToken` + `new Database(...)` with lib imports.

**Commit:**
```bash
git add src/pages/api/videos/update.ts
git commit -m "refactor: video update uses shared auth/db lib"
```

---

### Task C5: Refactor `src/pages/api/admin/data.ts`

**Objective:** Replace inline `auth` function with shared `isAdmin`.

**Files:**
- Modify: `src/pages/api/admin/data.ts`

Remove the local `auth` function (lines 7-27), import `isAdmin` from lib/auth, `ADMIN_JWT_SECRET` from lib/env.

**Commit:**
```bash
git add src/pages/api/admin/data.ts
git commit -m "refactor: admin data api uses shared auth lib"
```

---

### Task C6: Fix DELETE /api/videos — add auth

**Objective:** The DELETE handler has NO auth check (critical bug). Add it.

**Files:**
- Modify: `src/pages/api/videos/index.ts`

Changes:
1. Add imports for `isAdmin` and `ADMIN_JWT_SECRET`
2. Add auth check at top of DELETE handler
3. dátummal

```typescript
import type { APIRoute } from "astro";
import { getDb } from "../../../lib/db";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";

// GET /api/videos — public, no auth needed
export const GET: APIRoute = async () => {
  try {
    const db = getDb({ readonly: true });
    const videos = db.query("SELECT * FROM videos ORDER BY created_at DESC").all();
    db.close();
    return json({ videos });
  } catch {
    return json({ videos: [] });
  }
};

// DELETE /api/videos?id=xxx — admin only
export const DELETE: APIRoute = async ({ request, url }) => {
  // Auth check
  if (!(await isAdmin(request, ADMIN_JWT_SECRET()))) {
    return json({ error: "unauthorized" }, 401);
  }

  const id = url.searchParams.get("id");
  if (!id) return json({ error: "id requerido" }, 400);

  try {
    const db = getDb();
    const row = db.query("SELECT filename FROM videos WHERE id = ?").get(id) as any;
    db.run("DELETE FROM videos WHERE id = ?", [id]);
    db.close();

    if (row?.filename) {
      const filePath = join(process.cwd(), "public", "uploads", row.filename);
      try {
        const exists = await Bun.file(filePath).exists();
        if (exists) await (await import("fs")).promises.unlink(filePath);
      } catch {}
    }
    return json({ ok: true });
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
```

Also add the missing `join` import.

**Commit:**
```bash
git add src/pages/api/videos/index.ts
git commit -m "fix(security): add auth check to DELETE /api/videos"
```

---

### Task C7: Refactor chat API — move secrets to env

**Objective:** Eliminate hardcoded PASSWORD and LLAMA_URL. Use env vars with sensible defaults.

**Files:**
- Modify: `src/pages/api/chat.ts`

```typescript
import type { APIRoute } from "astro";
import { CHAT_PASSWORD, LLAMA_URL } from "../../../lib/env";

const PASSWORD = CHAT_PASSWORD() || "***";
const LLAMA = LLAMA_URL();

export const POST: APIRoute = async ({ request }) => {
  const body = await request.json().catch(() => null);
  if (!body) return new Response("bad request", { status: 400 });

  const { password, messages } = body;
  if (password !== PASSWORD) {
    return new Response("unauthorized", { status: 401 });
  }

  const upstream = await fetch(LLAMA, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "gemma-4",
      messages,
      stream: true,
      temperature: 0.7,
      max_tokens: 4096,
    }),
  });

  if (!upstream.ok) {
    return new Response("llama.cpp error", { status: 502 });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
};
```

Add to `.env`:
```
CHAT_PASSWORD=***  (replace with real password)
LLAMA_URL=http://host.docker.internal:8080/v1/chat/completions
```

**Verification:**
Run: `grep 'const PASSWORD\|const LLAMA_URL' src/pages/api/chat.ts` → both use getEnv

**Commit:**
```bash
git add src/pages/api/chat.ts .env
git commit -m "refactor: chat api uses env vars instead of hardcoded values"
```

---

### Task C8: Refactor enka API endpoints to use shared db

**Objective:** All three enka-*.ts files use `new Database(...)`. Switch to `getDb()`.

**Files:**
- Modify: `src/pages/api/enka-gi.ts`
- Modify: `src/pages/api/enka-hsr.ts`
- Modify: `src/pages/api/enka-zzz.ts`

Each: replace `new Database(DB_PATH, { readonly: true })` with `getDb({ readonly: true })` from lib/db.

Also clean up the weird `CACHE: { data: unknown; ts: number } | null = null as any;` declaration (line 6-7 in enka-gi.ts) — the unused const `CACHE`.

**Commit:**
```bash
git add src/pages/api/enka-gi.ts src/pages/api/enka-hsr.ts src/pages/api/enka-zzz.ts
git commit -m "refactor: enka APIs use shared db lib"
```

---

### Task C9: Refactor page files to use `src/lib/data.ts`

**Objective:** Replace `readFileSync(join(process.cwd(), 'data', ...), 'utf-8')` patterns with `readJson()`.

**Files:**
- Modify: `src/pages/index.astro` — use `readJson` and `tryReadJson`
- Modify: `src/pages/now.astro` — use `readJson`
- Modify: `src/pages/videos.astro` — dispatched to lib/db for DB connection
- Modify: `src/pages/v/[id].astro` — use getDb
- Modify: `src/pages/gacha.astro` — use readJson

Each: Replace `JSON.parse(readFileSync(join(...)))` with `readJson('./data/filename.json')` or use the Data component import.

**Commit:**
```bash
git add src/pages/index.astro src/pages/now.astro src/pages/v/[id].astro src/pages/gacha.astro src/pages/videos.astro src/pages/admin/index.astro
git commit -m "refactor: pages use shared data/db lib"
```

---

## Phase D — Fix GachaGrid XSS Vulnerability

### Task D1: Sanitize GachaGrid innerHTML rendering

**Objective:** The GachaGrid renders character data via raw `innerHTML +=` template literals. The data comes from SQLite (synced from Enka API), which is trusted but constitutes a risk surface. At minimum, escape HTML in the data, or better: refactor to use DOM creation.

**Files:**
- Modify: `src/features/gacha/GachaGrid.astro` (the `<script>` block)

**Approach:** Wrap character data that goes into innerHTML with the `esc()` function (already defined in AnimeGrid):

```typescript
function esc(s: string): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
```

Then use `esc(c.name)`, `esc(c.element)`, etc. in the template literal.

Better yet: don't use innerHTML at all. Create elements programmatically:

```typescript
characters.forEach((c: any) => {
  const card = document.createElement("article");
  card.className = "gacha-card";
  card.style.setProperty("--game-color", color);
  // ... build DOM tree ...
  grid.appendChild(card);
});
```

**Verification:**
Run: `grep 'innerHTML +=' src/features/gacha/GachaGrid.astro` → no direct innerHTML += with unescaped data

**Commit:**
```bash
git add src/features/gacha/GachaGrid.astro
git commit -m "fix(security): sanitize GachaGrid rendering, replace innerHTML with DOM API"
```

---

## Phase E — Fix Architecture Issues

### Task E1: Fix GachaCard.astro broken CSS comment

**Objective:** Line 122 has `color: #//color-muted;` which is invalid CSS. Replace with the correct variable.

**Files:**
- Modify: `src/features/gacha/GachaCard.astro` line 122

```css
/* Before: */
.card-level { color: #//color-muted; }

/* After: */
.card-level { color: var(--color-muted, #A08890); }
```

**Verification:**
Run: `grep '#//'  src/features/gacha/GachaCard.astro` → no matches

**Commit:**
```bash
git add src/features/gacha/GachaCard.astro
git commit -m "fix: broken CSS in GachaCard (.card-level color)"
```

---

### Task E2: Establish `.env.example`

**Objective:** Provide a template without real secrets.

**Files:**
- Create: `.env.example`

```bash
# Admin authentication
ADMIN_HASH=                   # PBKDF2 hash (generate with scripts/gen-admin-hash.ts)
ADMIN_SALT=                   # 64 hex chars
ADMIN_ITERATIONS=260000
ADMIN_JWT_SECRET=             # 32+ char random string

# Chat (optional)
CHAT_PASSWORD=                # Shared password for chat access
LLAMA_URL=http://host.docker.internal:8080/v1/chat/completions
```

**Verification:**
Run: `ls -la .env.example` → file exists

**Commit:**
```bash
git add .env.example
git commit -m "chore: add .env.example template"
```

---

### Task E3: Add .gitignore entry for .env

**Objective:** Ensure the real `.env` is never committed again (it already has real secrets committed).

**Files:**
- Modify: `.gitignore`

Add line:

```
.env
public/uploads/*
public/thumbs/*
```

**Note:** The existing `.env` is already in git history. After this task, run:
```bash
git rm --cached .env
git commit -m "chore: remove .env from git tracking"
```

**Verification:**
Run: `grep '\.env' .gitignore` → matches

**Commit:**
```bash
git add .gitignore
git rm --cached .env
git commit -m "chore: gitignore .env and rot13 the committed version"
```

---

### Task E4: Update STRUCTURE.json

**Objective:** Reflect the new `src/lib/` directory in the structure manifest.

**Files:**
- Modify: `STRUCTURE.json`

Add:
```json
{
  "version": "3.0.0",
  "fase": 3,
  "notas": "Refactor completo. src/lib/ centraliza auth, db, data, env.",
  "modulos": {
    "lib": {
      "ruta": "/src/lib/",
      "estado": "nuevo",
      "descripcion": "Utilidades compartidas: auth, db, data, env"
    }
    // ... keep existing modules ...
  }
}
```

**Commit:**
```bash
git add STRUCTURE.json
git commit -m "docs: update STRUCTURE.json for v3 refactor"
```

---

### Task E5: Update AGENTS.md

**Objective:** Document the new `src/lib/` invariants.

**Files:**
- Modify: `AGENTS.md`

Add under "Reglas invariables":

```
7. Usar `src/lib/auth.ts` para verificar sesiones (NO escribir verifyToken inline)
8. Usar `src/lib/db.ts` getDb() para SQLite (NO new Database() directo)
9. Usar `src/lib/data.ts` readJson() para leer archivos de /data/
10. Usar `src/lib/env.ts` para acceder a variables de entorno
```

Update stack line to: "Fase 3 · Refactor completo".

**Commit:**
```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md for v3 lib patterns"
```

---

## Phase F — Database Schema Hardening

### Task F1: Create unified schema migration script

**Objective:** The `init-gacha-db.ts` creates tables but is outdated (missing columns: filename, descriptors, width, height on videos, missing comments table). The upload.ts does ALTER TABLE on every upload. Create one canonical schema definition.

**Files:**
- Replace: `scripts/init-gacha-db.ts`

Rename semantics to `scripts/init-db.ts`:

```typescript
/**
 * scripts/init-db.ts
 * Initialize all database tables. Idempotent (CREATE IF NOT EXISTS).
 * Run: bun run scripts/init-db.ts
 */
import { Database } from "bun:sqlite";

const db = new Database("data/database.sqlite");

db.run("PRAGMA journal_mode=WAL");
db.run("PRAGMA foreign_keys=ON");

// Characters (gacha roster from Enka)
db.run(`CREATE TABLE IF NOT EXISTS characters (
  id            TEXT PRIMARY KEY,
  game          TEXT NOT NULL,
  name          TEXT NOT NULL,
  level         INTEGER DEFAULT 1,
  rarity        INTEGER DEFAULT 4,
  element       TEXT,
  path          TEXT,
  constellation INTEGER DEFAULT 0,
  imageUrl      TEXT,
  synced_at     DATETIME DEFAULT CURRENT_TIMESTAMP
)`);

// Videos
db.run(`CREATE TABLE IF NOT EXISTS videos (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  filename    TEXT,
  url         TEXT NOT NULL,
  thumbnail   TEXT,
  category    TEXT,
  descriptors TEXT DEFAULT '{}',
  width       INTEGER DEFAULT 1920,
  height      INTEGER DEFAULT 1080,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)`);

// Comments
db.run(`CREATE TABLE IF NOT EXISTS comments (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id   TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  alias      TEXT NOT NULL,
  body       TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)`);

// Indexes
db.run("CREATE INDEX IF NOT EXISTS idx_comments_video ON comments(video_id)");
db.run("CREATE INDEX IF NOT EXISTS idx_characters_game ON characters(game)");

console.log("✅ Database initialized: data/database.sqlite");
console.log("   Tables: characters, videos, comments");
db.close();
```

Also delete the now-redundant `scripts/init-comments-db.ts` and `scripts/init-videos-db.ts`.

**Commit:**
```bash
git mv scripts/init-gacha-db.ts scripts/init-db.ts
git rm scripts/init-comments-db.ts scripts/init-videos-db.ts
git add scripts/init-db.ts
git commit -m "refactor(db): unified schema init with all tables+indexes"
```

---

### Task F2: Remove ALTER TABLE from upload handler

**Objective:** The upload.ts does 4 `ALTER TABLE ... ADD COLUMN` on every upload (try/catch pattern). These are migration bandaids. Remove them now that the schema init handles all columns.

**Files:**
- Modify: `src/pages/api/videos/upload.ts`

Remove lines 86-89:
```typescript
// Remove these:
try { db.run("ALTER TABLE videos ADD COLUMN filename TEXT"); }     catch {}
try { db.run("ALTER TABLE videos ADD COLUMN descriptors TEXT DEFAULT '{}'"); } catch {}
try { db.run("ALTER TABLE videos ADD COLUMN width INTEGER DEFAULT 1920"); }    catch {}
try { db.run("ALTER TABLE videos ADD COLUMN height INTEGER DEFAULT 1080"); }   catch {}
```

**Verification:**
Run: `grep 'ALTER TABLE' src/pages/api/videos/upload.ts` → no matches

**Commit:**
```bash
git add src/pages/api/videos/upload.ts
git commit -m "fix(db): remove bandaids ALTER TABLE from upload handler"
```

---

## Phase G — Configuration & Deployment

### Task G1: Review astro.config.mjs security flag

**Objective:** `checkOrigin: false` disables CSRF protection. Document why it's needed, or remove if not.

**Files:**
- Modify: `astro.config.mjs`

Add comment:
```typescript
// checkOrigin: false is required because Caddy terminates TLS and
// Astro sees the origin as http://web:4321 internally vs https:// externally.
// The actual CSRF protection is handled by Caddy's CSP header + JWT cookies.
```

**Commit:**
```bash
git add astro.config.mjs
git commit -m "docs: explain checkOrigin: false with Caddy TLS termination context"
```

---

### Task G2: Ensure docker-compose uses .env securely

**Objective:** The compose file mounts `.env` as `env_file`. Add a warning comment.

**Files:**
- Modify: `docker-compose.yml`

Add comment above `env_file`:
```yaml
    # .env must exist with real secrets. Use .env.example as template.
    # NEVER commit .env to git.
    env_file:
      - .env
```

**Commit:**
```bash
git add docker-compose.yml
git commit -m "docs: add security comment to docker-compose env_file"
```

---

## Phase H — Code Quality Final Pass

### Task H1: TypeScript strict — fix implicit any in codebase

**Objective:** Several places use `any` for DB query results. Add proper interfaces.

**Files:**
- Create: `src/lib/types.ts`

```typescript
export interface VideoRow {
  id: string;
  title: string;
  filename: string | null;
  url: string;
  thumbnail: string | null;
  category: string | null;
  descriptors: string;
  width: number;
  height: number;
  created_at: string;
}

export interface CharacterRow {
  id: string;
  game: string;
  name: string;
  level: number;
  rarity: number;
  element: string | null;
  path: string | null;
  constellation: number;
  imageUrl: string | null;
  synced_at: string;
}

export interface CommentRow {
  id: number;
  video_id: string;
  alias: string;
  body: string;
  created_at: string;
}
```

Use these types throughout API endpoints and pages instead of `any`.

**Commit:**
```bash
git add src/lib/types.ts
git commit -m "feat(lib): add TypeScript interfaces for DB rows"
```

---

### Task H2: Verify build still works

**Objective:** After all modifications, verify `bun run build` succeeds.

Run: `cd /home/ubuntu/misitio && bun run build`
Expected: Build succeeds, output in `dist/`.

If any import paths broke during refactoring, fix them here.

**Commit:**
```bash
git add -A
git commit -m "fix: resolve any build issues from refactor"
```

---

## Phase I — Documentation Sync

### Task I1: Create docs/ARCHITECTURE.md

**Objective:** Standalone architecture document for future contributors/AI agents.

**Files:**
- Create: `docs/ARCHITECTURE.md`

```markdown
# misitio Architecture

## Overview

Astro 6 SSR app. Astro renders `.astro` pages server-side. Client-side
JavaScript handles interactive features (radio, danmaku, gacha tabs, anime
filters, chat streaming, admin panel).

## Directory Map

src/pages/*.astro          → Public routes
src/pages/api/*.ts         → API endpoints (Astro APIRoute)
src/features/*/            → Reusable UI components
src/layouts/Base.astro     → Global shell (used by all public pages)
src/blocks/registry.ts     → Dynamic composition registry
src/lib/auth.ts            → JWT token verification
src/lib/db.ts              → SQLite connection factory
src/lib/data.ts            → JSON file reading
src/lib/env.ts             → Environment variable access
src/lib/types.ts           → TypeScript interfaces for DB rows
src/middleware.ts           → Admin route protection
data/*.json                 → Content configuration
data/database.sqlite        → SQLite (characters, videos, comments)
scripts/*.ts                → Maintenance (init-db, sync-enka-*)

## Data Flow

1. **Static pages** (/, /now): Read data/*.json at render time via readJson()
2. **Gacha** (/gacha): Page renders tabs SSR. Client fetches /api/enka-*
   which reads SQLite with 1h in-memory cache
3. **Videos** (/videos): Same pattern. /v/[id] does SSR DB lookup for OG meta
4. **Anime** (/anime): Client-only. Fetches /api/anime which proxies AniList
   GraphQL with 1h in-memory cache
5. **Chat** (/chat): Client sends password to /api/chat which proxies
   llama.cpp SSE streaming. Token-based session in sessionStorage
6. **Danmaku** (/danmaku): Pure client-side Web Audio API visualization
7. **Onirico** (/onirico): p5.js generative visuals. Audio synthesis via
   Web Audio API (no server interaction except page load)
8. **Admin** (/admin): JWT cookie auth. Uploads videos via multipart POST,
   edits data/*.json via /api/admin/data

## Auth

- Cookie: `aris_admin` (httpOnly, secure, sameSite=strict, 8h)
- Token: `base64({ts}).base64(HMAC-SHA256)` with ADMIN_JWT_SECRET
- Password: PBKDF2-SHA256 with ADMIN_SALT + ADMIN_ITERATIONS
- Middleware protects all /admin/* except /admin/login
- Individual API endpoints re-verify via isAdmin() from src/lib/auth.ts

## Deployment

Docker Compose: `web` (bun ./dist/server/entry.mjs) + `caddy` (reverse proxy + auto TLS)
- Build: `docker compose up -d --build`
- Views: Caddy → web:4321 (internal), Caddy → :443 (external)
- Volumes: data/ (SQLite), public/uploads/ (videos), public/thumbs/ (thumbnails)

## Pitfalls

- Sharp doesn't work on ARM64 → use @unpic/astro for images
- SQLite must be in volume, never in image
- bun:sqlite is Bun-specific, won't work with Node.js
- Docker internal: use host.docker.internal for llama.cpp access
```

**Commit:**
```bash
git add docs/ARCHITECTURE.md
git commit -m "docs: add architecture reference document"
```

---

## Final Verification Checklist

After all tasks complete, verify:

- [ ] `bun run build` succeeds
- [ ] `find src -name '*.ts' | xargs grep -l 'new Database'` → only `scripts/init-db.ts` and `src/lib/db.ts`
- [ ] `find src -name '*.ts' | xargs grep -l 'verifyToken\|verifySession'` → only `src/lib/auth.ts` (defines) and consumers (import it)
- [ ] `git status` → clean, all files accounted for
- [ ] `ls src/features/danmaku/*.bak*` → no results
- [ ] `ls *.py` → no results (deployment scripts archived)
- [ ] `.env` is NOT tracked by git
- [ ] `README.md` describes the actual project
- [ ] DELETE /api/videos requires auth
- [ ] Chat password comes from env, not hardcoded
- [ ] `data/database.sqlite` schema has all columns (no runtime ALTER TABLE)

---

> **Total tasks:** ~35
> **Estimated time:** 2-3 hours
> **Key result:** misitio v3.0 — hardened, deduplicated, lib-ified, ready for major feature work.