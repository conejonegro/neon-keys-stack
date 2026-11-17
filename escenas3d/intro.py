"""Intro de cine 3D "¿SABÍAS QUÉ?": letreros, textos y música para escenas/intro.html.

Una cámara avanza por una calle synthwave de noche con lluvia; pasa bajo el logo NK y junto a letreros
neón (DATOS, teclado, CIENCIA, ?, MÚSICA); al final sube, se ve el sol al fondo de la calle y cae el
título. Los tiempos viven aquí (CFG) y la escena los lee del JSON, así imagen y sonido van juntos.

Uso:
  .venv/bin/python escenas3d/intro.py out/.tmp/intro-sabias-que.json out/.tmp/intro-sabias-que.wav
  cd escenas3d && node grabar.js escenas/intro.html out/pruebas/datos/intro-sabias-que-prueba.mp4 \\
    --datos out/.tmp/intro-sabias-que.json --audio out/.tmp/intro-sabias-que.wav
"""
import base64
import io
import json
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import avatar  # noqa: E402
import neon_keys as nk  # noqa: E402

TITULO = ("¿SABÍAS", "QUÉ?")       # dos líneas; la segunda, más grande y en magenta

BPM = 120
BEAT = 60 / BPM
CFG = {
    "total": 10.0,
    "bpm": BPM,
    "subida": [5.0, 6.5],    # la cámara frena y sube; suena la subida
    "titulo": 6.5,           # cae el título (beat 13)
    # Cada letrero sale de cuadro en el segundo `t`, justo con su "whoosh"
    "letreros": [
        {"id": "logo", "t": 1.0, "lado": 0, "ancho": 4.2, "y": 4.6},
        {"id": "datos", "t": 1.75, "lado": 1, "ancho": 0.95, "y": 3.3},
        {"id": "teclado", "t": 2.5, "lado": -1, "ancho": 2.5, "y": 3.5},
        {"id": "ciencia", "t": 3.25, "lado": 1, "ancho": 0.95, "y": 3.6},
        {"id": "pregunta", "t": 4.0, "lado": -1, "ancho": 1.6, "y": 3.7},
        {"id": "musica", "t": 4.75, "lado": 1, "ancho": 0.95, "y": 3.4},
    ],
}
NEGRO = (0, 0, 0)
AMARILLO = (255, 225, 70)


# ------------------------------------------------------------------ letreros (RGB sobre negro)
def png_base64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def tubo(tam, dibujar, radio=12):
    """Neón genérico: dibujar(ImageDraw, es_halo) en una capa de halo borrosa y otra de núcleo."""
    halo, nucleo = Image.new("RGB", tam), Image.new("RGB", tam)
    dibujar(ImageDraw.Draw(halo), True)
    dibujar(ImageDraw.Draw(nucleo), False)
    h = halo.filter(ImageFilter.GaussianBlur(radio))
    return ImageChops.lighter(ImageChops.add(h, h), nucleo)


def cuchilla(texto, color):
    """Letrero vertical tipo calle de noche: marco neón y letras una debajo de otra."""
    w, h = 300, 140 + 170 * len(texto)
    img = tubo((w, h), lambda d, halo: d.rounded_rectangle(
        [24, 24, w - 24, h - 24], radius=40, outline=color, width=22 if halo else 8), radio=14)
    f = nk.font(nk.FONT_BOLD, 150, 2)
    for i, letra in enumerate(texto):
        img = nk.glow_text(img, (w / 2, 140 + 170 * i), letra, f, (255, 255, 255), color, radius=16)
    return img


def logo():
    """La foto de perfil (NK en el átomo, sin contorno) con fondo negro para que brille sola."""
    fondo = avatar.background
    avatar.background = lambda: Image.new("RGB", (avatar.S, avatar.S))
    try:
        return avatar.marca_atomo(False)
    finally:
        avatar.background = fondo


def teclado():
    img = Image.new("RGB", (1080, 600))
    marco = tubo(img.size, lambda d, halo: d.rounded_rectangle(
        [30, 30, 1050, 570], radius=50, outline=nk.COLOR_LEFT, width=24 if halo else 9), radio=16)
    teclas = avatar.neon(Image.new("RGB", (avatar.S, avatar.S)),
                         lambda d, halo: avatar.keys(d, 150, 930, 130, 340, halo, lit=(2, 5)), radius=16)
    return ImageChops.lighter(marco, teclas.crop((0, 0, 1080, 600)))


