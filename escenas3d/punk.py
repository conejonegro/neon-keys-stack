#!/usr/bin/env python3
"""Neon Keys · "¿Puedes seguir esta batería?": The Kids Aren't Alright (The Offspring) por niveles, con carriles que
caen al estilo Guitar Hero (ADR-024).

Igual que trap.py y reggaeton.py: una sola tabla (PATRONES + SECCIONES) manda en la imagen y en el sonido. Aquí cada
sección lleva su propio tempo (práctica lenta → sube → tempo real), así que los golpes se calculan compás por compás.
La batería, la guitarra distorsionada y el bajo salen del soundfont (FluidR3, kit de batería del banco 128); la
transcripción del ritmo y del riff es propia. Ojo: es un cover (la composición tiene dueño): sirve para crecer, no
para Creator Rewards.

Uso:
    .venv/bin/python escenas3d/punk.py [--kit standard|power|room]
        # → out/.tmp/beat-punk-kids.json y .wav
    cd escenas3d && node grabar.js escenas/punk.html out/pruebas/beats/beat-punk-kids.mp4 \\
        --datos out/.tmp/beat-punk-kids.json --audio out/.tmp/beat-punk-kids.wav
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tinysoundfont

KITS = {"standard": 0, "room": 8, "power": 16}
_args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
_args.add_argument("--kit", choices=list(KITS), default="standard")
KIT = _args.parse_args().kit
sys.argv = sys.argv[:1]                            # techno.py lee sus propias opciones al importarse
from techno import eco, escribir_wav, filtro  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SOUNDFONT = RAIZ / "soundfonts" / "FluidR3Mono_GM.sf3"
SR = 44100
FPS = 30
NOMBRE = "beat-punk-kids"

BPM_REAL = 198                    # se cuenta "a la punk": la tarola en 2 y 4 a casi 200
BPM_LENTO = 130

# Carriles de izquierda a derecha (como el pad de Rock Band); el BOMBO no es carril: es la barra que cruza todo
CARRILES = ["TAROLA", "HI-HAT", "TOM", "PISO", "PLATILLO"]
NOTA_GM = {"BOMBO": 36, "TAROLA": 38, "HI-HAT": 42, "TOM": 47, "PISO": 43, "PLATILLO": 49, "RIDE": 51,
           "CLICK": 37}

# Patrones de un compás (16 semicorcheas), escritos como en una tablatura: o = golpe, x = platillo/hi-hat
PATRONES = {
    # Inicio de toms (el gancho): piso en corcheas, bombo en negras y tarola en 2, 2-y y 4
    "toms": {"BOMBO": "o---o---o---o---", "PISO": "o-o-o-o-o-o-o-o-", "TAROLA": "----o-o-----o---"},
    # El ritmo de la canción: frase de dos compases (bombo sincopado, tarola en 2 y 4)
    "A1": {"BOMBO": "o-------o-o---o-", "TAROLA": "----o-------o---", "HI-HAT": "--x-x-x-x-x-x-x-"},
    "A2": {"BOMBO": "--o-----o-o-----", "TAROLA": "----o-------o---", "HI-HAT": "x-x-x-x-x-x-x-x-"},
    # Cierre de la vuelta: bombo en contratiempo y platillos en 2, 3 y 4
    "A2fin": {"BOMBO": "--o---o---o---o-", "TAROLA": "----o---o---o---", "PLATILLO": "----x---x---x---"},
    # El redoble: la tarola de la canción, repartida tarola → tom → piso
    "redoble": {"TAROLA": "o-ooo-----------", "TOM": "------o-o-o-----", "PISO": "-----------oo-o-"},
    "golpe": {"BOMBO": "o---------------", "PLATILLO": "x---------------"},
    "nada": {},
}

# Guitarra y bajo (tablatura en notas MIDI). Acordes de quinta en Si♭ menor: i – VI – III – VII
QUINTAS = {"Bb": (46, 53, 58), "Gb": (42, 49, 54), "Db": (49, 56, 61), "Ab": (44, 51, 56)}
BAJO = {"Bb": 34, "Gb": 30, "Db": 37, "Ab": 32}
# El riff del inicio: nota pedal en corcheas (cuerda Re) y la melodía arriba (cuerda Sol); (corchea, nota)
RIFF = [(2, 61), (4, 61), (7, 60), (9, 60), (11, 60), (12, 60), (13, 61), (14, 61)]           # dos compases
RIFF_VUELTA = [(2, 61), (4, 61), (7, 60), (9, 60), (10, 60), (11, 61), (12, 61), (13, 63), (14, 63), (15, 61)]
PEDAL = {"Bb": 58, "Gb": 54, "Ab": 56}

# Secciones del guion: (toma, compases, bpm, patrones (se repiten), capas que se ven y suenan, texto, banda)
#   banda: None | "riff" (riff del inicio, un acorde cada 2 compases) | "coro" (quintas en corcheas, un acorde
#   por compás) | "final"
TODAS = ["BOMBO", "TAROLA", "HI-HAT", "TOM", "PISO", "PLATILLO"]
SECCIONES = [
    ("reto", 5, BPM_REAL, ["toms", "toms", "toms", "redoble", "toms"], TODAS, "¿Puedes seguir esta batería? 🥁", "riff"),
    ("promesa", 2, BPM_LENTO, ["nada"], [], "Vamos por partes.", None),
    ("bombo-tarola", 4, BPM_LENTO, ["A1", "A2"], ["BOMBO", "TAROLA"], "1. Bombo y tarola.", None),
    ("hihat", 4, BPM_LENTO, ["A1", "A2"], ["BOMBO", "TAROLA", "HI-HAT"], "2. Suma el hi-hat: ya empieza a sonar.",
     None),
    ("redoble", 2, BPM_LENTO, ["redoble", "nada"], TODAS, "3. Ahora viene el redoble.", None),
    ("otra-vez", 3, BPM_LENTO, ["toms", "toms", "redoble"], TODAS, "Escúchalo otra vez.", None),
    ("rapido1", 2, 150, ["A1", "A2"], TODAS, "Ahora, más rápido…", None),
    ("rapido2", 2, 172, ["A1", "A2fin"], TODAS, "", None),
    ("banda", 8, BPM_REAL, ["toms", "toms", "toms", "redoble"], TODAS, "Ahora con toda la banda 🔥", "riff"),
    ("coro", 12, BPM_REAL, ["A1", "A2", "A1", "A2fin"], TODAS, "", "coro"),
    ("cierre", 4, BPM_REAL, ["toms", "toms", "toms", "golpe"], TODAS, "¿Qué canción sigue?", "final"),
]
CIERRE_TEXTO = "Sígueme para el siguiente nivel."
CANCION = ["The Kids Aren't Alright", "The Offspring"]
COLA = 2.6                                          # segundos que suena el último golpe

# Tiempo de inicio y duración de cada compás (el tempo cambia por sección)
COMPASES = []                                       # (t0, duración, bpm, sección, compás dentro de la sección)
_t = 0.0
for _i, (_toma, _nc, _bpm, *_resto) in enumerate(SECCIONES):
    for _k in range(_nc):
        COMPASES.append((_t, 240 / _bpm, _bpm, _i, _k))
        _t += 240 / _bpm
FIN = _t                                            # el golpe final cae en el último compás
TOTAL = COMPASES[-1][0] + COLA
N = int(TOTAL * SR)
rng = np.random.default_rng(198)


def inicio(toma):
    return next(t0 for t0, _d, _b, i, k in COMPASES if SECCIONES[i][0] == toma and k == 0)


# ------------------------------------------------------------------ golpes (los mismos para imagen y sonido)
def golpes():
    """Lista de golpes [t, carril, paso, fuerza, capa]; carril −1 = bombo (la barra)."""
    lista = []
    for t0, dur, _bpm, i, k in COMPASES:
        _toma, _nc, _b, patrones, capas, _texto, _banda = SECCIONES[i]
        patron = PATRONES[patrones[k % len(patrones)]]
        paso_s = dur / 16
        for capa, linea in patron.items():
            if capa not in capas:
                continue
            for paso, c in enumerate(linea):
                if c == "-":
                    continue
                fuerza = 1.0 if paso % 4 == 0 else 0.85 if paso % 2 == 0 else 0.72
                if capa == "HI-HAT":
                    fuerza = 0.8 if paso % 4 == 0 else 0.6
                carril = -1 if capa == "BOMBO" else CARRILES.index(capa)
                lista.append([round(t0 + paso * paso_s, 5), carril, paso, fuerza, capa])
        # Platillo al empezar cada frase de la canción (y en el primer cuadro del video)
        if "PLATILLO" in capas and k % 4 == 0 and patrones != ["nada"] and _toma not in ("otra-vez", "redoble"):
            if not any(g[0] == round(t0, 5) and g[4] == "PLATILLO" for g in lista):
                lista.append([round(t0, 5), CARRILES.index("PLATILLO"), 0, 1.0, "PLATILLO"])
    lista.sort(key=lambda g: (g[0], g[1]))
    return lista


def notas_banda():
    """Notas de guitarra y bajo: (t, canal, nota, velocidad, duración). Canal 0 = guitarra, 1 = bajo."""
    notas = []
    acordes_riff = ["Bb", "Gb", "Ab", "Ab"]
    acordes_coro = ["Bb", "Gb", "Db", "Ab"]
    for t0, dur, _bpm, i, k in COMPASES:
        banda = SECCIONES[i][6]
        corchea = dur / 8
        if banda == "riff":
            par = k // 2 % 4                         # un acorde cada dos compases
            acorde = acordes_riff[par]
            for c in range(8):                       # pedal en corcheas, apagada con la palma
                notas.append((t0 + c * corchea, 0, PEDAL[acorde], 92, corchea * 0.7))
            riff = RIFF_VUELTA if par == 3 else RIFF
            for e, nota in riff:
                if e // 8 == k % 2:
                    notas.append((t0 + (e % 8) * corchea, 0, nota, 110, corchea * 1.6))
            if k % 2 == 0:
                notas.append((t0, 1, BAJO[acorde], 105, dur * 2 * 0.95))   # el bajo deja sonar cada nota
        elif banda == "coro":
            acorde = acordes_coro[k % 4]
            for c in range(8):
                fuerte = c in (0, 3, 6)
                for nota in QUINTAS[acorde]:
                    notas.append((t0 + c * corchea, 0, nota, 118 if fuerte else 100, corchea * 0.9))
                notas.append((t0 + c * corchea, 1, BAJO[acorde], 112 if fuerte else 98, corchea * 0.9))
        elif banda == "final":
            if k < 3:
                for c in range(8):
                    notas.append((t0 + c * corchea, 0, PEDAL["Bb"], 92, corchea * 0.7))
                for e, nota in RIFF:
                    if e // 8 == k % 2:
                        notas.append((t0 + (e % 8) * corchea, 0, nota, 110, corchea * 1.6))
                if k == 0:
                    notas.append((t0, 1, BAJO["Bb"], 105, dur * 3 * 0.95))
            else:                                    # el último golpe: acorde abierto que se queda sonando
                for nota in QUINTAS["Bb"]:
                    notas.append((t0, 0, nota, 124, COLA - 0.2))
                notas.append((t0, 1, BAJO["Bb"], 120, COLA - 0.2))
    return notas


# ------------------------------------------------------------------ síntesis (soundfont)
def sintetizar(eventos, programas):
    """eventos: (t, canal, nota, velocidad, duración). programas: {canal: (banco, preset, es_bateria)}."""
    synth = tinysoundfont.Synth(samplerate=SR)
    sfid = synth.sfload(str(SOUNDFONT))
    for canal, (banco, preset, bateria) in programas.items():
        synth.program_select(canal, sfid, banco, preset, bateria)
    cola = [(t, 1, c, n, v) for t, c, n, v, _d in eventos] + [(t + d, 0, c, n, 0) for t, c, n, _v, d in eventos]
    cola.sort(key=lambda e: (e[0], e[1]))           # a tiempos iguales, primero se suelta y luego se toca
    partes, cursor = [], 0.0
    for t, prende, canal, nota, vel in cola:
        n = int(round(t * SR)) - int(round(cursor * SR))
        if n > 0:
            partes.append(np.frombuffer(synth.generate(n), dtype=np.float32).copy())
            cursor = t
        if prende:
            synth.noteon(canal, nota, vel)
        else:
            synth.noteoff(canal, nota)
    resto = N - int(round(cursor * SR))
    if resto > 0:
        partes.append(np.frombuffer(synth.generate(resto), dtype=np.float32).copy())
    x = np.concatenate(partes).reshape(-1, 2).astype(np.float64)
    return x[:N] if len(x) >= N else np.pad(x, ((0, N - len(x)), (0, 0)))


_CUERDAS = {}


def cuerda(nota, dur, apagada, semilla):
    """Cuerda pulsada (Karplus-Strong): un ruido corto que da vueltas por un retardo del largo de la cuerda y se
    va suavizando. Apagada con la palma = se apaga más rápido y más opaca. Se calcula por bloques de un periodo."""
    clave = (nota, round(dur, 3), apagada, semilla)
    if clave in _CUERDAS:
        return _CUERDAS[clave]
    P = int(round(SR / (440 * 2 ** ((nota - 69) / 12))))
    n = int((dur + 0.03) * SR)
    bloques = n // P + 2
    y = np.zeros(bloques * P)
    r = np.random.default_rng(semilla)
    pua = r.uniform(-1, 1, P)
    pua = np.convolve(pua, np.ones(3) / 3, mode="same")         # púa no tan brillante
    y[:P] = pua - pua.mean()
    a = 0.25 if apagada else 0.5                                 # más peso al anterior = más opaco
    caida = 0.985 if apagada else 0.9985
    for k in range(1, bloques):
        previo = y[(k - 1) * P:k * P]
        antes = np.concatenate([[y[k * P - P - 1] if k > 1 else 0.0], previo[:-1]])
        y[k * P:(k + 1) * P] = caida * ((1 - a) * previo + a * antes)
    y = y[:n]
    suelta = int(0.02 * SR)
    y[-suelta:] *= np.linspace(1, 0, suelta)
    _CUERDAS[clave] = y
    return y


def guitarra(notas, toma):
    """Suma las cuerdas de una toma (cada nota del acorde es una cuerda un poquito desafinada y desfasada)."""
    x = np.zeros(N)
    for t, nota, vel, dur in notas:
        apagada = vel < 100
        s = cuerda(nota, dur, apagada, (nota * 7 + toma) % 23) * (vel / 127)
        a = int((t + 0.0015 * (nota % 3)) * SR)               # rasgueo: cuerdas graves primero
        if 0 <= a < N:
            m = min(len(s), N - a)
            x[a:a + m] += s[:m]
    return x


def amplificador(x, toma=0):
    """Ampli de punk hecho con código: dos etapas de distorsión (la primera asimétrica, como un bulbo), tono
    entre etapas y la caja de 4×12 (cae fuerte arriba de ~4 kHz, cuerpo en 120–300 Hz, sin el chirrido de
    2.5–6 kHz que suena a MIDI)."""
    x = filtro(x, 100, 6000)
    x = np.tanh(x * 12 + 0.2) - np.tanh(0.2)
    x = filtro(x, 80, 3800)
    x = np.tanh(x * 3)
    caja = filtro(filtro(x, 75, 4200), 60, 5000)                 # dos veces: la caja corta muy en seco
    caja += filtro(caja, 120, 320) * 0.5                         # cuerpo
    caja -= filtro(caja, 2600, 6000) * (0.45 if toma else 0.55)  # sin chirrido
    return caja


def sonido(lista):
    # Batería: cada golpe es una nota del kit; el piso y la tarola suenan más fuerte en el gancho
    bat = []
    for t, _carril, _paso, fuerza, capa in lista:
        bat.append((t, 9, NOTA_GM[capa], int(min(127, 40 + 87 * fuerza)), 0.4))
    # Click de práctica en negras (bajito) mientras se explica a velocidad lenta
    for t0, dur, bpm, i, _k in COMPASES:
        if bpm == BPM_LENTO:
            for b in range(4):
                bat.append((t0 + b * dur / 4, 9, NOTA_GM["CLICK"], 70 if b == 0 else 48, 0.1))
    kit = {9: (128, KITS[KIT], True)}
    bateria = sintetizar([e for e in bat if e[2] != NOTA_GM["PISO"]], kit)
    piso = sintetizar([e for e in bat if e[2] == NOTA_GM["PISO"]], kit)

    banda_notas = notas_banda()
    bajo = sintetizar([n for n in banda_notas if n[1] == 1], {1: (0, 33, False)})
    a, b = int(inicio("banda") * SR), int(inicio("cierre") * SR)
    nivel = lambda x, db: x * 10 ** (db / 20) / np.sqrt(np.mean(x[a:b] ** 2))   # RMS medido con toda la banda

    # Guitarra doblada: dos tomas de la guitarra limpia, cada una con su pequeño desfase y fuerza (como un
    # guitarrista que graba dos veces), cada una por el amplificador y a un lado. Las corcheas apagadas con la
    # palma usan la guitarra "palm muted" del soundfont
    tomas = []
    for toma in (0, 1):
        r = np.random.default_rng(30 + toma)
        notas = [(t + r.normal(0, 0.005) + 0.004 * toma, n, int(np.clip(v + r.integers(-6, 7), 60, 127)), d)
                 for t, c, n, v, d in banda_notas if c == 0]
        # Abiertas (melodía y acordes) = cuerdas sintetizadas; apagadas con la palma = la del soundfont
        abiertas = guitarra([nt for nt in notas if nt[2] >= 100], toma)
        palma = sintetizar([(t, 2, n, v, d) for t, n, v, d in notas if v < 100], {2: (0, 28, False)}).mean(1)
        tomas.append(amplificador(nivel(abiertas, -20) + nivel(palma, -23), toma))
    guitarras = np.stack([tomas[0] + tomas[1] * 0.12, tomas[1] + tomas[0] * 0.12], 1)

    bat_mono = bateria.mean(1)
    golpe = filtro(bat_mono, 30, 160)                # más cuerpo en el bombo
    bateria = bateria * 1.15 + golpe[:, None] * 0.6 + piso * 0.75   # el piso ya es grave: sin refuerzo
    bateria = np.stack([eco(bateria[:, c], 0.9, 0.18, 6.0, 3 + c) for c in (0, 1)], 1)

    # Con toda la banda la guitarra va al frente, el bajo justo debajo y la batería un poco atrás
    # Sin banda (el tutorial) la batería sube 5 dB para no quedar chiquita junto a las partes con banda
    sube = np.zeros(N)
    for s in textos():
        if s["banda"] is None:
            sube[int(s["t0"] * SR):int(s["t1"] * SR)] = 1
    rampa = int(0.08 * SR)
    sube = np.convolve(sube, np.ones(rampa) / rampa, mode="same")
    bateria = nivel(bateria, -14) * (10 ** (5 * sube / 20))[:, None]
    mezcla = bateria + nivel(guitarras, -13) + nivel(bajo.mean(1), -16)[:, None]

    # Del reto al modo lento: la batería se frena como cinta (tape stop) en el último tiempo
    t_lento = inicio("promesa")
    n = int(0.45 * SR)
    a = int(t_lento * SR) - n
    velocidad = np.linspace(1, 0, n) ** 0.7
    lee = np.clip(a + np.cumsum(velocidad).astype(int), 0, N - 1)
    mezcla[a:a + n] = mezcla[lee] * np.linspace(1, 0.2, n)[:, None]

    mezcla = np.tanh(mezcla * 1.3)
    mezcla[:int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))[:, None]
    fade = int(0.8 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return mezcla / np.max(np.abs(mezcla)) * 0.89  # pico a −1 dB: no lleva voz


# ------------------------------------------------------------------ textos
def textos():
    salida = []
    for i, (toma, _nc, bpm, _p, capas, texto, banda) in enumerate(SECCIONES):
        compases = [c for c in COMPASES if c[3] == i]
        salida.append({"t0": compases[0][0], "t1": compases[-1][0] + compases[-1][1], "toma": toma,
                       "texto": texto, "bpm": bpm, "capas": capas, "banda": banda})
    return salida


def main():
    lista = golpes()
    datos = {
        "total": TOTAL, "fps": FPS, "carriles": CARRILES, "kit": KIT,
        "golpes": lista,
        "compases": [[round(t0, 5), round(d, 5), bpm] for t0, d, bpm, _i, _k in COMPASES],
        "secciones": textos(),
        "cancion": CANCION, "cierre": inicio("cierre"), "fin": COMPASES[-1][0], "cierreTexto": CIERRE_TEXTO,
        "lento": inicio("promesa"), "banda": inicio("banda"),
    }
    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / f"{NOMBRE}.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    escribir_wav(tmp / f"{NOMBRE}.wav", sonido(lista))
    print(f"{len(lista)} golpes, {TOTAL:.1f} s, kit {KIT}")
    for s in datos["secciones"]:
        print(f"  {s['t0']:5.1f}–{s['t1']:5.1f} s  {s['toma']:9s} {s['bpm']} BPM  {s['texto']}")
    for ext in (".json", ".wav"):
        print(tmp / f"{NOMBRE}{ext}")


if __name__ == "__main__":
    main()
