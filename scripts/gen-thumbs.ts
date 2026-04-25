#!/usr/bin/env bun
// scripts/gen-thumbs.ts — genera thumbnails para videos ya subidos sin thumb
import { Database } from 'bun:sqlite';
import { join } from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { existsSync, mkdirSync } from 'fs';

const execFileAsync = promisify(execFile);
const BASE     = process.cwd();
const UPLOADS  = join(BASE, 'public', 'uploads');
const THUMBS   = join(BASE, 'public', 'thumbs');
mkdirSync(THUMBS, { recursive: true });

const db = new Database(join(BASE, 'data', 'database.sqlite'));
const videos = db.query("SELECT id, filename, url FROM videos WHERE thumbnail IS NULL OR thumbnail = ''").all() as any[];

console.log(`Procesando ${videos.length} videos sin thumbnail...`);

for (const v of videos) {
  const filename = v.filename ?? v.url?.split('/').pop();
  if (!filename) { console.log(`  skip ${v.id} (sin filename)`); continue; }

  const videoPath = join(UPLOADS, filename);
  const thumbFile = `${v.id}.jpg`;
  const thumbPath = join(THUMBS, thumbFile);

  if (!existsSync(videoPath)) { console.log(`  skip ${filename} (no existe en disco)`); continue; }
  if (existsSync(thumbPath))  { console.log(`  skip ${v.id} (thumb ya existe)`); continue; }

  try {
    await execFileAsync('ffmpeg', [
      '-y', '-i', videoPath,
      '-ss', '00:00:01', '-vframes', '1',
      '-vf', 'scale=640:-1', '-q:v', '3',
      thumbPath
    ]);

    // Obtener dimensiones
    let width = 1920, height = 1080;
    try {
      const probe = await execFileAsync('ffprobe', [
        '-v', 'quiet', '-print_format', 'json', '-show_streams', videoPath
      ]);
      const info = JSON.parse(probe.stdout);
      const vs = info.streams?.find((s: any) => s.codec_type === 'video');
      if (vs) { width = vs.width; height = vs.height; }
    } catch {}

    db.run("UPDATE videos SET thumbnail = ?, width = ?, height = ? WHERE id = ?",
      [`/thumbs/${thumbFile}`, width, height, v.id]);
    console.log(`  ✅ ${filename} → /thumbs/${thumbFile}`);
  } catch (e) {
    console.log(`  ❌ ${filename}: ${e}`);
  }
}

db.close();
console.log('\nListo.');
