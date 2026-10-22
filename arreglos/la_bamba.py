#!/usr/bin/env python3
"""Arreglo propio de "La Bamba" (son jarocho tradicional, dominio público) para Neon Keys.

Escribe midi/la-bamba.mid. Mano derecha = pista 1 (cian), mano izquierda = pista 2 (magenta).
La melodía es la tradicional; intro, acompañamiento, sección rápida y final son originales.

Estructura (en tiempos, ciclo de 8 tiempos: Do 2 · Fa 1.5 · Sol 4.5):
    0–16    intro con el riff en corcheas
    16–96   melodía cantada (desde el tiempo 52, doblada a la octava)
    96–136  sección rápida: riff en semicorcheas, sube de octava al final
    136–152 remate con la melodía en octavas
    152     glissando y acorde final

Uso:
    .venv/bin/python arreglos/la_bamba.py
"""

from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "midi" / "la-bamba.mid"

TOTAL_SECONDS = 63.26     # 70 s de video − 6.74 s de entrada y cierre (ver CLAUDE.md)
TOTAL_BEATS = 155
BPM = TOTAL_BEATS * 60 / TOTAL_SECONDS   # ≈ 147
TPB = 480

NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Melodía tradicional (tiempo, duración, nota); "Para bailar la bamba…"
MELODY = """
16.5:F5/.5 17:F5/.5 17.5:F5/.5 18:F5/1 19:F5/.5 19.5:E5/1 20.5:C5/1.5
24.5:F5/.5 25:F5/.5 25.5:F5/.5 26:F5/1 27:F5/.5 27.5:E5/1 28.5:C5/1
29.5:C5/.5 30:C5/.5 30.5:C5/1 31.5:D5/1 32.5:B4/1 33.5:D5/.5 34:F5/1 35:E5/.5 35.5:D5/.5 36:E5/1 37:C5/1
40.667:F5/.667 41.333:F5/.667 42:F5/.667 42.667:F5/.667 43.333:F5/.667 44:E5/1
45:C5/.5 45.5:C5/.5 46:C5/.5 46.5:C5/1 47.5:D5/1 48.5:B4/1 49.5:D5/.5 50:F5/.5 50.5:E5/.5 51:D5/.5 51.5:E5/.5 52:C5/1
56.667:F5/.667 57.333:F5/.667 58:F5/.667 58.667:F5/.667 59.333:F5/.667 60:E5/.667
60.667:C5/.667 61.333:C5/.667 62:C5/.5 62.5:C5/1 63.5:D5/1.5 65:B4/1 66:D5/1 67:F5/.5 67.5:E5/1.5
69:E5/1 70:C5/.5 70.5:A4/.5 71:A4/.5 71.5:G4/.5
72.667:F5/.667 73.333:F5/.667 74:F5/.667 74.667:F5/.667 75.333:F5/.667 76:E5/.5 76.5:C5/1.5
80.5:F5/1 81.5:F5/.5 82:F5/.667 82.667:F5/.667 83.333:F5/.667 84:E5/.5 84.5:C5/.5
85.5:C5/.5 86:C5/.667 86.667:C5/.667 87.333:D5/1.667 89:B4/1 90:D5/1 91:F5/.5 91.5:D5/.5
92:E5/1 93:E5/1 94:C5/.5 94.5:A4/.5 95:A4/.5 95.5:G4/1.5
"""
MELODY_SHIFT = -4   # en la fuente el ciclo empieza en el tiempo 4; aquí en el 0

# Remate tradicional (se toca en octavas).
TAG = """
108:E5/2 110:C5/1.5 111.5:D5/1 112.5:D5/1
116:E5/2 118:C5/1.5 119.5:D5/1 120.5:D5/1 123:B4/.25 123.25:B4/.75
"""
TAG_SHIFT = 28

# Acordes del ciclo: (inicio dentro del ciclo, duración, raíz, notas del acorde en octava 3/4)
CYCLE = [
    (0.0, 2.0, "C2", ["E3", "G3", "C4"]),
    (2.0, 1.5, "F2", ["F3", "A3", "C4"]),
    (3.5, 4.5, "G2", ["G3", "B3", "D4"]),
]
ARP = {"C": ["C", "E", "G"], "F": ["F", "A", "C"], "G": ["G", "B", "D", "F"]}


def midi_note(name):
    return 12 * (int(name[-1]) + 1) + NAMES[name[0]] + (1 if "#" in name else 0)


def parse(block, shift):
    out = []
    for tok in block.split():
        t, rest = tok.split(":")
        n, d = rest.split("/")
        out.append((float(t) + shift, float(d), midi_note(n)))
    return out


