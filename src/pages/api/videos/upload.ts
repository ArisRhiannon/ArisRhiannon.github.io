import type { APIRoute } from "astro";
import { isAdmin } from "../../../lib/auth";
import { ADMIN_JWT_SECRET } from "../../../lib/env";
import { getDb } from "../../../lib/db";
import { jsonResponse, errorResponse } from "../../../lib/response";
import { mkdirSync, writeFileSync } from "fs";
import { join } from "path";
import { randomUUID } from "crypto";
import { execFile } from "child_process";
import { promisify } from "util";

const execFileAsync = promisify(execFile);
const UPLOADS_DIR = join(process.cwd(), "public", "uploads");
const THUMBS_DIR = join(process.cwd(), "public", "thumbs");

export const POST: APIRoute = async ({ request }) => {
  if (!(await isAdmin(request, ADMIN_JWT_SECRET())))
    return new Response("unauthorized", { status: 401 });

  try {
    mkdirSync(UPLOADS_DIR, { recursive: true });
    mkdirSync(THUMBS_DIR, { recursive: true });

    const form = await request.formData();
    const file = form.get("video") as File | null;
    const title = (form.get("title") as string) ?? "Sin título";
    const category = (form.get("category") as string) ?? "general";
    const descriptors = (form.get("descriptors") as string) ?? "{}";

    if (!file || file.size === 0) {
      return errorResponse("No se recibió archivo", 400);
    }
    if (file.size > 500 * 1024 * 1024) {
      return errorResponse("Archivo demasiado grande (máx 500MB)", 413);
    }

    const ext = file.name.split(".").pop()?.toLowerCase() ?? "mp4";
    const id = randomUUID();
    const filename = `${id}.${ext}`;
    const filePath = join(UPLOADS_DIR, filename);

    const buffer = await file.arrayBuffer();
    writeFileSync(filePath, Buffer.from(buffer));

    // Generate thumbnail with ffmpeg
    let thumbnailUrl: string | null = null;
    let width = 1920,
      height = 1080;
    const thumbFile = `${id}.jpg`;
    const thumbPath = join(THUMBS_DIR, thumbFile);
    try {
      await execFileAsync("ffmpeg", [
        "-y",
        "-i",
        filePath,
        "-ss",
        "00:00:01",
        "-vframes",
        "1",
        "-vf",
        "scale=640:-1",
        "-q:v",
        "3",
        thumbPath,
      ]);
      thumbnailUrl = `/thumbs/${thumbFile}`;

      const probe = await execFileAsync("ffprobe", [
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        filePath,
      ]);
      const info = JSON.parse(probe.stdout);
      const vs = info.streams?.find((s: any) => s.codec_type === "video");
      if (vs) {
        width = vs.width ?? 1920;
        height = vs.height ?? 1080;
      }
    } catch {
      // ffmpeg not available or failed — thumbnail stays null
    }

    const db = getDb();
    db.run(
      `INSERT INTO videos (id, title, filename, url, thumbnail, category, descriptors, width, height)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        title,
        filename,
        `/uploads/${filename}`,
        thumbnailUrl,
        category,
        descriptors,
        width,
        height,
      ]
    );
    db.close();

    return jsonResponse({
      ok: true,
      id,
      url: `/uploads/${filename}`,
      thumbnail: thumbnailUrl,
    });
  } catch (e) {
    return errorResponse(String(e), 500);
  }
};
