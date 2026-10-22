#!/usr/bin/env python3
"""Arreglo propio de "El Son de la Negra" (son jalisciense tradicional, dominio público) para Neon Keys.

Escribe midi/son-de-la-negra.mid. Mano derecha = pista 1 (cian), mano izquierda = pista 2 (magenta).
Las melodías son las tradicionales (violines y trompetas del mariachi); el acomodo para piano, los
trémolos, el acompañamiento y el final en octavas son propios. Tonalidad: Sol mayor.

La unidad de tiempo es la corchea. El acompañamiento alterna compases de 6/8 y 3/4 (sesquiáltera),
como el guitarrón y la vihuela.

Estructura (en corcheas):
      0–50   intro: "si la si do re" + trémolo en Re, trémolo en Fa#, golpes en hemiola
     50–110  "si la si do re" y respuesta "do re do re la fa#"
    110–164  melodía de violines
    164–212  segunda parte ("mi re do si…"), la segunda vez en octavas
    212–260  trompetas: trémolo en Sol, subida cromática y escalas (clímax)
    260–338  final 1: arpegios rápidos, "sol re do re" y los golpes de seis
    338–372  final 2: arpegios que bajan en secuencia y remate "re fa# la sol… sol"

Uso:
    .venv/bin/python arreglos/son_de_la_negra.py
"""

from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "midi" / "son-de-la-negra.mid"

TOTAL_SECONDS = 63.26     # 70 s de video − 6.74 s de entrada y cierre (ver CLAUDE.md)
TOTAL_UNITS = 372         # corcheas
BPM = TOTAL_UNITS * 60 / TOTAL_SECONDS   # una "negra" del MIDI = una corchea del arreglo (≈ 0.17 s)
TPB = 480

NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Acordes: (bajo del guitarrón, acorde de la vihuela)
CHORDS = {
    "G": (43, ["D3", "G3", "B3"]),
    "C": (36, ["E3", "G3", "C4"]),
    "D7": (38, ["F#3", "A3", "C4"]),
    "A7": (45, ["E3", "G3", "C#4"]),
    "B7": (47, ["D#3", "A3", "B3"]),
    "Bm": (47, ["D3", "F#3", "B3"]),
    "Am": (45, ["E3", "A3", "C4"]),
}

# Patrones del acompañamiento: (posición, tipo, duración); b = bajo, q = quinta, c = acorde
PATTERN_68 = [(0, "b", 1), (1, "c", 1), (2, "c", 1), (3, "q", 1), (4, "c", 1), (5, "c", 1)]
PATTERN_34 = [(0, "b", 2), (2, "c", 2), (4, "c", 2)]
BAR0 = 2   # el primer compás empieza después de la anacrusa de la intro


def midi_note(name):
    return 12 * (int(name[-1]) + 1) + NAMES[name[0]] + (1 if "#" in name else 0)


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


def melody(part, start, text, vel, octave=False):
    """Toca una frase escrita como "B4:.5 A4:1 R:1 G4+B4:2" (nota:duración en corcheas, R = silencio).
    Con octave=True dobla cada nota una octava arriba."""
    t = start
    for tok in text.split():
        names, d = tok.split(":")
        d = float(d)
        if names != "R":
            for name in names.split("+"):
                n = midi_note(name)
                part.add(t, d, n, vel)
                if octave:
                    part.add(t, d, n + 12, vel - 10)
        t += d
    return t


def comp(lh, start, bars, vel, heavy=False):
    """Acompañamiento de son: cada compás es un acorde ("G") o una lista [(posición, acorde), …]."""
    for i, bar in enumerate(bars):
        b0 = start + 6 * i
        ternary = round((b0 - BAR0) / 6) % 2 == 0
        pattern = PATTERN_68 if ternary else PATTERN_34
        segs = bar if isinstance(bar, list) else [(0, bar)]
        for j, (off, name) in enumerate(segs):
            end = segs[j + 1][0] if j + 1 < len(segs) else 6
            root, chord = CHORDS[name]
            nxt = min([p for p, _, _ in pattern if p > off] + [end])
            lh.add(b0 + off, nxt - off, root, vel + 8)
            if heavy:
                lh.add(b0 + off, nxt - off, root - 12 if root - 12 >= 36 else root + 12, vel)
            for p, kind, d in pattern:
                if off < p < end:
                    d = min(d, end - p)
                    if kind == "c":
                        lh.chord(b0 + p, d, chord, vel - 8)
                    else:
                        lh.add(b0 + p, d, root + (7 if kind == "q" else 0), vel + 2)
    return start + 6 * len(bars)


