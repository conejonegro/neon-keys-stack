#!/usr/bin/env python3
"""Neon Keys · podcast de fútbol en pixel art: Alan y Luis caminan de lado (estilo Metal Slug) y platican
con globos de texto.

Los personajes son las tiras de caminata hechas con IA y limpiadas con `pixel_ia.py`
(`out/personajes/*-caminar.png`). El escenario synthwave, los globos, la boca al hablar y la música chiptune
se hacen con código. La voz se pone después en TikTok, como en los datos curiosos.

Uso:
    .venv/bin/python podcast.py                 # → out/pruebas/podcast/podcast-chivas-monterrey.mp4
    .venv/bin/python podcast.py --preview 4     # solo un cuadro PNG en t=4 s
"""

import argparse
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from ajolote import add, midi_hz, tone
from neon_keys import (COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, FONT_TEXT, FPS, H, SAMPLE_RATE, TITLE_GLOW, W, font,
                       glow_text, make_brand_layer)

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "out" / "pruebas" / "podcast" / "podcast-chivas-monterrey.mp4"

PX = 6                          # cada pixel del escenario mide 6×6 en el video
SW, SH = W // PX, H // PX       # 180 × 320
HORIZON = 176                   # línea del horizonte (pixeles chicos)
SUELO = 262                     # línea de los pies (y ≈ 1572 en el video, arriba de la zona de botones)
PASO = 0.11                     # segundos por cuadro de la caminata
VEL_SUELO = 13.0                # avance de la cuadrícula del piso (unidades de mundo por segundo)
VEL_CIUDAD = 6.0                # avance de la ciudad a lo lejos (pixeles chicos por segundo)

TITULO, SUBTITULO = "CHIVAS 1-0 MTY", "¿ALMEIDA TRAIDOR?"
WHITE = (255, 255, 255)
INK = (24, 10, 44)

# tira: caminata limpia · x: dónde va en el escenario · boca: (x, y, ancho) de la boca en el cuadro cuando
# la cabeza está en su punto más alto (fila 2) · fase: para que no pisen al mismo tiempo
PERSONAJES = {
    "alan": dict(nombre="ALAN", tira="out/personajes/alan-caminar.png", x=22, boca=(35, 25, 4), fase=3,
                 color=COLOR_RIGHT, tinta=(0, 120, 150)),
    "luis": dict(nombre="LUIS", tira="out/personajes/luis-caminar.png", x=100, boca=(33, 22, 5), fase=0,
                 color=COLOR_LEFT, tinta=(190, 20, 150)),
}

