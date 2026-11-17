#!/usr/bin/env python3
"""Neon Keys: genera videos verticales de piano "falling notes" a partir de un MIDI.

Uso:
    python neon_keys.py midi/clair-de-lune.mid --titulo "Clair de Lune" --subtitulo "Debussy"
    python neon_keys.py midi/clair-de-lune.mid --preview 20   # solo un cuadro PNG en t=20s
"""

import argparse
import math
import subprocess
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

import mido
import numpy as np
import tinysoundfont
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent

# --- Lienzo (TikTok 9:16) ---
W, H = 1080, 1920
FPS = 30
SAMPLE_RATE = 44100

# --- Layout ---
KEYS_TOP = 1360          # línea donde las notas "golpean" el teclado
WHITE_KEY_H = 230
BLACK_KEY_H = 145
FALL_SPEED = 420         # px por segundo
LEAD_IN = KEYS_TOP / FALL_SPEED  # segundos para que la primera nota llegue al teclado
OUTRO = 3.5              # segundos de cierre al final

# --- Paleta neón ---
BG_TOP = (8, 4, 22)
BG_BOTTOM = (26, 8, 44)
GRID = (255, 40, 200)
COLOR_RIGHT = (0, 240, 255)   # mano derecha / agudos
COLOR_LEFT = (255, 50, 210)   # mano izquierda / graves
TITLE_COLOR = (255, 255, 255)
TITLE_GLOW = (0, 220, 255)
BRAND_GLOW = (255, 50, 210)

FONT_BOLD = "/System/Library/Fonts/Supplemental/Futura.ttc"
FONT_TEXT = "/System/Library/Fonts/Avenir Next.ttc"

BLACK_PCS = {1, 3, 6, 8, 10}


@dataclass
class Note:
    pitch: int
    start: float
    end: float
    velocity: int
    hand: str  # "R" o "L"


def font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return ImageFont.load_default(size)


# ---------------------------------------------------------------- MIDI

def load_midi(path):
    """Devuelve (notas, eventos) con tiempos absolutos en segundos."""
    mid = mido.MidiFile(path)
    # Asigna mano por pista cuando hay dos pistas con notas; si no, por altura.
    track_of_channel = {}
    note_tracks = []
    for i, track in enumerate(mid.tracks):
        chans = {m.channel for m in track if m.type == "note_on"}
        if chans:
            note_tracks.append(i)
            for c in chans:
                track_of_channel.setdefault(c, i)

    notes, events, open_notes = [], [], {}
    t = 0.0
    for msg in mid:
        t += msg.time
        if msg.is_meta:
            continue
        events.append((t, msg))
        if msg.type == "note_on" and msg.velocity > 0:
            open_notes[(msg.channel, msg.note)] = (t, msg.velocity)
        elif msg.type in ("note_off", "note_on"):
            key = (msg.channel, msg.note)
            if key in open_notes:
                start, vel = open_notes.pop(key)
                if len(note_tracks) >= 2:
                    hand = "R" if track_of_channel.get(msg.channel) == note_tracks[0] else "L"
                else:
                    hand = "R" if msg.note >= 60 else "L"
                notes.append(Note(msg.note, start, max(t, start + 0.06), vel, hand))
    notes.sort(key=lambda n: n.start)
    return notes, events


# ---------------------------------------------------------------- Audio

def render_audio(events, sf_path, start, length, total, out_wav):
    """Sintetiza el piano para [start, start+length] y lo coloca tras el LEAD_IN."""
    synth = tinysoundfont.Synth(samplerate=SAMPLE_RATE)
    sfid = synth.sfload(str(sf_path))
    for ch in range(16):
        if ch != 9:
            synth.program_select(ch, sfid, 0, 0)

    end = start + length
    chunks = []
    cursor = start
    for t, msg in events:
        if t > end:
            break
        if t >= start and t > cursor:
            n = int(round((t - cursor) * SAMPLE_RATE))
            if n > 0:
                chunks.append(np.frombuffer(synth.generate(n), dtype=np.float32).copy())
            cursor = t
        playing = t >= start
        if msg.type == "note_on" and msg.velocity > 0:
            if playing:
                synth.noteon(msg.channel, msg.note, msg.velocity)
        elif msg.type in ("note_on", "note_off"):
            synth.noteoff(msg.channel, msg.note)
        elif msg.type == "control_change":
            synth.control_change(msg.channel, msg.control, msg.value)
    synth.notes_off()
    tail = int((end + 2.0 - cursor) * SAMPLE_RATE)
    chunks.append(np.frombuffer(synth.generate(tail), dtype=np.float32).copy())

    music = np.concatenate(chunks).reshape(-1, 2)
    lead = np.zeros((int(LEAD_IN * SAMPLE_RATE), 2), dtype=np.float32)
    audio = np.concatenate([lead, music])
    n_total = int(total * SAMPLE_RATE)
    audio = np.pad(audio, ((0, max(0, n_total - len(audio))), (0, 0)))[:n_total]

    # Fade out durante el cierre y normaliza a -1 dB.
    fade_n = int(OUTRO * SAMPLE_RATE)
    audio[-fade_n:] *= np.linspace(1, 0, fade_n, dtype=np.float32)[:, None]
    peak = float(np.abs(audio).max()) or 1.0
    audio *= 0.89 / peak

    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- Teclado

