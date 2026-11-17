#!/usr/bin/env python3
"""Neon Keys · dato curioso del ajolote en pixel art 16-bit (estilo arcade neón).

Todo se dibuja con código: el ajolote (sprites.py), el canal de Xochimilco, el contador tipo arcade y la
música chiptune (sintetizada aquí, sin samples ni derechos de terceros). Los subtítulos usan las fuentes
de la marca y salen palabra por palabra, como en datos_curiosos.py.

Uso:
    .venv/bin/python ajolote.py                         # video completo → out/videos/datos/dato-ajolote.mp4
    .venv/bin/python ajolote.py --hasta 15              # prueba de 15 s → out/pruebas/datos/dato-ajolote-prueba.mp4
    .venv/bin/python ajolote.py --preview 9             # solo un cuadro PNG en t=9s
"""

import argparse
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import sprites
from datos_curiosos import HIGHLIGHT, WORD_IN, ease_out, layout, parse_words
from neon_keys import (BRAND_GLOW, COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, FPS, H, SAMPLE_RATE, W, font,
                       glow_text, make_brand_layer)

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "out" / "videos" / "datos" / "dato-ajolote.mp4"

# --- Pixel art: la escena se dibuja a 180×320 y se agranda ×6 sin suavizar (mismo pixel que el sprite) ---
PX = 6
LW, LH = W // PX, H // PX
MAGENTA, CYAN, PURPLE, LIME = (255, 50, 210), (0, 240, 255), (150, 60, 255), (170, 255, 60)
RED, YELLOW, ORANGE, WHITE = (255, 50, 70), (255, 225, 70), (255, 150, 30), (255, 255, 255)
BOX = (6, 70, 173, 200)          # caja de la escena (x0, y0, x1, y1) en pixeles chicos
SURFACE_Y = 88                   # arriba: cielo; abajo: agua
HUD_Y = 54
DURATION = 65.5

# --- Guion: (inicio, fin, frase); *palabras* resaltadas ---
SCENES = [
    (0.4, 6.4, "Este animal mexicano tiene un *superpoder*"),
    (6.6, 13.9, "Si pierde una *pata*… ¡le vuelve a crecer!"),
    (14.1, 21.9, "Y también su *cola*, partes del *corazón* y hasta del *cerebro*"),
    (22.1, 27.9, "Y todo *sin dejar cicatriz*"),
    (28.1, 34.9, "Además, nunca deja de ser *bebé*: conserva sus *branquias* toda la vida"),
    (35.1, 40.9, "Y así puede vivir *más de 10 años*"),
    (41.1, 47.9, "En libertad solo vive en los canales de *Xochimilco*, en la CDMX"),
    (48.1, 54.9, "Y está en *peligro crítico* de extinción"),
    (55.1, 60.9, "La ciencia lo estudia para aprender a *regenerar* tejidos"),
    (61.1, 65.2, "Es el *ajolote*. Sígueme para más datos curiosos"),
]
WORD_DELAY = 0.17
SUB_Y = 1385
TAG_Y = 230

# --- Momentos clave (los usan el dibujo y el sonido) ---
LEG_POP, LEG_GROW = 8.0, (9.5, 12.0)
TAIL_POP, TAIL_GROW = 14.8, (15.8, 18.0)
HEART_BUILD = (18.5, 20.5)
BRAIN_GLOW = (20.5, 22.0)
SHINE = (23.0, 24.6)
GILLS = (28.0, 35.0)
DAYS = (35.0, 41.0)
BOAT = (41.0, 48.0)
ALERT = (48.0, 55.0)
SCIENCE = (55.0, 61.0)
PARTY = 61.0

# Puntos del sprite (pixeles del sprite, origen arriba a la izquierda).
SPR_LEG = (77, 50)
SPR_TAIL = (16, 38)
SPR_HEART = (55, 34)
SPR_BRAIN = (84, 18)
SPR_HEAD = (96, 30)


def between(t, span):
    return span[0] <= t < span[1]


def frac(t, span, steps=5):
    """0→1 dentro de span, en escalones (crece 'bloque por bloque')."""
    k = min(1.0, max(0.0, (t - span[0]) / (span[1] - span[0])))
    return math.floor(k * steps) / steps


