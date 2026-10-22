#!/usr/bin/env python3
"""Neon Keys · podcast de fútbol en el set: Alan y Luis sentados frente a frente, platicando del partido.

El set (cuarto con la tele, sillas, mesa y tazas) y las hojas de poses son de IA; las poses se limpian con
`pixel_ia.py luis-poses` / `alan-poses` (8 poses: cerrada, hablando, abierta, parpadeo, mano, mano hablando,
dedo arriba, hombros). Aquí se encima todo con código: la mesa y las tazas van delante de los personajes,
la boca se mueve cambiando de pose, parpadean, la tele se anima, y hay
globos de texto, chiptune, balbuceo 8-bit y silbatazo. La voz se pone después en TikTok (o un audio por frase).

Uso:
    .venv/bin/python podcast_set.py                    # → out/pruebas/podcast-set-tigres-prueba.mp4
    .venv/bin/python podcast_set.py --episodio penal   # → out/pruebas/podcast-set-penal-prueba.mp4
    .venv/bin/python podcast_set.py --preview 6     # solo un cuadro PNG en t=6 s
"""

import argparse
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from ajolote import add, midi_hz, tone
from neon_keys import (COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, FONT_TEXT, FPS, H, SAMPLE_RATE, TITLE_GLOW, W, font,
                       glow_text, make_brand_layer)
from podcast import leer_voz, silbato

ROOT = Path(__file__).resolve().parent
SET = ROOT / "out" / "personajes" / "ia" / "set-podcast-ia.png"

K = W / 941                     # escala del set de la IA (941×1672) al video
MESA_Y = int(1205 * K)          # borde de atrás de la mesa: lo de abajo va delante de los personajes
TAZAS = ((170, 315), (635, 790))            # columnas de las tazas en el set de la IA (también van delante)
TELE = (int(452 * K), int(545 * K), int(642 * K), int(690 * K))   # pantalla de la tele (video)
PX = 5                          # cada pixel de los personajes mide 5×5 en el video
ESCALON = 6                     # tamaño del escalón en las esquinas del globo

WHITE = (255, 255, 255)
INK = (24, 10, 44)

# poses: hoja limpia de 8 cuadros · cx: centro en el video
# voz: tono del balbuceo 8-bit · parpadeos: segundos en que cierra los ojos
PERSONAJES = {
    "alan": dict(nombre="ALAN", poses="out/personajes/alan-poses.png", cx=250, voz=330,
                 color=COLOR_RIGHT, tinta=(0, 120, 150), parpadeos=(1.9, 5.4, 8.8, 11.6)),
    "luis": dict(nombre="LUIS", poses="out/personajes/luis-poses.png", cx=830, voz=210,
                 color=COLOR_LEFT, tinta=(190, 20, 150), parpadeos=(3.1, 6.9, 10.2)),
}
CERRADA, HABLANDO, ABIERTA, PARPADEO, MANO, MANO_HABLA, DEDO, HOMBROS = range(8)
ESTILOS = {                     # poses que se alternan al hablar (una sílaba cada 1/9 s)
    "normal": (HABLANDO, ABIERTA, HABLANDO, CERRADA),
    "mano": (MANO_HABLA, MANO, MANO_HABLA, MANO),
    "dedo": (DEDO,),
    "hombros": (HOMBROS,),
}

# Cada episodio: título, subtítulo, diálogo y reacciones. Diálogo: (quién, texto, voz, gestos); gestos =
# [(palabra desde la que cambia, estilo)], empieza en "normal". La voz es un audio (wav/mp3) por frase; si
# falta, la línea sale con texto y balbuceo. Reacciones del que escucha: (línea, desde qué fracción, pose).
V = "out/pruebas/voces/"
EPISODIOS = {
    "tigres": dict(
        titulo="CHIVAS vs TIGRES", subtitulo="¿Quién debe ser titular?",
        dialogo=[
            ("luis", "Mañana Chivas contra Tigres… ¡va a estar durísimo!", V + "tigres-luis-1.mp3",
             [("¡va", "mano")]),
            ("alan", "Y con tanto lesionado… está complicado, wey.", V + "tigres-alan-2.mp3", [("Y", "mano")]),
            ("luis", "¡Ojalá metan a Santi y a Camberos de titulares!", V + "tigres-luis-3.mp3",
             [("Santi", "dedo")]),
        ],
        reacciones=[(0, 0.75, HOMBROS), (2, 0.55, "asiente")]),
    "penal": dict(
        titulo="CHIVAS", subtitulo="¿Y ese penal, Sepúlveda?",
        dialogo=[
            ("luis", "¡Pinche Sepúlveda, estúpido! ¿¡Cómo falla ese penal!?", V + "penal-luis-1.mp3",
             [("¿¡Cómo", "hombros")]),
            ("alan", "Sí, maldito idiota… ¡un penal es muy fácil!", V + "penal-alan-2.mp3", [("¡un", "mano")]),
            ("luis", "A la próxima, que lo tire el Piojo.", V + "penal-luis-3.mp3", [("Piojo", "dedo")]),
        ],
        reacciones=[(0, 0.45, HOMBROS), (1, 0.4, "asiente"), (2, 0.6, "asiente")]),
}
INICIO, PAUSA, FINAL = 0.9, 0.3, 1.4
LETRAS_POR_SEG = 21
GLOBO_Y = 398


