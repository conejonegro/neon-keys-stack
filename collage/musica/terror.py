"""Música de fondo melancólica y de terror para Cineclub Forever (20 s).

Instrumentos reales del soundfont del proyecto (FluidR3Mono, vía TinySoundFont): piano viejo (dos capas un poco
desafinadas, opaco), caja de música, chelo, cuerdas y cuerdas en trémolo. El resto con numpy: latido, cinta que se
ondula, crujido de vinil y reverb. 72 BPM, Re menor, bajo en lamento cromático Re–Do#–Do–Si–Si♭–La.

Uso: .venv/bin/python collage/musica/terror.py out/.tmp/cineclub-fondo-terror-prueba.wav
"""
import sys
import wave
from pathlib import Path

import numpy as np
import tinysoundfont

RAIZ = Path(__file__).resolve().parents[2]
SF = RAIZ / "soundfonts" / "FluidR3Mono_GM.sf3"
SR = 44100
BPM = 72
BEAT = 60 / BPM
BAR = 4 * BEAT
COMPASES = 6
DUR = COMPASES * BAR                 # 20 s
COLA = 4.0
N = int((DUR + COLA) * SR)
rng = np.random.default_rng(1922)

# programas General MIDI
PIANO, CAJA, CHELO, CUERDAS, TREMOLO = 0, 10, 42, 48, 44

# por compás: bajo (lamento cromático) y acorde de la mano izquierda
COMPAS = [
    (38, [50, 53, 57]),        # Rem
    (37, [49, 53, 57]),        # Rem/Do#  (Re menor con séptima mayor en el bajo)
    (36, [48, 53, 57]),        # Rem7/Do
    (35, [47, 53, 56]),        # Si semidisminuido (Si Fa La♭... tensión)
    (34, [46, 50, 53]),        # Si♭
    (33, [45, 49, 52, 55]),    # La7 (pide volver a Re)
]
# melodía (compás, tiempo, nota, duración en tiempos, fuerza): pocas notas, mucho silencio
MELODIA = [
    (0, 1, 69, 1.5, 52), (0, 2.5, 65, 0.5, 40), (0, 3, 64, 1, 46),
    (1, 0, 62, 2, 50), (1, 3, 61, 1, 42),
    (2, 0, 69, 1, 50), (2, 1, 72, 2, 56), (2, 3, 70, 1, 44),
    (3, 0, 69, 1.5, 50), (3, 1.5, 68, 1.5, 46),
    (4, 0, 65, 1, 46), (4, 1, 70, 2, 54), (4, 3, 69, 1, 44),
    (5, 0, 67, 1, 44), (5, 1, 64, 1, 42), (5, 2, 61, 2, 40),
]


def soundfont(programa, notas, ganancia=1.0):
    """notas: [(t, midi, dur, fuerza)] → audio estéreo float con el instrumento del soundfont."""
    synth = tinysoundfont.Synth(samplerate=SR)
    sfid = synth.sfload(str(SF))
    synth.program_select(0, sfid, 0, programa)
    eventos = sorted([(t, 1, m, v) for t, m, d, v in notas] + [(t + d, 0, m, 0) for t, m, d, v in notas])
    partes, cursor = [], 0.0
    for t, on, m, v in eventos:
        n = int(round((t - cursor) * SR))
        if n > 0:
            partes.append(np.frombuffer(synth.generate(n), dtype=np.float32).copy())
            cursor += n / SR
        if on:
            synth.noteon(0, m, v)
        else:
            synth.noteoff(0, m)
    resto = N - int(round(cursor * SR))
    partes.append(np.frombuffer(synth.generate(max(0, resto)), dtype=np.float32).copy())
    audio = np.concatenate(partes).reshape(-1, 2)[:N].astype(np.float64)
    return np.pad(audio, ((0, N - len(audio)), (0, 0))) * ganancia


def filtro(x, bajo=20, alto=20000):
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    curva = (1 / (1 + (bajo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / alto) ** 4))
    return np.fft.irfft(X * (curva[:, None] if x.ndim == 2 else curva), len(x), axis=0)


def desafinar(x, cents):
    """Cambia la afinación unos cents remuestreando (como un piano viejo que ya no está a tono)."""
    k = 2 ** (cents / 1200)
    idx = np.arange(len(x)) * k
    return np.stack([np.interp(idx, np.arange(len(x)), x[:, c], right=0) for c in range(2)], axis=1)