def tremolo(part, start, notes, count, vel0, vel1):
    """Trémolo en semicorcheas alternando las notas dadas (count notas de media corchea)."""
    for i in range(count):
        part.add(start + i * 0.5, 0.5, midi_note(notes[i % len(notes)]), vel0 + (vel1 - vel0) * i / count)
    return start + count * 0.5


def main():
    rh, lh = Part(), Part()

    # ---- Intro: anacrusa "si la si do" y trémolo en Re (24 veces), luego en Fa# (24 veces)
    t = melody(rh, 0, "B4:.5 A4:.5 B4:.5 C5:.5", 92)
    lh.chord(t, 12, ["G2", "G3", "B3", "D4"], 72)
    t = tremolo(rh, t, ["D5", "D6"], 24, 84, 104)
    lh.chord(t, 12, ["D2", "F#3", "A3", "C4"], 76)
    t = tremolo(rh, t, ["F#5", "F#6"], 24, 88, 108)
    # Golpes en hemiola: dos de tres corcheas y tres de dos, dos veces
    for off, d in [(0, 3), (3, 3), (6, 2), (8, 2), (10, 2), (12, 3), (15, 3), (18, 2), (20, 2), (22, 2)]:
        rh.chord(t + off, d, ["F#5", "A5", "C6", "F#6"], 104 + (8 if off in (0, 12, 22) else 0))
        lh.chord(t + off, d, ["D2", "D3"], 100)
    t += 24                                                         # 50

    # ---- "Si la si do re" cuatro veces
    s = t
    for i in range(4):
        t = melody(rh, t, "B4:.5 A4:.5 B4:.5 C5:.5 D5:4", 88 + 3 * i, octave=i >= 2)
    comp(lh, s, ["G", "D7", "G", "G"], 66)
    # Respuesta "do re do re la fa# / la do si la si", tres veces
    s = t
    for i in range(3):
        t = melody(rh, t, "C5:1 D5:1 C5:1 D5:1 A4:1 F#4:1", 92, octave=i == 2)
        fin = "A4:1 C5:1 B4:1 A4:1 B4:1 B4:1" if i == 2 else "A4:1 C5:1 B4:1 A4:1 B4:2"
        t = melody(rh, t, fin, 92, octave=i == 2)
    comp(lh, s, ["D7", "G"] * 3, 70)                                # 110

    # ---- Melodía de violines
    s = t
    frases = [
        "D5:1 C5:1 B4:1 C5:1 D5:1 B4:1", "G4:3 G4:3",
        "E4:1 F#4:1 G4:1 A4:1 B4:1 G4:1", "D4:3 D4:3",
        "D5:1 C5:1 B4:1 C5:1 D5:1 B4:1", "G4:3 G4:3",
        "E4:1 F#4:1 G4:1 A4:1 B4:1 A4:1", "G4:1 F#4:1 E4:1 D4:1 C4:1 D4:1",
        "E4:1 F#4:1 G4:1 A4:1 B4:2",
    ]
    for i, f in enumerate(frases):
        t = melody(rh, t, f, 86 + i, octave=i >= 4)
    comp(lh, s, ["G", "G", "C", "D7", "G", "G", "C", "D7", "G"], 70)   # 164

    # ---- Segunda parte, la segunda vez en octavas
    s = t
    for i in range(2):
        for f in ["E5:1 D5:1 C5:1 B4:1 C5:1 D5:1", "E5:3 E5:3",
                  "C5:1 D5:1 D5:1 D5:1 E5:1 D5:1", "E5:3 D5:3"]:
            t = melody(rh, t, f, 94 + 6 * i, octave=i == 1)
    comp(lh, s, ["C", "A7", "D7", [(0, "C"), (3, "G")]] * 2, 74)       # 212

    # ---- Trompetas (clímax): trémolo en Sol con la izquierda en octavas
    tremolo(lh, t, ["G2", "G3"], 24, 84, 100)
    lh.chord(t, 12, ["B3", "D4"], 70)
    t = tremolo(rh, t, ["G5", "G6"], 24, 98, 116)
    s = t
    t = melody(rh, t, "D#5:.5 C#5:.5 D#5:.5 E5:.5 F#5:1 F#5:1 G5:2", 108, octave=True)
    t = melody(rh, t, "B4:.5 C5:.5 D5:.5 F#5:.5 E5:.5 D5:.5 C5:.5 B4:2.5", 106, octave=True)
    for i in range(2):
        t = melody(rh, t, "B4:.5 C5:.5 D5:.5 D5:1 E5:1 F#5:1 G5:1.5", 108 + 2 * i, octave=True)
        t = melody(rh, t, "B4:.5 C5:.5 D5:.5 F#5:.5 E5:.5 D5:.5 C5:.5 B4:2.5", 106 + 2 * i, octave=True)
    escala = [[(0, "G"), (1.5, "D7"), (4.5, "G")], [(0, "D7"), (3.5, "G")]]
    comp(lh, s, [[(0, "B7"), (4, "G")], [(0, "D7"), (3.5, "G")]] + escala * 2, 82, heavy=True)  # 260

    # ---- Final 1: arpegios rápidos, tres veces
    s = t
    for i in range(3):
        t = melody(rh, t, "E5:.5 G5:.5 E5:.5 G5:.5 F#5:.5 D5:.5 F#5:.5 E5:.5 C5:.5 E5:.5 D5:1",
                   100 + 3 * i, octave=i >= 1)
        t = melody(rh, t, "A4:.5 C5:.5 A4:.5 C5:.5 B4:.5 G4:.5 B4:.5 A4:.5 F#4:.5 A4:.5 G4:1",
                   98 + 3 * i, octave=i >= 1)
    comp(lh, s, [[(0, "C"), (2, "D7"), (3.5, "C"), (5, "G")],
                 [(0, "D7"), (2, "G"), (3.5, "D7"), (5, "G")]] * 3, 80)
    # "Sol re do re", tres veces
    s = t
    for i in range(3):
        t = melody(rh, t, "G5:2 D5:2 C5:1 D5:1", 106 + 2 * i, octave=True)
    comp(lh, s, [[(0, "G"), (2, "D7"), (4, "C"), (5, "D7")]] * 3, 84, heavy=True)
    # Los golpes de seis: Sol, Re, Do, Re
    s = t
    for acorde in (["G5", "B5", "G6"], ["D5", "F#5", "D6"], ["C5", "E5", "C6"], ["D5", "F#5", "D6"]):
        for k in range(6):
            rh.chord(t + k, 1, acorde, 104 + (14 if k == 0 else 4 if k == 3 else 0))
        t += 6
    comp(lh, s, ["G", "D7", "C", "D7"], 88, heavy=True)               # 338

    # ---- Final 2: arpegios en secuencia hacia abajo (Do, Si menor, La menor, Sol), dos veces
    s = t
    for i in range(2):
        t = melody(rh, t, "C5:.5 C5:.5 E5:.5 E5:.5 G5:.5 G5:.5 B4:.5 B4:.5 D5:.5 D5:.5 F#5:.5 F#5:.5 "
                          "A4:.5 A4:.5 C5:.5 C5:.5 E5:.5 E5:.5 G4:.5 G4:.5 B4:.5 B4:.5 D5:.5 D5:.5",
                   104 + 6 * i, octave=True)
    comp(lh, s, [[(0, "C"), (3, "Bm")], [(0, "Am"), (3, "G")]] * 2, 86, heavy=True)
    # Remate: "re fa# la sol … ¡sol!"
    t = melody(rh, t, "D5:1 F#4:.5 A4:.5 G4:1 R:1", 112, octave=True)
    lh.chord(t - 4, 2, ["D2", "D3", "F#3", "C4"], 104)
    lh.chord(t - 2, 1, ["G2", "G3"], 110)
    rh.chord(t, 6, ["G4", "B4", "D5", "G5", "B5", "D6", "G6"], 120)
    lh.chord(t, 6, ["G2", "D3", "G3", "B3"], 116)
    t += 6
    assert abs(t - TOTAL_UNITS) < 1e-6, t                           # 372

    mid = mido.MidiFile(ticks_per_beat=TPB)
    meta = mido.MidiTrack([
        mido.MetaMessage("track_name", name="El Son de la Negra - Neon Keys", time=0),
        mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0),
        mido.MetaMessage("time_signature", numerator=6, denominator=8, time=0),
    ])
    mid.tracks += [meta, rh.to_track("mano derecha", 0), lh.to_track("mano izquierda", 1)]
    OUT.parent.mkdir(exist_ok=True)
    mid.save(OUT)
    print(f"{OUT}  ({BPM:.0f} corcheas por minuto, {mid.length:.1f} s, "
          f"{len(rh.notes)} + {len(lh.notes)} notas)")


if __name__ == "__main__":
    main()
