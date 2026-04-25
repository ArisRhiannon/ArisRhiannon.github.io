/**
 * Sincroniza personajes de Genshin Impact desde Enka Network.
 * Ejecutar después de actualizar tu showcase:
 *   bun run scripts/sync-enka-gi.ts
 */
import { Database } from 'bun:sqlite';

const UID  = '603731692';
const GAME = 'gi';

const db = new Database('data/database.sqlite');

// Asegurar tabla existe
db.run(`
  CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, game TEXT NOT NULL, name TEXT NOT NULL,
    level INTEGER DEFAULT 1, rarity INTEGER DEFAULT 4, element TEXT,
    path TEXT, constellation INTEGER DEFAULT 0, imageUrl TEXT,
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

async function syncGenshin() {
  console.log(`⏳ Sincronizando Genshin Impact UID ${UID}...`);

  const res = await fetch(`https://enka.network/api/uid/${UID}`, {
    headers: { 'User-Agent': 'aris-sama-site/1.0 (personal portfolio)' }
  });

  if (!res.ok) throw new Error(`Enka respondió ${res.status}`);
  const data = await res.json() as any;

  const avatarList: any[] = data.avatarInfoList ?? [];
  if (!avatarList.length) {
    console.warn('⚠️  No hay personajes en el showcase (máximo 8-9). Agrega personajes en el juego.');
    return;
  }

  const stmt = db.prepare(`
    INSERT INTO characters (id, game, name, level, rarity, element, constellation, imageUrl, synced_at)
    VALUES ($id, $game, $name, $level, $rarity, $element, $constellation, $imageUrl, datetime('now'))
    ON CONFLICT(id) DO UPDATE SET
      level = excluded.level, constellation = excluded.constellation, synced_at = excluded.synced_at
  `);

  // Mapa de elementos de GI
  const ELEMENTS: Record<number, string> = {
    1: 'Pyro', 2: 'Hydro', 3: 'Dendro', 4: 'Electro', 5: 'Anemo', 6: 'Cryo', 7: 'Geo'
  };

  let count = 0;
  for (const av of avatarList) {
    const id = `gi_${av.avatarId}`;
    const name: string = data.playerInfo?.showAvatarInfoList?.find((a: any) => a.avatarId === av.avatarId)?.name
      ?? `Personaje ${av.avatarId}`;
    const level = av.propMap?.[4001]?.val ? parseInt(av.propMap[4001].val) : 1;
    const element = ELEMENTS[av.skillDepotId >> 9 & 0xF] ?? '';
    const constellation = (av.talentIdList ?? []).length;
    const rarity = av.rarity ?? 4;
    const imageUrl = `https://enka.network/ui/UI_AvatarIcon_${av.avatarId}.png`;

    stmt.run({ $id: id, $game: GAME, $name: name, $level: level, $rarity: rarity,
      $element: element, $constellation: constellation, $imageUrl: imageUrl });
    count++;
  }

  console.log(`✅ ${count} personajes de Genshin sincronizados.`);
}

syncGenshin()
  .catch(e => console.error('❌', e))
  .finally(() => db.close());