# (quién, texto del globo, voz). La voz es un audio (wav/mp3) por frase; si falta el archivo
# esa línea sale solo con texto. Los tiempos salen de la duración de cada voz.
DIALOGO = [
    ("luis", "¡Ganamos uno a cero en Monterrey, wey, y aun así ando bien encabronado!",
     "out/pruebas/voces/chivas-monterrey-luis-1.wav"),
    ("alan", "¿Encabronado por qué, cabrón? ¡El Piojo la metió luego luego!",
     "out/pruebas/voces/chivas-monterrey-alan-2.wav"),
    ("luis", "¡Por Almeida, wey! ¡Todo el estadio aplaudiéndole como si fuera santo!",
     "out/pruebas/voces/chivas-monterrey-luis-3.wav"),
    ("alan", "¡Ah no, pero el Toro Guzmán nos regaló el gol! ¡Ese wey juega para nosotros!",
     "out/pruebas/voces/chivas-monterrey-alan-4.wav"),
    ("luis", "Y luego el penal. Yo ya estaba rezando, wey, te lo juro.",
     "out/pruebas/voces/chivas-monterrey-luis-5.wav"),
    ("alan", "¡Pero lo tiró Campos! ¡Segundo penal fallado seguido! ¡Hasta su afición le gritaba \"tíralo normal, pendejo\"!",
     "out/pruebas/voces/chivas-monterrey-alan-6.wav"),
    ("luis", "Ese cabrón cobra penales como si estuviera en el Mundial de Fortnite.",
     "out/pruebas/voces/chivas-monterrey-luis-7.wav"),
    ("alan", "¡Y el Rossy le dio una patada al abanderado y todavía se tiró, wey! ¡Qué descaro!",
     "out/pruebas/voces/chivas-monterrey-alan-8.wav"),
    ("luis", "Eso no es fútbol, es telenovela de las nueve.",
     "out/pruebas/voces/chivas-monterrey-luis-9.wav"),
    ("alan", "¡Y se soltó el diluvio! ¡Yo pensé que eran mis lágrimas!",
     "out/pruebas/voces/chivas-monterrey-alan-10.wav"),
    ("luis", "Luego Orbelín se va expulsado al 89. ¡Ahí sí se me bajó la presión, cabrón!",
     "out/pruebas/voces/chivas-monterrey-luis-11.wav"),
    ("alan", "¡Y al 95 el pinche Rossy mete el empate! ¡Yo ya iba a romper la tele!",
     "out/pruebas/voces/chivas-monterrey-alan-12.wav"),
    ("luis", "Y entonces… ¡el VAR! ¡Mano clarísima! ¡Anulado, hijos de su madre!",
     "out/pruebas/voces/chivas-monterrey-luis-13.wav"),
    ("alan", "¡Pero lo peor fue Almeida, wey! ¡Festejó el gol como loco! ¡Contra nosotros!",
     "out/pruebas/voces/chivas-monterrey-alan-14.wav"),
    ("luis", "¡Nos juró amor eterno y lo festeja en nuestra cara! ¡Traidor de mierda!",
     "out/pruebas/voces/chivas-monterrey-luis-15.wav"),
    ("alan", "¡Y luego se hizo expulsar para no dar la conferencia! ¡Puro teatro, cabrón!",
     "out/pruebas/voces/chivas-monterrey-alan-16.wav"),
    ("luis", "Y la prensa regia diciendo que nos regaló el partido. ¡Lloren, pinches llorones!",
     "out/pruebas/voces/chivas-monterrey-luis-17.wav"),
    ("alan", "¡Tercer lugar, empatados con Cruz Azul! ¡Vamos por todo, chingada madre!",
     "out/pruebas/voces/chivas-monterrey-alan-18.wav"),
    ("luis", "Almeida, te perdono… pero nomás si te eliminamos en la liguilla.",
     "out/pruebas/voces/chivas-monterrey-luis-19.wav"),
]
SILBATO_ANTES = 12               # el silbatazo suena justo antes de esta línea (la del VAR)
INICIO, PAUSA, PAUSA_SILBATO, FINAL = 0.5, 0.35, 0.9, 1.2
LETRAS_POR_SEG = 22             # para las líneas sin voz
GLOBO_Y = 432                   # parte de arriba del globo (debajo del título)


def leer_voz(path):
    """Voz como arreglo mono a SAMPLE_RATE, sin silencios en las orillas y normalizada; None si no existe."""
    p = ROOT / path if path else None
    if not p or not p.exists():
        return None
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE),
                          "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).copy()
    sonido = np.where(np.abs(a) > 0.02)[0]
    if len(sonido):
        a = a[max(0, sonido[0] - int(0.04 * SAMPLE_RATE)):sonido[-1] + int(0.12 * SAMPLE_RATE)]
    return a * (0.9 / (np.abs(a).max() or 1))


def armar_lineas():
    """Línea de tiempo del diálogo: cuándo empieza y termina cada línea, su voz y su volumen cuadro por cuadro
    (para mover la boca al ritmo de la voz)."""
    lineas, t = [], INICIO
    for i, (quien, texto, voz) in enumerate(DIALOGO):
        if i == SILBATO_ANTES:
            t += PAUSA_SILBATO - PAUSA
        a = leer_voz(voz)
        if a is None:
            dur, env = len(texto) / LETRAS_POR_SEG + 1.2, None
        else:
            dur = len(a) / SAMPLE_RATE
            hop = SAMPLE_RATE // FPS
            n = len(a) // hop
            env = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1))
            env /= env.max() or 1
        cps = LETRAS_POR_SEG if a is None else len(texto) / (dur * 0.8)     # el texto acaba antes que la voz
        lineas.append(dict(t0=t, t1=t + dur, quien=quien, texto=texto, voz=a, env=env, cps=cps))
        t += dur + PAUSA
    return lineas


