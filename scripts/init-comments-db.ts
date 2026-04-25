import { Database } from 'bun:sqlite';
import { join } from 'path';
const db = new Database(join(process.cwd(), 'data', 'database.sqlite'));
db.run(`CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL,
  alias TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)`);
db.close();
console.log('✅ tabla comments lista');
