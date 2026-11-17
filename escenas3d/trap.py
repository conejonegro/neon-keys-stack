#!/usr/bin/env python3
"""Neon Keys · "¿Por qué tu trap suena vacío?": el secuenciador 3D del techno (ADR-022), ahora con trap.

Igual que techno.py: una sola tabla (PATRONES + SECCIONES) manda en la imagen y en el sonido. Aquí se calculan
los golpes, se sintetiza el beat a 140 BPM (808 afinado, saturado y con glide; kick corto; clap en el 3;
hi-hats con redobles y cambios de tono; campanas en Do menor) y se escribe el JSON que lee escenas/trap.html.
Abre con un beat de trap mal hecho (808 desafinado y limpio, kick en cada tiempo, hats de metrónomo) que se
frena como cinta; luego se arma el bueno capa por capa. Cada truco (saturación, glide, redobles, tono) entra justo
cuando la voz lo explica, y en "antes" vuelve a sonar el beat malo.

Uso:
    .venv/bin/python escenas3d/trap.py      # → out/.tmp/beat-trap-vacio.json, .wav y -guion.txt
    cd escenas3d && node grabar.js escenas/trap.html out/pruebas/beats/beat-trap-vacio.mp4 \\
        --datos out/.tmp/beat-trap-vacio.json --audio out/.tmp/beat-trap-vacio.wav
"""

import json
import wave
from pathlib import Path

import numpy as np

from techno import eco, escribir_wav, filtro, ping_pong

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
FPS = 30
NOMBRE = "beat-trap-vacio"

BPM = 140
BEAT = 60 / BPM
COMPAS = 4 * BEAT
PASO = BEAT / 4                  # semicorchea

# Carriles de adelante (cerca de la cámara) hacia atrás
CARRILES = ["808", "KICK", "CLAP", "MELODÍA", "OPEN HAT", "HATS"]
# 808 y melodía: paso → (nota MIDI A, nota MIDI B). Los compases pares usan A y los nones B.
BAJO = {0: (36, 32), 6: (36, 32), 10: (39, 31), 14: (48, 43)}      # Do · Mib · Do arriba / Lab · Sol · Sol arriba
MELODIA = {0: (72, 68), 3: (75, 72), 6: (79, 75), 8: (77, 74), 11: (75, 72), 14: (74, 71)}
PATRONES = {
    "808": {p: 0.5 + (a - 36) / 24 for p, (a, _b) in BAJO.items()},     # la altura del bloque = la nota
    "KICK": {0: 1, 10: 0.85},
    "CLAP": {8: 1},
    "MELODÍA": {p: 0.45 + (a - 72) / 14 for p, (a, _b) in MELODIA.items()},
    "OPEN HAT": {4: 0.7, 12: 0.7},
    "HATS": {i: (0.8 if i % 4 == 0 else 0.6) for i in range(0, 16, 2)},  # corcheas parejas
    "ROLL": {},                                  # redoble de clap en la subida (lo arma golpes())
    # El trap mal hecho del inicio: kick en cada tiempo, clap en 2 y 4, hats parejos y 808 desafinado
    "KICK MAL": {0: 1, 4: 1, 8: 1, 12: 1},
    "CLAP MAL": {4: 1, 12: 1},
    "HATS MAL": {i: 0.6 for i in range(16)},
}
BAJO_MAL = {0: 37.45, 3: 34.6, 8: 39.3, 11: 31.8}                  # notas fuera de tono (cuartos de tono)
PATRONES["808 MAL"] = {p: 0.5 + (n - 36) / 24 for p, n in BAJO_MAL.items()}
# Redobles de hats: (paso donde empieza, cuántos golpes, en cuántos pasos). 4 en 2 pasos = fusas,
# 3 en 2 pasos = tresillos, 2 en 1 paso = semicorcheas dobles.
REDOBLES = ({6: (4, 2), 12: (3, 2), 14: (3, 2)},                    # compás A
            {3: (2, 1), 10: (2, 1), 14: (6, 2)})                    # compás B
TODAS = ["808", "KICK", "CLAP", "HATS", "MELODÍA", "OPEN HAT"]
MALO = ["808 MAL", "KICK MAL", "CLAP MAL", "HATS MAL"]
BASICO = ["808", "KICK", "CLAP", "HATS"]

