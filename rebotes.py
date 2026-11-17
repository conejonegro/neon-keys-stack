#!/usr/bin/env python3
"""Neon Keys · bolitas rebotando en un anillo con salida.

Cada rebote toca la siguiente nota de La Bamba en marimba. Cuando una bolita escapa por el
hueco, nacen 3 más. Al final todo se satura y el video "se traba" (glitch de video y audio
sincronizados) antes de cortar al logo.

Hay dos versiones (PRESETS): "corto" (10 s, la prueba original) y "largo" (70 s, para monetizar;
el hueco empieza chico y se va abriendo para que el caos llegue cerca del final).

Uso:
    .venv/bin/python rebotes.py                  # genera out/videos/bolitas/rebotes-la-bamba.mp4
    .venv/bin/python rebotes.py --version largo  # genera out/videos/bolitas/rebotes-la-bamba-largo.mp4
    .venv/bin/python rebotes.py --preview 6      # solo un cuadro PNG en t=6s
    .venv/bin/python rebotes.py --stats          # solo simula e imprime cuántas bolitas hay
"""

import argparse
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import tinysoundfont
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from arreglos.la_bamba import MELODY, MELODY_SHIFT, parse
from neon_keys import (BRAND_GLOW, COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, FONT_TEXT, FPS, H,
                       SAMPLE_RATE, W, font, glow_text, make_background, make_brand_layer)

ROOT = Path(__file__).resolve().parent
SOUNDFONT = ROOT / "soundfonts" / "FluidR3Mono_GM.sf3"

# --- Versiones ---
# gap: mitad del hueco en grados al inicio y al final de GROW (segundos); spawn: máximo de bolitas que nacen
# por escape. full: si se da, cuántas nacen sigue una curva que llega a MAX_INSIDE en ese segundo (ritmo parejo).
PRESETS = {
    "corto": dict(duration=10.0, seed=5, gap=(36, 36), grow=1.0, spawn=3, full=None,
                  salida="rebotes-la-bamba.mp4"),
    "largo": dict(duration=70.0, seed=5, gap=(20, 36), grow=60.0, spawn=3, full=62.0,
                  salida="rebotes-la-bamba-largo.mp4"),
}

# --- Tiempos (los ajusta configure() según la versión) ---
DURATION = 10.0
GLITCH_START = 8.0     # empieza a "trabarse"
FREEZE_START = 9.0     # congelado total
END_CARD = 9.3         # corte al logo

# --- Física ---
SEED = 5
GAP_START, GAP_END, GROW = math.radians(36), math.radians(36), 1.0
FULL_AT = None
CENTER = np.array([W / 2, 900.0])
RING_R = 350.0
BALL_R = 16.0
GAP_SPEED = 1.1                  # rad/s que gira el hueco
GRAVITY = 500.0
MIN_SPEED, MAX_SPEED = 1450.0, 2175.0
SPAWN = 3
MAX_INSIDE = 650
SUBSTEPS = 8

# --- Sonido ---
MARIMBA, GLOCKENSPIEL, PIANO = 12, 9, 0
MAX_NOTES_PER_SLOT = 5           # notas máximas cada 30 ms (para no saturar en el caos)

PALETTE = [COLOR_RIGHT, COLOR_LEFT, (255, 225, 70), (90, 255, 160), (255, 140, 60), (170, 100, 255)]
WHITE = (255, 255, 255)


def configure(name):
    global DURATION, GLITCH_START, FREEZE_START, END_CARD, SEED, GAP_START, GAP_END, GROW, SPAWN, FULL_AT
    p = PRESETS[name]
    DURATION = p["duration"]
    GLITCH_START, FREEZE_START, END_CARD = DURATION - 2.0, DURATION - 1.0, DURATION - 0.7
    SEED, SPAWN, GROW, FULL_AT = p["seed"], p["spawn"], p["grow"], p["full"]
    GAP_START, GAP_END = math.radians(p["gap"][0]), math.radians(p["gap"][1])
    return ROOT / "out" / "videos" / "bolitas" / p["salida"]


