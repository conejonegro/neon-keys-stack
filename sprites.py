#!/usr/bin/env python3
"""Neon Keys · personajes en pixel art 16-bit, dibujados con código.

Cada personaje es una función que devuelve una imagen RGBA chica (un "sprite") con partes que se pueden
animar (patas, cola, branquias…). Se agranda sin suavizar (NEAREST) para que se vean los pixeles.

Uso:
    .venv/bin/python sprites.py ajolote        # hoja del personaje → out/personajes/ajolote.png
    .venv/bin/python sprites.py podcast        # Alan y Luis → out/personajes/podcast.png
"""

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- Ajolote

SW, SH = 128, 72                 # tamaño del sprite en pixeles
PAL = {
    "outline": (96, 22, 72), "rim": (196, 82, 146),
    "D": (214, 92, 150), "d": (236, 122, 176), "p": (255, 158, 202), "l": (255, 196, 222), "h": (255, 232, 242),
    "fin": (255, 205, 228), "fin_d": (240, 160, 200), "fin_o": (214, 112, 168),
    "eye": (28, 10, 34), "shine": (255, 255, 255), "cheek": (255, 112, 166), "mouth": (120, 26, 78),
    "g0": (176, 34, 132), "g1": (240, 66, 188), "g2": (255, 140, 222), "g_o": (104, 16, 78),
}
LIGHT = np.array([-0.35, -0.75, 0.56])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _shade(u, v):
    """Tono según la normal de un elipsoide en (u, v) ∈ [-1, 1]: devuelve índice 0 (oscuro) … 4 (brillo)."""
    w = np.sqrt(np.clip(1 - u * u - v * v, 0, 1))
    lum = -0.0 + (u * LIGHT[0] + v * LIGHT[1] + w * LIGHT[2])
    return np.digitize(lum, [-0.05, 0.3, 0.62, 0.86])


def _put(rgb, alpha, mask, color):
    rgb[mask] = color
    alpha[mask] = 255


def ajolote(pata=1.0, cola=1.0, fase=0.0, branquias=None):
    """Sprite del ajolote mirando a la derecha.

    pata: 0…1 cuánto de la pata delantera existe (para animar que se pierde y vuelve a crecer).
    cola: 0…1 cuánto de la cola existe.
    fase: fase del nado (radianes): mueve patas, cola y branquias.
    branquias: color RGB para teñir las branquias (ej. cian cuando brillan), o None.
    """
    Y, X = np.mgrid[0:SH, 0:SW] + 0.5
    rgb = np.zeros((SH, SW, 3), np.uint8)
    alpha = np.zeros((SH, SW), np.uint8)
    tones = [PAL[k] for k in ("D", "d", "p", "l", "h")]
    sway = math.sin(fase)

    # --- Branquias del lado de atrás (más oscuras, detrás de todo) ---
    gill_specs = [((82, 22), -100, 25), ((78, 25), -133, 27), ((75, 30), -163, 24)]
    _gills(rgb, alpha, [((bx + 4, by - 2), a + 10, ln - 3) for (bx, by), a, ln in gill_specs], sway, dark=True,
           tint=branquias)

    # --- Branquias de enfrente (también detrás de la cabeza: la cabeza tapa su base) ---
    _gills(rgb, alpha, gill_specs, sway, dark=False, tint=branquias)

    # --- Patas del lado de atrás ---
    for lx in (46, 80):
        _leg(rgb, alpha, lx, 1.0, -sway, dark=True)

    # --- Cola y aleta ---
    tail_x0 = 36 - 28 * cola           # punta de la cola
    wig = sway * 2.0
    if cola > 0:
        span = max(1e-6, 32 - tail_x0)
        k = np.clip((X - tail_x0) / span, 0, 1)
        cy = 38 + wig * (1 - k)
        fin_h = 2 + 11 * k ** 0.7
        fin = (X >= tail_x0) & (X <= 44) & (np.abs(Y - cy) <= fin_h)
        _put(rgb, alpha, fin, PAL["fin"])
        _put(rgb, alpha, fin & (Y > cy + fin_h * 0.5), PAL["fin_d"])
        core_h = 1 + 6 * k ** 0.8
        core = (X >= tail_x0 + 2) & (X <= 38) & (np.abs(Y - cy) <= core_h)
    else:
        fin = np.zeros_like(alpha, bool)
        core = np.zeros_like(alpha, bool)

    # --- Cuerpo + cabeza + cola (una sola figura, sin costura) ---
    head = ((X - 89) / 22) ** 2 + ((Y - 32) / 18) ** 2 <= 1
    body = ((X - 58) / 26) ** 2 + ((Y - 39) / 12.5) ** 2 <= 1
    shape = head | body | core
    tone = np.full((SH, SW), 2)
    tv = np.clip((Y - 38) / 8, -1, 1)
    tone[core] = _shade(np.zeros_like(tv), tv * 0.9)[core]
    tone[body] = _shade((X - 58) / 26, (Y - 39) / 12.5)[body]
    tone[head] = _shade((X - 89) / 22, (Y - 32) / 18)[head]
    for i, c in enumerate(tones):
        _put(rgb, alpha, shape & (tone == i), c)

    # Pecas y pliegue suave del cuello.
    for fx, fy in ((50, 31), (57, 29), (64, 31), (45, 34), (70, 29), (84, 19)):
        if shape[fy, fx]:
            rgb[fy, fx] = PAL["d"]
    for yy in range(41, 47):
        if shape[yy, 71]:
            rgb[yy, 71] = PAL["d"]

    # Contorno de toda la silueta (cuerpo + aleta): oscuro abajo/derecha, más suave arriba/izquierda.
    _outline(rgb, alpha, shape | fin)

    # --- Patas de enfrente (la delantera se puede perder) ---
    _leg(rgb, alpha, 41, 1.0, sway)
    _leg(rgb, alpha, 74, pata, -sway)

    # --- Cara ---
    eye = [".##.", "####", "####", ".##."]
    for j, row in enumerate(eye):
        for i, ch in enumerate(row):
            if ch == "#":
                rgb[26 + j, 96 + i] = PAL["eye"]
    rgb[27, 97] = PAL["shine"]
    rgb[26, 97] = (200, 200, 230)
    for i in range(4):
        rgb[33, 98 + i] = PAL["cheek"]
        rgb[34, 99 + i] = PAL["cheek"]
    smile = [(97, 37), (98, 38), (99, 39), (100, 39), (101, 40), (102, 40), (103, 40), (104, 39), (105, 39),
             (106, 38), (107, 38), (108, 37), (109, 36)]
    for sx, sy in smile:
        rgb[sy, sx] = PAL["mouth"]
    rgb[30, 109] = PAL["D"]

    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


