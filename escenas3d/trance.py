#!/usr/bin/env python3
"""Neon Keys · "¿Quieres aprender a hacer esto?": un trance bailable y poderoso armado desde cero en el
secuenciador 3D de la serie de beats (ADR-022, ADR-023, ADR-027 → ADR-030).

Igual que psytrance.py: una sola tabla (PATRONES + SECCIONES) manda en la imagen y en el sonido. 138 BPM en Re
menor, acordes Rem – Si♭ – Fa – Do. Carriles KICK · BAJO · CLAP · HATS · PAD · ARP; el lead (supersaw de Surge XT,
ADR-026) no tiene carril: en la escena son los láseres. Por eso corre en `.venv-synth`.
  - KICK de trance: gordo, con cola corta, afinado en Fa
  - BAJO a contratiempo (bom-BA): una corchea entre kick y kick
  - CLAP en 2 y 4; HATS: open hat a contratiempo + cerrados en semicorcheas bajitos
  - PAD: supersaw propio; primero los acordes largos, luego cortado en semicorcheas (el "trance gate") y con delay
  - ARP: pluck que corre por el acorde, con eco
  - LEAD: melodía propia en supersaw (3-3-2), con sidechain en todo lo que no es batería
Abre con el trance terminado sonando ("Seguimos con los tutoriales… ¿Quieres aprender a hacer esto?"), se frena con
un tape stop y se arma capa por capa; la voz nombra las notas de cada parte (todo en Re menor).
Hay respiros sin voz para que se oiga la música (ADR-027).

Uso:
    .venv-synth/bin/python escenas3d/trance.py        # → out/.tmp/beat-trance.json, .wav y -guion.txt
    cd escenas3d && node grabar.js escenas/trance.html out/videos/beats/beat-trance.mp4 \\
        --datos out/.tmp/beat-trance.json --audio out/.tmp/beat-trance.wav
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
NOMBRE = "beat-trance"

BPM = 138
BEAT = 60 / BPM
COMPAS = 4 * BEAT
PASO = BEAT / 4                  # semicorchea

# Carriles de adelante (cerca de la cámara) hacia atrás
CARRILES = ["KICK", "BAJO", "CLAP", "HATS", "PAD", "ARP"]
# Acordes por compás (frase de 4): raíz del bajo y notas del pad
# (nota y notas = lo que se ve en pantalla cuando la voz las nombra)
ACORDES = [
    {"nombre": "Rem", "bajo": 38, "pad": [62, 65, 69, 74], "nota": "RE", "notas": "RE · FA · LA"},
    {"nombre": "Si♭", "bajo": 34, "pad": [62, 65, 70, 74], "nota": "SI♭", "notas": "SI♭ · RE · FA"},
    {"nombre": "Fa", "bajo": 41, "pad": [60, 65, 69, 72], "nota": "FA", "notas": "FA · LA · DO"},
    {"nombre": "Do", "bajo": 36, "pad": [60, 64, 67, 72], "nota": "DO", "notas": "DO · MI · SOL"},
]
KICK_HZ = 43.65                  # el kick termina afinado en Fa1 (dentro de Re menor)
# Trance gate: semicorcheas en las que el pad suena (el resto, cortado)
GATE = [0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 14]
# Arpegio: qué nota del acorde (0-3, una octava arriba) toca cada semicorchea
ARP = [0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 3, 2, 1]
# Lead (melodía propia, 4 compases en semicorcheas): (paso, nota, duración en pasos)
LEAD = [
    (0, 74, 3), (3, 77, 3), (6, 81, 2), (8, 79, 2), (10, 77, 2), (12, 76, 2), (14, 77, 2),
    (16, 74, 3), (19, 77, 3), (22, 82, 2), (24, 81, 4), (28, 77, 4),
    (32, 72, 3), (35, 77, 3), (38, 81, 2), (40, 84, 2), (42, 81, 2), (44, 79, 2), (46, 77, 2),
    (48, 76, 3), (51, 79, 3), (54, 84, 4), (58, 81, 2), (60, 79, 4),
]
PATRONES = {
    "KICK": {0: 1, 4: 1, 8: 1, 12: 1},
    "BAJO": {2: 1, 6: 1, 10: 1, 14: 1},
    "CLAP": {4: 1, 12: 1},
    "HATS": {p: (1.0 if p % 4 == 2 else 0.4) for p in range(16)},
    "PAD LARGO": {0: 1, 4: 0.9, 8: 0.9, 12: 0.9},              # acordes largos (un bloque por tiempo)
    "PAD": {p: (1.0 if p % 4 == 0 else 0.75) for p in GATE},    # cortado en semicorcheas
    "ARP": {p: 0.45 + 0.3 * ARP[p] for p in range(16)},         # la altura del bloque = la nota
    "ROLL": {},                                                  # redoble de caja en el break (lo arma golpes())
    "LEAD": {},                                                  # sin carril: los láseres (lo arma golpes())
}
BASE = ["KICK", "BAJO"]
BATERIA = ["KICK", "BAJO", "CLAP", "HATS"]
TODAS = ["KICK", "BAJO", "CLAP", "HATS", "PAD", "ARP"]
DROP = TODAS + ["LEAD"]
# El trance terminado del gancho: las mismas capas con " INTRO" (en la escena ya están armadas en el cuadro 0 y se
# caen con el tape stop)
INTRO = [c + " INTRO" for c in DROP]

# Secciones: (compases, texto con *palabra clave*, capas que suenan, toma de cámara). Una idea por sección; el
# texto es también el guion de la voz. Texto vacío = respiro: solo suena la música (a 138 BPM, 1 compás = 1.74 s).
# Los acordes van por compás contando desde el inicio (Rem en los compases 0, 4, 8…): las secciones que nombran
# notas empiezan en el acorde que nombran, y el drop cae en Rem (compás 40).
SECCIONES = [
    (2, "Seguimos con los tutoriales de *música electrónica.*", INTRO, "gancho"),
    (3, "¿Quieres aprender a hacer *esto?*", INTRO, "gancho2"),
    (1, "Vamos *paso a paso.*", INTRO, "cero"),                   # tape stop y silencio
    (2, "El *kick,* afinado en *Fa:* cuatro golpes, gordo y cortito.", ["KICK"], "kick"),
    (2, "El *bajo* arranca en *Re* y va entre kick y kick.", BASE, "bajo"),
    (2, "", BASE, "respiro1"),
    (2, "Cambia con cada acorde: *Re, Si bemol, Fa y Do.*", BASE, "bajo2"),
    (2, "*Clap* en el dos y el cuatro, *hats* a contratiempo.", BATERIA, "clap"),
    (2, "Los acordes: *Re menor,* Si bemol, Fa y Do.", BATERIA + ["PAD LARGO"], "acordes"),
    (2, "Cada acorde son tres notas: Fa es *Fa, La, Do.*", BATERIA + ["PAD LARGO"], "acordes2"),
    (2, "El truco del trance: el pad *cortado* en semicorcheas.", BATERIA + ["PAD"], "gate"),
    (2, "Y un *delay* al pad: cada corte rebota izquierda, derecha.", BATERIA + ["PAD"], "delay"),
    (2, "Los rebotes rellenan los huecos: suena más *grande.*", BATERIA + ["PAD"], "delay2"),
    (2, "", BATERIA + ["PAD"], "respiro2"),
    (2, "*Arpegio:* el acorde nota por nota, *Re, Fa, La, Re.*", TODAS, "arp"),
    (2, "Una octava más arriba, en semicorcheas, y con *eco.*", TODAS, "arp2"),
    (2, "*Sidechain:* cada vez que suena el kick, le baja el volumen a todo lo demás.", TODAS, "sidechain"),
    (2, "Bajo, acordes y arpegio se agachan y suben: así *respira.*", TODAS, "sidechain2"),
    (4, "Quita el kick… y deja que *suba.*", ["PAD LARGO", "ARP", "ROLL", "LEAD"], "break"),
    (4, "¡A disfrutar el *beat!*", DROP, "drop"),
    (2, "", DROP, "drop2"),
    (2, "*Guárdalo* para tu próxima sesión.", DROP, "drop3"),
]
COMPASES_CIERRE = 2
CIERRE_TEXTO = "Sígueme para más"

# Paleta del video (ADR-023: cada beat lleva la suya). Amanecer de festival: noche azul profunda que se abre a
# naranja, dorado y rosa en el horizonte. El cierre NK sigue en cian/magenta: es la marca.
PALETAS = {
    "amanecer": {
        "nombre": "Amanecer de festival", "fondo": ["#050821", "#3A1238"], "piso": "#FF6A3D",
        "filo": "#FF9A4A", "sol": ["#FFD24A", "#FF3D7A"], "estrellas": "#CFE0FF", "texto": "#FFC46B",
        "clave": "#FF4FA0", "acento": "#3D7BFF",
        "capas": {"KICK": "#FF8A3D", "BAJO": "#FF3D7A", "CLAP": "#FFD24A", "HATS": "#7FD8FF",
                  "PAD": "#B06BFF", "ARP": "#3DE0FF"},
        "laseres": ["#FFD24A", "#FF4FA0", "#3DE0FF", "#FF8A3D"],
    },
}
PALETA = "amanecer"

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
B0, B1 = rango("break")
C0, C1 = rango("cero")
TAPE = 0.9                                        # segundos que tarda el tape stop en frenar todo

rng = np.random.default_rng(138)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
N = int(TOTAL * SR)


# ------------------------------------------------------------------ golpes (los mismos para imagen y sonido)
def golpes():
    """Lista de golpes [t, carril, paso, fuerza, capa, extra]; extra = nota MIDI (bajo, arp, lead) o duración."""
    lista = []
    for c0, (nc, _texto, capas, toma) in zip(INICIOS, SECCIONES):
        for compas in range(c0, c0 + nc):
            acorde = ACORDES[compas % 4]
            t_compas = compas * COMPAS
            for capa in capas:
                base = capa.replace(" INTRO", "")
                if base == "LEAD":
                    # La melodía va por frases de 4 compases (empieza en el primer compás de la sección; el gancho
                    # ocupa varias secciones y la cuenta desde el compás 0)
                    k = (compas - (0 if capa.endswith(" INTRO") else c0)) % 4
                    for paso, nota, dur in LEAD:
                        if k * 16 <= paso < (k + 1) * 16:
                            t = t_compas + (paso - k * 16) * PASO
                            if t < GLITCH[0]:
                                lista.append([round(t, 5), -1, paso % 16, 1.0, capa, [nota, dur * PASO]])
                    continue
                patron = PATRONES[base]
                if base == "ROLL":
                    # Redoble de caja en los dos últimos compases del break: negras → corcheas → semicorcheas,
                    # creciendo; los dos últimos pasos en silencio antes del drop
                    k = compas - (c0 + nc - 2)
                    if k < 0:
                        continue
                    pasos = range(0, 16, 2) if k == 0 else range(14)
                    patron = {p: 0.3 + 0.35 * k + 0.3 * p / 16 for p in pasos}
                for paso, fuerza in patron.items():
                    t = t_compas + paso * PASO
                    if t >= GLITCH[1]:
                        continue
                    extra = 0
                    if base == "BAJO":
                        extra = acorde["bajo"]
                    elif base == "ARP":
                        extra = acorde["pad"][ARP[paso]] + 12
                    carril = CARRILES.index({"ROLL": "CLAP", "PAD LARGO": "PAD"}.get(base, base))
                    lista.append([round(t, 5), carril, paso, round(fuerza, 3), capa, extra])
    lista.sort(key=lambda g: g[0])
    return lista


def mapa_vis(t):
    """Segundo que se ve: en el tape stop la imagen también se frena hasta congelarse; luego, el glitch."""
    if C0 <= t < C1:
        tau = min(t - C0, TAPE)
        return C0 + tau - tau ** 2 / (2 * TAPE)
    return mapa_glitch(t)


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
    if s.ndim == 2:                               # ya viene en estéreo
        destino[a:a + n] += s[:n] * gan
        return
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


def kick(fuerza=1.0):
    """Kick de trance: golpe de 220 Hz que cae a Fa1 con cuerpo, clic arriba, saturado y cortado a ~300 ms."""
    t = np.arange(int(0.3 * SR)) / SR
    f = KICK_HZ + 170 * np.exp(-t * 34) + 30 * np.exp(-t * 9)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    s += filtro(rng.normal(0, 1, len(t)), 2000, 11000) * np.exp(-t * 400) * 0.35
    s = np.tanh(2.6 * s)
    s[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return s * fuerza


def sierra(f, t, voces=7, abrir=0.18):
    """Supersaw propio: varias sierras desafinadas (sin aliasing: suma de armónicos hasta 9 kHz)."""
    s = np.zeros_like(t)
    for v in range(voces):
        d = (v - (voces - 1) / 2) / ((voces - 1) / 2) * abrir         # ± semitonos
        fv = f * 2 ** (d / 12)
        fase = rng.uniform(0, 2 * np.pi)
        for k in range(1, 30):
            if fv * k > 9000:
                break
            s += np.sin(2 * np.pi * fv * k * t + fase * k) / k
    return s / voces


def nota_bajo(nota, fuerza=1.0):
    """Bajo a contratiempo: sierra + sub, filtro que se abre al tocar; dura casi una corchea."""
    dur = PASO * 1.8
    t = np.arange(int(dur * SR)) / SR
    f = hz(nota)
    s = sierra(f, t, voces=3, abrir=0.08)
    s = filtro(s, 30, 400) + filtro(s, 400, 2200) * np.exp(-t * 30) * 0.8
    s += 0.6 * np.sin(2 * np.pi * f * t)
    s = np.tanh(1.6 * s)
    env = np.minimum(1, t / 0.003) * np.clip((dur - t) / 0.02, 0, 1) * (0.75 + 0.25 * np.exp(-t * 12))
    return s * env * fuerza


def acorde_pad(notas, dur, gate=None):
    """Pad supersaw de un compás. gate = semicorcheas en las que suena (trance gate)."""
    t = np.arange(int(dur * SR)) / SR
    s = sum(sierra(hz(m), t) for m in notas) / len(notas)
    s = np.stack([filtro(s, 180, 5200), filtro(np.roll(s, 211), 180, 5200)], 1)   # un poco de ancho
    env = np.minimum(1, t / 0.02) * np.clip((dur - t) / 0.05, 0, 1)
    if gate is not None:
        g = np.zeros_like(t)
        for p in gate:
            a, b = int(p * PASO * SR), int((p + 0.82) * PASO * SR)
            seg = np.arange(b - a) / SR
            g[a:b] = np.minimum(1, seg / 0.003) * np.clip((len(seg) / SR - seg) / 0.008, 0, 1)
        env = env * g
    return s * env[:, None]


def pluck(nota):
    """Pluck del arpegio: sierra con filtro que se cierra muy rápido."""
    t = np.arange(int(0.32 * SR)) / SR
    f = hz(nota)
    s = sierra(f, t, voces=2, abrir=0.06)
    s = filtro(s, 200, 1200) + filtro(s, 1200, 8000) * np.exp(-t * 28)
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 11)


def caja():
    """Caja del redoble: ruido con cuerpo."""
    t = np.arange(int(0.18 * SR)) / SR
    s = filtro(rng.normal(0, 1, len(t)), 1200, 9000) * np.exp(-t * 22)
    s += np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.6
    return s


def subida_y_golpe():
    """Ruido blanco que sube en los 4 compases del break (silencio justo antes del drop) y el platillo al caer.
    El mismo platillo marca el inicio del gancho."""
    x = np.zeros((N, 2))
    dur = B1 - B0
    t = np.arange(int(dur * SR)) / SR
    partes = np.array_split(rng.normal(0, 1, len(t)), 40)
    ruido = np.concatenate([filtro(p, 250 + 8000 * (i / 39) ** 2, 1200 + 12000 * (i / 39) ** 2)
                            for i, p in enumerate(partes)]) * (t / t[-1]) ** 2.5
    ruido[int((dur - 2 * PASO) * SR):] = 0
    poner(x, ruido, B0, 0.5, -0.2)
    poner(x, np.roll(ruido, 307), B0, 0.5, 0.2)
    t = np.arange(int(2.6 * SR)) / SR
    platillo = filtro(rng.normal(0, 1, len(t)), 3000, 14000) * np.exp(-t * 2.0)
    for t0 in (0.0, T_DROP):
        poner(x, platillo, t0, 0.32, -0.4)
        poner(x, platillo, t0 + 0.01, 0.22, 0.6)
    return x


def tape_stop(x, t0, dur):
    """Frena la cinta: desde t0 la velocidad baja de 1 a 0 en dur segundos (el tono cae) y luego silencio."""
    a, n = int(t0 * SR), int(dur * SR)
    tau = np.arange(n) / SR
    fuente = a + (tau - tau ** 2 / (2 * dur)) * SR
    i = fuente.astype(int)
    fr = fuente - i
    y = x[i] * (1 - fr)[:, None] + x[i + 1] * fr[:, None]
    y *= np.linspace(1, 0.2, n)[:, None]
    x[a:a + n] = y
    x[a + n:int(C1 * SR)] = 0


def sonido(lista):
    bombo = np.zeros((N, 2))
    bajo = np.zeros((N, 2))
    bat = np.zeros((N, 2))
    pad = np.zeros((N, 2))
    arp = np.zeros((N, 2))
    lead = []
    for t, _carril, paso, fuerza, capa, extra in lista:
        base = capa.replace(" INTRO", "")
        compas = int(round(t / COMPAS - paso / 16))
        if base == "KICK":
            poner(bombo, kick(fuerza), t)
        elif base == "BAJO":
            poner(bajo, nota_bajo(extra, fuerza), t)
        elif base == "CLAP":
            poner(bat, clap(), t, 0.8, 0.05)
        elif base == "ROLL":
            poner(bat, caja(), t, 0.5 * fuerza, 0.1 * np.sin(paso))
        elif base == "HATS":
            if paso % 4 == 2:
                poner(bat, hat(1.0, True)[:int(0.16 * SR)], t, 0.6, 0.25)
            else:
                poner(bat, hat(0.7), t, 0.4, -0.3)
        elif base == "PAD LARGO" and paso == 0:
            poner(pad, acorde_pad(ACORDES[compas % 4]["pad"], COMPAS + 0.05), t)
        elif base == "PAD" and paso == 0:
            poner(pad, acorde_pad(ACORDES[compas % 4]["pad"], COMPAS, GATE), t)
        elif base == "ARP":
            poner(arp, pluck(extra), t, 0.5, 0.5 * np.sin(paso * 0.9))
        elif base == "LEAD":
            nota, dur = extra
            vel = 115 if t >= T_DROP or t < C1 else 90
            lead += [(t, nota, vel, dur * 0.95), (t, nota - 12, vel - 20, dur * 0.95)]
    fx = subida_y_golpe()

    print("Surge: Super (lead)")
    lead = tocar(lead, "Super", N, gan_db=-6)
    # En el break el lead suena filtrado (lejos) y se va abriendo
    b0, b1 = int(B0 * SR), int(B1 * SR)
    trozos = np.array_split(np.arange(b0, b1), 32)
    for i, idx in enumerate(trozos):
        for c in (0, 1):
            lead[idx, c] = filtro(lead[idx, c], 120, 900 + 7000 * (i / 31) ** 2) * (0.55 + 0.45 * i / 31)
    lead = ping_pong(lead, BEAT * 0.75, 0.3, 4)
    arp = ping_pong(arp, BEAT * 0.75, 0.42, 6)
    # Delay en el pad desde la sección "delay": cada corte del gate rebota izquierda ↔ derecha (antes suena seco)
    d0 = int(inicio("delay") * SR)
    pad[d0:] = ping_pong(pad, BEAT * 0.75, 0.38, 5)[d0:]
    pad = np.stack([eco(pad[:, k], 2.2, 0.3, 2.5, 5 + k) for k in (0, 1)], 1)
    lead = np.stack([eco(lead[:, k], 2.6, 0.22, 2.2, 7 + k) for k in (0, 1)], 1)

    # Sidechain: pad, arp, lead y bajo se agachan con cada kick (el "respiro" del trance)
    tk = np.array([g[0] for g in lista if g[4].startswith("KICK")])
    bombeo = np.ones(N)
    tt = np.arange(N) / SR
    for k in tk:
        a = int(k * SR)
        b = min(N, a + int(BEAT * SR))
        bombeo[a:b] = np.minimum(bombeo[a:b], 1 - 0.7 * np.exp(-(tt[a:b] - k) * 11))
    bombeo = bombeo[:, None]

    # Mezcla: kick al frente; los niveles se miden en el drop, con todo sonando
    a, b = int(T_DROP * SR), int(GLITCH[0] * SR)
    nivel = lambda x: x / (np.sqrt(np.mean(x[a:b] ** 2)) + 1e-9)
    bat = np.stack([eco(bat[:, k], 0.8, 0.12, 8.0, 3 + k) for k in (0, 1)], 1)
    mezcla = (nivel(bombo) * 0.36 + (nivel(bajo) * 0.2 + nivel(pad) * 0.13 + nivel(arp) * 0.09
              + nivel(lead) * 0.2) * bombeo + nivel(bat) * 0.13 + fx * 0.35)

    # La construcción va 1.5 dB abajo del gancho y del drop: así el drop pega más
    c1, b0 = int(C1 * SR), int(B0 * SR)
    mezcla[c1:b0] *= 0.84

    tape_stop(mezcla, C0 + 0.05, TAPE)

    # Glitch: trozos que se repiten, bitcrush y menos resolución
    g0, g1 = int(GLITCH[0] * SR), int(GLITCH[1] * SR)
    fuente = np.array([mapa_glitch(i / SR) for i in range(g0, g1)])
    trozo = mezcla[(fuente * SR).astype(int)]
    trozo = np.round(trozo * 32) / 32
    mezcla[g0:g1] = trozo[(np.arange(len(trozo)) // 4) * 4]

    # Cierre: un último kick y el acorde de Re menor que se queda sonando con eco
    cola = np.zeros((N, 2))
    poner(cola, kick(1.2), GLITCH[1])
    poner(cola, nota_bajo(38) * 1.0, GLITCH[1] + 2 * PASO)
    poner(cola, acorde_pad(ACORDES[0]["pad"], 2.4) * np.exp(-np.arange(int(2.4 * SR)) / SR * 1.4)[:, None], GLITCH[1])
    cola = np.stack([eco(cola[:, c], 2.4, 0.35, 2.2, 11 + c) for c in (0, 1)], 1)
    mezcla[g1:] = cola[g1:] * 0.5

    mezcla = np.tanh(mezcla * 0.6)                  # apenas toca el límite: fuerte pero limpio
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
    mudos = lambda g: C0 + TAPE <= g[0] < C1                     # tras el tape stop no suena ni se ve nada
    datos = {
        "total": TOTAL, "fps": FPS, "bpm": BPM, "beat": BEAT, "compas": COMPAS, "paso": PASO,
        "carriles": CARRILES, "patrones": PATRONES,
        # cuándo entra cada carril ya en la construcción (sin contar el gancho)
        "entrada": {c: next(g[0] for g in lista if g[1] == i and " INTRO" not in g[4]) for i, c in enumerate(CARRILES)},
        "golpes": [g[:5] for g in lista if g[1] >= 0 and not mudos(g)],
        "lead": [[g[0], *g[5]] for g in lista if g[4].replace(" INTRO", "") == "LEAD" and not mudos(g)],
        "acordes": [a["nombre"] for a in ACORDES],
        "notaBajo": [a["nota"] for a in ACORDES], "notasAcorde": [a["notas"] for a in ACORDES],
        "secciones": secciones,
        "glitch": list(GLITCH), "cierre": CIERRE, "cierreTexto": CIERRE_TEXTO,
        "cero": [C0, C1], "tape": TAPE, "breakdown": [B0, B1],
        "marcas": [0, 4, 8, 12], "paletas": PALETAS, "paleta": PALETA,
        "mapa": [round(mapa_vis(f / FPS), 4) for f in range(total_cuadros + 1)],
    }
    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / f"{NOMBRE}.json").write_text(json.dumps(datos), encoding="utf-8")
    escribir_wav(tmp / f"{NOMBRE}.wav", sonido(lista))
    # Guion para la IA de voz (ADR-025): solo las frases, en orden y sin segundos; los respiros no llevan voz
    guion = ["Guion de voz — ¿Quieres aprender a hacer esto? (trance)", "",
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
