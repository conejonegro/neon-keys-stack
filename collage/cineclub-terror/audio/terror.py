"""Sonido de "Temporada de Terror" (Cineclub Forever), 15 s, hecho con código.

Reusa el soundfont y los ayudantes de collage/musica/terror.py (cuerdas, chelo, caja de música, trémolo, latido,
reverb). Encima: proyector (zumbido y traqueteo), papel que se rasga en cada corte, golpes en los estampados y un
pizzicato que sube con las letras de "TODO OCTUBRE". Los tiempos son los de hf/index.html.

Uso: ../../.venv/bin/python audio/terror.py hf/assets/terror.wav
"""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "musica"))
import terror as T  # noqa: E402

SR = T.SR
DUR = 15.0
N = int(DUR * SR)
T.N = N                                   # los ayudantes del módulo generan N muestras
rng = np.random.default_rng(1968)
CAJA, CHELO, CUERDAS, TREMOLO, PIZZ, PIANO = 10, 42, 48, 44, 45, 0

# cortes (deben coincidir con index.html)
DESTELLOS = [1.6, 6.4, 12.6]
RASGOS = [4.0, 8.6, 10.8]


def env(n, ataque, caida):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(ataque, 1e-4)) * np.exp(-t / caida)


def poner(pista, t0, s, g=1.0):
    a = int(t0 * SR)
    s = s if s.ndim == 2 else np.stack([s, s], 1)
    b = min(N, a + len(s))
    pista[a:b] += s[: b - a] * g


def golpe_grave(f0=55, dur=1.2):
    t = np.arange(int(dur * SR)) / SR
    f = f0 + 60 * np.exp(-t * 25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)


def clic(dur=0.03):
    return T.filtro(rng.normal(0, 1, int(dur * SR)) * env(int(dur * SR), 0.0005, 0.006), 1500, 9000)


