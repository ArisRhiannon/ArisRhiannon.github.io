/**
 * src/lib/feed.ts
 * Queries para el feed — posts + profile.
 */

import { getDb, getReadDb } from "./db";

export interface MediaObj {
  url: string;
  type: "image" | "video" | "document";
  thumb?: string | null;
  width?: number;
  height?: number;
  alt?: string;
  name?: string;   // for documents
  size?: string;   // for documents
}

export interface Post {
  id: number;
  body: string;
  media_json: string;
  mood: string | null;
  pinned: number;
  created_at: string;
  updated_at: string;
}

export interface PostWithMedia extends Post {
  media: MediaObj[];
}

export interface Profile {
  display_name: string;
  subtitle: string;
  pfp_url: string;
}

// ── Profile ──────────────────────────────────────────────

export function getProfile(): Profile {
  const db = getReadDb();
  const row = db.query("SELECT display_name, subtitle, pfp_url FROM profile WHERE id = 1").get() as any;
  db.close();
  if (!row) return { display_name: "Aris", subtitle: "colecciono nitos", pfp_url: "/uploads/pfp.webp" };
  return { display_name: row.display_name, subtitle: row.subtitle, pfp_url: row.pfp_url };
}

export function updateProfile(data: Partial<Profile>): Profile {
  const db = getDb();
  const sets: string[] = [];
  const vals: any[] = [];
  if (data.display_name !== undefined) { sets.push("display_name = ?"); vals.push(data.display_name); }
  if (data.subtitle !== undefined) { sets.push("subtitle = ?"); vals.push(data.subtitle); }
  if (data.pfp_url !== undefined) { sets.push("pfp_url = ?"); vals.push(data.pfp_url); }
  if (sets.length > 0) {
    sets.push("updated_at = CURRENT_TIMESTAMP");
    db.run(`UPDATE profile SET ${sets.join(", ")} WHERE id = 1`, ...vals);
  }
  db.close();
  return getProfile();
}

// ── Posts ────────────────────────────────────────────────

export function getPosts(cursor?: number, limit = 20): { posts: PostWithMedia[]; next_cursor: number | null } {
 const db = getReadDb();
 let rows: Post[];
 if (cursor) {
 rows = db.query(
 "SELECT * FROM posts WHERE id < ? ORDER BY pinned DESC, created_at DESC LIMIT ?"
 ).all(cursor, limit) as Post[];
 } else {
 rows = db.query(
 "SELECT * FROM posts ORDER BY pinned DESC, created_at DESC LIMIT ?"
 ).all(limit) as Post[];
 }
 db.close();

  const posts = rows.map(parsePost);
  const next_cursor = posts.length === limit ? (posts[posts.length - 1]?.id ?? null) : null;
  return { posts, next_cursor };
}

export function getPostById(id: number): PostWithMedia | null {
  const db = getReadDb();
  const row = db.query("SELECT * FROM posts WHERE id = ?").get(id) as Post | null;
  db.close();
  return row ? parsePost(row) : null;
}

export function createPost(data: { body: string; media?: MediaObj[]; mood?: string | null; pinned?: boolean }): PostWithMedia {
  const db = getDb();
  const mediaJson = JSON.stringify(data.media ?? []);
  const mood = data.mood ?? null;
  const pinned = data.pinned ? 1 : 0;
  const result = db.run(
    "INSERT INTO posts (body, media_json, mood, pinned) VALUES (?, ?, ?, ?)",
    data.body, mediaJson, mood, pinned
  );
  const id = Number(result.lastInsertRowid);
  const row = db.query("SELECT * FROM posts WHERE id = ?").get(id) as Post;
  db.close();
  return parsePost(row);
}

export function deletePost(id: number): MediaObj[] {
  const db = getDb();
  const row = db.query("SELECT media_json FROM posts WHERE id = ?").get(id) as any;
  const media: MediaObj[] = row ? JSON.parse(row.media_json ?? "[]") : [];
  db.run("DELETE FROM posts WHERE id = ?", id);
  db.close();
  return media;
}

export function togglePin(id: number, pinned: boolean): void {
  const db = getDb();
  db.run("UPDATE posts SET pinned = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", pinned ? 1 : 0, id);
  db.close();
}

// ── Helpers ──────────────────────────────────────────────

function parsePost(row: Post): PostWithMedia {
  let media: MediaObj[] = [];
  try { media = JSON.parse(row.media_json ?? "[]"); } catch { media = []; }
  return { ...row, media };
}
