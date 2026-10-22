# Neon Keys · stack para videos verticales

Código con el que se hacen los videos de **Neon Keys** (piano "falling notes", datos curiosos, bolitas,
3D, pixel art) y de **Cineclub Forever** (collage de papel, motion graphics). Todo sale en 1080×1920 para TikTok.

Casi todo se hace con **Claude Code**: se le pide el video y él escribe o corre el código. Lo guían
`CLAUDE.md` (cómo está armado el proyecto), `RULES.md` (reglas de trabajo) y los skills de `.claude/skills/`.
Las decisiones técnicas y su porqué están en `docs/ADR.md`, y las reglas de TikTok en `docs/TIKTOK.md`.

## Stack

| Herramienta | Qué es | Para qué se usa |
|---|---|---|
| Claude Code | asistente de IA para programar, en la terminal | escribe y corre todo el código |
| Python 3.13 | lenguaje | 2D, audio, música |
| Node.js | entorno para correr JavaScript | 3D y motion graphics |
| ffmpeg / ffprobe | programa de línea de comandos | une cuadros y audio en .mp4 y revisa que el video esté sano |
| Flask | framework web de Python | web local para ver videos e ideas (`app.py`) |
| mido | librería de Python | lee los MIDI |
| Pillow | librería de Python para imágenes | dibuja cada cuadro 2D |
| NumPy | librería de Python de cálculo | efectos y síntesis de audio |
| TinySoundFont + FluidR3 GM | librería de Python + soundfont | convierte el MIDI en audio de piano |
| Three.js | librería de JavaScript para 3D | piano 3D, partículas, intro con lluvia |
| Rapier 3D | motor de física (JavaScript) | rebotes reales de las bolitas |
| Puppeteer + Chrome | librería de Node.js para controlar Chrome | graba las escenas 3D cuadro por cuadro |
| HyperFrames + GSAP | video con HTML + librería de animación | tipografía y recortes (Cineclub) |
| Remotion + React | framework de video con React | caricatura rubber hose (en prueba) |
| Piper / Kokoro | modelos de texto a voz que corren en la compu | narración (opcional) |

## Instalación

Necesitas Python 3.12 o 3.13, Node.js 20 o más, ffmpeg y Google Chrome.

```bash
# Python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install --no-deps tinysoundfont

# 3D
cd escenas3d && npm install && cd ..

# Remotion (solo si vas a usar la caricatura)
cd remotion && npm install && cd ..
```

En Mac, ffmpeg sale de evermeet.cx (binario listo, sin compilar) o de `brew install ffmpeg`. En Windows y
Linux, de ffmpeg.org.

**Ojo:** el proyecto se hizo en macOS y usa las fuentes del sistema Futura y Avenir Next. En otro sistema hay
que cambiarlas por otras (por ejemplo Montserrat y Lato, que ya vienen en `marcas/cineclub-forever/fuentes/`).

## Primer video

```bash
# Un cuadro de prueba (rápido)
.venv/bin/python neon_keys.py midi/marcha-turca.mid --titulo "Marcha Turca" --preview 20

# Video completo de 80 s → out/videos/
.venv/bin/python neon_keys.py midi/marcha-turca.mid --titulo "Marcha Turca" --subtitulo "Mozart" --duracion 73.3
```

Los comandos de los demás formatos (3D, bolitas, collage) están en `CLAUDE.md`.

## Qué NO viene en este repo

- **Videos terminados, ideas y personajes** (`out/`): ese contenido es del canal.
- **Modelos de voz** (`modelos/voz/`), unos 235 MB. Se bajan aparte: Piper `es_MX-ald-medium` y
  `es_MX-claude-high` (huggingface.co/rhasspy/piper-voices) y Kokoro v1.0 int8 (github.com/thewh1teagle/kokoro-onnx).
- **Recortes de carteles de "Temporada de Terror"**: son imágenes con derechos. La composición
  (`collage/cineclub-terror/hf/index.html`) está como ejemplo, pero no corre sin sus imágenes.
- **Personajes del podcast** (`podcast.py`, `podcast_set.py`): el código está, pero las imágenes y las voces no.
- **Audio ya generado** (.wav): se vuelve a crear corriendo los scripts.
- **Algunos skills**:
  - Remotion (`remotion-*`): `npx skills add remotion-dev/skills`.
  - `paper-collage-film` y `editorial-film-edit`: no van porque su licencia no está clara. Hay que conseguirlos con su autor.
  - Las herramientas compiladas del collage (`encode`, `extract`, `greenkey`, `mux`) se arman con los
    `.swift` de `paper-collage-film`.

## Licencias

- Skills incluidos: licencia MIT de sus autores. Charlie Hills (pack de motion, licencia en `brand-intake/`),
  LottieFiles (`motion-design`) y Gamezxz (`pixel-art-studio`).
- Soundfont FluidR3 GM: MIT. Fuentes de `marcas/` y `collage/`: SIL Open Font License.
- MIDIs: dominio público (Mutopia Project) o arreglos propios (`arreglos/`).
- Los logos y la identidad de **Neon Keys** y **Cineclub Forever** son de sus dueños: no los uses en tus videos.
