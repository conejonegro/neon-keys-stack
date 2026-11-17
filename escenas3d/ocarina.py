"""Neon Keys · Tributo a Zelda: Ocarina of Time, "Song of Storms" en electrónico (escena escenas/ocarina.html).

Versiones (--version):
  corta     15 s: la frase del juego (en Switch 2: L R X L R X) → la aprendemos lento → kick y bajo → drop.
  completa  ~34 s: el beat (kick, tarola, bajo, hats) suena desde el segundo 0: la frase de gancho → la canción completa del
            molino → un compás de respiro con subida → la repetición con clap y supersaw → final en Re con un trueno.
Todo sintetizado: ocarina (seno con aire, chiff y vibrato), lluvia y truenos de ruido filtrado, batería de techno.py y
el lead con Surge XT (por eso corre en `.venv-synth`).

La melodía es de Koji Kondo (Nintendo): es un cover/tributo, no entra a Creator Rewards (ADR-024). El arreglo en 4/4
(la original va en 3/4) es nuestro.

Uso:  .venv-synth/bin/python escenas3d/ocarina.py [--version corta|completa]
Sale: out/.tmp/beat-ocarina-tormenta[-completa]-prueba.json + .wav  →  grabar.js escenas/ocarina.html …
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# techno.py lee la línea de comandos al importarse (su propio --version): se leen los argumentos antes y se le
# deja la línea vacía
_ap = argparse.ArgumentParser()
_ap.add_argument("--version", choices=["corta", "completa"], default="corta")
ARGS = _ap.parse_args()
sys.argv = sys.argv[:1]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from surge import tocar  # noqa: E402
from techno import clap, eco, escribir_wav, filtro, hat, kick, ping_pong  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
BPM = 128
B = 60 / BPM                      # un tiempo
rng = np.random.default_rng(7)

# Notas que tienen botón en el juego (Re, Fa, Re agudo); las demás solo se marcan en los agujeros
BOTON = {62: "A", 65: "C▼", 74: "C▲"}
RE, MI, FA, SOL, LA, DO2, RE2, MI2, FA2 = 62, 64, 65, 67, 69, 72, 74, 76, 77
# La frase del juego (tiempo, nota, duración en tiempos)
FRASE = [(0, RE, 0.5), (0.5, FA, 0.5), (1, RE2, 2), (4, RE, 0.5), (4.5, FA, 0.5), (5, RE2, 2.5)]
LENTA = [(0, RE, 1), (1, FA, 1), (2, RE2, 1.8), (4, RE, 1), (5, FA, 1), (6, RE2, 1.8)]
# La canción completa del molino, pasada a 4/4 (un compás = 4 tiempos)
INICIO = [(0, RE, 0.5), (0.5, FA, 0.5), (1, RE2, 3), (4, RE, 0.5), (4.5, FA, 0.5), (5, RE2, 3),
          (8, MI2, 1.5), (9.5, FA2, 0.5), (10, MI2, 0.5), (10.5, FA2, 0.5), (11, MI2, 0.5), (11.5, DO2, 0.5),
          (12, LA, 4)]
VUELTA_1 = INICIO + [(16, LA, 1), (17, RE, 1), (18, FA, 1), (19, SOL, 1), (20, LA, 4),
                     (24, LA, 1), (25, RE, 1), (26, FA, 1), (27, SOL, 1), (28, MI, 4)]
VUELTA_2 = INICIO + [(16, LA, 1), (17, RE, 1), (18, FA, 1), (19, SOL, 1), (20, LA, 2), (22, LA, 2), (24, RE, 4)]
# Acordes por compás (raíz del bajo, notas del colchón)
DM, DO_, LAM, FA_ = (38, (50, 53, 57)), (36, (48, 52, 55)), (33, (45, 48, 52)), (41, (53, 57, 60))
ARMONIA_1 = [DM, DM, DO_, LAM, DM, FA_, DM, DO_]
ARMONIA_2 = [DM, DM, DO_, LAM, DM, LAM, DM]


def desde(b0, frase):
    return [(b0 + b, m, d) for b, m, d in frase]


TITULOS = {"titulo": "TRIBUTO A ZELDA", "juego": "Ocarina of Time", "cancion": "Song of Storms"}
VERSIONES = {
    "corta": {
        "nombre": "beat-ocarina-tormenta-prueba", "tiempos": 32,
        "secciones": [(0, 8, "gancho", TITULOS), (8, 16, "aprende", {"texto": "Tapa los agujeros *encendidos*"}),
                      (16, 24, "capa", {"capa": "+ KICK", "texto": "Ahora en *electrónico*"}),
                      (24, 32, "drop", {"texto": ""})],
        "melodia": desde(0, FRASE) + desde(8, LENTA) + desde(16, FRASE) + desde(24, FRASE),
        "kicks": [(16, 32)], "hats": [], "drop": 24, "lead": 24,
        "armonia": [(8, DM, 8), (16, DM, 8), (24, DM, 4), (28, (34, (46, 50, 53)), 4)],
        "bajo": [(16, 32)], "rayos": [0.15, 6.0], "final": None,
    },
    "completa": {
        "nombre": "beat-ocarina-tormenta-completa-prueba", "tiempos": 72,
        "secciones": [(0, 8, "gancho", TITULOS),
                      (8, 40, "capa", {"texto": ""}),
                      (40, 72, "drop", {"texto": ""})],
        "melodia": desde(0, FRASE) + desde(8, VUELTA_1) + desde(40, VUELTA_2),
        "kicks": [(0, 36), (40, 68)], "hats": [(0, 36)], "drop": 40, "lead": 40,
        "armonia": [(0, DM, 4), (4, DM, 4)] + [(8 + 4 * i, a, 4) for i, a in enumerate(ARMONIA_1)]
                   + [(40 + 4 * i, a, 4) for i, a in enumerate(ARMONIA_2)],
        "bajo": [(0, 36), (40, 68)], "rayos": [0.15, 24 * B, 32 * B], "final": 68,
    },
}


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def poner(destino, s, t, gan=1.0, lado=0.0):
    a = int(t * SR)
    if a >= len(destino) or a < 0:
        return
    n = min(len(s), len(destino) - a)
    destino[a:a + n, 0] += s[:n] * gan * np.sqrt((1 - lado) / 2)
    destino[a:a + n, 1] += s[:n] * gan * np.sqrt((1 + lado) / 2)


# ------------------------------------------------------------------ partitura
def notas(v):
    lista = []
    for b, m, d in sorted(v["melodia"]):
        n = {"t": round(b * B, 4), "midi": m, "dur": round(d * B, 4)}
        if m in BOTON:
            n["boton"] = BOTON[m]
        lista.append(n)
    return lista


def en(rangos):
    return [i for a, b in rangos for i in range(a, b)]


def kicks(v):
    return [round(i * B, 4) for i in en(v["kicks"])]


def rayos(v):
    r = list(v["rayos"]) + [round(i * B, 4) for i in range(v["drop"], v["kicks"][-1][1], 2)]
    if v["final"]:
        r.append(round(v["final"] * B, 4))
    return sorted(r)


# ------------------------------------------------------------------ síntesis
def ocarina(m, dur):
    """Ocarina: seno casi puro con un poco de 2º y 3º armónico, aire filtrado alrededor de la nota, el "chiff" del
    soplido al empezar y un vibrato que entra tarde."""
    t = np.arange(int((dur + 0.4) * SR)) / SR
    f = hz(m + 12)
    vib = 1 + 0.0045 * np.sin(2 * np.pi * 5.3 * t) * np.clip((t - 0.15) / 0.25, 0, 1)
    fase = 2 * np.pi * np.cumsum(f * vib) / SR
    s = np.sin(fase) + 0.1 * np.sin(2 * fase) + 0.035 * np.sin(3 * fase)
    aire = filtro(rng.normal(0, 1, len(t)), f * 0.85, f * 1.25) * 0.09
    chiff = filtro(rng.normal(0, 1, len(t)), 2500, 9000) * np.exp(-t * 55) * 0.18
    env = np.minimum(1, t / 0.035) * np.where(t < dur, 1.0, np.exp(-(t - dur) * 16))
    return (s * 0.8 + aire) * env + chiff * np.minimum(1, t / 0.002)


def nota_bajo(m, dur):
    """Bajo de house en contratiempo: sierra filtrada con un "tuc" de filtro al inicio."""
    t = np.arange(int(dur * SR)) / SR
    f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 30) if f * k < 8000)
    s = filtro(s, 30, 380) + filtro(s, 30, 1400) * np.exp(-t * 30) * 0.6
    env = np.minimum(1, t / 0.004) * np.clip((dur - t) / 0.02, 0, 1)
    return np.tanh(1.5 * s) * env


def pad(acorde, dur):
    """Colchón suave: sierras desafinadas muy filtradas, entra despacio."""
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for m in acorde:
        for d in (-0.08, 0.08):
            f = hz(m + d)
            s += sum(np.sin(2 * np.pi * f * k * t + k * d) / k for k in range(1, 12) if f * k < 5000)
    s = filtro(s, 80, 1100)
    return s * np.minimum(1, t / 0.5) * np.clip((dur - t) / 0.4, 0, 1) / len(acorde)


def trueno(lejos=True):
    """Retumbo grave que crece y se va apagando; con chasquido arriba si es cercano."""
    t = np.arange(int(3.5 * SR)) / SR
    retumbo = filtro(rng.normal(0, 1, len(t)), 25, 180 if lejos else 320)
    retumbo *= np.minimum(1, t / 0.12) * np.exp(-t * 1.3) * (1 + 0.5 * np.sin(2 * np.pi * 3.1 * t))
    chasquido = filtro(rng.normal(0, 1, len(t)), 1200, 9000) * np.exp(-t * 18) * (0.15 if lejos else 0.5)
    return retumbo * 1.6 + chasquido


def lluvia(n):
    """Lluvia continua: ruido ancho y suave, más gotitas sueltas."""
    x = np.zeros((n, 2))
    for c in (0, 1):
        x[:, c] = filtro(rng.normal(0, 1, n), 700, 9000) * 0.05 + filtro(rng.normal(0, 1, n), 120, 600) * 0.03
    t = np.arange(int(0.02 * SR)) / SR
    for _ in range(int(n / SR * 18)):
        gota = filtro(rng.normal(0, 1, len(t)), 3000, 12000) * np.exp(-t * 300)
        poner(x, gota, rng.uniform(0, n / SR), rng.uniform(0.02, 0.07), rng.uniform(-0.9, 0.9))
    return x


def subida(n, t_drop):
    """Ruido que sube en el compás antes del drop, y el platillo al caer."""
    x = np.zeros((n, 2))
    dur = 4 * B
    t = np.arange(int(dur * SR)) / SR
    partes = np.array_split(rng.normal(0, 1, len(t)), 24)
    ruido = np.concatenate([filtro(p, 400 + 7000 * (i / 23) ** 2, 2000 + 10000 * (i / 23) ** 2)
                            for i, p in enumerate(partes)]) * (t / t[-1]) ** 2
    poner(x, ruido, t_drop - dur, 0.3)
    t = np.arange(int(2.0 * SR)) / SR
    platillo = filtro(rng.normal(0, 1, len(t)), 3000, 14000) * np.exp(-t * 2.4)
    poner(x, platillo, t_drop, 0.25, -0.4)
    poner(x, platillo, t_drop + 0.01, 0.18, 0.6)
    return x


def sonido(v, lista_notas, total):
    n = int(total * SR)
    t_drop = v["drop"] * B
    oca = np.zeros(n)
    for nota in lista_notas:
        s = ocarina(nota["midi"], nota["dur"])
        a = int(nota["t"] * SR)
        m = min(len(s), n - a)
        oca[a:a + m] += s[:m]
    oca = eco(oca, segundos=2.4, mezcla=0.32, caida=2.2)
    ocarinas = np.stack([oca, oca], axis=1)

    bat = np.zeros((n, 2))
    graves = np.zeros((n, 2))
    lista_kicks = kicks(v)
    for k in lista_kicks:
        poner(bat, kick(), k, 0.9 if k >= t_drop - 0.01 else 0.62)   # antes del drop más ligero: el drop pega más
    for i in en(v["hats"]):                    # antes del drop: solo hat en contratiempo, más bajito
        poner(bat, hat(1.0), (i + 0.5) * B, 0.35, 0.3)
    for i in en(v["kicks"]):                   # tarola (clap) en 2 y 4 desde que entra el kick
        if i % 2 == 1:
            poner(bat, clap(), i * B, 0.45 if i >= v["drop"] else 0.3)
    for i in range(v["drop"], v["kicks"][-1][1]):
        poner(bat, hat(1.0), (i + 0.5) * B, 0.5, 0.3)
        poner(bat, hat(0.6), (i + 0.25) * B, 0.25, -0.3)
        poner(bat, hat(0.6), (i + 0.75) * B, 0.25, -0.3)

    colchon = np.zeros((n, 2))
    bajo = set(en(v["bajo"]))
    for b0, (raiz, acorde), dur in v["armonia"]:
        poner(colchon, pad(acorde, dur * B + 0.3), b0 * B, 0.35, -0.2)
        poner(colchon, pad(acorde, dur * B + 0.3), b0 * B + 0.012, 0.35, 0.2)
        for i in range(b0, b0 + dur):
            if i in bajo:
                poner(graves, nota_bajo(raiz, B * 0.45), (i + 0.5) * B, 0.55 if i >= v["drop"] else 0.36)

    # Lead del drop: supersaw de Surge XT doblando a la ocarina, con eco de ida y vuelta
    lead_notas = [(x["t"], x["midi"] + 12, 100, x["dur"] * 0.95) for x in lista_notas if x["t"] >= v["lead"] * B - 0.01]
    lead = ping_pong(tocar(lead_notas, "Super", n, gan_db=-8), B * 0.75, 0.35)

    # Bombeo (sidechain) del kick sobre todo lo que no es batería
    t = np.arange(n) / SR
    bombeo = np.ones(n)
    for k in lista_kicks:
        a = int(k * SR)
        bombeo[a:] = np.minimum(bombeo[a:], 1 - 0.65 * np.exp(-(t[a:] - k) * 9))
    bombeo = bombeo[:, None]

    ambiente = lluvia(n)
    for r in rayos(v):
        cerca = r >= t_drop
        poner(ambiente, trueno(lejos=not cerca), r + (0.05 if cerca else 0.25), 0.25 if cerca else 0.5)
    if v["final"]:
        poner(ambiente, trueno(lejos=False), v["final"] * B, 0.6)

    mezcla = (ocarinas * 0.55 + bat + (graves * 0.9 + colchon + lead * 0.8) * bombeo
              + ambiente * np.where(t < t_drop, 1.0, 0.6)[:, None] + subida(n, t_drop))
    mezcla = np.tanh(mezcla * 1.1) / 1.1
    fade = int(0.8 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return mezcla / np.max(np.abs(mezcla)) * 0.89


def main():
    v = VERSIONES[ARGS.version]
    total = round(v["tiempos"] * B, 4)
    lista = notas(v)
    secciones = [{"t0": round(b0 * B, 4), "t1": round(b1 * B, 4), "toma": toma, **txt}
                 for b0, b1, toma, txt in v["secciones"]]
    datos = {"bpm": BPM, "total": total, "notas": lista, "kicks": kicks(v), "rayos": rayos(v), "secciones": secciones}
    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    nombre = v["nombre"]
    (tmp / f"{nombre}.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    escribir_wav(tmp / f"{nombre}.wav", sonido(v, lista, total))
    print(f"Listo: out/.tmp/{nombre}.json y .wav ({total} s, {len(lista)} notas)")


if __name__ == "__main__":
    main()
