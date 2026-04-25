/**
 * Zenless Zone Zero — Enka aún no expone endpoint público estable para ZZZ.
 * Este script inserta personajes manualmente como placeholder.
 * Cuando Enka lo soporte, actualizar a fetch como GI/HSR.
 *
 *   bun run scripts/sync-enka-zzz.ts
 */
import { Database } from 'bun:sqlite';

const GAME = 'zzz';

const db = new Database('data/database.sqlite');
db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, game TEXT NOT NULL, name TEXT NOT NULL,
    level INTEGER DEFAULT 1, rarity INTEGER DEFAULT 4, element TEXT,
    path TEXT, constellation INTEGER DEFAULT 0, imageUrl TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Agrega aquí tus personajes de ZZZ manualmente por ahora
const ZZZ_MANUAL = [
  // { id: 'zzz_belle', name: 'Belle', level: 60, rarity: 5, element: 'Electric', imageUrl: '' },
];

if (!ZZZ_MANUAL.length) {
  console.log('ℹ️  No hay personajes ZZZ definidos. Agrega tus personajes en el array ZZZ_MANUAL de este script.');
  db.close();
  process.exit(0);
}

const stmt = db.prepare(`
  INSERT INTO characters (id, game, name, level, rarity, element, constellation, imageUrl, synced_at)
  VALUES ($id, $game, $name, $level, $rarity, $element, $constellation, $imageUrl, datetime('now'))
  ON CONFLICT(id) DO UPDATE SET level = excluded.level, synced_at = excluded.synced_at
`);

for (const c of ZZZ_MANUAL) {
  stmt.run({ $id: c.id, $game: GAME, $name: c.name, $level: c.level,
    $rarity: c.rarity, $element: c.element, $constellation: 0, $imageUrl: c.imageUrl ?? '' });
}

console.log(`✅ ${ZZZ_MANUAL.length} personajes ZZZ guardados.`);
db.close();
