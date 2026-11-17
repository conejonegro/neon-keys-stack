"""Neon Keys · "¿Cómo se hace el hard techno?": beat explicado en un osciloscopio CRT (1:14).

Toda la pantalla es un osciloscopio viejo: cada instrumento es un canal cuya onda se dibuja con la envolvente
real de su pista de audio (nada suena sin verse). Arranca bajito, solo con el kick limpio, y se arma canal por
canal: kick limpio → saturado, rumble encimado → con sidechain, hats y clap, stab metálico y el sinte que grita
(estilo electro / Boys Noize). Break sin kick con la pantalla que se sobrecarga; en el drop todos los canales se quedan grandes y saturados, temblando con el beat, y cierra con un glitch que deshace la imagen.

Las secciones (y el guion de la voz) están en SECCIONES. Deja en out/.tmp/ el JSON y el WAV que usa
escenas3d/techno_voz.py para pegar la voz (`--beat beat-hardtechno`).

Uso:
    .venv/bin/python hardtechno.py                  # → out/pruebas/beats/beat-hardtechno.mp4 (sin voz)
    .venv/bin/python hardtechno.py --preview 70     # un PNG de ese segundo en out/.preview/
    # Con voz (después de techno_voz.py):
    .venv/bin/python hardtechno.py --datos out/.tmp/beat-hardtechno-voz.json \\
        --audio out/.tmp/beat-hardtechno-voz.wav --salida out/pruebas/beats/beat-hardtechno-voz.mp4
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ / "escenas3d"))
_argv, sys.argv = sys.argv, sys.argv[:1]      # techno.py lee sus propias opciones al importarse
from techno import clap, eco, escribir_wav, filtro, hat, ping_pong  # noqa: E402
sys.argv = _argv

NOMBRE = "beat-hardtechno"
TMP = RAIZ / "out" / ".tmp"

# ------------------------------------------------------------------ tiempos
SR = 44100
FPS = 30
W, H = 1080, 1920
BPM = 150
BEAT = 60 / BPM               # 0.4 s
BAR = BEAT * 4                # 1.6 s
S16 = BEAT / 4

# Capas: kick (saturado), kick_limpio, rumble, sc (sidechain al rumble), hats, clap, stab, grito, grito2 (con
# bitcrush y filtro), y las del break: stab_largo, grito_filtrado, riser, roll. Las "_limpio"/"_seco" son el
# mismo instrumento sin su proceso: cada uno entra limpio y luego se le pone lo que lo hace sonar a hard techno.
COMPLETO = ["kick", "rumble", "sc", "hats", "clap", "stab", "grito2"]
SC = ["kick", "rumble", "sc"]
BATERIA = SC + ["hats", "clap"]
BREAK = ["hats", "stab_largo", "grito_filtrado", "riser", "roll"]

# (compases, texto con *palabra clave*, capas, toma, canal en foco). Texto vacío = respiro: solo música.
# Capas como (compás 1, compás 2) = antes/después dentro de la sección.
# A 150 BPM, 2 compases = 3.2 s: frases de 9 palabras como mucho.
SECCIONES = [
    (2, "*Así* se hace el *hard techno.*", ["kick_limpio"], "intro", "kick"),    # arranca bajito, solo el kick
    (2, "El *kick:* cuatro golpes a 150 BPM.", ["kick_limpio"], "kick", "kick"),
    (2, "Limpio suena así… *saturado,* así.", (["kick_limpio"], ["kick"]), "kick2", "kick"),
    (2, "El *rumble:* un bajo grave, limpio.", ["kick", "rumble_limpio"], "rumble", "rumble"),
    (2, "Limpio casi no se oye… *distorsionado* ruge.", (["kick", "rumble_limpio"], ["kick", "rumble"]),
     "rumble2", "rumble"),
    (2, "Se empasta con el kick: *sidechain* lo aparta.", (["kick", "rumble"], SC), "sidechain", "rumble"),
    (2, "", SC, "respiro1", None),
    (2, "*Hats* limpios… y con *saturación,* más sucios.", (SC + ["hats_limpio"], SC + ["hats"]), "hats", "hats"),
    (2, "*Clap* en el dos y el cuatro… con *reverb.*", (SC + ["hats", "clap_seco"], BATERIA), "clap", "hats"),
    (2, "", BATERIA, "respiro2", None),
    (2, "Un *acorde* corto y oscuro, limpio.", BATERIA + ["stab_limpio"], "stab", "stab"),
    (2, "Con *FM* suena a metal; el *delay* lo rebota.", BATERIA + ["stab"], "stab2", "stab"),
    (2, "El sello *electro:* un sinte de sierra, simple.", BATERIA + ["stab", "grito_limpio"], "grito", "grito"),
    (2, "*Saturación,* bitcrush y filtro: ahora *grita.*", COMPLETO, "grito2", "grito"),
    (2, "", COMPLETO, "respiro3", None),
    (2, "Va entre *145 y 160 BPM:* más rápido que el techno.", COMPLETO, "dato", None),
    (4, "Quita el kick… y deja que *suba.*", BREAK, "break", None),
    (4, "*¡Suéltalo!*", COMPLETO, "drop", None),
    (2, "", COMPLETO, "drop2", None),
    (2, "*Guárdalo* para tu próxima sesión.", COMPLETO, "drop3", None),
]
GRANDES = {"intro", "drop"}           # textos que van con la letra grande del título
COMPASES_CIERRE = 2
CIERRE_TEXTO = "Sígueme para más"

INICIOS = np.cumsum([0] + [s[0] for s in SECCIONES])
TOMAS = [s[3] for s in SECCIONES]


def rango(toma):
    i = TOMAS.index(toma)
    return INICIOS[i] * BAR, INICIOS[i + 1] * BAR


INTRO = rango("intro")[1]              # el volumen sube de bajito hasta aquí
B0, B1 = rango("break")
T_DROP = rango("drop")[0]
CIERRE = INICIOS[-1] * BAR             # último golpe: la imagen se congela y el glitch la deshace
GLITCH = (CIERRE - 2 * BEAT, CIERRE)   # últimos 2 tiempos del drop
TOTAL = CIERRE + COMPASES_CIERRE * BAR + 0.4
N = int(TOTAL * SR)

# Riff del sinte que grita (Fa menor), 1 compás en semicorcheas: (paso, nota MIDI, largo en pasos)
GRITO = [(0, 65, 2), (2, 65, 1), (3, 68, 2), (5, 65, 1), (6, 70, 2), (8, 72, 3), (11, 70, 1), (12, 68, 2),
         (14, 63, 2)]

# Anotaciones en la pantalla, como las que se escriben en un osciloscopio: (toma, compás dentro, canal, texto)
ETIQUETAS = [
    ("kick2", 0, "kick", "LIMPIO"), ("kick2", 1, "kick", "SATURADO"),
    ("rumble", None, "rumble", "LIMPIO"), ("rumble2", 0, "rumble", "LIMPIO"), ("rumble2", 1, "rumble", "DISTORSIÓN"),
    ("sidechain", 0, "rumble", "SIN SIDECHAIN"), ("sidechain", 1, "rumble", "SIDECHAIN ON"),
    ("hats", 0, "hats", "LIMPIOS"), ("hats", 1, "hats", "SATURADOS"),
    ("clap", 0, "hats", "CLAP SECO"), ("clap", 1, "hats", "CLAP + REVERB"),
    ("stab", None, "stab", "ACORDE LIMPIO"), ("stab2", None, "stab", "FM + DELAY"),
    ("grito", None, "grito", "SIERRA LIMPIA"), ("grito2", None, "grito", "BITCRUSH + FILTRO"),
    ("dato", None, "kick", "150 BPM"),
]

# ------------------------------------------------------------------ colores, fuentes y pantalla (MOTION.md)
CIAN = np.array([0, 240, 255])
MAG = np.array([255, 50, 210])
VIOLETA = np.array([170, 100, 255])
RESALTE = (255, 120, 230)
FUT = "/System/Library/Fonts/Supplemental/Futura.ttc"
AVN = "/System/Library/Fonts/Avenir Next.ttc"
MENLO = "/System/Library/Fonts/Menlo.ttc"
f_titulo = ImageFont.truetype(FUT, 92, index=2)
f_sub = ImageFont.truetype(AVN, 60, index=0)
f_etiqueta = ImageFont.truetype(FUT, 34, index=2)
f_mono = ImageFont.truetype(MENLO, 28)
f_mono_s = ImageFont.truetype(MENLO, 24)

X0, X1, Y0, Y1 = 70, 1010, 360, 1560
CANALES = [  # (nombre, etiqueta, centro y, amplitud, color, capas que lo prenden)
    ("kick", "CH1 KICK", Y0 + 130, 95, MAG, {"kick", "kick_limpio"}),
    ("rumble", "CH2 RUMBLE", Y0 + 365, 85, CIAN, {"rumble", "rumble_limpio"}),
    ("hats", "CH3 HATS + CLAP", Y0 + 590, 65, CIAN, {"hats", "hats_limpio", "clap", "clap_seco", "roll"}),
    ("stab", "CH4 STAB", Y0 + 800, 65, MAG, {"stab", "stab_limpio", "stab_largo"}),
    ("grito", "CH5 GRITO", Y0 + 1015, 75, VIOLETA, {"grito", "grito_limpio", "grito2", "grito_filtrado", "riser"}),
]

rng = np.random.default_rng(150)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def seccion_en(t):
    """Índice de la sección y compás dentro de ella para el segundo t (None en el cierre)."""
    c = int(t // BAR)
    i = int(np.searchsorted(INICIOS, c, side="right") - 1)
    if i >= len(SECCIONES):
        return None, 0
    return i, c - INICIOS[i]


def capas_en(t):
    i, k = seccion_en(t)
    if i is None:
        return set()
    capas = SECCIONES[i][2]
    capas = set(capas[min(k, 1)] if isinstance(capas, tuple) else capas)
    if TOMAS[i] == "break" and k < 2:
        capas -= {"roll"}
    return capas


# ------------------------------------------------------------------ golpes (los mismos para imagen y sonido)
def golpes():
    """Lista de (t, capa, fuerza, extra). Extra = nota MIDI y largo del grito, o compás del rumble."""
    lista = []
    for c in range(INICIOS[-1]):
        t0 = c * BAR
        capas = capas_en(t0 + 0.001)
        if "rumble" in capas or "rumble_limpio" in capas:
            lista.append((t0, "rumble", 1.0, ("sc" in capas, "rumble_limpio" in capas)))
        if "riser" in capas and t0 == B0:
            lista.append((t0, "riser", 1.0, None))
        for paso in range(16):
            t = t0 + paso * S16
            if GLITCH[1] <= t or B1 - 2 * S16 <= t < B1:
                continue
            if paso % 4 == 0:
                if "kick" in capas:
                    lista.append((t, "kick", 1.0, None))
                if "kick_limpio" in capas:
                    lista.append((t, "kick_limpio", 1.0, None))
            for capa in ("hats", "hats_limpio"):
                if capa in capas:
                    lista.append((t, capa, 1.0 if paso % 4 == 2 else 0.45, paso % 4 == 2))
            for capa in ("clap", "clap_seco"):
                if capa in capas and paso in (4, 12):
                    lista.append((t, capa, 1.0, None))
            for capa in ("stab", "stab_limpio"):
                if capa in capas and paso in (3, 6, 11, 14):
                    lista.append((t, capa, 1.0, None))
            if "stab_largo" in capas and paso in (0, 6, 11):
                lista.append((t, "stab_largo", 0.8, None))
            if "roll" in capas:
                k = c - (int(B1 // BAR) - 2)
                if (k == 0 and paso % 2 == 0) or k == 1:
                    lista.append((t, "roll", 0.3 + 0.35 * k + 0.3 * paso / 16, None))
            for p, nota, largo in GRITO:
                if p != paso:
                    continue
                if "grito2" in capas:
                    lista.append((t, "grito2", 1.0, (nota, largo)))
                elif "grito" in capas:
                    lista.append((t, "grito", 1.0, (nota, largo)))
                elif "grito_limpio" in capas:
                    lista.append((t, "grito_limpio", 1.0, (nota, largo)))
                elif "grito_filtrado" in capas:
                    lista.append((t, "grito_filtrado", (t - B0) / (B1 - B0), (nota, largo)))
    lista.append((T_DROP, "impacto", 1.0, None))
    lista.append((CIERRE, "final", 1.0, None))
    return sorted(lista, key=lambda g: g[0])


# ------------------------------------------------------------------ sonidos
def kick_duro(saturado=True):
    """Bombo: seno que cae de 240 a 50 Hz. Saturado queda casi cuadrado (el sonido del hard techno)."""
    t = np.arange(int(0.38 * SR)) / SR
    f = 50 + 190 * np.exp(-t * 30)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5)
    s = (np.tanh(5 * s) if saturado else np.tanh(1.2 * s) * 0.95) * np.minimum(1, (0.38 - t) / 0.03)
    s += filtro(rng.normal(0, 1, len(t)), 2000, 10000) * np.exp(-t * 300) * (0.5 if saturado else 0.25)
    return s * 0.9


def rumble_compas(sidechain, limpio=False):
    """Un compás de rumble continuo en Fa 1: seno + sierras, saturado, con acento en cada semicorchea.
    Limpio = solo el seno (casi no se oye en un celular). Con sidechain se hunde en cada kick: el bombeo."""
    t = np.arange(int(BAR * SR)) / SR
    f = hz(29)
    if limpio:
        s = np.sin(2 * np.pi * f * t) * 0.8
    else:
        s = np.sin(2 * np.pi * f * t) + 0.6 * (2 * ((f * t) % 1) - 1) + 0.25 * (2 * ((hz(41) * t) % 1) - 1)
        s = filtro(np.tanh(3 * s), 30, 1200)
    s *= 0.7 + 0.3 * np.exp(-(t % S16) * 25)
    if sidechain:
        s *= 0.06 + 0.94 * np.clip(((t % BEAT) - 0.015) / 0.17, 0, 1) ** 1.3
    borde = int(0.004 * SR)
    s[:borde] *= np.linspace(0, 1, borde)
    s[-borde:] *= np.linspace(1, 0, borde)
    return s


def stab_metal():
    """Acorde de Fa menor (Fa, La bemol, Do) con FM: suena a metal golpeado."""
    t = np.arange(int(0.26 * SR)) / SR
    indice = 0.5 + 3.5 * np.exp(-t * 18)
    s = sum(np.sin(2 * np.pi * hz(m) * t + indice * np.sin(2 * np.pi * hz(m) * 1.41 * t)) for m in (41, 44, 48, 53))
    return np.tanh(1.5 * s / 4) * np.minimum(1, t / 0.002) * np.exp(-t * 14)


def stab_limpio():
    """El mismo acorde de Fa menor con senos simples, sin FM."""
    t = np.arange(int(0.26 * SR)) / SR
    s = sum(np.sin(2 * np.pi * hz(m) * t) for m in (41, 44, 48, 53)) / 4
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 14) * 1.2


def grito_limpio(nota, largo):
    """El sinte antes de procesarlo: una sola sierra, sin saturar, un poco filtrada."""
    dur = largo * S16
    t = np.arange(int((dur + 0.05) * SR)) / SR
    s = filtro(2 * ((hz(nota) * t) % 1) - 1, 60, 2500)
    return s * np.minimum(1, t / 0.004) * np.clip((dur + 0.05 - t) / 0.05, 0, 1) * 0.7


def grito(nota, largo, crush=False, corte=None):
    """Sinte electro que grita: dos sierras desafinadas + cuadrada una octava abajo, muy saturadas.
    crush = bitcrush y filtro que abre y cierra; corte = filtro paso bajo (el break)."""
    dur = largo * S16
    t = np.arange(int((dur + 0.05) * SR)) / SR
    f = hz(nota)
    s = sum(2 * ((f * d * t) % 1) - 1 for d in (0.993, 1.007)) / 2 + 0.5 * np.sign(np.sin(np.pi * f * t))
    s = np.tanh(4 * s)
    if crush:
        paso = 6
        sec = np.repeat(s[::paso], paso)[:len(s)]
        sec = np.round(sec * 12) / 12
        abre = 0.5 + 0.5 * np.sin(2 * np.pi * t / (BEAT / 2))
        s = filtro(s, 80, 900) * (1 - abre) + (s * 0.4 + sec * 0.6) * abre
    if corte is not None:
        s = filtro(s, 60, 300 + 3500 * corte ** 2)
    env = np.minimum(1, t / 0.004) * np.clip((dur + 0.05 - t) / 0.05, 0, 1)
    return s * env * 0.8


def riser():
    """Ruido que abre el filtro + sirena que sube durante el break."""
    n = int((B1 - B0 - 2 * S16) * SR)
    trozos = []
    for k in range(32):
        r = rng.normal(0, 1, n // 32)
        trozos.append(filtro(r, 300 + 260 * k, 1500 + 450 * k) * (0.1 + 0.9 * (k / 32) ** 2))
    s = np.concatenate(trozos)
    t = np.arange(len(s)) / SR
    f = 200 * 10 ** (t / t[-1])
    s += np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.25 * (t / t[-1]) ** 2
    return s


def platillo():
    t = np.arange(int(1.6 * SR)) / SR
    return filtro(rng.normal(0, 1, len(t)), 4000, 15000) * np.exp(-t * 3) * 0.6


def boom():
    t = np.arange(int(1.4 * SR)) / SR
    f = 30 + 25 * np.exp(-t * 4)
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 2.5)


def poner(destino, s, t, gan=1.0):
    a = int(t * SR)
    if 0 <= a < len(destino):
        n = min(len(s), len(destino) - a)
        destino[a:a + n] += s[:n] * gan


def tartamudeo(x):
    """Glitch final: repite trozos de 1/16 y luego de 1/32, cada vez más triturados (bitcrush)."""
    a = int(GLITCH[0] * SR)
    for largo, veces, bits in ((S16, 4, 6), (S16 / 2, 8, 4)):
        n = int(largo * SR)
        trozo = np.round(x[a:a + n] * 2 ** bits) / 2 ** bits
        trozo = np.repeat(trozo[::4], 4)[:n]
        for v in range(veces):
            x[a + v * n:a + (v + 1) * n] = trozo
        a += veces * n


PISTAS = ["kick", "rumble", "hats", "clap", "stab", "stab_seco", "grito", "fx"]   # stab_seco: sin delay


def sonido(lista):
    """Devuelve (mezcla estéreo, pistas mono). Las pistas mono son las que dibuja el osciloscopio."""
    p = {k: np.zeros(N) for k in PISTAS}
    largo = np.zeros(N)                    # stabs del break, a una reverb enorme
    seco = np.zeros(N)                     # clap sin reverb
    k_sat, k_limpio, st, st_limpio = kick_duro(True), kick_duro(False), stab_metal(), stab_limpio()
    for t, capa, fuerza, extra in lista:
        if capa == "kick":
            poner(p["kick"], k_sat, t)
        elif capa == "kick_limpio":
            poner(p["kick"], k_limpio, t)
        elif capa == "rumble":
            poner(p["rumble"], rumble_compas(*extra), t)
        elif capa == "hats_limpio":
            poner(p["hats"], hat(1.0, abierto=extra), t, fuerza * 0.9)
        elif capa == "hats":
            # saturados: más cuerpo y más sucios
            poner(p["hats"], np.tanh(4 * hat(1.0, abierto=extra)) * 0.45, t, fuerza)
        elif capa in ("clap", "roll"):
            poner(p["clap"], clap(), t, fuerza)
        elif capa == "clap_seco":
            poner(seco, clap(), t, fuerza)
        elif capa == "stab_limpio":
            poner(p["stab_seco"], st_limpio, t)
        elif capa == "stab":
            poner(p["stab"], st, t)
        elif capa == "stab_largo":
            poner(largo, st, t, fuerza)
        elif capa == "grito":
            poner(p["grito"], grito(*extra), t)
        elif capa == "grito_limpio":
            poner(p["grito"], grito_limpio(*extra), t)
        elif capa == "grito2":
            poner(p["grito"], grito(*extra, crush=True), t)
        elif capa == "grito_filtrado":
            poner(p["grito"], grito(*extra, corte=fuerza), t, 0.5 + 0.5 * fuerza)
        elif capa == "riser":
            poner(p["fx"], riser(), t, 1.8)
        elif capa == "impacto":
            poner(p["fx"], platillo(), t)
            poner(p["kick"], boom(), t, 0.7)
    p["clap"] = eco(p["clap"], 1.6, 0.35, 3.0, semilla=3) + seco
    p["stab"] += eco(largo, 3.0, 0.7, 1.4, semilla=4)

    for x in p.values():
        x[int((B1 - 2 * S16) * SR):int(B1 * SR)] *= 0.0       # silencio antes del drop
        tartamudeo(x)
        x[int(CIERRE * SR):] = 0
    # Cierre: un último golpe que se queda sonando
    final = np.zeros(N)
    poner(final, kick_duro(True), CIERRE)
    poner(final, boom(), CIERRE, 0.8)
    p["kick"] += final + eco(final, 2.0, 0.5, 2.0, semilla=5) * 0.5

    gan = {"kick": 1.0, "rumble": 0.55, "hats": 0.3, "clap": 0.45, "stab": 0.38, "stab_seco": 0.38, "grito": 0.3,
           "fx": 0.4}
    mezcla = np.zeros((N, 2))
    for k, x in p.items():
        if k != "stab":
            mezcla += (x * gan[k])[:, None]
    # El stab rebota izquierda ↔ derecha cada 3/16
    mezcla += ping_pong(np.repeat((p["stab"] * gan["stab"])[:, None], 2, axis=1), BEAT * 0.75, 0.45, 5)
    mezcla /= np.max(np.abs(mezcla))
    mezcla = np.tanh(1.8 * mezcla) / np.tanh(1.8)
    fade = int(0.5 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    sube = int(INTRO * SR)
    mezcla[:sube] *= np.linspace(0.2, 1, sube)[:, None] ** 1.5
    return mezcla / np.max(np.abs(mezcla)) * 0.93, p


# ------------------------------------------------------------------ señales del osciloscopio
DR = 600  # puntos por segundo en la pantalla


def envolvente(x):
    v = SR // DR
    m = len(x) // v
    e = np.sqrt(np.mean(x[:m * v].reshape(m, v) ** 2, axis=1))
    e = np.convolve(e, np.ones(4) / 4, mode="same")
    return e / max(e.max(), 1e-9)


def senales(p, lista):
    """Ondas que dibuja cada canal: la envolvente real de su pista por una portadora visible."""
    env = {k: envolvente(x) for k, x in p.items()}
    td = np.arange(len(env["kick"])) / DR
    golpes_k = np.arange(0, TOTAL, BEAT)
    previo = golpes_k[np.clip(np.searchsorted(golpes_k, td, side="right") - 1, 0, None)]
    tau = td - previo
    fase_k = 2 * np.pi * (8 * tau + 5 * (1 - np.exp(-12 * tau)))
    # El grito sube y baja con su nota
    nota = np.full(len(td), 65.0)
    for t, capa, _f, extra in lista:
        if capa.startswith("grito"):
            nota[int(t * DR):int((t + extra[1] * S16) * DR)] = extra[0]
    fase_g = 2 * np.pi * np.cumsum(14 * 2 ** ((nota - 65) / 12)) / DR
    # Qué tan procesado está cada canal en cada momento (0 = limpio, 1 = con su efecto): la onda cambia de forma
    sucio = {k: np.ones(len(td)) for k in ("kick", "rumble", "hats", "stab", "grito")}
    limpios = {"kick_limpio": ("kick", BEAT), "hats_limpio": ("hats", S16), "clap_seco": ("hats", BEAT),
               "stab_limpio": ("stab", 0.3), "grito_limpio": ("grito", None)}
    for t, capa, _f, extra in lista:
        if capa == "rumble" and extra[1]:
            sucio["rumble"][int(t * DR):int((t + BAR) * DR)] = 0
        elif capa in limpios:
            canal, dur = limpios[capa]
            dur = extra[1] * S16 + 0.05 if dur is None else dur
            sucio[canal][int(t * DR):int((t + dur) * DR)] = 0
    for k in sucio:
        sucio[k] = np.convolve(sucio[k], np.ones(6) / 6, mode="same")
    r = np.random.default_rng(9)
    ruido = r.normal(0, 0.7, len(td))
    sierra_g = 2 * ((fase_g / (2 * np.pi)) % 1) - 1
    mezclar = lambda k, limpio, procesado: limpio * (1 - sucio[k]) + procesado * sucio[k]
    ondas = {
        # limpio: seno que se apaga; saturado: casi cuadrado y recortado
        "kick": mezclar("kick", np.sin(fase_k) * env["kick"] * 0.8,
                        np.clip(np.tanh(3 * np.sin(fase_k)) * env["kick"] * 1.4, -1, 0.85)),
        # limpio: seno redondo; distorsionado: cuadrado con armónicos
        "rumble": mezclar("rumble", np.sin(2 * np.pi * 10 * td),
                          np.tanh(3.5 * (np.sin(2 * np.pi * 10 * td) + 0.35 * np.sin(2 * np.pi * 30 * td + 1))))
        * env["rumble"],
        "hats": mezclar("hats", ruido * 0.6, np.clip(ruido * 2.5, -1, 1))
        * np.maximum(env["hats"], env["clap"] * 1.3),
        # limpio: un seno; con FM: tres ondas que chocan
        "stab": mezclar("stab", np.sin(2 * np.pi * 23 * td) * 0.9,
                        (np.sin(2 * np.pi * 23 * td) + np.sin(2 * np.pi * 27.4 * td) + np.sin(2 * np.pi * 34.5 * td)) / 3
                        * 1.3) * np.maximum(env["stab"], env["stab_seco"]) * 1.4,
        # limpio: sierra; procesado: saturado y en escalones (bitcrush)
        "grito": mezclar("grito", sierra_g * 0.8, np.round(np.tanh(3 * np.sin(fase_g)) * 4) / 4) * env["grito"]
        + ruido * 0.7 * env["fx"],
    }
    return ondas, env


# ------------------------------------------------------------------ textos (también guion de la voz)
def textos():
    salida = []
    for c0, (nc, texto, _capas, toma, _foco) in zip(INICIOS, SECCIONES):
        t0, t1 = c0 * BAR, (c0 + nc) * BAR
        palabras = [{"txt": p.replace("*", ""), "clave": p.startswith("*") or p.endswith("*")} for p in texto.split()]
        # las claves de varias palabras (*145 y 160 BPM:*) se marcan completas
        dentro = False
        for p, crudo in zip(palabras, texto.split()):
            if crudo.startswith("*"):
                dentro = True
            p["clave"] = dentro
            if crudo.rstrip(".,:!?…").endswith("*") or crudo.endswith("*"):
                dentro = False
        cada = min(0.33, (t1 - t0 - 0.5) / max(1, len(palabras)))
        for i, p in enumerate(palabras):
            p["t"] = round(t0 + 0.08 + i * cada, 3)
        salida.append({"t0": float(t0), "t1": float(t1), "toma": toma, "palabras": palabras,
                       "texto": texto.replace("*", "")})
    return salida


# ------------------------------------------------------------------ capas fijas
def fondo_base():
    y = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([8, 4, 22]), np.array([26, 8, 44])
    return ((top + (bot - top) * y) * np.ones((1, W, 1)) * 0.7).astype(np.float32)


def reticula(fuerza):
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    c = tuple(int(v * fuerza) for v in (0, 55, 70))
    for i in range(11):
        x = X0 + (X1 - X0) * i / 10
        d.line([(x, Y0), (x, Y1)], fill=c, width=2 if i in (0, 5, 10) else 1)
    for j in range(13):
        y = Y0 + (Y1 - Y0) * j / 12
        d.line([(X0, y), (X1, y)], fill=c, width=2 if j in (0, 12) else 1)
    for i in range(51):
        x = X0 + (X1 - X0) * i / 50
        for j in (0, 6, 12):
            y = Y0 + (Y1 - Y0) * j / 12
            d.line([(x, y - 6), (x, y + 6)], fill=tuple(int(v * fuerza) for v in (0, 70, 90)), width=1)
    return np.asarray(im).astype(np.float32)


ARRIBA = (60, 330)   # franja de los textos (arriba, centrados en y≈230 como pide MOTION.md)


def capa_texto(palabras, grande, vistas=None):
    """Texto de la franja de arriba: color (premultiplicado) y sombra. Las claves van en rosa.
    Acomoda la frase completa y dibuja solo las primeras `vistas` palabras, para que no se muevan al entrar."""
    fuente = f_titulo if grande else f_sub
    alto_linea = 100 if grande else 76
    im = Image.new("RGB", (W, ARRIBA[1] - ARRIBA[0]))
    som = Image.new("L", im.size)
    halo = Image.new("RGB", im.size)
    d, ds, dh = ImageDraw.Draw(im), ImageDraw.Draw(som), ImageDraw.Draw(halo)
    txt = [(p["txt"].upper() if grande else p["txt"], p["clave"]) for p in palabras]
    esp = d.textlength(" ", font=fuente)
    lineas, actual, ancho = [], [], 0
    for s, clave in txt:
        w = d.textlength(s, font=fuente)
        if actual and ancho + esp + w > 940:
            lineas.append((actual, ancho))
            actual, ancho = [], 0
        ancho += (esp if actual else 0) + w
        actual.append((s, clave, w))
    if actual:
        lineas.append((actual, ancho))
    y = (ARRIBA[1] - ARRIBA[0]) / 2 - len(lineas) * alto_linea / 2
    quedan = len(txt) if vistas is None else vistas
    for linea, ancho in lineas:
        x = (W - ancho) / 2
        for s, clave, w in linea:
            quedan -= 1
            if quedan < 0:
                break
            color = RESALTE if clave else (255, 255, 255)
            d.text((x, y), s, font=fuente, fill=color)
            ds.text((x, y), s, font=fuente, fill=255)
            dh.text((x, y), s, font=fuente, fill=(255, 50, 210) if clave else (0, 220, 255))
            x += w + esp
        y += alto_linea
    halo = np.asarray(halo.filter(ImageFilter.GaussianBlur(14 if grande else 9))).astype(np.float32) * 0.8
    sombra = np.asarray(som.filter(ImageFilter.GaussianBlur(10))).astype(np.float32)[..., None] / 255
    return np.asarray(im).astype(np.float32) + halo, np.clip(sombra * 1.6, 0, 1)


def suave(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ canales
def cursor_de(t):
    """Compás y posición del barrido (0-1)."""
    c = int(t // BAR)
    return c, (t - c * BAR) / BAR


def canal_activo(nombre, capas):
    return bool(capas & next(c[5] for c in CANALES if c[0] == nombre))


def dibujar_canales(d, t, ondas, r):
    c, u = cursor_de(t)
    i, _ = seccion_en(t)
    foco = SECCIONES[i][4]
    capas = capas_en(t)
    capas_prev = capas_en((c - 1) * BAR + 0.001) if c > 0 else set()
    # el break sobrecarga la pantalla y el drop se queda así, con todo grande y saturado
    sube = 1.0 if t >= T_DROP else suave((t - B0) / (B1 - B0)) if B0 <= t < B1 else 0.0
    temblor = r.normal(0, 7 * sube, 2) if sube else np.zeros(2)
    n = 480
    j = np.arange(n) / (n - 1)
    xs = X0 + j * (X1 - X0) + temblor[0]
    for nombre, _, cy, amp, color, _ in CANALES:
        cy = cy + temblor[1]
        if not canal_activo(nombre, capas):
            for x in range(X0, X1, 24):
                d.line([(x, cy), (x + 12, cy)], fill=(120, 20, 95), width=3)
            continue
        luz = 1.0 if foco in (None, nombre) else 0.45
        sig = ondas[nombre]
        y_off = cy
        a = amp * (1 + 0.6 * sube)
        col = tuple(int(v * luz) for v in color)
        nucleo = tuple(int(min(255, v + 150) * luz) for v in color)
        idx = ((c * BAR + j * BAR) * DR).astype(int).clip(0, len(sig) - 1)
        hasta = j <= u
        if hasta.sum() > 1:
            pts = list(zip(xs[hasta], y_off - sig[idx[hasta]] * a))
            d.line(pts, fill=col, width=4, joint="curve")
            d.line(pts, fill=nucleo, width=2)
        # Lo que queda del compás anterior, ya apagándose (como un monitor de signos vitales)
        despues = j > u + 0.03
        if canal_activo(nombre, capas_prev) and despues.sum() > 1:
            idx2 = (((c - 1) * BAR + j * BAR) * DR).astype(int).clip(0, len(sig) - 1)
            pts = list(zip(xs[despues], y_off - sig[idx2[despues]] * a))
            d.line(pts, fill=tuple(int(v * 0.35 * luz) for v in color), width=3, joint="curve")
    xc = X0 + u * (X1 - X0) + temblor[0]
    d.line([(xc, Y0), (xc, Y1)], fill=(150, 255, 255), width=3)


def lecturas(t):
    """Texto chico del osciloscopio y las anotaciones de cada sección (sin halo)."""
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    c, _ = cursor_de(t)
    d.text((X0, Y0 - 44), "OVERLOAD" if t >= T_DROP else "5V/div", font=f_mono, fill=tuple(MAG))
    d.text((X0, Y1 + 14), "TIME 160ms/div", font=f_mono_s, fill=(0, 140, 160))
    capas = capas_en(t)
    i, k = seccion_en(t)
    for nombre, etiqueta, cy, amp, color, _ in CANALES:
        activo = canal_activo(nombre, capas)
        col = tuple(int(v) for v in color) if activo else (170, 40, 140)
        d.text((X0 + 10, cy - amp - 40), etiqueta + ("" if activo else " · espera"), font=f_mono_s, fill=col)
        for toma, compas, canal, texto in ETIQUETAS:
            if canal == nombre and TOMAS[i] == toma and compas in (None, k):
                w = d.textlength(texto, font=f_etiqueta)
                x, y = X1 - w - 30, cy - amp - 48
                d.rectangle([x - 12, y - 6, x + w + 12, y + 42], outline=tuple(int(v) for v in color), width=2)
                d.text((x, y), texto, font=f_etiqueta, fill=(255, 255, 255))
    d.text((X1 - 300, Y0 - 44), f"{BPM} BPM  ▶ TRIG", font=f_mono, fill=tuple(CIAN))
    d.text((X1 - 270, Y1 + 14), f"COMPÁS {min(c, INICIOS[-1] - 1) + 1:02d} / {INICIOS[-1]}", font=f_mono_s,
           fill=(0, 140, 160))
    return np.asarray(im).astype(np.float32)


# ------------------------------------------------------------------ cuadro completo
FONDO = fondo_base()
RET = reticula(1.0)
_yy, _xx = np.mgrid[0:H, 0:W]
VINETA = np.clip(1.15 - (((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.6)) ** 2) * 0.75,
                 0.25, 1)[..., None].astype(np.float32)
LINEAS = (0.78 + 0.22 * (np.arange(H) % 4 < 2)).astype(np.float32)[:, None, None]
GRANO = [np.random.default_rng(k).normal(0, 5, (H, W, 1)).astype(np.float32) for k in range(6)]
del _yy, _xx


def brillo(a):
    """Bloom: desenfoques a media resolución sumados."""
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W // 2, H // 2), Image.BILINEAR)
    g = np.zeros((H // 2, W // 2, 3), np.float32)
    for rad, peso in ((3, 0.9), (9, 0.7), (25, 0.5)):
        g += np.asarray(im.filter(ImageFilter.GaussianBlur(rad))).astype(np.float32) * peso
    return np.asarray(Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32)


def cantidad_glitch(t, tk):
    if t < B0:
        return 0.1 * math.exp(-tk * 12)
    if t < T_DROP:
        return 0.7 * ((t - B0) / (B1 - B0)) ** 2
    if t < T_DROP + 0.15:
        return 1.0
    if t < GLITCH[0]:
        return 0.15 + 0.5 * math.exp(-tk * 10)
    if t < CIERRE:
        return 0.9
    return 1.0 - 0.4 * suave((t - CIERRE) / (TOTAL - CIERRE))


def acabado(a, g, f):
    r = np.random.default_rng(1000 + f)
    for _ in range(int(g * 10)):
        y0, h, dx = int(r.uniform(340, 1550)), int(r.uniform(6, 40)), int(r.uniform(-80, 80) * g)
        a[y0:y0 + h] = np.roll(a[y0:y0 + h], dx, axis=1)
    sep = int(3 + 12 * g)
    a[..., 0] = np.roll(a[..., 0], sep, axis=1)
    a[..., 2] = np.roll(a[..., 2], -sep, axis=1)
    a *= LINEAS
    a *= VINETA
    a += GRANO[f % len(GRANO)]
    return np.clip(a, 0, 255).astype(np.uint8)


class Render:
    def __init__(self, ondas, env, secciones, cierre_t):
        self.ondas, self.env = ondas, env
        self.secciones = secciones
        self.cierre_t = cierre_t           # cuándo aparece "Sígueme para más" (con voz: cuando se dice)
        self.fosforo = np.zeros((H, W, 3), np.float32)
        self.congelado = None              # el último cuadro del drop, que el glitch final deshace
        self.cache = {}

    def texto(self, clave, palabras, grande, vistas=None):
        if clave not in self.cache:
            if len(self.cache) > 40:
                self.cache.clear()
            self.cache[clave] = capa_texto(palabras, grande, vistas)
        return self.cache[clave]

    def poner_texto(self, a, t):
        """Palabra por palabra: cada una entra en 0.18 s (MOTION.md)."""
        if t >= CIERRE:
            if t < self.cierre_t:
                return a
            pal = [{"txt": "Sígueme", "clave": False}, {"txt": "para", "clave": False}, {"txt": "más", "clave": True}]
            rgb, som = self.texto(("cierre",), pal, True)
            alfa = suave((t - self.cierre_t) / 0.18)
        else:
            k = next(n for n, s in enumerate(self.secciones) if s["t0"] <= t < s["t1"])
            s = self.secciones[k]
            ps = s["palabras"]
            vistas = sum(1 for p in ps if p["t"] <= t)
            if not vistas:
                return a
            grande = s["toma"] in GRANDES
            rgb, som = self.texto((k, vistas), ps, grande, vistas)
            alfa = 1.0
            nueva = suave((t - ps[vistas - 1]["t"]) / 0.18)
            if nueva < 1 and vistas > 1:
                rgb0, som0 = self.texto((k, vistas - 1), ps, grande, vistas - 1)
                rgb, som = rgb0 + (rgb - rgb0) * nueva, som0 + (som - som0) * nueva
            elif nueva < 1:
                alfa = nueva
            # el texto se apaga al final de su sección
            alfa *= 1 - suave((t - (s["t1"] - 0.15)) / 0.15)
        y0, y1 = ARRIBA
        zona = a[y0:y1]
        zona *= 1 - 0.75 * som * alfa
        zona[:] = 255 - (255 - np.clip(zona, 0, 255)) * (255 - np.clip(rgb * alfa, 0, 255)) / 255
        return a

    def glitch_final(self, t, f, r):
        """La imagen se congela en el último golpe y el glitch la rompe en bloques hasta apagarla."""
        if self.congelado is None:                  # vista previa que cae directo en el cierre
            self.cuadro(int(CIERRE * FPS) - 1)
        p = (t - CIERRE) / (TOTAL - CIERRE)
        a = self.congelado.copy()
        if t < CIERRE + 0.1:
            a += 120                                # destello del último golpe
        for _ in range(int(4 + 10 * p)):           # bloques que se corren de lado
            y0, h = int(r.uniform(Y0 - 60, Y1)), int(r.uniform(20, 160))
            a[y0:y0 + h] = np.roll(a[y0:y0 + h], int(r.uniform(-260, 260)), axis=1)
        if r.random() < 0.35:                       # la imagen brinca hacia arriba o abajo
            a = np.roll(a, int(r.uniform(-120, 120)), axis=0)
        if r.random() < 0.25:                       # canales de color cruzados
            a = a[..., [2, 0, 1]] if r.random() < 0.5 else a[..., [1, 2, 0]]
        negro = r.random() < 0.15 + 0.5 * p         # cada vez más cuadros en negro
        return a * (0.08 if negro else 1 - 0.85 * suave(p))

    def cuadro(self, f):
        t = f / FPS
        i = min(int(t * DR), len(self.env["kick"]) - 1)
        ek = float(self.env["kick"][i])
        tk = t - math.floor(t / BEAT) * BEAT
        r = np.random.default_rng(f)

        if t >= CIERRE:
            a = self.glitch_final(t, f, r)
        else:
            luz = Image.new("RGB", (W, H))
            dibujar_canales(ImageDraw.Draw(luz), t, self.ondas, r)
            self.fosforo = self.fosforo * 0.45 + np.asarray(luz).astype(np.float32)
            a = FONDO + RET
            if t >= T_DROP:
                a = a + 20 * ek
            if T_DROP <= t < T_DROP + 0.1:
                a = a + 120
            a = a + self.fosforo + brillo(self.fosforo)
            a = a + lecturas(t) * 0.9
            self.congelado = a.copy()
        a = self.poner_texto(a, t)
        return acabado(a, cantidad_glitch(t, tk), f)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Hard techno explicado en un osciloscopio CRT")
    ap.add_argument("--preview", type=float, nargs="+", help="segundos a guardar como PNG")
    ap.add_argument("--datos", help="JSON con los tiempos de las palabras (el -voz.json de techno_voz.py)")
    ap.add_argument("--audio", help="WAV a usar en vez del beat solo (el -voz.wav de techno_voz.py)")
    ap.add_argument("--salida", default=str(RAIZ / f"out/pruebas/beats/{NOMBRE}.mp4"))
    args = ap.parse_args()

    TMP.mkdir(parents=True, exist_ok=True)
    print("Sintetizando el audio…")
    lista = golpes()
    mezcla, pistas = sonido(lista)
    ondas, env = senales(pistas, lista)
    secciones = textos()
    cierre_t = CIERRE + 0.3
    if args.datos:
        datos = json.loads(Path(args.datos).read_text(encoding="utf-8"))
        secciones = datos["secciones"]
        cierre_t = max(cierre_t, datos.get("cierre_voz", cierre_t))
    else:
        # Lo que necesita techno_voz.py para pegar la voz (ADR-025)
        datos = {"total": TOTAL, "fps": FPS, "bpm": BPM, "beat": BEAT, "compas": BAR, "secciones": secciones,
                 "cierre": CIERRE, "cierreTexto": CIERRE_TEXTO, "glitch": list(GLITCH)}
        (TMP / f"{NOMBRE}.json").write_text(json.dumps(datos), encoding="utf-8")
        escribir_wav(TMP / f"{NOMBRE}.wav", mezcla)
        guion = ["Guion de voz — ¿Cómo se hace el hard techno? (osciloscopio)", "",
                 "Voz: ElevenLabs, todo en UN SOLO AUDIO, en este orden, con una pausa corta entre frase y frase.", ""]
        guion += [s["texto"] for s in secciones if s["texto"]] + [f"{CIERRE_TEXTO}."]
        (TMP / f"{NOMBRE}-guion.txt").write_text("\n".join(guion) + "\n", encoding="utf-8")
        print(f"{len(lista)} golpes, {TOTAL:.1f} s, drop en {T_DROP:.1f} s ({T_DROP / TOTAL:.0%})")
        for s in secciones:
            print(f"  {s['t0']:5.1f} s  {s['toma']:9s} {s['texto']}")

    render = Render(ondas, env, secciones, cierre_t)
    if args.preview:
        (RAIZ / "out/.preview").mkdir(exist_ok=True)
        for seg in args.preview:
            f_obj = int(seg * FPS)
            render.fosforo[:] = 0
            for f in range(max(0, f_obj - 8), f_obj):   # unos cuadros antes para el fósforo
                render.cuadro(f)
            ruta = RAIZ / f"out/.preview/hardtechno-{seg:.1f}.png"
            Image.fromarray(render.cuadro(f_obj)).save(ruta)
            print(ruta)
        return

    wav = Path(args.audio) if args.audio else TMP / f"{NOMBRE}.wav"
    mp4 = TMP / Path(args.salida).name
    total = int(TOTAL * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-b:a", "192k", "-shortest", str(mp4)], stdin=subprocess.PIPE)
    for f in range(total):
        ff.stdin.write(render.cuadro(f).tobytes())
        if f % 150 == 0:
            print(f"cuadro {f}/{total}", flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg falló")
    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(mp4), args.salida)
    print("Listo:", args.salida)


if __name__ == "__main__":
    main()
