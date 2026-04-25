import os, subprocess, textwrap

BASE = os.path.expanduser("~/misitio")

uploads_dir = os.path.join(BASE, "public", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
subprocess.run(["chmod", "777", uploads_dir], check=True)
print(f"✅  {uploads_dir} creado con chmod 777")

dockerfile = textwrap.dedent("""\
    FROM oven/bun:1-debian AS base
    WORKDIR /app

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
    COPY --from=builder /app/dist ./dist
    COPY --from=builder /app/node_modules ./node_modules
    COPY --from=builder /app/package.json ./package.json
    COPY --from=builder /app/scripts ./scripts
    COPY --from=builder /app/src ./src
    COPY --from=builder /app/data ./data
    RUN mkdir -p public/uploads

    EXPOSE 4321
    CMD ["bun", "./dist/server/entry.mjs"]
""")

with open(os.path.join(BASE, "Dockerfile"), "w") as f:
    f.write(dockerfile)
print("✅  Dockerfile actualizado")

result = subprocess.run(
    ["docker", "compose", "up", "-d", "--build"],
    cwd=BASE, capture_output=True, text=True
)
print(result.stdout[-2000:] if result.stdout else "")
if result.returncode != 0:
    print("❌ Error:", result.stderr[-2000:])
else:
    print("✅  Listo. Prueba subir un video desde /admin")
