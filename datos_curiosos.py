#!/usr/bin/env python3
"""Neon Keys · videos de "¿Sabías qué?" con subtítulos animados y música de fondo.

La voz en off se agrega después en TikTok, por eso la música va baja.
Las escenas se definen en SCENES; las palabras entre *asteriscos* se resaltan en magenta.

Uso:
    .venv/bin/python datos_curiosos.py                 # genera out/videos/datos/dato-la-bamba.mp4
    .venv/bin/python datos_curiosos.py --preview 6     # solo un cuadro PNG en t=6s
    .venv/bin/python datos_curiosos.py --narracion ~/Downloads/la-bamba-narration.mp3
                                                       # con voz → out/videos/datos/dato-la-bamba-voz.mp4
"""

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from neon_keys import (BRAND_GLOW, COLOR_LEFT, COLOR_RIGHT, FONT_BOLD, FONT_TEXT, FPS, H, W,
                       font, glow_text, make_background, make_brand_layer)

ROOT = Path(__file__).resolve().parent

# --- Contenido del video ---
TAG = "¿SABÍAS QUÉ?"
DISC_LABEL = ("LA BAMBA", "SON JAROCHO")
# Una frase por escena. Sin narración, los tiempos se calculan según el número de palabras;
# con --narracion se usan NARRATION_TIMES para que cada subtítulo entre junto con la voz.
SCRIPT = [
    "La canción mexicana *más famosa* del mundo…",
    "…la grabó alguien que *no hablaba español*",
    "*Ritchie Valens*, un chavo de *17 años* de Los Ángeles, en *1958*",
    "Se aprendió la letra *de oído*, sílaba por sílaba",
    "Y ni siquiera era el éxito: salió como *lado B* del disco *Donna*",
    "Pero La Bamba ya existía desde hacía *siglos*: es un *son jarocho* de *Veracruz*",
    "Se tocaba en *bodas*, y en *1790* ya sonaba en un teatro de la Ciudad de México",
    "En 1959 Valens murió en un accidente de avión: *“el día que murió la música”*",
    "Y en 1987 *Los Lobos* la llevaron al *#1* en Estados Unidos e Inglaterra… *en español*",
    "*Escúchala en piano* en mi perfil",
]
FIRST_START = 0.5
SCENE_GAP = 0.1
SECONDS_PER_WORD = 0.33   # ritmo de lectura cómodo para la voz en off
MIN_SCENE = 3.4


# Inicio y fin de cada frase dentro del audio de narración (medido con silencedetect).
NARRATION_TIMES = [
    (0.00, 2.57), (3.07, 5.25), (5.85, 11.53), (12.07, 15.02), (15.58, 19.44),
    (20.16, 24.82), (25.28, 30.84), (31.39, 37.66), (38.24, 45.18), (45.77, 47.65),
]
VOICE_OFFSET = 0.5     # la voz entra medio segundo después del inicio del video
TAIL = 1.5             # segundos después de la última frase


def build_scenes(script):
    scenes, t = [], FIRST_START
    for text in script:
        words = len(text.split())
        dur = max(MIN_SCENE, 1.0 + SECONDS_PER_WORD * words)
        scenes.append((t, t + dur, text, WORD_DELAY))
        t += dur + SCENE_GAP
    return scenes, round(scenes[-1][1] + 0.4, 2)


def build_scenes_from_voice(script, times):
    """Cada subtítulo entra con su frase y se queda hasta que empieza la siguiente.
    Las palabras aparecen al ritmo en que se dicen."""
    scenes = []
    for i, (text, (v0, v1)) in enumerate(zip(script, times)):
        start = v0 + VOICE_OFFSET - 0.1
        end = (times[i + 1][0] + VOICE_OFFSET - 0.15) if i + 1 < len(times) else v1 + VOICE_OFFSET + TAIL
        delay = max(0.12, min(0.45, (v1 - v0) * 0.85 / len(text.split())))
        scenes.append((start, end, text, delay))
    return scenes, round(times[-1][1] + VOICE_OFFSET + TAIL, 2)


MUSIC = ROOT / "out" / "videos" / "piano" / "la-bamba.mp4"
MUSIC_START = 8.2      # entra justo en "Para bailar la bamba"
MUSIC_VOLUME = 0.55    # baja, para que se escuche la voz en off
MUSIC_UNDER_VOICE = 0.18   # con narración, la música va todavía más baja
BPM = 147              # el anillo del disco late al ritmo
OUTPUT = ROOT / "out" / "videos" / "datos" / "dato-la-bamba.mp4"

