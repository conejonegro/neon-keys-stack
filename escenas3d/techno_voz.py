#!/usr/bin/env python3
"""Neon Keys · pega la voz en off (un solo audio de la IA de voz) a un beat explicado (techno.py, trap.py; ADR-022).

Corta la voz por sus silencios, junta los pedazos en las frases del guion (algunas frases traen una pausa por
dentro), pone cada frase al inicio de su sección, baja el beat mientras se habla y mueve los subtítulos para que
cada palabra salga cuando se dice. Si una frase no cabe en su sección, se acelera un poco (sin cambiar el tono).

Uso (después de `.venv/bin/python escenas3d/techno.py`):
    .venv/bin/python escenas3d/techno_voz.py out/pruebas/voces/techno/techno-voiceover-liam.mp3
        # → out/.tmp/beat-techno-rueda-voz.json + .wav
    cd escenas3d && node grabar.js escenas/techno.html out/videos/beats/beat-techno-rueda-voz.mp4 \\
        --datos out/.tmp/beat-techno-rueda-voz.json --audio out/.tmp/beat-techno-rueda-voz.wav

    # El de trap (después de `.venv/bin/python escenas3d/trap.py`):
    .venv/bin/python escenas3d/techno_voz.py ~/Downloads/trap-voice.mp3 --beat beat-trap-vacio

    # La batería por niveles (después de `.venv/bin/python escenas3d/punk.py`); su escena pone sus propios textos
    .venv/bin/python escenas3d/techno_voz.py ~/Downloads/voz-reto-bateria.mp3 --beat beat-punk-kids
"""

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
TMP = RAIZ / "out" / ".tmp"
FFMPEG = Path.home() / ".local/bin/ffmpeg"
SR = 44100