LINEAS = armar_lineas()
DURATION = round(LINEAS[-1]["t1"] + FINAL, 2)
SILBATAZO = LINEAS[SILBATO_ANTES]["t0"] - 0.75


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


# ---------------------------------------------------------------- Personajes

def cargar_tira(path, n=6):
    tira = Image.open(ROOT / path).convert("RGBA")
    w = tira.width // n
    cuadros = [tira.crop((i * w, 0, (i + 1) * w, tira.height)) for i in range(n)]
    tops = [int(np.where((np.array(c)[..., 3] > 0).any(1))[0][0]) for c in cuadros]
    return cuadros, tops


def con_boca(cuadro, top, boca, abierta):
    """Abre la boca de perfil: un hueco oscuro bajo el bigote (la cabeza sube y baja al caminar)."""
    if not abierta:
        return cuadro
    c = cuadro.copy()
    d = ImageDraw.Draw(c)
    x, y, ancho = boca
    y += top - 2
    d.rectangle([x, y, x + ancho - 1, y + 1], fill=(44, 10, 18))
    d.point([(x + 1, y)], fill=(236, 228, 218))
    return c


# ---------------------------------------------------------------- Escenario

def make_cielo():
    img = Image.new("RGB", (SW, SH), (12, 4, 30))
    d = ImageDraw.Draw(img)
    top, bot = (12, 4, 34), (118, 24, 112)
    for y in range(HORIZON):
        k = int(y / HORIZON * 9) / 8                    # franjas, como en consola vieja
        d.line([(0, y), (SW, y)], fill=mix(top, bot, k ** 1.6))
    rng = np.random.default_rng(7)
    for _ in range(45):
        x, y = int(rng.integers(0, SW)), int(rng.integers(0, 110))
        d.point((x, y), fill=mix((120, 110, 180), WHITE, float(rng.random())))
    # Sol retro con franjas abajo.
    cx, cy, r = SW // 2, 146, 38                        # se mete detrás de la ciudad
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        if dy > -4 and (dy + 4) % 6 < 1 + (dy + 4) // 9:
            continue
        half = int(math.sqrt(r * r - dy * dy))
        d.line([(cx - half, y), (cx + half, y)], fill=mix((255, 226, 96), (255, 56, 150), (y - cy + r) / (2 * r)))
    return img


def make_ciudad():
    """Tira de edificios con ventanas y un estadio con torres de luz; se repite al avanzar."""
    ancho, alto = 720, HORIZON
    img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(3)
    x = 0
    while x < ancho:
        if 72 <= x < 206:                              # hueco para el estadio
            x = 206
            continue
        bw, bh = int(rng.integers(10, 24)), int(rng.integers(18, 58))
        col = mix((22, 8, 46), (40, 14, 70), float(rng.random()))
        d.rectangle([x, alto - bh, x + bw - 1, alto - 1], fill=col)
        d.line([(x, alto - bh), (x + bw - 1, alto - bh)], fill=(90, 30, 120))
        for wy in range(alto - bh + 3, alto - 3, 4):
            for wx in range(x + 2, x + bw - 2, 3):
                if rng.random() < 0.35:
                    d.point((wx, wy), fill=[(0, 200, 230), (255, 60, 200), (255, 210, 120)][int(rng.integers(0, 3))])
        x += bw + int(rng.integers(0, 3))
    # Estadio: tazón con borde neón y cuatro torres de luz.
    sx, base = 85, alto - 1
    for i in range(30):
        y = base - i
        half = 44 + i // 3
        d.line([(sx + 55 - half, y), (sx + 55 + half, y)], fill=(32, 12, 60))
    d.line([(sx + 55 - 54, base - 30), (sx + 55 + 54, base - 30)], fill=(255, 50, 210))
    for i in range(8):
        d.line([(sx + 8 + i * 13, base - 26), (sx + 8 + i * 13, base - 4)], fill=(52, 20, 86))
    for tx in (sx - 4, sx + 22, sx + 88, sx + 114):
        d.line([(tx, base - 30), (tx, base - 50)], fill=(60, 30, 90))
        d.rectangle([tx - 2, base - 54, tx + 2, base - 51], fill=(255, 250, 220))
    return img


