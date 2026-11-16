"""Genera las miniaturas livianas (WebP) que usan las tarjetas del portafolio.

Uso (desde la carpeta del sitio):
    python herramientas/generar_miniaturas.py

Lee PROJECTS_DATA y la función thumbOf() directamente de index.html (con Node),
así los nombres coinciden siempre con los que pide la página. Solo crea las
miniaturas que faltan; las fotos originales no se tocan. Si una miniatura no
existe, la página usa la foto original, así que nada se rompe.
"""
import json
import os
import re
import subprocess
import sys
from urllib.parse import unquote

from PIL import Image, ImageOps

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(RAIZ, "index.html")
# Las tarjetas son 4:5 y miden como mucho ~380px de ancho => 2x para retina
CAJA_W, CAJA_H = 640, 800
CALIDAD = 78
MAX_SLIDES = 5  # igual que renderProjectCards()

html = open(INDEX, encoding="utf-8").read()
datos = re.search(r"const PROJECTS_DATA = (\[.*?\n    \]);", html, re.S).group(1)
thumb_fn = re.search(r"(function thumbOf\(src\) \{.*?\n    \})", html, re.S).group(1)

js = f"""
const PROJECTS_DATA = {datos};
{thumb_fn}
const out = [];
for (const p of PROJECTS_DATA) {{
  const slides = [{{ src: p.cover }}].concat(p.images.filter(im => im.src !== p.cover)).slice(0, {MAX_SLIDES});
  for (const s of slides) out.push([s.src, thumbOf(s.src)]);
}}
process.stdout.write(JSON.stringify(out));
"""
pares = json.loads(subprocess.run(["node", "-"], input=js, capture_output=True, text=True,
                                  encoding="utf-8", check=True).stdout)

creadas = saltadas = 0
faltan = []
antes = despues = 0
for src, thumb in dict(pares).items():
    destino = os.path.join(RAIZ, thumb)
    origen = os.path.join(RAIZ, unquote(src))
    if os.path.exists(destino):
        saltadas += 1
        continue
    if not os.path.exists(origen):
        faltan.append(src)
        continue
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    im = ImageOps.exif_transpose(Image.open(origen))
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    escala = min(1.0, max(CAJA_W / im.width, CAJA_H / im.height))
    if escala < 1:
        im = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
    # Recorte centrado a 4:5: la tarjeta usa object-fit: cover centrado, así que se ve igual
    if im.width > CAJA_W or im.height > CAJA_H:
        w, h = min(im.width, CAJA_W), min(im.height, CAJA_H)
        x, y = (im.width - w) // 2, (im.height - h) // 2
        im = im.crop((x, y, x + w, y + h))
    im.save(destino, "WEBP", quality=CALIDAD, method=6)
    antes += os.path.getsize(origen)
    despues += os.path.getsize(destino)
    creadas += 1

print(f"Miniaturas creadas: {creadas}, ya existían: {saltadas}")
if creadas:
    print(f"Peso: {antes / 1e6:.1f} MB originales -> {despues / 1e6:.1f} MB miniaturas")
for f in faltan:
    print("NO ENCONTRADA:", f, file=sys.stderr)
