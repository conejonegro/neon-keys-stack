"""Sonido de las bolitas "armonía": cada golpe que calculó bolitas.mjs toca la nota fija de esa bolita.

Todas las notas son de la misma escala (Do mayor pentatónica), así que suenen como suenen juntas,
siempre se oye armónico. Pesadas = graves, tipo campana suave; ligeras = agudas, tipo cristal.
El volumen sigue la fuerza del golpe y el lado (izquierda/derecha) sigue la posición de la bolita.

Uso:  ../.venv/bin/python bolitas_sonido.py ../out/.tmp/bolitas-armonia.json ../out/.tmp/bolitas-armonia.wav
"""

import json
import sys
import wave

import numpy as np

SR = 44100
datos = json.loads(open(sys.argv[1], encoding="utf-8").read())
SALIDA = sys.argv[2]
DUR = datos["total"]
FPS = datos["fps"]

# Do mayor pentatónica (MIDI). Graves para las pesadas, agudas para las ligeras.
GRAVES = [48, 52, 55, 57, 60, 64, 67]
AGUDAS = [72, 74, 76, 79, 81, 84, 86, 88, 91, 93]
VENTANA = 0.03     # en cada ventana de 30 ms suenan como máximo MAX_POR_VENTANA golpes (los más fuertes)
MAX_POR_VENTANA = 2
FUERZA_MIN = 1.2

hz = lambda m: 440 * 2 ** ((m - 69) / 12)
rng = np.random.default_rng(3)


def campana(f, dur=1.6):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t * 3) + 0.15 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 6)
    return s * np.minimum(1, t / 0.004) * np.exp(-t * 2.6)


def cristal(f, dur=0.9):
    """FM tipo campanita de vidrio: el brillo se apaga más rápido que la nota."""
    t = np.arange(int(dur * SR)) / SR
    indice = 2.2 * np.exp(-t * 9)
    s = np.sin(2 * np.pi * f * t + indice * np.sin(2 * np.pi * 3.5 * f * t))
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 5.5) * 0.7


# Cada bolita con su nota fija: se reparten en orden, así las que caen seguidas hacen arpegios
notas = []
ng = nl = 0
for b in datos["bolitas"]:
    if b["tipo"] == "pesada":
        notas.append(("pesada", GRAVES[ng % len(GRAVES)]))
        ng += 1
    else:
        notas.append(("ligera", AGUDAS[nl % len(AGUDAS)]))
        nl += 1

# Elegir los golpes que suenan
golpes = [g for g in datos["golpes"] if g[2] >= FUERZA_MIN]
por_ventana = {}
for g in golpes:
    por_ventana.setdefault(int(g[0] / VENTANA), []).append(g)
elegidos = [g for lista in por_ventana.values() for g in sorted(lista, key=lambda g: -g[2])[:MAX_POR_VENTANA]]

# Se guardan en el JSON para que la escena haga destellar justo las bolitas que suenan
datos["suenan"] = sorted(elegidos)
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(datos, f)

cache = {}
izq = np.zeros(int(SR * (DUR + 2)))
der = np.zeros_like(izq)
for t, i, fuerza in elegidos:
    tipo, m = notas[i]
    if (tipo, m) not in cache:
        cache[(tipo, m)] = campana(hz(m)) if tipo == "pesada" else cristal(hz(m))
    s = cache[(tipo, m)] * min(1.0, fuerza / 5) ** 0.8 * (0.9 if tipo == "pesada" else 0.55)
    cuadro = datos["cuadros"][min(len(datos["cuadros"]) - 1, int(t * FPS))]
    x = cuadro[3 * i] if 3 * i < len(cuadro) else 0.0
    lado = np.clip(x / 1.5, -1, 1) * 0.7
    a = int(t * SR)
    n = min(len(s), len(izq) - a)
    izq[a : a + n] += s[:n] * np.sqrt((1 - lado) / 2)
    der[a : a + n] += s[:n] * np.sqrt((1 + lado) / 2)


def eco(x, segundos=1.8, mezcla=0.28, semilla=0):
    """Reverb sencilla: convolución con ruido que se apaga (como un cuarto grande)."""
    r = np.random.default_rng(semilla)
    t = np.arange(int(segundos * SR)) / SR
    ir = r.normal(0, 1, len(t)) * np.exp(-t * 3.2)
    ir /= np.sqrt(np.sum(ir**2))
    n = len(x) + len(ir)
    m = 1 << (n - 1).bit_length()
    humedo = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return x * (1 - mezcla) + humedo * mezcla * 3


izq, der = eco(izq, semilla=1), eco(der, semilla=2)
estereo = np.stack([izq, der], axis=1)[: int(SR * DUR)]
fade = int(0.3 * SR)
estereo[-fade:] *= np.linspace(1, 0, fade)[:, None]
estereo = estereo / np.max(np.abs(estereo)) * 0.89
with wave.open(SALIDA, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((estereo * 32767).astype(np.int16).tobytes())
print(f"Sonido listo: {len(elegidos)} de {len(datos['golpes'])} golpes suenan → {SALIDA}")
