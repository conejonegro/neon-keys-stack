"""Beat de boom bap tumbado para "Tu primer beat en una drum machine" (escenas/drum-machine.html).

88 BPM, swing de MPC en semicorcheas, la tarola un poco atrasada (laid back). Batería sintetizada como los sonidos
de una máquina profesional (cada pad suena siempre igual; la fuerza cambia el volumen), cuadrada a la rejilla con
swing. Un "sample" original (Rhodes + cuerdas en Fa menor) cortado en el pad CHOP, bajo cálido y, de vez en cuando,
un efecto en el pad FX (scratch, platillo al revés). Cada golpe es un evento de un pad: el mismo tiempo mueve el audio y la escena.

Uso: .venv/bin/python escenas3d/boombap.py  → out/.tmp/beat-drum-machine.{wav,json}
     y una copia del audio para revisar en out/pruebas/beats/beat-drum-machine-8compases.wav
     --prueba: 4 compases solo con kick, tarola y hi-hat (para revisar pads y sincronía) → beat-drum-machine-prueba
"""
import argparse
import json
import shutil
import wave
from pathlib import Path

import numpy as np
import tinysoundfont

RAIZ = Path(__file__).resolve().parent.parent
SOUNDFONT = RAIZ / "soundfonts" / "FluidR3Mono_GM.sf3"
SR = 44100
_args = argparse.ArgumentParser(description=__doc__.split("\n")[0])
_args.add_argument("--prueba", action="store_true", help="4 compases solo con kick, tarola y hi-hat")
PRUEBA = _args.parse_args().prueba
NOMBRE = "beat-drum-machine-prueba" if PRUEBA else "beat-drum-machine"
SOLO_BATERIA = ("KICK", "SNARE", "HI-HAT", "OPEN HAT")

BPM = 88
BEAT = 60 / BPM
COMPAS = 4 * BEAT
PASO = BEAT / 4
SWING = 0.62                      # 50 % = recto; 62 % = las semicorcheas pares se atrasan (MPC)
TAROLA_ATRAS = 0.018              # la tarola cae 18 ms detrás del pulso: lo que lo hace "tumbado"
COMPASES = 4 if PRUEBA else 8
TOTAL = COMPASES * COMPAS + 1.2   # cola para que respire el último golpe
N = int(TOTAL * SR)

# Patrones de un compás (16 semicorcheas). o = golpe fuerte, x = normal, . = fantasma
PATRONES = {
    "A": {"KICK": "o-------o-x-----", "SNARE": "----o-------o---", "PERC": "-----------.----"},
    "B": {"KICK": "o-----x---o--x--", "SNARE": "----o--.----o---", "OPEN HAT": "--------------x-"},
    "A2": {"KICK": "o-------o-x-----", "SNARE": "----o-------o---", "PERC": "-------.---.----"},
    # Fin de frase: bombo que empuja al compás siguiente y tarola fantasma antes del 1
    "fin": {"KICK": "o-------o-x---x-", "SNARE": "----o-------o-..", "OPEN HAT": "------x---------"},
}
ORDEN = ["A", "B", "A2", "fin", "A", "B", "A2", "fin"]
FUERZA = {"o": 1.0, "x": 0.78, ".": 0.32}
# Hats en semicorcheas (note repeat de la MPC) con dinámica fija: tiempo fuerte, contratiempo, las de en medio suaves
HATS = [0.9, 0.3, 0.6, 0.38, 0.85, 0.3, 0.62, 0.42, 0.88, 0.3, 0.6, 0.36, 0.84, 0.32, 0.0, 0.45]

