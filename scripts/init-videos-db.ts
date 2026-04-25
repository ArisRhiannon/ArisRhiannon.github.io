import { Database } from "bun:sqlite";
const db = new Database("data/database.sqlite");
db.run(`
  CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    title TEXT,
    url TEXT,
    thumbnail TEXT,
    category TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);
console.log("✅ Tabla de videos inicializada correctamente.");
db.close();
