FROM oven/bun:1-debian AS base
WORKDIR /app

# Instalar ffmpeg para thumbnails automáticos de video
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg python3 python3-pip && pip3 install --break-system-packages yt-dlp && rm -rf /var/lib/apt/lists/*

FROM base AS deps
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile --prefer-offline

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN bun run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
# ffmpeg ya está instalado en stage base
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/scripts ./scripts
COPY --from=builder /app/src ./src
COPY --from=builder /app/data ./data
RUN mkdir -p public/uploads public/thumbs public/music

EXPOSE 4321
CMD ["bun", "./dist/server/entry.mjs"]