def armar_lineas():
    lineas, t = [], INICIO
    for quien, texto, voz, gestos in DIALOGO:
        a = leer_voz(voz)
        dur = len(texto) / LETRAS_POR_SEG + 1.0 if a is None else len(a) / SAMPLE_RATE
        cps = LETRAS_POR_SEG if a is None else len(texto) / (dur * 0.8)     # el texto acaba antes que la voz
        env = None
        if a is not None:               # volumen de la voz cuadro por cuadro (para abrir la boca)
            hop = SAMPLE_RATE // FPS
            n = len(a) // hop
            env = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1))
            env /= env.max() or 1
        cambios = [(texto.index(p), estilo) for p, estilo in gestos]
        lineas.append(dict(t0=t, t1=t + dur, quien=quien, texto=texto, voz=a, env=env, cps=cps,
                           cambios=cambios))
        t += dur + PAUSA
    return lineas


def usar(nombre):
    """Elige el episodio: arma su línea de tiempo y el nombre del video."""
    global TITULO, SUBTITULO, DIALOGO, REACCIONES, LINEAS, DURATION, OUTPUT
    ep = EPISODIOS[nombre]
    TITULO, SUBTITULO, DIALOGO, REACCIONES = ep["titulo"], ep["subtitulo"], ep["dialogo"], ep["reacciones"]
    LINEAS = armar_lineas()
    DURATION = round(LINEAS[-1]["t1"] + FINAL, 2)
    OUTPUT = ROOT / "out" / "pruebas" / f"podcast-set-{nombre}-prueba.mp4"


usar("tigres")


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- Set

def cargar_set():
    """Set de la IA al tamaño del video + la capa de adelante (mesa y tazas, sin el fondo de atrás)."""
    fondo = Image.open(SET).convert("RGB").resize((W, H), Image.NEAREST)
    a = np.array(fondo.convert("RGBA"))
    m = np.zeros(a.shape[:2], bool)
    m[MESA_Y:] = True
    for x0, x1 in TAZAS:
        X0, X1, Y0 = int(x0 * K), int(x1 * K), int(1140 * K)
        claro = a[Y0:MESA_Y, X0:X1, :3].min(2) > 150
        for r in range(claro.shape[0]):                 # de la orilla izquierda a la derecha de la taza
            c = np.where(claro[r])[0]
            if len(c):
                m[Y0 + r, X0 + c[0]:X0 + c[-1] + 1] = True
    a[~m, 3] = 0
    # Viñeta suave: centra la mirada en los personajes.
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.55) / (H * 0.6)) ** 2)
    vineta = Image.fromarray((np.clip(1.15 - d * 0.55, 0.55, 1) * 255).astype(np.uint8)).convert("RGB")
    return fondo, Image.fromarray(a), vineta


def cargar_poses(path):
    hoja = Image.open(ROOT / path).convert("RGBA")
    w = hoja.width // 8
    return [hoja.crop((i * w, 0, (i + 1) * w, hoja.height)).resize((w * PX, hoja.height * PX), Image.NEAREST)
            for i in range(8)]


