#!/usr/bin/env python3
"""Neon Keys · prueba de audio: *Firestarter* (The Prodigy) en versión electrónica, sin guitarras ni soundfont.

Solo música (~22 s) para decidir si la serie de batería por niveles (ADR-024) se pasa a electrónica. Todo sale de
síntesis: el riff (la guitarra con wah del original) es una sierra por un filtro wah que se abre y se cierra, el
breakbeat es un bombo/caja/hats "de sampler" (saturados y con poco ancho de banda, como los del big beat de los 90),
y el bajo es un reese (dos sierras desafinadas, distorsionadas). Es un cover: sirve para crecer, no para Creator
Rewards.

Uso: .venv/bin/python escenas3d/firestarter.py   # → out/.tmp/firestarter-electronica-prueba.wav

Con Surge XT (sinte de estudio gratis, cargado con DawDreamer en el entorno `.venv-synth`): el riff y el bajo salen de
presets de fábrica de Surge (`plugins/surge-xt/patches/`); la batería sigue siendo la nuestra.
    .venv-synth/bin/python escenas3d/firestarter.py --surge "Squelch" --bajo "Distorted Bass"
        # → out/.tmp/firestarter-surge-squelch-prueba.wav
"""

import argparse
import sys
from pathlib import Path

import numpy as np

_args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
_args.add_argument("--surge", help="preset de Surge XT para el riff (nombre del .fxp sin extensión)")
_args.add_argument("--bajo", default="Distorted Bass", help="preset de Surge XT para el bajo (con --surge)")
ARGS = _args.parse_args()
sys.argv = sys.argv[:1]                            # techno.py lee sus propias opciones al importarse
from techno import eco, escribir_wav, filtro  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
BPM = 141
NEGRA = 60 / BPM
COMPAS = 4 * NEGRA
SEMI = NEGRA / 4
COMPASES = 13
COLA = 2.0
N = int((COMPASES * COMPAS + COLA) * SR)
rng = np.random.default_rng(1996)                   # el año del sencillo
hz = lambda m: 440 * 2 ** ((m - 69) / 12)

# El riff (tablatura de fans): Si♭4 repetido en corcheas, luego Si♭4 – Fa♯4 – La4 que sube a Si4 (el whammy)
#   (corchea dentro de los dos compases, nota, largo en corcheas, nota a la que se desliza o None)
RIFF = [(0, 70, 1, None), (1, 70, 1, None), (2, 70, 1, None), (3, 70, 1, None), (4, 70, 1, None),
        (5, 70, 1, None), (6, 70, 1, None), (8, 70, 1, None), (9, 66, 1, None), (10, 69, 2, None),
        (12, 69, 4, 71)]

# Breakbeat de dos compases (16 semicorcheas cada uno): o = golpe, g = caja fantasma, x = hat, X = hat abierto
BREAK = [
    {"BOMBO": "o-------o-o-----", "CAJA": "----o--g----o--g", "HAT": "x-x-x-x-x-x-x-X-"},
    {"BOMBO": "o-o-------o--o--", "CAJA": "----o--g-g--o-oo", "HAT": "x-x-x-x-x-x-x-x-"},
]

# Secciones: (compás inicial, qué suena)
#   0–1: el riff solo (se reconoce desde el primer segundo) · 2–5: + breakbeat · 6: subida de ruido y redoble ·
#   7–11: todo con el bajo reese · 12: golpe final
RIFF_DESDE, BREAK_DESDE, SUBIDA, DROP, FINAL = 0, 2, 6, 7, 12


# ------------------------------------------------------------------ síntesis
def poner(destino, s, t, gan=1.0, lado=0.0):
    a = int(t * SR)
    if a >= N or a < 0:
        return
    n = min(len(s), N - a)
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


def sierra(f, t):
    """Sierra sin aliasing (suma de armónicos hasta la mitad de la frecuencia de muestreo)."""
    fase = 2 * np.pi * np.cumsum(f) / SR if np.ndim(f) else 2 * np.pi * f * t
    fmax = np.max(f)
    s = np.zeros_like(t)
    for k in range(1, int(SR / 2.2 / fmax) + 1):
        s += np.sin(k * fase) / k
    return s


def wah(x, centro):
    """Filtro pasa banda resonante (state variable) con la frecuencia que cambia muestra a muestra: el pedal wah."""
    y = np.zeros_like(x)
    bajo = banda = 0.0
    q = 0.28                                        # menos = más resonante ("uaaa")
    f = 2 * np.sin(np.pi * np.clip(centro, 60, 6000) / SR)
    for i in range(len(x)):
        alto = x[i] - bajo - q * banda
        banda += f[i] * alto
        bajo += f[i] * banda
        y[i] = banda
    return y


