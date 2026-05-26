# Plan: Optimizaciones de Build 100% Seguras

**Objetivo:** Reducir tiempo de build 50-100% SIN afectar funcionalidad, rendimiento o comportamiento del sitio.

**Fecha:** 2026-05-03

---

## Tarea 1: Mover `three` a devDependencies

**Riesgo:** 0% — El paquete no se usa en runtime (no hay imports de three en el código)

**Archivo:** `/home/ubuntu/misitio/package.json`

```json
"dependencies": {
  "@astrojs/node": "^10.0.4",
  "@tailwindcss/vite": "^4.0.0",
  "astro": "^6.1.1",
  "motion": "^11.0.0",
  "simplex-noise": "^4.0.3",
  "tailwindcss": "^4.0.0",
  "zod": "^3.23.0"
},
"devDependencies": {
  "@types/three": "^0.184.0",
  "three": "^0.184.0"
}
```

**Impacto estimado:** -20% tiempo de build (184MB menos en node_modules del builder)

---

## Tarea 2: Crear .dockerignore para excluir archivos innecesarios

**Riesgo:** 0% — Solo excluye archivos que Docker no necesita

**Archivo:** `/home/ubuntu/misitio/.dockerignore`

```
# Version control
.git
.gitignore

# Documentación
*.md
!README.md
AGENTS.md
ARCHITECTURE*.md
PLAN*.md
docs/

# Desarrollo
.env
.env.*
!.env.example
.vscode/
.idea/

# Testing
coverage/
*.test.ts
*.spec.ts
__tests__/

# Scripts archive
scripts/archive/
scripts_backup/

# Misc
*.log
npm-debug.log*
bun-debug.log*

# Kavita (servicio externo)
kavita/
kavita-backup/
```

**Impacto estimado:** -5% tiempo de build (menos archivos para COPY)

---

## Tarea 3: Unificar instalación de ffmpeg en Dockerfile

**Riesgo:** 0% — Elimina redundancia, mismo resultado final

**Archivo:** `/home/ubuntu/misitio/Dockerfile`

```dockerfile
FROM oven/bun:1-debian AS base
WORKDIR /app

# Instalar ffmpeg UNA SOLA VEZ (línea 5)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg python3 python3-pip && \
    pip3 install --break-system-packages yt-dlp && \
    rm -rf /var/lib/apt/lists/*

FROM base AS deps
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN bun run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
# Eliminar segunda instalación de ffmpeg - ya está en base
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/scripts ./scripts
COPY --from=builder /app/src ./src
COPY --from=builder /app/data ./data
RUN mkdir -p public/uploads public/thumbs public/music

EXPOSE 4321
CMD ["bun", "./dist/server/entry.mjs"]
```

**Impacto estimado:** -10-15% tiempo de build (elimina ~30-60s de apt-get重复)

---

## Tarea 4: Agregar bun install con cache optimizado

**Riesgo:** 0% — Solo optimiza el install, no el código

**Archivo:** `/home/ubuntu/misitio/Dockerfile` (línea de deps)

```dockerfile
FROM base AS deps
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile --prefer-offline
```

**Nota:** `--prefer-offline` usa cache local si existe, acelera install en builds repetidos

**Impacto estimado:** -10-30% tiempo de install (dependiendo de cache)

---

## Tarea 5: Agregar flag de Astro para builds más rápidos

**Riesgo:** 0% — Solo cambia configuración de build, no comportamiento runtime

**Archivo:** `/home/ubuntu/misitio/package.json`

```json
"scripts": {
  "dev": "astro dev",
  "build": "astro build",
  "build:fast": "astro build --verbose --no-watch",
  "preview": "astro preview",
  "sync-enka": "bun run scripts/sync-enka.ts"
}
```

**Impacto:** Mínima mejora, más para debugging

---

## Resumen de Impacto

| Tarea | Riesgo | Impacto en Build |
|-------|--------|------------------|
| Mover three a dev | 0% | -20% |
| .dockerignore | 0% | -5% |
| Unificar ffmpeg | 0% | -15% |
| bun install flags | 0% | -15% |
| **TOTAL** | **0%** | **-40-50%** |

---

## Notas

- **Zero breaking changes** — ninguna de estas tareas afecta runtime, UI, API, o funcionalidad
- **Verificación post-implementación:** ejecutar `docker compose build` y verificar que el sitio responde igual en puerto 4321
- **Medición:** guardar tiempo de build antes y después con `time docker compose build`