# El "sample": un acorde por compás en Fa menor (voicings de soul, sin raíz: la raíz la toca el bajo, en el
# registro de 58–87 Hz, que todavía se oye en la bocina del celular)
ACORDES = [
    ("Fm9", 41, [56, 60, 63, 67]),
    ("D♭maj9", 37, [53, 56, 60, 63]),
    ("B♭m9", 34, [56, 60, 61, 65]),
    ("C7♯9", 36, [52, 58, 63, 64]),
]
# Cortes del CHOP en cada compás: (semicorchea, duración en semicorcheas). El primero es el acorde completo
CORTES = {0: [(0, 10), (11, 5)], 1: [(0, 16)], 2: [(0, 10), (11, 5)], 3: [(0, 8), (8, 3), (11, 5)]}
# Bajo: (semicorchea, semitonos sobre la raíz, duración en semicorcheas)
BAJO = [(0, 0, 5), (7, 0, 2), (10, 0, 3), (14, 7, 2)]
BAJO_FIN = [(0, 0, 5), (7, 0, 2), (10, 0, 3), (14, 4, 2)]   # en el C7: sube a Mi para caer en Fa

# Efectos del pad FX, de vez en cuando: (compás, semicorchea, efecto)
EFECTOS = [(1, 12, "scratch"), (3, 8, "reversa"), (7, 12, "scratch")]


