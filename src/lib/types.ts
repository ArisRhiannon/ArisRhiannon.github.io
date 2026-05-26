/**
 * src/lib/types.ts
 * TypeScript interfaces for database rows.
 */

export interface VideoRow {
  id: string;
  title: string;
  filename: string | null;
  url: string;
  thumbnail: string | null;
  category: string | null;
  descriptors: string;
  width: number;
  height: number;
  created_at: string;
}

export interface CharacterRow {
  id: string;
  game: string;
  name: string;
  level: number;
  rarity: number;
  element: string | null;
  path: string | null;
  constellation: number;
  imageUrl: string | null;
  synced_at: string;
}

export interface CommentRow {
  id: number;
  video_id: string;
  alias: string;
  body: string;
  created_at: string;
}