#!/usr/bin/env python3
"""Neon Keys · dato curioso 3D: ondas gravitacionales (el choque de agujeros negros que LIGO escuchó en 2015).

Prepara lo que necesita escenas/ondas.html: los tiempos de la espiral (los mismos para la imagen y el sonido),
las capas de texto hechas con Pillow (mismas fuentes y halo que el 2D) y el audio sintetizado: el "chirp" que
sube de tono mientras los agujeros giran más rápido, el golpe del choque, el zumbido que se apaga (ringdown),
un fondo ambiental y, al final, el chirp otra vez "como lo escuchó LIGO".

Uso:
    .venv/bin/python escenas3d/ondas.py          # → out/.tmp/ondas.json + out/.tmp/ondas.wav
    cd escenas3d && node grabar.js escenas/ondas.html ../out/pruebas/dato-ondas-gravitacionales-prueba.mp4 \\
        --datos out/.tmp/ondas.json --audio out/.tmp/ondas.wav
"""

import base64
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import neon_keys as nk  # noqa: E402

SR = nk.SAMPLE_RATE
WHITE = (255, 255, 255)

# Espiral: la separación se encoge como τ^(1/4) y el giro se acelera como τ^(-3/8) (τ = tiempo que falta),
# que es como se acercan de verdad dos agujeros negros al radiar ondas gravitacionales.
T_CHOQUE = 12.0                 # segundo del choque (clímax)
TAU_MIN = 0.06                  # τ al chocar (evita el infinito)
TC = T_CHOQUE + TAU_MIN
W0 = 1.1                        # giro inicial (radianes por segundo)
A0 = 3.2                        # separación inicial (unidades de la escena)
TOTAL = 23.4

TITULO = ("¿SE PUEDE ESCUCHAR", "LA GRAVEDAD?")
# (desde, hasta, líneas, color del halo). Van arriba, sobre el cielo negro, donde la malla no estorba.
TEXTOS = [
    (0.7, 4.6, ["Hace 1,300 millones de años,", "dos agujeros negros giraban", "uno alrededor del otro"],
     nk.TITLE_GLOW),
    (4.8, 8.6, ["Cada vuelta los acercaba más…", "y los hacía girar más rápido"], nk.BRAND_GLOW),
    (8.9, 11.7, ["Hasta que…"], nk.TITLE_GLOW),
    (13.7, 16.8, ["En un instante soltaron más energía", "que todas las estrellas", "del universo juntas"],
     nk.BRAND_GLOW),
    (17.0, 20.3, ["En 2015 esas ondas llegaron", "a la Tierra… y así sonaron:"], nk.TITLE_GLOW),
]
CHOQUE_TXT = (12.0, 13.5, "¡CHOCARON!")
CIERRE = 20.5                   # desde aquí: NEON KEYS + "Sígueme para más"
REPETICION = (18.55, 1.7)       # el chirp otra vez (inicio, duración)


def omega(t):
    tau = np.maximum(TC - t, TAU_MIN)
    return W0 * (TC / tau) ** 0.375


def png_base64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- Capas de texto

def capa_titulo():
    capa = Image.new("RGB", (nk.W, nk.H))
    f = nk.font(nk.FONT_BOLD, 80, 2)
    capa = nk.glow_text(capa, (nk.W / 2, 215), TITULO[0], f, WHITE, nk.TITLE_GLOW, radius=18)
    return nk.glow_text(capa, (nk.W / 2, 310), TITULO[1], f, WHITE, nk.BRAND_GLOW, radius=18)


def capa_texto(lineas, halo, y0=470):
    capa = Image.new("RGB", (nk.W, nk.H))
    f = nk.font(nk.FONT_TEXT, 58, 0)
    for i, linea in enumerate(lineas):
        capa = nk.glow_text(capa, (nk.W / 2, y0 + i * 78), linea, f, WHITE, halo, radius=12)
    return capa