# ---------------------------------------------------------------- Pixel helpers

DIGITS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
}
HEART = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
SMALL_HEART = [".X.X.", "XXXXX", ".XXX.", "..X.."]
BRAIN = [".XXXX.", "XXXXXX", "XXXXXX", ".X..X."]


def blit(d, x, y, pattern, color, limit=None):
    """Dibuja un patrón de 'X'; con limit solo los primeros N pixeles (para 'construirlo')."""
    n = 0
    for j, row in enumerate(pattern):
        for i, ch in enumerate(row):
            if ch in "X1":
                if limit is not None and n >= limit:
                    return
                d.point((x + i, y + j), fill=color)
                n += 1


def pattern_size(pattern):
    return sum(row.count("X") + row.count("1") for row in pattern)


def draw_number(d, cx, y, text, color):
    w = len(text) * 4 - 1
    x = cx - w // 2
    for ch in text:
        blit(d, x, y, DIGITS[ch], color)
        x += 4


def sparkle(d, x, y, color):
    d.point((x, y), fill=WHITE)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        d.point((x + dx, y + dy), fill=color)


# ---------------------------------------------------------------- Ajolote

def axolotl_pos(t):
    """Esquina superior izquierda del sprite en la escena (pixeles chicos)."""
    enter = min(1.0, t / 3.0)
    home = 26
    if between(t, SCIENCE):          # se hace a un lado para que quepa el ADN
        home -= 10 * min(1.0, (t - SCIENCE[0]) / 0.8, (SCIENCE[1] - t) / 0.8)
    x = -sprites.SW + (home + sprites.SW) * ease_out(enter) + math.sin(t * 0.6) * 4 * enter
    y = 112 + math.sin(t * 1.8) * 2
    return round(x), round(y)


def at(t, p):
    x, y = axolotl_pos(t)
    return x + p[0], y + p[1]


def axolotl_sprite(t):
    pata = 1.0 if t < LEG_POP else frac(t, LEG_GROW)
    cola = 1.0 if t < TAIL_POP else frac(t, TAIL_GROW, steps=6)
    tint = None
    if between(t, GILLS):
        g = 0.5 + 0.5 * math.sin((t - GILLS[0]) * 5)
        tint = tuple(int(c * g + m * (1 - g)) for c, m in zip(CYAN, MAGENTA))
    spr = sprites.ajolote(pata=pata, cola=cola, fase=t * 4, branquias=tint)
    if between(t, SHINE):            # brillo que recorre el cuerpo: "sin cicatriz"
        k = (t - SHINE[0]) / (SHINE[1] - SHINE[0])
        a = np.array(spr)
        band = -30 + int((sprites.SW + 60) * k)
        xs = np.arange(sprites.SW)[None, :] + np.arange(sprites.SH)[:, None] * 0.5
        mask = (np.abs(xs - band) < 3.5) & (a[..., 3] > 0)
        a[mask, :3] = np.minimum(255, a[mask, :3].astype(int) + 90)
        spr = Image.fromarray(a)
    return spr


# ---------------------------------------------------------------- Escena

POPS = [(LEG_POP, SPR_LEG), (TAIL_POP, SPR_TAIL)]
SCORE_EVENTS = [(LEG_POP, 100), (LEG_GROW[1], 500), (TAIL_POP, 100), (TAIL_GROW[1], 500),
                (HEART_BUILD[1], 1000), (BRAIN_GLOW[1], 1000), (SHINE[1], 500), (PARTY, 5000)]


def score_at(t):
    s = int(t * 20) * 5
    for te, pts in SCORE_EVENTS:
        if t >= te:
            s += int(pts * min(1.0, (t - te) / 0.6))
    if between(t, DAYS):
        s += int((t - DAYS[0]) * 300) * 10
    elif t >= DAYS[1]:
        s += int((DAYS[1] - DAYS[0]) * 300) * 10
    return s


def lives_at(t):
    if LEG_POP <= t < LEG_GROW[1] or TAIL_POP <= t < TAIL_GROW[1]:
        return 2
    if between(t, ALERT):
        return 1
    return 3


