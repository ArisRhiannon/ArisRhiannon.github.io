/**
 * src/lib/db.ts
 * Unified SQLite database connection factory.
 *
 * Always connects to data/database.sqlite from process.cwd().
 * Use readonly=true for read operations (avoids write locks).
 *
 * BUG WORKAROUND: bun:sqlite v1.3.x crashes with "bad parameter or other API misuse"
 * when { readonly: false } is passed explicitly. Only pass options when readonly=true.
 */

import { Database } from "bun:sqlite";
import { join } from "path";

const DB_FILENAME = "database.sqlite";

function dbPath(): string {
 return join(process.cwd(), "data", DB_FILENAME);
}

export function getDb(options?: { readonly?: boolean }): Database {
 if (options?.readonly) {
 return new Database(dbPath(), { readonly: true });
 }
 // Don't pass { readonly: false } — bun:sqlite bug causes "bad parameter or other API misuse"
 return new Database(dbPath());
}

/**
 * Shorthand for read-only DB connections.
 */
export function getReadDb(): Database {
  return getDb({ readonly: true });
}

/**
 * Create tables if they don't exist.
 * Called at module load time to ensure schema is ready.
 */
export function ensureSchema(): void {
  const db = getDb();
  db.run(`
    CREATE TABLE IF NOT EXISTS guestbook (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL DEFAULT 'anon',
      message TEXT NOT NULL,
      emoji TEXT DEFAULT '✨',
      ip TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS reactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      post_id INTEGER NOT NULL,
      emoji TEXT NOT NULL,
      ip TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(post_id, ip)
    )
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS now_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      icon TEXT DEFAULT '💭',
      category TEXT NOT NULL,
      text TEXT NOT NULL,
      sort_order INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
  db.close();
}

// Ensure schema on module load
ensureSchema();
