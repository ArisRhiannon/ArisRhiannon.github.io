import os

path = "/home/ubuntu/misitio/src/layouts/Base.astro"

# Usamos path.exists que es más robusto para verificar el archivo
if os.path.exists(path):
    with open(path, "r") as f:
        content = f.read()

    # 1. Restaurar el cursor en todo el documento (CSS)
    content = content.replace("cursor: none;", "cursor: auto;")

    # 2. Eliminar los elementos HTML que Claude inyectó
    content = content.replace('<div id="cursor-ring" aria-hidden="true"></div>', "")
    content = content.replace('<div id="cursor-dot"  aria-hidden="true"></div>', "")
    content = content.replace('<canvas id="cursor-trail" aria-hidden="true"></canvas>', "")

    # 3. Desactivar la lógica de JavaScript para ahorrar recursos
    content = content.replace("initCursor();", "// initCursor();")

    with open(path, "w") as f:
        f.write(content)
    print("✅ Base.astro purificado. El cursor nativo ha retomado el control.")
else:
    print(f"❌ Error Crítico: No se encontró el archivo en {path}")
