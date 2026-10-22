"""Sonido del personaje raro: balbuceo de pájaro (una sílaba por cada abrir del pico),
base rara de fondo y efectos. Lee el guion de src/rubberhose/guion.json y escribe un WAV
en public/ para que Remotion lo use.

Uso:  ../.venv/bin/python sonido.py [segundos] [salida.wav]
"""

import json
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
AQUI = Path(__file__).parent
GUION = json.loads((AQUI / "src/rubberhose/guion.json").read_text(encoding="utf-8"))
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
SALIDA = Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI / "public/raro-sustancia.wav"

rng = np.random.default_rng(7)
mix = np.zeros(int(SR * DUR))


def poner(señal, t, vol=1.0):
    i = int(t * SR)
    if i >= len(mix):
        return
    n = min(len(señal), len(mix) - i)
    mix[i : i + n] += señal[:n] * vol


def env(n, ataque=0.01, caida=6.0):
    t = np.arange(n) / SR
    a = np.clip(t / ataque, 0, 1)
    return a * np.exp(-t * caida)


def silaba(f0):
    """Graznido corto: armónicos con la altura cayendo, como un pájaro de caricatura."""
    n = int(0.1 * SR)
    t = np.arange(n) / SR
    f = f0 * (1.15 - 0.35 * t / t[-1]) * (1 + 0.03 * np.sin(2 * np.pi * 38 * t))
    fase = 2 * np.pi * np.cumsum(f) / SR
    s = sum(np.sin(k * fase) / k ** 1.3 for k in range(1, 7))
    clack = rng.normal(0, 1, n) * np.exp(-t * 300) * 0.6  # golpecito del pico
    return (s * 0.45 + clack) * env(n, 0.006, 14)


def bombo():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def tarola():
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    return rng.normal(0, 1, n) * np.exp(-t * 22) * 0.5 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.3


def bajo(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    # dos osciladores desafinados = bajo "borracho"
    s = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * 1.01 * t + 2 * np.sin(2 * np.pi * 3 * t))
    s = np.convolve(s, np.ones(40) / 40, mode="same")  # suavizar
    return s * env(n, 0.01, 2.5)


def pop():
    n = int(0.15 * SR)
    t = np.arange(n) / SR
    f = 300 + 900 * t / t[-1]
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 25)


def boing():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 180 * (1 + 0.5 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)


def zumbido(dur=0.35, sube=True):
    """Whoosh: ruido filtrado que barre de grave a agudo (o al revés)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ruido = rng.normal(0, 1, n)
    corte = np.linspace(0.02, 0.35, n) if sube else np.linspace(0.35, 0.02, n)
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):  # pasa-bajos de un polo con corte que cambia
        acc += corte[i] * (ruido[i] - acc)
        y[i] = acc
    return y * np.sin(np.pi * t / dur) ** 2 * 2.5


def impacto():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 40 + 120 * np.exp(-t * 25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) + rng.normal(0, 1, n) * np.exp(-t * 30) * 0.4


# Entrada: sube volando y aterriza
poner(zumbido(0.3), 0.0, 0.5)
poner(impacto(), 0.28, 0.5)

# Base: 96 bpm, bajo en La menor con notas raras
BPM = 96
pulso = 60 / BPM
notas = [55, 55, 65.4, 61.7, 55, 82.4, 77.8, 73.4]
k = 0
t = 0.0
while t < DUR:
    poner(bombo(), t, 0.55)
    if k % 2 == 1:
        poner(tarola(), t, 0.35)
    poner(bajo(notas[k % len(notas)], pulso * 0.9), t, 0.18)
    k += 1
    t += pulso

# Balbuceo sincronizado con el pico (mismas sílabas que calcula Raro.tsx)
sps = GUION["silabasPorSegundo"]
for i, fr in enumerate(GUION["frases"]):
    base = 520 + 60 * i
    for s in range(int(fr["habla"] * sps)):
        f0 = base * rng.uniform(0.8, 1.35)
        poner(silaba(f0), fr["inicio"] + s / sps, 0.5)
    if i > 0:  # cambio de pose y cámara
        poner(zumbido(0.25, sube=False), fr["inicio"] - 0.05, 0.35)
    if fr.get("objeto"):  # el objeto entra volando
        poner(zumbido(0.4), fr["inicio"] + 0.2, 0.4)
    if fr.get("objeto") == "jeringa":
        poner(pop(), fr["inicio"] + 0.5, 0.5)
    if fr.get("objeto") == "diez":
        poner(impacto(), fr["inicio"] + 0.45, 0.6)
        poner(boing(), fr["inicio"] + 0.5, 0.4)

# Fundido al final y normalizar
fade = int(0.4 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)
mix = mix / np.max(np.abs(mix)) * 0.85
SALIDA.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(SALIDA), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print(f"Sonido listo: {SALIDA}")
