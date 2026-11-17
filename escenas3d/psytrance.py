#!/usr/bin/env python3
"""Neon Keys · "¿Cómo se hace un buen psytrance?": el secuenciador 3D de la serie de beats (ADR-022, ADR-023) con
el galope del psytrance por dentro (ADR-027).

Igual que reggaeton.py: una sola tabla (PATRONES + SECCIONES) manda en la imagen y en el sonido. 145 BPM en Fa♯
menor. Batería y bajo son síntesis propia; el acid sale de Surge XT (ADR-026), así que corre en `.venv-synth`.
  - KICK corto y duro (se corta antes de la siguiente semicorchea: deja lugar al bajo)
  - BAJO rodante: tres semicorcheas entre bombo y bombo (K-B-B-B), sierra que se abre en cada nota
  - CLAP en 2 y 4, OPEN HAT a contratiempo, HATS en semicorcheas, ACID en semicorcheas (preset "Acidofil")
Abre con un psytrance mal hecho (kick largo y bajo encima: todo embarrado) que se apaga cerrando el filtro; luego se
arma el bueno capa por capa. Hay secciones sin texto ("respiros") para que la música se escuche sola: un usuario se
quejó de que en el techno la voz no dejaba oírla.

Uso:
    .venv-synth/bin/python escenas3d/psytrance.py      # → out/.tmp/beat-psytrance.json, .wav y -guion.txt
    cd escenas3d && node grabar.js escenas/psytrance.html out/pruebas/beats/beat-psytrance.mp4 \\
        --datos out/.tmp/beat-psytrance.json --audio out/.tmp/beat-psytrance.wav
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.argv = sys.argv[:1]                            # techno.py lee sus propias opciones al importarse
from surge import tocar  # noqa: E402
from techno import clap, eco, escribir_wav, filtro, hat, ping_pong  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
FPS = 30
NOMBRE = "beat-psytrance"

BPM = 145
BEAT = 60 / BPM
COMPAS = 4 * BEAT
PASO = BEAT / 4                  # semicorchea

# Carriles de adelante (cerca de la cámara) hacia atrás
CARRILES = ["KICK", "BAJO", "CLAP", "OPEN HAT", "HATS", "ACID"]
# Bajo por compás (frase de 4): Fa♯1 casi siempre; el último tiempo de la frase sube a La
BAJO_FRASE = [[30] * 4, [30] * 4, [30] * 4, [30, 30, 30, 33]]
# Acid: una nota por semicorchea (Fa♯ frigio) y los acentos (más fuerte y más largo)
ACID = [54, 54, 66, 54, 55, 54, 61, 54, 54, 66, 54, 64, 54, 55, 54, 59]
ACENTO = {0, 2, 6, 9, 11, 15}
PATRONES = {
    "KICK": {0: 1, 4: 1, 8: 1, 12: 1},
    "BAJO": {p: (1.0 if p % 4 == 1 else 0.85) for p in range(16) if p % 4},
    "CLAP": {4: 1, 12: 1},
    "OPEN HAT": {2: 0.8, 6: 0.8, 10: 0.8, 14: 0.8},
    "HATS": {p: (0.8 if p % 4 == 0 else 0.55) for p in range(16)},
    "ACID": {p: 0.4 + (n - 54) / 12 * 0.9 for p, n in enumerate(ACID)},     # la altura del bloque = la nota
    "ROLL": {},                                  # redoble de clap en la subida (lo arma golpes())
    # El psytrance mal hecho: kick largo en cada tiempo y el bajo largo ENCIMA del kick (se pisan), clap en 2 y 4
    "KICK MAL": {0: 1, 4: 1, 8: 1, 12: 1},
    "BAJO MAL": {0: 1, 2: 0.8, 4: 1, 6: 0.8, 8: 1, 10: 0.8, 12: 1, 14: 0.8},
    "CLAP MAL": {4: 1, 12: 1},
}
TODAS = ["KICK", "BAJO", "CLAP", "OPEN HAT", "HATS", "ACID"]
MALO = ["KICK MAL", "BAJO MAL", "CLAP MAL"]
GALOPE = ["KICK", "BAJO"]
BATERIA = ["KICK", "BAJO", "CLAP", "OPEN HAT", "HATS"]

# Secciones: (compases, texto con *palabra clave*, capas que suenan, toma de cámara). Una idea por sección; el
# texto es también el guion de la voz. Texto vacío = respiro: solo suena la música (a 145 BPM, 1 compás = 1.66 s).
SECCIONES = [
    (2, "Si tu *psytrance* suena así…", MALO, "malo"),
    (2, "…el bajo se está comiendo tu *kick.*", MALO, "mal"),     # el beat se apaga cerrando el filtro
    (2, "El secreto: un *kick* cortito, que se corte rápido.", ["KICK"], "kick"),
    (2, "Y el *bajo* en los huecos: tres notas entre cada kick.", GALOPE, "bajo"),
    (2, "*Bom,* ta-ta-ta. Ese galope es el psytrance.", GALOPE, "galope"),
    (2, "", GALOPE, "respiro1"),
    (2, "*Clap* en el dos y el cuatro.", ["KICK", "BAJO", "CLAP"], "clap"),
    (2, "*Open* *hat* a contratiempo: empuja hacia adelante.", ["KICK", "BAJO", "CLAP", "OPEN HAT"], "openhat"),
    (2, "*Hats* en semicorcheas, bajitos.", BATERIA, "hats"),
    (2, "", BATERIA, "respiro2"),
    (2, "Ahora, el *acid:* una nota que se retuerce.", TODAS, "acid"),
    (4, "", TODAS, "respiro3"),
    (2, "Dato: viene de las fiestas de playa de *Goa,* en la India.", TODAS, "dato"),
    (2, "A 145, cada capa va en su *hueco.*", TODAS, "recap"),
    (2, "¿Así sonaba *antes?*", MALO, "antes"),
    (2, "…y así suena *ahora.*", TODAS, "ahora"),
    (2, "Quita el kick… sube la *tensión…*", ["CLAP", "HATS", "ACID", "ROLL"], "subida"),
    (4, "…y *suéltalo.*", TODAS, "drop"),
    (4, "", TODAS, "drop2"),
    (2, "*Guárdalo* para tu próxima sesión.", TODAS, "drop3"),
]
COMPASES_CIERRE = 2
CIERRE_TEXTO = "Sígueme para más"

# Paleta del video (ADR-023: cada beat lleva la suya). El cierre NK sigue en cian/magenta: es la marca.
PALETAS = {
    "uv": {
        "nombre": "Ultravioleta + verde tóxico", "fondo": ["#06020F", "#160530"], "piso": "#9D4DFF",
        "filo": "#9D4DFF", "sol": ["#C6FF1A", "#9D4DFF"], "estrellas": "#D9C2FF", "texto": "#B8FF2E",
        "clave": "#FF3DF0", "acento": "#7A3DFF",
        "capas": {"KICK": "#8A4DFF", "BAJO": "#B8FF2E", "CLAP": "#FF3DF0", "OPEN HAT": "#3DFFE0",
                  "HATS": "#E6D8FF", "ACID": "#F4FF3D"},
    },
}
PALETA = "uv"

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
A0, A1 = rango("antes")
M0, M1 = rango("mal")
APAGON = 0.7                                      # segundos en que el beat malo se apaga cerrando el filtro

rng = np.random.default_rng(145)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
N = int(TOTAL * SR)


# ------------------------------------------------------------------ golpes (los mismos para imagen y sonido)
def golpes():
    """Lista de golpes [t, carril, paso, fuerza, capa, extra]; extra = nota MIDI (bajo y acid)."""
    lista = []
    for c0, (nc, _texto, capas, toma) in zip(INICIOS, SECCIONES):
        for compas in range(c0, c0 + nc):
            ultimo = compas == c0 + nc - 1
            for capa in capas:
                patron = PATRONES[capa]
                if capa == "ROLL":
                    # Redoble de clap en el último compás de la subida: corcheas, luego semicorcheas, creciendo;
                    # los dos últimos pasos quedan en silencio antes del drop
                    patron = {p: 0.35 + 0.6 * p / 13 for p in range(14) if ultimo and (p >= 6 or p % 2 == 0)}
                t_compas = compas * COMPAS
                for paso, fuerza in patron.items():
                    t = t_compas + paso * PASO
                    if t >= GLITCH[1]:
                        continue
                    if toma == "subida" and ultimo and (capa == "CLAP" or paso >= 14):
                        continue                 # antes del drop: el redoble y luego silencio
                    extra = 0
                    if capa in ("BAJO", "BAJO MAL"):
                        extra = BAJO_FRASE[compas % 4][paso // 4]
                    elif capa == "ACID":
                        extra = ACID[paso]
                    carril = CARRILES.index("CLAP" if capa == "ROLL" else capa.replace(" MAL", ""))
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


def kick(fuerza=1.0, largo=False):
    """Kick de psytrance: golpe de 300 → 50 Hz muy rápido, clic arriba, saturado y cortado a ~170 ms.
    largo = el kick del beat malo: retumba medio segundo y se come al bajo."""
    t = np.arange(int((0.5 if largo else 0.17) * SR)) / SR
    f = 50 + 250 * np.exp(-t * 55) + 40 * np.exp(-t * 12)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (3.5 if largo else 9))
    s += filtro(rng.normal(0, 1, len(t)), 2500, 12000) * np.exp(-t * 500) * (0.15 if largo else 0.5)
    s = np.tanh(3.0 * s)
    s[-int(0.012 * SR):] *= np.linspace(1, 0, int(0.012 * SR))
    return s * fuerza


def nota_bajo(nota, fuerza=1.0, dur=PASO * 0.9, largo=False):
    """Una nota del bajo rodante: sierra (más una octava arriba, bajita) por un filtro que se abre al tocar y se
    cierra en seguida (el "tuc" de cada nota); envolvente corta para que no pise el kick."""
    t = np.arange(int(dur * SR)) / SR
    f = hz(nota)
    s = np.zeros_like(t)
    for k in range(1, 40):
        if f * k > 9000:
            break
        s += np.sin(2 * np.pi * f * k * t) / k
    s += 0.25 * np.sin(2 * np.pi * f * 2 * t)
    brillo = filtro(s, 25, 1600) * np.exp(-t * (4 if largo else 45))
    cuerpo = filtro(s, 25, 260)
    s = np.tanh(1.8 * (cuerpo + brillo * 0.9))
    env = np.minimum(1, t / 0.002) * np.exp(-t * (1.5 if largo else 7)) * np.clip((dur - t) / 0.008, 0, 1)
    return s * env * fuerza


def zap():
    """El "pew" de láser típico del psy: seno que cae de 3 kHz a 120 Hz en 0.35 s."""
    t = np.arange(int(0.35 * SR)) / SR
    f = 120 + 2900 * np.exp(-t * 14)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * 0.5


def subida_y_golpe():
    """Ruido que sube durante la subida (con silencio justo antes del drop) y el platillo al caer."""
    x = np.zeros((N, 2))
    dur = T_DROP - T_SUBIDA
    t = np.arange(int(dur * SR)) / SR
    partes = np.array_split(rng.normal(0, 1, len(t)), 32)
    ruido = np.concatenate([filtro(p, 300 + 8000 * (i / 31) ** 2, 1500 + 11000 * (i / 31) ** 2)
                            for i, p in enumerate(partes)]) * (t / t[-1]) ** 2
    ruido[int((dur - 2 * PASO) * SR):] = 0
    poner(x, ruido, T_SUBIDA, 0.45)
    t = np.arange(int(2.2 * SR)) / SR
    platillo = filtro(rng.normal(0, 1, len(t)), 3000, 14000) * np.exp(-t * 2.4)
    poner(x, platillo, T_DROP, 0.3, -0.4)
    poner(x, platillo, T_DROP + 0.01, 0.2, 0.6)
    return x


def sonido(lista):
    bombo = np.zeros((N, 2))
    bajo = np.zeros((N, 2))
    bat = np.zeros((N, 2))
    fx = np.zeros((N, 2))
    acid = []
    for t, _carril, paso, fuerza, capa, extra in lista:
        if capa == "KICK":
            poner(bombo, kick(fuerza), t)
        elif capa == "KICK MAL":
            poner(bombo, kick(fuerza, largo=True), t)
        elif capa == "BAJO":
            poner(bajo, nota_bajo(extra, fuerza), t)
        elif capa == "BAJO MAL":
            poner(bajo, nota_bajo(extra, fuerza, PASO * 2.4, largo=True), t)
        elif capa in ("CLAP", "CLAP MAL", "ROLL"):
            poner(bat, clap(), t, 0.75 * fuerza, 0.05)
        elif capa == "OPEN HAT":
            poner(bat, hat(1.0, True)[:int(0.12 * SR)], t, 0.55 * fuerza, 0.25)
        elif capa == "HATS":
            poner(bat, hat(fuerza), t, 0.6, -0.3)
        elif capa == "ACID":
            acento = paso in ACENTO
            acid.append((t, extra, 120 if acento else 85, PASO * (0.95 if acento else 0.6)))
    # Zaps de láser cada dos compases del drop
    for c in range(int(INICIOS[TOMAS.index("drop")]), int(INICIOS[-1])):
        if c % 2 == 0 and c * COMPAS < GLITCH[0]:
            poner(fx, zap(), c * COMPAS, 0.8, -0.4 if c % 4 == 0 else 0.4)
    fx += subida_y_golpe()

    print("Surge: Acidofil")
    acid = tocar(acid, "Acidofil", N)
    acid = ping_pong(acid, BEAT * 0.75, 0.35, 5)               # eco en corchea con puntillo

    # Mezcla: kick y bajo al frente (se turnan, no se pisan), acid en medio, hats y clap arriba. Los niveles se
    # miden en el drop, con todo sonando
    a, b = int(T_DROP * SR), int(GLITCH[0] * SR)
    nivel = lambda x: x / (np.sqrt(np.mean(x[a:b] ** 2)) + 1e-9)
    bat = np.stack([eco(bat[:, k], 0.7, 0.12, 8.0, 3 + k) for k in (0, 1)], 1)
    mezcla = nivel(bombo) * 0.34 + nivel(bajo) * 0.26 + nivel(bat) * 0.16 + nivel(acid) * 0.17 + fx * 0.35

    # Apagón: el beat malo se oscurece (el filtro se cierra) y baja de tono hasta quedar en silencio
    m0, n = int(M0 * SR), int(APAGON * SR)
    trozos = np.array_split(np.arange(m0, m0 + n), 24)
    for i, idx in enumerate(trozos):
        k = i / 23
        for c in (0, 1):
            mezcla[idx, c] = filtro(mezcla[idx, c], 20, 8000 * (1 - k) ** 3 + 120) * (1 - k) ** 1.5
    mezcla[m0 + n:int(M1 * SR)] = 0

    # Glitch: trozos que se repiten, bitcrush y menos resolución
    g0, g1 = int(GLITCH[0] * SR), int(GLITCH[1] * SR)
    fuente = np.array([mapa_glitch(i / SR) for i in range(g0, g1)])
    trozo = mezcla[(fuente * SR).astype(int)]
    trozo = np.round(trozo * 32) / 32
    mezcla[g0:g1] = trozo[(np.arange(len(trozo)) // 4) * 4]

    # Cierre: un último kick con el bajo y una nota de acid que se queda sonando con eco
    cola = np.zeros((N, 2))
    poner(cola, kick(1.2), GLITCH[1])
    poner(cola, nota_bajo(30, 1.0, PASO * 6, largo=True), GLITCH[1] + PASO)
    final_acid = tocar([(GLITCH[1], 54, 120, 1.6)], "Acidofil", N)
    cola = cola * 0.45 + final_acid * 0.6
    cola = np.stack([eco(cola[:, c], 2.4, 0.35, 2.2, 11 + c) for c in (0, 1)], 1)
    mezcla[g1:] = cola[g1:]

    mezcla = np.tanh(mezcla * 0.55)                 # apenas toca el límite: fuerte pero limpio
    mezcla[:int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))[:, None]
    fade = int(0.6 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return mezcla / np.max(np.abs(mezcla)) * 0.5    # pico a −6 dB: espacio para la voz


# ------------------------------------------------------------------ textos (también guion de la voz)
def textos():
    salida = []
    for c0, (nc, texto, _capas, toma) in zip(INICIOS, SECCIONES):
        t0, t1 = c0 * COMPAS, (c0 + nc) * COMPAS
        palabras = [{"txt": p.replace("*", ""), "clave": p.startswith("*")} for p in texto.split()]
        cada = min(0.33, (t1 - t0 - 0.5) / max(1, len(palabras)))
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
        "golpes": [g[:5] for g in lista if not M0 + APAGON <= g[0] < M1],     # tras el apagón no se ve nada
        "secciones": secciones,
        "glitch": list(GLITCH), "cierre": CIERRE, "cierreTexto": CIERRE_TEXTO,
        "antes": [A0, A1], "capasAntes": MALO, "malo": [inicio("malo"), M1], "apagon": APAGON,
        "marcas": [0, 4, 8, 12], "paletas": PALETAS, "paleta": PALETA,
        "mapa": [round(mapa_glitch(f / FPS), 4) for f in range(total_cuadros + 1)],
    }
    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / f"{NOMBRE}.json").write_text(json.dumps(datos), encoding="utf-8")
    escribir_wav(tmp / f"{NOMBRE}.wav", sonido(lista))
    # Guion para la IA de voz (ADR-025): solo las frases, en orden y sin segundos; los respiros no llevan voz
    guion = ["Guion de voz — ¿Cómo se hace un buen psytrance?", "",
             "Voz: ElevenLabs, todo en UN SOLO AUDIO, en este orden, con una pausa corta entre frase y frase.", ""]
    guion += [s["texto"] for s in secciones if s["texto"]] + [f"{CIERRE_TEXTO}."]
    (tmp / f"{NOMBRE}-guion.txt").write_text("\n".join(guion) + "\n", encoding="utf-8")
    print(f"{len(lista)} golpes, {TOTAL:.1f} s, drop en {T_DROP:.1f} s ({T_DROP / TOTAL:.0%})")
    for s in secciones:
        print(f"  {s['t0']:5.1f} s  {s['toma']:9s} {s['texto']}")
    for ext in (".json", ".wav", "-guion.txt"):
        print(tmp / f"{NOMBRE}{ext}")


if __name__ == "__main__":
    main()
