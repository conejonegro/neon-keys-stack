# Registro de decisiones (ADR)

Cada decisión dice qué se eligió, por qué y qué consecuencias tiene. Las nuevas van al final.

---

## ADR-001 · Generar el video con código, no con un editor ni con IA

**Fecha:** 2026-10-10 · **Estado:** aceptada

**Contexto.** El canal necesita producir muchos videos con el mismo estilo. Editar a mano en CapCut no
escala, y las IAs de video no pueden mostrar notas reales sincronizadas con la música.

**Decisión.** Un script de Python (`neon_keys.py`) lee el MIDI y dibuja cada cuadro con Pillow.

**Consecuencias.** Cada video nuevo es cambiar MIDI y título. La sincronía entre notas y audio es exacta
porque ambos salen del mismo MIDI. Los cambios de diseño se hacen en código.

---

## ADR-002 · Pasar los cuadros a ffmpeg por pipe, sin guardar imágenes

**Fecha:** 2026-10-10 · **Estado:** aceptada

**Contexto.** Un video de 80 s tiene ~2,400 cuadros de 1080×1920; como PNG ocuparían varios GB.

**Decisión.** Cada cuadro se dibuja en memoria y se escribe como RGB crudo al `stdin` de ffmpeg
(`-f rawvideo -pix_fmt rgb24`), que lo codifica con libx264 (CRF 18, yuv420p, `+faststart`).

**Consecuencias.** Solo ocupa disco el `.mp4` final. Velocidad aproximada: ~13 cuadros/s
(~2–3 min por cada minuto de video).

---

## ADR-003 · Audio con TinySoundFont + FluidR3, sin compilar nada

**Fecha:** 2026-10-10 · **Estado:** aceptada

**Contexto.** FluidSynth habría tenido que compilarse con Homebrew en macOS 12 (ver ADR-004).

**Decisión.** `tinysoundfont` (wheel de pip) sintetiza el piano offline con el soundfont
`FluidR3Mono_GM.sf3` (14 MB, del repositorio de MuseScore). Se instala con `--no-deps` porque su
dependencia `pyaudio` no compila y solo sirve para reproducir en vivo, cosa que no usamos.
Se respetan los mensajes de pedal (`control_change`). El audio se normaliza a −1 dB y se desvanece en el cierre.

**Consecuencias.** Sonido de piano decente y gratis. Para mejor calidad se puede cambiar el soundfont con
`--soundfont`.

---

## ADR-004 · ffmpeg estático en vez de Homebrew

**Fecha:** 2026-10-10 · **Estado:** aceptada

**Contexto.** La Mac es macOS 12 Monterey (Intel). Homebrew ya no ofrece binarios para esta versión:
`brew install ffmpeg` empezó a compilar ~25 dependencias desde fuente (más de una hora).

**Decisión.** Usar los binarios estáticos de evermeet.cx (ffmpeg y ffprobe 9.0.2) en `~/.local/bin`.

**Consecuencias.** Instalación en un minuto. Para actualizar, volver a bajar de evermeet.cx.
Regla general: evitar Homebrew para cualquier cosa que compile.

---

## ADR-005 · Render atómico en `out/.tmp/`

**Fecha:** 2026-10-10 · **Estado:** aceptada

**Contexto.** Un video (`clair-de-lune.mp4`) quedó corrupto: se abrió en QuickTime mientras o justo
después de escribirse y el archivo cambió de tamaño (tenía la marca `com.apple.quarantine` de QuickTime).
Además, la web lo listaba en la galería antes de terminar.

**Decisión.** ffmpeg escribe en `out/.tmp/<nombre>.mp4` y, solo si termina bien, se mueve a `out/`
con `Path.replace`. Antes de entregar se verifica con `ffmpeg -v error -i … -f null -` (0 errores).

**Consecuencias.** En `out/` solo hay videos completos. La galería web no muestra videos a medias.

---

## ADR-006 · Música de dominio público (Mutopia Project)

**Fecha:** 2026-10-10 · **Estado:** aceptada