def dibujar_suelo(img, t):
    """Piso negro con cuadrícula neón en perspectiva; las líneas hacia el horizonte se deslizan al avanzar."""
    a = np.array(img)
    xs = np.arange(SW) - SW / 2
    cam = VEL_SUELO * t
    for y in range(HORIZON + 1, SH):
        dd = y - HORIZON
        cerca = min(1.0, dd / 110)
        fila = np.tile(np.array(mix((10, 2, 26), (22, 6, 44), cerca), np.uint8), (SW, 1))
        mundo = xs * (40.0 / dd) + cam
        idx = np.floor(mundo / 16)
        linea = np.zeros(SW, bool)
        linea[1:] = idx[1:] != idx[:-1]
        if dd > 7:
            fila[linea] = mix((40, 8, 64), (255, 50, 210), cerca ** 1.4)
        a[y] = fila
    k = 1.0
    while True:                                          # líneas horizontales (más juntas a lo lejos)
        y = int(HORIZON + k)
        if y >= SH:
            break
        cerca = min(1.0, (y - HORIZON) / 110)
        if y - HORIZON > 4:
            a[y] = mix((40, 8, 64), (255, 50, 210), cerca ** 1.4 * 0.85)
        k *= 1.45
    a[HORIZON] = (255, 140, 230)
    return Image.fromarray(a)


# ---------------------------------------------------------------- Globos de texto

class Globo:
    """Globo pixel (bordes en escalón) con nombre y texto que se escribe letra por letra."""

    def __init__(self, quien, texto, cfg, cabeza_x, cabeza_y):
        self.cfg = cfg
        self.texto = texto
        self.font = font(FONT_TEXT, 60, 0)              # Avenir Next Bold
        self.font_nombre = font(FONT_BOLD, 34, 2)
        self.lineas = self._partir(texto, 780)
        alto_linea = 74
        bw = max(self.font.getlength(l) for l in self.lineas) + 2 * 48
        bh = 58 + alto_linea * len(self.lineas) + 40
        bw, bh = PX * math.ceil(bw / PX), PX * math.ceil(bh / PX)
        # Fijo en el cielo (deja ver la ciudad); una flechita sobre la cabeza indica quién habla.
        x0, y0 = PX * round((W - bw) / 2 / PX), GLOBO_Y
        self.box = (x0, y0, x0 + bw, y0 + bh)
        self.alto_linea = alto_linea

    def _partir(self, texto, maximo):
        lineas, actual = [], ""
        for palabra in texto.split():
            prueba = (actual + " " + palabra).strip()
            if self.font.getlength(prueba) <= maximo:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        return lineas + [actual]

    def dibujar(self, img, letras):
        d = ImageDraw.Draw(img)
        x0, y0, x1, y1 = self.box
        p = PX
        borde, relleno, neon = INK, (250, 248, 255), self.cfg["color"]
        # Contorno neón exterior, borde oscuro y relleno, con esquinas en escalón.
        for grosor, col in ((2, neon), (1, borde), (0, relleno)):
            g = grosor * p
            d.rectangle([x0 - g + p, y0 - g, x1 + g - p - 1, y1 + g - 1], fill=col)
            d.rectangle([x0 - g, y0 - g + p, x1 + g - 1, y1 + g - p - 1], fill=col)
        d.text((x0 + 48, y0 + 34), self.cfg["nombre"], font=self.font_nombre, fill=self.cfg["tinta"], anchor="lm")
        quedan = letras
        for i, linea in enumerate(self.lineas):
            if quedan <= 0:
                break
            d.text((x0 + 48, y0 + 64 + i * self.alto_linea), linea[:quedan], font=self.font, fill=INK, anchor="lt")
            quedan -= len(linea) + 1


# ---------------------------------------------------------------- Render