class Keyboard:
    def __init__(self, lo, hi):
        # Ajusta el rango a teclas blancas en los extremos.
        while lo % 12 in BLACK_PCS:
            lo -= 1
        while hi % 12 in BLACK_PCS:
            hi += 1
        self.lo, self.hi = lo, hi
        whites = [p for p in range(lo, hi + 1) if p % 12 not in BLACK_PCS]
        self.white_w = W / len(whites)
        self.black_w = self.white_w * 0.62
        self.x = {}
        for i, p in enumerate(whites):
            self.x[p] = (i * self.white_w, (i + 1) * self.white_w)
        for p in range(lo, hi + 1):
            if p % 12 in BLACK_PCS:
                edge = self.x[p - 1][1]
                self.x[p] = (edge - self.black_w / 2, edge + self.black_w / 2)

    def is_black(self, p):
        return p % 12 in BLACK_PCS


# ---------------------------------------------------------------- Dibujo

def make_background(kb=None):
    """Degradado + piso synthwave. Con `kb` dibuja además los carriles de cada Do."""
    img = Image.new("RGB", (W, H))
    grad = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(BG_TOP), np.array(BG_BOTTOM)
    arr = (top + (bot - top) * grad).repeat(W, axis=1).astype(np.uint8)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)

    # Carriles tenues en cada Do para dar referencia.
    for p in range(kb.lo, kb.hi + 1) if kb else ():
        if p % 12 == 0:
            x = int(kb.x[p][0])
            d.line([(x, 0), (x, KEYS_TOP)], fill=(40, 22, 70), width=2)

    # Piso synthwave en perspectiva debajo del teclado.
    floor_top = KEYS_TOP + WHITE_KEY_H
    glow = Image.new("RGB", (W, H))
    g = ImageDraw.Draw(glow)
    vanish_x = W / 2
    for i in range(-14, 15):
        x_bottom = vanish_x + i * 140
        g.line([(vanish_x + i * 18, floor_top), (x_bottom, H)], fill=GRID, width=2)
    for k in range(1, 12):
        y = floor_top + (H - floor_top) * (k / 11) ** 1.8
        g.line([(0, y), (W, y)], fill=GRID, width=2)
    glow = Image.blend(Image.new("RGB", (W, H)), glow, 0.35)
    soft = glow.filter(ImageFilter.GaussianBlur(6))
    img = ImageChops.add(img, ImageChops.add(glow, soft))
    return img


def glow_text(base, xy, text, fnt, color, glow_color, anchor="mm", radius=14, alpha=1.0, spacing=0):
    """Dibuja texto con halo neón sobre `base` (RGB)."""
    layer = Image.new("RGB", base.size)
    d = ImageDraw.Draw(layer)
    if spacing:
        text = (" " * spacing).join(text)
    d.text(xy, text, font=fnt, fill=glow_color, anchor=anchor)
    halo = layer.filter(ImageFilter.GaussianBlur(radius))
    halo = ImageChops.add(halo, halo)
    core = Image.new("RGB", base.size)
    ImageDraw.Draw(core).text(xy, text, font=fnt, fill=color, anchor=anchor)
    combined = ImageChops.lighter(ImageChops.screen(halo, Image.new("RGB", base.size)), core)
    if alpha < 1.0:
        combined = Image.blend(Image.new("RGB", base.size), combined, alpha)
    return ImageChops.screen(base, combined)


def make_title_layer(titulo, subtitulo):
    layer = Image.new("RGB", (W, H))
    layer = glow_text(layer, (W / 2, 230), titulo, font(FONT_BOLD, 92, 2), TITLE_COLOR, TITLE_GLOW, radius=18)
    if subtitulo:
        layer = glow_text(layer, (W / 2, 320), subtitulo.upper(), font(FONT_TEXT, 40, 0),
                          (230, 230, 255), BRAND_GLOW, radius=10, spacing=1)
    return layer


def make_brand_layer():
    layer = Image.new("RGB", (W, H))
    return glow_text(layer, (W / 2, 1640), "NEON KEYS", font(FONT_BOLD, 38, 2),
                     (255, 255, 255), BRAND_GLOW, radius=10, alpha=0.8, spacing=1)