# Por beat: pedazos de voz (separados por silencio) que forman cada frase del guion, en orden
PEDAZOS = {
    "beat-techno-rueda": [1, 2, 2, 2, 2, 2, 1, 2, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    "beat-trap-vacio": [1, 1, 3, 1, 2, 2, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1],
    "beat-reggaeton-perreo": [1, 1, 2, 2, 5, 1, 2, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1],
    "beat-punk-kids": [1, 2, 3, 3, 1, 3, 3, 3, 2, 1],
    "beat-psytrance": [1, 1, 3, 2, 3, 1, 2, 1, 2, 2, 1, 1, 1, 2, 1, 1, 1],
    # trance-voz-liam-completa.wav: las dos tomas de ElevenLabs juntas y con el gancho en orden
    "beat-trance": [1, 1, 1, 4, 2, 5, 2, 5, 4, 4, 3, 2, 5, 3, 3, 3, 2, 1, 1, 1],
}
# Formatos que no llevan una frase por sección (punk.py, ADR-025; los respiros sin voz de psytrance.py, ADR-027):
# en qué sección (toma) empieza cada frase; "fin" = el último compás (el golpe final), "NK" = el cierre con la
# marca. Sin entrada aquí: una frase por sección + la del cierre
LUGAR_FRASE = {
    "beat-punk-kids": ["reto", "promesa", "bombo-tarola", "hihat", "redoble", "otra-vez", "rapido1", "banda",
                       "cierre", "fin"],
    "beat-psytrance": ["malo", "mal", "kick", "bajo", "galope", "clap", "openhat", "hats", "acid", "dato", "recap",
                       "antes", "ahora", "subida", "drop", "drop3", "NK"],
    "beat-trance": ["gancho", "gancho2", "cero", "kick", "bajo", "bajo2", "clap", "acordes", "acordes2", "gate",
                    "delay", "delay2", "arp", "arp2", "sidechain", "sidechain2", "break", "drop", "drop3", "NK"],
}
# Pausa máxima dentro de una frase (segundos): la voz que se detiene entre notas ("Re… Si bemol… Fa…") se aprieta
# para caber en su sección sin acelerarla. Sin entrada: las pausas se quedan como vienen
PAUSA_MAX = {"beat-trance": 0.22}
# Efectos de la voz por beat (frases contadas desde 0, la última es el cierre):
#   radio = suena chiquita, como bocina de celular (el beat malo); tiros = la cola de esa palabra rebota en delay;
#   grande = saturada con delay y reverb enormes (el drop); cola = eco que se aleja (el cierre)
EFECTOS = {
    "beat-reggaeton-perreo": {
        "reverb": 0.0,                           # la voz va limpia; los efectos solo en algunas palabras
        "radio": [],
        "tiros": [(4, "dembow"), (13, "ahora"), (14, "dembow")],
        "grande": [15],
        "cola": [17],
    },
    "beat-psytrance": {
        "reverb": 0.0,
        "radio": [],
        "tiros": [(4, "galope"), (8, "acid")],
        "grande": [14],                          # "…y suéltalo." (cae el drop)
        "cola": [16],
    },
    "beat-trance": {
        "reverb": 0.0,
        "radio": [],
        "tiros": [(10, "delay"), (13, "eco")],
        "grande": [17],                          # "¡A disfrutar el beat!" (cae el drop)
        "cola": [19],
    },
}
UMBRAL_DB = -38          # más bajo que esto es silencio
SILENCIO_MIN = 0.18      # segundos de silencio para separar pedazos
ENTRADA = 0.08           # la frase empieza un poquito después del cambio de sección
HOLGURA = 0.12           # espacio mínimo antes de la frase siguiente
BAJA_BEAT = 0.5          # el beat baja a la mitad (−6 dB) mientras se habla


def leer(ruta, tempo=1.0):
    """Audio → numpy mono a 44.1 kHz (con ffmpeg; tempo != 1 acelera sin cambiar el tono)."""
    filtro = ["-af", f"atempo={tempo:.4f}"] if abs(tempo - 1) > 1e-3 else []
    crudo = subprocess.run([str(FFMPEG), "-v", "error", "-i", str(ruta), *filtro, "-ac", "1", "-ar", str(SR),
                            "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(crudo, dtype="<f4").astype(np.float64)


def pedazos(x):
    """[(inicio, fin)] en segundos de cada tramo con voz."""
    paso = int(0.01 * SR)
    n = len(x) // paso
    rms = np.sqrt(np.mean(x[:n * paso].reshape(n, paso) ** 2, axis=1))
    voz = 20 * np.log10(np.maximum(rms, 1e-9)) > UMBRAL_DB
    # Un tramo de voz termina solo cuando el silencio dura SILENCIO_MIN o más
    tramos, inicio, callado = [], None, 0
    for i, v in enumerate(voz):
        if v:
            if inicio is None:
                inicio = i
            callado = 0
        elif inicio is not None:
            callado += 1
            if callado * 0.01 >= SILENCIO_MIN:
                tramos.append((inicio * 0.01, (i - callado + 1) * 0.01))
                inicio, callado = None, 0
    if inicio is not None:
        tramos.append((inicio * 0.01, (n - callado) * 0.01))
    return tramos


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ruta_voz = Path(sys.argv[1]).expanduser()
    nombre = sys.argv[sys.argv.index("--beat") + 1] if "--beat" in sys.argv else "beat-techno-rueda"
    grupos = PEDAZOS[nombre]
    datos = json.loads((TMP / f"{nombre}.json").read_text(encoding="utf-8"))
    secciones = datos["secciones"]
    voz = leer(ruta_voz)
    tramos = pedazos(voz)
    lugar = LUGAR_FRASE.get(nombre)
    frases_guion = len(lugar) if lugar else len(secciones) + 1   # + "Sígueme para más" del cierre
    if len(tramos) != sum(grupos) or len(grupos) != frases_guion:
        sys.exit(f"La voz tiene {len(tramos)} pedazos y el guion espera {sum(grupos)} "
                 f"({frases_guion} frases). Revisa PEDAZOS en techno_voz.py.")

    # Agrupa los pedazos en frases y decide dónde va cada una
    if lugar:
        t0 = {s["toma"]: s["t0"] for s in secciones}
        especiales = {"fin": datos.get("fin"), "NK": datos["cierre"]}
        inicios = [especiales[l] if l in especiales else t0[l] for l in lugar]
    else:
        inicios = [s["t0"] for s in secciones] + [datos["cierre"]]
    finales = inicios[1:] + [datos["total"] - 0.3]
    pista = np.zeros(int(datos["total"] * SR))
    hablando = np.zeros_like(pista)
    lugares = []                                          # (muestra donde empieza, largo) de cada frase
    de_frase = []                                         # la sección (con sus palabras) de cada frase, o None
    k = 0
    print("Frase  va en   dura   cabe   acelera")
    for i, n in enumerate(grupos):
        a, b = max(0.0, tramos[k][0] - 0.03), tramos[k + n - 1][1] + 0.08
        trozo = voz[int(a * SR):int(b * SR)]
        if nombre in PAUSA_MAX:
            # Une los pedazos de la frase con pausas de PAUSA_MAX como mucho
            partes = [voz[int(max(0.0, x - 0.03) * SR):int((y + 0.08) * SR)] for x, y in tramos[k:k + n]]
            huecos = [min(PAUSA_MAX[nombre], tramos[k + m + 1][0] - tramos[k + m][1]) for m in range(n - 1)]
            trozo = partes[0]
            for h, parte in zip(huecos, partes[1:]):
                trozo = np.concatenate([trozo[:len(trozo) - int(0.08 * SR)], np.zeros(int(max(0, h - 0.11) * SR)),
                                        parte])
        k += n
        dur = len(trozo) / SR
        cabe = finales[i] - inicios[i] - ENTRADA - HOLGURA
        tempo = max(1.0, dur / cabe)
        if tempo > 1:
            tmp = TMP / "voz-trozo.wav"
            escribir(tmp, trozo, 1)
            trozo = leer(tmp, tempo)
            tmp.unlink()
        t = inicios[i] + ENTRADA
        j = int(t * SR)
        trozo = trozo[: len(pista) - j]
        lugares.append((j, len(trozo)))
        pista[j:j + len(trozo)] += trozo
        hablando[j:j + len(trozo)] = 1
        print(f"{i + 1:5d}  {t:5.1f} s {len(trozo) / SR:4.2f} s {cabe:4.2f} s  {'×%.2f' % tempo if tempo > 1 else '—'}")

        # Subtítulos: cada palabra sale cuando se dice (reparto por largo de la palabra dentro de la frase)
        sec = None
        if lugar and lugar[i] not in ("fin", "NK"):
            sec = next(s for s in secciones if s["toma"] == lugar[i])
        elif not lugar and i < len(secciones):
            sec = secciones[i]
        de_frase.append(sec)
        if sec and sec.get("palabras"):
            palabras = sec["palabras"]
            pesos = np.array([len(p["txt"]) + 2 for p in palabras], float)
            antes = np.concatenate([[0], np.cumsum(pesos)[:-1]]) / pesos.sum()
            for p, f in zip(palabras, antes):
                p["t"] = round(t + f * len(trozo) / SR - 0.04, 3)

    # Mezcla: la voz arriba y el beat se agacha mientras se habla (sube y baja suave)
    ataque, suelta = int(0.04 * SR), int(0.3 * SR)
    env = np.convolve(hablando, np.ones(ataque) / ataque, mode="same")
    env = np.convolve(np.minimum(1, env * 1.5), np.ones(suelta) / suelta, mode="same")
    with wave.open(str(TMP / f"{nombre}.wav")) as w:
        beat = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2) / 32768
    n = min(len(beat), len(pista))
    beat, pista, env = beat[:n], pista[:n], env[:n]
    pista *= 0.92 / np.max(np.abs(pista))
    voz_st = pista[:, None] * np.ones((1, 2))
    if nombre in EFECTOS:
        voz_st = efectos(pista, EFECTOS[nombre], lugares, de_frase, datos["beat"])
    mezcla = beat * (1 - BAJA_BEAT * np.clip(env, 0, 1))[:, None] + voz_st * 0.85
    mezcla *= 0.94 / np.max(np.abs(mezcla))

    (TMP / f"{nombre}-voz.json").write_text(json.dumps(datos), encoding="utf-8")
    escribir(TMP / f"{nombre}-voz.wav", mezcla, 2)
    print(TMP / f"{nombre}-voz.json")
    print(TMP / f"{nombre}-voz.wav")


def banda(x, bajo, alto):
    """Paso banda suave con FFT (bajo/alto en Hz)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * (1 / (1 + (bajo / np.maximum(f, 1)) ** 4)) / (1 + (f / alto) ** 4), len(x))


def reverb(x, segundos, caida, semilla):
    r = np.random.default_rng(semilla)
    t = np.arange(int(segundos * SR)) / SR
    ir = r.normal(0, 1, len(t)) * np.exp(-t * caida)
    ir /= np.sqrt(np.sum(ir ** 2))
    m = 1 << (len(x) + len(ir) - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]


def rebotes(x, retardo, veces, caida):
    """Delay que rebota izquierda ↔ derecha y se va oscureciendo."""
    y = np.zeros((len(x), 2))
    d = int(retardo * SR)
    eco = banda(x, 350, 5000)
    for k in range(1, veces + 1):
        if d * k >= len(x):
            break
        y[d * k:, k % 2] += eco[:len(x) - d * k] * caida ** k
    return y


def efectos(pista, cfg, lugares, secciones, beat):
    """Voz mono → estéreo con sus efectos: radio, tiros de delay en palabras clave, el drop enorme y la cola."""
    seca = pista.copy()
    envio = np.zeros(len(pista))                  # lo que se manda al delay
    grande = np.zeros(len(pista))
    for i in cfg["radio"]:
        j, n = lugares[i]
        seca[j:j + n] = np.tanh(3 * banda(seca[j:j + n], 600, 3200)) * 0.55
    for i, palabra in cfg["tiros"]:
        j, n = lugares[i]
        ps = secciones[i]["palabras"]
        k = next(x for x, p in enumerate(ps) if palabra in p["txt"].lower())
        fin = ps[k + 1]["t"] if k + 1 < len(ps) else (j + n) / SR
        b = min(j + n, int((fin + 0.04) * SR))
        a = max(int(ps[k]["t"] * SR), b - int(0.32 * SR))       # la cola de la palabra: "…bow"
        envio[a:b] += seca[a:b] * np.hanning(b - a)
    for i in cfg["grande"]:
        j, n = lugares[i]
        grande[j:j + n] += seca[j:j + n]
    for i in cfg["cola"]:
        j, n = lugares[i]
        envio[j + n // 2:j + n] += seca[j + n // 2:j + n]

    voz = seca[:, None] * np.ones((1, 2))
    voz += reverb(seca, 1.2, 4.0, 1)[:, None] * cfg["reverb"] * np.array([1.0, 0.9])
    voz += rebotes(envio, beat * 0.75, 6, 0.55) * 0.7              # corchea con puntillo, al tempo
    voz += rebotes(grande, beat * 0.75, 8, 0.65) * 0.8
    voz += np.stack([reverb(grande, 3.0, 1.6, 2 + c) for c in (0, 1)], 1) * 0.45
    return voz


def escribir(ruta, x, canales):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(canales)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    main()
