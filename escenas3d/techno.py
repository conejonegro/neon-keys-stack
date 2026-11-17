#!/usr/bin/env python3
"""Neon Keys · "¿Por qué tu techno no rueda?": un secuenciador 3D que se llena capa por capa (ADR-022).

Una sola tabla (PATRONES + SECCIONES) manda en la imagen y en el sonido: aquí se calculan todos los golpes
(segundo, carril, paso, fuerza), se sintetiza la batería a 132 BPM y se escribe el JSON que lee
escenas/techno.html. El texto de cada sección es también el guion de la voz en off (se guarda aparte con sus
tiempos para grabarla a tiempo).

Dos versiones: `largo` (por defecto, ~1:10, para monetizar: 17 ideas, antes/después, subida y drop doble) y
`corto` (la prueba de ~22 s).

Uso:
    .venv/bin/python escenas3d/techno.py [--version largo|corto]
        # → out/.tmp/beat-techno-rueda.json, .wav y -guion.txt  (corto: beat-techno-rueda-corto.*)
    cd escenas3d && node grabar.js escenas/techno.html out/videos/beats/beat-techno-rueda.mp4 \\
        --datos out/.tmp/beat-techno-rueda.json --audio out/.tmp/beat-techno-rueda.wav
"""

import argparse
import json
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
FPS = 30

BPM = 132
BEAT = 60 / BPM
COMPAS = 4 * BEAT
PASO = BEAT / 4                  # semicorchea
_args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
_args.add_argument("--version", choices=["largo", "corto"], default="largo")
VERSION = _args.parse_args().version
NOMBRE = "beat-techno-rueda" + ("-corto" if VERSION == "corto" else "")

# Carriles de adelante (cerca de la cámara) hacia atrás
CARRILES = ["KICK", "RUMBLE", "CLAP", "STAB", "OPEN HAT", "HATS"]
# Paso → fuerza (0..1). La altura del bloque sale de la fuerza.
PATRONES = {
    "KICK": {0: 1, 4: 1, 8: 1, 12: 1},
    "GHOST": {11: 0.32},                         # va en el carril del kick, pero entra después
    "RUMBLE": {1: 0.55, 2: 0.85, 3: 0.65, 5: 0.55, 6: 0.85, 7: 0.65, 9: 0.55, 13: 0.55, 14: 0.85, 15: 0.65},
    "CLAP": {4: 1, 12: 1},
    "STAB": {10: 1},
    "OPEN HAT": {2: 0.8, 6: 0.8, 10: 0.8, 14: 0.8},
    "HATS": {i: (0.5 if i % 4 == 0 else 0.85 if i % 2 else 0.62) for i in range(16)},
    "ROLL": {},                                  # redoble de clap en la subida (lo arma golpes())
}
TODAS = ["KICK", "RUMBLE", "GHOST", "CLAP", "HATS", "OPEN HAT", "STAB"]

# Secciones: (compases, texto con *palabra clave*, capas que suenan, toma de cámara). Una idea por sección; el
# texto es también el guion de la voz (~0.33 s por palabra, así que ~10 palabras por cada 2 compases).
if VERSION == "corto":
    SECCIONES = [
        (2, "¿Por qué tu *techno* no rueda?", ["KICK"], "gancho"),
        (1, "Entre kick y kick queda un *hueco.*", ["KICK"], "hueco"),
        (2, "Llénalo con un *rumble* que nunca pise al kick.", ["KICK", "RUMBLE"], "rumble"),
        (1, "Un *ghost* kick flojito… y rueda.", ["KICK", "RUMBLE", "GHOST"], "ghost"),
        (1, "*Clap* en el 2 y en el 4.", ["KICK", "RUMBLE", "GHOST", "CLAP"], "clap"),
        (1, "*Hats* en semicorcheas, open hat a contratiempo.", TODAS[:-1], "hats"),
        (1, "Y un *stab* con eco donde nadie toca.", TODAS, "stab"),
        (2, "Seis capas. *Ahora* *sí* rueda.", TODAS, "drop"),
    ]
    COMPASES_CIERRE = 1
    CIERRE_TEXTO = "Sígueme para más"
