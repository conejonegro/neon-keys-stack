# Neon Keys

Generador de videos verticales de piano "falling notes" para el canal de TikTok **Neon Keys**.
Entra un MIDI y sale un `.mp4` 1080×1920 listo para subir, con estética neón/synthwave.

**El canal no es solo de piano:** también datos curiosos y científicos ("¿Sabías que el pulpo tiene 3
corazones?"), animaciones como las bolitas, etc., todo con el mismo estilo neón. La marca general es el
monograma **NK** (N cian + K magenta); el teclado identifica solo a los videos de piano.
Foto de perfil elegida: NK dentro de un átomo neón, **sin contorno** (`avatar.py` → `marca_atomo(False)`,
copia en `out/avatar-tiktok.png`).

Reglas de trabajo: @RULES.md
Decisiones técnicas y su porqué: `docs/ADR.md`
Reglas de TikTok / Creator Rewards (con fuentes): `docs/TIKTOK.md`
Para generar un video completo, usar el skill `/render-video`.
Para personajes y escenas pixel art, usar el skill `pixel-art-studio` (método y revisión; ADR-012).

**Marcas y motion graphics (ADR-018, ADR-019):** cada marca tiene su carpeta en `marcas/<marca>/` con
`brand.md`, `MOTION.md` (colores, fuentes, tiempos, reglas de movimiento), `marca.json` (los mismos valores para
el código), `logo.png` y, si hace falta, `fuentes/`. Marcas: `neon-keys` (la de siempre, por defecto) y
`cineclub-forever` (cine, borrador sin aprobar). Si no está claro para qué marca es un video, preguntar.
Antes de diseñar, generar o animar cualquier cosa, leer completos `MOTION.md` y `brand.md` de esa marca. Cada
color, fuente y tiempo sale de ahí; nunca mezclar el estilo de dos marcas.
El archivo fija el look, no la ambición: cuando se pida "con todo", ir con todo. Si algo no está cubierto,
preguntar en vez de elegir. Al terminar, revisar los cuadros contra `MOTION.md`, corregir y solo entonces
enseñarlos. Skills de motion en `.claude/skills/` (pack de charlie947 + `motion-design` de LottieFiles);
HyperFrames ya se probó (ADR-021, en `collage/cineclub-terror/`): sirve para tipografía y recortes; para 3D
seguir con `escenas3d/grabar.js`.

## Cómo se corre

```bash
# Línea de comandos
.venv/bin/python neon_keys.py midi/marcha-turca.mid --titulo "Marcha Turca" --subtitulo "Mozart" --duracion 73.3

# Solo un cuadro PNG para revisar el look (rápido)
.venv/bin/python neon_keys.py midi/marcha-turca.mid --titulo "Marcha Turca" --preview 20

# Web local → http://127.0.0.1:5050
.venv/bin/python app.py

# Piano 3D (Three.js, ADR-011): 1) notas + audio  2) grabar con Chrome invisible
.venv/bin/python escenas3d/preparar.py midi/marcha-turca.mid --inicio 0 --duracion 10
cd escenas3d && node grabar.js escenas/prueba.html out/pruebas/marcha-turca-3d.mp4 \
  --datos out/.tmp/marcha-turca-3d.json --audio out/.tmp/marcha-turca-3d.wav   # --preview T = un PNG

# Piano 3D con partículas, título y cierre (ADR-016)
.venv/bin/python escenas3d/preparar.py midi/son-de-la-negra.mid --inicio 0 --duracion 63.26 \
  --titulo "Son de la Negra" --subtitulo "Tradicional mexicana" --cierre "¡Viva México! Sígueme para más"
cd escenas3d && node grabar.js escenas/piano.html out/videos/son-de-la-negra-3d.mp4 \
  --datos out/.tmp/son-de-la-negra-3d.json --audio out/.tmp/son-de-la-negra-3d.wav

# Bolitas 3D en la esfera (ADR-017): física → sonido + textos → grabar
cd escenas3d && node rebotes3d.mjs ../out/.tmp/rebotes-esfera-3d.json   # --stats = solo números
cd .. && .venv/bin/python escenas3d/rebotes3d_sonido.py out/.tmp/rebotes-esfera-3d.json out/.tmp/rebotes-esfera-3d.wav
cd escenas3d && node grabar.js escenas/rebotes.html out/videos/rebotes-esfera-3d.mp4 \
  --datos out/.tmp/rebotes-esfera-3d.json --audio out/.tmp/rebotes-esfera-3d.wav
```

El HTML de la escena no se anima abriéndolo en Chrome: necesita el servidor de `grabar.js`, que le pide
cada cuadro con `window.dibujar(t)`. Lo que se mira es el `.mp4`.

Opciones de `neon_keys.py`: `--titulo`, `--subtitulo`, `--inicio` (segundo de la canción; por defecto la
primera nota), `--duracion` (segundos de música; por defecto 62), `--salida`, `--soundfont`, `--preview T`.

### Calcular la duración

`duración total del video = LEAD_IN (≈3.24 s) + --duracion + OUTRO (3.5 s)`

Para un video de T segundos: `--duracion = T − 6.74`. Ejemplos: 20 s → `13.3`, 80 s → `73.3`.

## Estructura

```
neon_keys.py          generador: MIDI → notas → cuadros (Pillow) + audio (TinySoundFont) → ffmpeg
datos_curiosos.py     videos "¿Sabías qué?": subtítulos animados + disco + música baja (voz en off en TikTok)
rebotes.py            bolitas que rebotan en un anillo con salida; cada rebote = nota; glitch final (--version corto|largo)
ajolote.py            dato curioso del ajolote en pixel art 8-bit arcade neón: escena, HUD, subtítulos y
                      música chiptune sintetizados con código (sin IA ni samples) → out/videos/dato-ajolote.mp4
sprites.py            personajes pixel art 16-bit con partes animables; `sprites.py ajolote` → hoja para
                      aprobar en out/personajes/
pixel_ia.py           personaje pixel art hecho con IA (en out/personajes/ia/) → fondo fuera, cuadrícula real,
                      paleta fija (skill pixel-art-studio) + gestos de boca; `pixel_ia.py alan` →
                      out/personajes/alan-pixel.png. Cada personaje se configura en `PERSONAJES`
podcast.py            podcast de fútbol pixel art: Alan y Luis caminan de lado (tiras de pixel_ia.py) sobre
                      escenario synthwave con estadio; globos de texto, boca al hablar, chiptune + silbatazo
                      (guion en `DIALOGO`) → out/pruebas/podcast-*.mp4
marcas/               una carpeta por marca: brand.md, MOTION.md, marca.json, logo.png, fuentes/ (ADR-019)
avatar.py             imágenes de perfil 1080×1080 → out/avatares/ (marca-* generales, piano-* guardadas)
collage/              collage de papel rasgado (skill paper-collage-film, ADR-020): un proyecto por pieza.
                      cineclub-intro/: comp/scenes.js (escenas verticales), comp/grade_cineclub.js (color de marca),
                      preparar_recortes.py (dominio público → cutouts/), audio/score.html, script.md (tiempos)
                      cineclub-terror/: "Temporada de Terror" con HyperFrames (ADR-021): preparar.py (recortes,
                      logo sin fondo, texturas), hf/index.html (composición GSAP), audio/terror.py, script.md
                      musica/: piezas de fondo solo audio (tripi.py, terror.py con el soundfont, triphop.py)
arreglos/             arreglos propios que generan MIDIs (la_bamba.py, son_de_la_negra.py)
escenas3d/            formato piano 3D con Three.js (ADR-011), dependencias npm propias (`.npmrc` fija el
                      registro público). preparar.py: MIDI → notas JSON + WAV (reusa neon_keys.py);
                      grabar.js: Chrome invisible (--use-angle=gl) cuadro por cuadro → ffmpeg;
                      escenas/prueba.html: teclado 3D, notas desde el horizonte, sol retro, piso shader.
                      escenas/piano.html: lo mismo + notas que estallan en partículas, título, marca y cierre
                      (ADR-016; preparar.py --titulo --subtitulo --cierre)
                      Bolitas 3D (ADR-015): bolitas.mjs (física Rapier → JSON) + bolitas_sonido.py (golpes →
                      WAV en escala) + escenas/bolitas.html; se graba con grabar.js --datos/--audio
                      Bolitas en esfera (ADR-017): rebotes3d.js (física compartida Node/escena, tiempos y
                      glitch en CFG) + rebotes3d.mjs (golpes → JSON) + rebotes3d_sonido.py (música electrónica
                      y textos) + escenas/rebotes.html
                      Intro "¿SABÍAS QUÉ?" (ADR-018): intro.py (letreros, título, tiempos y música) +
                      escenas/intro.html (calle mojada con Reflector, lluvia, cámara que sube, glitch)
remotion/             formato "caricatura" con Remotion (React + SVG, ADR-014): personaje rubber hose con líneas que
                      "hierven" (src/rubberhose/), guion en guion.json, sonido.py (balbuceo + base), render.sh
                      (cuadros + ffmpeg propio; el ffmpeg de Remotion no corre en macOS 12)
app.py                servidor Flask de la web local (puerto 5050, solo 127.0.0.1); agrupa los videos por
                      tipo según el prefijo del archivo: `dato-*` = datos curiosos, `rebotes-*` = bolitas, `podcast-*` = podcast, `caricatura-*` = caricatura,
                      el resto = piano (`VIDEO_TYPES`). Un formato nuevo necesita su prefijo ahí.
web/index.html        la página (HTML + JS sin frameworks)
midi/                 canciones .mid (kebab-case, dominio público)
soundfonts/           FluidR3Mono_GM.sf3 (piano)
out/videos/           videos terminados (los que se suben)
out/pruebas/          pruebas, teasers y formatos en ensayo (la web los marca con 🧪). Se guardan aquí los
                      `--hasta`, los `-prueba` y las pruebas 3D; al aprobar una versión larga va a out/videos/
out/videos.json       por video: titulo, descripcion, hashtags, ia, estado (listo/programado/publicado),
                      fecha, nota. La web lo muestra con botón "Copiar"; lo actualiza la web al marcar estados
out/ideas.json        ideas para próximos videos (tipo, gancho, dato, escena, sonidos, estado idea/hecho) y
                      `plantilla_prompt`: prompt base para la IA de video externa (estilo 8-bit neón arcade,
                      sin texto ni voz). La web arma el prompt = plantilla + escena + sonidos
out/por-probar.json   skills, librerías y herramientas que queremos probar (tipo skill/libreria/otro, enlace,
                      nota, estado pendiente/probado). Sección "Por probar" de la web
out/.tmp/             render en curso; se mueve a out/videos/ u out/pruebas/ solo al terminar
out/.preview/         PNGs de vista previa de la web
.venv/                entorno de Python
```

## Entorno (importante)

- **macOS 12 Monterey, Intel (x86_64).** Homebrew ya no tiene binarios para esta versión y compila todo
  desde fuente (ffmpeg tardaba más de una hora). No usar `brew` para dependencias pesadas.
- **ffmpeg / ffprobe 9.0.2**: binarios estáticos de evermeet.cx en `~/.local/bin`.
- **Python 3.13** en `.venv`. Para reinstalar:
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install numpy pillow mido flask
  .venv/bin/pip install --no-deps tinysoundfont   # su dependencia pyaudio no compila aquí y no se usa
  ```
- Fuentes del sistema: Futura (Bold, índice 2 del .ttc) y Avenir Next.
- **Voz (texto a voz, en prueba):** entorno aparte `.venv-voz` con Python 3.12, porque `onnxruntime` no tiene
  versión para Python 3.13 en Mac Intel (la última que sirve aquí es la 1.19.2). Se creó con
  `.venv/bin/uv venv --python 3.12 .venv-voz` (uv baja un Python ya armado, sin compilar) y
  `uv pip install onnxruntime==1.19.2 piper-tts soundfile` + `kokoro-onnx --no-deps espeakng-loader phonemizer-fork`.
  Modelos en `modelos/voz/`: Piper `es_MX-ald-medium` (Unlicense) y `es_MX-claude-high` (Apache 2.0), Kokoro
  v1.0 int8 (Apache 2.0, voces `em_alex` y `em_santa`). Todos permiten uso comercial.

## Parámetros clave (`neon_keys.py`)

| Constante | Valor | Qué controla |
|---|---|---|
| `W, H, FPS` | 1080, 1920, 30 | Formato TikTok |
| `KEYS_TOP` | 1360 | Línea donde las notas tocan el teclado |
| `FALL_SPEED` | 420 px/s | Velocidad de caída (define `LEAD_IN`) |
| `OUTRO` | 3.5 s | Cierre con logo |
| `COLOR_RIGHT` / `COLOR_LEFT` | cian / magenta | Mano derecha / izquierda |

Mano derecha = primera pista del MIDI con notas; izquierda = la segunda. Si solo hay una pista, se
separa por altura (Do central = 60).

## Videos hechos

| Archivo | Canción | Tramo | Duración | Notas |
|---|---|---|---|---|
