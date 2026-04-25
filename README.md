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