def gap_angle(t):
    return -math.pi / 2 + GAP_SPEED * t


def target_inside(t):
    """Cuántas bolitas 'deberían' estar dentro en t: crece exponencial de 1 a MAX_INSIDE en FULL_AT."""
    return MAX_INSIDE ** min(1.0, t / FULL_AT)


def gap_half(t):
    """Mitad del hueco; se abre poco a poco durante GROW segundos (curva suave)."""
    k = min(1.0, t / GROW)
    return GAP_START + (GAP_END - GAP_START) * k * k


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


# ---------------------------------------------------------------- Simulación

def simulate(until):
    """Simula a 240 Hz y guarda el estado de cada cuadro más los eventos de sonido."""
    rng = np.random.default_rng(SEED)
    pos = np.array([[CENTER[0] - 40, CENTER[1] - 120]])
    vel = np.array([[420.0, -260.0]])
    col = np.array([-1])          # -1 = bolita blanca inicial
    out = np.array([False])       # ya escapó (vuela hacia afuera, sin colisiones)

    dt = 1 / (FPS * SUBSTEPS)
    frames, bounces, escapes = [], [], []
    total = 1                     # bolitas que han aparecido en total (incluye las que ya salieron)
    n_frames = int(math.ceil(until * FPS)) + 1
    for f in range(n_frames):
        frames.append((pos.copy(), vel.copy(), col.copy(), out.copy(), total))
        for s in range(SUBSTEPS):
            t = (f * SUBSTEPS + s) * dt
            vel[:, 1] += GRAVITY * dt
            pos += vel * dt

            d = pos - CENTER
            dist = np.hypot(d[:, 0], d[:, 1])
            inside = ~out
            hit = inside & (dist + BALL_R >= RING_R)
            ang = np.arctan2(d[:, 1], d[:, 0])
            in_gap = np.abs(wrap(ang - gap_angle(t))) < gap_half(t)

            bounce = hit & ~in_gap
            if bounce.any():
                idx = np.nonzero(bounce)[0]
                n = d[idx] / dist[idx, None]
                vn = np.sum(vel[idx] * n, axis=1)
                going_out = vn > 0
                idx, n, vn = idx[going_out], n[going_out], vn[going_out]
                vel[idx] -= 2 * vn[:, None] * n
                pos[idx] = CENTER + n * (RING_R - BALL_R - 0.5)
                sp = np.hypot(vel[idx, 0], vel[idx, 1])
                vel[idx] *= np.clip(sp, MIN_SPEED, MAX_SPEED)[:, None] / sp[:, None]
                for i, nn in zip(idx, n):
                    bounces.append((t, CENTER + nn * RING_R, int(col[i])))

            escaped = inside & (dist > RING_R + BALL_R + 4)
            if escaped.any():
                out[escaped] = True
                n_new = 0
                for _ in range(int(escaped.sum())):
                    escapes.append(t)
                    inside_now = int((~out).sum()) + n_new
                    want = SPAWN
                    if FULL_AT:
                        want = max(1, min(SPAWN, math.ceil(target_inside(t) - inside_now)))
                    n_new += max(0, min(want, MAX_INSIDE - inside_now))
                total += n_new
                if n_new:
                    a = rng.uniform(0, 2 * np.pi, n_new)
                    spd = rng.uniform(650, 950, n_new)
                    pos = np.vstack([pos, CENTER + rng.normal(0, 6, (n_new, 2))])
                    vel = np.vstack([vel, np.c_[np.cos(a) * spd, np.sin(a) * spd]])
                    col = np.concatenate([col, rng.integers(0, len(PALETTE), n_new)])
                    out = np.concatenate([out, np.zeros(n_new, bool)])

            # Quita las que ya salieron de la pantalla.
            keep = ~(out & ((pos[:, 1] > H + 50) | (pos[:, 0] < -50) | (pos[:, 0] > W + 50)))
            if not keep.all():
                pos, vel, col, out = pos[keep], vel[keep], col[keep], out[keep]
    return frames, bounces, escapes


