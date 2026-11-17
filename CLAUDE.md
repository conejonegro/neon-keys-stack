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
Qué se hizo cada sesión y qué quedó pendiente: `docs/BITACORA.md` (se crea en la primera sesión; agregar una entrada al terminar cada sesión)
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
cd escenas3d && node grabar.js escenas/prueba.html out/pruebas/piano/marcha-turca-3d.mp4 \
  --datos out/.tmp/marcha-turca-3d.json --audio out/.tmp/marcha-turca-3d.wav   # --preview T = un PNG

# Piano 3D con partículas, título y cierre (ADR-016)
.venv/bin/python escenas3d/preparar.py midi/son-de-la-negra.mid --inicio 0 --duracion 63.26 \
  --titulo "Son de la Negra" --subtitulo "Tradicional mexicana" --cierre "¡Viva México! Sígueme para más"
cd escenas3d && node grabar.js escenas/piano.html out/videos/piano/son-de-la-negra-3d.mp4 \
  --datos out/.tmp/son-de-la-negra-3d.json --audio out/.tmp/son-de-la-negra-3d.wav

# Bolitas 3D en la esfera (ADR-017): física → sonido + textos → grabar
cd escenas3d && node rebotes3d.mjs ../out/.tmp/rebotes-esfera-3d.json   # --stats = solo números
cd .. && .venv/bin/python escenas3d/rebotes3d_sonido.py out/.tmp/rebotes-esfera-3d.json out/.tmp/rebotes-esfera-3d.wav
cd escenas3d && node grabar.js escenas/rebotes.html out/videos/bolitas/rebotes-esfera-3d.mp4 \
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
                      música chiptune sintetizados con código (sin IA ni samples) → out/videos/datos/dato-ajolote.mp4
sprites.py            personajes pixel art 16-bit con partes animables; `sprites.py ajolote` → hoja para
                      aprobar en out/personajes/
pixel_ia.py           personaje pixel art hecho con IA (en out/personajes/ia/) → fondo fuera, cuadrícula real,
                      paleta fija (skill pixel-art-studio) + gestos de boca; `pixel_ia.py alan` →
                      out/personajes/alan-pixel.png. Cada personaje se configura en `PERSONAJES`
podcast.py            podcast de fútbol pixel art: Alan y Luis caminan de lado (tiras de pixel_ia.py) sobre
                      escenario synthwave con estadio; globos de texto, boca al hablar, chiptune + silbatazo
                      (guion en `DIALOGO`) → out/pruebas/podcast/podcast-*.mp4
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
                      Beat explicado (ADR-022): techno.py [--version largo|corto] (patrones 16 pasos + secciones con texto → golpes,
                      batería sintetizada a 132 BPM, guion de voz con tiempos) + escenas/techno.html
                      (secuenciador 3D que se llena capa por capa y se enrolla en una rueda en el drop);
                      techno_voz.py: pega una voz de IA (un solo audio) frase por frase, baja el beat al hablar
                      y mueve los subtítulos al ritmo de la voz (`--beat beat-trap-vacio` para el de trap)
                      Beat de trap: trap.py (808 afinado/saturado con glide, hats con redobles y tono, 140 BPM;
                      reusa la síntesis de techno.py; abre con un trap mal hecho que se frena con tape stop) +
                      escenas/trap.html (la escena del techno con capas de trap; drop con bocina neón, sin rueda)
                      Batería por niveles (ADR-024): punk.py [--kit standard|power|room] (The Kids Aren't Alright: tempo
                      por sección, batería/bajo del soundfont, guitarra Karplus-Strong + ampli) + escenas/punk.html
                      (pista tipo Guitar Hero con 5 carriles y el bombo como barra, contador, BPM, combo)
                      Beat de trance (ADR-030): trance.py (138 BPM, Re menor, gate, supersaw de Surge; corre en
                      .venv-synth; abre terminado y se frena con tape stop) + escenas/trance.html (escenario de
                      festival con láseres en el gancho y el drop)
                      Tributo a Zelda (ADR-028): ocarina.py [--version corta|completa] (ocarina sintetizada, lluvia,
                      truenos, beat y supersaw de Surge; corre en .venv-synth) + escenas/ocarina.html (ocarina
                      translúcida neón con Trifuerza, aldea con tormenta, cinta de botones L R X, cámara continua)
                      Beat de reguetón (ADR-023): reggaeton.py [--paleta lima|tropical|verde-morado] (dembow 3-3-2 a
                      95 BPM, rayón de disco al inicio) + escenas/reggaeton.html (paleta del JSON, tomas con inclinación
                      y barridos, bola disco en el drop)
