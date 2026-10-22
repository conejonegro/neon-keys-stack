"""Sonido electrónico de las bolitas en la esfera (rebotes3d.mjs) + capas de texto del video.

Cada golpe que suena toca un "pluck" de sintetizador con eco ping-pong. La nota sale del acorde que
suena en ese momento (La menor – Fa – Do – Sol, hipnótico y siempre armónico) y de la altura del golpe:
arriba de la esfera = agudo, abajo = grave. Debajo va una base electrónica a 125 BPM que crece:
pad → hi-hats → bombo → bajo → subida con redoble → drop en el clímax → glitch (el audio se traba
igual que el video) → golpe final en el cierre. Todo se sintetiza con numpy, sin samples.

También agrega al JSON las capas de texto (título, marca y cierre) hechas con neon_keys.py.

Uso:  .venv/bin/python escenas3d/rebotes3d_sonido.py out/.tmp/rebotes-esfera-3d.json out/.tmp/rebotes-esfera-3d.wav
"""

import base64
import io
import json
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import neon_keys as nk  # noqa: E402

TITULO = "SALE 1, ENTRAN 2"
SUBTITULO = "¿Cuántas habrá al final?"
CIERRE = "Sígueme para más"

SR = 44100
ruta_json, SALIDA = sys.argv[1], sys.argv[2]
datos = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
cfg = datos["cfg"]
DUR = datos["total"]
FPS = datos["fps"]
BEAT = 60 / cfg["bpm"]
COMPAS = 4 * BEAT
CLIMAX, GLITCH, CIERRE_T = cfg["climax"], cfg["glitch"], cfg["cierre"]
BOMBO = cfg["bombo"]
R = cfg["R"]

rng = np.random.default_rng(11)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
N = int(SR * (DUR + 3))


def pista():
    return np.zeros((N, 2))


def poner(destino, s, t, gan=1.0, lado=0.0):
    """Suma el sonido mono `s` en el segundo t, con paneo lado ∈ [-1, 1]."""
    a = int(t * SR)
    if a >= N or a < 0:
        return
    n = min(len(s), N - a)
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


def en_tramos(t, tramos):
    return any(a <= t < b for a, b in tramos)


# ------------------------------------------------------------------ acordes (2 compases cada uno)
# La menor – Fa – Do – Sol. Tonos del acorde en semitonos sobre La.
ACORDES = [(57, [0, 3, 7]), (53, [0, 4, 7]), (60, [0, 4, 7]), (55, [0, 4, 7])]


def acorde(t):
    return ACORDES[int(t / (2 * COMPAS)) % 4]


def tonos(t, desde=0, octavas=3):
    raiz, iv = acorde(t)
    return [raiz + 12 * o + i + desde for o in range(octavas) for i in iv]


# ------------------------------------------------------------------ instrumentos
def onda_sierra(f, t, armonicos, caida=0.0):
    """Sierra por suma de armónicos; con `caida` los agudos se apagan antes (filtro que se cierra)."""
    s = np.zeros_like(t)
    for k in range(1, armonicos + 1):
        if f * k > SR / 2.2:
            break
        s += np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * caida * (k - 1))
    return s


def pluck(m, dur=0.55):
    t = np.arange(int(dur * SR)) / SR
    f = hz(m)
    s = onda_sierra(f, t, 14, caida=9) + 0.8 * onda_sierra(f * 1.006, t, 14, caida=9)
    s += 0.5 * np.sin(2 * np.pi * f * 2 * t + 1.5 * np.exp(-t * 14) * np.sin(2 * np.pi * f * 4 * t))  # brillo FM
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 7) * 0.35


def bombo():
    t = np.arange(int(0.45 * SR)) / SR
    f = 45 + 110 * np.exp(-t * 32)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    s += rng.normal(0, 1, len(t)) * np.exp(-t * 120) * 0.25   # clic del golpe
    return s


def ruido_agudo(dur, caida):
    t = np.arange(int(dur * SR)) / SR
    r = rng.normal(0, 1, len(t))
    r = np.diff(r, prepend=0)          # quita graves (filtro paso alto sencillo)
    return r * np.exp(-t * caida)


def palmada():
    t = np.arange(int(0.25 * SR)) / SR
    r = rng.normal(0, 1, len(t))
    env = sum(np.exp(-np.maximum(0, t - d) * 60) * (t >= d) for d in (0, 0.012, 0.024)) * np.exp(-t * 18)
    return np.diff(r, prepend=0) * env * 0.6


def bajo(m, dur):
    t = np.arange(int(dur * SR)) / SR
    f = hz(m)
    s = onda_sierra(f, t, 10, caida=14) + 0.9 * np.sin(2 * np.pi * f * t)
    return s * np.minimum(1, t / 0.004) * np.exp(-t * 5)


def pad(raiz_tonos, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for m in raiz_tonos:
        for d in (-0.08, 0.0, 0.08):          # tres voces desafinadas ("supersaw")
            s += onda_sierra(hz(m + d), t, 6)
    env = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.6)
    return s * env / len(raiz_tonos)