else:
    SECCIONES = [
        (2, "¿Por qué tu *techno* no rueda como el de los clubs?", ["KICK"], "gancho"),
        (2, "Todo empieza con el *kick:* cuatro golpes por compás.", ["KICK"], "kick"),
        (2, "Entre kick y kick queda un *hueco…* ahí muere el groove.", ["KICK"], "hueco"),
        (2, "Llénalo con un *rumble:* el kick con reverb, filtrado en graves.", ["KICK", "RUMBLE"], "rumble"),
        (2, "Regla de oro: el rumble nunca *pisa* al kick.", ["KICK", "RUMBLE"], "sidechain"),
        (2, "Un *ghost* kick flojito justo antes… y empieza a rodar.", ["KICK", "RUMBLE", "GHOST"], "ghost"),
        (2, "*Clap* en el 2 y en el 4: marca el paso.", ["KICK", "RUMBLE", "GHOST", "CLAP"], "clap"),
        (2, "*Hats* en cada semicorchea, unos fuertes y otros suaves.", TODAS[:-2], "hats"),
        (2, "Un *open* *hat* a contratiempo, entre kick y kick.", TODAS[:-1], "open"),
        (2, "Un poco de *swing:* atrásalos tantito y suena humano.", TODAS[:-1], "swing"),
        (2, "Y un *stab* de acorde con eco, donde nadie toca.", TODAS, "stab"),
        (2, "*Seis* *capas.* Cada una en su lugar.", TODAS, "recap"),
        (2, "Así sonaba *antes…*", ["KICK"], "antes"),
        (2, "…y así suena *ahora.*", TODAS, "ahora"),
        (2, "Y cuando todo *encaja…*", TODAS + ["ROLL"], "subida"),
        (3, "¡Ahora *sí* rueda!", TODAS, "drop"),
        (3, "*Guárdalo* para tu próxima sesión.", TODAS, "drop2"),
    ]
    COMPASES_CIERRE = 2
    CIERRE_TEXTO = "Sígueme para más"

INICIOS = np.cumsum([0] + [nc for nc, *_ in SECCIONES])        # compás donde empieza cada sección
TOMAS = [toma for *_, toma in SECCIONES]


def inicio(toma, defecto=0.0):
    return INICIOS[TOMAS.index(toma)] * COMPAS if toma in TOMAS else defecto


CIERRE = INICIOS[-1] * COMPAS                     # NK + "Sígueme para más"
TOTAL = CIERRE + COMPASES_CIERRE * COMPAS + 0.4
GLITCH = (CIERRE - 2 * BEAT, CIERRE)              # últimos 2 tiempos del drop
T_DROP = inicio("drop")
T_SUBIDA = inicio("subida", None)
# Sidechain y swing: en la versión larga entran cuando se explican (así se oye la diferencia)
T_SIDECHAIN = inicio("sidechain")
T_SWING = inicio("swing")
SWING = 0.024 if VERSION == "largo" else 0.012   # los contratiempos llegan un poquito tarde (más "humano")

rng = np.random.default_rng(132)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
N = int(TOTAL * SR)


# ------------------------------------------------------------------ golpes (los mismos para imagen y sonido)
def golpes():
    lista = []
    for c0, (nc, _texto, capas, toma) in zip(INICIOS, SECCIONES):
        for compas in range(c0, c0 + nc):
            ultimo = compas == c0 + nc - 1
            for capa in capas:
                patron = PATRONES[capa]
                if capa == "ROLL":
                    # Redoble de clap en el último compás de la subida: corcheas, luego semicorcheas, creciendo
                    patron = {p: 0.35 + 0.6 * p / 15 for p in range(16) if ultimo and (p >= 8 or p % 2 == 0)}
                for paso, fuerza in patron.items():
                    # Antes del drop se cae el grave (los últimos 2 tiempos de la subida quedan sin kick)
                    if toma == "subida" and ultimo and paso >= 8 and capa in ("KICK", "RUMBLE", "GHOST", "STAB"):
                        continue
                    t = compas * COMPAS + paso * PASO
                    if capa in ("HATS", "OPEN HAT") and paso % 2 and t >= T_SWING:
                        t += SWING
                    if t >= GLITCH[1]:
                        continue
                    carril = 0 if capa == "GHOST" else CARRILES.index("CLAP" if capa == "ROLL" else capa)
                    lista.append([round(t, 5), carril, paso, round(fuerza, 3), capa])
    lista.sort(key=lambda g: g[0])
    return lista


