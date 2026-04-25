import type { APIRoute } from 'astro';

const ANILIST_USERNAME = 'GoddamnBernkastel';
const CACHE_TTL = 60 * 60 * 1000;

let cache: { data: any[]; ts: number } | null = null;

const QUERY = `
query ($username: String) {
  MediaListCollection(userName: $username, type: ANIME) {
    lists {
      status
      entries {
        media {
          id
          title { romaji english }
          coverImage { large }
          season seasonYear format episodes
          genres siteUrl
        }
        status
        score(format: POINT_10)
        progress
        startedAt { year month day }
        completedAt { year month day }
      }
    }
  }
}`;

function formatDate(d: any): string | null {
  if (!d?.year) return null;
  const m = d.month ? String(d.month).padStart(2,'0') : '??';
  const dd = d.day ? String(d.day).padStart(2,'0') : '??';
  return `${d.year}-${m}-${dd}`;
}

async function fetchAniList(): Promise<any[]> {
  const res = await fetch('https://graphql.anilist.co', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ query: QUERY, variables: { username: ANILIST_USERNAME } }),
  });
  if (!res.ok) throw new Error(`AniList error: ${res.status}`);
  const json = await res.json();
  const lists = json?.data?.MediaListCollection?.lists ?? [];
  const entries: any[] = [];
  for (const list of lists) {
    for (const e of list.entries) {
      entries.push({
        id: e.media.id,
        title: e.media.title.romaji,
        coverImage: e.media.coverImage.large,
        status: e.status,
        score: e.score,
        progress: e.progress,
        episodes: e.media.episodes,
        seasonYear: e.media.seasonYear,
        format: e.media.format,
        genres: (e.media.genres ?? []).slice(0, 3),
        startedAt: formatDate(e.startedAt),
        completedAt: formatDate(e.completedAt),
        siteUrl: e.media.siteUrl,
      });
    }
  }
  return entries;
}

export const GET: APIRoute = async () => {
  try {
    const now = Date.now();
    if (cache && now - cache.ts < CACHE_TTL) {
      return new Response(JSON.stringify({ entries: cache.data, cached: true }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }
    const data = await fetchAniList();
    cache = { data, ts: now };
    return new Response(JSON.stringify({ entries: data, cached: false }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }
};