def pregunta():
    img = tubo((600, 600), lambda d, halo: d.ellipse(
        [40, 40, 560, 560], outline=nk.COLOR_LEFT, width=26 if halo else 10), radio=16)
    return nk.glow_text(img, (300, 310), "?", nk.font(nk.FONT_BOLD, 380, 2), (255, 255, 255),
                        nk.COLOR_LEFT, radius=24)


def capa_titulo():
    capa = Image.new("RGB", (nk.W, nk.H))
    a, b = TITULO
    capa = nk.glow_text(capa, (nk.W / 2, 540), a.strip(), nk.font(nk.FONT_BOLD, 170, 2), (255, 255, 255),
                        nk.TITLE_GLOW, radius=26)
    return nk.glow_text(capa, (nk.W / 2, 740), b, nk.font(nk.FONT_BOLD, 230, 2), (255, 255, 255),
                        nk.COLOR_LEFT, radius=30)


# ------------------------------------------------------------------ sonido (120 BPM, todo sintetizado)
SR = 44100
DUR = CFG["total"]
N = int(SR * DUR)
rng = np.random.default_rng(21)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
T_TIT = CFG["titulo"]
SUB0, SUB1 = CFG["subida"]


def poner(destino, s, t, gan=1.0, lado=0.0):
    a = int(t * SR)
    if a >= N or a < 0:
        return
    n = min(len(s), N - a)
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


