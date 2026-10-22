#!/usr/bin/env python3
"""Neon Keys · convierte un personaje pixel art hecho con IA en pixel art limpio y animable.

La IA (ChatGPT, Gemini, fal.ai…) da el parecido y el detalle, pero su "pixel art" es una imagen grande con
pixeles irregulares, fondo blanco y cientos de colores casi iguales. Aquí se arregla con el skill
pixel-art-studio (ADR-012): se quita el fondo, se recupera la cuadrícula real (cada pixel de verdad = un
bloque de N pixeles de la imagen), se limpian pixeles sueltos y se fija la paleta. Después se le dibujan
encima los gestos para hablar (boca abierta, gritando ¡gol!).

Uso:
    .venv/bin/python pixel_ia.py alan          # → out/personajes/alan-pixel.png (1x) + alan-pixel-hoja.png
    .venv/bin/python pixel_ia.py luis-caminar  # tira de caminata → luis-caminar.png (1x) + .gif + -hoja.png
"""

import argparse
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "pixel-art-studio" / "scripts"))
import pixelstudio as ps  # noqa: E402

OUT = ROOT / "out" / "personajes"

# fuente: imagen de la IA · bloque: tamaño de un pixel real en la imagen de la IA · colores: paleta final
# boca: (x, y) del centro de los labios en el sprite limpio, para dibujar los gestos de hablar
PERSONAJES = {
    "alan": dict(fuente="out/personajes/ia/alan-ia.png", bloque=10, colores=64, boca=(68, 48)),
    # tira de caminata de lado (estilo Metal Slug): varios cuadros en una fila
    "luis-caminar": dict(fuente="out/personajes/ia/luis-caminar-ia.png", bloque=6, colores=48, tira=True),
    "alan-caminar": dict(fuente="out/personajes/ia/alan-caminar-ia.png", bloque=6, colores=72, tira=True),
    # hojas de poses sentados para el podcast en el set (2 filas × 4: cerrada, hablando, abierta, parpadeo /
    # mano, mano hablando, dedo arriba, hombros). Vienen ya con fondo transparente (con_alfa)
    "luis-poses": dict(fuente="out/personajes/ia/luis-poses-ia.png", bloque=4.5, colores=64, tira=True,
                       con_alfa=True, columnas=4),
    "alan-poses": dict(fuente="out/personajes/ia/alan-poses-ia.png", bloque=4.5, colores=64, tira=True,
                       con_alfa=True, columnas=4),
}


def quitar_fondo(im):
    """Vuelve transparente el fondo blanco liso, rellenando desde los bordes (lo blanco de adentro,
    como franjas o dientes, no se toca)."""
    a = np.array(im.convert("RGB")).astype(int)
    blanco = (a.min(2) > 225) & ((a.max(2) - a.min(2)) < 30)
    H, W = blanco.shape
    fondo = np.zeros_like(blanco)
    q = deque()
    for y in range(H):
        for x in range(W):
            if (y in (0, H - 1) or x in (0, W - 1)) and blanco[y, x]:
                fondo[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < H and 0 <= nx < W and blanco[ny, nx] and not fondo[ny, nx]:
                fondo[ny, nx] = True
                q.append((ny, nx))
    return Image.fromarray(np.dstack([a, np.where(fondo, 0, 255)]).astype(np.uint8), "RGBA")


def limpiar(cfg):
    """Imagen de la IA → sprite 1x con cuadrícula real, sin restos de fondo y paleta fija."""
    src = quitar_fondo(Image.open(ROOT / cfg["fuente"]))
    a = np.array(ps.block_downscale(src, cfg["bloque"])).astype(int)
    for _ in range(2):              # restos blancos del fondo pegados a la silueta
        op = a[..., 3] > 0
        borde = np.zeros_like(op)
        borde[1:] |= ~op[:-1]
        borde[:-1] |= ~op[1:]
        borde[:, 1:] |= ~op[:, :-1]
        borde[:, :-1] |= ~op[:, 1:]
        a[(a[..., :3].min(2) > 200) & op & borde, 3] = 0
    tmp = OUT / ".tmp-pixel-ia.png"
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a.astype(np.uint8), "RGBA").save(tmp)
    s = ps.Sprite.from_png(str(tmp), scale=1)
    s.clean(max_colors=cfg["colores"], despeckle_min=3, dedupe_tol=8)
    tmp.unlink()
    return s.composite(1)