def make_background():
    """Fondo chico fijo: negro con cuadrícula neón de colores."""
    img = Image.new("RGB", (LW, LH), (6, 3, 16))
    d = ImageDraw.Draw(img)
    colors = [MAGENTA, CYAN, PURPLE, LIME]
    for i, x in enumerate(range(3, LW, 12)):
        d.line([(x, 0), (x, LH)], fill=tuple(v // 8 for v in colors[i % 4]))
    for i, y in enumerate(range(4, LH, 12)):
        d.line([(0, y), (LW, y)], fill=tuple(v // 8 for v in colors[(i + 1) % 4]))
    return img


def make_water():
    """Cielo, agua con degradado en bandas (look 16-bit) y fondo del canal; fijo."""
    x0, y0, x1, y1 = BOX
    img = Image.new("RGB", (x1 - x0 + 1, y1 - y0 + 1))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, x1 - x0, SURFACE_Y - y0], fill=(16, 8, 40))
    bands = [(8, 34, 86), (7, 30, 78), (6, 26, 70), (5, 22, 62), (4, 18, 54), (3, 14, 46)]
    h = y1 - SURFACE_Y
    for i, c in enumerate(bands):
        top = SURFACE_Y - y0 + i * h // len(bands)
        d.rectangle([0, top, x1 - x0, SURFACE_Y - y0 + (i + 1) * h // len(bands)], fill=c)
    rng = np.random.default_rng(11)   # piedritas del fondo
    d.rectangle([0, y1 - y0 - 6, x1 - x0, y1 - y0], fill=(36, 16, 64))
    for px, py in zip(rng.integers(0, x1 - x0, 40), rng.integers(y1 - y0 - 6, y1 - y0, 40)):
        d.point((int(px), int(py)), fill=(60, 30, 96))
    return img


def draw_scene(base, water, t):
    img = base.copy()
    x0, y0, x1, y1 = BOX
    img.paste(water, (x0, y0))
    alert = between(t, ALERT)
    if alert and int(t * 3) % 2 == 0:
        region = img.crop((x0, SURFACE_Y, x1 + 1, y1))
        img.paste(ImageChops.add(region, Image.new("RGB", region.size, (90, 0, 20))), (x0, SURFACE_Y))
    d = ImageDraw.Draw(img)

    # Estrellas.
    rng = np.random.default_rng(3)
    for sx, sy in zip(rng.integers(x0 + 2, x1 - 2, 18), rng.integers(y0 + 2, SURFACE_Y - 2, 18)):
        if (t * 2 + sx) % 3 > 0.6:
            d.point((int(sx), int(sy)), fill=(200, 190, 255))

    # Sol y luna que dan vueltas rápido ("pasan los años").
    if between(t, DAYS):
        p = ((t - DAYS[0]) / 1.2) % 1
        sx = x0 + 6 + p * (x1 - x0 - 12)
        sy = SURFACE_Y - 4 - math.sin(p * math.pi) * 10
        if int((t - DAYS[0]) / 0.6) % 2 == 0:
            d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=YELLOW)
        else:
            d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(230, 230, 255))
            d.ellipse([sx - 1, sy - 4, sx + 4, sy + 1], fill=(16, 8, 40))

    # Superficie ondulada.
    for xx in range(x0, x1 + 1):
        yy = SURFACE_Y + round(math.sin(xx * 0.3 + t * 3) * 0.8)
        d.point((xx, yy), fill=CYAN)
        d.point((xx, yy + 1), fill=(0, 120, 160))

    # Trajinera de Xochimilco.
    if between(t, BOAT):
        k = (t - BOAT[0]) / (BOAT[1] - BOAT[0])
        bx = round(x1 + 10 - k * (x1 - x0 + 70))
        by = SURFACE_Y - 2 + round(math.sin(t * 3))
        stripes = [RED, YELLOW, LIME, CYAN, MAGENTA, ORANGE]
        for i in range(48):
            d.line([(bx + i, by), (bx + i, by + 4)], fill=stripes[(i // 8) % len(stripes)])
        d.line([(bx + 2, by + 5), (bx + 45, by + 5)], fill=(120, 50, 20))
        d.line([(bx + 5, by - 1), (bx + 5, by - 11)], fill=YELLOW)
        d.line([(bx + 42, by - 1), (bx + 42, by - 11)], fill=YELLOW)
        d.arc([bx + 5, by - 19, bx + 42, by - 3], 180, 360, fill=MAGENTA, width=2)
        for i, fx in enumerate(range(bx + 9, bx + 40, 4)):
            d.point((fx, by - 15 + (i % 2)), fill=[ORANGE, YELLOW, RED][i % 3])

    # Plantas.
    for i, px in enumerate(range(x0 + 6, x1 - 2, 13)):
        h = 14 + (i * 7) % 12
        sway = math.sin(t * 1.5 + i)
        for j in range(h):
            xx = px + round(sway * j / h * 3)
            d.point((xx, y1 - 6 - j), fill=LIME if j % 4 else (90, 200, 40))
            if j % 4 == 2:
                d.point((xx + (1 if i % 2 else -1), y1 - 6 - j), fill=(120, 220, 50))

    # Burbujas que suben.
    for i in range(12):
        period = 3 + (i % 4)
        p = ((t + i * 0.77) / period) % 1
        bx = x0 + 8 + (i * 37) % (x1 - x0 - 16) + round(math.sin(t * 2 + i) * 1.5)
        by = round(y1 - 8 - p * (y1 - SURFACE_Y - 10))
        if i % 3 == 0:
            d.ellipse([bx - 1, by - 1, bx + 1, by + 1], outline=(150, 230, 255))
        else:
            d.point((bx, by), fill=(150, 230, 255))

    # ADN girando (los científicos).
    if between(t, SCIENCE):
        for yy in range(96, 186):
            ph = yy * 0.3 + t * 3
            a = 160 + round(math.sin(ph) * 6)
            b = 160 - round(math.sin(ph) * 6)
            d.point((a, yy), fill=CYAN)
            d.point((b, yy), fill=MAGENTA)
            if yy % 4 == 0:
                d.line([(min(a, b) + 1, yy), (max(a, b) - 1, yy)], fill=(90, 80, 140))

    # Ajolote (recortado a la caja).
    spr = axolotl_sprite(t)
    sx, sy = axolotl_pos(t)
    layer = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    layer.paste(spr, (sx, sy), spr)
    clip = Image.new("L", (LW, LH), 0)
    ImageDraw.Draw(clip).rectangle([x0, y0, x1, y1], fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), clip))
    img.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(img)

    # Corazón que se reconstruye pixel por pixel y luego late con ondas.
    if HEART_BUILD[0] <= t < SHINE[1] + 1:
        hx, hy = at(t, SPR_HEART)
        n = pattern_size(HEART)
        k = n if t >= HEART_BUILD[1] else int(n * (t - HEART_BUILD[0]) / (HEART_BUILD[1] - HEART_BUILD[0]))
        beat = (t - HEART_BUILD[0]) % 0.7 < 0.12
        blit(d, hx - 3, hy - 3, HEART, (255, 130, 150) if beat else RED, limit=k)
        if HEART_BUILD[1] <= t < SHINE[0]:
            r = 8 + ((t - HEART_BUILD[1]) % 0.7) * 70
            d.ellipse([hx - r, hy - r, hx + r, hy + r], outline=(0, 160, 200))

    # Cerebro que brilla.
    if between(t, BRAIN_GLOW):
        pulse = 0.5 + 0.5 * math.sin((t - BRAIN_GLOW[0]) * 10)
        bx, by = at(t, SPR_BRAIN)
        blit(d, bx - 3, by - 2, BRAIN, tuple(int(a + (255 - a) * pulse * 0.5) for a in (200, 150, 255)))

    # Lupa.
    if between(t, SCIENCE):
        cx, cy = at(t, SPR_HEAD)
        d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], outline=WHITE, width=2)
        d.line([(cx + 16, cy + 16), (cx + 26, cy + 26)], fill=YELLOW, width=3)

    # Explosión de pixeles al perder una parte.
    for tp, p in POPS:
        dt = t - tp
        if 0 <= dt < 1.2:
            ox, oy = at(t, p)
            r = np.random.default_rng(int(tp * 10))
            for vx, vy, c in zip(r.uniform(-40, 40, 22), r.uniform(-60, 5, 22), r.integers(0, 3, 22)):
                px = round(ox + vx * dt)
                py = round(oy + vy * dt + 55 * dt * dt)
                d.rectangle([px, py, px + 1, py + 1], fill=[sprites.PAL["p"], WHITE, MAGENTA][c])

    # Destellos mientras crece y anillo de "level up" al terminar.
    for span, p in ((LEG_GROW, SPR_LEG), (TAIL_GROW, SPR_TAIL)):
        ox, oy = at(t, p)
        if between(t, span):
            for k in range(6):
                ang = t * 4 + k * 2 * math.pi / 6
                if (t * 8 + k) % 2 < 1.4:
                    sparkle(d, round(ox + math.cos(ang) * 14), round(oy + math.sin(ang) * 10), YELLOW)
        dt = t - span[1]
        if 0 <= dt < 0.5:
            r = 4 + dt * 60
            d.ellipse([ox - r, oy - r, ox + r, oy + r], outline=CYAN, width=2)

    # Destellos del brillo y fiesta final.
    if between(t, SHINE):
        for k in range(7):
            if (t * 6 + k) % 2 < 1:
                sx2, sy2 = at(t, (20 + k * 14, 14 + (k % 2) * 30))
                sparkle(d, sx2, sy2, CYAN)
    if t >= PARTY:
        r = np.random.default_rng(7)
        for i, (cx, sp, c) in enumerate(zip(r.integers(x0, x1, 50), r.uniform(15, 35, 50), r.integers(0, 4, 50))):
            cy = y0 + ((t - PARTY) * sp + i * 5) % (y1 - y0)
            d.rectangle([int(cx), round(cy), int(cx) + 1, round(cy) + 1], fill=[MAGENTA, CYAN, LIME, YELLOW][c])

    # Marco (rojo parpadeando en la alerta).
    frame_c = RED if alert and int(t * 3) % 2 == 0 else CYAN
    d.rectangle([x0 - 1, y0 - 1, x1 + 1, y1 + 1], outline=frame_c)
    d.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], outline=tuple(v // 3 for v in frame_c))

    # HUD: vidas a la izquierda, puntaje al centro.
    lives = lives_at(t)
    for i in range(3):
        on = i < lives and not (alert and lives == 1 and i == 0 and int(t * 4) % 2)
        blit(d, 10 + i * 7, HUD_Y + 1, SMALL_HEART, RED if on else (60, 30, 50))
    draw_number(d, LW // 2 + 8, HUD_Y, f"{min(score_at(t), 999999):06d}", YELLOW)
    return img


# ---------------------------------------------------------------- Texto y compuesto final

def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.3 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.5
    m = np.clip(vig, 0.5, 1)[..., None].repeat(3, axis=2)
    return Image.fromarray((m * 255).astype(np.uint8))


class Renderer:
    def __init__(self, duration):
        self.duration = duration
        self.base = make_background()
        self.water = make_water()
        self.vignette = make_vignette()
        self.brand = make_brand_layer()
        self.sub_font = font(FONT_BOLD, 72, 2)
        self.scenes = [(s, e, layout(parse_words(txt), self.sub_font, SUB_Y)) for s, e, txt in SCENES]
        self.tag = glow_text(Image.new("RGB", (W, H)), (W / 2, TAG_Y), "¿SABÍAS QUÉ?", font(FONT_BOLD, 64, 2),
                             WHITE, BRAND_GLOW, radius=16)

    def frame(self, t):
        small = draw_scene(self.base, self.water, t)
        img = small.resize((W, H), Image.NEAREST)
        # Brillo neón suave (sin líneas de pantalla vieja).
        halo = small.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR)
        img = ImageChops.screen(img, ImageChops.multiply(halo, Image.new("RGB", (W, H), (70, 70, 80))))
        img = ImageChops.multiply(img, self.vignette)

        glow, core = Image.new("RGB", (W, H)), Image.new("RGB", (W, H))
        gd, cd = ImageDraw.Draw(glow), ImageDraw.Draw(core)
        for start, end, words in self.scenes:
            if not (start <= t < end + 0.01):
                continue
            fade_out = min(1.0, (end - t) / 0.3)
            for i, (x, y, w, hot) in enumerate(words):
                k = (t - start - i * WORD_DELAY) / WORD_IN
                if k <= 0:
                    continue
                a = ease_out(min(1.0, k)) * fade_out
                dy = 22 * (1 - ease_out(min(1.0, k)))
                cd.text((x, y + dy), w, font=self.sub_font, anchor="lm",
                        fill=tuple(int(c * a) for c in (HIGHLIGHT if hot else WHITE)))
                gd.text((x, y + dy), w, font=self.sub_font, anchor="lm",
                        fill=tuple(int(c * a * 0.9) for c in (COLOR_LEFT if hot else COLOR_RIGHT)))
        halo = glow.resize((W // 3, H // 3), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
        halo = halo.resize((W, H), Image.BILINEAR)
        img = ImageChops.screen(img, ImageChops.add(halo, halo))
        img = ImageChops.lighter(img, core)
        img = ImageChops.screen(img, self.tag)
        img = ImageChops.screen(img, self.brand)

        if t < 0.3:
            img = Image.blend(Image.new("RGB", (W, H)), img, t / 0.3)
        if t > self.duration - 0.5:
            img = Image.blend(Image.new("RGB", (W, H)), img, max(0.0, (self.duration - t) / 0.5))
        return img


# ---------------------------------------------------------------- Audio chiptune

def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def tone(freq, dur, kind="square", duty=0.5, vol=0.2, decay=None, sweep_to=None):
    n = int(dur * SAMPLE_RATE)
    tt = np.arange(n) / SAMPLE_RATE
    f = np.full(n, freq) if sweep_to is None else np.linspace(freq, sweep_to, n)
    phase = np.cumsum(f) / SAMPLE_RATE % 1
    if kind == "square":
        w = np.where(phase < duty, 1.0, -1.0)
    elif kind == "triangle":
        w = 4 * np.abs(phase - 0.5) - 1
    elif kind == "sine":
        w = np.sin(2 * np.pi * phase)
    else:   # ruido
        w = np.random.default_rng(int(freq)).uniform(-1, 1, n)
    env = np.exp(-tt / decay) if decay else np.ones(n)
    env[-min(n, 200):] *= np.linspace(1, 0, min(n, 200))
    return (w * env * vol).astype(np.float32)


def add(buf, t, sig):
    i = int(t * SAMPLE_RATE)
    j = min(len(buf), i + len(sig))
    if i < j:
        buf[i:j] += sig[:j - i]


def render_audio(out_wav, duration):
    buf = np.zeros(int((DURATION + 0.5) * SAMPLE_RATE), dtype=np.float32)
    bpm = 132
    beat = 60 / bpm
    bar = beat * 4
    chords = [(48, 52, 55), (43, 47, 50), (45, 48, 52), (41, 45, 48)]   # Do, Sol, Lam, Fa
    melody = [
        [72, 76, 79, 76], [74, 71, 74, 79], [76, 72, 69, 72], [77, 76, 74, 72],
        [72, 76, 79, 84], [83, 79, 74, 79], [81, 79, 76, 72], [74, 77, 76, 74],
    ]
    for b in range(int(DURATION / bar) + 1):
        t0 = b * bar
        ch = chords[b % 4]
        mv = 0.5 if between(t0, ALERT) else 1.0   # la música baja durante la alerta
        for k in range(8):                   # bajo en corcheas
            n = ch[0] - 12 + (12 if k % 2 else 0)
            add(buf, t0 + k * beat / 2, tone(midi_hz(n), beat / 2 * 0.9, "triangle", vol=0.22 * mv))
        for k in range(8):                   # arpegio
            n = ch[[0, 1, 2, 1][k % 4]] + 24
            add(buf, t0 + k * beat / 2, tone(midi_hz(n), beat / 2 * 0.8, "square", 0.25, 0.035 * mv, decay=0.12))
        if b >= 2:                           # melodía después de 2 compases de intro
            for k, n in enumerate(melody[b % 8]):
                add(buf, t0 + k * beat, tone(midi_hz(n), beat * 0.85, "square", 0.5, 0.05 * mv, decay=0.35))
        for k in range(4):                   # bombo y platillo
            add(buf, t0 + k * beat, tone(150, 0.12, "sine", vol=0.35 * mv, decay=0.05, sweep_to=45))
            add(buf, t0 + k * beat + beat / 2, tone(9000 + k, 0.04, "noise", vol=0.05 * mv, decay=0.012))

    def coin(t):
        add(buf, t, tone(midi_hz(83), 0.07, "square", vol=0.12))
        add(buf, t + 0.07, tone(midi_hz(88), 0.3, "square", vol=0.12, decay=0.1))

    def powerup(t):
        for i in range(14):
            add(buf, t + i * 0.035, tone(midi_hz(60 + i * 2), 0.04, "square", 0.25, 0.1))

    def pop(t):
        add(buf, t, tone(1000, 0.08, "noise", vol=0.25, decay=0.03))
        add(buf, t, tone(900, 0.2, "square", vol=0.15, decay=0.08, sweep_to=150))

    def thump(t):
        for dt in (0, 0.18):
            add(buf, t + dt, tone(55, 0.25, "sine", vol=0.55, decay=0.07))

    for tp, _ in POPS:
        pop(tp)
    for span in (LEG_GROW, TAIL_GROW):
        for k in range(5):
            add(buf, span[0] + k * (span[1] - span[0]) / 5, tone(midi_hz(76 + k * 2), 0.06, "square", vol=0.08))
        powerup(span[1])
    t = HEART_BUILD[0]
    while t < SHINE[0]:
        thump(t)
        t += 0.7
    for k in range(int((HEART_BUILD[1] - HEART_BUILD[0]) / 0.1)):
        add(buf, HEART_BUILD[0] + k * 0.1, tone(midi_hz(84 + k % 5), 0.03, "square", vol=0.05))
    coin(BRAIN_GLOW[0])
    for k in range(8):
        add(buf, SHINE[0] + k * 0.2, tone(midi_hz(96 - k), 0.05, "triangle", vol=0.08))
    for k in range(int((DAYS[1] - DAYS[0]) / 0.6)):
        coin(DAYS[0] + k * 0.6)
    for k in range(int((ALERT[1] - ALERT[0]) / 0.66)):
        add(buf, ALERT[0] + k * 0.66, tone(880 if k % 2 == 0 else 660, 0.15, "square", vol=0.07))
    for k in range(4):
        coin(SCIENCE[0] + k * 1.5)
    powerup(PARTY)
    coin(PARTY + 0.6)

    peak = float(np.abs(buf).max()) or 1.0
    buf *= 0.8 / peak
    end = int(duration * SAMPLE_RATE)
    fade = int(min(1.0, duration / 4) * SAMPLE_RATE)
    buf = buf[:end]
    buf[end - fade:] *= np.linspace(1, 0, fade)
    pcm = (np.clip(np.stack([buf, buf], axis=1), -1, 1) * 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- Main

def main():
    ap = argparse.ArgumentParser(description="Dato curioso del ajolote en pixel art 16-bit.")
    ap.add_argument("--preview", type=float, default=None)
    ap.add_argument("--hasta", type=float, default=None, help="genera solo los primeros N segundos (prueba)")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()
    duration = min(DURATION, args.hasta) if args.hasta else DURATION
    default_out = ROOT / "out" / "pruebas" / "datos" / (OUTPUT.stem + "-prueba.mp4") if args.hasta else OUTPUT
    out = Path(args.salida) if args.salida else default_out

    r = Renderer(duration)
    if args.preview is not None:
        png = out.with_suffix(f".preview-{args.preview:g}s.png")
        r.frame(args.preview).save(png)
        print(png)
        return

    tmp_dir = ROOT / "out" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_out = tmp_dir / out.name
    wav = tmp_out.with_suffix(".wav")
    render_audio(wav, duration)

    n_frames = int(duration * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav), "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(duration), "-movflags", "+faststart",
        str(tmp_out),
    ], stdin=subprocess.PIPE)
    for i in range(n_frames):
        ff.stdin.write(r.frame(i / FPS).tobytes())
        if i % (FPS * 5) == 0:
            print(f"{i / FPS:.0f}s / {duration:.0f}s", flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg falló")
    wav.unlink(missing_ok=True)
    tmp_out.replace(out)
    print(f"Listo: {out}")


if __name__ == "__main__":
    main()
