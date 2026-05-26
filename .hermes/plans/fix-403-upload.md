# Fix 403 Upload — checkOrigin CSRF bloquea FormData

## Diagnóstico

HTTP 403 en POST con body `multipart/form-data` (imágenes, música).
Los POST con body `application/json` (texto) funcionan.

**Causa:** `checkOrigin: true` en `astro.config.mjs`. Astro verifica el header
`Origin` contra el host del request. Para requests `multipart/form-data` vía
`fetch()`, el navegador no siempre incluye `Origin` en same-origin → Astro
rechaza con 403 y HTML (no JSON) → cliente muestra "respuesta inválida".

**Por qué es seguro desactivarlo:** Todos los endpoints de escritura tienen
`isAdmin()` que verifica JWT desde cookie `aris_admin`. La cookie tiene
`httpOnly: true` + `sameSite: "lax"` → JavaScript no puede leerla y no se
envía en requests cross-site. CSRF ya está mitigado a nivel de cookie.

## Plan

1. `astro.config.mjs` → `checkOrigin: false`
2. Verificar que auth login sigue poniendo sameSite: lax
3. Build + deploy

## Archivos

- `astro.config.mjs` — 1 línea
- `src/pages/api/auth/login.ts` — verificar (no modificar si ya está bien)