def rasgadura(dur=0.5):
    """Papel que se rompe: ruido con crujidos irregulares que se apaga."""
    n = int(dur * SR)
    crujidos = (rng.random(n) > 0.82) * rng.normal(0, 1, n)
    grano = np.repeat(rng.random(n // 220 + 1), 220)[:n] ** 3        # tirones del papel
    s = T.filtro(crujidos * grano, 900, 7000) * np.minimum(1, np.arange(n) / (0.02 * SR)) * np.exp(-np.arange(n) / (0.28 * SR))
    return s / np.max(np.abs(s))


def soplo(dur=0.22):
    """Las dos mitades de la hoja que se cierran: un soplo que crece."""
    n = int(dur * SR)
    s = T.filtro(rng.normal(0, 1, n), 200, 2500) * (np.arange(n) / n) ** 2
    return s / np.max(np.abs(s))


def proyector():
    t = np.arange(N) / SR
    zumbido = 0.5 * np.sin(2 * np.pi * 50 * t) + 0.25 * np.sin(2 * np.pi * 100 * t) + 0.1 * np.sin(2 * np.pi * 150 * t)
    traqueteo = np.zeros(N)
    for k in np.arange(0, DUR, 1 / 24):                                  # 24 cuadros por segundo
        a = int(k * SR)
        c = clic(0.012) * (0.6 + 0.4 * rng.random())
        traqueteo[a:a + len(c)] += c[: N - a]
    s = zumbido * 0.04 + T.filtro(traqueteo, 600, 5000) * 0.05
    return s * np.minimum(1, t / 0.4)


def mezclar():
    m = np.zeros((N, 2))
    t = np.arange(N) / SR

    # base: cuerdas graves en Re y un chelo que se queda
    cuerdas = T.soundfont(CUERDAS, [(0.3, 38, 12.2, 34), (0.3, 45, 12.2, 28), (4.0, 50, 8.5, 26), (8.6, 51, 4.0, 22)])
    m += cuerdas * 0.55 * np.minimum(1, t / 1.5)[:, None]
    m += T.soundfont(CHELO, [(4.55, 38, 2.4, 70), (4.55, 39, 2.4, 60), (8.6, 38, 4.0, 58)]) * 0.55

    # Rosemary: caja de música desafinada (canción de cuna)
    cuna = [(1.75, 81, 0.5, 60), (2.15, 79, 0.5, 56), (2.55, 77, 0.5, 56), (2.95, 76, 0.5, 52), (3.35, 74, 1.0, 54)]
    caja = T.soundfont(CAJA, cuna)
    m += T.filtro(T.desafinar(caja, -18) * 0.6 + T.desafinar(caja, 14) * 0.5, 200, 7000) * 0.5

    # Possession: pizzicato que sube con cada letra de TODO (6.75…) y OCTUBRE (7.05…)
    letras = [(6.75 + 0.07 * i, 62 + i, 0.3, 80) for i in range(4)] + [(7.05 + 0.07 * i, 66 + i, 0.3, 84) for i in range(7)]
    m += T.soundfont(PIZZ, letras) * 0.7

    # The Substance → patrocinador: trémolo disonante que crece hasta el cierre
    trem = T.soundfont(TREMOLO, [(8.6, 69, 4.0, 40), (8.6, 70, 4.0, 36), (10.8, 73, 1.8, 34), (10.8, 74, 1.8, 30)])
    m += trem * (np.clip((t - 8.6) / 3.5, 0, 1) ** 1.4)[:, None] * 0.8 * (t < 12.6)[:, None]

    # cierre: acorde de piano grave y la cuna otra vez, más lenta
    piano = T.soundfont(PIANO, [(12.62, 38, 2.4, 70), (12.62, 45, 2.4, 60), (12.62, 50, 2.4, 56), (12.62, 53, 2.4, 52)])
    m += T.filtro(T.desafinar(piano, -8), 50, 3000) * 0.7
    fin = T.soundfont(CAJA, [(12.9, 81, 0.6, 50), (13.35, 77, 0.6, 46), (13.8, 74, 1.2, 46)])
    m += T.filtro(T.desafinar(fin, -15), 200, 7000) * 0.45

    # latido de 4 a 12.6 s, cada vez más rápido
    k, tl = 0, 4.0
    while tl < 12.4:
        poner(m, tl, T.filtro(T.latido(), 20, 300), 0.5 + 0.3 * (tl - 4) / 8.4)
        tl += 0.95 - 0.35 * (tl - 4) / 8.4
        k += 1

    m = T.reverb(m, segundos=3.5, mezcla=0.35)

    # efectos secos (después de la reverb, para que peguen)
    fx = np.zeros((N, 2))
    poner(fx, 0.04, clic(0.05), 0.9)                                     # se enciende el proyector
    for d in DESTELLOS:
        poner(fx, d, clic(0.04), 0.8)
        poner(fx, d, golpe_grave(48, 1.4), 0.9)
    for r in RASGOS:
        poner(fx, r - 0.24, soplo(), 0.35)
        poner(fx, r - 0.04, golpe_grave(70, 0.4), 0.5)                   # las mitades chocan
        poner(fx, r + 0.04, rasgadura(0.55), 0.55)
    poner(fx, 1.6, golpe_grave(60, 0.6), 0.4)                            # cae el perfil
    poner(fx, 6.4, golpe_grave(62, 0.5), 0.5)                            # la franja azul golpea
    poner(fx, 9.0, golpe_grave(80, 0.35), 0.7)                           # se estampan los ojos
    poner(fx, 9.0, rasgadura(0.15), 0.3)
    poner(fx, 9.38, golpe_grave(66, 0.35), 0.45)
    poner(fx, 9.62, golpe_grave(58, 0.45), 0.6)
    poner(fx, 11.05, rasgadura(0.2), 0.3)                                # el pedazo negro
    rasp = T.filtro(rng.normal(0, 1, int(1.6 * SR)), 2500, 7000) * np.sin(np.linspace(0, np.pi, int(1.6 * SR))) ** 2
    poner(fx, 10.85, rasp / np.max(np.abs(rasp)), 0.08)                  # uñas que raspan
    pr = proyector()
    fx += np.stack([pr, np.roll(pr, 331)], 1)

    m = m / (np.percentile(np.abs(m), 99.9) / 0.6) + fx
    m *= np.clip((DUR - t) / 0.35, 0, 1)[:, None]                        # fundido final con el parpadeo
    m = np.tanh(m * 1.1)
    return m / np.max(np.abs(m)) * 0.9


if __name__ == "__main__":
    salida = sys.argv[1]
    s = mezclar()
    with wave.open(salida, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((s * 32767).astype("<i2").tobytes())
    print(f"Listo: {salida} ({len(s) / SR:.1f} s)")
