/**
 * scripts/init-feed-tables.ts
 * Crea las tables de posts y profile si no existen.
 * Uso: bun run scripts/init-feed-tables.ts
 */
import { Database } from "bun:sqlite";
import { join } from "path";

const dbPath = join(process.cwd(), "data", "database.sqlite");
const db = new Database(dbPath);

db.run(`
  CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    display_name TEXT NOT NULL DEFAULT 'Aris',
    subtitle TEXT NOT NULL DEFAULT 'colecciono nitos',
    pfp_url TEXT NOT NULL DEFAULT '/uploads/pfp.webp',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

db.run(`
  CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body TEXT NOT NULL,
    media_json TEXT DEFAULT '[]',
    mood TEXT DEFAULT NULL,
    pinned INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

db.run(`
  CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
`);

db.run(`
  CREATE INDEX IF NOT EXISTS idx_posts_pinned ON posts(pinned DESC, created_at DESC);
`);

// Insert default profile row if empty
const existing = db.query("SELECT id FROM profile WHERE id = 1").get();
if (!existing) {
  db.run(`INSERT INTO profile (id, display_name, subtitle, pfp_url) VALUES (1, 'Aris', 'colecciono nitos', '/uploads/pfp.webp')`);
  console.log("Created default profile row");
}

db.close();
console.log("Feed tables ready ✓");