class Part:
    def __init__(self):
        self.notes = []  # (inicio, duración, nota, velocidad)

    def add(self, start, dur, note, vel):
        self.notes.append((start, dur, note, max(1, min(127, int(vel)))))

    def chord(self, start, dur, notes, vel):
        for n in notes:
            self.add(start, dur, midi_note(n) if isinstance(n, str) else n, vel)

    def to_track(self, name, channel):
        events = []
        for s, d, n, v in self.notes:
            events.append((round(s * TPB), 1, n, v))
            events.append((round((s + d * 0.92) * TPB), 0, n, 0))
        events.sort(key=lambda e: (e[0], e[1]))  # note_off antes que note_on en el mismo tick
        track = mido.MidiTrack([mido.MetaMessage("track_name", name=name, time=0)])
        last = 0
        for tick, kind, n, v in events:
            msg = "note_on" if kind else "note_off"
            track.append(mido.Message(msg, channel=channel, note=n, velocity=v, time=tick - last))
            last = tick
        return track


def arpeggio(root_letter, octave, count, up_octaves=1):
    """Notas de arpegio subiendo y bajando sobre el acorde."""
    letters = ARP[root_letter]
    base = []
    for o in range(octave, octave + up_octaves + 1):
        for L in letters:
            base.append(12 * (o + 1) + NAMES[L])
    low = 12 * (octave + 1) + NAMES[root_letter]
    base = sorted(set(n for n in base if low <= n <= low + 12 * up_octaves))
    path = base + base[-2:0:-1]
    return [path[i % len(path)] for i in range(count)]


def son_accompaniment(lh, cycle_start, vel, bass_eighths=False):
    """Mano izquierda estilo son: bajo en el tiempo fuerte y acorde en los contratiempos."""
    for off, dur, root, chord in CYCLE:
        s = cycle_start + off
        steps = int(dur * 2)
        root_n = midi_note(root)
        for i in range(steps):
            t = s + i * 0.5
            if i % 2 == 0:
                if bass_eighths:
                    lh.add(t, 0.5, root_n, vel + 10)
                    lh.add(t, 0.5, root_n + 12, vel)
                else:
                    lh.add(t, 1.0 if i + 1 < steps else 0.5, root_n, vel + 8)
            else:
                lh.chord(t, 0.45, chord, vel - 8)
                if bass_eighths:
                    lh.add(t, 0.5, root_n + 7, vel - 4)


def riff(rh, cycle_start, vel, sixteenths=False, octave=4):
    """El riff de La Bamba: arpegios Do–Fa–Sol."""
    step = 0.25 if sixteenths else 0.5
    for off, dur, root, _ in CYCLE:
        count = int(round(dur / step))
        notes = arpeggio(root[0], octave, count, up_octaves=2 if sixteenths else 1)
        for i, n in enumerate(notes):
            accent = 12 if i == 0 else 0
            rh.add(cycle_start + off + i * step, step, n, vel + accent)


def main():
    rh, lh = Part(), Part()

    # Intro: riff en corcheas, el segundo ciclo más fuerte.
    for c, start in enumerate((0, 8)):
        riff(rh, start, 78 + 10 * c)
        son_accompaniment(lh, start, 62 + 6 * c)

    # Melodía cantada.
    melody = parse(MELODY, MELODY_SHIFT)
    for s, d, n in melody:
        rh.add(s, d, n, 100)
        if s >= 52:  # segunda mitad: octava abajo para engrosar
            rh.add(s, d, n - 12, 78)
    for start in range(16, 96, 8):
        son_accompaniment(lh, start, 64 if start < 52 else 72)

    # Sección rápida (el clímax): riff en semicorcheas, sube de octava en los dos últimos ciclos.
    for c, start in enumerate(range(96, 136, 8)):
        riff(rh, start, 88 + 4 * c, sixteenths=True, octave=4 if c < 3 else 5)
        son_accompaniment(lh, start, 80 + 3 * c, bass_eighths=True)

    # Remate en octavas con acordes marcados.
    for s, d, n in parse(TAG, TAG_SHIFT):
        rh.add(s, d, n, 108)
        rh.add(s, d, n + 12, 98)
    for start in (136, 144):
        son_accompaniment(lh, start, 84, bass_eighths=True)

    # Glissando de Do5 a Do7 y acorde final.
    gl = [n for n in range(midi_note("C5"), midi_note("C7") + 1) if n % 12 in (0, 2, 4, 5, 7, 9, 11)]
    for i, n in enumerate(gl):
        rh.add(151 + i * (0.9 / len(gl)), 0.12, n, 85 + i * 2)
    rh.chord(152, 3, ["C5", "E5", "G5", "C6", "E6", "G6", "C7"], 118)
    lh.chord(152, 3, ["C2", "G2", "C3", "E3", "G3"], 116)

    mid = mido.MidiFile(ticks_per_beat=TPB)
    meta = mido.MidiTrack([
        mido.MetaMessage("track_name", name="La Bamba - Neon Keys", time=0),
        mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0),
        mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0),
    ])
    mid.tracks += [meta, rh.to_track("mano derecha", 0), lh.to_track("mano izquierda", 1)]
    OUT.parent.mkdir(exist_ok=True)
    mid.save(OUT)
    print(f"{OUT}  ({BPM:.0f} bpm, {mid.length:.1f} s)")


if __name__ == "__main__":
    main()
