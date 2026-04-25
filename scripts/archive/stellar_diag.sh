#!/bin/bash
echo "--- 🛰️ REPORTE DE DIAGNÓSTICO: STELLAR TERMINAL ---"
echo "Fecha: $(date)"

echo -e "\n1. 🐳 Estado de los Contenedores:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n2. 📄 Últimos errores del servidor (Web):"
sudo docker compose logs --tail=20 web

echo -e "\n3. 📂 Verificación de Carpetas Críticas (Container):"
sudo docker exec misitio-web-1 ls -ld /app/data /app/public/uploads 2>&1

echo -e "\n4. 🗄️ Verificación de Base de Datos (SQLite):"
sudo docker exec misitio-web-1 bun -e "
  import { Database } from 'bun:sqlite';
  try {
    const db = new Database('data/database.sqlite');
    const table = db.query(\"SELECT name FROM sqlite_master WHERE type='table' AND name='videos'\").get();
    console.log(table ? '✅ Tabla videos: EXISTE' : '❌ Tabla videos: NO EXISTE');
    db.close();
  } catch (e) { console.log('❌ Error DB: ' + e.message); }
"

echo -e "\n5. 🔑 Verificación de Secretos (.env):"
if [ -f ~/misitio/.env ]; then
    grep -E "ADMIN_JWT_SECRET|ADMIN_HASH" ~/misitio/.env | sed 's/=.*/=********/'
else
    echo "❌ Archivo .env NO ENCONTRADO en ~/misitio"
fi
echo -e "\n--- FIN DEL REPORTE ---"