# Secciones: (compases, texto con *palabra clave*, capas que suenan, toma de cámara). Una idea por sección; el
# texto es también el guion de la voz (~0.33 s por palabra; a 140 BPM, 2 compases = 3.4 s).
SECCIONES = [
    (2, "Si tu *trap* suena así…", MALO, "malo"),
    (1, "…lo estás haciendo *mal.*", MALO, "mal"),         # el beat se frena como cinta (tape stop)
    (3, "Mira: la *808* fue un fracaso. La dejaron de hacer en 1983.", ["808"], "fracaso"),
    (2, "Hoy su bombo largo es el *bajo* de casi todo el trap.", ["808"], "bajo"),
    (2, "Para que pegue, *afínalo* al tono de tu canción.", ["808"], "afina"),
    (2, "*Satúralo:* así se oye hasta en la bocina del celular.", ["808"], "satura"),
    (3, "Encima, un *kick* cortito: el golpe arriba, el 808 abajo.", ["808", "KICK"], "kick"),
    (2, "Y desliza entre notas… ese *uuuh* es el glide.", ["808", "KICK"], "glide"),
    (2, "*Clap* solo en el tres: a 140 se siente a la mitad.", ["808", "KICK", "CLAP"], "clap"),
    (2, "Ahora los *hi-hats:* la mitad del flow está aquí.", BASICO, "hihats"),
    (2, "Parejos suenan a *metrónomo.* Mete redobles.", BASICO, "parejos"),
    (3, "*Semicorcheas,* fusas y tresillos… rápido, pero con medida.", BASICO, "rolls"),
    (2, "Súbeles el *tono* en el redoble: así hablan.", BASICO, "tono"),
    (2, "Un *open hat* a contratiempo: deja respirar el beat.", BASICO + ["OPEN HAT"], "openhat"),
    (2, "Y al final, la *melodía:* campanas oscuras en menor.", TODAS, "melodia"),
    (2, "*Seis* *capas.* Cada una en su lugar.", TODAS, "recap"),
    (2, "¿Te acuerdas cómo sonaba *antes?*", MALO, "antes"),
    (2, "…y así suena *ahora.*", TODAS, "ahora"),
    (2, "Y cuando cae el *808…*", ["CLAP", "HATS", "MELODÍA", "ROLL"], "subida"),
    (3, "¡Ahora *sí* pega!", TODAS, "drop"),
    (3, "*Guárdalo* para tu próxima sesión.", TODAS, "drop2"),
]
COMPASES_CIERRE = 2
CIERRE_TEXTO = "Sígueme para más"

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
# Cada truco suena desde que se explica (y se apaga en "antes")
TRUCOS = {"satura": inicio("satura"), "glide": inicio("glide"), "rolls": inicio("rolls"), "tono": inicio("tono")}
A0, A1 = rango("antes")
M0, M1 = rango("mal")
TAPE_STOP = 0.75                                  # segundos que tarda el beat malo en frenarse


def activo(truco, t):
    return t >= TRUCOS[truco] and not (A0 <= t < A1)


rng = np.random.default_rng(140)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
N = int(TOTAL * SR)


# ------------------------------------------------------------------ golpes (los mismos para imagen y sonido)
def golpes():
    """Lista de golpes [t, carril, paso, fuerza, capa, extra]; extra = nota MIDI (808/melodía) o tono (hats)."""
    lista = []
    for c0, (nc, _texto, capas, toma) in zip(INICIOS, SECCIONES):
        for compas in range(c0, c0 + nc):
            ultimo = compas == c0 + nc - 1
            b = compas % 2
            for capa in capas:
                patron = PATRONES[capa]
                if capa == "ROLL":
                    # Redoble de clap en el último compás de la subida: corcheas, luego semicorcheas, creciendo
                    patron = {p: 0.35 + 0.6 * p / 15 for p in range(16) if ultimo and (p >= 8 or p % 2 == 0)}
                t_compas = compas * COMPAS
                for paso, fuerza in patron.items():
                    t = t_compas + paso * PASO
                    if t >= GLITCH[1]:
                        continue
                    if toma == "subida" and ultimo and paso >= 8 and capa == "MELODÍA":
                        continue                 # antes del drop se queda solo el redoble
                    extra = 0
                    if capa == "808":
                        extra = BAJO[paso][b]
                    elif capa == "808 MAL":
                        extra = BAJO_MAL[paso]
                    elif capa == "MELODÍA":
                        extra = MELODIA[paso][b]
                    carril = CARRILES.index("CLAP" if capa == "ROLL" else capa.replace(" MAL", ""))
                    if capa == "HATS" and activo("rolls", t) and toma != "subida":
                        continue                 # con redobles, los hats se arman abajo
                    lista.append([round(t, 5), carril, paso, round(fuerza, 3), capa, extra])
                if capa == "HATS" and activo("rolls", t_compas) and toma != "subida":
                    lista += hats_con_redobles(t_compas, b)
    lista.sort(key=lambda g: g[0])
    return lista


