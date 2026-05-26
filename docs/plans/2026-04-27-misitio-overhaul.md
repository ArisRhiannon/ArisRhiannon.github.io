# misitio Overhaul — Implementation Plan

> **For Hermes:** Execute tasks sequentially. Each task touches distinct files. Build and verify after each batch.

**Goal:** Fix all review findings, overhaul videos page, create standalone guestbook page, improve transitions and post cards.

**Architecture:** Astro 6 SSR + Bun + SQLite. All changes are UI/layout/CSS + minor API fixes. No new dependencies.

**Tech Stack:** Astro 6, Tailwind v4, vanilla JS/TS, CSS custom properties from public/design-tokens.css.

---

## Phase 1 — Security Fixes

### Task 1: Fix CSRF protection
**Files:** Modify `astro.config.mjs:10`
**Change:** `checkOrigin: false` → `checkOrigin: true`

### Task 2: Add auth to DELETE /api/videos
**Files:** Modify `src/pages/api/videos/index.ts:21-44`
**Change:** Add `isAdmin()` check before DELETE handler. Import from auth lib.

### Task 3: Fix .env.example formatting
**Files:** Modify `.env.example:15-20`
**Change:** Fix concatenated lines. Separate ADMIN_JWT_SECRET comment from CHAT_PASSWORD section.

### Task 4: Delete stale files
**Files:** Delete root-level `design-tokens.css`, `{public,src/` directory
**Command:** `rm -rf "/home/ubuntu/misitio/design-tokens.css" "/home/ubuntu/misitio/{public,src"`

---

## Phase 2 — New Guestbook Page + Nav

### Task 5: Create /guestbook page
**Files:** Create `src/pages/guestbook.astro`
**Design:** Full-page guestbook with:
- Atmospheric hero section with glow effects
- 3-column responsive message wall (masonry-like grid)
- Each entry: glass card with emoji, name, message, timestamp, subtle border
- Enhanced form: emoji picker, name input, message (all styled with the dark yume aesthetic)
- Floating particles/bokeh background
- Real-time entry animation on submit
- Admin delete buttons (visible to authenticated users)
- Uses Base layout, fetches from /api/guestbook

### Task 6: Update nav in Base.astro
**Files:** Modify `src/layouts/Base.astro:15-21`
**Change:** Add `{ label: 'guestbook', href: '/guestbook' }` after 'anime' in navItems array.

### Task 7: Remove guestbook from main page
**Files:** Modify `src/pages/index.astro:22-23`
**Change:** Remove `<Guestbook authenticated={authenticated} />` import and component. Remove `import Guestbook` line.

---

## Phase 3 — Videos Page Overhaul

### Task 8: Rewrite /videos page
**Files:** Rewrite `src/pages/videos.astro`
**Design:**
- Hero: "galeria" with cyan glow chip, video count
- Category filters as floating pill bar
- Grid: masonry layout with `columns: 3` CSS (not flex/grid)
- Each card: 16:9 thumb with play overlay on hover, title, category badge, descriptor tags
- Cards have hover lift + glow effect
- Better empty state
- Responsive: 3 cols desktop, 2 tablet, 1 mobile

### Task 9: Improve /v/[id] single video page
**Files:** Modify `src/pages/v/[id].astro`
**Changes:**
- Add Base layout wrapper (currently standalone HTML)
- Better player styling with rounded corners and shadow
- Move comments to collapsible section
- Add video metadata display (resolution, duration if available)
- Better share button styling

---

## Phase 4 — Page Transitions (Temporal Flow)

### Task 10: Replace page transition system
**Files:** Modify `src/layouts/Base.astro`, `src/scripts/micro-interactions.ts`
**Design:** Replace the radial-wipe overlay with a "temporal dissolve" transition:
- On navigation: current page gently fades down and blurs slightly (like sinking into water)
- New page: fades in from above, sharpening into focus
- Duration: 400ms, cubic-bezier(0.4, 0, 0.2, 1) for smooth flow
- No overlay element — use CSS `view-transition` API with `astro:transitions`
- Custom `::view-transition-old`: `animation: dissolve-out 0.4s ease-in both` (fade + translateY(8px) + blur(4px))
- Custom `::view-transition-new`: `animation: dissolve-in 0.4s ease-out both` (fade + translateY(-8px→0) + blur(0))
- Remove the old `#page-overlay` element and its CSS from Base.astro

---

## Phase 5 — Post Card Improvements

### Task 11: Add typewriter subtitle to post cards
**Files:** Modify `src/features/feed/PostCard.astro`
**Design:** 
- Below the post body, add a `<span class="post-subtitle-typer">` element
- On page load, each post's subtitle (profile.subtitle) types itself letter by letter
- Once fully typed, stays static (no delete cycle)
- Use `IntersectionObserver` to only start typing when post enters viewport
- Typing speed: 40ms per char
- Cursor disappears after typing finishes
- Styled as small mono text in muted color

### Task 12: Fix image cropping in posts
**Files:** Modify `src/features/feed/PostCard.astro` CSS
**Current issue:** `object-fit: cover` crops images. 
**Fix:** Change to `object-fit: contain` for single images (preserve full image). For multi-image grids, keep `cover` for consistent grid look.
**Also:** Add `background: var(--color-surface-2)` behind images so the letterbox area is themed.

### Task 13: Fix post card adaptive sizing
**Files:** Modify `src/features/feed/PostCard.astro` + `FeedGrid.astro`
**Current issue:** Cards use `grid-row: span X` with fixed pixel estimates that don't work well.
**New approach:** Remove CSS grid `grid-auto-rows: 10px` with manual spans. Switch FeedGrid to use CSS `columns` (masonry) OR use `grid-template-columns: repeat(auto-fill, minmax(300px, 1fr))` with `grid-auto-rows: auto` — no manual row spans. Let content determine height naturally.
**For PostCard:**
- Remove `calcRowSpan()` function
- Remove `style="grid-row: span ..."` attribute
- Set `height: fit-content` on cards
- Media images get `aspect-ratio` based on their actual dimensions
- Text-only posts get compact padding

---

## Phase 6 — Build & Verify

### Task 14: Build and verify
**Command:** `cd /home/ubuntu/misitio && bun run build`
**Expected:** Build passes. No import errors, no CSS issues.

---

## Execution Order
Tasks are sequential within phases. Phases 1-2 can be parallelized with subagents since they touch different files. Phases 3-4-5 must be sequential (they may overlap on Base.astro).
