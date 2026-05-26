/**
 * src/lib/now.ts
 * CRUD for now_items — dynamic "what I'm doing now" entries.
 */
import { getDb, getReadDb } from "./db";
import { readFileSync, existsSync } from "fs";
import { join } from "path";

export interface NowItem {
  id: number;
  icon: string;
  category: string;
  text: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export function getNowItems(): NowItem[] {
  try {
    const db = getReadDb();
    const rows = db.query("SELECT * FROM now_items ORDER BY sort_order ASC, created_at DESC").all() as NowItem[];
    db.close();
    return rows;
  } catch {
    return [];
  }
}

export function createNowItem(data: { icon?: string; category: string; text: string; sort_order?: number }): NowItem {
  const db = getDb();
  const icon = data.icon ?? "💭";
  const sort = data.sort_order ?? 0;
  const result = db.run(
    "INSERT INTO now_items (icon, category, text, sort_order) VALUES (?, ?, ?, ?)",
    icon, data.category, data.text, sort
  );
  const id = Number(result.lastInsertRowid);
  const row = db.query("SELECT * FROM now_items WHERE id = ?").get(id) as NowItem;
  db.close();
  return row;
}

export function updateNowItem(id: number, data: Partial<{ icon: string; category: string; text: string; sort_order: number }>): void {
  const db = getDb();
  const sets: string[] = [];
  const vals: any[] = [];
  if (data.icon !== undefined) { sets.push("icon = ?"); vals.push(data.icon); }
  if (data.category !== undefined) { sets.push("category = ?"); vals.push(data.category); }
  if (data.text !== undefined) { sets.push("text = ?"); vals.push(data.text); }
  if (data.sort_order !== undefined) { sets.push("sort_order = ?"); vals.push(data.sort_order); }
  if (sets.length > 0) {
    sets.push("updated_at = CURRENT_TIMESTAMP");
    db.run(`UPDATE now_items SET ${sets.join(", ")} WHERE id = ?`, ...vals, id);
  }
  db.close();
}

export function deleteNowItem(id: number): void {
  const db = getDb();
  db.run("DELETE FROM now_items WHERE id = ?", id);
  db.close();
}

/**
 * Seed now_items from data/now.json if table is empty.
 */
export function seedNowFromJson(): void {
  try {
    const db = getReadDb();
    const count = (db.query("SELECT COUNT(*) as n FROM now_items").get() as any)?.n ?? 0;
    db.close();
    if (count > 0) return; // already seeded

    const jsonPath = join(process.cwd(), "data", "now.json");
    if (!existsSync(jsonPath)) return;

    const raw = JSON.parse(readFileSync(jsonPath, "utf-8"));
    const items = raw.items ?? [];
    items.forEach((item: any, i: number) => {
      createNowItem({
        icon: item.icon ?? "💭",
        category: item.category ?? "",
        text: item.text ?? "",
        sort_order: i,
      });
    });
  } catch { /* ok */ }
}

// Seed on module load
seedNowFromJson();