def filtro(x, bajo, alto):
    """Paso banda suave con FFT (bajo/alto en Hz)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    curva = (1 / (1 + (bajo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / alto) ** 4))
    return np.fft.irfft(X * curva, len(x))


def sierra(f, t, armonicos=8, caida=0.0):
    s = np.zeros_like(t)
    for k in range(1, armonicos + 1):
        if f * k > SR / 2.2:
            break
        s += np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * caida * (k - 1))
    return s


def bombo(grave=1.0):
    t = np.arange(int(0.5 * SR)) / SR
    f = 45 * grave + 120 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5) + rng.normal(0, 1, len(t)) * np.exp(-t * 150) * 0.2


def hat():
    t = np.arange(int(0.09 * SR)) / SR
    return np.diff(rng.normal(0, 1, len(t)), prepend=0) * np.exp(-t * 60) * 0.5


def caja():
    t = np.arange(int(0.22 * SR)) / SR
    r = filtro(rng.normal(0, 1, len(t)), 900, 9000)
    return (r * 1.4 + np.sin(2 * np.pi * 190 * t) * 0.6) * np.exp(-t * 22)


def bajo(m, dur):
    t = np.arange(int(dur * SR)) / SR
    s = sierra(hz(m), t, 12, caida=10) + 0.8 * np.sin(2 * np.pi * hz(m) * t)
    return s * np.minimum(1, t / 0.004) * np.exp(-t * 6)


def pad(notas, dur):
    t = np.arange(int(dur * SR)) / SR
    s = sum(sierra(hz(m + d), t, 6) for m in notas for d in (-0.09, 0, 0.09))
    return s * np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.3) / len(notas)


def whoosh(dur=0.7):
    """Ruido que crece y se va, como un letrero pasando cerca."""
    t = np.arange(int(dur * SR)) / SR
    pico = 0.42 * dur
    env = np.where(t < pico, (t / pico) ** 2.2, np.exp(-(t - pico) * 9))
    return filtro(rng.normal(0, 1, len(t)), 500, 4500) * env


def eco(x, segundos=1.8, mezcla=0.3):
    t = np.arange(int(segundos * SR)) / SR
    ir = rng.normal(0, 1, len(t)) * np.exp(-t * 3)
    ir /= np.sqrt(np.sum(ir ** 2))
    m = 1 << (len(x) + len(ir) - 1).bit_length()
    humedo = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return x * (1 - mezcla) + humedo * mezcla * 3


def sonido():
    mezcla = np.zeros((N, 2))
    tt = np.arange(N) / SR

    # Lluvia de fondo, todo el tiempo (izquierda y derecha distintas)
    for c in (0, 1):
        mezcla[:, c] += filtro(rng.normal(0, 1, N), 600, 7000) * 0.035

    # Acordes: Am – F – C – G (subida) – Am (título)
    acordes = [(0, 2, 45, [57, 60, 64]), (2, 4, 41, [57, 60, 65]), (4, SUB0, 48, [55, 60, 64]),
               (SUB0, T_TIT, 43, [55, 59, 62]), (T_TIT, DUR, 45, [57, 60, 64, 69])]
    for a, b, raiz, notas in acordes:
        p = pad(notas, b - a + 0.3)
        poner(mezcla, p, a, 0.11, -0.3)
        poner(mezcla, p, a + 0.012, 0.11, 0.3)
        if b <= SUB0 or a >= T_TIT:
            for k in range(int(round((b - a) / (BEAT / 2)))):   # bajo en corcheas
                poner(mezcla, bajo(raiz - 12 + (12 if k % 4 == 3 else 0), BEAT / 2), a + k * BEAT / 2, 0.22)

    # Batería: bombo en cada tiempo desde el segundo 0 (gancho), hats a contratiempo desde el 2
    for k in range(int(DUR / BEAT)):
        t = k * BEAT
        if t < SUB0 or t >= T_TIT:
            poner(mezcla, bombo(), t, 0.55)
        if (2.0 <= t < SUB0) or t >= T_TIT:
            poner(mezcla, hat(), t + BEAT / 2, 0.18, 0.35)
        if t >= T_TIT and k % 2 == 1:
            poner(mezcla, caja(), t, 0.3)

    # Cada letrero pasa con un whoosh hacia su lado
    for L in CFG["letreros"]:
        poner(mezcla, whoosh(), L["t"] - 0.32, 0.5 if L["id"] == "logo" else 0.35, 0.75 * L["lado"])

    # Subida: redoble que acelera + barrido hacia arriba, y un silencio de 0.12 s antes del golpe
    t = SUB0
    while t < T_TIT - 0.12:
        avance = (t - SUB0) / (T_TIT - SUB0)
        poner(mezcla, caja(), t, 0.08 + 0.22 * avance)
        t += BEAT / (2 if avance < 0.4 else 4 if avance < 0.75 else 8)
    n = int((T_TIT - SUB0) * SR)
    u = np.arange(n) / n
    barrido = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (u * 2.5)) / SR) * u ** 2 * 0.15
    barrido += filtro(rng.normal(0, 1, n), 2000, 12000) * u ** 2 * 0.25
    barrido *= np.where(u > 1 - 0.12 / (T_TIT - SUB0), 0, 1)
    poner(mezcla, barrido, SUB0, 1.0)

    # El golpe del título: bombo grave, sub largo, ráfaga con eco y acorde
    golpe = np.zeros(int(2.5 * SR))
    t2 = np.arange(len(golpe)) / SR
    golpe += np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t2 * 8)) / SR) * np.exp(-t2 * 1.6) * 0.9
    golpe[: int(0.5 * SR)] += bombo(0.8) * 0.8
    golpe += filtro(rng.normal(0, 1, len(golpe)), 300, 8000) * np.exp(-t2 * 5) * 0.35
    golpe = eco(golpe, mezcla=0.35)
    poner(mezcla, golpe, T_TIT, 0.75)
    estoc = pad([57, 64, 69, 72, 76], 1.6) * np.exp(-np.arange(int(1.6 * SR)) / SR * 2)
    poner(mezcla, eco(estoc, mezcla=0.4), T_TIT, 0.22)

    # Zumbido de neón mientras el título parpadea al encenderse
    n = int(0.45 * SR)
    t3 = np.arange(n) / SR
    zumbido = np.sign(np.sin(2 * np.pi * 120 * t3)) * 0.4 + rng.normal(0, 1, n) * (rng.random(n) > 0.995)
    poner(mezcla, filtro(zumbido, 100, 3000) * np.exp(-t3 * 5), T_TIT, 0.12)

    # Fundido corto al final y techo suave
    mezcla *= np.minimum(1, (DUR - tt) / 0.4)[:, None]
    mezcla = np.tanh(mezcla * 1.2)
    return mezcla / np.max(np.abs(mezcla)) * 0.9


def main():
    ruta_json, ruta_wav = Path(sys.argv[1]), Path(sys.argv[2])
    ruta_json.parent.mkdir(parents=True, exist_ok=True)
    texturas = {
        "logo": logo(), "datos": cuchilla("DATOS", nk.COLOR_RIGHT), "teclado": teclado(),
        "ciencia": cuchilla("CIENCIA", nk.COLOR_LEFT), "pregunta": pregunta(),
        "musica": cuchilla("MÚSICA", AMARILLO),
    }
    datos = {
        "total": CFG["total"], "fps": 30, "cfg": CFG,
        "texturas": {k: png_base64(v) for k, v in texturas.items()},
        "capas": {"titulo": png_base64(capa_titulo()), "marca": png_base64(nk.make_brand_layer())},
    }
    ruta_json.write_text(json.dumps(datos), encoding="utf-8")
    s = sonido()
    with wave.open(str(ruta_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((s * 32767).astype("<i2").tobytes())
    print(f"Listo: {ruta_json} y {ruta_wav} ({DUR:.1f} s)")


if __name__ == "__main__":
    main()