remotion/             formato "caricatura" con Remotion (React + SVG, ADR-014): personaje rubber hose con líneas que
                      "hierven" (src/rubberhose/), guion en guion.json, sonido.py (balbuceo + base), render.sh
                      (cuadros + ffmpeg propio; el ffmpeg de Remotion no corre en macOS 12)
hardtechno.py         beat explicado de hard techno en un osciloscopio CRT (ADR-031): Pillow + numpy, sin 3D;
                      --preview T, --datos/--audio para la versión con voz de techno_voz.py
app.py                servidor Flask de la web local (puerto 5050, solo 127.0.0.1); agrupa los videos por
                      tipo según su subcarpeta (o, si está suelto, el prefijo del archivo): `dato-*` = datos curiosos, `rebotes-*` = bolitas, `podcast-*` = podcast, `caricatura-*` = caricatura, `beat-*` = beats explicados,
                      el resto = piano (`VIDEO_TYPES`). Un formato nuevo necesita su prefijo ahí.
web/index.html        la página (HTML + JS sin frameworks)
midi/                 canciones .mid (kebab-case, dominio público)
soundfonts/           FluidR3Mono_GM.sf3 (piano)
out/videos/           videos terminados (los que se suben), en una subcarpeta por tipo: piano/, beats/, datos/,
                      bolitas/ (la web toma el tipo de la carpeta; ver RULES.md 18)