def eco(x, segundos=2.2, mezcla=0.3, semilla=0):
    r = np.random.default_rng(semilla)
    t = np.arange(int(segundos * SR)) / SR
    ir = r.normal(0, 1, len(t)) * np.exp(-t * 2.6)
    ir /= np.sqrt(np.sum(ir ** 2))
    n = len(x) + len(ir)
    m = 1 << (n - 1).bit_length()
    humedo = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return x * (1 - mezcla) + humedo * mezcla * 3


def ping_pong(x, retardo, realim=0.45, repeticiones=6):
    """Eco que rebota izquierda ↔ derecha (hipnótico)."""
    y = x.copy()
    d = int(retardo * SR)
    for k in range(1, repeticiones + 1):
        g = realim ** k
        canal = k % 2   # alterna lados
        y[d * k:, canal] += x[:-d * k, 0] * g * 0.7 + x[:-d * k, 1] * g * 0.3
    return y


# ------------------------------------------------------------------ 1. plucks de los golpes
golpes = datos["golpes"]
tiempos = np.array([g[0] for g in golpes])
plucks = pista()
cache = {}
for t, _id, x, y, z in golpes:
    if t >= CIERRE_T:
        continue
    lista = tonos(t, desde=0, octavas=3)                  # La3..Sol6 aprox.
    i = int(np.clip((y / R + 1) / 2, 0, 0.999) * len(lista))
    m = lista[i]
    if m not in cache:
        cache[m] = pluck(m)
    # Menos volumen por nota cuando suenan muchas a la vez (densidad en ±0.25 s)
    densidad = np.searchsorted(tiempos, t + 0.25) - np.searchsorted(tiempos, t - 0.25)
    gan = 1.0 / np.sqrt(max(1.0, densidad / 4))
    poner(plucks, cache[m], t, gan, lado=float(np.clip(x / R, -1, 1)) * 0.6)

# Escapes: "bloop" que sube, suave (máximo uno cada 60 ms)
ultimo = -1
for t, *_ in datos["escapes"]:
    if t - ultimo < 0.06 or t >= CIERRE_T:
        continue
    ultimo = t
    tt = np.arange(int(0.09 * SR)) / SR
    f = 700 + 1400 * (tt / 0.09) ** 0.6
    poner(plucks, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 30) * 0.18, t, lado=rng.uniform(-0.5, 0.5))

plucks = ping_pong(plucks, 0.75 * BEAT)                    # corchea con puntillo
plucks = np.stack([eco(plucks[:, 0], semilla=1), eco(plucks[:, 1], semilla=2)], axis=1)

# ------------------------------------------------------------------ 2. base electrónica
base = pista()
lateral = np.ones(N)   # "sidechain": el pad y el bajo se agachan con cada bombo

# Pad: todo el video hasta el glitch, más fuerte después del bombo
t = 0.0
while t < GLITCH:
    raiz, iv = acorde(t)
    p = pad([raiz - 12 + i for i in iv] + [raiz], 2 * COMPAS + 0.6)
    vol = 0.10 if t < BOMBO[0][0] else 0.14
    poner(base, p, t, vol)
    t += 2 * COMPAS

pasos = np.arange(0, GLITCH, BEAT / 4)   # semicorcheas
for k, t in enumerate(pasos):
    sub = k % 4
    if en_tramos(t, BOMBO) and sub == 0:
        poner(base, bombo(), t, 0.9)
        a = int(t * SR)
        caida = np.minimum(1, np.arange(int(0.3 * SR)) / SR / 0.25) ** 0.6
        lateral[a:a + len(caida)] = np.minimum(lateral[a:a + len(caida)], 0.35 + 0.65 * caida[: N - a])
    # Hi-hat a contratiempo desde el compás 4; en la subida, semicorcheas
    if t >= 4 * COMPAS and (en_tramos(t, BOMBO) or t >= 4 * COMPAS and t < BOMBO[0][0]):
        if sub == 2:
            poner(base, ruido_agudo(0.08, 45), t, 0.10, lado=0.2)
        elif t >= 22 * COMPAS and t < BOMBO[0][1]:
            poner(base, ruido_agudo(0.04, 80), t, 0.05, lado=-0.2)
    # Palmada en 2 y 4 desde el compás 16
    if t >= 16 * COMPAS and en_tramos(t, BOMBO) and sub == 0 and int(round(t / BEAT)) % 2 == 1:
        poner(base, palmada(), t, 0.35)
    # Bajo a contratiempo (corcheas "off-beat") desde el compás 16
    if t >= 16 * COMPAS and en_tramos(t, BOMBO) and sub == 2:
        raiz, _ = acorde(t)
        poner(base, bajo(raiz - 24, BEAT * 0.45), t, 0.32)