def hats_con_redobles(t_compas, b):
    """Corcheas con redobles; con el truco del tono, cada golpe del redoble sube (A) o baja (B) un poco."""
    salida, redobles = [], REDOBLES[b]
    tapados = {p + k for p, (_n, largo) in redobles.items() for k in range(largo)}
    for paso in range(0, 16, 2):
        if paso not in tapados:
            salida.append([t_compas + paso * PASO, paso, 0.8 if paso % 4 == 0 else 0.6, 0])
    for p0, (n, largo) in redobles.items():
        for k in range(n):
            pos = p0 + k * largo / n
            tono = (k + 1) * (1 if b == 0 else -1) if activo("tono", t_compas) else 0
            salida.append([t_compas + pos * PASO, int(pos), 0.45 + 0.35 * k / max(1, n - 1), tono])
    carril = CARRILES.index("HATS")
    return [[round(t, 5), carril, p, round(f, 3), "HATS", tono] for t, p, f, tono in salida if t < GLITCH[1]]


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


def bajo_808(lista):
    """El 808 como un solo oscilador (mono, como en el estudio): cada nota corta la anterior. Con glide, la
    frecuencia se desliza desde la nota anterior; con saturación, se le suman armónicos que se oyen en el cel."""
    notas = [(t, extra) for t, _c, _p, _f, capa, extra in lista if capa in ("808", "808 MAL")]
    frec = np.zeros(N)
    amp = np.zeros(N)
    satura = np.zeros(N)
    previa = None
    for i, (t, nota) in enumerate(notas):
        a = int(t * SR)
        sig = int(notas[i + 1][0] * SR) if i + 1 < len(notas) else N
        b = min(N, sig, a + int(PASO * 6 * SR))
        n = b - a
        tt = np.arange(n) / SR
        f = hz(nota) * np.ones(n)
        if previa is not None and activo("glide", t) and int(previa[0] * SR) + int(PASO * 6 * SR) >= a:
            f = hz(nota) + (hz(previa[1]) - hz(nota)) * np.exp(-tt / 0.045)      # se desliza en ~0.1 s
        f *= 1 + 0.25 * np.exp(-tt * 60)          # golpecito de tono al inicio (el "punch")
        frec[a:b] = f
        env = np.minimum(1, tt / 0.003) * np.exp(-tt * 1.1)
        env *= np.minimum(1, (n - np.arange(n)) / (0.012 * SR))           # suelta sin clic
        amp[a:b] = env
        satura[a:b] = 1 if activo("satura", t) else 0
        previa = (t, nota)
    fase = 2 * np.pi * np.cumsum(frec) / SR
    s = np.sin(fase) * amp
    # Saturación: limpio = seno puro (en la bocina del celular casi no se oye); saturado = tanh con drive alto
    sucio = np.tanh(4.5 * s) * 0.8
    k = np.convolve(satura, np.ones(400) / 400, mode="same")
    return s * (1 - k) * 0.85 + sucio * k


def kick(fuerza=1.0):
    """Kick corto de trap: seno que cae rápido de 190 a 60 Hz y un clic arriba (el 808 pone el cuerpo)."""
    t = np.arange(int(0.13 * SR)) / SR
    f = 60 + 130 * np.exp(-t * 55)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 26)
    s += filtro(rng.normal(0, 1, len(t)), 2000, 10000) * np.exp(-t * 300) * 0.5
    return np.tanh(2.2 * s) * fuerza


def clap():
    t = np.arange(int(0.36 * SR)) / SR
    r = filtro(rng.normal(0, 1, len(t)), 1000, 8000)
    env = sum(np.exp(-np.maximum(0, t - d) * 70) * (t >= d) for d in (0, 0.012, 0.025)) * 0.5
    env += np.exp(-np.maximum(0, t - 0.032) * 13) * (t >= 0.032) * 0.7
    return r * env


def hat(fuerza, tono=0, abierto=False):
    """Hi-hat de ruido filtrado; `tono` en semitonos sube o baja la banda (los redobles que "hablan")."""
    dur, caida = (0.28, 12) if abierto else (0.045, 110)
    t = np.arange(int(dur * SR)) / SR
    k = 2 ** (tono * 2 / 12)                    # cada golpe del redoble se mueve un tono entero
    r = filtro(rng.normal(0, 1, len(t)), 6000 * k, 15000 * min(1.4, k))
    r += np.sin(2 * np.pi * 8200 * k * t) * 0.25            # brillo metálico que se oye subir/bajar
    return r * np.exp(-t * caida) * fuerza * (0.5 if abierto else 0.42)


def campana(nota):
    """Campana oscura: seno + parcial inarmónico (como una FM sencilla), ataque rápido y cola larga."""
    t = np.arange(int(1.1 * SR)) / SR
    f = hz(nota)
    s = np.sin(2 * np.pi * f * t + 1.6 * np.exp(-t * 7) * np.sin(2 * np.pi * f * 3.5 * t))
    s += 0.25 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 3.2) * 0.5