out/pruebas/          pruebas, teasers y formatos en ensayo, por tipo como out/videos/ (más cineclub/, tienda/,
                      otros/; las voces siguen en pruebas/voces/). La web los marca con 🧪. Se guardan aquí los
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
| `marcha-turca.mp4` | Rondo alla Turca, Mozart | desde el inicio, 73.3 s | 1:20 | Al usuario le gustó mucho |
| `rey-de-la-montana.mp4` | En la gruta del rey de la montaña, Grieg | `--inicio 131.6 --duracion 13.3` | 0:20 | Borrado (11-oct): no le gustó |
| `la-bamba.mp4` | La Bamba, tradicional mexicana | arreglo propio (`arreglos/la_bamba.py`), `--duracion 63.26` | 1:10 | Melodía tradicional + intro, son, parte rápida y final originales |
| `dato-la-bamba.mp4` | Datos curiosos de La Bamba | `datos_curiosos.py` (guion en `SCRIPT`) | 0:51 | Borrado (11-oct): no le gustó |
| `dato-la-bamba-voz.mp4` | Datos curiosos de La Bamba, con voz | `datos_curiosos.py --narracion` | — | Publicado en TikTok el 11-oct |
| `dato-ajolote.mp4` | ¿Sabías qué? El ajolote, pixel art 8-bit | `ajolote.py` | 1:05 | Primer dato curioso 8-bit hecho con código (los anteriores 8-bit se hicieron en otra IA) |
| `rebotes-la-bamba.mp4` | Bolitas rebotando con notas de La Bamba | `rebotes.py` (SEED 5, ver `--stats`) | 0:10 | Borrado (11-oct): no le gustó |
| `rebotes-la-bamba-largo.mp4` | Bolitas rebotando, versión para monetizar | `rebotes.py --version largo` (SEED 5) | 1:10 | Crecimiento parejo, caos a los 62 s. Contador = total aparecidas (~6000); aviso pequeño bajo el título; bolitas sin brillo blanco. Aprobado |
| `marcha-turca-3d.mp4` | Marcha Turca en piano 3D (Three.js) | `escenas3d/`, `--inicio 0 --duracion 10` | 0:17 | Prueba del formato 3D. Le encantó; brillo bajado y piso arreglado a pedido |
| `pruebas/podcast/podcast-chivas-atlas-prueba.mp4` | Podcast pixel art: Alan y Luis, Chivas vs Atlas (el penal) | `podcast.py` | 0:12 | Prueba del formato. Le encantó. Personajes: IA + `pixel_ia.py`; voces: IA de pago (mp3 por frase) |
| `pruebas/caricatura/caricatura-sustancia-prueba.mp4` | Caricatura rara opinando de *La Sustancia* | `remotion/render.sh RaroSustancia …` | 0:10 | Prueba del formato rubber hose + Waking Life con Remotion (v1 y v2 más fluida). Le gustaron las transiciones, pero no le convenció: en pausa |
| `pruebas/bolitas/rebotes-armonia-3d-prueba.mp4` | Bolitas 3D con física real que suenan en armonía | `escenas3d/bolitas.mjs` + `bolitas_sonido.py` + `grabar.js` | 0:05 | Prueba; referencia reel de @particlesflow |
| `son-de-la-negra-3d.mp4` | El Son de la Negra, piano 3D con partículas | arreglo propio (`arreglos/son_de_la_negra.py`), `escenas/piano.html`, `--duracion 63.26` | 1:10 | Primer 3D para monetizar: notas que estallan en partículas, título y cierre "¡Viva México!" |
| `rebotes-esfera-3d.mp4` | Bolitas 3D en esfera neón: sale 1, entran 2 | `escenas3d/rebotes3d*` + `escenas/rebotes.html` | 1:10 | Música electrónica sintetizada, clímax 57.6 s, glitch final. Le encantó ("increíble") |
| `pruebas/datos/intro-sabias-que-prueba.mp4` | Intro de cine 3D "¿SABÍAS QUÉ?": calle synthwave con lluvia y letreros neón | `escenas3d/intro.py` + `escenas/intro.html` + `grabar.js` | 0:10 | Primera prueba de motion graphics con `MOTION.md` (skill title-sequence-3d). Gancho para datos curiosos |
| `pruebas/cineclub/cineclub-intro-collage-prueba.mp4` | Cineclub Forever: intro de collage de papel rasgado (proyector, Nosferatu, Méliès, logo) | `collage/cineclub-intro/` | 0:10 | Primera prueba del estilo de @kaye_creatives, en vertical y con imágenes de dominio público. Le encantó ("quedó increíble"): base aprobada para Cineclub |
| `pruebas/cineclub/cineclub-terror-prueba.mp4` | Cineclub Forever presenta la Temporada de Terror (patrocina True Love Design) | `collage/cineclub-terror/` con HyperFrames (ADR-021) | 0:15 | Recortes de carteles de terror, un color y una tipografía por cartel. Sin monetizar (imágenes con derechos) |
| `pruebas/beats/beat-techno-rueda-prueba.mp4` | "¿Por qué tu techno no rueda?": secuenciador 3D neón que se arma capa por capa (kick, rumble, ghost, clap, hats, stab) | `escenas3d/techno.py` + `escenas/techno.html` (ADR-022) | 0:22 | Inspirado en un reel de @beatmakerhacks, con guion, paleta y cámara propios. Le encantó. Sin voz: el dueño la graba en TikTok (`techno.py --version corto`) |
| `beat-techno-rueda.mp4` | "¿Por qué tu techno no rueda?" versión larga: 17 ideas (four on the floor, sidechain, swing, antes/después, subida y drop doble) | `escenas3d/techno.py` (largo) + `escenas/techno.html` | 1:10 | Para monetizar. La prueba de 0:22 le encantó ("quedó increíble"). Guion de voz: `out/pruebas/beats/beat-techno-rueda-guion.txt` |
| `beat-techno-rueda-voz.mp4` | Lo mismo con voz en off (IA de voz, "Liam") | `techno_voz.py out/pruebas/voces/techno/techno-voiceover-liam.mp3` | 1:10 | La que se sube. Subtítulos sincronizados a la voz |
| `beat-trap-vacio-voz.mp4` | "¿Por qué tu trap suena vacío?": trap mal hecho → tape stop → el bueno capa por capa (808 afinado/saturado/glide, kick, clap half-time, hats con redobles y tono, open hat, campanas); drop con bocina neón | `escenas3d/trap.py` + `escenas/trap.html` + `techno_voz.py --beat beat-trap-vacio` | 1:23 | Segundo de la serie (el techno pasó 10k vistas). Voz de IA del dueño. Le gustó ("quedó súper bien") |
| `beat-reggaeton-perreo.mp4` | "¿Por qué tu reguetón no hace perrear?": reguetón cuadrado → rayón de disco → el dembow 3-3-2 capa por capa (kick, caja, bajo, acordes Am–F–C–G, shaker, timbales, hueco); paleta lima ácido, cámara ladeada/cenital/barridos; drop con bola disco que se arma con las baldosas | `escenas3d/reggaeton.py` + `escenas/reggaeton.html` (ADR-023) | 1:16 | Tercero de la serie (techno + trap: 20k vistas, ~800 seguidores). Sin voz todavía (`techno_voz.py --beat beat-reggaeton-perreo`) |
| `beat-reggaeton-perreo-voz.mp4` | Lo mismo con voz en off (IA de voz del dueño) y efectos en la voz: reverb ligera, delay en palabras clave, voz de radio en el beat malo, "¡Perreo!" saturado y eco en el cierre | `techno_voz.py ~/Downloads/dembow-voice-full.mp3 --beat beat-reggaeton-perreo` (`EFECTOS`) | 1:16 | La que se sube |
| `beat-punk-kids.mp4` | "¿Puedes seguir esta batería?": *The Kids Aren't Alright* (The Offspring) por niveles, carriles estilo Guitar Hero (bombo = barra), reto con toda la banda → niveles lentos → más rápido → banda → NK | `escenas3d/punk.py` + `escenas/punk.html` (ADR-024) | 1:10 | Cover (no monetizable): para ganar seguidores. Kit Standard, guitarras con ampli propio |
| `beat-psytrance.mp4` | "¿Cómo se hace un buen psytrance?": embarrado → apagón → kick cortito y bajo rodante (galope K-B-B-B), clap, open hat, hats, acid de Surge XT; respiros sin voz; drop con túnel de anillos en espiral; paleta ultravioleta + verde tóxico | `escenas3d/psytrance.py` (`.venv-synth`) + `escenas/psytrance.html` (ADR-027) | 1:20 | Cuarto de la serie. Sin voz todavía (guion en `out/pruebas/beats/beat-psytrance-guion.txt`; `techno_voz.py --beat beat-psytrance`) |
| `beat-psytrance-voz.mp4` | Lo mismo con voz en off de ElevenLabs (un solo audio, ADR-025); eco en "galope" y "acid", "…y suéltalo" grande, eco en el cierre | `techno_voz.py ~/Downloads/psytrance-voz-off.mp3 --beat beat-psytrance` | 1:20 | La que se sube |
| `pruebas/beats/beat-trance.mp4` | "Seguimos con los tutoriales… ¿Quieres aprender a hacer esto?": trance que abre terminado (escenario con láseres) → tape stop → kick, bajo a contratiempo, clap/hats, acordes, pad cortado (gate), arpegio, sidechain → break con láseres al cielo → drop con escenario de festival y láseres; paleta amanecer de festival; nombra las notas de todo, delay en el pad, sidechain explicado | `escenas3d/trance.py` (`.venv-synth`) + `escenas/trance.html` (ADR-030) | 1:27 | Quinto de la serie. Guion: `out/pruebas/beats/beat-trance-guion.txt`; instrucciones para ElevenLabs: `beat-trance-elevenlabs.txt` |
| `pruebas/beats/beat-trance-voz.mp4` | Lo mismo con voz en off de ElevenLabs ("Liam", dos tomas juntas: `out/pruebas/voces/trance/trance-voz-liam-completa.wav`); pausas entre notas apretadas (`PAUSA_MAX`), eco en "delay" y "eco", "¡A disfrutar el beat!" grande | `techno_voz.py out/pruebas/voces/trance/trance-voz-liam-completa.wav --beat beat-trance` | 1:27 | La que se sube |
| `pruebas/beats/beat-ocarina-tormenta-completa-prueba.mp4` | Tributo a Zelda: *Song of Storms* en ocarina 3D translúcida neón sobre una aldea con tormenta, con beat electrónico y cinta de botones de Switch 2 (L R X) | `escenas3d/ocarina.py --version completa` (`.venv-synth`) + `escenas/ocarina.html` (ADR-028) | 0:34 | En curso: le está gustando. Falta el largo (~75 s). Cover: no monetiza |
| `pruebas/beats/beat-ocarina-saria-largo.mp4` | Tributo a Zelda #2: *Saria's Song* (partes A y B) en la ocarina 3D, bosque mágico de noche con Trifuerzas doradas al fondo | `escenas3d/saria.py --version larga` (`.venv-synth`) + `escenas/saria.html` (ADR-029) | 1:23 | La prueba de ~37 s le gustó; esta suma la parte B, Trifuerzas, sin hongos, cámara más baja. Cover: no monetiza |
| `pruebas/beats/beat-ocarina-saria-corto.mp4` | Lo mismo en corto: frase → parte A → mitad de la parte B → drop con la escalera → final | `escenas3d/saria.py --version corta` + `escenas/saria.html` | 0:44 | La recomendada: para covers no hace falta el minuto y el largo puede aburrir |
| `pruebas/beats/beat-hardtechno.mp4` | "¿Cómo se hace el hard techno?": toda la pantalla es un osciloscopio CRT; abre bajito solo con el kick limpio ("Así se hace el hard techno"), sin nombrar notas; cada instrumento es un canal con su onda real (kick limpio → saturado, rumble → sidechain, hats + clap, stab metálico, sinte que grita); drop con todos los canales grandes y saturados (como al final del break) y cierre con glitch que congela y rompe la imagen | `hardtechno.py` (ADR-031) | 1:14 | Sexto de la serie, primero con otra UI. La prueba de 16 s le gustó. Sin voz todavía (guion: `out/pruebas/beats/beat-hardtechno-guion.txt`) |
| `clair-de-lune` | Clair de Lune, Debussy | — | — | Descartado: "muy aburrido" |

## Pendientes / ideas

La lista viva de ideas está en `out/ideas.json` (se ve y edita en la web). Al proponer ideas de datos
curiosos, verificar el dato y escribir `escena` y `sonidos` en inglés siguiendo la plantilla.

- **Podcast:** guion largo (62 s o más) con 15–20 frases; voces de la IA de pago, un mp3 por frase en
  `out/pruebas/voces/` y su ruta en `DIALOGO` de `podcast.py`.
- Texto del cierre fijo en "Sígueme para la parte 2" (`make_outro_layer`); hacerlo configurable
  (`--cierre`) para clips sueltos.
- Partes 2, 3… de la Marcha Turca con `--inicio 73`.
- Otras piezas rápidas de dominio público: El vuelo del moscardón, La Campanella, Vals del minuto.
- Unir una intro cinematográfica hecha en fal.ai (sin texto; el título se pone con ffmpeg).
- Skills, librerías y herramientas por probar: `out/por-probar.json` (sección "Por probar" de la web).
  Ahí está el skill **anatomy** con su revisión.
