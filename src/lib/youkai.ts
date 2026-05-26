/**
 * src/lib/youkai.ts
 * Adapter to read telemetry from Youkai's database.
 * Supports running inside Docker (volume mount) or locally.
 */

import { Database } from "bun:sqlite";
import { existsSync } from "fs";

const CONTAINER_DB_PATH = "/app/data/youkai_db/fairy.db";
const HOST_DB_PATH = "/home/ubuntu/Desktop/los nitos hermanos/youkai/db/fairy.db";

export function getYoukaiDb(): Database | null {
  const path = existsSync(CONTAINER_DB_PATH) ? CONTAINER_DB_PATH : HOST_DB_PATH;
  if (!existsSync(path)) {
    console.warn(`Youkai database not found at: ${path}`);
    return null;
  }
  return new Database(path, { readonly: true });
}

export interface YoukaiStats {
  totalMessages: number;
  circulatingCredits: number;
  treasuryBalance: number;
  activeLoans: number;
  totalListeners: number;
  triggerLogs: number;
  trustScores: number;
  userProfiles: number;
}

export function getYoukaiStats(): YoukaiStats {
  const db = getYoukaiDb();
  if (!db) {
    return {
      totalMessages: 0,
      circulatingCredits: 0,
      treasuryBalance: 0,
      activeLoans: 0,
      totalListeners: 0,
      triggerLogs: 0,
      trustScores: 0,
      userProfiles: 0,
    };
  }

  try {
    const totalMessages = db.query("SELECT COUNT(*) as count FROM messages").get() as { count: number } | null;
    const circulating = db.query("SELECT SUM(balance) as sum FROM user_credits").get() as { sum: number } | null;
    const treasury = db.query("SELECT SUM(balance) as sum FROM guild_treasury").get() as { sum: number } | null;
    const loans = db.query("SELECT COUNT(*) as count FROM loans WHERE status = 'active'").get() as { count: number } | null;
    const listeners = db.query("SELECT COUNT(*) as count FROM guild_listeners").get() as { count: number } | null;
    const logs = db.query("SELECT COUNT(*) as count FROM listener_trigger_log").get() as { count: number } | null;
    const trust = db.query("SELECT COUNT(*) as count FROM trust_scores").get() as { count: number } | null;
    const profiles = db.query("SELECT COUNT(*) as count FROM user_profiles").get() as { count: number } | null;

    return {
      totalMessages: totalMessages?.count || 0,
      circulatingCredits: circulating?.sum || 0,
      treasuryBalance: treasury?.sum || 0,
      activeLoans: loans?.count || 0,
      totalListeners: listeners?.count || 0,
      triggerLogs: logs?.count || 0,
      trustScores: trust?.count || 0,
      userProfiles: profiles?.count || 0,
    };
  } catch (err) {
    console.error("Failed to query Youkai database stats:", err);
    return {
      totalMessages: 0,
      circulatingCredits: 0,
      treasuryBalance: 0,
      activeLoans: 0,
      totalListeners: 0,
      triggerLogs: 0,
      trustScores: 0,
      userProfiles: 0,
    };
  } finally {
    db.close();
  }
}