**Contexto.** Las canciones modernas tienen derechos; TikTok puede silenciarlas o excluirlas de Creator Rewards.

**Decisión.** Bajar MIDIs de mutopiaproject.org (todo es dominio público o licencia libre). Preferir
piezas rápidas y famosas: Marcha Turca, Rey de la Montaña, Vuelo del moscardón, etc.

**Consecuencias.** Sin riesgo de derechos. El repertorio es clásico, así que el gancho tiene que venir
de la energía de la pieza y del estilo visual.

---

## ADR-007 · Formato, layout y estética

**Fecha:** 2026-10-10 · **Estado:** aceptada (aprobada por el usuario)

**Decisión.**
- 1080×1920, 30 fps, H.264 + AAC 192 kbps.
- Teclado en `KEYS_TOP = 1360`, teclas blancas de 230 px; piso synthwave en perspectiva debajo.
- Notas a 420 px/s; cian = mano derecha, magenta = mano izquierda; brillo neón con blur a 1/4 de
  resolución (barato) y chispas al tocar la tecla.
- Título arriba (Futura Bold 92 px) y marca "NEON KEYS" pequeña bajo el teclado.
- Las notas aparecen con un fundido debajo del título para no tapar el texto.
- Cierre de 3.5 s con logo grande y llamada a seguir.

**Consecuencias.** Identidad reconocible. El rango del teclado se ajusta a las notas del tramo (±2
semitonos); en piezas de rango amplio sale ancho y con teclas delgadas, pero el usuario lo aprobó así
(se probó un recorte de rango y se descartó a petición suya).

---

## ADR-008 · Duración = entrada + música + cierre

**Fecha:** 2026-10-10 · **Estado:** aceptada

**Decisión.** El video empieza con `LEAD_IN = KEYS_TOP / FALL_SPEED ≈ 3.24 s` de notas cayendo antes de que
suene la primera, y termina con `OUTRO = 3.5 s`. Total = 3.24 + `--duracion` + 3.5.

**Consecuencias.** Para un video de T segundos se usa `--duracion T − 6.74`. Por defecto `--duracion 62`
da ~68.7 s, por encima del minuto que exige Creator Rewards.

---

## ADR-009 · Web local con Flask que invoca el script

**Fecha:** 2026-10-10 · **Estado:** aceptada

**Contexto.** El usuario prefiere una interfaz visual a la terminal.

**Decisión.** `app.py` (Flask, puerto 5050, solo `127.0.0.1`) sirve `web/index.html` y ejecuta
`neon_keys.py` como subproceso. Lee el progreso de su salida estándar. Un solo render a la vez;
los nombres de salida se derivan del título (slug) y se numeran si ya existen.

**Consecuencias.** La lógica de video vive solo en `neon_keys.py`. Los trabajos se guardan en memoria:
si se reinicia el servidor, se pierde el progreso de un render en curso.

---

## ADR-010 · La web es la lista de publicación; datos en `out/videos.json`

**Fecha:** 2026-10-11 · **Estado:** aceptada

**Contexto.** El usuario pide los videos por el chat y usa la web solo para verlos y subirlos a TikTok.

**Decisión.** La web pasa a ser una lista de publicación: los videos se agrupan por tipo (prefijo del
archivo, `VIDEO_TYPES`), cada uno muestra descripción + hashtags con botón de copiar, duración y si es
monetizable (≥ 62 s, medido con ffprobe), y un estado listo/programado/publicado con fecha. Hay una vista
de la semana y una sección de imágenes. El formulario para crear desde MIDI queda escondido tras un botón.
Los datos editoriales viven en `out/videos.json` (junto a los videos, escrito de forma atómica); la duración
no se guarda, se mide.

**Consecuencias.** Al crear un video hay que agregar su entrada en `out/videos.json` (lo indica el skill
`/render-video`). Un JSON basta para un solo usuario local; si se borra, se pierden descripciones y estados
pero no los videos.

**Actualización (2026-10-11):** se agrega `out/ideas.json` con la lista de ideas y una plantilla de prompt
para la IA de video externa (los datos curiosos que el usuario hace fuera de este proyecto). La plantilla
vive en un solo lugar para poder cambiar el estilo de todos los prompts a la vez.


