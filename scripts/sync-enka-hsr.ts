/**
 * Sincroniza personajes de Honkai: Star Rail desde Enka Network.
 *   bun run scripts/sync-enka-hsr.ts
 */
import { Database } from 'bun:sqlite';

const UID  = '600180174';
const GAME = 'hsr';

const db = new Database('data/database.sqlite');

db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, game TEXT NOT NULL, name TEXT NOT NULL,
    level INTEGER DEFAULT 1, rarity INTEGER DEFAULT 4, element TEXT,
    path TEXT, constellation INTEGER DEFAULT 0, imageUrl TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

async function syncHSR() {
  console.log(`⏳ Sincronizando Honkai: Star Rail UID ${UID}...`);

  const res = await fetch(`https://enka.network/api/hsr/uid/${UID}`, {
    headers: { 'User-Agent': 'aris-sama-site/1.0 (personal portfolio)' }
  });

  if (!res.ok) throw new Error(`Enka respondió ${res.status}`);
  const data = await res.json() as any;

  const avatarList: any[] = data.detailInfo?.avatarDetailList ?? [];
  if (!avatarList.length) {
    console.warn('⚠️  No hay personajes en el showcase de HSR.');
    return;
  }

  const stmt = db.prepare(`
    INSERT INTO characters (id, game, name, level, rarity, element, path, constellation, imageUrl, synced_at)
    VALUES ($id, $game, $name, $level, $rarity, $element, $path, $constellation, $imageUrl, datetime('now'))
    ON CONFLICT(id) DO UPDATE SET
      level = excluded.level, constellation = excluded.constellation, synced_at = excluded.synced_at
  `);

  let count = 0;
  for (const av of avatarList) {
    const id = `hsr_${av.avatarId}`;
    const name: string = av.avatarName ?? `Personaje ${av.avatarId}`;
    const level: number = av.level ?? 1;
    const rarity: number = av.rarity ?? 4;
    const element: string = av.element ?? '';
    const path: string = av.baseType ?? '';
    const constellation: number = av.rank ?? 0;
    const imageUrl = `https://enka.network/ui/hsr/SpriteOutput/AvatarRoundIcon/${av.avatarId}.png`;

    stmt.run({ $id: id, $game: GAME, $name: name, $level: level, $rarity: rarity,
      $element: element, $path: path, $constellation: constellation, $imageUrl: imageUrl });
    count++;
  }

  console.log(`✅ ${count} personajes de HSR sincronizados.`);
}

syncHSR()
  .catch(e => console.error('❌', e))
  .finally(() => db.close());