def nota_riff(nota, dur, desliza):
    """Una nota del riff: dos sierras un poco desafinadas → wah que se abre en el ataque → distorsión suave."""
    t = np.arange(int((dur + 0.06) * SR)) / SR
    f = np.full(len(t), hz(nota))
    if desliza:                                     # el whammy: sube un tono a la mitad de la nota
        k = np.clip((t - dur * 0.35) / 0.12, 0, 1)
        f = hz(nota) * (hz(desliza) / hz(nota)) ** k
    s = sierra(f * 1.003, t) + sierra(f * 0.997, t)
    centro = 500 + 2600 * np.exp(-t * 9) + 500 * np.sin(2 * np.pi * 5.5 * t) * (t > 0.15)
    s = wah(s, centro)
    s = np.tanh(s * 2.2)
    env = np.minimum(1, t / 0.004) * np.clip((dur + 0.06 - t) / 0.05, 0, 1)
    return s * env * 0.5


def bombo(fuerza=1.0):
    """Bombo de breakbeat: cuerpo de 60 Hz con golpe de palo arriba; saturado como sampleado de un disco."""
    t = np.arange(int(0.32 * SR)) / SR
    f = 55 + 95 * np.exp(-t * 30)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)
    s += filtro(rng.normal(0, 1, len(t)), 1200, 6000) * np.exp(-t * 180) * 0.5
    return np.tanh(2.6 * s) * fuerza


def caja(fuerza=1.0):
    """Caja gorda y sucia: parche a 190 Hz + bordonero (ruido) largo, con algo de sala."""
    t = np.arange(int(0.3 * SR)) / SR
    tono = np.sin(2 * np.pi * 190 * t * (1 + 0.3 * np.exp(-t * 50))) * np.exp(-t * 22) * 0.7
    ruido = filtro(rng.normal(0, 1, len(t)), 1200, 8000) * np.exp(-t * 14)
    return np.tanh(1.8 * (tono + ruido)) * np.minimum(1, t / 0.001) * fuerza


def hat(fuerza, abierto=False):
    dur, caida = (0.28, 12) if abierto else (0.06, 70)
    t = np.arange(int(dur * SR)) / SR
    r = filtro(rng.normal(0, 1, len(t)), 5500, 12000)
    return r * np.exp(-t * caida) * fuerza * 0.5


def reese(dur, nota):
    """Bajo reese: dos sierras desafinadas que se mueven entre sí, filtradas abajo y distorsionadas (el bajo del rave)."""
    t = np.arange(int(dur * SR)) / SR
    f = hz(nota)
    s = sierra(f * 1.008, t) + sierra(f * 0.992, t) + 0.8 * np.sin(2 * np.pi * f * t)
    s = filtro(s, 30, 520)
    s = np.tanh(2.5 * s)
    env = np.minimum(1, t / 0.01) * np.clip((dur - t) / 0.03, 0, 1)
    return s * env


def subida(dur):
    """Ruido que sube de tono y volumen durante un compás (antes del drop)."""
    t = np.arange(int(dur * SR)) / SR
    r = rng.normal(0, 1, len(t))
    partes = np.array_split(r, 16)
    salida = np.concatenate([filtro(p, 300 + 6000 * (i / 15) ** 2, 1500 + 9000 * (i / 15) ** 2)
                             for i, p in enumerate(partes)])
    return salida * (t / dur) ** 2


def impacto():
    """Golpe del drop: bombo grave largo + ruido + acorde de quinta en Si♭ que se apaga."""
    t = np.arange(int(1.6 * SR)) / SR
    f = 40 + 110 * np.exp(-t * 18)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3)
    s += filtro(rng.normal(0, 1, len(t)), 200, 9000) * np.exp(-t * 5) * 0.4
    for m in (46, 53, 58):
        s += np.tanh(2 * (sierra(hz(m) * 1.004, t) + sierra(hz(m) * 0.996, t))) * np.exp(-t * 2.2) * 0.12
    return np.tanh(1.5 * s)


