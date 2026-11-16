"""Crea versiones livianas para la web de fotos, artes y videos pesados.

Uso (desde la carpeta del sitio):
    python herramientas/optimizar_para_web.py "Fotos/Padel Point 360 Torneo Reid" "Animaciones/LNB"

Las rutas son relativas a "Portafolio diigital de trabajos". Cada archivo se
guarda en optimizadas/<misma ruta>, sin tocar el original:
  - Fotos/artes sin transparencia -> JPG, máx. 1600 px de lado corto y 2048 de lado largo
  - Imágenes con transparencia    -> WebP (conserva la transparencia)
  - Videos .mp4/.mov              -> MP4 H.264 720p con inicio rápido (necesita ffmpeg)
Archivos de trabajo (.psd, .ai, audio) se ignoran. Si el destino ya existe, se salta.
Imprime la ruta que hay que poner en PROJECTS_DATA.
"""
import os
import subprocess
import sys

from PIL import Image, ImageOps

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "Portafolio diigital de trabajos"
LADO_CORTO = 1600
LADO_LARGO = 2048
IMAGENES = (".jpg", ".jpeg", ".png", ".webp")
VIDEOS = (".mp4", ".mov")


def tiene_transparencia(im):
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        return im.convert("RGBA").getchannel("A").getextrema()[0] < 250
    return False


def optimizar_imagen(origen, destino_sin_ext):
    im = ImageOps.exif_transpose(Image.open(origen))
    alfa = tiene_transparencia(im)
    escala = min(1.0, LADO_CORTO / min(im.size), LADO_LARGO / max(im.size))
    if escala < 1:
        im = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
    if alfa:
        destino = destino_sin_ext + ".webp"
        if not os.path.exists(destino):
            im.convert("RGBA").save(destino, "WEBP", quality=85, method=6)
    else:
        destino = destino_sin_ext + ".jpg"
        if not os.path.exists(destino):
            im.convert("RGB").save(destino, "JPEG", quality=85, optimize=True, progressive=True)
    return destino


def optimizar_video(origen, destino_sin_ext):
    destino = destino_sin_ext + ".mp4"
    if not os.path.exists(destino):
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", origen,
            "-vf", "scale='if(gt(iw,ih),-2,720)':'if(gt(iw,ih),720,-2)'",
            "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", destino,
        ], check=True)
    return destino


for carpeta in sys.argv[1:]:
    entrada = os.path.join(RAIZ, BASE, carpeta)
    salida = os.path.join(RAIZ, "optimizadas", carpeta)
    os.makedirs(salida, exist_ok=True)
    for f in sorted(os.listdir(entrada)):
        origen = os.path.join(entrada, f)
        nombre, ext = os.path.splitext(f)
        destino_sin_ext = os.path.join(salida, nombre)
        if ext.lower() in IMAGENES:
            destino = optimizar_imagen(origen, destino_sin_ext)
        elif ext.lower() in VIDEOS:
            destino = optimizar_video(origen, destino_sin_ext)
        else:
            continue
        kb_antes, kb_despues = os.path.getsize(origen) // 1024, os.path.getsize(destino) // 1024
        web = os.path.relpath(destino, RAIZ).replace("\\", "/")
        print(f"{kb_antes:>7} KB -> {kb_despues:>5} KB  {web}")