class Renderer:
    def __init__(self):
        self.cielo = make_cielo()
        self.ciudad = make_ciudad()
        self.tiras = {k: cargar_tira(c["tira"]) for k, c in PERSONAJES.items()}
        titulo = glow_text(Image.new("RGB", (W, H)), (W / 2, 230), TITULO, font(FONT_BOLD, 92, 2), WHITE,
                           COLOR_LEFT, radius=18)
        self.titulo = glow_text(titulo, (W / 2, 330), SUBTITULO, font(FONT_TEXT, 50, 0), WHITE, TITLE_GLOW,
                                radius=12)
        self.brand = make_brand_layer()
        self.globos = []
        for i, ln in enumerate(LINEAS):
            cfg = PERSONAJES[ln["quien"]]
            cuadro = self.tiras[ln["quien"]][0][0]
            cabeza_x = (cfg["x"] + cuadro.width * 0.6) * PX
            cabeza_y = (SUELO - cuadro.height) * PX
            fin = ln["t1"] + 0.25 if i + 1 == len(LINEAS) else LINEAS[i + 1]["t0"] - 0.05
            self.globos.append((ln["t0"], fin, ln["quien"], ln, Globo(ln["quien"], ln["texto"], cfg, cabeza_x,
                                                                      cabeza_y)))

    def habla(self, quien, t):
        """Boca abierta: con voz, cuando el volumen de ese cuadro pasa el umbral; sin voz, mientras se escribe."""
        for t0, _, q, ln, _ in self.globos:
            if q != quien or not (t0 <= t < ln["t1"]):
                continue
            if ln["env"] is not None:
                i = int((t - t0) * FPS)
                return i < len(ln["env"]) and ln["env"][i] > 0.22
            escribiendo = (t - t0) * ln["cps"] < len(ln["texto"]) + 3
            return escribiendo and int(t * 11) % 3 != 0
        return False

    def frame(self, t):
        small = dibujar_suelo(self.cielo.copy(), t)
        off = int(VEL_CIUDAD * t) % self.ciudad.width
        for dx in (-off, self.ciudad.width - off):
            small.paste(self.ciudad, (dx, 0), self.ciudad)
        small = dibujar_suelo_sobre(small, t)
        d = ImageDraw.Draw(small)
        for quien, cfg in PERSONAJES.items():
            cuadros, tops = self.tiras[quien]
            i = (int(t / PASO) + cfg["fase"]) % len(cuadros)
            c = con_boca(cuadros[i], tops[i], cfg["boca"], self.habla(quien, t))
            sx = cfg["x"] + c.width // 2
            d.ellipse([sx - 16, SUELO - 3, sx + 14, SUELO + 2], fill=(6, 0, 16))      # sombra
            small.paste(c, (cfg["x"], SUELO - c.height + 1), c)
            if any(q == quien and t0 <= t < t1 for t0, t1, q, _, _ in self.globos):
                ax, ay = cfg["x"] + c.width // 2 + 2, SUELO - c.height - 9 + int(t * 4) % 2
                for k in range(4):
                    d.line([(ax - 3 + k, ay + k), (ax + 3 - k, ay + k)], fill=cfg["color"])

        img = small.resize((W, H), Image.NEAREST)
        halo = small.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR)
        img = ImageChops.screen(img, ImageChops.multiply(halo, Image.new("RGB", (W, H), (60, 60, 70))))
        for t0, t1, quien, ln, globo in self.globos:
            if t0 <= t < t1:
                globo.dibujar(img, int((t - t0) * ln["cps"]))
        img = ImageChops.screen(img, self.titulo)
        img = ImageChops.screen(img, self.brand)
        return img


def dibujar_suelo_sobre(img, t):
    """Vuelve a pintar el piso encima de la base de los edificios (la ciudad termina en el horizonte)."""
    piso = dibujar_suelo(Image.new("RGB", (SW, SH)), t)
    mask = Image.new("L", (SW, SH), 0)
    ImageDraw.Draw(mask).rectangle([0, HORIZON, SW, SH], fill=255)
    img.paste(piso, (0, 0), mask)
    return img


# ---------------------------------------------------------------- Audio

