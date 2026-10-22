"""Trip hop melancólico y de terror para Cineclub Forever (20 s), al estilo Portishead / Massive Attack.

84 BPM, 7 compases. Breakbeat polvoso sintetizado (bombo grave, caja con reverb, hi-hats con swing, saturado y con
poco ancho de banda, como sampleado de un disco), sub-bajo que se desliza, piano real opaco y desafinado y cuerdas del
soundfont del proyecto, theremín grave con eco, crujido de vinil y cinta ondulada.
Comparte las herramientas de terror.py (soundfont, filtros, reverb, cinta).

Uso: .venv/bin/python collage/musica/triphop.py out/.tmp/cineclub-fondo-triphop-prueba.wav
"""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import terror as T  # noqa: E402

SR = T.SR
BPM = 84
BEAT = 60 / BPM
BAR = 4 * BEAT
COMPASES = 7
DUR = COMPASES * BAR                 # 20 s
COLA = 3.5
N = int((DUR + COLA) * SR)
T.N = N                              # terror.py usa N para el largo de sus pistas
rng = np.random.default_rng(1994)    # el año de "Dummy"
hz = lambda m: 440 * 2 ** ((m - 69) / 12)

# por compás: raíz del bajo y acorde (ciclo de 4)
CICLO = [
    (38, [50, 53, 57, 60]),    # Rem7
    (36, [48, 53, 57, 60]),    # Rem/Do
    (34, [46, 50, 53, 57]),    # Si♭maj7
    (33, [45, 49, 52, 55]),    # La7
]
# theremín: (compás, tiempo, nota, duración en tiempos)
THEREMIN = [(2, 0, 62, 1.5), (2, 1.5, 65, 0.5), (2, 2, 64, 2),
            (3, 0, 61, 3), (3, 3, 57, 1),
            (4, 0, 62, 1), (4, 1, 69, 2.5), (4, 3.5, 67, 0.5),
            (5, 0, 65, 2), (5, 2, 64, 1), (5, 3, 61, 1),
            (6, 0, 62, 4)]


def poner(destino, s, t, gan=1.0, lado=0.0):
    a = int(t * SR)
    if a < 0:
        s, a = s[-a:], 0
    if a >= N:
        return
    n = min(len(s), N - a)
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


# ------------------------------------------------------------------ batería (sintetizada y ensuciada)
def bombo():
    t = np.arange(int(0.6 * SR)) / SR
    f = 44 + 90 * np.exp(-t * 22)
    cuerpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)
    clic = T.filtro(rng.normal(0, 1, len(t)), 800, 4000) * np.exp(-t * 180) * 0.4
    return np.tanh((cuerpo + clic) * 2.2)


def caja():
    t = np.arange(int(0.5 * SR)) / SR
    ruido = T.filtro(rng.normal(0, 1, len(t)), 700, 7000) * np.exp(-t * 11)
    tono = np.sin(2 * np.pi * (200 + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 18)
    return np.tanh((ruido * 1.0 + tono * 0.7) * 1.8)


def hat(abierto=False):
    t = np.arange(int((0.35 if abierto else 0.08) * SR)) / SR
    r = T.filtro(rng.normal(0, 1, len(t)), 6000, 14000)
    return r * np.exp(-t * (9 if abierto else 55))


def latido():
    return T.latido()


def bateria():
    b = np.zeros((N, 2))
    sw = 0.09 * BEAT                       # swing de las semicorcheas
    for c in range(1, COMPASES):
        t0 = c * BAR
        ultimo = c == COMPASES - 1
        # bombo: 1, "a" del 2 y el 3 y medio (boom … bap)
        for tb, g in ((0, 1.0), (1.75, 0.7), (2.5, 0.85)):
            if ultimo and tb > 0:
                continue
            poner(b, bombo(), t0 + tb * BEAT + (sw if tb % 0.5 else 0), 0.7 * g)
        if not ultimo:
            for tc in (1, 3):
                poner(b, caja(), t0 + tc * BEAT, 0.42, 0.08)
            # caja fantasma suave antes del 3
            poner(b, caja(), t0 + 2.75 * BEAT + sw, 0.09, -0.1)
        for k in range(8):
            if ultimo and k > 1:
                break
            abierto = k == 7 and c % 2 == 0
            poner(b, hat(abierto), t0 + k * BEAT / 2 + (sw if k % 2 else 0), (0.10 if k % 2 else 0.14) * (1.4 if abierto else 1), 0.3)
    # "sampleado de disco": poco ancho de banda, saturación y bits de menos
    b = T.filtro(b, 45, 7500)
    b = np.tanh(b * 1.6) / 1.2
    b = np.round(b * 48) / 48
    # reverb corta solo para la caja y el bombo (la sala del breakbeat)
    return T.reverb(b, segundos=1.4, mezcla=0.22, semilla=5)


# ------------------------------------------------------------------ bajo y theremín (numpy)
def sub(m, dur, desde=None):
    t = np.arange(int(dur * SR)) / SR
    f = hz(m) if desde is None else hz(desde) + (hz(m) - hz(desde)) * np.minimum(1, t / 0.12)
    fase = 2 * np.pi * np.cumsum(f) / SR
    s = np.tanh((np.sin(fase) + 0.2 * np.sin(2 * fase)) * 1.6)
    return s * np.minimum(1, t / 0.02) * np.exp(-t * 0.7) * np.minimum(1, (dur - t) / 0.08)


def theremin():
    """Sinusoide con glissando entre notas y vibrato que crece; registro grave para que no chille."""
    n = N
    curva = np.full(n, np.nan)
    previo = THEREMIN[0][2]
    for c, b, m, d in THEREMIN:
        a, z = int((c * BAR + b * BEAT) * SR), int((c * BAR + (b + d) * BEAT) * SR)
        k = np.minimum(1, np.arange(z - a) / (0.16 * SR))
        k = k * k * (3 - 2 * k)
        curva[a:z] = previo + (m - previo) * k
        previo = m
    vivo = ~np.isnan(curva)
    curva = np.where(vivo, curva, previo)
    t = np.arange(n) / SR
    vib = 0.3 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, np.maximum(0, t - 2 * BAR) / 2)
    fase = 2 * np.pi * np.cumsum(hz(curva + vib)) / SR
    s = np.sin(fase) + 0.1 * np.sin(2 * fase)
    a0, a1 = 2 * BAR, 7 * BAR
    env = np.clip((t - a0) / 0.8, 0, 1) * np.clip((a1 - t) / 2.0, 0, 1)
    return s * env