def _erode(m):
    e = m.copy()
    e[1:, :] &= m[:-1, :]
    e[:-1, :] &= m[1:, :]
    e[:, 1:] &= m[:, :-1]
    e[:, :-1] &= m[:, 1:]
    return e


def _outline(rgb, alpha, shape):
    edge = shape & ~_erode(shape)
    below = np.zeros_like(shape)
    below[:-1, :] = ~shape[1:, :]
    right = np.zeros_like(shape)
    right[:, :-1] = ~shape[:, 1:]
    dark = edge & (below | right)
    _put(rgb, alpha, edge & ~dark, PAL["rim"])
    _put(rgb, alpha, dark, PAL["outline"])


def _leg(rgb, alpha, lx, amount, sway, dark=False):
    """Pata corta con 4 deditos; amount 0…1 crece desde el cuerpo."""
    n = int(round(9 * amount))
    if n <= 0:
        return
    off = int(round(sway))
    m = np.zeros(alpha.shape, bool)
    for j in range(n):
        y = 46 + j
        w0, w1 = lx + off * (j > 4), lx + 5 + off * (j > 4)
        m[y, w0:w1] = True
    if n == 9:
        y = 46 + 9
        for t in range(4):
            m[y, lx - 1 + t * 2 + off] = True
            m[y - 1, lx - 1 + t * 2 + off] = True
    base, shade_c, edge_c = (PAL["d"], PAL["D"], PAL["outline"]) if dark else (PAL["p"], PAL["d"], PAL["outline"])
    _put(rgb, alpha, m, base)
    sh = m.copy()
    sh[:, :-2] &= ~m[:, 2:]
    _put(rgb, alpha, m & sh, shade_c)
    e = m & ~_erode(m)
    top = np.zeros_like(m)
    top[46, :] = True
    _put(rgb, alpha, e & ~top, edge_c if not dark else PAL["D"])


def _gills(rgb, alpha, specs, sway, dark, tint):
    """Plumas: tallo de 1 px con plumitas alternadas a los lados y contorno. Se dibujan detrás de la cabeza."""
    cols = [PAL["g0"], PAL["g1"], PAL["g2"]]
    if dark:
        cols = [tuple(int(v * 0.6) for v in c) for c in cols]
    if tint is not None:
        cols = [tuple(int(a * 0.35 + b * 0.65) for a, b in zip(c, tint)) for c in cols]
    paint = {}
    for (bx, by), ang, length in specs:
        a0 = math.radians(ang + sway * 5)
        for s in range(length):
            a = a0 - 0.012 * s
            px = bx + math.cos(a0) * s + math.cos(a) * 0.0
            py = by + math.sin(a0) * s - 0.02 * s * s * math.cos(a0)
            nx, ny = -math.sin(a0), math.cos(a0)
            paint[(round(py), round(px))] = cols[0] if s < 6 else cols[1]
            if s >= 5 and s % 2 == 1:          # plumitas a ambos lados, más largas al centro de la pluma
                reach = 3 if 0.3 < s / length < 0.8 else 2
                for side in (-1, 1):
                    for k in range(1, reach + 1):
                        q = (round(py + ny * side * k - math.sin(a0) * k * 0.5),
                             round(px + nx * side * k - math.cos(a0) * k * 0.5))
                        paint[q] = cols[2] if k == reach else cols[1]
        paint[(round(py), round(px))] = cols[2]
    m = np.zeros(alpha.shape, bool)
    for (iy, ix) in paint:
        if 0 <= iy < SH and 0 <= ix < SW:
            m[iy, ix] = True
    ring = _dilate(m) & ~m & (alpha == 0)
    _put(rgb, alpha, ring, PAL["g_o"] if not dark else tuple(int(v * 0.6) for v in PAL["g_o"]))
    for (iy, ix), c in paint.items():
        if 0 <= iy < SH and 0 <= ix < SW:
            rgb[iy, ix] = c
            alpha[iy, ix] = 255


def _dilate(m):
    d = m.copy()
    d[1:, :] |= m[:-1, :]
    d[:-1, :] |= m[1:, :]
    d[:, 1:] |= m[:, :-1]
    d[:, :-1] |= m[:, 1:]
    return d


# ---------------------------------------------------------------- Podcast: Alan y Luis

PW, PH = 80, 96                  # sprite de medio cuerpo (busto)
CX = 40
EYE_Y, MOUTH_Y = 42, 54
RIM_L, RIM_R = (96, 222, 246), (236, 84, 204)      # luz de borde neón (cian izquierda, magenta derecha)