# ---------------------------------------------------------------- Tiempo "trabado"

def source_time(t):
    """Mapea el tiempo de salida al tiempo de la simulación; aquí vive el glitch."""
    if t < GLITCH_START:
        return t
    if t < GLITCH_START + 0.6:   # cada pedacito de 0.1 s se repite dos veces
        k = math.floor((t - GLITCH_START) / 0.2)
        return GLITCH_START + k * 0.1 + ((t - GLITCH_START) - k * 0.2) % 0.1
    if t < FREEZE_START:   # casi congelado, avanza a saltitos
        return GLITCH_START + 0.3 + math.floor((t - GLITCH_START - 0.6) / 0.1) * 0.034
    return GLITCH_START + 0.44   # congelado


def glitch_amount(t):
    start = GLITCH_START - 0.4
    if t < start:
        return 0.0
    return min(1.0, (t - start) / (END_CARD - 0.1 - start))


# ---------------------------------------------------------------- Audio

def render_audio(bounces, escapes, out_wav):
    melody = [n for _, _, n in parse(MELODY, MELODY_SHIFT)]
    events = []   # (t, canal, nota, velocidad, duración)
    slots = {}
    for i, (t, _, _) in enumerate(sorted(bounces, key=lambda b: b[0])):
        slot = int(t / 0.03)
        slots[slot] = slots.get(slot, 0) + 1
        if slots[slot] > MAX_NOTES_PER_SLOT:
            continue
        note = melody[i % len(melody)]
        events.append((t, 0, note, 100, 0.35))
        if i % 4 == 0:
            events.append((t, 0, note - 24, 70, 0.4))   # bajo suave cada 4 rebotes
    for t in escapes:
        for k, n in enumerate((84, 88, 91)):           # destello Do mayor en glockenspiel
            events.append((t + k * 0.03, 1, n, 70, 0.5))
    # Golpe final en el corte al logo.
    for n in (36, 48, 55, 60, 64, 67, 72):
        events.append((END_CARD, 2, n, 110, 2.0))

    synth = tinysoundfont.Synth(samplerate=SAMPLE_RATE)
    sf = synth.sfload(str(SOUNDFONT))
    synth.program_select(0, sf, 0, MARIMBA)
    synth.program_select(1, sf, 0, GLOCKENSPIEL)
    synth.program_select(2, sf, 0, PIANO)

    timeline = []
    for t, ch, n, v, d in events:
        timeline.append((t, 1, ch, n, v))
        timeline.append((t + d, 0, ch, n, 0))
    timeline.sort(key=lambda e: (e[0], e[1]))

    chunks, cursor = [], 0.0
    for t, on, ch, n, v in timeline:
        if t > cursor:
            k = int(round((t - cursor) * SAMPLE_RATE))
            if k:
                chunks.append(np.frombuffer(synth.generate(k), dtype=np.float32).copy())
            cursor = t
        if on:
            synth.noteon(ch, n, v)
        else:
            synth.noteoff(ch, n)
    tail = int((DURATION + 1 - cursor) * SAMPLE_RATE)
    chunks.append(np.frombuffer(synth.generate(max(tail, 1)), dtype=np.float32).copy())
    src = np.concatenate(chunks).reshape(-1, 2)

    # Aplica el mismo mapa de tiempo que el video: el audio se traba igual.
    per_frame = SAMPLE_RATE // FPS
    n_frames = int(DURATION * FPS)
    out = np.zeros((n_frames * per_frame, 2), dtype=np.float32)
    for f in range(n_frames):
        t = f / FPS
        s = int(round((t if t >= END_CARD else source_time(t)) * SAMPLE_RATE))
        seg = src[s:s + per_frame]
        if END_CARD - 1 / FPS <= t < END_CARD:
            seg = seg * 0  # micro silencio antes del golpe
        out[f * per_frame:f * per_frame + len(seg)] = seg
    peak = float(np.abs(out).max()) or 1.0
    out *= 0.9 / peak
    out[-int(0.4 * SAMPLE_RATE):] *= np.linspace(1, 0, int(0.4 * SAMPLE_RATE))[:, None]

    pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- Video