def capa_choque():
    capa = Image.new("RGB", (nk.W, nk.H))
    return nk.glow_text(capa, (nk.W / 2, 560), CHOQUE_TXT[2], nk.font(nk.FONT_BOLD, 124, 2), WHITE,
                        nk.BRAND_GLOW, radius=30)


def capa_cierre():
    capa = nk.glow_text(Image.new("RGB", (nk.W, nk.H)), (nk.W / 2, 820), "NEON KEYS",
                        nk.font(nk.FONT_BOLD, 130, 2), WHITE, nk.BRAND_GLOW, radius=26)
    return nk.glow_text(capa, (nk.W / 2, 980), "Sígueme para más ciencia", nk.font(nk.FONT_TEXT, 54, 0),
                        WHITE, nk.TITLE_GLOW, radius=14)


# ---------------------------------------------------------------- Audio

def suave(x, n):
    """Paso bajo sencillo (promedio móvil)."""
    return np.convolve(x, np.ones(n) / n, mode="same")


def reverb(x, segundos=2.2, mezcla=0.35):
    rng = np.random.default_rng(11)
    n = int(segundos * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (n / 5))
    ir = suave(ir, 6)
    m = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]
    wet *= np.abs(x).max() / (np.abs(wet).max() or 1)
    return x * (1 - mezcla) + wet * mezcla


def chirp(dur_total, f0, f1, t_fin, tau_min, sr=SR):
    """Tono que sube como la espiral: f ∝ τ^(-3/8), con volumen que crece ∝ f^(2/3) (como el de LIGO)."""
    t = np.arange(int(dur_total * sr)) / sr
    tc = t_fin + tau_min
    tau = np.maximum(tc - t, tau_min)
    rel = (tc / tau) ** 0.375
    rel = rel / rel.max()
    f = f0 + (f1 - f0) * (rel - rel.min()) / (rel.max() - rel.min())
    fase = 2 * np.pi * np.cumsum(f) / sr
    amp = (f / f1) ** (2 / 3)
    sig = np.sin(fase) + 0.35 * np.sin(2 * fase) + 0.15 * np.sin(3 * fase)
    sig = np.tanh(1.6 * sig) * amp
    sig[t > t_fin] = 0
    return sig, f


