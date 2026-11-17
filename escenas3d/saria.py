"""Neon Keys · Tributo a Zelda: Ocarina of Time, "Saria's Song" (Lost Woods) en electrónico (escena escenas/saria.html).

Versión prueba (~37 s): la frase del juego sola con el bosque (F A B, F A B; en Switch 2: R A Y R A Y) → la parte A
completa con beat y un arpegio que gira (hipnótico) → un compás de respiro con subida → la parte A otra vez con
supersaw, clap y hats → final largo en Mi con un brillo de hadas.
Versión larga (~83 s): frase sola → parte A con beat → parte B ("Re Mi Fa, Sol La Si, Do Si Mi…") con respiro y
subida al final → drop con la parte A → clímax con la parte B completa (incluye la escalera que sube hasta Fa↑) →
final en Mi.
Versión corta (~45 s, la recomendada: el largo se puede hacer aburrido): frase sola → parte A con beat → la mitad de
la parte B que sube hasta Mi↑ (respiro con subida) → drop con la escalera de la parte B → final en Mi.
Todo sintetizado: la ocarina, el bajo y el colchón salen de ocarina.py; el ambiente es de bosque de noche (grillos,
viento, campanitas de hada) en vez de lluvia y truenos.

La melodía es de Koji Kondo (Nintendo): es un cover/tributo, no entra a Creator Rewards (ADR-024). El arreglo es nuestro.

Uso:  .venv-synth/bin/python escenas3d/saria.py [--version prueba|corta|larga]
Sale: out/.tmp/beat-ocarina-saria-prueba.json + .wav (o beat-ocarina-saria-corto.* / -largo.*)  →  grabar.js escenas/saria.html …
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# techno.py y ocarina.py leen la línea de comandos al importarse: se leen los argumentos antes y se les deja vacía
_ap = argparse.ArgumentParser()
_ap.add_argument("--version", choices=["prueba", "corta", "larga"], default="prueba")
ARGS = _ap.parse_args()
sys.argv = sys.argv[:1]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocarina import en, hz, nota_bajo, ocarina, pad, poner, subida  # noqa: E402
from surge import tocar  # noqa: E402
from techno import clap, eco, escribir_wav, filtro, hat, kick, ping_pong  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SR = 44100
BPM = 124
B = 60 / BPM
rng = np.random.default_rng(11)

# Notas con botón en el juego (N64 → Switch 2 en saria.html). Saria's Song = C▼ C▶ C◀ (Fa La Si)
BOTON = {62: "A", 65: "C▼", 69: "C▶", 71: "C◀", 74: "C▲"}
RE, MI, FA, SOL, LA, SI, DO2, RE2, MI2, FA2 = 62, 64, 65, 67, 69, 71, 72, 74, 76, 77
FRASE = [(0, FA, 0.5), (0.5, LA, 0.5), (1, SI, 1.5), (4, FA, 0.5), (4.5, LA, 0.5), (5, SI, 2.5)]
# Parte A (8 compases de 4/4): "Fa La Si, Fa La Si, Fa La Si Mi Re, Si Do Si Sol Mi…"
PARTE_A = [
    (0, FA, .5), (.5, LA, .5), (1, SI, 1), (2, FA, .5), (2.5, LA, .5), (3, SI, 1),
    (4, FA, .5), (4.5, LA, .5), (5, SI, .5), (5.5, MI2, .5), (6, RE2, 1), (7, SI, .5), (7.5, DO2, .5),
    (8, SI, .5), (8.5, SOL, .5), (9, MI, 2.5), (11.5, 62, .5), (12, MI, .5), (12.5, SOL, .5), (13, MI, 3),
    (16, FA, .5), (16.5, LA, .5), (17, SI, 1), (18, FA, .5), (18.5, LA, .5), (19, SI, 1),
    (20, FA, .5), (20.5, LA, .5), (21, SI, .5), (21.5, MI2, .5), (22, RE2, 1), (23, SI, .5), (23.5, DO2, .5),
    (24, MI2, .5), (24.5, SI, .5), (25, SOL, 2.5), (27.5, SI, .5), (28, SOL, .5), (28.5, 62, .5), (29, MI, 3),
]
# Parte B, primera mitad (8 compases): "Re Mi Fa, Sol La Si, Do Si Mi…" dos veces, la segunda sube hasta Mi↑
PARTE_B1 = [
    (0, RE, .5), (.5, MI, .5), (1, FA, 3), (4, SOL, .5), (4.5, LA, .5), (5, SI, 3), (8, DO2, .5), (8.5, SI, .5), (9, MI, 7),
    (16, RE, .5), (16.5, MI, .5), (17, FA, 3), (20, SOL, .5), (20.5, LA, .5), (21, SI, 3),
    (24, DO2, .5), (24.5, RE2, .5), (25, MI2, 7),
]
# Parte B, segunda mitad (8 compases): la escalera que sube de tres en tres hasta Fa↑ y baja a Mi
PARTE_B2 = [(4 * c + 2 * j + d, m, dur) for c, base in enumerate([(RE, MI, FA, SOL), (FA, SOL, LA, SI),
                                                                   (LA, SI, DO2, RE2), (DO2, RE2, MI2, FA2)])
            for j in (0, 1) for d, m, dur in ((0, base[j], .5), (.5, base[j + 1], .5), (1, base[j + 2], 1))]
PARTE_B2 += [(16, MI2, 4), (20, RE2, .5), (20.5, DO2, .5), (21, SI, 1), (22, LA, 2),
             (24, SOL, .5), (24.5, LA, .5), (25, SI, 1), (26, SOL, 2), (28, MI, 4)]
# Acordes por compás (raíz del bajo, notas del colchón): Fa lidio → Fa, Sol, Mim, Lam (+ Rem y Do en la parte B)
FA_, SOL_, MIM, LAM = (41, (53, 57, 60, 64)), (43, (55, 59, 62)), (40, (52, 55, 59)), (45, (57, 60, 64))
REM, DO_ = (38, (53, 57, 62)), (36, (55, 60, 64))
ARMONIA_A = [FA_, SOL_, MIM, LAM, FA_, SOL_, MIM, LAM]
ARMONIA_B1 = [REM, SOL_, DO_, MIM, REM, SOL_, DO_, MIM]
ARMONIA_B2 = [REM, FA_, LAM, DO_, MIM, FA_, SOL_, MIM]


def tramo(b0, partes):
    """Pone partes (melodía, armonía) una tras otra desde el tiempo b0: (notas, acordes) en tiempos absolutos."""
    mel, arm = [], []
    for notas_, acordes in partes:
        mel += [(b0 + b, m, d) for b, m, d in notas_]
        arm += [(b0 + 4 * i, a, 4) for i, a in enumerate(acordes)]
        b0 += 4 * len(acordes)
    return mel, arm

TITULOS = {"titulo": "TRIBUTO A ZELDA", "juego": "Ocarina of Time", "cancion": "Saria's Song"}
A, B1, B2 = (PARTE_A, ARMONIA_A), (PARTE_B1, ARMONIA_B1), (PARTE_B2, ARMONIA_B2)
_mel, _arm = tramo(8, [A, B1, A, B1, B2])
LARGA = {
    "nombre": "beat-ocarina-saria-largo", "tiempos": 172,
    "secciones": [(0, 8, "gancho", TITULOS), (8, 40, "capa", {"texto": ""}), (40, 72, "bosque", {"texto": ""}),
                  (72, 104, "drop", {"texto": ""}), (104, 172, "climax", {"texto": ""})],
    "melodia": FRASE + _mel,
    # el último compás de la primera parte B (Mi↑ largo) va sin batería: el respiro con la subida
    "kicks": [(8, 68), (72, 168)], "drop": 72, "final": 168, "entradas": [40, 104],
    "armonia": [(0, FA_, 4), (4, SOL_, 4)] + _arm + [(168, MIM, 4)],
}
# Corta: la segunda vuelta de "Re Mi Fa, Sol La Si" (la que sube a Mi↑) y luego directo a la escalera
B1_MITAD = ([(b - 16, m, d) for b, m, d in PARTE_B1 if b >= 16], ARMONIA_B1[4:])
_mel_c, _arm_c = tramo(8, [A, B1_MITAD, B2])
CORTA = {
    "nombre": "beat-ocarina-saria-corto", "tiempos": 92,
    "secciones": [(0, 8, "gancho", TITULOS), (8, 40, "capa", {"texto": ""}), (40, 56, "bosque", {"texto": ""}),
                  (56, 72, "drop", {"texto": ""}), (72, 92, "climax", {"texto": ""})],
    "melodia": FRASE + _mel_c,
    "kicks": [(8, 52), (56, 88)], "drop": 56, "final": 88, "entradas": [40],
    "armonia": [(0, FA_, 4), (4, SOL_, 4)] + _arm_c + [(88, MIM, 4)],
}
PRUEBA = {
    "nombre": "beat-ocarina-saria-prueba", "tiempos": 76,
    "secciones": [(0, 8, "gancho", TITULOS), (8, 40, "capa", {"texto": ""}), (40, 76, "drop", {"texto": ""})],
    "melodia": [(b, m, d) for b, m, d in FRASE] + [(8 + b, m, d) for b, m, d in PARTE_A]
               + [(40 + b, m, d) for b, m, d in PARTE_A],
    "kicks": [(8, 36), (40, 72)], "drop": 40, "final": 72,
    "armonia": [(0, FA_, 4), (4, SOL_, 4)] + [(8 + 4 * i, a, 4) for i, a in enumerate(ARMONIA_A)]
               + [(40 + 4 * i, a, 4) for i, a in enumerate(ARMONIA_A)] + [(72, MIM, 4)],
}
V = {"prueba": PRUEBA, "corta": CORTA, "larga": LARGA}[ARGS.version]


# ------------------------------------------------------------------ partitura
def notas():
    lista = []
    for b, m, d in sorted(V["melodia"]):
        n = {"t": round(b * B, 4), "midi": m, "dur": round(d * B, 4)}
        if m in BOTON:
            n["boton"] = BOTON[m]
        lista.append(n)
    return lista


def kicks():
    return [round(i * B, 4) for i in en(V["kicks"])]


def pulsos():
    """Destellos del bosque (la escena los usa como los relámpagos de la tormenta): al entrar el beat, al empezar la
    parte B, en cada compás del drop y en el final."""
    r = [round(b * B, 4) for b in [8] + V.get("entradas", [])]
    r += [round(i * B, 4) for i in range(V["drop"], V["kicks"][-1][1], 4)]
    return sorted(set(r + [round(V["final"] * B, 4)]))


# ------------------------------------------------------------------ síntesis
def campanita(m, dur=1.6):
    """Campanita de hada: seno con un parcial inarmónico, ataque de vidrio y cola larga."""
    t = np.arange(int(dur * SR)) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
    s += 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 14)
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 3.2)


def pluck(m, dur):
    """Arpegio que gira (estilo kalimba/marimba de vidrio): seno + octava, ataque corto."""
    t = np.arange(int(dur * SR)) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 18)
    s += filtro(rng.normal(0, 1, len(t)), 2000, 7000) * np.exp(-t * 200) * 0.2
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 7)


def bosque(n):
    """Noche en el bosque: viento suave que respira, grillos y algún pajarito lejano."""
    x = np.zeros((n, 2))
    t = np.arange(n) / SR
    for c in (0, 1):
        viento = filtro(rng.normal(0, 1, n), 150, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * t / 7.3 + c))
        x[:, c] += viento * 0.035
    # grillos: chirridos de 4.6 kHz en trenes de 3
    tc = np.arange(int(0.012 * SR)) / SR
    chirp = np.sin(2 * np.pi * 4600 * tc) * np.sin(np.pi * tc / tc[-1])
    for lado in (-0.7, 0.6):
        k = rng.uniform(0, 0.4)
        while k < n / SR:
            for j in range(3):
                poner(x, chirp, k + j * 0.018, 0.04, lado)
            k += rng.uniform(0.32, 0.5)
    # búho/pajarito lejano
    for k in np.arange(3.0, n / SR, 9.0):
        tb = np.arange(int(0.35 * SR)) / SR
        silbo = np.sin(2 * np.pi * (1300 + 300 * np.sin(np.pi * tb / tb[-1])) * tb) * np.sin(np.pi * tb / tb[-1])
        poner(x, filtro(silbo, 400, 3000), k + rng.uniform(0, 2), 0.03, rng.uniform(-0.8, 0.8))
    return x


def brillo(n, t0, subiendo=True):
    """Barrido de campanitas de hada (sube por la escala de Fa lidio) que abre una sección."""
    x = np.zeros((n, 2))
    escala = [77, 79, 81, 83, 84, 86, 88, 89, 91, 93]
    orden = escala if subiendo else escala[::-1]
    for i, m in enumerate(orden):
        poner(x, campanita(m), t0 + i * 0.045, 0.16, -0.8 + 1.6 * i / (len(orden) - 1))
    return x


def sonido(lista_notas, total):
    n = int(total * SR)
    t_drop = V["drop"] * B
    oca = np.zeros(n)
    for nota in lista_notas:
        s = ocarina(nota["midi"], nota["dur"])
        a = int(nota["t"] * SR)
        m = min(len(s), n - a)
        oca[a:a + m] += s[:m]
    oca = eco(oca, segundos=2.8, mezcla=0.36, caida=1.9)
    ocarinas = np.stack([oca, oca], axis=1)

    bat = np.zeros((n, 2))
    lista_kicks = kicks()
    for k in lista_kicks:
        poner(bat, kick(), k, 0.85 if k >= t_drop - 0.01 else 0.55)
    for i in en(V["kicks"]):
        if i % 2 == 1:
            poner(bat, clap(), i * B, 0.42 if i >= V["drop"] else 0.22)
        poner(bat, hat(1.0), (i + 0.5) * B, 0.45 if i >= V["drop"] else 0.3, 0.3)
        if i >= V["drop"]:
            poner(bat, hat(0.6), (i + 0.25) * B, 0.22, -0.3)
            poner(bat, hat(0.6), (i + 0.75) * B, 0.22, -0.3)
            if i % 4 == 3:
                poner(bat, hat(1.0, abierto=True), (i + 0.5) * B, 0.3, 0.2)

    colchon = np.zeros((n, 2))
    graves = np.zeros((n, 2))
    arpegio = np.zeros((n, 2))
    bajo = set(en(V["kicks"]))
    for b0, (raiz, acorde), dur in V["armonia"]:
        poner(colchon, pad(acorde, dur * B + 0.3), b0 * B, 0.35, -0.2)
        poner(colchon, pad(acorde, dur * B + 0.3), b0 * B + 0.012, 0.35, 0.2)
        # arpegio en semicorcheas, sube y baja por el acorde una octava arriba: el "giro" hipnótico, desde el segundo 0
        tonos = [m + 12 for m in acorde]
        figura = tonos + tonos[-2:0:-1]
        for j in range(dur * 4):
            m = figura[j % len(figura)]
            g = 0.13 if b0 < V["drop"] else 0.11
            poner(arpegio, pluck(m, 0.5), b0 * B + j * B / 4, g, 0.6 * np.sin(j * 0.7))
        for i in range(b0, b0 + dur):
            if i in bajo:
                poner(graves, nota_bajo(raiz, B * 0.45), (i + 0.5) * B, 0.55 if i >= V["drop"] else 0.36)
    arpegio = ping_pong(arpegio, B * 0.75, 0.3, 5)

    # Lead del drop: supersaw de Surge XT doblando a la ocarina una octava arriba
    lead_notas = [(x["t"], x["midi"] + 12, 96, x["dur"] * 0.95) for x in lista_notas if x["t"] >= t_drop - 0.01]
    lead = ping_pong(tocar(lead_notas, "Super", n, gan_db=-10), B * 0.75, 0.35)

    t = np.arange(n) / SR
    bombeo = np.ones(n)
    for k in lista_kicks:
        a = int(k * SR)
        bombeo[a:] = np.minimum(bombeo[a:], 1 - 0.6 * np.exp(-(t[a:] - k) * 9))
    bombeo = bombeo[:, None]

    magia = brillo(n, 8 * B - 0.5) + brillo(n, t_drop - 0.45) + brillo(n, V["final"] * B, subiendo=False)
    for b in V.get("entradas", []):
        magia += brillo(n, b * B - 0.45)
    # el compás antes del drop: sin batería, solo la subida (el respiro)
    mezcla = (ocarinas * 0.55 + bat + (graves * 0.9 + colchon + lead * 0.75 + arpegio) * bombeo
              + bosque(n) * np.where(t < t_drop, 1.0, 0.55)[:, None] + magia + subida(n, t_drop) * 0.8)
    mezcla = np.tanh(mezcla * 1.1) / 1.1
    fade = int(1.2 * SR)
    mezcla[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return mezcla / np.max(np.abs(mezcla)) * 0.89


def main():
    total = round(V["tiempos"] * B, 4)
    lista = notas()
    secciones = [{"t0": round(b0 * B, 4), "t1": round(b1 * B, 4), "toma": toma, **txt}
                 for b0, b1, toma, txt in V["secciones"]]
    datos = {"bpm": BPM, "total": total, "notas": lista, "kicks": kicks(), "pulsos": pulsos(), "secciones": secciones}
    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    nombre = V["nombre"]
    (tmp / f"{nombre}.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    escribir_wav(tmp / f"{nombre}.wav", sonido(lista, total))
    print(f"Listo: out/.tmp/{nombre}.json y .wav ({total} s, {len(lista)} notas)")


if __name__ == "__main__":
    main()
