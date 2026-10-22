#!/usr/bin/env python3
"""Neon Keys · imagen de perfil (avatar) para TikTok.

Genera PNG cuadrados de 1080×1080 con la misma estética de los videos. TikTok los muestra recortados en
círculo y muy pequeños, así que todo lo importante va dentro del círculo central y sin letras chicas.

El canal no es solo de piano (también datos curiosos, ciencia, bolitas), así que hay dos familias:
"piano-*" (guardadas, con teclado) y "marca-*" (generales, sin teclado).

Uso:
    .venv/bin/python avatar.py            # genera todos en out/avatares/
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from neon_keys import BG_BOTTOM, BG_TOP, BRAND_GLOW, COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, font, glow_text

ROOT = Path(__file__).resolve().parent
S = 1080                     # lado del cuadrado
C = S / 2                    # centro
WHITE = (255, 255, 255)
GRID = (255, 40, 200)


def background():
    """Degradado oscuro con un resplandor violeta al centro."""
    y, x = np.mgrid[0:S, 0:S]
    grad = (y / S)[..., None]
    top, bot = np.array(BG_TOP), np.array(BG_BOTTOM)
    arr = top + (bot - top) * grad
    r = np.hypot(x - C, y - C) / (S / 2)
    arr += (np.clip(1 - r, 0, 1) ** 2)[..., None] * np.array([40, 10, 60])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def neon(base, draw_fn, radius=14, strength=2):
    """Dibuja con draw_fn(ImageDraw, es_halo) una capa de halo y una de núcleo y las combina."""
    glow, core = Image.new("RGB", (S, S)), Image.new("RGB", (S, S))
    draw_fn(ImageDraw.Draw(glow), True)
    draw_fn(ImageDraw.Draw(core), False)
    halo = glow.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(strength - 1):
        halo = ImageChops.add(halo, halo)
    return ImageChops.lighter(ImageChops.screen(base, halo), core)


def floor(base, top_y):
    """Piso synthwave en perspectiva desde top_y hasta abajo."""
    g = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(g)
    for i in range(-10, 11):
        d.line([(C + i * 14, top_y), (C + i * 110, S)], fill=GRID, width=3)
    for k in range(1, 9):
        y = top_y + (S - top_y) * (k / 8) ** 1.8
        d.line([(0, y), (S, y)], fill=GRID, width=3)
    g = Image.blend(Image.new("RGB", (S, S)), g, 0.4)
    return ImageChops.add(base, ImageChops.add(g, g.filter(ImageFilter.GaussianBlur(6))))


def keys(d, x0, x1, y0, h, halo, n_white=7, lit=(2, 5)):
    """Mini teclado; las teclas en `lit` se encienden en cian/magenta."""
    w = (x1 - x0) / n_white
    for i in range(n_white):
        x = x0 + i * w
        c = (COLOR_RIGHT if i == lit[1] else COLOR_LEFT) if i in lit else (235, 230, 255)
        if halo and i not in lit:
            continue
        d.rounded_rectangle([x + 4, y0, x + w - 4, y0 + h], radius=10, fill=c)
    for i in (0, 1, 3, 4, 5):            # negras: Do#, Re#, Fa#, Sol#, La#
        if halo:
            continue
        x = x0 + (i + 1) * w
        d.rounded_rectangle([x - w * 0.3, y0, x + w * 0.3, y0 + h * 0.6], radius=6, fill=(20, 8, 36))


def avatar_a():
    """Monograma NK sobre un mini teclado y piso synthwave."""
    img = floor(background(), 760)
    nk = font(FONT_BOLD, 400, 2)
    # La N termina en el centro y la K empieza ahí; cada una con su color.
    n_layer = glow_text(Image.new("RGB", (S, S)), (C + 10, 420), "N", nk, WHITE, COLOR_RIGHT, radius=26, anchor="rm")
    k_layer = glow_text(Image.new("RGB", (S, S)), (C - 10, 420), "K", nk, WHITE, COLOR_LEFT, radius=26, anchor="lm")
    img = ImageChops.screen(img, ImageChops.screen(n_layer, k_layer))
    return neon(img, lambda d, h: keys(d, 250, 830, 620, 150, h), radius=16)


def avatar_b():
    """Anillo neón con hueco (como el video de las bolitas) y teclado dentro."""
    img = background()
    r = 380

    def ring(d, halo):
        box = [C - r, C - r, C + r, C + r]
        d.arc(box, -60, 210, fill=COLOR_RIGHT, width=34 if halo else 16)
        d.arc(box, 210, 240, fill=COLOR_LEFT, width=34 if halo else 16)
        # Bolitas escapando por el hueco.
        for k, (a, dist, rad) in enumerate([(-80, r + 10, 26), (-72, r + 95, 20), (-86, r + 170, 15)]):
            x, y = C + math.cos(math.radians(a)) * dist, C + math.sin(math.radians(a)) * dist
            if y - rad < 0:
                continue
            c = COLOR_LEFT if k % 2 else COLOR_RIGHT
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=c)

    img = neon(img, ring, radius=18)
    return neon(img, lambda d, h: keys(d, 300, 780, 440, 230, h, lit=(1, 4)), radius=16)


def avatar_c():
    """Notas cayendo sobre el teclado: la imagen de los videos de piano, en miniatura."""
    img = floor(background(), 820)
    x0, x1 = 230, 850
    w = (x1 - x0) / 7
    bars = [(1, 180, 520, COLOR_LEFT), (2, 330, 560, COLOR_RIGHT), (4, 120, 420, COLOR_RIGHT),
            (5, 260, 560, COLOR_LEFT), (3, 70, 250, COLOR_RIGHT)]

    def notes(d, halo):
        for i, y0, y1, c in bars:
            x = x0 + i * w
            d.rounded_rectangle([x + 14, y0, x + w - 14, y1], radius=18, fill=c)

    img = neon(img, notes, radius=20)
    return neon(img, lambda d, h: keys(d, x0, x1, 590, 210, h, lit=(2, 4)), radius=16)


def nk_layer(cx, cy, size, radius=26):
    """Monograma NK: la N (cian) termina en cx y la K (magenta) empieza ahí."""
    f = font(FONT_BOLD, size, 2)
    n = glow_text(Image.new("RGB", (S, S)), (cx + size * 0.025, cy), "N", f, WHITE, COLOR_RIGHT, radius=radius, anchor="rm")
    k = glow_text(Image.new("RGB", (S, S)), (cx - size * 0.025, cy), "K", f, WHITE, COLOR_LEFT, radius=radius, anchor="lm")
    return ImageChops.screen(n, k)


def marca_anillo():
    """NK dentro del anillo con hueco; unas bolitas escapan (guiño al video de las bolitas)."""
    img = background()
    r = 400

    def ring(d, halo):
        box = [C - r, C - r, C + r, C + r]
        w = 34 if halo else 16
        d.arc(box, -55, 120, fill=COLOR_RIGHT, width=w)
        d.arc(box, 120, 235, fill=COLOR_LEFT, width=w)
        for k, (a, dist, rad) in enumerate([(-74, r + 20, 24), (-90, r + 100, 18)]):
            x, y = C + math.cos(math.radians(a)) * dist, C + math.sin(math.radians(a)) * dist
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=COLOR_LEFT if k % 2 else COLOR_RIGHT)

    img = neon(img, ring, radius=18)
    return ImageChops.screen(img, nk_layer(C, C + 10, 360))


def marca_atomo(contorno=True):
    """NK en el centro de órbitas neón con electrones: ciencia + bolitas.

    contorno=True: las órbitas pasan por detrás de las letras (se recortan solo al ras de cada letra).
    contorno=False: sin recorte; letras y órbitas se mezclan."""
    img = background()
    rx, ry = 440, 150
    colors = (COLOR_RIGHT, COLOR_LEFT, (255, 225, 70))

    def orbits(d, halo):
        for k, ang in enumerate((0, 60, 120)):
            pts = []
            a = math.radians(ang)
            for t in np.linspace(0, 2 * math.pi, 200):
                x, y = rx * math.cos(t), ry * math.sin(t)
                pts.append((C + x * math.cos(a) - y * math.sin(a), C + x * math.sin(a) + y * math.cos(a)))
            d.line(pts + [pts[0]], fill=colors[k], width=18 if halo else 6)
            t = (0.6, 2.4, 4.3)[k]
            x, y = rx * math.cos(t), ry * math.sin(t)
            ex, ey = C + x * math.cos(a) - y * math.sin(a), C + x * math.sin(a) + y * math.cos(a)
            d.ellipse([ex - 26, ey - 26, ex + 26, ey + 26], fill=colors[k])

    img = neon(img, orbits, radius=16)
    if contorno:
        # Máscara con la forma de las letras, un poco engordada: ahí se borran las órbitas.
        f = font(FONT_BOLD, 300, 2)
        mask = Image.new("L", (S, S), 0)
        md = ImageDraw.Draw(mask)
        md.text((C + 7.5, C + 10), "N", font=f, fill=255, anchor="rm", stroke_width=14, stroke_fill=255)
        md.text((C - 7.5, C + 10), "K", font=f, fill=255, anchor="lm", stroke_width=14, stroke_fill=255)
        img = Image.composite(background(), img, mask.filter(ImageFilter.GaussianBlur(3)))
    return ImageChops.screen(img, nk_layer(C, C + 10, 300))


def marca_piso():
    """NK grande sobre el piso synthwave, sin teclado: la marca sola."""
    img = floor(background(), 700)
    return ImageChops.screen(img, nk_layer(C, 470, 460, radius=30))


def main():
    out = ROOT / "out" / "avatares"
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in (("piano-a", avatar_a), ("piano-b", avatar_b), ("piano-c", avatar_c),
                     ("marca-anillo", marca_anillo), ("marca-atomo", marca_atomo),
                     ("marca-atomo-sin-contorno", lambda: marca_atomo(False)), ("marca-piso", marca_piso)):
        path = out / f"avatar-{name}.png"
        fn().save(path)
        print(path)


if __name__ == "__main__":
    main()