def render_audio(path):
    n = int(TOTAL * SR)
    t = np.arange(n) / SR
    mezcla = np.zeros(n)

    # Fondo ambiental: acordes lentos de senos desafinados (Rem → Sib → Fa → Do), crece hacia el choque.
    acordes = [(50, 53, 57, 62), (46, 50, 53, 58), (41, 48, 53, 57), (48, 52, 55, 60)]
    pad = np.zeros(n)
    for i, ac in enumerate(acordes * 2):
        t0 = i * 3.0
        a, b = int(t0 * SR), min(n, int((t0 + 3.6) * SR))
        tt = t[a:b] - t0
        env = np.minimum(1, tt / 1.2) * np.minimum(1, (3.6 - tt) / 1.0)
        for nota in ac:
            f = 440 * 2 ** ((nota - 69) / 12)
            for det in (-0.6, 0.6):
                pad[a:b] += np.sin(2 * np.pi * (f + det) * tt + 0.3 * np.sin(2 * np.pi * 0.2 * tt)) * env
    sube = np.clip(t / T_CHOQUE, 0, 1) ** 1.5
    pad *= 0.05 + 0.1 * sube
    pad *= np.interp(t, [T_CHOQUE - 0.45, T_CHOQUE], [1, 0])     # silencio justo antes del golpe
    mezcla += pad

    # El chirp de la espiral (mismo tiempo que la imagen).
    sig, _ = chirp(T_CHOQUE + 0.01, 45, 330, T_CHOQUE, TAU_MIN)
    mezcla[:len(sig)] += 0.42 * sig

    # Subida de ruido antes del choque.
    rng = np.random.default_rng(5)
    a, b = int(8.5 * SR), int(T_CHOQUE * SR)
    ruido = suave(rng.standard_normal(b - a), 3)
    mezcla[a:b] += ruido * np.linspace(0, 1, b - a) ** 3 * 0.12

    # Choque: golpe grave que cae, explosión de ruido y "ringdown" (el zumbido del agujero nuevo al calmarse).
    i0 = int(T_CHOQUE * SR)
    d = int(2.5 * SR)
    tt = np.arange(d) / SR
    f_golpe = 95 * np.exp(-tt * 2.2) + 26
    golpe = np.sin(2 * np.pi * np.cumsum(f_golpe) / SR) * np.exp(-tt * 1.4)
    explosion = suave(rng.standard_normal(d), 18) * np.exp(-tt * 2.6) * 3
    ring = np.sin(2 * np.pi * 360 * tt) * np.exp(-tt * 9) * 0.5
    brillo = sum(np.sin(2 * np.pi * f * tt) for f in (1175, 1568, 2349)) * np.exp(-tt * 1.8) * 0.05
    mezcla[i0:i0 + d] += 0.9 * golpe + 0.35 * explosion + ring + brillo

    # Después del choque: ondas que se alejan (pulsos graves espaciados) y acorde abierto y brillante.
    for k, tk in enumerate(np.arange(T_CHOQUE + 0.9, 20.3, 0.9)):
        j = int(tk * SR)
        dd = int(0.7 * SR)
        tt = np.arange(dd) / SR
        mezcla[j:j + dd] += np.sin(2 * np.pi * (55 * np.exp(-tt * 3) + 32) * tt) * np.exp(-tt * 5) * 0.35 / (
            1 + 0.25 * k)
    calma = np.zeros(n)
    a = int((T_CHOQUE + 0.4) * SR)
    tt = t[a:] - t[a]
    for nota in (41, 53, 57, 60, 65, 69):
        f = 440 * 2 ** ((nota - 69) / 12)
        calma[a:] += np.sin(2 * np.pi * f * tt + 0.4 * np.sin(2 * np.pi * 0.15 * tt))
    calma[a:] *= np.minimum(1, tt / 2.5) * 0.045
    mezcla += calma

    # "Así sonaron": el chirp otra vez, corto, como el de LIGO (de ~35 a ~250 Hz en un segundo y medio).
    t_rep, d_rep = REPETICION
    sig, _ = chirp(d_rep + 0.01, 35, 250, d_rep, 0.03)
    j = int(t_rep * SR)
    mezcla[j:j + len(sig)] += 0.5 * sig
    dd = int(0.8 * SR)
    tt = np.arange(dd) / SR
    k = j + int(d_rep * SR)
    mezcla[k:k + dd] += np.sin(2 * np.pi * 250 * tt) * np.exp(-tt * 10) * 0.3

    mezcla = reverb(mezcla)
    fade = int(1.2 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)
    mezcla[:int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))
    mezcla *= 0.89 / np.abs(mezcla).max()
    pcm = (np.stack([mezcla, mezcla], 1) * 32767).astype("<i2")
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    datos = {
        "total": TOTAL, "tChoque": T_CHOQUE, "tc": TC, "tauMin": TAU_MIN, "w0": W0, "a0": A0,
        "repeticion": list(REPETICION), "cierre": CIERRE,
        "capas": {
            "titulo": {"img": png_base64(capa_titulo()), "t0": 0.0, "t1": T_CHOQUE - 0.2},
            "textos": [{"img": png_base64(capa_texto(l, h)), "t0": a, "t1": b} for a, b, l, h in TEXTOS],
            "choque": {"img": png_base64(capa_choque()), "t0": CHOQUE_TXT[0], "t1": CHOQUE_TXT[1]},
            "marca": png_base64(nk.make_brand_layer()),
            "cierre": png_base64(capa_cierre()),
        },
    }
    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "ondas.json").write_text(json.dumps(datos))
    render_audio(tmp / "ondas.wav")
    print(tmp / "ondas.json")
    print(tmp / "ondas.wav")


if __name__ == "__main__":
    main()
