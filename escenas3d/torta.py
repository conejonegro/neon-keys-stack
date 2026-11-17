"""Así se arma: la torta ahogada (prueba de 10 s). Tiempos de cada paso + música y efectos hechos con código.

La escena (escenas/torta.html) lee los mismos tiempos del JSON, así que cada golpe suena cuando cae la pieza.
Música: son alegre a 120 BPM en Sol mayor (guitarrón, vihuela rasgueada y marimba), cuerdas con Karplus-Strong.

Uso:  .venv/bin/python escenas3d/torta.py            → out/.tmp/torta-ahogada.json + .wav
Luego: cd escenas3d && node grabar.js escenas/torta.html out/pruebas/asi-se-arma/torta-ahogada-prueba.mp4 \
         --datos out/.tmp/torta-ahogada.json --audio out/.tmp/torta-ahogada.wav
"""

import json
import os
import wave

import numpy as np

SR = 44100
TOTAL = 10.0
BPM = 120
PULSO = 60 / BPM
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(RAIZ, "out", ".tmp")

# Pasos (segundos). La escena y el sonido salen de aquí.
EV = {
    "birote": 0.05,            # empieza a caer; toca la barra 0.45 s después
    "abrir": 1.35,
    "carnitas": [2.0 + i * 0.13 for i in range(10)],
    "cerrar": 3.55,
    "jarro": 4.15,             # entra el jarro; vierte de 4.55 a 5.55
    "vertir": 4.55,
    "ahogada": 5.45,
    "chile": [6.15 + i * 0.17 for i in range(5)],
    "cebolla": [7.15 + i * 0.16 for i in range(5)],
    "lista": 8.35,
}
CAIDA = 0.45                   # segundos que tarda una pieza en caer

hz = lambda m: 440 * 2 ** ((m - 69) / 12)
rng = np.random.default_rng(7)
mezcla = np.zeros((int(TOTAL * SR) + SR, 2))


def poner(s, t, vol=1.0, pan=0.0):
    i = int(t * SR)
    s = s[: len(mezcla) - i] * vol
    mezcla[i:i + len(s), 0] += s * (1 - pan) ** 0.5 / 0.7071
    mezcla[i:i + len(s), 1] += s * (1 + pan) ** 0.5 / 0.7071


def cuerda(f, dur=1.2, brillo=0.5, decae=0.996):
    """Karplus-Strong por bloques: cada periodo sale del anterior promediado."""
    n = max(2, int(SR / f))
    total = int(dur * SR)
    y = np.zeros(total + n + 1)
    ruido = rng.uniform(-1, 1, n)
    y[1:n + 1] = ruido * brillo + np.convolve(ruido, np.ones(4) / 4, "same") * (1 - brillo)
    s = n + 1
    while s < len(y):
        e = min(s + n, len(y))
        y[s:e] = decae * 0.5 * (y[s - n:e - n] + y[s - n - 1:e - n - 1])
        s = e
    out = y[1:total + 1]
    return out * np.minimum(1, np.arange(total) / (SR * 0.002))


def marimba(f, dur=0.7):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 3.9 * f * t) * np.exp(-t * 18)
    return s * np.minimum(1, t / 0.003) * np.exp(-t * 6)


def barrido(f0, f1, dur, caida=12.0):
    t = np.arange(int(dur * SR)) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * caida) * np.minimum(1, t / 0.002)


def ruido_filtrado(dur, corte, caida):
    t = np.arange(int(dur * SR)) / SR
    r = rng.uniform(-1, 1, len(t))
    a = np.exp(-2 * np.pi * corte / SR)
    y = np.zeros_like(r)
    acc = 0.0
    for i in range(len(r)):           # pasa-bajos de un polo (corto: solo efectos)
        acc = (1 - a) * r[i] + a * acc
        y[i] = acc
    return y / (np.abs(y).max() + 1e-9) * np.exp(-t * caida)