def dibujar_tele(img, t):
    """La tele: un balón que va y viene entre los jugadores, línea de barrido y parpadeo de pantalla."""
    x0, y0, x1, y1 = TELE
    pant = img.crop(TELE)
    a = np.array(pant).astype(np.float32)
    a *= 0.94 + 0.06 * math.sin(t * 23) * math.sin(t * 7)
    barrido = int((t * 90) % (y1 - y0 + 40)) - 20
    for k in range(-6, 7):
        r = barrido + k
        if 0 <= r < a.shape[0]:
            a[r] = a[r] * 0.82 + 255 * 0.18 * (1 - abs(k) / 7)
    a[::4] *= 0.9                                        # líneas de tubo
    pant = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(pant)
    w, h = x1 - x0, y1 - y0
    bx = w * (0.5 + 0.38 * math.sin(t * 1.3) * math.cos(t * 0.45))
    by = h * (0.62 + 0.22 * math.sin(t * 2.1 + 1))
    s = 7
    d.rectangle([bx - s, by - s, bx + s, by + s], fill=(20, 20, 20))
    d.rectangle([bx - s + 3, by - s + 3, bx + s - 3, by + s - 3], fill=WHITE)
    if int(t * 2) % 2 == 0:                              # punto rojo de "en vivo"
        d.rectangle([w - 26, 10, w - 14, 22], fill=(255, 40, 60))
    img.paste(pant, (x0, y0))


# ---------------------------------------------------------------- Globos

