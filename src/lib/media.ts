/**
 * src/lib/media.ts
 * Procesamiento de uploads para el feed.
 * - Imagenes: convierte a WebP, resize max 1920px, thumb 400px
 * - Videos: guarda original, genera thumb con ffmpeg
 * - Documentos: guarda original
 */

import { mkdirSync, writeFileSync, unlinkSync, existsSync } from "fs";
import { join } from "path";
import { randomUUID } from "crypto";
import { execFile } from "child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const UPLOADS_DIR = join(process.cwd(), "public", "uploads", "feed");
const THUMBS_DIR = join(process.cwd(), "public", "thumbs", "feed");
const PFP_DIR = join(process.cwd(), "public", "uploads");
const PUBLIC_DIR = join(process.cwd(), "public");

const MAX_IMAGE_SIZE = 10 * 1024 * 1024;   // 10MB
const MAX_VIDEO_SIZE = 100 * 1024 * 1024;  // 100MB
const MAX_DOC_SIZE = 20 * 1024 * 1024;     // 20MB

const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/avif"];
const ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime"];
const ALLOWED_DOC_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/plain",
  "text/csv",
];

function ensureDirs() {
  mkdirSync(UPLOADS_DIR, { recursive: true });
  mkdirSync(THUMBS_DIR, { recursive: true });
  mkdirSync(PFP_DIR, { recursive: true });
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
}

export interface UploadResult {
  url: string;
  type: "image" | "video" | "document";
  thumb: string | null;
  width?: number;
  height?: number;
  alt?: string;
  name?: string;
  size?: string;
}

/**
 * Process an uploaded file for the feed.
 */
export async function processUpload(file: File): Promise<UploadResult> {
  ensureDirs();
  const mime = file.type;
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "bin";
  const uid = randomUUID();

  if (ALLOWED_IMAGE_TYPES.includes(mime)) {
    if (file.size > MAX_IMAGE_SIZE) throw new Error("Imagen muy grande (max 10MB)");
    return processImage(file, uid, ext);
  }

  if (ALLOWED_VIDEO_TYPES.includes(mime)) {
    if (file.size > MAX_VIDEO_SIZE) throw new Error("Video muy grande (max 100MB)");
    return processVideo(file, uid, ext);
  }

  if (ALLOWED_DOC_TYPES.includes(mime) || mime === "application/octet-stream") {
    if (file.size > MAX_DOC_SIZE) throw new Error("Documento muy grande (max 20MB)");
    return processDocument(file, uid, ext);
  }

  throw new Error(`Tipo no soportado: ${mime}`);
}

/**
 * Process an image: save original as WebP, generate thumbnail.
 */
async function processImage(file: File, uid: string, _ext: string): Promise<UploadResult> {
  const filename = `${uid}.webp`;
  const thumbFilename = `${uid}.webp`;
  const filepath = join(UPLOADS_DIR, filename);
  const thumbPath = join(THUMBS_DIR, thumbFilename);

  // Save original to temp
  const tempPath = join(UPLOADS_DIR, `${uid}_temp`);
  const buf = Buffer.from(await file.arrayBuffer());
  writeFileSync(tempPath, buf);

  // Convert to WebP, resize max 1920px
  try {
    await execFileAsync("ffmpeg", [
      "-i", tempPath,
      "-vf", "scale='min(1920,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease",
      "-q:v", "75",
      "-y", filepath,
    ], { timeout: 30000 });
  } catch {
    // Fallback: just copy if ffmpeg fails
    writeFileSync(filepath, buf);
  }

  // Generate thumbnail 400px
  try {
    await execFileAsync("ffmpeg", [
      "-i", filepath,
      "-vf", "scale='min(400,iw)':min'(400,ih)':force_original_aspect_ratio=decrease",
      "-q:v", "60",
      "-y", thumbPath,
    ], { timeout: 15000 });
  } catch {
    // Copy as thumb if fails
    writeFileSync(thumbPath, buf);
  }

  // Get dimensions
  let width = 1200, height = 800;
  try {
    const { stdout } = await execFileAsync("ffprobe", [
      "-v", "error", "-select_streams", "v:0",
      "-show_entries", "stream=width,height",
      "-of", "csv=s=x:p=0", filepath,
    ], { timeout: 5000 });
    const [w, h] = stdout.trim().split("x").map(Number);
    if (w && h) { width = w; height = h; }
  } catch { /* use defaults */ }

  // Cleanup temp
  try { unlinkSync(tempPath); } catch { /* ok */ }

  return {
    url: `/uploads/feed/${filename}`,
    type: "image",
    thumb: `/thumbs/feed/${thumbFilename}`,
    width,
    height,
    alt: "",
  };
}

/**
 * Process a video: save original, generate thumbnail.
 */
