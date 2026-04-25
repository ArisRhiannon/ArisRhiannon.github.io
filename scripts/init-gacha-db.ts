/**
 * Inicializa la base de datos SQLite con todas las tablas necesarias.
 * Ejecutar UNA vez antes del primer sync:
 *   bun run scripts/init-gacha-db.ts
 */
import { Database } from 'bun:sqlite';

const db = new Database('data/database.sqlite');

db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id          TEXT PRIMARY KEY,
    game        TEXT NOT NULL,
    name        TEXT NOT NULL,
    level       INTEGER DEFAULT 1,
    rarity      INTEGER DEFAULT 4,
    element     TEXT,
    path        TEXT,
    constellation INTEGER DEFAULT 0,
    imageUrl    TEXT,
    synced_at   DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

db.run(`
  CREATE TABLE IF NOT EXISTS videos (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    url         TEXT NOT NULL,
    thumbnail   TEXT,
    category    TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

console.log('✅ Tablas characters y videos listas en data/database.sqlite');
db.close();