def t_paso(compas, paso):
    """Tiempo de una semicorchea con swing: las pares (2.ª de cada corchea) se atrasan."""
    t = compas * COMPAS + (paso // 2) * 2 * PASO
    return t + (2 * PASO * SWING if paso % 2 else 0)


def golpes():
    """Lista de eventos (t, pad, fuerza). La misma lista arma el audio y anima los pads."""
    lista = []
    for c, nombre in enumerate(ORDEN):
        for pad, patron in PATRONES[nombre].items():
            for p, s in enumerate(patron):
                if s in FUERZA:
                    t = t_paso(c, p) + (TAROLA_ATRAS if pad == "SNARE" else 0)
                    lista.append((t, pad, FUERZA[s]))
        abierto = [p for p, s in enumerate(PATRONES[nombre].get("OPEN HAT", "")) if s != "-"]
        for p, v in enumerate(HATS):
            if v and p not in abierto:
                lista.append((t_paso(c, p), "HI-HAT", v))
        for p, dur in CORTES[c % 4]:
            lista.append((t_paso(c, p), "CHOP", 0.9 if p == 0 else 0.7))
        for p, _semi, _dur in (BAJO_FIN if c % 4 == 3 else BAJO):
            lista.append((t_paso(c, p), "BASS", 0.85 if p == 0 else 0.65))
        for c_fx, p, _efecto in EFECTOS:
            if c_fx == c:
                lista.append((t_paso(c, p), "FX", 1.0))
    lista.sort()
    return [g for g in lista if g[1] in SOLO_BATERIA] if PRUEBA else lista


# ------------------------------------------------------------------ síntesis
def sintetizar(eventos, programas, n_total=N):
    """eventos: (t, canal, nota, velocidad, duración). programas: {canal: (banco, preset, es_bateria)}."""
    synth = tinysoundfont.Synth(samplerate=SR)
    sfid = synth.sfload(str(SOUNDFONT))
    for canal, (banco, preset, bateria) in programas.items():
        synth.program_select(canal, sfid, banco, preset, bateria)
    cola = [(t, 1, c, n, v) for t, c, n, v, _d in eventos] + [(t + d, 0, c, n, 0) for t, c, n, _v, d in eventos]
    cola.sort(key=lambda e: (e[0], e[1]))
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
    resto = n_total - int(round(cursor * SR))
    if resto > 0:
        partes.append(np.frombuffer(synth.generate(resto), dtype=np.float32).copy())
    x = np.concatenate(partes).reshape(-1, 2).astype(np.float64)
    return x[:n_total] if len(x) >= n_total else np.pad(x, ((0, n_total - len(x)), (0, 0)))


def filtro(x, bajo, alto, orden=4):
    """Paso banda suave con FFT (bajo/alto en Hz); funciona en mono o estéreo."""
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    curva = (1 / (1 + (bajo / np.maximum(f, 1)) ** orden)) * (1 / (1 + (f / alto) ** orden))
    return np.fft.irfft(X * (curva[:, None] if x.ndim == 2 else curva), len(x), axis=0)


def sala(x, segundos=0.5, mezcla=0.18, caida=9.0, semilla=0):
    """Reverb corta de cuarto (ruido con caída), por canal."""
    r = np.random.default_rng(semilla)
    t = np.arange(int(segundos * SR)) / SR
    y = np.empty_like(x)
    for c in range(x.shape[1]):
        ir = r.normal(0, 1, len(t)) * np.exp(-t * caida)
        ir /= np.sqrt(np.sum(ir ** 2))
        m = 1 << (len(x) + len(ir) - 1).bit_length()
        humedo = np.fft.irfft(np.fft.rfft(x[:, c], m) * np.fft.rfft(ir, m), m)[: len(x)]
        y[:, c] = x[:, c] * (1 - mezcla) + humedo * mezcla * 2.5
    return y


def poner(destino, s, t, gan=1.0):
    i = int(round(t * SR))
    if i >= len(destino):
        return
    n = min(len(s), len(destino) - i)
    destino[i:i + n] += s[:n] * gan


# ------------------------------------------------------------------ el kit (un sonido fijo por pad)
def _t(segundos):
    return np.arange(int(segundos * SR)) / SR


def kit():
    """Los sonidos de la máquina: se calculan una vez y cada golpe los reproduce igual (como un sample)."""
    r = np.random.default_rng(12)
    # Bombo: barrido de 160 a 50 Hz con cuerpo largo + golpe del mazo (clic filtrado) para el celular
    t = _t(0.5)
    cuerpo = np.sin(2 * np.pi * np.cumsum(50 + 110 * np.exp(-t * 38)) / SR) * np.exp(-t * 6.5)
    mazo = filtro(r.normal(0, 1, len(t)), 1800, 9000) * np.exp(-t * 260) * 0.45
    bombo = np.tanh((cuerpo + mazo) * 1.6) / np.tanh(1.6)
    # Tarola: dos tonos de parche + cuerpo de bordón (ruido) + chasquido arriba, compactada
    t = _t(0.35)
    parche = (np.sin(2 * np.pi * np.cumsum(185 + 70 * np.exp(-t * 60)) / SR) * np.exp(-t * 24) * 0.7
              + np.sin(2 * np.pi * 330 * t) * np.exp(-t * 32) * 0.3)
    bordon = filtro(r.normal(0, 1, len(t)), 1200, 9000) * np.exp(-t * 16)
    chasquido = filtro(r.normal(0, 1, len(t)), 3500, 12000) * np.exp(-t * 90) * 0.6
    tarola = np.tanh((parche + bordon * 0.85 + chasquido) * 1.5) / np.tanh(1.5)
    # Hi-hats metálicos: seis osciladores cuadrados desafinados (como la 808/909) + aire, muy agudos
    def metal(segundos, caida):
        t = _t(segundos)
        m = sum(np.sign(np.sin(2 * np.pi * f * 1.45 * t + k)) for k, f in enumerate([205.3, 304.4, 369.6, 522.7, 540.0, 800.0]))
        m = filtro(m / 6 + r.normal(0, 0.35, len(t)), 7000, 16000)
        return m * np.minimum(1, t / 0.0008) * np.exp(-t * caida)
    hat, abierto = metal(0.12, 60), metal(0.55, 7)
    # Rim: clic de madera seco
    t = _t(0.08)
    rim = (np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 95) + np.sin(2 * np.pi * 820 * t) * np.exp(-t * 70) * 0.6
           + filtro(r.normal(0, 1, len(t)), 2000, 10000) * np.exp(-t * 250) * 0.5)
    norm = lambda x: x / np.max(np.abs(x))
    return {"KICK": norm(bombo), "SNARE": norm(tarola), "HI-HAT": norm(hat), "OPEN HAT": norm(abierto), "PERC": norm(rim)}


def scratch(reb):
    """Scratch de bebé sobre el inicio del sample: el disco va y viene 4 veces en un tiempo."""
    t = _t(BEAT)
    pos = 0.11 * np.abs(np.sin(np.pi * t / PASO)) * SR + 0.02 * SR
    i0 = pos.astype(int)
    a = (pos - i0)[:, None]
    y = reb[i0] * (1 - a) + reb[i0 + 1] * a
    y = filtro(y, 250, 9000)
    return np.tanh(y * 1.8) * np.minimum(1, (BEAT - t) / 0.02)[:, None]