async function processVideo(file: File, uid: string, ext: string): Promise<UploadResult> {
  const filename = `${uid}.${ext}`;
  const thumbFilename = `${uid}.jpg`;
  const filepath = join(UPLOADS_DIR, filename);
  const thumbPath = join(THUMBS_DIR, thumbFilename);

  const buf = Buffer.from(await file.arrayBuffer());
  writeFileSync(filepath, buf);

  // Generate thumbnail from first frame
  try {
    await execFileAsync("ffmpeg", [
      "-i", filepath,
      "-vframes", "1",
      "-vf", "scale='min(800,iw)':min'(800,ih)':force_original_aspect_ratio=decrease",
      "-q:v", "60",
      "-y", thumbPath,
    ], { timeout: 15000 });
  } catch { /* no thumb */ }

  // Get dimensions
  let width = 1920, height = 1080;
  try {
    const { stdout } = await execFileAsync("ffprobe", [
      "-v", "error", "-select_streams", "v:0",
      "-show_entries", "stream=width,height",
      "-of", "csv=s=x:p=0", filepath,
    ], { timeout: 5000 });
    const [w, h] = stdout.trim().split("x").map(Number);
    if (w && h) { width = w; height = h; }
  } catch { /* use defaults */ }

  return {
    url: `/uploads/feed/${filename}`,
    type: "video",
    thumb: existsSync(thumbPath) ? `/thumbs/feed/${thumbFilename}` : null,
    width,
    height,
    alt: "",
  };
}

/**
 * Process a document: save original, no thumbnail.
 */
async function processDocument(file: File, uid: string, ext: string): Promise<UploadResult> {
  const filename = `${uid}.${ext}`;
  const filepath = join(UPLOADS_DIR, filename);

  const buf = Buffer.from(await file.arrayBuffer());
  writeFileSync(filepath, buf);

  return {
    url: `/uploads/feed/${filename}`,
    type: "document",
    thumb: null,
    name: file.name,
    size: formatSize(file.size),
    alt: file.name,
  };
}

/**
 * Process PFP upload: resize to 128x128 WebP.
 */
export async function processPfp(file: File): Promise<string> {
  ensureDirs();
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) throw new Error("PFP debe ser imagen");
  if (file.size > MAX_IMAGE_SIZE) throw new Error("Imagen muy grande (max 10MB)");

  const pfpPath = join(PFP_DIR, "pfp.webp");
  const tempPath = join(PFP_DIR, "pfp_temp");

  const buf = Buffer.from(await file.arrayBuffer());
  writeFileSync(tempPath, buf);

  try {
    await execFileAsync("ffmpeg", [
      "-i", tempPath,
      "-vf", "scale=128:128:force_original_aspect_ratio=crop",
      "-q:v", "80",
      "-y", pfpPath,
    ], { timeout: 10000 });
  } catch {
    writeFileSync(pfpPath, buf);
  }

 try { unlinkSync(tempPath); } catch { /* ok */ }

 // Regenerate favicons from the new pfp
 regenerateFavicons(pfpPath).catch(() => { /* non-critical */ });

 return "/uploads/pfp.webp";
}

/**
 * Regenerate favicon files (ico, png, svg) from the pfp image.
 */
async function regenerateFavicons(pfpPath: string): Promise<void> {
 const sizes = [16, 32, 48, 180];
 const pngPaths: string[] = [];

 for (const s of sizes) {
   const outPath = join(PUBLIC_DIR, s === 180 ? "favicon-180.png" : `favicon-${s}.png`);
   pngPaths.push(outPath);
   try {
     await execFileAsync("ffmpeg", [
       "-i", pfpPath,
       "-vf", `scale=${s}:${s}`,
       "-y", outPath,
     ], { timeout: 10000 });
   } catch { /* skip if fails */ }
 }

 // Generate ICO from 16+32+48 PNGs using Python/Pillow
 try {
   const pyScript = `
from PIL import Image
sizes = []
for s in [16, 32, 48]:
   img = Image.open("${join(PUBLIC_DIR, `favicon-${s}.png`)}")
   sizes.append(img)
sizes[0].save("${join(PUBLIC_DIR, "favicon.ico")}", format="ICO", sizes=[(s.width, s.height) for s in sizes], append_images=sizes[1:])
`;
   await execFileAsync("python3", ["-c", pyScript], { timeout: 10000 });
 } catch { /* skip if fails */ }

 // Generate SVG favicon with embedded PNG (base64)
 try {
   const b64 = readFileSync(join(PUBLIC_DIR, "favicon-180.png")).toString("base64");
   const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180"><image href="data:image/png;base64,${b64}" width="180" height="180"/></svg>`;
   writeFileSync(join(PUBLIC_DIR, "favicon.svg"), svg);
 } catch { /* skip if fails */ }
}

/**
 * Delete media files from filesystem.
 */
export function deleteMediaFiles(media: { url: string; thumb?: string | null }[]): void {
  for (const m of media) {
    const basePath = join(process.cwd(), "public");
    try {
      const fullPath = join(basePath, m.url);
      if (existsSync(fullPath)) unlinkSync(fullPath);
    } catch { /* ok */ }
    if (m.thumb) {
      try {
        const thumbPath = join(basePath, m.thumb);
        if (existsSync(thumbPath)) unlinkSync(thumbPath);
      } catch { /* ok */ }
    }
  }
}