def reverb(x, segundos=4.5, mezcla=0.42, semilla=3):
    r = np.random.default_rng(semilla)
    t = np.arange(int(segundos * SR)) / SR
    salida = np.zeros_like(x)
    for c in range(2):
        ir = filtro(r.normal(0, 1, len(t)) * np.exp(-t * 1.5), 150, 5000)
        ir /= np.sqrt(np.sum(ir ** 2))
        m = 1 << (len(x) + len(ir) - 1).bit_length()
        salida[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], m) * np.fft.rfft(ir, m), m)[: len(x)]
    return x * (1 - mezcla) + salida * mezcla * 2.4


def cinta(x, prof=0.0035, vel=0.21):
    t = np.arange(len(x)) / SR
    desfase = prof * (np.sin(2 * np.pi * vel * t) + 0.4 * np.sin(2 * np.pi * vel * 2.3 * t + 0.7))
    idx = np.clip(np.arange(len(x)) + desfase * SR, 0, len(x) - 1)
    return np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)


def latido():
    """Un "lub-dub" grave y apagado."""
    t = np.arange(int(0.9 * SR)) / SR
    golpe = lambda t0, g: np.where(t >= t0, np.sin(2 * np.pi * np.cumsum(40 + 25 * np.exp(-(t - t0).clip(0) * 20)) / SR) * np.exp(-(t - t0).clip(0) * 9) * g, 0)
    return golpe(0, 1.0) + golpe(0.22, 0.65)


def vinil():
    s = filtro(rng.normal(0, 1, N), 300, 4000) * 0.008
    return s + filtro((rng.random(N) > 0.9995) * rng.normal(0, 1, N) * 0.06, 1200, 8000)


def arreglo():
    t0 = lambda c, b=0: c * BAR + b * BEAT
    izq = [(t0(c) + i * 0.03, m, BAR * 0.98, 34) for c, (_, ac) in enumerate(COMPAS) for i, m in enumerate(ac)]
    mel = [(t0(c, b), m, d * BEAT, v) for c, b, m, d, v in MELODIA]
    piano = soundfont(PIANO, izq + mel)
    piano = desafinar(piano, -7) * 0.6 + desafinar(piano, 9) * 0.5      # dos capas fuera de tono
    piano = filtro(piano, 60, 2600)                                      # opaco, sin brillo
    caja = filtro(soundfont(CAJA, [(t + 0.02, m + 12, d, int(v * 0.6)) for t, m, d, v in mel if t >= t0(2)]), 200, 6000)
    chelo = soundfont(CHELO, [(t0(c), b, BAR * 1.02, 46) for c, (b, _) in enumerate(COMPAS)])
    cuerdas = soundfont(CUERDAS, [(0, 38, DUR, 30), (0, 45, DUR, 26), (t0(2), 50, DUR - t0(2), 22)])
    # disonancia que crece: trémolo en medio tono (La / Si♭ y luego Do# / Re)
    tremolo = soundfont(TREMOLO, [(t0(3), 69, BAR * 2.9, 28), (t0(3), 70, BAR * 2.9, 24), (t0(4, 2), 73, BAR * 1.4, 26), (t0(4, 2), 74, BAR * 1.4, 22)])
    rampa = np.clip((np.arange(N) / SR - t0(3)) / (BAR * 2.5), 0, 1)[:, None]
    tremolo *= rampa ** 1.5

    mezcla = piano * 1.0 + caja * 0.35 + chelo * 0.55 + cuerdas * 0.5 + tremolo * 0.6
    # latido al final (compases 5 y 6)
    lat = np.zeros((N, 2))
    for k in range(8):
        a = int((t0(4) + k * BEAT) * SR)
        s = latido()
        lat[a:a + len(s)] += (s * (0.5 + 0.5 * k / 7))[:, None] * 0.35
    mezcla += filtro(lat, 20, 300)
    mezcla = reverb(mezcla)
    mezcla /= np.percentile(np.abs(mezcla), 99.95) / 0.8    # nivel según la música, antes del vinil
    mezcla[:, 0] += vinil()
    mezcla[:, 1] += np.roll(vinil(), 7919)
    mezcla = cinta(mezcla)
    t = np.arange(N) / SR
    mezcla *= (np.minimum(1, t / 1.5) * np.clip((DUR + COLA - t) / 3.0, 0, 1))[:, None]
    mezcla = np.tanh(mezcla * 1.2)
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