def _toward(h, target, amount):
    diff = ((target - h + 180.0) % 360.0) - 180.0
    return (h + max(-amount, min(amount, diff))) % 360.0


def _ramp(base, n=5, hue_shift=14.0, dark=0.45, light=0.6):
    """Rampa de sombreado oscuro → claro con cambio de tono (técnica del skill pixel-art-studio):
    las sombras giran hacia azul y los brillos hacia amarillo; la saturación es máxima en el medio."""
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in base))
    hdeg = h * 360
    v0, v1 = max(0.05, v * (1 - dark)), min(1.0, v + (1 - v) * light)
    out = []
    for i in range(n):
        t = i / (n - 1)
        vv = v0 + (v1 - v0) * t
        if t < 0.5:
            hh, ss = _toward(hdeg, 240, (0.5 - t) * 2 * hue_shift), min(1.0, s * (1 + 0.25 * (0.5 - t) * 2))
        else:
            hh, ss = _toward(hdeg, 60, (t - 0.5) * 2 * hue_shift), s * (1 - 0.45 * (t - 0.5) * 2)
        out.append(tuple(round(c * 255) for c in colorsys.hsv_to_rgb(hh / 360, ss, vv)))
    if n % 2:
        out[n // 2] = tuple(base)
    return out


GOLD = _ramp((198, 156, 68), 4, 20, 0.45, 0.65)
ALAN = {
    "skin": _ramp((232, 180, 156), 5, 6, 0.32, 0.5),
    "hair": _ramp((112, 72, 42), 5, 10, 0.55, 0.45),
    "beard": [(56, 32, 24), (88, 54, 34), (120, 80, 50)],
    "head": dict(top=22, mid=43, chin=61, rx=17.5, chin_w=11.5, p=3.0),
}
LUIS = {
    "skin": _ramp((220, 160, 124), 5, 6, 0.34, 0.5),
    "beard": _ramp((40, 36, 46), 5, 22, 0.6, 0.3),
    "head": dict(top=21, mid=41, chin=60, rx=14.5, chin_w=6.5, p=1.7),
}


def _lit(u, v, n):
    """Tono 0…n-1 según la luz sobre una superficie curva (u, v ∈ [-1, 1])."""
    w = np.sqrt(np.clip(1 - u * u - v * v, 0, 1))
    lum = u * LIGHT[0] + v * LIGHT[1] + w * LIGHT[2]
    return np.digitize(lum, {3: [0.2, 0.65], 4: [0.05, 0.42, 0.78], 5: [-0.1, 0.25, 0.55, 0.82]}[n])


def _paint(rgb, alpha, mask, tone, colors):
    tone = np.clip(tone, 0, len(colors) - 1)
    for i, c in enumerate(colors):
        _put(rgb, alpha, mask & (tone == i), c)


def _mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _ellipse(X, Y, cx, cy, rx, ry):
    return ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1


def _cabeza(X, Y, f):
    """Máscara de la cabeza + coordenadas (u, v) que siguen su silueta, para sombrear."""
    top, mid, chin, rx = f["top"], f["mid"], f["chin"], f["rx"]
    dy = Y - mid
    w = np.where(dy <= 0, rx * np.sqrt(np.clip(1 - (dy / (mid - top)) ** 2, 0, 1)),
                 rx - (rx - f["chin_w"]) * np.clip(dy / (chin - mid), 0, 1) ** f["p"])
    w = np.where(Y > chin - 3, w * np.sqrt(np.clip((chin + 0.5 - Y) / 3.5, 0, 1)), w)
    m = (Y >= top) & (Y <= chin + 0.5) & (np.abs(X - CX) <= w)
    u = np.clip((X - CX) / np.maximum(w, 1) * 0.92, -1, 1)
    v = np.clip((Y - (top + chin) / 2) / ((chin - top) / 2), -1, 1) * 0.75
    return m, u, v, w


def _torso(X, Y, ancho, y0=64):
    hw = np.minimum(ancho, 13 + np.sqrt(np.clip(Y - y0 + 2, 0, None)) * 7.5)
    m = (Y >= y0) & (np.abs(X - CX) <= hw)
    tone = _lit(np.clip((X - CX) / (hw + 4), -1, 1), np.clip((Y - 84) / 26, -1, 1), 4)
    return m, tone, hw


def _pix(rgb, alpha, pts, color):
    for x, y in pts:
        if 0 <= x < PW and 0 <= y < PH:
            rgb[y, x] = color
            alpha[y, x] = 255


def _linea(x0, y0, x1, y1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    return {(round(x0 + (x1 - x0) * t / max(1, n - 1)), round(y0 + (y1 - y0) * t / max(1, n - 1))) for t in range(n)}


class _Lienzo:
    """Sprite en construcción. Cada pixel guarda su material (una rampa de colores) y su tono dentro de
    ella: las sombras bajan un escalón de la rampa en vez de mezclar colores, así la paleta queda corta."""

    def __init__(self):
        self.Y, self.X = np.mgrid[0:PH, 0:PW] + 0.5
        self.ix, self.iy = self.X.astype(int), self.Y.astype(int)
        self.mat = np.full((PH, PW), -1)
        self.tone = np.zeros((PH, PW), int)
        self.ramps, self._ids = [], {}

    @property
    def alpha(self):
        return np.where(self.mat >= 0, 255, 0).astype(np.uint8)

    def _id(self, colors):
        key = tuple(tuple(c) for c in colors)
        if key not in self._ids:
            self._ids[key] = len(self.ramps)
            self.ramps.append(key)
        return self._ids[key]

    def paint(self, m, tone, colors):
        i = self._id(colors)
        t = np.clip(np.broadcast_to(tone, m.shape), 0, len(colors) - 1)
        self.mat[m] = i
        self.tone[m] = t[m]

    def put(self, m, c):
        self.paint(m, 0, [c])

    def pix(self, pts, c):
        m = np.zeros((PH, PW), bool)
        for x, y in pts:
            if 0 <= x < PW and 0 <= y < PH:
                m[y, x] = True
        self.put(m, c)

    def shade(self, m, k=-1):
        """Sube o baja k escalones el tono dentro de la rampa de cada pixel (sombra proyectada, brillo)."""
        m = m & (self.mat >= 0)
        top = np.array([len(r) - 1 for r in self.ramps])[self.mat[m]]
        self.tone[m] = np.clip(self.tone[m] + k, 0, top)

    def retint(self, m, colors):
        """Cambia el material conservando el tono (ej. piel → piel con sombra de barba)."""
        m = m & (self.mat >= 0)
        self.mat[m] = self._id(colors)
        self.tone[m] = np.clip(self.tone[m], 0, len(colors) - 1)

    def imagen(self):
        rgb = np.zeros((PH, PW, 3), np.uint8)
        for i, cols in enumerate(self.ramps):
            sel = self.mat == i
            rgb[sel] = np.array(cols, np.uint8)[np.clip(self.tone[sel], 0, len(cols) - 1)]
        return Image.fromarray(np.dstack([rgb, self.alpha]), "RGBA")


def _cara(L, quien, boca, cejas):
    """Orejas, cabeza con volumen, nariz, boca. Devuelve (máscara, tono de piel) para agregar detalles."""
    sk, f = quien["skin"], quien["head"]
    X, Y = L.X, L.Y
    # Orejas (detrás de la cabeza).
    for side in (-1, 1):
        ex = CX + side * (f["rx"] + 0.3)
        m = _ellipse(X, Y, ex, EYE_Y + 1.5, 2.6, 4.6)
        L.paint(m, _lit((X - ex) / 2.6 * 0.6 + side * 0.2, (Y - EYE_Y - 1.5) / 4.6, 5) - 1, sk)
        L.put(m & _ellipse(X, Y, ex + side * 0.3, EYE_Y + 1.8, 1.0, 2.6), sk[0])
    head, u, v, w = _cabeza(X, Y, f)
    tone = _lit(u, v, 5)
    # Cuencas de los ojos y sombra bajo las cejas.
    for side in (-1, 1):
        tone = np.where(_ellipse(X, Y, CX + side * 6.5, EYE_Y - 0.5, 5, 2.6), tone - 1, tone)
    # Nariz: puente con luz, lado derecho en sombra, punta redonda, sombra proyectada.
    nose_tip = _ellipse(X, Y, CX, 48.5, 2.6, 1.8)
    tone = np.where((np.abs(X - (CX - 0.5)) < 0.6) & (Y > 42) & (Y < 47), tone + 1, tone)
    tone = np.where((X > CX + 0.6) & (X < CX + 2.6) & (Y > 43) & (Y < 48), tone - 1, tone)
    tone = np.where(nose_tip, _lit((X - CX) / 2.6, (Y - 48.5) / 1.8, 5), tone)
    tone = np.where((Y > 50) & (Y < 51.2) & (np.abs(X - CX - 0.5) < 2.5), tone - 1, tone)
    # Mejillas con luz, sombra bajo el labio y la barbilla.
    tone = np.where(_ellipse(X, Y, CX - 8, 48, 3, 2), tone + 1, tone)
    tone = np.where((Y > MOUTH_Y + 2) & (Y < MOUTH_Y + 3) & (np.abs(X - CX) < 3), tone - 1, tone)
    below = np.zeros_like(head)
    below[:-1, :] = ~head[1:, :]
    tone = np.where(below & (Y > 50), tone - 1, tone)
    tone = np.clip(tone, 0, 4)
    L.paint(head, tone, sk)
    L.pix([(CX - 2, 49), (CX + 2, 49)], sk[0])
    L.pix([(CX - 1, 47)], sk[4])
    return head, tone, w


def _boca(L, boca, y, sk, sonrisa=False):
    """boca 0 = cerrada, 1 = hablando, 2 = gritando ¡gol!"""
    lip, lip_l, dark, teeth, tongue = (150, 70, 70), (206, 120, 112), (52, 14, 22), (240, 234, 224), (206, 78, 88)
    if boca == 0:
        L.pix([(x, y) for x in range(CX - 3, CX + 4)], lip)
        if sonrisa:
            L.pix([(CX - 4, y - 1), (CX + 4, y - 1)], lip)
        L.pix([(x, y + 1) for x in range(CX - 2, CX + 3)], lip_l)
    elif boca == 1:
        L.pix([(x, yy) for x in range(CX - 3, CX + 4) for yy in (y, y + 1)], dark)
        L.pix([(x, y) for x in range(CX - 2, CX + 3)], teeth)
        L.pix([(x, y + 2) for x in range(CX - 2, CX + 3)], lip_l)
        if sonrisa:
            L.pix([(CX - 4, y - 1), (CX + 4, y - 1)], lip)
    else:
        L.pix([(x, yy) for x in range(CX - 4, CX + 5) for yy in range(y - 1, y + 4)
               if not (abs(x - CX) == 4 and yy in (y - 1, y + 3))], dark)
        L.pix([(x, y - 1) for x in range(CX - 3, CX + 4)], teeth)
        L.pix([(x, yy) for x in range(CX - 2, CX + 3) for yy in (y + 2, y + 3)], tongue)
        L.pix([(x, y + 4) for x in range(CX - 2, CX + 3)], lip_l)


def _contorno_neon(L):
    """Contorno "selout": el tono más oscuro de cada material (un escalón más claro en el borde de arriba,
    que recibe la luz) + luz de borde neón de color fijo: cian a la izquierda, magenta a la derecha."""
    shape = L.mat >= 0
    edge = shape & ~_erode(shape)
    edge[-1, :] = False                     # el corte de abajo del busto no lleva contorno
    arriba = np.zeros_like(shape)
    arriba[1:, :] = ~shape[:-1, :]
    arriba[0, :] = True
    L.shade(edge, -9)
    L.shade(edge & arriba, 1)
    inner = shape & ~edge
    for color, sh in ((RIM_L, 1), (RIM_R, -1)):
        side = np.zeros_like(shape)
        if sh == 1:
            side[:, 1:] = edge[:, :-1]
        else:
            side[:, :-1] = edge[:, 1:]
        L.put(inner & side & (L.Y > 18), color)


def alan(boca=0, cejas=0):
    """Alan: piel clara, pelo café alborotado, cara redonda, lentes de aviador naranjas, playera de México."""
    L = _Lienzo()
    X, Y, ix, iy = L.X, L.Y, L.ix, L.iy
    sk, hr, bd = ALAN["skin"], ALAN["hair"], ALAN["beard"]

    # --- Cuello ancho con papada y tatuaje ---
    neck = (np.abs(X - CX) <= 10) & (Y >= 50) & (Y < 76)
    L.paint(neck, np.where(Y < 64, 0, 1), sk)
    papada = _ellipse(X, Y, CX, 61.5, 10, 3.6)
    L.paint(papada, _lit((X - CX) / 10, (Y - 61.5) / 3.6, 5) - 1, sk)
    L.pix([(CX - 1, 67), (CX + 1, 67), (CX, 68), (CX - 2, 69), (CX, 69), (CX + 2, 69), (CX, 70), (CX - 1, 71),
           (CX + 1, 71)], (84, 92, 96))

    # --- Playera verde de México ---
    torso, tone, hw = _torso(X, Y, 38, y0=66)
    vneck = (Y < 80) & (np.abs(X - CX) <= (80 - Y) * 0.55)
    jersey = torso & ~vneck
    g = [(10, 62, 40), (16, 96, 58), (26, 130, 78), (50, 162, 98)]
    r = np.hypot(X - CX, (Y - 104) * 1.1)
    ang = np.arctan2(Y - 104, X - CX)
    patron = ((np.abs(r - 16) < 0.6) | (np.abs(r - 25) < 0.6) | (np.abs(r - 33) < 0.6)
              | ((r > 17) & (r < 24) & (np.floor(ang * 10) % 2 == 0)))
    tone = np.where(patron & (tone > 0), tone - 1, tone)
    pliegue = (np.abs((X - CX) - (Y - 70) * 0.5 - 22) < 0.7) | (np.abs((X - CX) + (Y - 70) * 0.5 + 22) < 0.7)
    tone = np.where(pliegue & (Y > 78), 0, tone)
    tone = np.where(_ellipse(X, Y, CX, 68, 14, 4), np.minimum(tone, 1), tone)    # sombra bajo la cabeza
    L.paint(jersey, tone, g)
    rings = [jersey]
    for _ in range(6):
        rings.append(_erode(rings[-1]))
    hombro = (Y <= 82) & (np.abs(X - CX) >= 15) & (Y > 66)
    for k in (1, 3, 5):
        L.put(rings[k] & ~rings[k + 1] & hombro, (236, 238, 232))
        L.put(rings[k] & ~rings[k + 1] & hombro & (X > CX + 22), (196, 200, 200))
    v1 = _dilate(vneck) & jersey
    v2 = _dilate(v1) & jersey & ~v1
    v3 = _dilate(v1 | v2) & jersey & ~v1 & ~v2
    L.put(v1 | v2 | (jersey & (Y < 70) & (np.abs(X - CX) <= 13)), (200, 34, 46))
    L.put(v2 & (X > CX), (150, 22, 34))
    L.put(v3 & (Y < 82), (238, 238, 232))
    L.put(vneck & torso, sk[1])
    L.put(vneck & torso & (Y < 72), sk[0])
    L.pix([(CX - 19, 87), (CX - 18, 87), (CX - 17, 86), (CX - 16, 86), (CX - 17, 87), (CX - 16, 87),
           (CX - 15, 85), (CX - 14, 85), (CX - 15, 86), (CX - 14, 86), (CX - 15, 87), (CX - 14, 87)], (240, 240, 236))
    L.paint(_ellipse(X, Y, CX + 16, 86, 1.8, 2.3), _lit((X - CX - 16) / 1.8, (Y - 86) / 2.3, 3), GOLD[:3])
    # Cadena con medalla.
    L.pix(_linea(CX - 9, 66, CX, 84) | _linea(CX + 9, 66, CX, 84), GOLD[1])
    L.pix([(CX - 8, 67), (CX - 6, 71), (CX - 4, 75)], GOLD[3])
    med = _ellipse(X, Y, CX, 87, 3.2, 3.2)
    L.paint(med, _lit((X - CX) / 3.2, (Y - 87) / 3.2, 4), GOLD)
    L.put(med & ~_erode(med) & (X > CX), GOLD[0])

    # --- Cara redonda ---
    head, stone, w = _cara(L, ALAN, boca, cejas)
    L.put(head & _ellipse(X, Y, CX - 9.5, 49, 2.5, 1.5), (240, 168, 150))      # chapeteado
    L.put(head & _ellipse(X, Y, CX + 9.5, 49, 2.5, 1.5), (226, 150, 134))
    # Barba de candado café + sombra de barba en la quijada.
    sombra = head & (Y >= 50) & (np.abs(X - CX) >= w - 3.5)
    L.retint(sombra, [_mix(c, bd[1], 0.3) for c in sk])
    # Candado: bigote + anillo alrededor de la boca + barbilla redonda.
    anillo = _ellipse(X, Y, CX, MOUTH_Y + 1.5, 6.5, 6.2) & ~_ellipse(X, Y, CX, MOUTH_Y + 0.8, 4.3, 2.2 + boca * 0.7)
    candado = head & anillo & (Y >= 51)
    L.paint(candado, _lit((X - CX) / 6.5, (Y - MOUTH_Y - 1.5) / 6.2, 3), bd)
    L.put(candado & ~_erode(candado) & (Y > MOUTH_Y + 3), bd[0])
    L.put(head & _ellipse(X, Y, CX, MOUTH_Y + 0.8, 4.3, 2.2 + boca * 0.7) & (Y > MOUTH_Y + 1.5), sk[2])
    _boca(L, boca, MOUTH_Y, sk)

    # --- Pelo café lacio: masa con raya de lado, fleco en puntas y mechones que salen de la coronilla ---
    tips = 2.6 * (1 - np.abs(((X - CX) % 4) - 2) / 2)               # puntas del fleco
    fleco_y = 30.5 + tips + np.clip(X - CX, 0, None) * 0.12            # más largo del lado derecho
    masa = _ellipse(X, Y, CX - 1, 30, 19.5, 12.5)
    hair = masa & ((Y < fleco_y) | ((np.abs(X - CX) >= 14.2) & (Y < 45 - np.abs(X - CX) * 0.05)))
    ht = _lit((X - CX + 1) / 20, (Y - 27) / 14, 5)
    corona = (CX - 6, 13)
    theta = np.arctan2(X - corona[0], Y - corona[1])
    hebra = np.floor(theta * 16) % 3 == 0
    ht = np.where(hebra, ht - 1, ht)
    brillo = (np.abs(np.hypot((X - corona[0]) / 1.3, Y - corona[1]) - 10.5) < 1.0) & ~hebra
    ht = np.where(brillo, ht + 1, ht)
    L.paint(hair, np.clip(ht, 0, 4), hr)
    # Sombra que el pelo proyecta sobre la frente.
    hair = (L.alpha > 0) & ~head & (Y < 40)
    hm = np.zeros_like(hair)
    hm[1:, :] = hair[:-1, :]
    hm[2:, :] |= hair[:-2, :]
    sh = head & hm & ~hair & (Y < 37)
    L.shade(sh, -1)

    # --- Cejas y lentes de aviador ---
    cy = EYE_Y - 5 - cejas
    for side in (-1, 1):
        L.pix([(CX + side * k, cy + (1 if k > 8 else 0)) for k in range(3, 11)], hr[1])
        L.pix([(CX + side * k, cy - 1) for k in range(4, 9)], hr[0])
    for side in (-1, 1):
        lx = CX + side * 7
        lens = _ellipse(X, Y, lx + side * 0.4, EYE_Y + 0.6, 6, 4.8) & (Y >= EYE_Y - 3.2)
        sombra_l = np.zeros_like(lens)
        sombra_l[2:, 1:] = lens[:-2, :-1]
        L.shade(sombra_l & head & ~lens, -1)
        frame = _dilate(lens) & ~lens
        L.put(frame, GOLD[1])
        L.put(frame & (Y < EYE_Y - 2.5), GOLD[2])
        grad = np.clip(((Y - (EYE_Y - 3)) / 9 * 4).astype(int), 0, 3)
        L.paint(lens, grad, [(200, 70, 50), (232, 112, 58), (248, 150, 70), (252, 190, 96)])
        L.put(lens & _ellipse(X, Y, lx + 0.5, EYE_Y + 0.5, 2, 1.3), (196, 96, 54))     # ojo detrás del lente
        L.pix([(lx - 4, EYE_Y - 1), (lx - 3, EYE_Y - 2), (lx - 2, EYE_Y - 3)], (255, 236, 200))    # reflejo
    L.pix([(x, EYE_Y - 3) for x in range(CX - 2, CX + 3)], GOLD[2])
    L.pix([(x, EYE_Y - 2) for x in range(CX - 1, CX + 2)], GOLD[0])

    _contorno_neon(L)
    return L.imagen()


def luis(boca=0, ojos=1, cejas=0):
    """Luis: calvo, barba larga, lentes redondos, poncho de sarape con camisa de cuadros roja."""
    L = _Lienzo()
    X, Y, ix, iy = L.X, L.Y, L.ix, L.iy
    sk, bd = LUIS["skin"], LUIS["beard"]

    # --- Cuello ---
    L.paint((np.abs(X - CX) <= 7.5) & (Y >= 50) & (Y < 74), np.zeros((PH, PW), int), sk)

    # --- Poncho de sarape con volumen ---
    torso, tone, hw = _torso(X, Y, 36, y0=66)
    tone = np.where(_ellipse(X, Y, CX, 70, 16, 6), np.minimum(tone, 1), tone)          # sombra de la barba
    navy = _ramp((30, 32, 56), 4, 14, 0.5, 0.12)
    L.paint(torso, tone, navy)
    yb = Y - 0.003 * (X - CX) ** 2
    franjas = [(82, (52, 178, 96)), (83, (128, 206, 70)), (84, (244, 206, 52)), (85, (248, 140, 44)),
               (86, (226, 56, 64)), (88, (236, 234, 222)), (90, (64, 140, 226)), (91, (54, 200, 214)),
               (92, (64, 140, 226)), (94, (236, 234, 222))]
    for y0, col in franjas:
        m = torso & (yb >= y0) & (yb < y0 + 1)
        L.paint(m, np.array([0, 1, 1, 2])[np.clip(tone, 0, 3)], _ramp(col, 3, 16, 0.4, 0.3))
    zz = torso & (np.floor(yb) == 88) & ((ix // 2) % 3 == 0)
    L.paint(zz, tone, navy)
    # Cuello de camisa de cuadros roja.
    collar = (Y >= 63) & (Y < 72) & (np.abs(X - CX) <= 12) & ~((np.abs(X - CX) <= (72 - Y) * 0.7) & (Y >= 65))
    cuadro = ((ix % 4 < 2) ^ (iy % 4 < 2)).astype(int) + ((ix % 4 == 0) & (iy % 4 == 0)) - (X > CX + 4)
    L.paint(collar, np.clip(1 - cuadro, 0, 2) + (Y > 69), [(196, 48, 50), (150, 32, 38), (96, 18, 26), (40, 12, 18)])

    # --- Cabeza calva ---
    head, stone, w = _cara(L, LUIS, boca, 0)
    L.paint(_ellipse(X, Y, CX - 5, 26, 3.5, 2.2), _lit((X - CX + 5) / 3.5, (Y - 26) / 2.2, 5) * 0 + 4, sk)
    L.pix([(CX - 6, 25), (CX - 5, 25), (CX - 7, 26)], (255, 240, 226))                 # brillo de la calva

    # --- Barba larga negra, cuadrada abajo, que nace de la cara ---
    hw_b = 12.2 - np.clip(Y - 52, 0, None) * 0.05 - np.clip(Y - 73, 0, None) ** 2 * 0.45
    larga = (Y >= 50) & (Y <= 77) & (np.abs(X - CX) <= hw_b)
    cara = head & (Y >= 45 + 6 * np.clip(1 - np.abs(X - CX) / 11, 0, 1))
    patilla = head & (np.abs(X - CX) >= w - 2.5) & (Y >= 38)
    barba = larga | cara | patilla
    labios = (Y >= MOUTH_Y) & (Y < MOUTH_Y + 2 + boca * 1.5) & (np.abs(X - CX) <= 3.5 + boca * 0.5)
    barba &= ~labios
    bw = np.where(Y < 52, np.maximum(w, 1), np.maximum(hw_b, 1))
    bt = _lit(np.clip((X - CX) / bw, -1, 1) * 0.85, np.clip((Y - 62) / 17, -1, 1) * 0.9, 5)
    bt = np.where((ix % 3 == 0) & (Y > 57) & (bt >= 2), bt - 1, bt)          # mechones rectos
    bt = np.where((Y > 75) & (bt > 1), bt - 1, bt)                           # sombra en el borde de abajo
    L.paint(barba, np.clip(bt, 0, 4), bd)
    # Transición suave piel → barba en las mejillas (vello corto), para que no se vea encimada.
    borde = head & ~barba & _dilate(_dilate(barba)) & (Y < MOUTH_Y) & ~labios
    L.retint(borde, [_mix(c, bd[2], 0.4) for c in sk])
    L.put(head & labios, sk[1])
    # Bigote.
    bigote = (Y >= 49.8) & (Y < 53.2) & (np.abs(X - CX) <= 7 - np.clip(Y - 51, 0, None) * 0.8) & \
             ~((np.abs(X - CX) < 1) & (Y < 51))
    L.paint(bigote, _lit((X - CX) / 7, (Y - 51) / 2.5, 5), bd)
    L.pix([(x, 54) for x in (CX - 5, CX - 4, CX + 4, CX + 5)], bd[1])
    _boca(L, boca, MOUTH_Y, sk, sonrisa=True)
    L.pix([(CX - 2, 49), (CX + 2, 49)], sk[0])

    # --- Ojos, cejas y lentes redondos ---
    cy = EYE_Y - 5 - cejas
    for side in (-1, 1):
        L.pix([(CX + side * k, cy + (1 if k > 9 else 0)) for k in range(3, 11)], bd[1])
        L.pix([(CX + side * k, cy - 1) for k in range(4, 9)], bd[0])
    for side in (-1, 1):
        ex = CX + side * 7
        if ojos:
            L.pix([(x, EYE_Y - 1) for x in range(ex - 2, ex + 3)], sk[0])
            L.pix([(ex - 2, EYE_Y), (ex + 2, EYE_Y), (ex - 1, EYE_Y + 1), (ex + 2, EYE_Y + 1)], (236, 230, 226))
            L.pix([(ex - 1, EYE_Y), (ex, EYE_Y), (ex + 1, EYE_Y), (ex, EYE_Y + 1), (ex + 1, EYE_Y + 1)],
                  (70, 44, 28))
            L.pix([(ex, EYE_Y), (ex, EYE_Y + 1)], (24, 14, 12))
            L.pix([(ex - 1, EYE_Y)], (250, 250, 255))
        else:
            L.pix([(x, EYE_Y + 1) for x in range(ex - 2, ex + 3)], sk[0])
        d = np.hypot(X - ex, Y - (EYE_Y + 0.5))
        aro = (d >= 4.6) & (d < 5.6)
        sombra_g = np.zeros_like(aro)
        sombra_g[2:, 1:] = aro[:-2, :-1]
        L.shade(sombra_g & head & ~aro, -1)
        L.put(aro, (84, 74, 90))
        L.put(aro & (Y < EYE_Y - 1) & (X < ex + 1), (200, 190, 206))
        L.pix([(ex - 3, EYE_Y - 1), (ex - 2, EYE_Y - 2)], (226, 240, 255))
    L.pix([(x, EYE_Y - 2) for x in range(CX - 2, CX + 3)], (84, 74, 90))
    L.pix([(CX - 13, EYE_Y - 1), (CX - 14, EYE_Y - 1), (CX + 13, EYE_Y - 1), (CX + 14, EYE_Y - 1)], (84, 74, 90))

    _contorno_neon(L)
    return L.imagen()


def hoja_podcast(path):
    """Imagen para aprobar a Alan y Luis: grandes arriba + gestos chicos abajo."""
    from neon_keys import COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, FONT_TEXT, font, glow_text
    Wd, Hd = 1080, 1350
    img = Image.new("RGB", (Wd, Hd), (10, 5, 26))
    d = ImageDraw.Draw(img)
    for x in range(0, Wd, 60):
        d.line([(x, 0), (x, Hd)], fill=(26, 14, 52))
    for y in range(0, Hd, 60):
        d.line([(0, y), (Wd, y)], fill=(26, 14, 52))
    img = glow_text(img, (Wd / 2, 70), "ALAN  Y  LUIS", font(FONT_BOLD, 70, 2), (255, 255, 255), COLOR_LEFT, radius=16)
    img = glow_text(img, (Wd / 2, 135), "personajes 16-bit · podcast de fútbol · propuesta", font(FONT_TEXT, 30, 0),
                    (220, 210, 255), COLOR_RIGHT, radius=8)
    sc = 5
    for cx, spr, name, col in ((270, alan(), "ALAN", COLOR_RIGHT), (810, luis(), "LUIS", COLOR_LEFT)):
        big = spr.resize((PW * sc, PH * sc), Image.NEAREST)
        img.paste(big, (cx - big.width // 2, 175), big)
        img = glow_text(img, (cx, 690), name, font(FONT_BOLD, 50, 2), (255, 255, 255), col, radius=12)
    d = ImageDraw.Draw(img)
    filas = [[("cerrada", alan()), ("hablando", alan(boca=1)), ("¡gol!", alan(boca=2, cejas=1)),
              ("cejas arriba", alan(cejas=1))],
             [("cerrada", luis()), ("hablando", luis(boca=1)), ("¡gol!", luis(boca=2, cejas=1)),
              ("parpadeo", luis(ojos=0))]]
    sc = 2
    for r, poses in enumerate(filas):
        for i, (label, spr) in enumerate(poses):
            s = spr.resize((PW * sc, PH * sc), Image.NEAREST)
            cx, cy = 135 + i * 270, 840 + r * 260
            img.paste(s, (cx - s.width // 2, cy - s.height // 2), s)
            d.text((cx, cy + s.height // 2 + 18), label, font=font(FONT_TEXT, 26, 0), fill=(180, 170, 220),
                   anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


# ---------------------------------------------------------------- Hoja del personaje

def hoja_ajolote(path):
    """Imagen para aprobar el diseño: grande al centro + poses chicas abajo."""
    from neon_keys import BRAND_GLOW, COLOR_RIGHT, FONT_BOLD, FONT_TEXT, font, glow_text
    Wd, Hd = 1080, 1350
    img = Image.new("RGB", (Wd, Hd), (10, 5, 26))
    d = ImageDraw.Draw(img)
    for x in range(0, Wd, 60):
        d.line([(x, 0), (x, Hd)], fill=(26, 14, 52))
    for y in range(0, Hd, 60):
        d.line([(0, y), (Wd, y)], fill=(26, 14, 52))
    img = glow_text(img, (Wd / 2, 90), "AJOLOTE", font(FONT_BOLD, 76, 2), (255, 255, 255), BRAND_GLOW, radius=16)
    img = glow_text(img, (Wd / 2, 160), "personaje 16-bit · propuesta", font(FONT_TEXT, 34, 0), (220, 210, 255),
                    COLOR_RIGHT, radius=8)
    big = ajolote(fase=0.6).resize((SW * 8, SH * 8), Image.NEAREST)
    img.paste(big, ((Wd - big.width) // 2, 230), big)
    d = ImageDraw.Draw(img)
    poses = [("nadando", ajolote(fase=2.4)), ("sin pata", ajolote(pata=0.0, fase=0.6)),
             ("sin cola", ajolote(cola=0.0, fase=0.6)), ("branquias brillando", ajolote(fase=0.6, branquias=(0, 240, 255)))]
    sc = 2
    cell = Wd // 2
    for i, (label, spr) in enumerate(poses):
        s = spr.resize((SW * sc * 1, SH * sc * 1), Image.NEAREST)
        cx = cell * (i % 2) + cell // 2
        cy = 900 + (i // 2) * 210
        img.paste(s, (cx - s.width // 2, cy - s.height // 2), s)
        d.text((cx, cy + s.height // 2 + 20), label, font=font(FONT_TEXT, 28, 0), fill=(180, 170, 220), anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description="Personajes pixel art de Neon Keys.")
    ap.add_argument("personaje", choices=["ajolote", "podcast"])
    args = ap.parse_args()
    out = ROOT / "out" / "personajes" / f"{args.personaje}.png"
    print({"ajolote": hoja_ajolote, "podcast": hoja_podcast}[args.personaje](out))


if __name__ == "__main__":
    main()
