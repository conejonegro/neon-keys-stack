# Neon Keys · stack para videos verticales

Código con el que se hacen los videos de **Neon Keys** (piano "falling notes", datos curiosos, bolitas,
3D, pixel art, beats explicados) y de **Cineclub Forever** (collage de papel, motion graphics). Todo sale en
1080×1920 para TikTok. La idea es que lo bajes, lo instales y **armes tu propia marca** encima (ver
[Crea tu marca](#crea-tu-marca)).

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
| Surge XT + DawDreamer | sinte de estudio gratis + librería para tocarlo desde Python | supersaw y acid de los beats de trance, psytrance y ocarina (opcional) |

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

# Surge XT (solo para trance.py, psytrance.py, ocarina.py, saria.py, firestarter.py, sandstorm.py)
python3.12 -m venv .venv-synth
.venv-synth/bin/pip install dawdreamer numpy
```

Para Surge XT baja el zip "pluginsonly" de surge-synthesizer.github.io y pon los `.vst3` en `plugins/surge-xt/`.
Los presets (`.fxp`) que usa cada script se bajan del repositorio de Surge (`resources/data/patches_factory/`) a
`plugins/surge-xt/patches/`. Detalles en `docs/ADR.md` (ADR-026).

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

Los comandos de los demás formatos (3D, bolitas, collage, beats) están en `CLAUDE.md`. O más fácil: abre
Claude Code en la carpeta y pídele el video.

## Crea tu marca

Cada marca vive en su carpeta, `marcas/<tu-marca>/`, y Claude Code la lee antes de diseñar o animar cualquier cosa.
Así nunca se mezclan los estilos. Ejemplos: `marcas/neon-keys/` (neón, piano) y `marcas/cineclub-forever/`
(collage de cine).

1. **Junta de 3 a 5 imágenes** de lo que te gusta: capturas de videos, tu logo, posts, paletas. Mete tu logo
   en PNG si ya tienes.
2. **Abre Claude Code** en la carpeta del proyecto (`claude`) y escribe `/brand-intake`. Te hace una entrevista
   corta (nombre, qué haces, a quién le hablas, qué sensación quieres y qué no harías nunca) y le pasas las
   imágenes.
3. **Revisa lo que crea** en `marcas/<tu-marca>/`:

   | Archivo | Qué es |
   |---|---|
   | `brand.md` | quién eres, qué haces y a quién le hablas |
   | `MOTION.md` | tus colores, fuentes, tiempos y reglas de movimiento (incluidas 5 cosas que tu marca nunca hace) |
   | `marca.json` | los mismos valores, para el código |
   | `logo.png`, `fuentes/` | tu logo y tus fuentes (usa fuentes con licencia libre, como las de Google Fonts) |

4. **Agrega tu marca a `CLAUDE.md`**, en la lista de marcas, y si quieres que sea la de por defecto, dilo ahí.
5. **Pide una prueba corta**: "hazme una prueba de 10 s de [idea] para mi marca". Revisa cuadros sueltos, corrige
   el `MOTION.md` con lo que no te guste y después pide el video completo.

**Ejemplo de un look distinto al neón:** `escenas3d/escenas/torta.html` + `escenas3d/torta.py` es una escena 3D
de día con paleta tapatía, contorno de caricatura, un personaje de bloques y etiquetas con línea y puntito
("así se arma una torta ahogada"). Sirve para ver cómo se cambia el look completo sin tocar `grabar.js`:

```bash
.venv/bin/python escenas3d/torta.py
cd escenas3d && node grabar.js escenas/torta.html out/pruebas/torta-prueba.mp4 \
  --datos out/.tmp/torta-ahogada.json --audio out/.tmp/torta-ahogada.wav
```

`docs/BITACORA.md` no viene: Claude Code la crea en tu primera sesión y le agrega una entrada al final de cada una.

## Qué NO viene en este repo

- **Videos terminados, ideas y personajes** (`out/`): ese contenido es del canal.
- **Modelos de voz** (`modelos/voz/`), unos 235 MB. Se bajan aparte: Piper `es_MX-ald-medium` y
  `es_MX-claude-high` (huggingface.co/rhasspy/piper-voices) y Kokoro v1.0 int8 (github.com/thewh1teagle/kokoro-onnx).
- **Recortes de carteles de "Temporada de Terror"**: son imágenes con derechos. La composición
  (`collage/cineclub-terror/hf/index.html`) está como ejemplo, pero no corre sin sus imágenes.
- **Personajes del podcast** (`podcast.py`, `podcast_set.py`): el código está, pero las imágenes y las voces no.
- **Audio ya generado** (.wav): se vuelve a crear corriendo los scripts.
- **Surge XT** (`plugins/`): se baja aparte (ver Instalación).
- **Otras marcas del dueño** (diseño, tienda): son privadas.
- **Algunos skills**:
  - Remotion (`remotion-*`): `npx skills add remotion-dev/skills`.
  - `paper-collage-film` y `editorial-film-edit`: no van porque su licencia no está clara. Hay que conseguirlos con su autor.
  - Las herramientas compiladas del collage (`encode`, `extract`, `greenkey`, `mux`) se arman con los
    `.swift` de `paper-collage-film`.

## Licencias

- Skills incluidos: licencia MIT de sus autores. Charlie Hills (pack de motion, licencia en `brand-intake/`),
  LottieFiles (`motion-design`) y Gamezxz (`pixel-art-studio`).
- Soundfont FluidR3 GM: MIT. Fuentes de `marcas/`, `collage/` y `escenas3d/fuentes/`: SIL Open Font License.
- MIDIs: dominio público (Mutopia Project) o arreglos propios (`arreglos/`).
- Los logos y la identidad de **Neon Keys** y **Cineclub Forever** son de sus dueños: no los uses en tus videos.