# --- Layout ---
TAG_Y = 330
PROGRESS_Y = 240
DISC_C = (W // 2, 720)
DISC_R = 230
SUB_CENTER_Y = 1235
SUB_MAX_W = 940
SUB_LINE_H = 98
WORD_DELAY = 0.17      # segundos entre palabra y palabra (sin narración)
WORD_IN = 0.18         # duración de la animación de entrada de cada palabra

WHITE = (255, 255, 255)
HIGHLIGHT = (255, 120, 230)


def make_disc():
    """Disco de vinil (RGBA) con etiqueta; se rota cuadro a cuadro."""
    size = DISC_R * 2 + 4
    disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(disc)
    c = size / 2
    d.ellipse([c - DISC_R, c - DISC_R, c + DISC_R, c + DISC_R], fill=(14, 10, 22, 255))
    for r in range(100, DISC_R - 6, 7):
        d.ellipse([c - r, c - r, c + r, c + r], outline=(42, 34, 64, 255), width=1)
    # Reflejo que hace visible el giro.
    d.pieslice([c - DISC_R + 8, c - DISC_R + 8, c + DISC_R - 8, c + DISC_R - 8], 200, 235,
               fill=(70, 60, 100, 120))
    label_r = 92
    d.ellipse([c - label_r, c - label_r, c + label_r, c + label_r], fill=COLOR_LEFT + (255,))
    d.text((c, c - 18), DISC_LABEL[0], font=font(FONT_BOLD, 30, 2), fill=WHITE, anchor="mm")
    d.text((c, c + 20), DISC_LABEL[1], font=font(FONT_TEXT, 17, 0), fill=WHITE, anchor="mm")
    d.ellipse([c - 9, c - 9, c + 9, c + 9], fill=(8, 4, 22, 255))
    return disc


def parse_words(text):
    """'a *b c* d' → [('a', False), ('b', True), ('c', True), ('d', False)]."""
    words, hot = [], False
    for raw in text.split():
        # El asterisco de cierre puede ir antes de la puntuación: "*Valens*,"
        starts, ends = raw.startswith("*"), raw.rstrip(".,:;!?…”\"").endswith("*")
        word = raw.replace("*", "")
        if starts:
            hot = True
        words.append((word, hot))
        if ends:
            hot = False
    return words


def layout(words, fnt, center_y=SUB_CENTER_Y):
    """Acomoda palabras en líneas centradas; devuelve [(x, y, palabra, resaltada)]."""
    space = fnt.getlength(" ")
    lines, cur, cur_w = [], [], 0
    for w, hot in words:
        ww = fnt.getlength(w)
        if cur and cur_w + space + ww > SUB_MAX_W:
            lines.append((cur, cur_w))
            cur, cur_w = [], 0
        cur_w += (space if cur else 0) + ww
        cur.append((w, hot, ww))
    if cur:
        lines.append((cur, cur_w))
    top = center_y - (len(lines) - 1) * SUB_LINE_H / 2
    placed = []
    for li, (line, lw) in enumerate(lines):
        x = (W - lw) / 2
        for w, hot, ww in line:
            placed.append((x, top + li * SUB_LINE_H, w, hot))
            x += ww + space
    return placed


def ease_out(x):
    return 1 - (1 - x) ** 3


class DatoRenderer:
    def __init__(self, scenes, duration):
        self.duration = duration
        self.bg = make_background()
        self.brand = make_brand_layer()
        self.disc = make_disc()
        self.sub_font = font(FONT_BOLD, 76, 2)
        self.scenes = [(s, e, layout(parse_words(txt), self.sub_font), d) for s, e, txt, d in scenes]
        self.tag = glow_text(Image.new("RGB", (W, H)), (W / 2, TAG_Y), TAG, font(FONT_BOLD, 64, 2),
                             WHITE, BRAND_GLOW, radius=16, spacing=0)

    def frame(self, t):
        img = self.bg.copy()
        glow = Image.new("RGB", (W, H))
        core = Image.new("RGB", (W, H))
        gd, cd = ImageDraw.Draw(glow), ImageDraw.Draw(core)

        # Anillo neón que late con el ritmo.
        beat = (t * BPM / 60) % 1
        pulse = 1 - ease_out(min(1, beat * 2))
        r = DISC_R + 10 + 10 * pulse
        cx, cy = DISC_C
        ring = tuple(int(c * (0.55 + 0.45 * pulse)) for c in COLOR_RIGHT)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring, width=14)
        cd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=tuple(min(255, c + 60) for c in ring), width=4)

        # Barra de progreso: ayuda a que la gente se quede hasta el final.
        x0, x1, y = 160, W - 160, PROGRESS_Y
        ImageDraw.Draw(img).rounded_rectangle([x0, y - 3, x1, y + 3], radius=3, fill=(40, 24, 70))
        xp = x0 + (x1 - x0) * min(1.0, t / self.duration)
        if xp > x0 + 6:
            gd.rounded_rectangle([x0, y - 6, xp, y + 6], radius=6, fill=COLOR_LEFT)
            cd.rounded_rectangle([x0, y - 3, xp, y + 3], radius=3, fill=HIGHLIGHT)

        # Subtítulos palabra por palabra.
        for start, end, words, delay in self.scenes:
            if not (start <= t < end + 0.01):
                continue
            fade_out = min(1.0, (end - t) / 0.3)
            for i, (x, y, w, hot) in enumerate(words):
                k = (t - start - i * delay) / WORD_IN
                if k <= 0:
                    continue
                a = ease_out(min(1.0, k)) * fade_out
                dy = 22 * (1 - ease_out(min(1.0, k)))
                core_c = HIGHLIGHT if hot else WHITE
                glow_c = COLOR_LEFT if hot else COLOR_RIGHT
                cd.text((x, y + dy), w, font=self.sub_font, anchor="lm",
                        fill=tuple(int(c * a) for c in core_c))
                gd.text((x, y + dy), w, font=self.sub_font, anchor="lm",
                        fill=tuple(int(c * a * 0.9) for c in glow_c))

        small = glow.resize((W // 3, H // 3), Image.BILINEAR)
        halo = small.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
        halo = ImageChops.add(halo, halo)
        img = ImageChops.screen(img, halo)

        # Disco girando (33⅓ rpm ≈ 200°/s).
        rot = self.disc.rotate(-t * 200, resample=Image.BICUBIC)
        img.paste(rot, (cx - rot.width // 2, cy - rot.height // 2), rot)

        img = ImageChops.lighter(img, core)
        tag_a = min(1.0, t / 0.4)
        img = ImageChops.screen(img, Image.blend(Image.new("RGB", (W, H)), self.tag, tag_a))
        img = ImageChops.screen(img, self.brand)

        if t < 0.4:
            img = Image.blend(Image.new("RGB", (W, H)), img, t / 0.4)
        if t > self.duration - 0.4:
            img = Image.blend(Image.new("RGB", (W, H)), img, max(0.0, (self.duration - t) / 0.4))
        return img


def main():
    ap = argparse.ArgumentParser(description="Genera un video de dato curioso estilo Neon Keys.")
    ap.add_argument("--preview", type=float, default=None)
    ap.add_argument("--narracion", default=None,
                    help="audio de voz (mp3/m4a/wav); sincroniza los subtítulos con NARRATION_TIMES")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()

    voice = Path(args.narracion).expanduser() if args.narracion else None
    if voice and not voice.exists():
        sys.exit(f"No encuentro la narración: {voice}")
    if voice:
        scenes, duration = build_scenes_from_voice(SCRIPT, NARRATION_TIMES)
        default_out = OUTPUT.with_name(OUTPUT.stem + "-voz.mp4")
    else:
        scenes, duration = build_scenes(SCRIPT)
        default_out = OUTPUT
    out = Path(args.salida) if args.salida else default_out

    r = DatoRenderer(scenes, duration)
    if args.preview is not None:
        png = out.with_suffix(f".preview-{args.preview:g}s.png")
        r.frame(args.preview).save(png)
        print(png)
        return

    if not MUSIC.exists():
        sys.exit(f"Falta la música: {MUSIC} (genera primero el video de La Bamba)")

    music_in = ["-ss", str(MUSIC_START), "-t", str(duration), "-i", str(MUSIC)]
    fade = f"afade=t=in:d=0.3,afade=t=out:st={duration - 1}:d=1"
    if voice:
        delay_ms = int(VOICE_OFFSET * 1000)
        audio = ["-i", str(voice), "-filter_complex",
                 f"[1:a]volume={MUSIC_UNDER_VOICE},{fade}[m];"
                 f"[2:a]adelay={delay_ms}:all=1,volume=1.0[v];"
                 f"[m][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
                 "-map", "0:v", "-map", "[a]"]
    else:
        audio = ["-map", "0:v", "-map", "1:a", "-af", f"volume={MUSIC_VOLUME},{fade}"]

    tmp_dir = ROOT / "out" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_out = tmp_dir / out.name
    n_frames = int(duration * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        *music_in, *audio,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(duration), "-movflags", "+faststart",
        str(tmp_out),
    ], stdin=subprocess.PIPE)
    for i in range(n_frames):
        ff.stdin.write(r.frame(i / FPS).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg falló")
    tmp_out.replace(out)
    print(f"Listo: {out}")


if __name__ == "__main__":
    main()
