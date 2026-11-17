#!/usr/bin/env python3
"""Neon Keys · "¿Por qué tu reguetón no hace perrear?": el secuenciador 3D de la serie de beats (ADR-022, ADR-023)
con el dembow por dentro.

Igual que trap.py: una sola tabla (PATRONES + SECCIONES) manda en la imagen y en el sonido. Aquí se calculan los
golpes, se sintetiza el beat a 95 BPM (kick en cada tiempo, caja dembow 3-3-2, bajo sub en tresillo, timbales al
final de cada vuelta, acordes menores cortitos y shaker) y se escribe el JSON que lee escenas/reggaeton.html.
Abre con un reguetón cuadrado (caja en 2 y 4, como pop) que se frena con un rayón de disco; luego se arma el bueno
capa por capa. El hueco del kick suena desde que se explica, y en "antes" vuelve a sonar el beat cuadrado.
El JSON lleva las tres paletas del video (`--paleta`, por defecto lima); la escena usa la elegida.

Uso:
    .venv/bin/python escenas3d/reggaeton.py [--paleta lima|tropical|verde-morado]
        # → out/.tmp/beat-reggaeton-perreo.json, .wav y -guion.txt
    cd escenas3d && node grabar.js escenas/reggaeton.html out/pruebas/beats/beat-reggaeton-perreo.mp4 \\
        --datos out/.tmp/beat-reggaeton-perreo.json --audio out/.tmp/beat-reggaeton-perreo.wav
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
_args.add_argument("--paleta", choices=["lima", "tropical", "verde-morado"], default="lima")
PALETA = _args.parse_args().paleta
sys.argv = sys.argv[:1]                            # techno.py lee sus propias opciones al importarse
from techno import eco, escribir_wav, filtro, ping_pong  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
FPS = 30
NOMBRE = "beat-reggaeton-perreo"

BPM = 95
BEAT = 60 / BPM
COMPAS = 4 * BEAT
PASO = BEAT / 4                  # semicorchea

# Carriles de adelante (cerca de la cámara) hacia atrás
CARRILES = ["KICK", "CAJA", "BAJO", "TIMBAL", "ACORDES", "SHAKER"]
DEMBOW = [3, 6, 11, 14]                           # la caja: tres, tres, dos (dos veces por compás)
TRESILLO = [0, 3, 6, 8, 11, 14]                   # el bajo sigue el mismo 3-3-2
# Progresión en La menor, un acorde por compás: Am · F · C · G (raíz del bajo, notas del acorde)
ACORDES = [(33, (57, 60, 64)), (29, (57, 60, 65)), (36, (55, 60, 64)), (31, (55, 59, 62))]
PATRONES = {
    "KICK": {0: 1, 4: 1, 8: 1, 12: 1},
    "CAJA": {3: 0.9, 6: 1, 11: 0.9, 14: 1},
    "BAJO": {0: 1, 3: 0.75, 6: 0.85, 8: 1, 11: 0.75, 14: 0.85},
    "TIMBAL": {12: 0.55, 13: 0.68, 14: 0.82, 15: 1},   # solo en el segundo compás de cada vuelta
    "ACORDES": {0: 0.9, 3: 0.7, 6: 0.8, 10: 0.65},
    "SHAKER": {i: (0.8 if i % 4 == 2 else 0.6) for i in range(0, 16, 2)},
    "ROLL": {},                                  # redoble de timbal en la subida (lo arma golpes())
    # El reguetón cuadrado del inicio: kick en cada tiempo, caja en 2 y 4, shaker parejo y bajo largo
    "KICK MAL": {0: 1, 4: 1, 8: 1, 12: 1},
    "CAJA MAL": {4: 1, 12: 1},
    "BAJO MAL": {0: 1, 8: 1},
    "SHAKER MAL": {i: 0.6 for i in range(16)},
}
TODAS = ["KICK", "CAJA", "BAJO", "TIMBAL", "ACORDES", "SHAKER"]
MALO = ["KICK MAL", "CAJA MAL", "BAJO MAL", "SHAKER MAL"]

# Secciones: (compases, texto con *palabra clave*, capas que suenan, toma de cámara). Una idea por sección; el
# texto es también el guion de la voz (~0.33 s por palabra; a 95 BPM, 1 compás = 2.5 s ≈ 7 palabras).
SECCIONES = [
    (1, "Si tu *reguetón* suena así…", MALO, "malo"),
    (1, "…le falta *perreo.*", MALO, "mal"),             # el beat se frena con un rayón de disco
    (1, "Primero el *kick:* uno en cada tiempo.", ["KICK"], "kick"),
    (2, "La caja no va en el dos y el cuatro: va a *destiempo.*", ["KICK", "CAJA"], "dembow"),
    (2, "Cuéntalo así: *tres,* *tres,* *dos.* Ese es el dembow.", ["KICK", "CAJA"], "tresillo"),
    (2, "El *bajo* sigue el mismo tres-tres-dos, pegado al kick.", ["KICK", "CAJA", "BAJO"], "bajo"),
    (2, "Acordes *menores* y cortitos: ahí vive lo romántico.", ["KICK", "CAJA", "BAJO", "ACORDES"], "acordes"),
    (1, "Un *shaker* en corcheas para que corra.", ["KICK", "CAJA", "BAJO", "ACORDES", "SHAKER"], "shaker"),
    (2, "*Timbales* al final de cada vuelta: avisan que viene algo.", TODAS, "timbales"),
    (2, "Dato: el dembow nació en *Jamaica,* con una canción de 1990.", TODAS, "dato"),
    (2, "Quítale el *kick* un tiempo antes de la vuelta: el hueco también pega.", TODAS, "hueco"),
    (1, "*Seis* *capas,* un solo ritmo.", TODAS, "recap"),
    (1, "¿Así sonaba *antes?*", MALO, "antes"),
    (1, "…y así suena *ahora.*", TODAS, "ahora"),
    (2, "Y cuando cae el *dembow…*", ["CAJA", "ACORDES", "SHAKER", "ROLL"], "subida"),
    (3, "¡*Perreo!*", TODAS, "drop"),
    (2, "*Guárdalo* para tu próxima sesión.", TODAS, "drop2"),
]
COMPASES_CIERRE = 2
CIERRE_TEXTO = "Sígueme para más"

# Paletas para elegir (ADR-023). El cierre NK sigue en cian/magenta: es la marca.
PALETAS = {
    "lima": {
        "nombre": "Lima ácido", "fondo": ["#03120A", "#0C2414"], "piso": "#B6FF3B", "filo": "#B6FF3B",
        "sol": ["#FFE146", "#B6FF3B"], "estrellas": "#C8FF9A", "texto": "#B6FF3B", "clave": "#FFE146",
        "acento": "#FF32D2",
        "capas": {"KICK": "#4FC41A", "CAJA": "#FFE146", "BAJO": "#B6FF3B", "TIMBAL": "#FF32D2",
                  "ACORDES": "#E2FF8C", "SHAKER": "#FFF6A8"},
    },
    "tropical": {
        "nombre": "Tropical", "fondo": ["#020D14", "#062431"], "piso": "#00FFA3", "filo": "#00FFA3",
        "sol": ["#FF6A3C", "#FFC23C"], "estrellas": "#9AFFE0", "texto": "#00FFA3", "clave": "#FFC23C",
        "acento": "#FF6A3C",
        "capas": {"KICK": "#00B874", "CAJA": "#FFC23C", "BAJO": "#00FFA3", "TIMBAL": "#FF6A3C",
                  "ACORDES": "#8CFFD8", "SHAKER": "#FFE7A0"},
    },
    "verde-morado": {
        "nombre": "Verde + morado", "fondo": ["#080416", "#1A082C"], "piso": "#AA64FF", "filo": "#AA64FF",
        "sol": ["#AA64FF", "#A8FF3E"], "estrellas": "#C9B0FF", "texto": "#A8FF3E", "clave": "#FFE146",
        "acento": "#AA64FF",
        "capas": {"KICK": "#8A4DFF", "CAJA": "#A8FF3E", "BAJO": "#C08CFF", "TIMBAL": "#FFE146",
                  "ACORDES": "#D4FFA0", "SHAKER": "#F0E6FF"},
    },
}

INICIOS = np.cumsum([0] + [nc for nc, *_ in SECCIONES])        # compás donde empieza cada sección
TOMAS = [toma for *_, toma in SECCIONES]


def inicio(toma):
    return INICIOS[TOMAS.index(toma)] * COMPAS


def rango(toma):
    i = TOMAS.index(toma)
    return INICIOS[i] * COMPAS, INICIOS[i + 1] * COMPAS


CIERRE = INICIOS[-1] * COMPAS                     # NK + "Sígueme para más"
TOTAL = CIERRE + COMPASES_CIERRE * COMPAS + 0.4
GLITCH = (CIERRE - 2 * BEAT, CIERRE)              # últimos 2 tiempos del drop
T_DROP = inicio("drop")
T_SUBIDA = inicio("subida")
T_HUECO = inicio("hueco")
A0, A1 = rango("antes")
M0, M1 = rango("mal")
RAYON = 0.55                                      # segundos del rayón de disco que frena el beat cuadrado

rng = np.random.default_rng(95)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
N = int(TOTAL * SR)


def con_hueco(compas):
    """El kick (y el bajo) se callan en el último tiempo de cada vuelta desde que se explica (no en "antes")."""
    t = compas * COMPAS
    return compas % 2 == 1 and t >= T_HUECO and not (A0 <= t < A1)


# ------------------------------------------------------------------ golpes (los mismos para imagen y sonido)
def golpes():
    """Lista de golpes [t, carril, paso, fuerza, capa, extra]; extra = nota MIDI (bajo), acorde (acordes) o
    tono (timbal: 1 = hembra, aguda; 0 = macho)."""
    lista = []
    for c0, (nc, _texto, capas, toma) in zip(INICIOS, SECCIONES):
        for compas in range(c0, c0 + nc):
            ultimo = compas == c0 + nc - 1
            acorde = compas % 4
            for capa in capas:
                patron = PATRONES[capa]
                if capa == "ROLL":
                    # Redoble de timbal en el último compás de la subida: corcheas, luego semicorcheas, creciendo;
                    # los dos últimos pasos quedan en silencio antes del drop
                    patron = {p: 0.35 + 0.6 * p / 13 for p in range(14) if ultimo and (p >= 6 or p % 2 == 0)}
                if capa == "TIMBAL" and compas % 2 == 0:
                    continue
                t_compas = compas * COMPAS
                for paso, fuerza in patron.items():
                    t = t_compas + paso * PASO
                    if t >= GLITCH[1]:
                        continue
                    if capa in ("KICK", "BAJO") and paso >= 12 and con_hueco(compas):
                        continue
                    if toma == "subida" and ultimo and paso >= 8 and capa in ("ACORDES", "CAJA"):
                        continue                 # antes del drop se queda solo el redoble
                    extra = 0
                    if capa == "BAJO":
                        extra = ACORDES[acorde][0] + (12 if paso == 14 else 0)
                    elif capa == "BAJO MAL":
                        extra = ACORDES[acorde][0]
                    elif capa == "ACORDES":
                        extra = acorde
                    elif capa in ("TIMBAL", "ROLL"):
                        extra = paso % 2
                    carril = CARRILES.index("TIMBAL" if capa == "ROLL" else capa.replace(" MAL", ""))
                    lista.append([round(t, 5), carril, paso, round(fuerza, 3), capa, extra])
    lista.sort(key=lambda g: g[0])
    return lista


def mapa_glitch(t):
    """Segundo que se ve/oye durante el glitch: trozos que se repiten, cada vez más cortos."""
    g0, g1 = GLITCH
    if not (g0 <= t < g1):
        return t
    k = (t - g0) / (g1 - g0)
    largo = PASO * 2 if k < 0.35 else PASO if k < 0.7 else PASO / 2
    bloque = largo * 3
    return g0 + ((t - g0) // bloque) * bloque + (t - g0) % largo


# ------------------------------------------------------------------ síntesis
def poner(destino, s, t, gan=1.0, lado=0.0):
    a = int(t * SR)
    if a >= N or a < 0:
        return
    n = min(len(s), N - a)
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


def kick(fuerza=1.0):
    """Kick redondo de reguetón: seno que cae de 160 a 48 Hz, con cuerpo y un clic arriba."""
    t = np.arange(int(0.3 * SR)) / SR
    f = 48 + 112 * np.exp(-t * 38)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    s += filtro(rng.normal(0, 1, len(t)), 1800, 9000) * np.exp(-t * 320) * 0.45
    return np.tanh(2.0 * s) * fuerza


def caja(fuerza=1.0):
    """Caja seca y brillante (la del dembow): tono de 210 Hz + ruido filtrado, muy corta."""
    t = np.arange(int(0.2 * SR)) / SR
    tono = np.sin(2 * np.pi * 210 * t * (1 + 0.2 * np.exp(-t * 60))) * np.exp(-t * 32) * 0.55
    ruido = filtro(rng.normal(0, 1, len(t)), 1800, 10000) * np.exp(-t * 26)
    return (tono + ruido) * np.minimum(1, t / 0.001) * fuerza


def timbal(tono, fuerza=1.0):
    """Timbal: parche afinado (hembra aguda, macho grave) con su anillo metálico y el golpe del palo."""
    t = np.arange(int(0.32 * SR)) / SR
    f0 = 430 if tono else 330
    f = f0 * (1 + 0.12 * np.exp(-t * 45))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10)
    s += 0.35 * np.sin(2 * np.pi * f0 * 1.52 * t) * np.exp(-t * 15)
    s += filtro(rng.normal(0, 1, len(t)), 2500, 12000) * np.exp(-t * 200) * 0.6
    return s * 0.55 * fuerza


def pluck(acorde, fuerza=1.0):
    """Acorde cortito: cada nota con armónicos que se apagan rápido (los agudos antes), como una cuerda."""
    t = np.arange(int(0.5 * SR)) / SR
    s = np.zeros(len(t))
    for nota in ACORDES[acorde][1]:
        f = hz(nota)
        for k in range(1, 8):
            s += np.sin(2 * np.pi * f * k * t + k) / k * np.exp(-t * (6 + 2.6 * k))
    return s * np.minimum(1, t / 0.002) * 0.16 * fuerza


def shaker(fuerza):
    t = np.arange(int(0.1 * SR)) / SR
    r = filtro(rng.normal(0, 1, len(t)), 5000, 15000)
    return r * np.minimum(1, t / 0.012) * np.exp(-t * 45) * 0.4 * fuerza


def bajo(lista):
    """Bajo sub: un seno por nota (mono), que suena hasta la nota siguiente o 3 semicorcheas."""
    x = np.zeros(N)
    notas = [(t, extra, capa) for t, _c, _p, _f, capa, extra in lista if capa in ("BAJO", "BAJO MAL")]
    for i, (t, nota, capa) in enumerate(notas):
        a = int(t * SR)
        largo = PASO * (8 if capa == "BAJO MAL" else 3)
        b = min(N, int(notas[i + 1][0] * SR) if i + 1 < len(notas) else N, a + int(largo * SR))
        n = b - a
        tt = np.arange(n) / SR
        s = np.sin(2 * np.pi * hz(nota) * tt) + 0.18 * np.sin(4 * np.pi * hz(nota) * tt)
        env = np.minimum(1, tt / 0.004) * np.exp(-tt * (1.0 if capa == "BAJO MAL" else 3.0))
        env *= np.minimum(1, (n - np.arange(n)) / (0.01 * SR))           # suelta sin clic
        x[a:b] += s * env
    return np.tanh(1.4 * x) * 0.8


def subida_y_golpe():
    """Subida de ruido y tono antes del drop, y el platillo al caer."""
    x = np.zeros((N, 2))
    dur = T_DROP - T_SUBIDA
    t = np.arange(int(dur * SR)) / SR
    k = t / dur
    ruido = rng.normal(0, 1, len(t))
    barrido = np.zeros_like(ruido)
    trozo = int(0.05 * SR)
    for a in range(0, len(t), trozo):
        f = 400 * (9000 / 400) ** (a / len(t))
        barrido[a:a + trozo] = filtro(ruido[a:a + trozo * 2], f * 0.6, f * 1.6)[:len(barrido[a:a + trozo])]
    tono = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2 * k)) / SR)
    sube = barrido * 0.5 + tono * 0.12
    sube[int((dur - 2 * PASO) * SR):] = 0           # silencio justo antes del drop
    poner(x, sube * k ** 2.2, T_SUBIDA, 0.5)
    t = np.arange(int(2.2 * SR)) / SR
    platillo = filtro(rng.normal(0, 1, len(t)), 3500, 15000) * np.exp(-t * 2.4) * 0.5
    poner(x, platillo, T_DROP, 0.6, -0.4)
    poner(x, platillo, T_DROP + 0.01, 0.4, 0.6)
    return x


def sonido(lista):
    bat = np.zeros((N, 2))
    mel = np.zeros((N, 2))
    for t, carril, paso, fuerza, capa, extra in lista:
        capa = capa.replace(" MAL", "")
        if capa == "KICK":
            poner(bat, kick(fuerza), t, 0.75)
        elif capa == "CAJA":
            poner(bat, caja(fuerza), t, 0.8, lado=0.05)
        elif capa in ("TIMBAL", "ROLL"):
            poner(bat, timbal(extra, fuerza), t, 0.75, lado=0.35 if extra else -0.35)
        elif capa == "SHAKER":
            poner(bat, shaker(fuerza), t, 1.0, lado=0.25 if paso % 4 else -0.15)
        elif capa == "ACORDES":
            poner(mel, pluck(extra, fuerza), t, 0.6, lado=0.15 if paso % 2 else -0.15)

    sub = bajo(lista)
    mel = ping_pong(mel, 3 * PASO, 0.35, 4)
    mel = np.stack([eco(mel[:, c], 2.0, 0.3, 2.4, 5 + c) for c in (0, 1)], 1)
    bat[:, 0] = eco(bat[:, 0], 0.6, 0.12, 9.0, 3)
    bat[:, 1] = eco(bat[:, 1], 0.6, 0.12, 9.0, 4)
    mezcla = bat + mel + sub[:, None] * 0.5 + subida_y_golpe()

    # Rayón de disco: el beat cuadrado va y viene bajo la aguja (dos vaivenes) y se queda en silencio
    m0, m1, n = int(M0 * SR), int(M1 * SR), int(RAYON * SR)
    tau = np.arange(n) / SR
    velocidad = 1.8 * np.cos(2 * np.pi * 4.0 * tau) * np.linspace(1, 0.6, n)
    lee = np.clip(m0 + np.cumsum(velocidad).astype(int), 0, N - 1)
    raya = mezcla[lee] * np.minimum(1, np.linspace(1.5, 0, n))[:, None]
    raya += filtro(rng.normal(0, 1, n), 1200, 6000)[:, None] * np.abs(velocidad)[:, None] * 0.04
    mezcla[m0:m1] = 0
    mezcla[m0:m0 + n] = raya

    g0, g1 = int(GLITCH[0] * SR), int(GLITCH[1] * SR)
    fuente = np.array([mapa_glitch(i / SR) for i in range(g0, g1)])
    trozo = mezcla[(fuente * SR).astype(int)]
    trozo = np.round(trozo * 32) / 32
    trozo = trozo[(np.arange(len(trozo)) // 4) * 4]
    mezcla[g0:g1] = trozo

    # Cierre: un último kick con el acorde de La menor que se aleja y el sub que cae de tono
    cola = np.zeros((N, 2))
    t = np.arange(int(2.8 * SR)) / SR
    cae = np.sin(2 * np.pi * np.cumsum(hz(33) * 2 ** (-t * 0.35)) / SR) * np.exp(-t * 1.0)
    poner(cola, cae * 0.6, GLITCH[1])
    poner(cola, kick(1.0), GLITCH[1], 0.8)
    poner(cola, pluck(0), GLITCH[1], 0.8)
    poner(cola, timbal(1), GLITCH[1], 0.5, 0.3)
    cola = np.stack([eco(cola[:, c], 2.4, 0.35, 2.2, 11 + c) for c in (0, 1)], 1)
    mezcla[g1:] = cola[g1:]

    mezcla = np.tanh(mezcla * 1.1)
    mezcla[:int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))[:, None]
    fade = int(0.6 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return mezcla / np.max(np.abs(mezcla)) * 0.5    # pico a −6 dB: espacio para la voz


# ------------------------------------------------------------------ textos (también guion de la voz)
def textos():
    salida = []
    for c0, (nc, texto, _capas, toma) in zip(INICIOS, SECCIONES):
        t0, t1 = c0 * COMPAS, (c0 + nc) * COMPAS
        palabras = [{"txt": p.replace("*", ""), "clave": p.startswith("*")} for p in texto.split()]
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
        "golpes": [g[:5] for g in lista if not M0 <= g[0] < M1],     # tras el rayón no se ve nada
        "secciones": secciones,
        "glitch": list(GLITCH), "cierre": CIERRE, "cierreTexto": CIERRE_TEXTO,
        "hueco": T_HUECO, "antes": [A0, A1], "capasAntes": MALO, "malo": [inicio("malo"), M1],
        "dembow": DEMBOW, "paletas": PALETAS, "paleta": PALETA,
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
    print(f"{len(lista)} golpes, {TOTAL:.1f} s, paleta {PALETA}")
    for ext in (".json", ".wav", "-guion.txt"):
        print(tmp / f"{NOMBRE}{ext}")


if __name__ == "__main__":
    main()