---

## ADR-011 · Piano 3D con Three.js (formato nuevo, no reemplaza al 2D)

**Fecha:** 2026-10-11 · **Estado:** aceptada (en prueba)

**Contexto.** El usuario quería un estilo 3D. Blender (`bpy`) no sirve aquí: no hay versión para Python 3.13
en Mac Intel (solo 4.5 con Python 3.11) y renderizar con Cycles en este i5 de 2 núcleos con Iris 6100
tardaría horas. Three.js dibuja en tiempo real con la tarjeta gráfica y ya había Node 23 y Chrome.

**Decisión.** Carpeta aparte `escenas3d/` con sus propias dependencias de npm (`three`, `puppeteer-core`,
que usa el Chrome instalado en lugar de descargar otro). `preparar.py` reutiliza `load_midi` y
`render_audio` de `neon_keys.py` (sin modificarlo) y escribe notas JSON + WAV en `out/.tmp/`.
`grabar.js` levanta un servidor local (los módulos no cargan desde `file://`), abre la escena en Chrome
invisible, llama a `window.dibujar(t)` cuadro por cuadro y arma el `.mp4` con ffmpeg en `out/.tmp/` antes de
moverlo a `out/`. Chrome se lanza con `--use-angle=gl`: con `metal` no crea contexto WebGL en esta Mac.
El piso synthwave es un shader con líneas suavizadas que se apagan a lo lejos (la `GridHelper` de Three.js
parpadeaba, hacía moiré y pintaba distinta la línea central).

**Consecuencias.** Es un segundo formato de piano, con su propio look (notas que llegan del horizonte,
sol retro, brillo suave); el 2D aprobado no cambia. ~0.13 s por cuadro (un video de 70 s ≈ 10 min). Agrega
JavaScript al proyecto. `escenas3d/.npmrc` fija el registro público de npm porque el `~/.npmrc` global
apunta a un registro privado de otro proyecto. El HTML de la escena no se anima si se abre solo en Chrome.

---

## ADR-012 · Skill pixel-art-studio como método para los personajes pixel art

**Fecha:** 2026-10-12 · **Estado:** aceptada