def make_outro_layer():
    layer = Image.new("RGB", (W, H))
    layer = glow_text(layer, (W / 2, 820), "NEON KEYS", font(FONT_BOLD, 130, 2),
                      (255, 255, 255), BRAND_GLOW, radius=26)
    layer = glow_text(layer, (W / 2, 980), "Sígueme para la parte 2", font(FONT_TEXT, 54, 0),
                      (255, 255, 255), TITLE_GLOW, radius=14)
    return layer


def brighten(color, f):
    return tuple(min(255, int(c + (255 - c) * f)) for c in color)


def hand_color(note):
    return COLOR_RIGHT if note.hand == "R" else COLOR_LEFT


class Renderer:
    def __init__(self, notes, kb, titulo, subtitulo, start, length):
        self.notes = notes
        self.kb = kb
        self.start = start
        self.length = length
        self.total = LEAD_IN + length + OUTRO
        self.bg = make_background(kb)
        self.title = make_title_layer(titulo, subtitulo)
        self.brand = make_brand_layer()
        self.outro = make_outro_layer()
        self.lookahead = KEYS_TOP / FALL_SPEED + 0.2
        # Las notas aparecen con fundido debajo del título.
        ramp = np.clip((np.arange(H) - 380) / 260, 0, 1)
        self.notes_mask = Image.fromarray((ramp[:, None] * 255).repeat(W, axis=1).astype(np.uint8), "L")
        self.black = Image.new("RGB", (W, H))

    def song_time(self, t):
        return t - LEAD_IN + self.start

    def frame(self, t):
        st = self.song_time(t)
        song_end = self.start + self.length
        kb = self.kb

        notes_layer = Image.new("RGB", (W, H))
        nd = ImageDraw.Draw(notes_layer)
        active = {}

        visible = [n for n in self.notes
                   if n.start < st + self.lookahead and n.end > st - 0.7
                   and self.start - 0.01 <= n.start <= song_end]
        # Blancas primero para que las negras queden encima.
        visible.sort(key=lambda n: kb.is_black(n.pitch))
        for n in visible:
            if n.pitch not in kb.x:
                continue
            x0, x1 = kb.x[n.pitch]
            pad = 3
            # Pequeño hueco vertical para separar notas repetidas.
            y_bottom = min(KEYS_TOP - (n.start - st) * FALL_SPEED, KEYS_TOP) - 1
            y_top = KEYS_TOP - (n.end - st) * FALL_SPEED + 2
            color = hand_color(n)
            if n.start <= st < n.end:
                active[n.pitch] = color
            if y_bottom > y_top and y_bottom > 0:
                core = brighten(color, 0.25 + 0.25 * n.velocity / 127)
                nd.rounded_rectangle([x0 + pad, y_top, x1 - pad, y_bottom],
                                     radius=min(10, (x1 - x0) / 3, (y_bottom - y_top) / 2), fill=core)
                # Brillo interior para que parezca tubo de neón.
                if y_bottom - y_top > 14:
                    cx = (x0 + x1) / 2
                    nd.line([(cx, y_top + 6), (cx, y_bottom - 6)], fill=brighten(color, 0.85),
                            width=max(2, int((x1 - x0) * 0.18)))

            # Chispas al momento del golpe.
            age = st - n.start
            if 0 <= age < 0.6:
                rng = np.random.default_rng(int(n.start * 1000) * 131 + n.pitch)
                cx = (x0 + x1) / 2
                life = 1 - age / 0.6
                for _ in range(10):
                    vx = rng.uniform(-260, 260)
                    vy = rng.uniform(-700, -250)
                    px = cx + vx * age
                    py = KEYS_TOP + vy * age + 0.5 * 1600 * age * age
                    r = 2 + 3 * life
                    nd.ellipse([px - r, py - r, px + r, py + r], fill=brighten(color, 0.5 * life))

        # Destello de la línea de impacto en teclas activas.
        for p, color in active.items():
            x0, x1 = kb.x[p]
            nd.rectangle([x0, KEYS_TOP - 10, x1, KEYS_TOP + 4], fill=brighten(color, 0.4))

        notes_layer = Image.composite(notes_layer, self.black, self.notes_mask)

        # Halo neón: blur barato a 1/4 de resolución.
        small = notes_layer.resize((W // 4, H // 4), Image.BILINEAR)
        halo = small.filter(ImageFilter.GaussianBlur(7)).resize((W, H), Image.BILINEAR)
        halo = ImageChops.add(halo, halo)

        img = ImageChops.screen(self.bg, halo)
        img = ImageChops.lighter(img, notes_layer)

        # Línea de impacto permanente.
        d = ImageDraw.Draw(img)
        d.line([(0, KEYS_TOP - 2), (W, KEYS_TOP - 2)], fill=(120, 80, 200), width=3)

        self.draw_keyboard(img, active)
        img = ImageChops.screen(img, self.title)
        img = ImageChops.screen(img, self.brand)

        # Fundido de entrada.
        if t < 0.6:
            img = Image.blend(Image.new("RGB", (W, H)), img, t / 0.6)

        # Cierre: oscurece y muestra la marca.
        outro_start = self.total - OUTRO
        if t >= outro_start:
            k = min(1.0, (t - outro_start) / 0.8)
            img = Image.blend(img, Image.new("RGB", (W, H), BG_TOP), 0.82 * k)
            img = ImageChops.screen(img, Image.blend(Image.new("RGB", (W, H)), self.outro, k))
        return img

    def draw_keyboard(self, img, active):
        kb = self.kb
        d = ImageDraw.Draw(img)
        y0 = KEYS_TOP
        for p in range(kb.lo, kb.hi + 1):
            if kb.is_black(p):
                continue
            x0, x1 = kb.x[p]
            fill = brighten(active[p], 0.35) if p in active else (225, 222, 240)
            d.rectangle([x0 + 1, y0, x1 - 1, y0 + WHITE_KEY_H], fill=fill)
            d.rectangle([x0 + 1, y0 + WHITE_KEY_H - 10, x1 - 1, y0 + WHITE_KEY_H],
                        fill=tuple(int(c * 0.75) for c in fill))
        for p in range(kb.lo, kb.hi + 1):
            if not kb.is_black(p):
                continue
            x0, x1 = kb.x[p]
            fill = active[p] if p in active else (18, 12, 30)
            d.rectangle([x0, y0, x1, y0 + BLACK_KEY_H], fill=fill)
            if p not in active:
                d.rectangle([x0 + 3, y0 + BLACK_KEY_H - 12, x1 - 3, y0 + BLACK_KEY_H - 4],
                            fill=(55, 45, 75))


# ---------------------------------------------------------------- Main

def main():
    ap = argparse.ArgumentParser(description="Genera un video Neon Keys desde un MIDI.")
    ap.add_argument("midi")
    ap.add_argument("--titulo", default=None)
    ap.add_argument("--subtitulo", default="")
    ap.add_argument("--inicio", type=float, default=None,
                    help="segundo de la canción donde empieza el video (por defecto, la primera nota)")
    ap.add_argument("--duracion", type=float, default=62.0,
                    help="segundos de música (TikTok paga a partir de 1 minuto)")
    ap.add_argument("--salida", default=None)
    ap.add_argument("--soundfont", default=str(ROOT / "soundfonts" / "FluidR3Mono_GM.sf3"))
    ap.add_argument("--preview", type=float, default=None,
                    help="renderiza solo un cuadro PNG en este segundo del video")
    args = ap.parse_args()

    midi_path = Path(args.midi)
    titulo = args.titulo or midi_path.stem.replace("-", " ").title()
    out = Path(args.salida) if args.salida else ROOT / "out" / "videos" / "piano" / f"{midi_path.stem}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    notes, events = load_midi(midi_path)
    if not notes:
        sys.exit("El MIDI no tiene notas.")
    start = args.inicio if args.inicio is not None else max(0.0, notes[0].start - 0.2)
    length = min(args.duracion, notes[-1].end - start)
    in_range = [n for n in notes if start <= n.start <= start + length]
    kb = Keyboard(min(n.pitch for n in in_range) - 2, max(n.pitch for n in in_range) + 2)

    r = Renderer(notes, kb, titulo, args.subtitulo, start, length)

    if args.preview is not None:
        png = out.with_suffix(f".preview-{args.preview:g}s.png")
        r.frame(args.preview).save(png)
        print(png)
        return

    # Se escribe en out/.tmp y se mueve al final, para que nadie abra un video a medias.
    tmp_dir = ROOT / "out" / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    tmp_out = tmp_dir / out.name
    wav = tmp_out.with_suffix(".wav")
    print(f"Audio: {length:.1f}s de música desde {start:.1f}s …")
    render_audio(events, args.soundfont, start, length, r.total, wav)

    n_frames = int(r.total * FPS)
    print(f"Video: {n_frames} cuadros ({r.total:.1f}s) …")
    ff = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav),
        "-map", "0:v", "-map", "1:a", "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(tmp_out),
    ], stdin=subprocess.PIPE)
    for i in range(n_frames):
        ff.stdin.write(r.frame(i / FPS).tobytes())
        if i % (FPS * 5) == 0:
            print(f"  {i / FPS:5.1f}s / {r.total:.1f}s", flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg falló")
    wav.unlink(missing_ok=True)
    tmp_out.replace(out)
    print(f"Listo: {out}")


if __name__ == "__main__":
    main()