class Globo:
    """Globo pixel con esquinas en escalón, contorno neón del que habla, nombre y colita hacia él."""

    def __init__(self, ln, cfg):
        self.cfg = cfg
        self.ln = ln
        self.font = font(FONT_TEXT, 56, 0)
        self.font_nombre = font(FONT_BOLD, 32, 2)
        self.lineas = self._partir(ln["texto"], 800)
        self.alto_linea = 68
        bw = max(self.font.getlength(l) for l in self.lineas) + 2 * 44
        bh = 54 + self.alto_linea * len(self.lineas) + 34
        self.size = (ESCALON * math.ceil(bw / ESCALON), ESCALON * math.ceil(bh / ESCALON))
        izquierda = cfg["cx"] < W / 2
        x = 44 if izquierda else W - 44 - self.size[0]
        self.pos = (x, GLOBO_Y)
        self.cola_x = (cfg["cx"] - x)                  # colita apuntando hacia quien habla
        self.cola_x = max(60, min(self.size[0] - 60, self.cola_x))

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

    def capa(self, letras):
        bw, bh = self.size
        m, cola = 3 * ESCALON, 7 * ESCALON
        img = Image.new("RGBA", (bw + 2 * m, bh + 2 * m + cola), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        p = ESCALON
        neon, borde, relleno = self.cfg["color"], INK, (250, 248, 255)
        cx = m + self.cola_x
        for grosor, col in ((2, neon), (1, borde), (0, relleno)):
            g = grosor * p
            x0, y0, x1, y1 = m, m, m + bw, m + bh
            d.rectangle([x0 - g + p, y0 - g, x1 + g - p - 1, y1 + g - 1], fill=col)
            d.rectangle([x0 - g, y0 - g + p, x1 + g - 1, y1 + g - p - 1], fill=col)
            for k in range(6):                           # colita en escalón
                half = (6 - k) * p // 2 + g
                d.rectangle([cx - half, y1 + k * p - g, cx + half - 1, y1 + (k + 1) * p - 1 + g], fill=col)
        d.text((m + 44, m + 32), self.cfg["nombre"], font=self.font_nombre, fill=self.cfg["tinta"], anchor="lm")
        quedan = letras
        for i, linea in enumerate(self.lineas):
            if quedan <= 0:
                break
            d.text((m + 44, m + 60 + i * self.alto_linea), linea[:quedan], font=self.font, fill=INK, anchor="lt")
            quedan -= len(linea) + 1
        return img, m

    def dibujar(self, img, t):
        ln = self.ln
        capa, m = self.capa(int((t - ln["t0"]) * ln["cps"]))
        k = 0.8 + 0.2 * ease_out((t - ln["t0"]) / 0.16)   # aparece con un "pop"
        if k < 1:
            capa = capa.resize((int(capa.width * k), int(capa.height * k)), Image.NEAREST)
        x = self.pos[0] - m + int((1 - k) * (self.cola_x + m))
        y = self.pos[1] - m + int((1 - k) * capa.height / k)
        img.paste(capa, (x, y), capa)


# ---------------------------------------------------------------- Render

class Renderer:
    def __init__(self):
        self.fondo, self.frente, self.vineta = cargar_set()
        self.poses = {k: cargar_poses(c["poses"]) for k, c in PERSONAJES.items()}
        self.globos = [Globo(ln, PERSONAJES[ln["quien"]]) for ln in LINEAS]
        self.titulo = glow_text(Image.new("RGB", (W, H)), (W / 2, 230), TITULO, font(FONT_BOLD, 92, 2), WHITE,
                                COLOR_LEFT, radius=18)
        self.subtitulo = glow_text(Image.new("RGB", (W, H)), (W / 2, 326), SUBTITULO, font(FONT_TEXT, 50, 0),
                                   WHITE, TITLE_GLOW, radius=12)
        self.brand = make_brand_layer()

    def linea_en(self, t):
        for i, ln in enumerate(LINEAS):
            fin = LINEAS[i + 1]["t0"] if i + 1 < len(LINEAS) else DURATION
            if ln["t0"] <= t < fin:
                return i, ln
        return None, None

    def pose(self, quien, t):
        """Qué pose toca y cuánto sube/baja (en pixeles del personaje)."""
        cfg = PERSONAJES[quien]
        i, ln = self.linea_en(t)
        if ln is not None and ln["quien"] == quien:
            letra = (t - ln["t0"]) * ln["cps"]
            estilo = "normal"
            for desde, e in ln["cambios"]:
                if letra >= desde:
                    estilo = e
            seq = ESTILOS[estilo]
            if ln["env"] is not None and t < ln["t1"]:   # con voz: la boca sigue el volumen
                k = int((t - ln["t0"]) * FPS)
                v = ln["env"][k] if k < len(ln["env"]) else 0
                if estilo == "normal":
                    n = ABIERTA if v > 0.55 else HABLANDO if v > 0.2 else CERRADA
                elif estilo == "mano":
                    n = MANO_HABLA if v > 0.2 else MANO
                else:
                    n = ESTILOS[estilo][0]
                return n, 1 if v > 0.7 else 0
            if t < ln["t1"] and letra < len(ln["texto"]) + 2:
                return seq[int((t - ln["t0"]) * 9) % len(seq)], int((t - ln["t0"]) * 4.5) % 2
            return {"normal": CERRADA, "mano": MANO}.get(estilo, ESTILOS[estilo][0]), 0
        if ln is not None:                               # escucha
            for li, desde, reaccion in REACCIONES:
                if li == i and t >= ln["t0"] + desde * (ln["t1"] - ln["t0"]):
                    if reaccion == "asiente":
                        return CERRADA, 1 if int((t - ln["t0"]) * 5) % 2 else 0
                    if t < ln["t1"] + 0.2:
                        return reaccion, 0
        if any(0 <= t - b < 0.13 for b in cfg["parpadeos"]):
            return PARPADEO, 0
        return CERRADA, 1 if (t * 0.8) % 1 < 0.5 else 0     # respira

    def hablando(self, quien, t):
        _, ln = self.linea_en(t)
        return ln is not None and ln["quien"] == quien and t < ln["t1"]

    def frame(self, t):
        img = self.fondo.copy()
        dibujar_tele(img, t)
        img = img.convert("RGBA")
        for quien, cfg in PERSONAJES.items():
            n, dy = self.pose(quien, t)
            c = self.poses[quien][n]
            img.alpha_composite(c, (cfg["cx"] - c.width // 2, MESA_Y + 30 - c.height + dy * PX))
        img.alpha_composite(self.frente)
        img = ImageChops.multiply(img.convert("RGB"), self.vineta)
        # Indicador neón sobre quien habla.
        for quien, cfg in PERSONAJES.items():
            if self.hablando(quien, t):
                ax, ay = cfg["cx"] + (20 if quien == "alan" else -10), 912 + int(t * 4) % 2 * PX
                for k in range(5):
                    d2 = ImageDraw.Draw(img)
                    d2.rectangle([ax - (5 - k) * PX, ay + k * PX, ax + (5 - k) * PX - 1, ay + (k + 1) * PX - 1],
                                 fill=cfg["color"])
        i, ln = self.linea_en(t)
        if ln is not None and (t < ln["t1"] + 0.25 or i + 1 == len(LINEAS)):
            self.globos[i].dibujar(img, t)
        # Título: entra con un golpe al inicio (gancho) y se queda.
        k = ease_out(t / 0.35)
        if k < 1:
            tit = Image.blend(Image.new("RGB", (W, H)), self.titulo, k)
            img = ImageChops.screen(img, tit)
        else:
            img = ImageChops.screen(img, self.titulo)
        if t > 0.35:
            img = ImageChops.screen(img, Image.blend(Image.new("RGB", (W, H)), self.subtitulo,
                                                     ease_out((t - 0.35) / 0.3)))
        img = ImageChops.screen(img, self.brand)
        if t < 0.25:                                     # destello del silbatazo
            img = Image.blend(img, Image.new("RGB", (W, H), WHITE), 0.5 * (1 - t / 0.25))
        return img


# ---------------------------------------------------------------- Audio

def render_audio(out_wav, duration):
    buf = np.zeros(int((duration + 0.5) * SAMPLE_RATE), dtype=np.float32)
    beat = 60 / 118
    bar = beat * 4
    chords = [(50, 53, 57), (46, 50, 53), (41, 45, 48), (48, 52, 55)]   # Rem, Sib, Fa, Do
    for b in range(int(duration / bar) + 1):
        t0 = b * bar
        ch = chords[b % 4]
        for k in range(8):
            n = ch[0] - 12 + (7 if k % 4 == 2 else 0)
            add(buf, t0 + k * beat / 2, tone(midi_hz(n), beat / 2 * 0.85, "triangle", vol=0.22))
        for k in range(4):
            add(buf, t0 + k * beat + beat / 2, tone(midi_hz(ch[1] + 12), beat * 0.3, "square", 0.25, 0.025,
                                                   decay=0.1))
            add(buf, t0 + k * beat, tone(140, 0.14, "sine", vol=0.32 if k % 2 == 0 else 0.0, decay=0.06,
                                         sweep_to=45))
            if k % 2:
                add(buf, t0 + k * beat, tone(1800, 0.09, "noise", vol=0.09, decay=0.04))
            add(buf, t0 + k * beat + beat / 2, tone(9000, 0.03, "noise", vol=0.035, decay=0.01))
    buf *= 0.4 / (float(np.abs(buf).max()) or 1.0)
    # Ambiente de estadio desde la tele: ruido grave que respira.
    n = len(buf)
    ruido = np.random.default_rng(4).standard_normal(n).astype(np.float32)
    kk = 400
    ruido = np.convolve(ruido, np.ones(kk) / kk, mode="same")
    tt = np.arange(n) / SAMPLE_RATE
    buf += ruido * (0.5 + 0.3 * np.sin(tt * 0.9)) * 0.6
    # Mientras alguien habla con voz, el fondo baja (y vuelve a subir suave entre frases).
    habla = np.zeros(n, np.float32)
    for ln in LINEAS:
        if ln["voz"] is not None:
            habla[int(ln["t0"] * SAMPLE_RATE):int(ln["t1"] * SAMPLE_RATE)] = 1
    kk = int(0.15 * SAMPLE_RATE)
    buf *= 1 - 0.55 * np.convolve(habla, np.ones(kk) / kk, mode="same")
    # Balbuceo 8-bit: una sílaba por cada cambio de boca (para que se "oiga" quién habla sin voz).
    for ln in LINEAS:
        if ln["voz"] is not None:
            add(buf, ln["t0"], ln["voz"])
            continue
        f0 = PERSONAJES[ln["quien"]]["voz"]
        rng = np.random.default_rng(len(ln["texto"]))
        fin = ln["t0"] + len(ln["texto"]) / ln["cps"]
        t = ln["t0"]
        while t < fin:
            f = f0 * float(rng.choice([1, 1.12, 1.26, 0.89, 1.5]))
            add(buf, t, tone(f, 0.07, "square", 0.3, 0.07, decay=0.04, sweep_to=f * 0.92))
            t += 1 / 9 * 2
    silbato(buf, 0.02, 0.5)
    end = int(duration * SAMPLE_RATE)
    buf = buf[:end]
    fade = int(0.7 * SAMPLE_RATE)
    buf[end - fade:] *= np.linspace(1, 0, fade)
    buf *= 0.9 / (float(np.abs(buf).max()) or 1.0)
    pcm = (np.clip(np.stack([buf, buf], axis=1), -1, 1) * 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- Main

def main():
    ap = argparse.ArgumentParser(description="Podcast de fútbol en el set (Alan y Luis sentados).")
    ap.add_argument("--preview", type=float, default=None, help="solo un cuadro PNG en ese segundo")
    ap.add_argument("--salida", default=None)
    ap.add_argument("--episodio", default="tigres", choices=sorted(EPISODIOS))
    args = ap.parse_args()
    usar(args.episodio)
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