def reversa():
    """Platillo al revés: crece durante dos tiempos y se corta justo en el 1 del compás siguiente."""
    r = np.random.default_rng(21)
    t = _t(2 * BEAT)
    m = sum(np.sign(np.sin(2 * np.pi * f * 1.1 * t + k)) for k, f in enumerate([205.3, 304.4, 369.6, 522.7, 540.0, 800.0]))
    plato = filtro(m / 6 * 0.6 + r.normal(0, 1, len(t)), 3000, 14000) * np.exp(-t * 2.4)
    plato = plato[::-1] * np.minimum(1, t / 0.15)
    return np.stack([plato, np.roll(plato, 90)], 1)


def lofi(x, semilla=5):
    """Cadena de sampler: banda apenas recortada, saturación ligera y un poco de wow (limpio, sin bits de menos)."""
    y = filtro(x, 90, 9000, orden=2)
    n = len(y)
    t = np.arange(n) / SR
    wow = 0.0018 * np.sin(2 * np.pi * 0.55 * t) + 0.0006 * np.sin(2 * np.pi * 3.1 * t + 1)
    lee = np.clip(np.arange(n) + wow * SR, 0, n - 1)
    i0 = lee.astype(int)
    i1 = np.minimum(i0 + 1, n - 1)
    a = (lee - i0)[:, None]
    y = y[i0] * (1 - a) + y[i1] * a
    return np.tanh(y * 1.2) / np.tanh(1.2)


def sample_acordes():
    """Renderiza el "sample" original: cada acorde tocado por Rhodes y cuerdas, ya procesado. Devuelve 4 rebanadas."""
    largo = COMPAS + 0.6
    rebanadas = []
    for _nombre, _raiz, notas in ACORDES:
        n = int(largo * SR)
        eventos = []
        for k, nota in enumerate(notas):
            # Rasgueo humano del Rhodes: cada nota un poco después
            eventos.append((0.012 * k, 0, nota, 92 - 4 * k, COMPAS * 0.95))
            eventos.append((0.0, 1, nota + 12 if k == len(notas) - 1 else nota, 58, COMPAS))
        x = sintetizar(eventos, {0: (0, 4, False), 1: (0, 49, False)}, n)
        rebanadas.append(lofi(x / (np.max(np.abs(x)) + 1e-9) * 0.9))
    return rebanadas


