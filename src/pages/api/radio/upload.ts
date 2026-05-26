/**
 * POST /api/radio/upload
 * Upload audio files for the radio player. Auth required.
 * Saves to public/music/ and returns the URL.
 */
import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { mkdirSync, existsSync } from "fs";
import { join } from "path";

const VALID_EXTENSIONS = ['.mp3', '.ogg', '.opus', '.flac', '.wav', '.aac', '.m4a', '.webm'];
const MAX_SIZE = 100 * 1024 * 1024; // 100MB

export const POST: APIRoute = async ({ request, cookies }) => {
  const token = cookies.get("aris_admin")?.value;
  if (!token || !(await isAdmin(request, ADMIN_JWT_SECRET()))) {
    return new Response("unauthorized", { status: 401 });
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  const file = form.get("file") as File | null;
  if (!file || file.size === 0) {
    return new Response(JSON.stringify({ ok: false, error: "file required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (file.size > MAX_SIZE) {
    return new Response(JSON.stringify({ ok: false, error: "file too large (max 100MB)" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Validate extension
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!VALID_EXTENSIONS.includes(ext)) {
    return new Response(JSON.stringify({ ok: false, error: `invalid format: ${ext}` }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Save to public/music/
  const musicDir = join(process.cwd(), "public", "music");
  if (!existsSync(musicDir)) mkdirSync(musicDir, { recursive: true });

  // Sanitize filename
  const safeName = file.name
    .replace(/[^a-zA-Z0-9._-]/g, '_')
    .replace(/_{2,}/g, '_')
    .toLowerCase();

  const filePath = join(musicDir, safeName);

  try {
    const buffer = Buffer.from(await file.arrayBuffer());
    const { writeFileSync } = await import("fs");
    writeFileSync(filePath, buffer);

    const url = `/music/${safeName}`;
    return new Response(JSON.stringify({ ok: true, url, name: safeName }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (e: any) {
    return new Response(JSON.stringify({ ok: false, error: e.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};