def eco_pingpong(x, retardo, realim=0.5, veces=6):
    y = x.copy()
    d = int(retardo * SR)
    for k in range(1, veces + 1):
        y[d * k:, k % 2] += (x[:-d * k, 0] + x[:-d * k, 1]) * 0.5 * realim ** k
    return y


# ------------------------------------------------------------------ arreglo
def arreglo():
    tc = lambda c, b=0: c * BAR + b * BEAT
    acordes, cuerdas_notas, bajo = [], [], np.zeros((N, 2))
    for c in range(COMPASES):
        raiz, ac = CICLO[c % 4]
        # piano: acorde suave en el 1 y repetido en el "y" del 3 (más bajito)
        acordes += [(tc(c) + i * 0.025, m, BAR * 0.6, 40) for i, m in enumerate(ac)]
        acordes += [(tc(c, 2.5) + i * 0.02, m, BEAT * 1.4, 28) for i, m in enumerate(ac[1:])]
        cuerdas_notas += [(tc(c), m - 12, BAR * 1.02, 24) for m in ac[:2]]
        if c >= 1:
            siguiente = CICLO[(c + 1) % 4][0]
            poner(bajo, sub(raiz, BAR * 0.72), tc(c), 0.5)
            poner(bajo, sub(siguiente, BAR * 0.26, desde=raiz), tc(c, 2.95), 0.4)   # se desliza al siguiente
    piano = T.soundfont(T.PIANO, acordes)
    piano = T.desafinar(piano, -8) * 0.6 + T.desafinar(piano, 10) * 0.45
    piano = T.filtro(piano, 70, 2400)
    cuerdas = T.soundfont(T.CUERDAS, cuerdas_notas)
    tremolo = T.soundfont(T.TREMOLO, [(tc(4), 69, BAR * 2.9, 26), (tc(4), 70, BAR * 2.9, 22)])
    tremolo *= np.clip((np.arange(N) / SR - tc(4)) / (BAR * 2.4), 0, 1)[:, None] ** 1.5
    th = np.zeros((N, 2))
    poner(th, theremin(), 0, 0.16, -0.1)
    th = T.reverb(eco_pingpong(th, BEAT * 0.75, 0.42), segundos=3.5, mezcla=0.45, semilla=8)

    armonia = T.reverb(piano * 1.0 + cuerdas * 0.45 + tremolo * 0.5, segundos=4.0, mezcla=0.38)
    mezcla = armonia * 2.0 + bateria() * 1.0 + T.filtro(bajo, 25, 900) * 1.0 + th
    mezcla /= np.percentile(np.abs(mezcla), 99.95) / 0.8
    mezcla[:, 0] += T.vinil()[:N] * 1.3
    mezcla[:, 1] += np.roll(T.vinil()[:N], 7919) * 1.3
    mezcla = T.cinta(mezcla, prof=0.0025, vel=0.18)
    t = np.arange(N) / SR
    mezcla *= (np.minimum(1, t / 0.25) * np.clip((DUR + COLA - t) / 3.0, 0, 1))[:, None]
    mezcla = np.tanh(mezcla * 1.15)
    return mezcla / np.max(np.abs(mezcla)) * 0.89


if __name__ == "__main__":
    salida = sys.argv[1]
    s = arreglo()
    with wave.open(salida, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((s * 32767).astype("<i2").tobytes())
    print(f"Listo: {salida} ({len(s) / SR:.1f} s)")
