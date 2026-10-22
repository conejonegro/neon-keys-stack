"""Música de fondo "tripi" para Cineclub Forever: lo-fi psicodélico de cine viejo, sintetizado con numpy.

96 BPM, 8 compases (20 s). Rhodes con trémolo, pad con phaser, cinta que se ondula, theremín con eco,
bajo, batería lo-fi con escobillas y crujido de vinil. Acordes Rem9 – Si♭maj7 – Solm9 – La7 (dos vueltas).
Sin samples ni IA: todo son ondas, ruido y filtros.

Uso: .venv/bin/python collage/musica/tripi.py out/.tmp/cineclub-fondo-tripi-prueba.wav
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
COMPASES = 8
DUR = COMPASES * BAR
N = int(DUR * SR) + SR * 3          # cola para los ecos
rng = np.random.default_rng(1922)    # el año de Nosferatu
hz = lambda m: 440 * 2 ** ((m - 69) / 12)

# acorde por compás: (raíz del bajo, notas del Rhodes)
ACORDES = [
    (38, [53, 57, 60, 64]),   # Rem9  (Fa La Do Mi sobre Re)
    (34, [50, 53, 57, 62]),   # Si♭maj7
    (31, [50, 53, 57, 58]),   # Solm9 (Re Fa La Si♭)
    (33, [49, 55, 58, 64]),   # La7(♭9)  (Do# Sol Si♭ Mi)
]


def pista():
    return np.zeros((N, 2))


def poner(destino, s, t, gan=1.0, lado=0.0):
    a = int(t * SR)
    if a < 0:                      # lo que cae antes del inicio se recorta
        s, a = s[-a:], 0
    if a >= N:
        return
    n = min(len(s), N - a)
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


def filtro(x, bajo=20, alto=20000):
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    curva = (1 / (1 + (bajo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / alto) ** 4))
    return np.fft.irfft(X * (curva[:, None] if x.ndim == 2 else curva), len(x), axis=0)


def reverb(x, segundos=3.2, mezcla=0.35, semilla=3):
    r = np.random.default_rng(semilla)
    t = np.arange(int(segundos * SR)) / SR
    salida = np.zeros_like(x)
    for c in range(2):
        ir = r.normal(0, 1, len(t)) * np.exp(-t * 2.2)
        ir = filtro(ir, 200, 7000)
        ir /= np.sqrt(np.sum(ir ** 2))
        m = 1 << (len(x) + len(ir) - 1).bit_length()
        salida[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], m) * np.fft.rfft(ir, m), m)[: len(x)]
    return x * (1 - mezcla) + salida * mezcla * 2.2


def eco_pingpong(x, retardo, realim=0.5, veces=7):
    y = x.copy()
    d = int(retardo * SR)
    for k in range(1, veces + 1):
        g = realim ** k
        y[d * k:, k % 2] += (x[:-d * k, 0] + x[:-d * k, 1]) * 0.5 * g
    return y


# ------------------------------------------------------------------ instrumentos
def rhodes(m, dur):
    """Piano eléctrico por FM: campana al ataque que se suaviza."""
    t = np.arange(int(dur * SR)) / SR
    f = hz(m)
    indice = 1.6 * np.exp(-t * 3.5) + 0.25
    s = np.sin(2 * np.pi * f * t + indice * np.sin(2 * np.pi * f * t))
    s += 0.25 * np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 30)     # el "tine" metálico
    return s * np.minimum(1, t / 0.004) * np.exp(-t * 1.1) * np.minimum(1, (dur - t) / 0.08)


def pad(notas, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for m in notas:
        for d in (-0.11, 0.0, 0.11):
            f = hz(m + d)
            for k in range(1, 7):
                s += np.sin(2 * np.pi * f * k * t + k * 1.3) / k
    s /= len(notas) * 3
    return s * np.minimum(1, t / 0.9) * np.minimum(1, (dur - t) / 0.9)


def bajo(m, dur, desde=None):
    t = np.arange(int(dur * SR)) / SR
    f = hz(m) if desde is None else hz(desde) + (hz(m) - hz(desde)) * np.minimum(1, t / 0.09)   # deslizamiento
    fase = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(fase) + 0.18 * np.sin(2 * fase) + 0.08 * np.sin(3 * fase)
    return s * np.minimum(1, t / 0.01) * np.exp(-t * 1.6) * np.minimum(1, (dur - t) / 0.05)


def bombo():
    t = np.arange(int(0.42 * SR)) / SR
    f = 46 + 70 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)


def caja():
    t = np.arange(int(0.35 * SR)) / SR
    r = filtro(rng.normal(0, 1, len(t)), 1200, 6000)
    return (r * 0.9 + 0.25 * np.sin(2 * np.pi * 180 * t)) * np.exp(-t * 14)


def escobilla(fuerza=1.0):
    t = np.arange(int(0.16 * SR)) / SR
    r = filtro(rng.normal(0, 1, len(t)), 3000, 11000)
    return r * np.minimum(1, t / 0.02) * np.exp(-t * 26) * fuerza


def theremin(notas, inicio):
    """Notas (midi, duración en beats) con glissando entre ellas y vibrato que crece."""
    total = sum(d for _, d in notas) * BEAT
    n = int(total * SR)
    curva = np.zeros(n)
    t0 = 0
    previo = notas[0][0]
    for m, d in notas:
        a, b = int(t0 * SR), min(n, int((t0 + d * BEAT) * SR))
        k = np.minimum(1, np.arange(b - a) / (0.12 * SR))
        k = k * k * (3 - 2 * k)
        curva[a:b] = previo + (m - previo) * k
        previo = m
        t0 += d * BEAT
    t = np.arange(n) / SR
    vib = (0.18 + 0.22 * np.minimum(1, t / 3)) * np.sin(2 * np.pi * 5.6 * t)
    f = hz(curva + vib)
    fase = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(fase) + 0.12 * np.sin(2 * fase) + 0.05 * np.sin(3 * fase)
    s *= np.minimum(1, t / 0.6) * np.minimum(1, (total - t) / 1.2)
    return s, inicio


def phaser(x, velocidad=0.18, etapas=4, mezcla=0.55):
    """Phaser clásico: filtros pasa-todo cuya frecuencia sube y baja despacio (bucle por muestra)."""
    y = x.copy()
    n = len(x)
    t = np.arange(n) / SR
    fc = 300 * (2 ** (2.6 * (0.5 + 0.5 * np.sin(2 * np.pi * velocidad * t))))
    tan = np.tan(np.pi * fc / SR)
    a = (tan - 1) / (tan + 1)
    for c in range(2):
        s = x[:, c].copy()
        for _ in range(etapas):
            z = 0.0
            out = np.empty(n)
            ac = a if c == 0 else np.roll(a, int(SR * 0.7))
            for i in range(n):
                v = ac[i] * s[i] + z
                z = s[i] - ac[i] * v
                out[i] = v
            s = out
        y[:, c] = x[:, c] * (1 - mezcla) + s * mezcla
    return y


def cinta(x, prof=0.0022, vel=0.33):
    """Wow de cinta: la velocidad de reproducción se ondula muy poco (todo desafina y regresa)."""
    n = len(x)
    t = np.arange(n) / SR
    desfase = prof * (np.sin(2 * np.pi * vel * t) + 0.35 * np.sin(2 * np.pi * vel * 2.7 * t + 1.1))
    idx = np.clip(np.arange(n) + desfase * SR, 0, n - 1)
    return np.stack([np.interp(idx, np.arange(n), x[:, c]) for c in range(2)], axis=1)


def vinil():
    s = filtro(rng.normal(0, 1, N), 400, 5000) * 0.006
    chasquidos = (rng.random(N) > 0.9996) * rng.normal(0, 1, N) * 0.35
    return filtro(chasquidos, 1500, 9000) + s


# ------------------------------------------------------------------ arreglo
def arreglo():
    rh, pd, bj, bt, th = pista(), pista(), pista(), pista(), pista()
    for c in range(COMPASES):
        t = c * BAR
        raiz, notas = ACORDES[c % 4]
        # Rhodes: acorde en el 1 y en el "y" del 2, notas ligeramente rasgueadas; trémolo de lado a lado
        for golpe, dur, g in ((0, 1.5, 0.22), (1.5, 2.5, 0.16)):
            for i, m in enumerate(notas):
                poner(rh, rhodes(m, dur * BEAT + 0.4), t + golpe * BEAT + i * 0.012, g)
        # pad con todo el compás
        poner(pd, pad([raiz + 12] + notas[:3], BAR + 0.9), t - 0.3, 0.11)
        # bajo: raíz en el 1, quinta en el "y" del 2, raíz con deslizamiento en el 3
        poner(bj, bajo(raiz, BEAT * 1.4), t, 0.42)
        poner(bj, bajo(raiz + 7, BEAT * 0.5), t + 1.5 * BEAT, 0.25)
        poner(bj, bajo(raiz, BEAT * 1.3, desde=raiz + 5), t + 2 * BEAT, 0.34)
        if c == COMPASES - 1:
            continue
        # batería a medio tiempo: bombo 1 y "y" del 2, caja en el 3, escobillas en semicorcheas con swing
        if c >= 1:
            poner(bt, bombo(), t, 0.55)
            poner(bt, bombo(), t + 1.5 * BEAT, 0.38)
            poner(bt, caja(), t + 2 * BEAT, 0.24, 0.1)
            for k in range(16):
                sw = 0.06 * BEAT if k % 2 else 0
                poner(bt, escobilla(0.7 if k % 4 == 0 else 0.4), t + k * BEAT / 4 + sw, 0.12, -0.35 if k % 2 else 0.35)
    # theremín: entra en el compás 3, frase de pregunta y respuesta (Re dórico)
    frase = [(69, 2), (72, 1), (74, 3), (72, 1), (69, 1), (67, 4),      # pregunta (12 tiempos)
             (76, 2), (74, 1), (72, 1), (74, 2), (69, 2), (62, 4)]      # respuesta, cae a Re (12 tiempos)
    s, ini = theremin(frase, 2 * BAR)
    poner(th, s, ini, 0.17, 0.15)

    rh = rh * (1 + 0.35 * np.sin(2 * np.pi * (BPM / 60 / 2) * np.arange(N) / SR))[:, None] * np.array([1.0, 1.0])
    pan = 0.5 + 0.5 * np.sin(2 * np.pi * (BPM / 60 / 4) * np.arange(N) / SR)
    rh = np.stack([rh[:, 0] * (0.4 + 0.6 * pan), rh[:, 1] * (1.0 - 0.6 * pan)], axis=1)
    print("phaser del pad…")
    pd = phaser(filtro(pd, 80, 3500))
    th = eco_pingpong(th, BEAT * 0.75, 0.45)
    bt = filtro(bt, 30, 9000)
    # bitcrush suave a la batería (lo-fi)
    bt = np.round(bt * 64) / 64

    mezcla = rh * 1.0 + pd + bj + bt + th
    mezcla = reverb(mezcla, mezcla=0.3)
    mezcla[:, 0] += vinil()
    mezcla[:, 1] += np.roll(vinil(), 7919)
    mezcla = cinta(mezcla)
    mezcla = mezcla[: int((DUR + 2.2) * SR)]
    t = np.arange(len(mezcla)) / SR
    mezcla *= (np.minimum(1, t / 1.2) * np.minimum(1, (t[-1] - t) / 2.4))[:, None]
    mezcla = np.tanh(mezcla * 1.1)
    return mezcla / np.max(np.abs(mezcla)) * 0.89


if __name__ == "__main__":
    salida = sys.argv[1]
    s = arreglo()
    with wave.open(salida, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((s * 32767).astype("<i2").tobytes())
    print(f"Listo: {salida} ({len(s) / SR:.1f} s)")