def main():
    notas_riff, notas_bajo = [], []
    riff = np.zeros((N, 2))
    bat = np.zeros((N, 2))
    bajo = np.zeros((N, 2))
    fx = np.zeros((N, 2))
    corchea = NEGRA / 2

    for c in range(COMPASES):
        t0 = c * COMPAS
        # Riff (dos compases que se repiten tal cual, como el loop del original)
        if RIFF_DESDE <= c < FINAL and c % 2 == 0:
            for e, nota, largo, desliza in RIFF:
                if desliza:                              # sin pitch bend: la nota y luego a la que sube, ligadas
                    notas_riff += [(t0 + e * corchea, nota, 110, largo * corchea * 0.4),
                                   (t0 + (e + largo * 0.4) * corchea, desliza, 110, largo * corchea * 0.55)]
                else:
                    notas_riff.append((t0 + e * corchea, nota, 110, largo * corchea * 0.92))
                if not ARGS.surge:
                    s = nota_riff(nota, largo * corchea * 0.92, desliza)
                    poner(riff, s, t0 + e * corchea, 1.0, -0.25)
                    poner(riff, s, t0 + e * corchea + 0.012, 0.8, 0.35)     # doblado a la derecha
        # Breakbeat
        if BREAK_DESDE <= c < FINAL:
            patron = BREAK[c % 2]
            if c == SUBIDA:                                              # redoble de caja que se acelera
                patron = {"BOMBO": "o-------o-------", "CAJA": "o-o-o-o-oooooooo", "HAT": ""}
            for paso in range(16):
                t = t0 + paso * SEMI + (0.008 if paso % 2 else 0)        # un poquito de swing
                if patron["BOMBO"][paso:paso + 1] == "o":
                    poner(bat, bombo(), t, 1.0)
                g = patron["CAJA"][paso:paso + 1]
                if g == "o":
                    poner(bat, caja(1.0 if c != SUBIDA else 0.5 + 0.5 * paso / 15), t, 0.9, 0.05)
                elif g == "g":
                    poner(bat, caja(0.3), t, 0.9, 0.05)
                h = patron["HAT"][paso:paso + 1]
                if h in ("x", "X"):
                    poner(bat, hat(0.9 if paso % 4 == 0 else 0.6, h == "X"), t, 1.0, 0.3)
        # Bajo reese desde el drop: Si♭ grave sincopado con el bombo, baja a La al final del segundo compás
        if DROP <= c < FINAL:
            for paso, largo in ((0, 6), (6, 2), (8, 6), (14, 2)):
                nota = 33 if (c % 2 == 1 and paso == 14) else 34
                notas_bajo.append((t0 + paso * SEMI, nota, 115, largo * SEMI * 0.95))
                if not ARGS.surge:
                    poner(bajo, reese(largo * SEMI * 0.95, nota), t0 + paso * SEMI, 1.0)
    if ARGS.surge:
        from surge import tocar
        riff = tocar(notas_riff, ARGS.surge, N)
        bajo = tocar(notas_bajo, ARGS.bajo, N)
    poner(fx, subida(COMPAS), SUBIDA * COMPAS, 1.0)
    poner(fx, impacto(), DROP * COMPAS, 1.0)
    poner(fx, impacto(), FINAL * COMPAS, 1.3)

    # Mezcla: batería "de sampler" (sin agudos de más, comprimida) y un poco de sala; riff con eco corto
    bat = np.stack([filtro(bat[:, k], 35, 11000) for k in (0, 1)], 1)
    bat = np.tanh(bat * 1.6)
    bat = np.stack([eco(bat[:, k], 0.6, 0.12, 9.0, 4 + k) for k in (0, 1)], 1)
    riff = np.stack([eco(riff[:, k], 1.2, 0.18, 5.0, 8 + k) for k in (0, 1)], 1)
    nivel = lambda x: x / (np.sqrt(np.mean(x[int(DROP * COMPAS * SR):int(FINAL * COMPAS * SR)] ** 2)) + 1e-9)
    mezcla = nivel(bat) * 0.30 + nivel(riff) * 0.22 + nivel(bajo) * 0.20 + fx * 0.35
    mezcla = np.tanh(mezcla * 1.2)
    fade = int(0.8 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mezcla = mezcla / np.max(np.abs(mezcla)) * 0.89

    nombre = f"firestarter-surge-{ARGS.surge.lower().replace(' ', '-')}" if ARGS.surge else "firestarter-electronica"
    salida = RAIZ / "out" / ".tmp" / f"{nombre}-prueba.wav"
    salida.parent.mkdir(parents=True, exist_ok=True)
    escribir_wav(salida, mezcla)
    print(f"{N / SR:.1f} s → {salida}")


if __name__ == "__main__":
    main()