def mapa_glitch(t):
    """Segundo que se ve/oye durante el glitch: trozos que se repiten, cada vez más cortos."""
    g0, g1 = GLITCH
    if not (g0 <= t < g1):
        return t
    k = (t - g0) / (g1 - g0)
    largo = PASO * 2 if k < 0.35 else PASO if k < 0.7 else PASO / 2
    bloque = largo * 3                     # en cada bloque suena 3 veces su primer trozo
    return g0 + ((t - g0) // bloque) * bloque + (t - g0) % largo


# ------------------------------------------------------------------ síntesis
def poner(destino, s, t, gan=1.0, lado=0.0):
    """Suma el sonido mono `s` en el segundo t, con paneo lado ∈ [-1, 1]."""
    a = int(t * SR)
    if a >= N or a < 0:
        return
    n = min(len(s), N - a)
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


def filtro(x, bajo, alto):
    """Paso banda suave con FFT (bajo/alto en Hz)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    curva = (1 / (1 + (bajo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / alto) ** 4))
    return np.fft.irfft(X * curva, len(x))


def eco(x, segundos=1.8, mezcla=0.3, caida=3.0, semilla=0):
    r = np.random.default_rng(semilla)
    t = np.arange(int(segundos * SR)) / SR
    ir = r.normal(0, 1, len(t)) * np.exp(-t * caida)
    ir /= np.sqrt(np.sum(ir ** 2))
    m = 1 << (len(x) + len(ir) - 1).bit_length()
    humedo = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return x * (1 - mezcla) + humedo * mezcla * 3


def ping_pong(x, retardo, realim=0.5, repeticiones=7):
    """Eco que rebota izquierda ↔ derecha."""
    y = x.copy()
    d = int(retardo * SR)
    for k in range(1, repeticiones + 1):
        g = realim ** k
        y[d * k:, k % 2] += (x[:-d * k, 0] + x[:-d * k, 1]) * 0.5 * g
    return y


def kick(fuerza=1.0):
    """Bombo de techno: seno que cae de 170 a 48 Hz, clic de ataque y un poco de saturación."""
    dur = 0.42 if fuerza > 0.5 else 0.16
    t = np.arange(int(dur * SR)) / SR
    f = 48 + 122 * np.exp(-t * 38)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (6.5 if fuerza > 0.5 else 22))
    s += filtro(rng.normal(0, 1, len(t)), 1500, 9000) * np.exp(-t * 260) * 0.35
    return np.tanh(1.8 * s) * fuerza


def rumble(fuerza):
    """Golpe grave y sucio entre kicks (en el estudio: el kick mandado a una reverb y filtrado)."""
    t = np.arange(int(PASO * 1.6 * SR)) / SR
    f = hz(31)                                    # Sol 1: un poco arriba del kick, sin chocar
    s = np.tanh(2.4 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.01 * t)))
    s += filtro(rng.normal(0, 1, len(t)), 30, 260) * 0.8
    return s * np.minimum(1, t / 0.006) * np.exp(-t * 16) * fuerza


def clap():
    t = np.arange(int(0.32 * SR)) / SR
    r = filtro(rng.normal(0, 1, len(t)), 900, 7500)
    env = sum(np.exp(-np.maximum(0, t - d) * 70) * (t >= d) for d in (0, 0.011, 0.023)) * 0.5
    env += np.exp(-np.maximum(0, t - 0.03) * 16) * (t >= 0.03) * 0.6
    return r * env


def hat(fuerza, abierto=False):
    dur, caida = (0.3, 13) if abierto else (0.05, 95)
    t = np.arange(int(dur * SR)) / SR
    r = filtro(rng.normal(0, 1, len(t)), 6500, 16000)
    return r * np.exp(-t * caida) * fuerza * (0.55 if abierto else 0.45)


def stab():
    """Acorde de Fa menor 9 con sierras desafinadas y un filtro que se cierra rápido."""
    t = np.arange(int(0.32 * SR)) / SR
    s = np.zeros_like(t)
    for m in (53, 56, 60, 63, 67):
        for d in (-0.07, 0.07):
            f = hz(m + d)
            for k in range(1, 14):
                if f * k > SR / 2.2:
                    break
                # Armónicos agudos se apagan antes (filtro que se cierra)
                s += np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (6 + 9 * (k - 1)))
    return s * np.minimum(1, t / 0.003) * np.exp(-t * 7) / 6


def subida_y_golpe():
    """Subida de ruido y tono antes del drop, y el golpe (grave + platillo) al caer."""
    x = np.zeros((N, 2))
    dur = T_DROP - T_SUBIDA
    t = np.arange(int(dur * SR)) / SR
    k = t / dur
    ruido = rng.normal(0, 1, len(t))
    # Barrido: se filtra por trozos con un paso banda que sube de 400 Hz a 9 kHz
    barrido = np.zeros_like(ruido)
    trozo = int(0.05 * SR)
    for a in range(0, len(t), trozo):
        f = 400 * (9000 / 400) ** (a / len(t))
        barrido[a:a + trozo] = filtro(ruido[a:a + trozo * 2], f * 0.6, f * 1.6)[:len(barrido[a:a + trozo])]
    tono = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2 * k)) / SR)
    sube = (barrido * 0.5 + tono * 0.12) * k ** 2.2
    poner(x, sube, T_SUBIDA, 0.55)
    # Golpe del drop
    t = np.arange(int(2.2 * SR)) / SR
    grave = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 9)) / SR) * np.exp(-t * 2.2)
    platillo = filtro(rng.normal(0, 1, len(t)), 3500, 15000) * np.exp(-t * 2.4) * 0.5
    poner(x, np.tanh(1.5 * grave) * 0.8 + platillo, T_DROP, 0.7, -0.1)
    poner(x, platillo, T_DROP + 0.01, 0.3, 0.6)
    return x


def sonido(lista):
    bat = np.zeros((N, 2))         # todo menos el rumble
    grave = np.zeros((N, 2))       # rumble (lleva sidechain)
    stabs = np.zeros((N, 2))       # stab (lleva eco ping-pong)
    for t, carril, paso, fuerza, capa in lista:
        if capa in ("KICK", "GHOST"):
            poner(bat, kick(fuerza), t, 0.9)
        elif capa == "RUMBLE":
            poner(grave, rumble(fuerza), t, 0.5)
        elif capa in ("CLAP", "ROLL"):
            poner(bat, clap(), t, 0.42 * fuerza)
        elif capa == "HATS":
            poner(bat, hat(fuerza), t, 0.6, lado=0.25 if paso % 2 else -0.15)
        elif capa == "OPEN HAT":
            poner(bat, hat(fuerza, True), t, 0.6, lado=-0.3)
        elif capa == "STAB":
            poner(stabs, stab(), t, 0.5)

    # Sidechain: el rumble se agacha en cada kick para no pisarlo
    tt = np.arange(N) / SR
    duck = np.ones(N)
    for t, _c, _p, fuerza, capa in lista:
        if capa == "KICK" and t >= T_SIDECHAIN:
            a = int(t * SR)
            d = tt[a:a + int(0.25 * SR)] - t
            duck[a:a + len(d)] = np.minimum(duck[a:a + len(d)], 1 - 0.92 * np.exp(-d * 14))
    grave = np.stack([eco(grave[:, c], 1.2, 0.35, 5.0, c) for c in (0, 1)], 1)
    grave = np.stack([filtro(grave[:, c], 25, 300) for c in (0, 1)], 1) * duck[:, None]

    stabs = ping_pong(stabs, 3 * PASO, 0.5)
    stabs = np.stack([eco(stabs[:, c], 1.6, 0.3, 3.0, 7 + c) for c in (0, 1)], 1)
    bat[:, 0] = eco(bat[:, 0], 0.6, 0.12, 9.0, 3)
    bat[:, 1] = eco(bat[:, 1], 0.6, 0.12, 9.0, 4)
    mezcla = bat + grave * 1.2 + stabs
    if T_SUBIDA is not None:
        mezcla += subida_y_golpe()

    # Glitch: los trozos se repiten (mismo mapa de tiempo que la imagen) y se ensucian con bitcrush
    g0, g1 = int(GLITCH[0] * SR), int(GLITCH[1] * SR)
    fuente = np.array([mapa_glitch(i / SR) for i in range(g0, g1)])
    trozo = mezcla[(fuente * SR).astype(int)]
    pasos = 2 ** 5
    trozo = np.round(trozo * pasos) / pasos
    trozo = trozo[(np.arange(len(trozo)) // 4) * 4]           # baja la resolución de tiempo
    mezcla[g0:g1] = trozo

    # Cierre: un último kick grande con su cola y el stab que se aleja
    cola = np.zeros((N, 2))
    poner(cola, kick(1.0), GLITCH[1], 1.0)
    poner(cola, stab(), GLITCH[1], 0.5)
    cola = ping_pong(cola, 3 * PASO, 0.55, 8)
    cola = np.stack([eco(cola[:, c], 2.4, 0.4, 2.2, 11 + c) for c in (0, 1)], 1)
    mezcla[g1:] = cola[g1:]

    mezcla = np.tanh(mezcla * 1.15)
    mezcla[:int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))[:, None]
    fade = int(0.6 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    # Pico a −6 dB: queda espacio para la voz en off que se pone en TikTok
    return mezcla / np.max(np.abs(mezcla)) * 0.5


def escribir_wav(ruta, x):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


# ------------------------------------------------------------------ textos (también guion de la voz)
def textos():
    salida = []
    for c0, (nc, texto, _capas, toma) in zip(INICIOS, SECCIONES):
        t0, t1 = c0 * COMPAS, (c0 + nc) * COMPAS
        palabras = [{"txt": p.replace("*", ""), "clave": p.startswith("*")} for p in texto.split()]
        # Palabra por palabra: ~0.33 s cada una (ritmo de voz), más rápido si no cabe en la sección
        cada = min(0.33, (t1 - t0 - 0.5) / len(palabras))
        for i, p in enumerate(palabras):
            p["t"] = round(t0 + 0.08 + i * cada, 3)
        salida.append({"t0": float(t0), "t1": float(t1), "toma": toma, "palabras": palabras,
                       "texto": texto.replace("*", "")})
    return salida


def main():
    lista = golpes()
    secciones = textos()
    total_cuadros = int(round(TOTAL * FPS))
    datos = {
        "total": TOTAL, "fps": FPS, "bpm": BPM, "beat": BEAT, "compas": COMPAS, "paso": PASO,
        "carriles": CARRILES, "patrones": PATRONES,
        "entrada": {capa: next(g[0] for g in lista if g[4] == capa) for capa in CARRILES},
        "golpes": [g[:4] + [g[4]] for g in lista],
        "secciones": secciones,
        "glitch": list(GLITCH), "cierre": CIERRE, "cierreTexto": CIERRE_TEXTO,
        "sidechain": T_SIDECHAIN, "swing": T_SWING,
        "mapa": [round(mapa_glitch(f / FPS), 4) for f in range(total_cuadros + 1)],
    }
    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / f"{NOMBRE}.json").write_text(json.dumps(datos), encoding="utf-8")
    escribir_wav(tmp / f"{NOMBRE}.wav", sonido(lista))
    guion = ["Guion para la voz en off (empieza a decir cada frase en su segundo):", ""]
    guion += [f"{s['t0']:5.1f} s  {s['texto']}" for s in secciones]
    guion += [f"{CIERRE:5.1f} s  {CIERRE_TEXTO}."]
    (tmp / f"{NOMBRE}-guion.txt").write_text("\n".join(guion) + "\n", encoding="utf-8")
    print(f"{len(lista)} golpes, {TOTAL:.1f} s")
    for ext in (".json", ".wav", "-guion.txt"):
        print(tmp / f"{NOMBRE}{ext}")


if __name__ == "__main__":
    main()