def silbato(buf, t, dur=0.55):
    n = int(dur * SAMPLE_RATE)
    tt = np.arange(n) / SAMPLE_RATE
    trino = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 28 * tt))
    sig = np.sin(2 * np.pi * (2700 + 60 * np.sin(2 * np.pi * 28 * tt)) * tt) * trino
    env = np.minimum(1, tt / 0.02) * np.minimum(1, (dur - tt) / 0.08)
    add(buf, t, (sig * env * 0.32).astype(np.float32))


def render_audio(out_wav, duration):
    buf = np.zeros(int((duration + 0.5) * SAMPLE_RATE), dtype=np.float32)
    beat = 60 / 140
    bar = beat * 4
    chords = [(45, 48, 52), (41, 45, 48), (48, 52, 55), (43, 47, 50)]   # Lam, Fa, Do, Sol
    for b in range(int(duration / bar) + 1):
        t0 = b * bar
        ch = chords[b % 4]
        for k in range(8):
            n = ch[0] - 12 + (12 if k % 2 else 0)
            add(buf, t0 + k * beat / 2, tone(midi_hz(n), beat / 2 * 0.9, "triangle", vol=0.2))
        for k in range(8):
            n = ch[[0, 1, 2, 1][k % 4]] + 24
            add(buf, t0 + k * beat / 2, tone(midi_hz(n), beat / 2 * 0.8, "square", 0.25, 0.03, decay=0.12))
        for k in range(4):
            add(buf, t0 + k * beat, tone(150, 0.12, "sine", vol=0.3, decay=0.05, sweep_to=45))
            add(buf, t0 + k * beat + beat / 2, tone(9000 + k, 0.04, "noise", vol=0.04, decay=0.012))
    peak = float(np.abs(buf).max()) or 1.0
    buf *= 0.45 / peak                                  # música baja
    # Mientras alguien habla, la música baja más (y vuelve a subir suave entre frases).
    habla = np.zeros(len(buf), np.float32)
    for ln in LINEAS:
        if ln["voz"] is not None:
            habla[int(ln["t0"] * SAMPLE_RATE):int(ln["t1"] * SAMPLE_RATE)] = 1
    k = int(0.15 * SAMPLE_RATE)
    habla = np.convolve(habla, np.ones(k) / k, mode="same")
    buf *= 1 - 0.6 * habla
    for ln in LINEAS:
        if ln["voz"] is not None:
            add(buf, ln["t0"], ln["voz"])
    silbato(buf, SILBATAZO, 0.6)
    end = int(duration * SAMPLE_RATE)
    buf = buf[:end]
    fade = int(0.8 * SAMPLE_RATE)
    buf[end - fade:] *= np.linspace(1, 0, fade)
    pcm = (np.clip(np.stack([buf, buf], axis=1), -1, 1) * 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- Main

def main():
    ap = argparse.ArgumentParser(description="Podcast de fútbol en pixel art (Alan y Luis caminando).")
    ap.add_argument("--preview", type=float, default=None, help="solo un cuadro PNG en ese segundo")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()
    out = Path(args.salida) if args.salida else OUTPUT
    r = Renderer()
    if args.preview is not None:
        png = ROOT / "out" / ".preview" / f"{out.stem}-{args.preview:g}s.png"
        png.parent.mkdir(parents=True, exist_ok=True)
        r.frame(args.preview).save(png)
        print(png)
        return

    tmp_dir = ROOT / "out" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_out = tmp_dir / out.name
    wav = tmp_out.with_suffix(".wav")
    render_audio(wav, DURATION)
    ff = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav), "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(DURATION), "-movflags", "+faststart",
        str(tmp_out),
    ], stdin=subprocess.PIPE)
    for i in range(int(DURATION * FPS)):
        ff.stdin.write(r.frame(i / FPS).tobytes())
        if i % (FPS * 2) == 0:
            print(f"{i / FPS:.0f}s / {DURATION:.0f}s", flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg falló")
    wav.unlink(missing_ok=True)
    tmp_out.replace(out)
    print(f"Listo: {out}")


if __name__ == "__main__":
    main()