def bright(c, f):
    return tuple(min(255, int(x + (255 - x) * f)) for x in c)


def ball_color(ci):
    return WHITE if ci < 0 else PALETTE[ci]


class Renderer:
    def __init__(self, frames, bounces):
        self.frames = frames
        self.bounces = sorted(bounces, key=lambda b: b[0])
        self.bounce_t = np.array([b[0] for b in self.bounces])
        self.bg = make_background()
        self.brand = make_brand_layer()
        title = Image.new("RGB", (W, H))
        title = glow_text(title, (W / 2, 250), "CADA REBOTE = UNA NOTA", font(FONT_BOLD, 58, 2),
                          WHITE, COLOR_RIGHT, radius=14)
        title = glow_text(title, (W / 2, 330), "LA BAMBA", font(FONT_TEXT, 40, 0),
                          (240, 230, 255), BRAND_GLOW, radius=10, spacing=1)
        # Aviso pequeño con la regla del juego.
        ImageDraw.Draw(title).text((W / 2, 392), "Cada bolita que sale hace aparecer nuevas",
                                   font=font(FONT_TEXT, 28, 0), fill=(150, 140, 175), anchor="mm")
        self.title = title
        self.end = glow_text(Image.new("RGB", (W, H)), (W / 2, 900), "NEON KEYS",
                             font(FONT_BOLD, 130, 2), WHITE, BRAND_GLOW, radius=26)
        self.counter_font = font(FONT_BOLD, 72, 2)
        self.label_font = font(FONT_TEXT, 26, 0)

    def scene(self, st):
        f = min(len(self.frames) - 1, int(round(st * FPS)))
        pos, vel, col, out, total = self.frames[f]
        glow = Image.new("RGB", (W, H))
        core = Image.new("RGB", (W, H))
        gd, cd = ImageDraw.Draw(glow), ImageDraw.Draw(core)

        # Anillo con hueco; el color gira con el tiempo.
        hue = (st * 0.15) % 1
        ring_c = tuple(int(255 * (0.5 + 0.5 * math.cos(2 * math.pi * (hue + k / 3)))) for k in range(3))
        ga = math.degrees(gap_angle(st))
        gh = math.degrees(gap_half(st))
        cx, cy = CENTER
        box = [cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R]
        gd.arc(box, ga + gh, ga - gh + 360, fill=ring_c, width=22)
        cd.arc(box, ga + gh, ga - gh + 360, fill=bright(ring_c, 0.5), width=8)

        # Destellos donde rebotan.
        lo = np.searchsorted(self.bounce_t, st - 0.15)
        hi = np.searchsorted(self.bounce_t, st)
        for t, p, ci in self.bounces[lo:hi][-80:]:
            k = 1 - (st - t) / 0.15
            r = 10 + 26 * (1 - k)
            c = tuple(int(x * k) for x in ball_color(ci))
            gd.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=c)

        # Bolitas con estela. Halo suave (sin brillo blanco encima); con muchas bolitas se atenúa más
        # para que no se vuelva una mancha blanca.
        halo_k = 0.55 * max(0.22, min(1.0, (60 / max(1, len(pos))) ** 0.5))
        for (x, y), (vx, vy), ci in zip(pos, vel, col):
            c = ball_color(ci)
            hc = tuple(int(v * halo_k) for v in c)
            tx, ty = x - vx * 0.05, y - vy * 0.05
            gd.line([(tx, ty), (x, y)], fill=tuple(int(v * 0.6) for v in hc), width=int(BALL_R * 1.4))
            gd.ellipse([x - BALL_R - 3, y - BALL_R - 3, x + BALL_R + 3, y + BALL_R + 3], fill=hc)
            cd.ellipse([x - BALL_R, y - BALL_R, x + BALL_R, y + BALL_R], fill=c)

        # Contador: todas las bolitas que han aparecido, no solo las que están dentro.
        cd.text((W / 2, 1480), f"{total}", font=self.counter_font, fill=WHITE, anchor="mm")
        gd.text((W / 2, 1480), f"{total}", font=self.counter_font, fill=COLOR_LEFT, anchor="mm")
        cd.text((W / 2, 1532), "BOLITAS", font=self.label_font, fill=(230, 220, 255), anchor="mm")

        small = glow.resize((W // 4, H // 4), Image.BILINEAR)
        halo = small.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
        halo = ImageChops.add(halo, halo)
        img = ImageChops.screen(self.bg, halo)
        img = ImageChops.lighter(img, core)
        img = ImageChops.screen(img, self.title)
        return ImageChops.screen(img, self.brand)

    def frame(self, t):
        if t >= END_CARD:
            k = min(1.0, (t - END_CARD) / 0.25)
            return Image.blend(Image.new("RGB", (W, H)), self.end, k)
        img = self.scene(source_time(t))
        if t < 0.3:
            img = Image.blend(Image.new("RGB", (W, H)), img, t / 0.3)
        g = glitch_amount(t)
        return glitch(img, g, int(t * FPS)) if g > 0 else img


def glitch(img, g, seed):
    """Desfase RGB, franjas desplazadas y temblor; más fuerte conforme sube g."""
    rng = np.random.default_rng(seed)
    a = np.asarray(img).copy()
    s = int(4 + 34 * g)
    a[:, :, 0] = np.roll(a[:, :, 0], s, axis=1)
    a[:, :, 2] = np.roll(a[:, :, 2], -s, axis=1)
    for _ in range(int(2 + 14 * g)):
        y0 = rng.integers(0, H - 40)
        h = rng.integers(8, int(20 + 120 * g))
        a[y0:y0 + h] = np.roll(a[y0:y0 + h], rng.integers(-int(160 * g) - 1, int(160 * g) + 1), axis=1)
    shake = int(18 * g)
    if shake:
        a = np.roll(a, (rng.integers(-shake, shake + 1), rng.integers(-shake, shake + 1)), axis=(0, 1))
    if g > 0.8 and rng.random() < 0.3:
        a = 255 - a   # destello invertido
    return Image.fromarray(a)


# ---------------------------------------------------------------- Main

def main():
    ap = argparse.ArgumentParser(description="Video de bolitas rebotando estilo Neon Keys.")
    ap.add_argument("--preview", type=float, default=None)
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--version", choices=PRESETS, default="corto")
    ap.add_argument("--seed", type=int, default=None, help="cambia la semilla (para probar con --stats)")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()
    default_out = configure(args.version)
    if args.seed is not None:
        global SEED
        SEED = args.seed

    frames, bounces, escapes = simulate(FREEZE_START)
    if args.stats:
        step = 1 if DURATION <= 15 else 5
        for sec in list(range(0, int(FREEZE_START), step)) + [int(FREEZE_START)]:
            f = min(len(frames) - 1, sec * FPS)
            print(f"{sec:2d}s  bolitas dentro: {int((~frames[f][3]).sum()):4d}  "
                  f"total: {frames[f][4]:5d}  "
                  f"escapes hasta aquí: {sum(1 for e in escapes if e < sec):4d}  "
                  f"rebotes: {sum(1 for b in bounces if b[0] < sec):5d}")
        return

    out = Path(args.salida or default_out)
    r = Renderer(frames, bounces)
    if args.preview is not None:
        png = out.with_suffix(f".preview-{args.preview:g}s.png")
        r.frame(args.preview).save(png)
        print(png)
        return

    tmp_dir = ROOT / "out" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_out = tmp_dir / out.name
    wav = tmp_out.with_suffix(".wav")
    render_audio(bounces, escapes, wav)

    n_frames = int(DURATION * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav), "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        str(tmp_out),
    ], stdin=subprocess.PIPE)
    for i in range(n_frames):
        ff.stdin.write(r.frame(i / FPS).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg falló")
    wav.unlink(missing_ok=True)
    tmp_out.replace(out)
    print(f"Listo: {out}")


if __name__ == "__main__":
    main()
