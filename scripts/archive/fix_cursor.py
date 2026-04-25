import os

path = "/home/ubuntu/misitio/src/layouts/Base.astro"

if os.is_file(path):
    with open(path, "r") as f:
        content = f.read()

    # 1. Restaurar el cursor en el CSS
    content = content.replace("cursor: none;", "cursor: auto;")

    # 2. Eliminar los elementos HTML del cursor
    content = content.replace('<div id="cursor-ring" aria-hidden="true"></div>', "")
    content = content.replace('<div id="cursor-dot"  aria-hidden="true"></div>', "")
    content = content.replace('<canvas id="cursor-trail" aria-hidden="true"></canvas>', "")

    # 3. Desactivar la inicialización del script del cursor
    # Buscamos la llamada a initCursor() y la comentamos
    content = content.replace("initCursor();", "// initCursor();")

    with open(path, "w") as f:
        f.write(content)
    print("✅ Cursor de NieR desactivado. Sistema operativo retomando el control.")
else:
    print("❌ No se encontró Base.astro")