# ---------------------------------------------------------------- música
# Compases de 2 s: Sol, Do, Re7, Sol, Sol (remate)
ACORDES = [(55, [67, 71, 74]), (48, [67, 72, 76]), (50, [66, 69, 72]), (55, [67, 71, 74]), (55, [67, 71, 74])]
MELODIA = [  # (pulso, nota midi) por compás de 4 pulsos
    [(0, 79), (1, 81), (1.5, 79), (2, 83), (3, 81)],
    [(0, 79), (1, 76), (2, 79), (3, 84)],
    [(0, 81), (1, 78), (1.5, 81), (2, 84), (3, 81)],
    [(0, 83), (1, 81), (2, 79), (2.5, 81), (3, 83)],
]
for c, (bajo, acorde) in enumerate(ACORDES):
    t0 = c * 4 * PULSO
    if t0 >= TOTAL:
        break
    final = c == 4
    for p in ([0] if final else [0, 2]):
        nota = bajo if p == 0 else bajo + 7
        poner(cuerda(hz(nota - 12), 1.4, 0.3, 0.997), t0 + p * PULSO, 0.55)
    if not final:
        for p in [0.5, 1.5, 2.5, 3.5, 1.0, 3.0]:        # rasgueo de vihuela a contratiempo
            for k, n in enumerate(acorde):
                poner(cuerda(hz(n - 12), 0.5, 0.8, 0.99), t0 + p * PULSO + k * 0.012, 0.16 if p % 1 else 0.1, 0.25)
        if c < len(MELODIA):
            for p, n in MELODIA[c]:
                poner(marimba(hz(n)), t0 + p * PULSO, 0.22, -0.2)

# ---------------------------------------------------------------- efectos
def golpe():
    s = barrido(140, 45, 0.35, 10) * 0.9
    r = ruido_filtrado(0.12, 900, 30)
    s[: len(r)] += r * 0.4
    return s



poner(golpe(), EV["birote"] + CAIDA, 0.7)
poner(barrido(300, 1200, 0.18, 6) * 0.5, EV["abrir"], 0.35)                    # se abre: rechinido alegre
for i, t in enumerate(EV["carnitas"]):
    poner(barrido(700 - i * 25, 260, 0.12, 25), t + CAIDA, 0.32, rng.uniform(-0.4, 0.4))
poner(golpe(), EV["cerrar"] + 0.35, 0.45)
poner(barrido(200, 500, 0.4, 3) * 0.3, EV["jarro"], 0.3)                         # entra el jarro (fiu)
sal = ruido_filtrado(1.3, 700, 1.4)
sal *= np.minimum(1, np.arange(len(sal)) / (SR * 0.15))
poner(sal, EV["vertir"], 0.35)                                                   # la salsa
poner(golpe(), EV["ahogada"], 0.55)
for i, t in enumerate(EV["chile"]):
    poner(barrido(1100, 380, 0.14, 18), t + 0.35, 0.3, rng.uniform(-0.3, 0.3))
for i, t in enumerate(EV["cebolla"]):
    poner(barrido(520 + i * 40, 780 + i * 40, 0.22, 10), t + CAIDA, 0.25, rng.uniform(-0.3, 0.3))
for k, n in enumerate([67, 71, 74, 79, 83]):                                     # ¡lista!: arpegio + campana
    poner(marimba(hz(n), 1.0), EV["lista"] + k * 0.06, 0.3)
t = np.arange(int(1.8 * SR)) / SR
poner(np.sin(2 * np.pi * 1568 * t) * np.exp(-t * 2.5) + 0.3 * np.sin(2 * np.pi * 3920 * t) * np.exp(-t * 6),
      EV["lista"] + 0.3, 0.2)

# ---------------------------------------------------------------- salida
mezcla = mezcla[: int(TOTAL * SR)]
cola = int(0.4 * SR)
mezcla[-cola:] *= np.linspace(1, 0, cola)[:, None]
mezcla *= 0.89 / np.abs(mezcla).max()
os.makedirs(TMP, exist_ok=True)
with wave.open(os.path.join(TMP, "torta-ahogada.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mezcla * 32767).astype("<i2").tobytes())
json.dump({"total": TOTAL, "fps": 30, "caida": CAIDA, "ev": EV},
          open(os.path.join(TMP, "torta-ahogada.json"), "w", encoding="utf-8"))
print("Listo: out/.tmp/torta-ahogada.json y out/.tmp/torta-ahogada.wav")