def subida_y_golpe():
    """Subida de ruido y tono antes del drop, y el golpe del 808 + platillo al caer."""
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
    poner(x, (barrido * 0.5 + tono * 0.12) * k ** 2.2, T_SUBIDA, 0.5)
    t = np.arange(int(2.2 * SR)) / SR
    platillo = filtro(rng.normal(0, 1, len(t)), 3500, 15000) * np.exp(-t * 2.4) * 0.5
    poner(x, platillo, T_DROP, 0.6, -0.4)
    poner(x, platillo, T_DROP + 0.01, 0.4, 0.6)
    return x


def sonido(lista):
    bat = np.zeros((N, 2))
    mel = np.zeros((N, 2))
    for t, carril, paso, fuerza, capa, extra in lista:
        capa = capa.replace(" MAL", "")           # el beat malo usa los mismos sonidos (sin sidechain)
        if capa == "KICK":
            poner(bat, kick(fuerza), t, 0.75)
        elif capa in ("CLAP", "ROLL"):
            poner(bat, clap(), t, 0.85 * fuerza)
        elif capa == "HATS":
            poner(bat, hat(fuerza, extra), t, 1.15, lado=0.2 if paso % 2 else -0.1)
        elif capa == "OPEN HAT":
            poner(bat, hat(fuerza, 0, True), t, 0.95, lado=-0.3)
        elif capa == "MELODÍA":
            poner(mel, campana(extra), t, 0.5, lado=0.15 if paso % 2 else -0.15)

    b808 = bajo_808(lista)
    # El 808 se agacha apenitas con cada kick (sidechain corto) para que el golpe quede arriba
    tt = np.arange(N) / SR
    duck = np.ones(N)
    for t, _c, _p, _f, capa, _e in lista:
        if capa == "KICK":
            a = int(t * SR)
            d = tt[a:a + int(0.12 * SR)] - t
            duck[a:a + len(d)] = np.minimum(duck[a:a + len(d)], 1 - 0.5 * np.exp(-d * 30))
    b808 *= duck
    mel = ping_pong(mel, 3 * PASO, 0.4, 5)
    mel = np.stack([eco(mel[:, c], 2.4, 0.4, 2.0, 5 + c) for c in (0, 1)], 1)
    bat[:, 0] = eco(bat[:, 0], 0.7, 0.14, 8.0, 3)
    bat[:, 1] = eco(bat[:, 1], 0.7, 0.14, 8.0, 4)
    mezcla = bat + mel + b808[:, None] * 0.5 + subida_y_golpe()

    # Tape stop: el beat malo se frena como una cinta (la velocidad baja a cero) y queda en silencio
    m0, m1, n = int(M0 * SR), int(M1 * SR), int(TAPE_STOP * SR)
    lee = m0 + np.cumsum(np.linspace(1, 0, n)).astype(int)
    frena = mezcla[lee] * np.minimum(1, np.linspace(1.6, 0, n))[:, None]
    mezcla[m0:m1] = 0
    mezcla[m0:m0 + n] = frena

    g0, g1 = int(GLITCH[0] * SR), int(GLITCH[1] * SR)
    fuente = np.array([mapa_glitch(i / SR) for i in range(g0, g1)])
    trozo = mezcla[(fuente * SR).astype(int)]
    trozo = np.round(trozo * 32) / 32
    trozo = trozo[(np.arange(len(trozo)) // 4) * 4]
    mezcla[g0:g1] = trozo

    # Cierre: un último 808 largo y saturado que cae de tono, con la campana que se aleja
    cola = np.zeros((N, 2))
    t = np.arange(int(2.8 * SR)) / SR
    cae = np.tanh(3.5 * np.sin(2 * np.pi * np.cumsum(hz(36) * 2 ** (-t * 0.35)) / SR)) * np.exp(-t * 1.0)
    poner(cola, cae * 0.7, GLITCH[1])
    poner(cola, kick(1.0), GLITCH[1], 0.8)
    poner(cola, campana(72), GLITCH[1], 0.35)
    cola = np.stack([eco(cola[:, c], 2.4, 0.3, 2.2, 11 + c) for c in (0, 1)], 1)
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
        "golpes": [g[:5] for g in lista if not M0 <= g[0] < M1],     # tras el tape stop no se ve nada
        "secciones": secciones,
        "glitch": list(GLITCH), "cierre": CIERRE, "cierreTexto": CIERRE_TEXTO,
        "trucos": TRUCOS, "antes": [A0, A1], "capasAntes": MALO, "malo": [inicio("malo"), M1],
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