**Contexto.** Los personajes del podcast (Alan y Luis) se veían planos y con la paleta sucia: las sombras y
el contorno se hacían mezclando colores, y salían 96 y 133 colores casi repetidos. El skill
[pixel-art-studio](https://github.com/Gamezxz/pixel-art-studio) (MIT, solo Pillow, sin internet) dibuja igual
que nosotros, con código, pero trae técnica: rampas con cambio de tono, contorno "selout", lista de revisión
y estadísticas (colores, pixeles sueltos).

**Decisión.** Instalarlo como skill del proyecto en `.claude/skills/pixel-art-studio/` (con una sección
"Neon Keys" que manda sobre sus convenciones). `sprites.py` sigue autocontenido: se copió la idea de
`ramp()` como `_ramp()` y el lienzo de los personajes (`_Lienzo`) guarda por pixel su material y su tono, así
las sombras bajan un escalón de la rampa en vez de mezclar. `pixelstudio.py` solo se usa para revisar
(`stats()`), no lo importa `sprites.py`.

**Consecuencias.** Paleta corta (~45 colores por personaje) y volumen más limpio. La luz neón de borde ahora es
de color fijo. Si se actualiza el skill desde GitHub, hay que conservar su sección "Neon Keys" y las rutas.

---

## ADR-013 · Voces del podcast con Chatterbox (demo de Hugging Face por API)

**Fecha:** 2026-10-12 · **Estado:** aceptada (en prueba)

**Contexto.** El podcast de Alan y Luis necesita voces. Las voces que corren en esta Mac (Piper `es_MX`,
Kokoro; entorno `.venv-voz` con Python 3.12) suenan robóticas. Los mejores modelos abiertos en español con
licencia comercial (Chatterbox Multilingual, MIT; Qwen3-TTS, Apache 2.0) necesitan tarjeta gráfica, y esta
Mac no tiene una que sirva. XTTS, IndexTTS y Fish Audio quedan fuera porque no permiten uso comercial.

**Decisión.** Generar las voces con la demo oficial de Chatterbox Multilingual V3 en Hugging Face
(`ResembleAI/Chatterbox-Multilingual-TTS-V3`), llamándola desde `.venv-voz` con `gradio_client` y el token de
la cuenta del usuario (`~/.cache/huggingface/token`). Como referencia de voz se usa una grabación masculina:
Kokoro `em_alex` para Luis (Piper `claude` sonaba a mujer, ~197 Hz) y Piper `ald` para Alan. Ajustes que le
gustaron: exaggeration 1.8–2.0, cfg 0.3, temperature 0.9–1.0, y el texto escrito con emoción
(MAYÚSCULAS, ¡!, ...). Una toma intensa usada como referencia hace que la siguiente salga igual de intensa.
`podcast.py` lee los `.wav` de `DIALOGO`: los tiempos salen de la duración de cada voz, la boca se abre con el
volumen y la música baja mientras hablan.

**Consecuencias.** La cuenta gratis da muy pocos minutos de GPU (cada frase aparta 90 s; unas 4–5 frases al
día). Para un podcast de 1 minuto conviene Hugging Face PRO (40 min/día) o un cuaderno de Google Colab.
Clonar las voces reales de Alan y Luis (10 s de grabación de cada uno) es posible y permitido porque son ellos.

**Actualización (12-oct).** Al usuario no le convenció Chatterbox con referencias sintéticas (copia el sonido
robótico de Piper/Kokoro). Las voces finales de la prueba las generó él en una IA de voz de pago y las pasó como
un mp3 por frase (`out/pruebas/voces/chivas-penal-dialogo-*.mp3`). `podcast.py` acepta wav o mp3 sin cambios.

## ADR-014 · Remotion para el formato "caricatura" (rubber hose)

**Fecha:** 2026-10-12 · **Estado:** aceptada (en prueba)

**Contexto.** El usuario quiso probar un estilo nuevo: caricatura rara tipo "rubber hose" (contorno negro
grueso, color plano, brazos de fideo, guantes blancos) con líneas que "hierven" como en *Waking Life*. Remotion
hace videos con React y Chrome invisible, igual que `escenas3d/`, pero ya trae resortes, secuencias, audio y
render a `.mp4`, además de skills oficiales (`remotion-dev/skills`, en `.claude/skills/remotion-*`).
Su licencia es gratis para personas y empresas de hasta 3 empleados.

**Decisión.** Proyecto aparte en `remotion/` (con su `.npmrc` al registro público). El personaje se dibuja en
SVG con código (`src/rubberhose/Raro.tsx`): primero todo el contorno negro y encima el color, con un filtro de
ruido (`feTurbulence` + `feDisplacementMap`) cuya semilla cambia cada 3 cuadros, y el color tiembla aparte de la
línea. El guion vive en `src/rubberhose/guion.json`; `sonido.py` (con `.venv`) arma el balbuceo, la base y los
efectos con las mismas sílabas que mueven el pico. Los videos de este formato llevan el prefijo `caricatura-`.

**Consecuencias.** En macOS 12 el Chrome que descarga Remotion no arranca (le falta un símbolo de
VideoToolbox), así que `remotion.config.ts` usa el Chrome instalado, igual que `escenas3d/grabar.js`. No usar
`<HtmlInCanvas>` ni los `@remotion/effects` que lo necesitan: piden Chrome 149+ con una bandera experimental.
El ffmpeg y el "compositor" que trae Remotion tampoco corren en macOS 12 (piden AVFoundation de macOS 13+),
así que `npx remotion render … video.mp4` falla con `EPIPE`. Por eso `remotion/render.sh` le pide a Remotion
solo los cuadros (`--sequence`, JPEG, `--concurrency=1`: con más pestañas Chrome se cae) y arma el `.mp4` con
el ffmpeg de `~/.local/bin` y el WAV de `sonido.py`:
`cd remotion && ./render.sh RaroSustancia caricatura-sustancia-prueba 10 pruebas`.
Vista en vivo (solo si el usuario la pide): `npm run dev`.

## ADR-015 · Bolitas 3D con física real (Rapier) y armonía por escala

**Fecha:** 2026-10-12 · **Estado:** aceptada (en prueba)

**Contexto.** El usuario vio un reel (@particlesflow) con cientos de bolitas brillantes que se apilan en forma de
tazón y suenan al chocar, con pesos distintos. Blender se descartó otra vez por la Mac (ADR-011): Cycles tardaría
horas y Blender 4.5 es la última versión para Intel.

**Decisión.** Tres pasos en `escenas3d/`: `bolitas.mjs` simula con Rapier (`@dimforge/rapier3d-compat`, WebAssembly,
sin compilar) a 240 Hz: bolitas pesadas al centro y ligeras por la orilla de un tazón invisible (tablitas
inclinadas), con freno al rodar para que se apilen; guarda posiciones por cuadro y cada golpe (cambio brusco de
velocidad). `bolitas_sonido.py` toca una nota fija por bolita de Do mayor pentatónica (pesadas graves tipo
campana, ligeras agudas tipo cristal), con máximo 2 golpes cada 30 ms, volumen por fuerza, estéreo por posición
y eco; anota en el JSON qué golpes suenan. `escenas/bolitas.html` dibuja con Three.js (`InstancedMesh`, material
con barniz, reflejos `RoomEnvironment`, sombras, glow suave), colorea por altura y hace destellar la bolita que
suena. Se graba con `grabar.js` (0.2 s por cuadro).

**Consecuencias.** La física es determinista: el mismo programa de caída da siempre el mismo video. Para variar
(regla 8b) se cambian forma del tazón, colores, escala o el programa de caída.

---

## ADR-016 · Piano 3D con estallido de partículas, título y cierre (`escenas3d/escenas/piano.html`)

**Fecha:** 2026-10-12 · **Estado:** aceptada

**Contexto.** Para *El Son de la Negra* en 3D el usuario pidió que cada nota "se destruya en partículas pequeñas"
al tocar el teclado. Además, el formato 3D aún no tenía título, marca ni cierre (pendiente desde ADR-011).

**Decisión.** Escena nueva `piano.html` (copia del look aprobado de `prueba.html`, que se queda como estaba). Al
llegar cada nota salen 14 esquirlas (tetraedros con rebote en el teclado), 34 chispas (puntos con halo y freno de
aire) y un anillo de luz que se abre; las notas largas sueltan chispas mientras se apoyan, como si se
desmoronaran, y la tecla se hunde un poco. Todo es aditivo, sale casi blanco y se enfría al color de la mano.
Cada partícula se siembra con azar fijo por nota y su posición se calcula con fórmulas a partir de `t` (no se
simula cuadro a cuadro), así una vista previa en cualquier segundo sale igual que en el video. Las capas de texto
las dibuja `preparar.py --titulo/--subtitulo/--cierre` con las funciones de `neon_keys.py` (mismas fuentes y
halo que el 2D) y viajan en el JSON como PNG; la escena las mezcla en modo *screen* encima del render, sin bloom.
La fuerza de cada nota (`vel`) da más energía al estallido.

**Consecuencias.** Un video de 70 s tarda más que la prueba 3D por las partículas. Las notas de `prueba.html` no
cambian. Para un clip suelto basta con otro `--cierre`.

### Arreglo propio de El Son de la Negra (`arreglos/son_de_la_negra.py`)

La melodía es tradicional (son jalisciense, dominio público); los arreglos famosos (Blas Galindo 1940, Mariachi
Vargas) no se copian. Las notas de las partes se tomaron de una guía de flauta dulce (flautinextremo.com) y los
acordes de un cifrado (Sol mayor: G, D7, C, A7). El ritmo, los trémolos, la sesquiáltera del acompañamiento y el
final en octavas son propios. Unidad = corchea; el tempo sale de ajustar 372 corcheas a 63.26 s (≈ 0.17 s cada una).

---

## ADR-017 · Bolitas en 3D: esfera con hueco, física propia y música electrónica sintetizada

**Fecha:** 2026-10-14 · **Estado:** aceptada

**Contexto.** El usuario pidió las bolitas de `rebotes.py` en 3D con Three.js, de 1:10, con "cada bolita que sale
aparecen dos", clímax, sonido más electrónico e hipnótico y el glitch final.

**Decisión.** Una esfera neón de alambre con un hueco redondo que gira sobre un eje inclinado. La física es propia
y sencilla (`escenas3d/rebotes3d.js`, sin Rapier: las bolitas no chocan entre sí, igual que en 2D), determinista
con azar de semilla, y la comparten Node (`rebotes3d.mjs`, saca golpes y escapes para el sonido) y la escena
(`escenas/rebotes.html`, vuelve a simular al dibujar y comprueba que sus golpes coincidan con los del JSON; si no,
falla). Así no se pasan las posiciones de miles de bolitas por cuadro (serían cientos de MB). Cada escape hace
nacer 2 bolitas siempre (con tope de 1,400 dentro); el ancho del hueco se ajusta solo para seguir una curva de
crecimiento (rápida al inicio para enganchar, exponencial después). Los tiempos van al compás de la música
(125 BPM): clímax en el compás 30 (el hueco se abre de golpe, gira rápido y la cámara se aleja) y glitch en el 34.
El sonido (`rebotes3d_sonido.py`) se sintetiza con numpy: cada golpe que suena es un pluck con eco ping-pong cuya
nota sale del acorde del momento (Am–F–C–G) y de la altura del golpe; debajo, pad, hi-hats, bombo con sidechain,
bajo, subida con redoble y drop. El glitch usa el mismo mapa de tiempo en video (shader de franjas y RGB) y audio
(trozos repetidos + bitcrush).

**Consecuencias.** Para variar (regla 8b) basta con cambiar `semilla`, `faseInicial`, colores o los acordes. Si
se cambia la física hay que volver a correr `rebotes3d.mjs` y el sonido antes de grabar.

---

## ADR-018 · Guía de movimiento propia (`MOTION.md` + `brand.md`) y skills de motion graphics

**Fecha:** 2026-10-21 · **Estado:** aceptada

**Contexto.** El dueño vio videos donde se le pasa a Claude un archivo con reglas "profesionales" de motion
graphics para que todo salga con el mismo estilo. El método viene del pack de charlie947 (skill
`brand-intake`) y de Tommaso Nervegna: una guía con medidas concretas que se lee antes de animar.

**Decisión.** `MOTION.md` y `brand.md` en la raíz, escritos con los valores del código y de los ADR (no
sacados de capturas); `CLAUDE.md` obliga a leerlos antes de animar. Se instalan solo dos fuentes de skills,
revisadas a mano: el pack de charlie947 (MIT) y `motion-design` de LottieFiles (MIT), ambos solo texto. No se
usan MCPs (After Effects es de pago; Blender sería un mundo nuevo y Three.js ya cubre el 3D). HyperFrames queda
en "Por probar": mientras tanto se graba con `escenas3d/grabar.js`, que hace lo mismo (Chrome cuadro por
cuadro + ffmpeg).

**Consecuencias.** Si cambia un color o un tiempo en el código, hay que actualizar `MOTION.md`; si no
coinciden, manda el código. Los skills del pack piensan en LinkedIn o newsletters: se usan con formato
1080×1920 y las zonas seguras de TikTok.

---

## ADR-019 · Una carpeta por marca (`marcas/<marca>/`)

**Fecha:** 2026-10-21 · **Estado:** aceptada

**Contexto.** El dueño quiere hacer videos de cine con otra marca suya, **Cineclub Forever**
(cineclub-forever.vercel.app), con otro estilo y sin tocar Neon Keys.

**Decisión.** `brand.md` y `MOTION.md` dejan la raíz y pasan a `marcas/neon-keys/`. Cada marca tiene la misma
estructura: `brand.md` y `MOTION.md` (para Claude), `marca.json` (colores en hex, rutas de fuentes con su índice,
logo, firma y cierre, para el código), `logo.png` y `fuentes/` si no son del sistema. Cineclub Forever sale del
CSS de su sitio: fondo `#0A0A0A`, acento ámbar `#FCBB00`, Montserrat y Lato (OFL, bajadas de sus repos
oficiales), y su logo en blanco y negro. Los scripts ya aprobados (`neon_keys.py`, bolitas, piano 3D) no se
tocan. Los formatos nuevos leen `marca.json` con una opción `--marca` cuando se hagan.

**Consecuencias.** Para una marca nueva basta con crear su carpeta (el skill `brand-intake` ayuda a escribirla).
En las marcas de cine hay riesgo de derechos: clips, carteles y música de películas no se usan en videos para
monetizar; se usa material propio o películas de dominio público.

---

## ADR-020 · Collage de papel rasgado para Cineclub Forever (skill `paper-collage-film`, vertical)

**Fecha:** 2026-10-21 · **Estado:** en prueba

**Contexto.** El dueño vio los motion graphics de @kaye_creatives (tutorial en Higgsfield) y quiere ese nivel. Pasó
el skill `paper-collage-film` (revisado: solo usa internet para Google Fonts; Chrome local, Swift y síntesis de audio).

**Decisión.** Proyecto en `collage/cineclub-intro/` creado con `new_project.sh`. El motor (CL / CLX) y las
transiciones del skill se usan tal cual; las escenas se reescribieron para 1080×1920 (`window.FILM_SIZE`), porque las
del ejemplo están dibujadas con coordenadas fijas de 16:9. Los recortes son de dominio público (Wikimedia Commons:
proyector PSF, Méliès 1902, Nosferatu 1922, cartel Lumière 1896, kinetoscopio) y se preparan con
`preparar_recortes.py`; nada de Higgsfield. La paleta por anclas del skill (`grade.js`) teñía los grises de verde y
el cobalto de morado, así que el color lo pone `grade_cineclub.js`: lo cálido y saturado pasa a ámbar `#FCBB00` y lo
demás a blanco y negro con crema `#F1ECE2`. La música es la del skill (`audio/score.html`) sin los sonidos de YouTube
(clic, campana, coche, avión, tecleo). El video sale a 24 fps.

**Consecuencias.** Otra pieza de Cineclub se hace re-temporizando o cambiando escenas en `scenes.js` y los textos en
`COPY`. El ciclo ("CICLO SNOB") cambia cada mes. Para Neon Keys habría que hacer otro filtro de color (o usar la paleta
`night` del skill).

---

## ADR-021 · HyperFrames para piezas de tipografía y recortes (Cineclub "Temporada de Terror")

**Contexto.** HyperFrames (HeyGen, Apache 2.0) estaba en "Por probar" (ADR-018). El dueño pidió una pieza de imagen
corporativa de Cineclub: "presenta la temporada de terror, todo octubre, patrocinada por True Love Design", con la
tipografía y el color de cinco carteles de referencia y un ritmo más pausado que la intro de collage.

**Decisión.** Se probó HyperFrames en `collage/cineclub-terror/hf/` (instalado solo ahí, versión fija 0.8.185). La
composición es HTML + GSAP; un reloj de 15 s lleva una línea interna "en dos" (pose cada 2 cuadros) y el acabado
(grano, temblor, parpadeo) depende del cuadro. Recortes, logo sin fondo y texturas se hacen con Pillow
(`preparar.py`); el sonido con código (`audio/terror.py`, reusa `collage/musica/terror.py`). Paleta especial de
temporada: un acento por cartel (lila, menta, rojo) y el ámbar de Cineclub solo en la apertura y el cierre.

**Consecuencias.** HyperFrames sirve para piezas de texto, recortes y cortes; `check` avisa si un texto dura muy poco
para leerse, justo la queja del video anterior. Render: ~3 min para 15 s en esta Mac. Para 3D sigue `grabar.js`.
Se usa con `--describe false` y sin `publish`, para que nada salga a internet. Las imágenes de los carteles tienen
derechos: esta pieza no se monetiza.

