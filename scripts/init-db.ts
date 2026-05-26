/**
 * scripts/init-db.ts
 * Unified database initialization — creates ALL tables.
 * Run once before first sync: bun run scripts/init-db.ts
 */
import { Database } from "bun:sqlite";
import { join } from "path";

const db = new Database(join(process.cwd(), "data", "database.sqlite"));

// Characters table (gacha showcase)
db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    game TEXT NOT NULL,
    name TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    rarity INTEGER DEFAULT 4,
    element TEXT,
    path TEXT,
    constellation INTEGER DEFAULT 0,
    imageUrl TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Videos table (upload gallery)
db.run(`
  CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    filename TEXT,
    url TEXT NOT NULL,
    thumbnail TEXT,
    category TEXT,
    descriptors TEXT DEFAULT '{}',
    width INTEGER DEFAULT 1920,
    height INTEGER DEFAULT 1080,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Comments table (video comments)
db.run(`
  CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Idempotent column additions for existing databases missing new columns
const videoCols = [
  { name: "filename", sql: "ALTER TABLE videos ADD COLUMN filename TEXT" },
  { name: "descriptors", sql: "ALTER TABLE videos ADD COLUMN descriptors TEXT DEFAULT '{}'" },
  { name: "width", sql: "ALTER TABLE videos ADD COLUMN width INTEGER DEFAULT 1920" },
  { name: "height", sql: "ALTER TABLE videos ADD COLUMN height INTEGER DEFAULT 1080" },
];
for (const col of videoCols) {
  try { db.run(col.sql); } catch { /* column already exists */ }
}

console.log("✅ All tables initialized: characters, videos, comments");
db.close();