# Subida antes del clímax: ruido que se abre + redoble que acelera, en el hueco sin bombo
ini_sub = BOMBO[0][1] - 2 * COMPAS
dur_sub = CLIMAX - ini_sub
tt = np.arange(int(dur_sub * SR)) / SR
ruido = rng.normal(0, 1, len(tt))
brillo = (tt / dur_sub) ** 2
ruido = ruido * brillo + np.diff(ruido, prepend=0) * (1 - brillo)   # de opaco a brillante
poner(base, ruido * (tt / dur_sub) ** 2.5 * 0.22, ini_sub)
f = 200 * 2 ** (3 * tt / dur_sub)
poner(base, np.sin(2 * np.pi * np.cumsum(f) / SR) * (tt / dur_sub) ** 2 * 0.12, ini_sub)
t = BOMBO[0][1]
for paso in (BEAT, BEAT / 2, BEAT / 4, BEAT / 8):
    fin = t + COMPAS / 2 if paso > BEAT / 8 else CLIMAX
    while t < fin - 1e-6:
        poner(base, palmada(), t, 0.22 + 0.25 * (t - BOMBO[0][1]) / (CLIMAX - BOMBO[0][1]))
        t += paso

# Drop: golpe grave + platillo
tt = np.arange(int(2.5 * SR)) / SR
golpe = np.sin(2 * np.pi * np.cumsum(30 + 90 * np.exp(-tt * 9)) / SR) * np.exp(-tt * 1.6)
poner(base, golpe, CLIMAX, 1.0)
poner(base, ruido_agudo(2.0, 2.2), CLIMAX, 0.22)

base *= lateral[:, None] ** 0.5
base = np.stack([eco(base[:, 0], 1.2, 0.12, 3), eco(base[:, 1], 1.2, 0.12, 4)], axis=1)

# ------------------------------------------------------------------ 3. mezcla, glitch y cierre
mezcla = plucks * 0.9 + base
mezcla /= np.max(np.abs(mezcla[: int(CIERRE_T * SR)])) or 1.0

# El audio se traba igual que el video: cada cuadro toma el pedacito de la simulación que se ve
por_cuadro = SR // FPS
salida = np.zeros((int(DUR * FPS) * por_cuadro, 2))
for f, st in enumerate(datos["mapa"]):
    t = f / FPS
    if t >= CIERRE_T:
        break
    s = int(round(st * SR))
    seg = mezcla[s:s + por_cuadro].copy()
    g = datos["glitch"][f]
    if g > 0.3:   # "bitcrush": menos niveles de volumen y muestras repetidas
        pasos_b = max(4, int(64 * (1 - g)))
        seg = np.round(seg * pasos_b) / pasos_b
        r = 1 + int(10 * g)
        seg = np.repeat(seg[::r], r, axis=0)[: len(seg)]
    if CIERRE_T - 1 / FPS <= t < CIERRE_T:
        seg *= 0   # micro silencio antes del golpe final
    salida[f * por_cuadro:f * por_cuadro + len(seg)] = seg

# Golpe final en el corte al logo: acorde grave de La menor + golpe y eco largo
cola = np.zeros((len(salida) - int(CIERRE_T * SR), 2))
tt = np.arange(len(cola)) / SR
grave = np.sin(2 * np.pi * np.cumsum(35 + 80 * np.exp(-tt * 10)) / SR) * np.exp(-tt * 1.8)
acorde_final = sum(onda_sierra(hz(m), tt, 8, caida=2) for m in (45, 57, 60, 64, 69)) / 5 * np.exp(-tt * 1.2)
cola += (grave * 0.9 + acorde_final * 0.5)[:, None]
cola = np.stack([eco(cola[:, 0], 2.5, 0.35, 5), eco(cola[:, 1], 2.5, 0.35, 6)], axis=1)
salida[int(CIERRE_T * SR):] += cola[: len(salida) - int(CIERRE_T * SR)]

salida = np.tanh(salida * 1.1) * 0.95   # saturación suave (más "electrónico", sin picos)
fade = int(0.5 * SR)
salida[:int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
salida[-fade:] *= np.linspace(1, 0, fade)[:, None]
salida = salida / np.max(np.abs(salida)) * 0.89
with wave.open(SALIDA, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((salida * 32767).astype("<i2").tobytes())
print(f"Sonido listo: {len(golpes)} golpes, {DUR:.1f} s → {SALIDA}")


# ------------------------------------------------------------------ capas de texto
def png_base64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


cierre = nk.glow_text(Image.new("RGB", (nk.W, nk.H)), (nk.W / 2, 820), "NEON KEYS",
                      nk.font(nk.FONT_BOLD, 130, 2), (255, 255, 255), nk.BRAND_GLOW, radius=26)
cierre = nk.glow_text(cierre, (nk.W / 2, 980), CIERRE, nk.font(nk.FONT_TEXT, 54, 0),
                      (255, 255, 255), nk.TITLE_GLOW, radius=14)
datos["capas"] = {
    "titulo": png_base64(nk.make_title_layer(TITULO, SUBTITULO)),
    "marca": png_base64(nk.make_brand_layer()),
    "cierre": png_base64(cierre),
}
Path(ruta_json).write_text(json.dumps(datos), encoding="utf-8")
print(f"Capas de texto agregadas a {ruta_json}")