def limpiar_tira(cfg):
    """Tira de caminata de la IA → cuadros 1x del mismo tamaño, con los pies en la misma línea, la cabeza
    en la misma columna (así el personaje camina en su lugar) y una sola paleta para todos.
    Si la hoja trae varias filas, se ponen una tras otra como una sola tira."""
    src = Image.open(ROOT / cfg["fuente"])
    src = src.convert("RGBA") if cfg.get("con_alfa") else quitar_fondo(src)
    small = np.array(ps.block_downscale(src, cfg["bloque"]))   # toda la tira junta: misma cuadrícula
    filas = np.where((small[..., 3] > 0).any(1))[0]
    cortes = [i + 1 for i, (a, b) in enumerate(zip(filas[:-1], filas[1:])) if b - a > 2]
    if cortes:                      # varias filas → una sola tira, todas con el mismo alto
        bandas = np.split(filas, cortes)
        alto_f = max(b[-1] - b[0] + 1 for b in bandas)
        piezas = [small[b[-1] + 1 - alto_f:b[-1] + 1] for b in bandas]
        n = cfg.get("columnas")     # poses que casi se tocan (manos): se cortan en partes iguales
        if n:
            cw = small.shape[1] / n
            piezas = [p[:, round(i * cw):round((i + 1) * cw)] for p in piezas for i in range(n)]
        sep = np.zeros((alto_f, 6, 4), np.uint8)
        small = np.concatenate([x for p in piezas for x in (p, sep)][:-1], axis=1)
    op = small[..., 3] > 0
    cols = np.where(op.any(0))[0]
    grupos, ini = [], cols[0]
    for a, b in zip(cols[:-1], cols[1:]):
        if b - a > 2:
            grupos.append((ini, a))
            ini = b
    grupos.append((ini, cols[-1]))
    grupos = [g for g in grupos if g[1] - g[0] > 10]           # sin restos sueltos
    cuadros = []
    for x0, x1 in grupos:
        m = op[:, x0:x1 + 1]
        rows = np.where(m.any(1))[0]
        top, bot = rows[0], rows[-1]
        cabeza = m[top:top + 12]
        cx = x0 + np.where(cabeza.any(0))[0].mean()
        cuadros.append((x0, x1, top, bot, cx))
    alto = max(c[3] - c[2] for c in cuadros) + 3
    izq = max(c[4] - c[0] for c in cuadros) + 1
    der = max(c[1] - c[4] for c in cuadros) + 1
    ancho = int(np.ceil(izq + der))
    tira = np.zeros((alto, ancho * len(cuadros), 4), np.uint8)
    for i, (x0, x1, top, bot, cx) in enumerate(cuadros):
        pieza = small[top:bot + 1, x0:x1 + 1]
        ox = i * ancho + int(round(izq - (cx - x0)))
        oy = alto - 1 - (bot - top)
        tira[oy:oy + pieza.shape[0], ox:ox + pieza.shape[1]] = pieza
    tmp = OUT / ".tmp-pixel-ia.png"
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(tira, "RGBA").save(tmp)
    s = ps.Sprite.from_png(str(tmp), scale=1)
    s.clean(max_colors=cfg["colores"], despeckle_min=3, dedupe_tol=8)
    tmp.unlink()
    img = s.composite(1)
    return [img.crop((i * ancho, 0, (i + 1) * ancho, alto)) for i in range(len(cuadros))]


