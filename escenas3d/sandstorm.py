#!/usr/bin/env python3
"""Neon Keys · prueba de audio: *Sandstorm* (Darude) en versión electrónica con Surge XT (ADR-026).

Solo música (~25 s) para la batería por niveles en electrónica (ADR-024). El riff y el bajo salen de presets de Surge
XT; la batería es la del techno (bombo four on the floor, clap, hats) con un redoble de caja en la subida.
Mi menor a 136 BPM; el riff (semicorcheas) va Si – Si – Mi – Re – La, sobre Em – Am – G – D. Es un cover: sirve para
crecer, no para Creator Rewards.

Uso: .venv-synth/bin/python escenas3d/sandstorm.py [--lead Distortionworks] [--bajo "Bass 1"]
    # → out/.tmp/sandstorm-<lead>-prueba.wav
"""

import argparse
import sys
from pathlib import Path

import numpy as np

_args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
_args.add_argument("--lead", default="Distortionworks", help="preset de Surge XT para el riff")
_args.add_argument("--bajo", default="Bass 1", help="preset de Surge XT para el bajo")
_args.add_argument("--pad", default="Super", help="preset de Surge XT para los acordes del drop")
ARGS = _args.parse_args()
sys.argv = sys.argv[:1]                            # techno.py lee sus propias opciones al importarse
import techno  # noqa: E402
from surge import tocar  # noqa: E402
from techno import clap, eco, escribir_wav, filtro, hat, kick  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
BPM = 136
NEGRA = 60 / BPM
COMPAS = 4 * NEGRA
SEMI = NEGRA / 4
COMPASES = 14
COLA = 2.5
N = int((COMPASES * COMPAS + COLA) * SR)
techno.N = N                                        # poner() de techno.py usa su N
rng = np.random.default_rng(1999)                   # el año del sencillo

# El riff: dos compases (32 semicorcheas). (semicorchea donde empieza, nota, cuántas seguidas, la última larga)
#   Si×5 · Si×7 · Mi×7 · Re×7 · La×2 (cada grupo cierra con una corchea)
RIFF = [(0, 71, 5), (6, 71, 7), (14, 76, 7), (22, 74, 7), (30, 69, 2)]
# Acorde bajo cada grupo del riff: (semicorchea, nota grave)
ACORDES = [(0, 40), (14, 45), (22, 43), (30, 38)]               # Mi, La, Sol, Re
PAD = {40: (52, 55, 59, 64), 45: (52, 57, 60, 64), 43: (50, 55, 59, 62), 38: (50, 54, 57, 62)}

# Secciones (compases): riff con bombo desde el segundo 0 · + clap, hats y bajo · subida con redoble · drop · final
CLAP_DESDE, SUBIDA, DROP, FINAL = 2, 6, 8, 13


def main():
    lead, bajo, pad = [], [], []
    bat = np.zeros((N, 2))
    fx = np.zeros((N, 2))
    for c in range(COMPASES):
        t0 = c * COMPAS
        mitad = c % 2                                               # el riff dura dos compases
        if c < FINAL:
            for s0, nota, veces in RIFF:
                for k in range(veces):
                    s = s0 + k
                    if s // 16 != mitad:
                        continue
                    larga = k == veces - 1 and veces > 2
                    lead.append((t0 + (s % 16) * SEMI, nota, 112 if k == 0 else 100, SEMI * (1.9 if larga else 0.85)))
            for i, (s0, raiz) in enumerate(ACORDES):
                fin = ACORDES[i + 1][0] if i + 1 < len(ACORDES) else 32
                for s in range(s0, fin):
                    if s // 16 != mitad or c < CLAP_DESDE:
                        continue
                    if s % 4 == 2:                                  # bajo de trance: en el contratiempo
                        bajo.append((t0 + (s % 16) * SEMI, raiz, 110, SEMI * 1.6))
                if c >= DROP and s0 // 16 == mitad:
                    largo = (fin - s0) * SEMI
                    for nota in PAD[raiz]:
                        pad.append((t0 + (s0 % 16) * SEMI, nota, 90, largo * 0.98))

        # Batería
        for paso in range(16):
            t = t0 + paso * SEMI
            if c >= FINAL:
                break
            subiendo = SUBIDA <= c < DROP
            if paso % 4 == 0 and not (c == DROP - 1 and paso >= 8):
                techno.poner(bat, kick(), t, 1.0)
            if c >= CLAP_DESDE and not subiendo and paso in (4, 12):
                techno.poner(bat, clap(), t, 0.8, 0.05)
            if c >= CLAP_DESDE and paso % 4 == 2:
                techno.poner(bat, hat(1.0, True), t, 0.7, 0.3)
            if c >= DROP and paso % 2 == 1:
                techno.poner(bat, hat(0.6), t, 0.8, -0.3)
            # Redoble de la subida: negras → corcheas → semicorcheas
            if subiendo:
                k = (c - SUBIDA) * 16 + paso
                cada = 4 if k < 8 else 2 if k < 20 else 1
                if paso % cada == 0:
                    techno.poner(bat, clap(), t, 0.4 + 0.5 * k / 31, 0.05)

    # Subida de ruido (dos compases) y golpes en el drop y el final
    t = np.arange(int(2 * COMPAS * SR)) / SR
    partes = np.array_split(rng.normal(0, 1, len(t)), 24)
    ruido = np.concatenate([filtro(p, 300 + 7000 * (i / 23) ** 2, 1500 + 10000 * (i / 23) ** 2)
                            for i, p in enumerate(partes)]) * (t / t[-1]) ** 2
    techno.poner(fx, ruido, SUBIDA * COMPAS, 0.5)
    for tc in (DROP, FINAL):
        techno.poner(fx, filtro(rng.normal(0, 1, int(2 * SR)), 3000, 14000) * np.exp(-np.arange(int(2 * SR)) / SR * 2.5),
                     tc * COMPAS, 0.35)                              # platillo
        techno.poner(fx, kick(), tc * COMPAS, 1.2)
    final = [(FINAL * COMPAS, n, 120, COLA) for n in (40, 52, 59, 64, 71)]

    print("Surge:", ARGS.lead, "/", ARGS.bajo, "/", ARGS.pad)
    lead = tocar(lead + final[3:], ARGS.lead, N)
    bajo = tocar(bajo + final[:1], ARGS.bajo, N)
    pad = tocar(pad + final[1:], ARGS.pad, N)

    # Mezcla: bombo y bajo se turnan (el bajo en el contratiempo); el lead con eco al tempo
    a, b = int(DROP * COMPAS * SR), int(FINAL * COMPAS * SR)
    nivel = lambda x: x / (np.sqrt(np.mean(x[a:b] ** 2)) + 1e-9)
    lead = techno.ping_pong(lead, NEGRA * 0.75, 0.3, 4)
    bat = np.stack([eco(bat[:, k], 0.8, 0.1, 8.0, 3 + k) for k in (0, 1)], 1)
    mezcla = nivel(bat) * 0.30 + nivel(lead) * 0.26 + nivel(bajo) * 0.18 + nivel(pad) * 0.10 + fx * 0.4
    mezcla = np.tanh(mezcla * 1.2)
    fade = int(1.0 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mezcla = mezcla / np.max(np.abs(mezcla)) * 0.89

    salida = RAIZ / "out" / ".tmp" / f"sandstorm-{ARGS.lead.lower().replace(' ', '-')}-prueba.wav"
    salida.parent.mkdir(parents=True, exist_ok=True)
    escribir_wav(salida, mezcla)
    print(f"{N / SR:.1f} s → {salida}")


if __name__ == "__main__":
    main()