def sonido(lista):
    sonidos = kit()
    gan = {"KICK": 1.0, "SNARE": 0.8, "HI-HAT": 0.28, "OPEN HAT": 0.22, "PERC": 0.3}   # volumen de cada pad
    lado = {"HI-HAT": 0.25, "OPEN HAT": 0.25, "PERC": -0.3}     # hats un poco a la derecha, rim a la izquierda
    tarolas, resto = np.zeros((N, 2)), np.zeros((N, 2))
    hats = sorted(t for t, pad, _v in lista if pad == "HI-HAT")
    for t, pad, v in lista:
        if pad not in sonidos:
            continue
        s = sonidos[pad] * gan[pad] * v ** 1.3
        if pad == "OPEN HAT":
            # Grupo de choke: el siguiente hi-hat cerrado corta al abierto, como en una máquina real
            sig = next((h for h in hats if h > t + 1e-3), None)
            if sig is not None:
                n = int((sig - t) * SR)
                s = s[:n] * np.minimum(1, (n - np.arange(min(n, len(s)))) / (0.004 * SR))
        p = lado.get(pad, 0.0)
        estereo = np.stack([s * (1 - max(p, 0)), s * (1 + min(p, 0))], 1)
        poner(tarolas if pad == "SNARE" else resto, estereo, t)
    # La tarola lleva un poco de cuarto; lo demás va seco
    bateria = sala(tarolas, 0.5, 0.12, 9.0, 7) + resto
    bateria = np.tanh(bateria * 1.05) / 1.05

    # El sample cortado: cada corte reproduce la rebanada del acorde de ese compás desde el inicio (o desde el
    # punto del corte, como un chop de MPC) y se corta con un desvanecido corto
    rebanadas = sample_acordes() if not PRUEBA else [np.zeros((N, 2))] * 4
    chop = np.zeros((N, 2))
    for c in range(COMPASES):
        reb = rebanadas[c % 4]
        for p, dur in CORTES[c % 4]:
            desde = int(p * PASO * SR) if p else 0
            largo = int(dur * PASO * SR * (1.0 if p == 0 else 0.92))
            trozo = reb[desde:desde + largo].copy()
            f = min(int(0.03 * SR), len(trozo))
            trozo[-f:] *= np.linspace(1, 0, f)[:, None]
            poner(chop, trozo, t_paso(c, p), 1.0 if p == 0 else 0.85)

    # Bajo: bajo eléctrico del soundfont (dedos) + un seno grave debajo; redondo, sin brillo
    notas_bajo, sub = [], np.zeros(N)
    for c in range(COMPASES):
        raiz = ACORDES[c % 4][1]
        for p, semi, dur in (BAJO_FIN if c % 4 == 3 else BAJO):
            t, d, nota = t_paso(c, p), dur * PASO * 0.95, raiz + semi
            notas_bajo.append((t, 1, nota, 100 if p == 0 else 84, d))
            tt = np.arange(int(d * SR)) / SR
            env = np.minimum(1, tt / 0.008) * np.minimum(1, (d - tt) / 0.04)
            poner(sub, np.sin(2 * np.pi * 440 * 2 ** ((nota - 69) / 12) * tt) * env, t)
    bajo = filtro(sintetizar(notas_bajo, {1: (0, 33, False)}).mean(1), 35, 1100)
    bajo = np.tanh((bajo / (np.max(np.abs(bajo)) + 1e-9) + sub * 0.7) * 1.6)

    # Sidechain suave: el sample y el bajo se agachan un poco con cada bombo (el bombo manda)
    agacha = np.ones(N)
    for t, pad, v in lista:
        if pad == "KICK":
            i = int(t * SR)
            k = np.arange(int(0.18 * SR)) / SR
            seg = 1 - 0.35 * v * np.exp(-k * 18)
            agacha[i:i + len(seg)] = np.minimum(agacha[i:i + len(seg)], seg[:max(0, N - i)])

    # Efectos del pad FX
    fx = np.zeros((N, 2))
    for c, p, efecto in EFECTOS:
        if c < COMPASES and not PRUEBA:
            poner(fx, scratch(rebanadas[0]) if efecto == "scratch" else reversa(), t_paso(c, p))

    if PRUEBA:
        chop, bajo = np.zeros((N, 2)), np.zeros(N)
    rms = lambda x: np.sqrt(np.mean(x ** 2)) + 1e-12
    nivel = lambda x, db: x * 10 ** (db / 20) / rms(x)
    mezcla = (nivel(bateria, -12)
              + nivel(chop, -19) * agacha[:, None]
              + nivel(bajo, -17)[:, None] * agacha[:, None]
              + (nivel(fx, -21) if np.any(fx) else 0))
    mezcla = np.tanh(mezcla * 1.15)
    mezcla = filtro(mezcla, 18, 15000, orden=8)       # sin lo de arriba de 15 kHz: el AAC no se pasa de 0 dB
    fade = int(0.8 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return mezcla / np.max(np.abs(mezcla)) * 0.84     # pico a −1.5 dB


def escribir_wav(ruta, x):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def main():
    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    lista = golpes()
    escribir_wav(tmp / f"{NOMBRE}.wav", sonido(lista))
    datos = {
        "bpm": BPM, "swing": round(SWING * 100), "total": TOTAL, "estado": "PLAY",
        "golpes": [{"t": round(t, 4), "pad": pad, "v": round(v, 3)} for t, pad, v in lista],
        "textos": [],
    }
    (tmp / f"{NOMBRE}.json").write_text(json.dumps(datos, ensure_ascii=False))
    if not PRUEBA:
        destino = RAIZ / "out" / "pruebas" / "beats" / f"{NOMBRE}-8compases.wav"
        shutil.copy(tmp / f"{NOMBRE}.wav", destino)
        print(f"Audio: {destino}")
    print(f"{NOMBRE}: {TOTAL:.1f} s, {len(lista)} golpes")


if __name__ == "__main__":
    main()