def hoja_tira(nombre, cuadros, path_hoja, path_gif):
    """Hoja para aprobar (los cuadros en fila + uno grande) y GIF de la caminata en loop."""
    from neon_keys import COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, FONT_TEXT, font, glow_text
    fondo = (10, 5, 26)
    w, h = cuadros[0].size
    sc = 6
    frames = []
    for c in cuadros:
        f = Image.new("RGB", (w * sc + 40, h * sc + 40), fondo)
        big = c.resize((w * sc, h * sc), Image.NEAREST)
        f.paste(big, (20, 20), big)
        frames.append(f)
    frames[0].save(path_gif, save_all=True, append_images=frames[1:], duration=120, loop=0)
    Wd, Hd = 1080, 1350
    img = Image.new("RGB", (Wd, Hd), fondo)
    d = ImageDraw.Draw(img)
    for x in range(0, Wd, 60):
        d.line([(x, 0), (x, Hd)], fill=(26, 14, 52))
    for y in range(0, Hd, 60):
        d.line([(0, y), (Wd, y)], fill=(26, 14, 52))
    img = glow_text(img, (Wd / 2, 70), nombre.upper(), font(FONT_BOLD, 70, 2), (255, 255, 255), COLOR_LEFT,
                    radius=16)
    img = glow_text(img, (Wd / 2, 135), "caminata de lado · pixel art (IA + limpieza)", font(FONT_TEXT, 30, 0),
                    (220, 210, 255), COLOR_RIGHT, radius=8)
    big = cuadros[0].resize((w * 7, h * 7), Image.NEAREST)
    img.paste(big, ((Wd - big.width) // 2, 180), big)
    d = ImageDraw.Draw(img)
    k = 3
    paso = Wd // len(cuadros)
    for i, c in enumerate(cuadros):
        s = c.resize((w * k, h * k), Image.NEAREST)
        x = i * paso + (paso - s.width) // 2
        img.paste(s, (x, 1000), s)
        d.text((i * paso + paso / 2, 1000 + s.height + 20), f"paso {i + 1}", font=font(FONT_TEXT, 24, 0),
               fill=(180, 170, 220), anchor="mm")
    img.save(path_hoja)
    return path_hoja


def boca(sprite, n, cfg):
    """Gesto de la boca sobre el sprite limpio: 0 = como viene, 1 = hablando, 2 = gritando ¡gol!"""
    im = sprite.copy()
    if n == 0:
        return im
    q = im.load()
    cx, cy = cfg["boca"]
    labio = q[cx, cy + 1]
    oscuro, dientes, lengua = (46, 14, 20, 255), (236, 228, 218, 255), (190, 70, 80, 255)
    if n == 1:
        for x in range(cx - 3, cx + 4):
            q[x, cy] = q[x, cy + 1] = oscuro
            q[x, cy + 2] = labio
        for x in range(cx - 2, cx + 3):
            q[x, cy] = dientes
    else:
        for x in range(cx - 4, cx + 5):
            for y in range(cy - 1, cy + 4):
                if not (abs(x - cx) == 4 and y in (cy - 1, cy + 3)):
                    q[x, y] = oscuro
            q[x, cy + 4] = labio
        for x in range(cx - 3, cx + 4):
            q[x, cy - 1] = dientes
        for x in range(cx - 2, cx + 3):
            q[x, cy + 3] = lengua
    return im


def hoja(nombre, sprite, cfg, path):
    """Imagen para aprobar: el personaje grande + sus gestos de boca."""
    from neon_keys import COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, FONT_TEXT, font, glow_text
    Wd, Hd = 1080, 1350
    img = Image.new("RGB", (Wd, Hd), (10, 5, 26))
    d = ImageDraw.Draw(img)
    for x in range(0, Wd, 60):
        d.line([(x, 0), (x, Hd)], fill=(26, 14, 52))
    for y in range(0, Hd, 60):
        d.line([(0, y), (Wd, y)], fill=(26, 14, 52))
    img = glow_text(img, (Wd / 2, 70), nombre.upper(), font(FONT_BOLD, 70, 2), (255, 255, 255), COLOR_LEFT,
                    radius=16)
    img = glow_text(img, (Wd / 2, 135), "pixel art (IA + limpieza) · propuesta", font(FONT_TEXT, 30, 0),
                    (220, 210, 255), COLOR_RIGHT, radius=8)
    sc = max(1, 760 // max(sprite.size))
    big = sprite.resize((sprite.width * sc, sprite.height * sc), Image.NEAREST)
    img.paste(big, ((Wd - big.width) // 2, 180), big)
    d = ImageDraw.Draw(img)
    cx, cy = cfg["boca"]
    caja = (cx - 22, cy - 26, cx + 22, cy + 18)
    for i, label in enumerate(("cerrada", "hablando", "¡gol!")):
        c = boca(sprite, i, cfg).crop(caja)
        c = c.resize((c.width * 6, c.height * 6), Image.NEAREST)
        x = 60 + i * 340
        img.paste(c, (x, 980), c)
        d.text((x + c.width / 2, 980 + c.height + 22), label, font=font(FONT_TEXT, 28, 0), fill=(180, 170, 220),
               anchor="mm")
    img.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description="Limpia un personaje pixel art hecho con IA.")
    ap.add_argument("personaje", choices=sorted(PERSONAJES))
    args = ap.parse_args()
    cfg = PERSONAJES[args.personaje]
    if cfg.get("tira"):
        cuadros = limpiar_tira(cfg)
        w, h = cuadros[0].size
        hoja_1x = Image.new("RGBA", (w * len(cuadros), h))
        for i, c in enumerate(cuadros):
            hoja_1x.paste(c, (i * w, 0))
        master = OUT / f"{args.personaje}.png"
        hoja_1x.save(master)
        print(master, f"{len(cuadros)} cuadros de {w}x{h}")
        print(hoja_tira(args.personaje.split("-")[0], cuadros, OUT / f"{args.personaje}-hoja.png",
                        OUT / f"{args.personaje}.gif"))
        return
    sprite = limpiar(cfg)
    master = OUT / f"{args.personaje}-pixel.png"
    sprite.save(master)
    print(master, sprite.size)
    print(hoja(args.personaje, sprite, cfg, OUT / f"{args.personaje}-pixel-hoja.png"))


if __name__ == "__main__":
    main()
