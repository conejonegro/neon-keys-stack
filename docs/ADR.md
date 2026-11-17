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

## ADR-022 · Formato "beat explicado": secuenciador 3D que se arma capa por capa (`escenas3d/techno.py`)

**Contexto.** El dueño vio un reel de @beatmakerhacks que explica cómo hacer que la batería de techno "ruede" con un
secuenciador 3D de bloques naranjas, y pidió uno así para Neon Keys (~20 s, él pone la voz en TikTok).

**Decisión.** Se hizo con lo que ya teníamos (Three.js + `grabar.js`) y con guion, paleta y cámara propios: 16 pasos
× 6 carriles (KICK, RUMBLE, CLAP, STAB, OPEN HAT, HATS) sobre el sol retro y el piso synthwave; graves en magenta,
agudos en cian, clap morado y stab amarillo (acentos de MOTION.md). Una sola tabla en `techno.py` (`PATRONES` +
`SECCIONES`, una sección por idea y por compás a 132 BPM) da los golpes del audio **y** de la imagen, los textos
palabra por palabra y el guion de la voz con sus segundos. Toda la batería es síntesis (kick con caída de tono,
rumble con reverb + sidechain, clap, hats, stab de Fa menor con eco ping-pong), con el pico a −6 dB para dejar
espacio a la voz. El texto y las etiquetas se dibujan en un canvas 2D en modo *screen*; una sombra arriba asegura
que se lean. Sol, montañas y piso van hundidos en la dirección de las tomas para quedar detrás de la cuadrícula.
En el drop la cuadrícula se enrolla en un cilindro (doblez por baldosa en `colocar()`) que gira al tempo.

**Consecuencias.** Para otro tema (house, trap, otra técnica) basta cambiar `PATRONES`, `SECCIONES` y las tomas de
`TOMAS` en la escena. Prefijo `beat-` en `VIDEO_TYPES` (tipo "beats" en la web). Dos versiones (`--version`): `corto`
(prueba de ~22 s) y `largo` (1:10, para monetizar). En la larga el sidechain y el swing entran cuando se explican,
para que se oiga la diferencia; hay un antes/después (todo menos el kick se hunde y vuelve), una subida con redoble
de clap y silencio antes del drop, y el drop dura 6 compases (clímax al 78 %).


## ADR-023 · Beat explicado #3: reguetón con paleta, cámara y final propios (`escenas3d/reggaeton.py`)

**Contexto.** Techno y trap juntos pasaron 20k vistas y trajeron ~800 de los primeros 1,000 seguidores. Para el
tercero (reguetón, explicando el dembow) el dueño pidió que no se viera igual: otra paleta (verdes y amarillos,
aunque se salga del cian/magenta), otros movimientos de cámara y un final 3D que se arme como la rueda del techno
(la bocina del trap estaba bien, pero la rueda gustó más). También pidió no poner un dato histórico largo al
inicio, porque el del 808 dejó mucho rato sin que pasara nada.

**Decisión.** Se reusa la forma de `trap.py` (PATRONES + SECCIONES → golpes, audio, textos y guion) a 95 BPM, con
carriles KICK · CAJA · BAJO · TIMBAL · ACORDES · SHAKER. Abre con un reguetón cuadrado (caja en 2 y 4) que se frena
con un rayón de disco; el dato ("nació en Jamaica, 1990") va a la mitad, con todo sonando. La paleta va en el JSON
(`--paleta lima|tropical|verde-morado`; el dueño eligió **lima ácido**) y la escena (`escenas/reggaeton.html`)
la lee en vez de usar colores fijos; el cierre NK se queda en cian/magenta porque es la marca. Esta serie rompe a
propósito "cámara casi quieta" de MOTION.md: las tomas tienen inclinación (ángulo holandés), una toma cenital con
corchetes 3-3-2, travellings a ras, cortes con barrido (desenfoque de movimiento en un ShaderPass antes del texto)
y un balanceo con cada caja. En el drop, 560 facetas salen de las baldosas, vuelan en arco y arman una bola disco
de espejo (reflejos de un cuarto con focos de la paleta, vía PMREM), que gira al tempo, da un jalón con cada caja,
lanza rayos que se prenden por turnos y suelta ondas con el kick.

**Consecuencias.** Cada video de la serie lleva su propio clímax visual y puede tener su propia paleta. El hueco
del kick se oye y se ve (los bloques se agachan). `grabar.js --preview` no aguanta varias instancias en paralelo
(chocan); las vistas previas se sacan una por una.


## ADR-024 · Batería por niveles estilo Guitar Hero con una canción famosa (`escenas3d/punk.py`)

**Contexto.** El reguetón casi no funcionó (el dembow quedó suave, "de playa"). El canal tiene ~1,000 seguidores y
necesita 10,000 para monetizar, así que por ahora se buscan seguidores, vistas y likes. El dueño pidió un tutorial de
batería pop punk con carriles que caen (Guitar Hero / Rock Band) y una canción famosa recreada por nosotros: eligió
*The Kids Aren't Alright* (The Offspring). El guion por niveles lo armó con ChatGPT a partir de nuestra propuesta.

**Decisión.** Se reusa la forma de los beats (una tabla `PATRONES` + `SECCIONES` → golpes, audio y textos), pero cada
sección lleva su propio tempo: reto a 198 BPM con toda la banda → frenón de cinta → niveles a 130 BPM con click
(bombo + tarola, + hi-hat, el redoble repartido tarola → tom → piso) → 150 y 172 BPM → banda completa (riff del
inicio y coro) → cierre con el ritmo de toms del inicio y un golpe final. La batería es transcripción propia (patrones
de 16 semicorcheas escritos como tablatura); los tiempos de cada compás se calculan en `COMPASES`. Sonido: kit
**Standard** del soundfont (el dueño lo prefirió al Power); bajo "Fingered Bass" del soundfont; guitarra doblada en
dos tomas con pequeños desfases: las notas apagadas con la palma son la "Palm Muted Guitar" del soundfont y las
abiertas son cuerdas Karplus-Strong, las dos por un ampli hecho con código (dos etapas de distorsión y caja que corta
arriba de ~4 kHz, sin el chirrido de 2.5–6 kHz que sonaba a MIDI). Cada instrumento se fija a un nivel RMS medido en
la parte de la banda; sin banda la batería sube 5 dB, y el tom de piso no pasa por el refuerzo de graves del bombo
(saturaba). La escena (`escenas/punk.html`) es una pista 3D que sale del sol retro, con 5 carriles de colores
(tarola magenta, hi-hat amarillo, tom cian, piso verde, platillo naranja) y el bombo como barra morada que la cruza;
las gemas viven en un grupo que avanza con el tiempo (z = −t·V), así el tempo variable sale solo. Pads con onda y
chispas en cada golpe; contador 1·2·3·4, BPM, nombres de carriles y combo en el canvas 2D.

**Consecuencias.** Es un cover: la grabación es nuestra pero la composición tiene dueño, así que sirve para crecer y
**no** para Creator Rewards. Otra canción = otros `PATRONES`, `SECCIONES`, acordes y riff. La línea de golpe queda en
y≈1475 para respetar la zona segura (nada importante bajo y=1600).

## ADR-025 · Voz en off: ElevenLabs en un solo audio, guion sin segundos

**Contexto.** Los guiones de voz (`out/pruebas/*-guion.txt`) llevaban el segundo en que empieza cada frase. El
guion lo escribe otra IA (ChatGPT) y la voz la genera el dueño con una IA de voz; los segundos no le sirven a
ninguna de las dos, porque la voz sale con su propio ritmo.

**Decisión.** La voz se hace en **ElevenLabs**, con todo el guion en **un solo audio**. Al pasarle el guion a la
otra IA se le pide eso y **no** se le piden tiempos: solo las frases en orden, una por renglón, con la sección a la
que pertenece cada una. El corte y la sincronización los hacemos aquí: `escenas3d/techno_voz.py` corta el audio por
sus silencios, junta los pedazos en frases (`PEDAZOS`), pone cada frase al inicio de su sección, baja la música
mientras se habla y mueve los subtítulos al ritmo de la voz.

**Consecuencias.** Los guiones que se pasan a la otra IA van sin columna de segundos (los tiempos de las secciones
solo se dan como referencia de cuánto dura cada parte). Si una frase no cabe en su sección, `techno_voz.py` la
acelera un poco; si sobra mucho texto, se recorta el guion. Para un formato nuevo (por ejemplo `punk.py`) hay que
agregar su entrada en `PEDAZOS` y que su escena lea los subtítulos de la voz.

## ADR-026 · Surge XT con DawDreamer para sonidos electrónicos (en prueba)

**Contexto.** En la batería por niveles (ADR-024) la guitarra distorsionada y los instrumentos del soundfont sonaban
"a MIDI". Se propuso pasar la serie a electrónica (prueba: *Firestarter*, The Prodigy) y probar un sinte de estudio en
lugar de la síntesis hecha a mano.

**Decisión.** **Surge XT 1.3.4** (gratis, GPL) en `plugins/surge-xt/` (solo los `.vst3` del zip "pluginsonly", sin
instalar nada en el sistema) y **DawDreamer 0.9.0** (rueda ya armada para Mac Intel) en un entorno aparte,
`.venv-synth` (Python 3.12, creado con `.venv/bin/uv venv --python 3.12 .venv-synth` + `uv pip install dawdreamer
numpy`). El zip no trae los presets de fábrica: se bajan los `.fxp` que hagan falta del repositorio de Surge
(`resources/data/patches_factory/`) a `plugins/surge-xt/patches/`. DawDreamer no lee esos `.fxp`, así que
`cargar_preset()` (en `escenas3d/surge.py`, junto con `tocar()`) mete el parche dentro del estado del plugin (XML de JUCE con su
base64 propio). La batería se queda con nuestra síntesis; Surge toca riff y bajo.

**Consecuencias.** Los scripts que usan Surge corren con `.venv-synth/bin/python`. Pendiente de que el dueño compare
las pruebas (`out/pruebas/firestarter-*-prueba.wav`) antes de adoptarlo en más formatos.

## ADR-027 · Beat explicado #4: psytrance con respiros sin voz y túnel en el drop (`escenas3d/psytrance.py`)

**Contexto.** Recrear canciones completas (*The Kids Aren't Alright*, *Firestarter*, *Sandstorm*) no sonaba tan
limpio como los beats hechos desde cero. El dueño pidió volver a la serie de beats con algo intenso y "bien
ponchado": psytrance. Un usuario comentó en el video de techno que la voz no dejaba escuchar la música.

**Decisión.** Misma forma que `reggaeton.py` (PATRONES + SECCIONES → golpes, audio, textos y guion) a 145 BPM en
Fa♯ menor, con carriles KICK · BAJO · CLAP · OPEN HAT · HATS · ACID. Lo que define al género se explica primero: el
kick corto que se corta antes de la siguiente semicorchea y el **bajo rodante** en los huecos (K-B-B-B, "bom,
ta-ta-ta"). Abre con un psytrance embarrado (kick largo y bajo encima) que se apaga cerrando el filtro. Hay
**secciones sin texto** (respiros de 2 a 4 compases, y medio drop) donde solo suena la música y la cámara gira en
espiral; `techno_voz.py` pone cada frase en su sección por nombre (`LUGAR_FRASE`) y se salta los respiros. El acid
sale de Surge XT (ADR-026), así que el script corre en `.venv-synth`. Mezcla a −16.8 LUFS antes de la voz, con el
saturador apenas tocado (la primera prueba quedó aplastada a −6 LUFS). Paleta ultravioleta + verde tóxico. La cámara
se mece despacio desde que entra el acid (hipnótico, en vez del ladeo con la caja del reguetón). Clímax: 560 piezas
salen de las baldosas y arman 28 anillos torcidos en espiral que giran en sentidos contrarios; la cámara se mete y
vuela por dentro (los anillos que quedan atrás pasan al fondo: túnel sin fin), cada kick manda una onda de luz por
el túnel y cada clap lo hace girar un jalón.

**Consecuencias.** El drop cae al 75 % (59.6 s de 79.8 s). Para dejar respirar la música en otros beats basta con
poner secciones de texto vacío y su entrada en `LUGAR_FRASE`.

## ADR-028 · Tributo a Zelda: ocarina 3D translúcida con beat (`escenas3d/ocarina.py` + `escenas/ocarina.html`)

**Contexto.** El remake de *Ocarina of Time* (Switch 2) salió el 5-nov-2026. El dueño quiso un video de trend: la
*Song of Storms* en una ocarina 3D, en versión electrónica. Pidió explícitamente salirse un poco del look Neon Keys
(fondo "más Zelda"), con la Trifuerza, y una ocarina gordita, translúcida y con contornos neón.

**Decisión.** Todo con código, sin modelos ni imágenes de IA:
- Ocarina de revolución (`LatheGeometry`) con sección de superelipse (cuadradona) y `MeshPhysicalMaterial` con
  `transmission`; el borde neón y la retícula se inyectan en el shader (`onBeforeCompile`, uniform `uNeon` que late
  con el kick). Los agujeros se pegan a la superficie por raycast (`pegar`).
- Digitación de ocarina de 12 agujeros en `DIGITACION` (los pulgares se dibujan con `depthTest: false` para verse a
  través del vidrio).
- Fondo de aldea con tormenta: el reflejo del esmalte sale de un "estudio" propio pasado por PMREM.
- La cámara no usa tomas con cortes, sino puntos de paso por sección (`PASOS_CAMARA`) interpolados con Catmull-Rom.
- Audio en `.venv-synth` (Surge XT para el supersaw, batería de `techno.py`). `ocarina.py` lee sus argumentos antes
  de importar `techno.py`, porque ese módulo parsea la línea de comandos al importarse.

**Consecuencias.** La capa de texto (canvas) llega sin premultiplicar: el shader de la capa multiplica rgb × alfa (si
no, lo semitransparente sale blanco; eso hacía los halos "cuadrados"). Cuando el último paso del compositor es el
`RenderPass` del texto hay que poner un `ShaderPass(CopyShader)` después, o la escena 3D sale negra. Es cover de una
melodía de Nintendo con su marca (Trifuerza): no entra a Creator Rewards y hay un riesgo pequeño de reclamo.


## ADR-029 · Tributo a Zelda #2: Saria's Song en un bosque mágico (`escenas3d/saria.py` + `escenas/saria.html`)

**Contexto.** Segundo video de la serie de la ocarina, ahora con *Saria's Song* (Lost Woods). El dueño pidió quitar
el molino y poner algo del bosque, y que sea "mágico e hipnotizante" para atrapar y retener (es para ganar
seguidores, no monetiza).

**Decisión.**
- Escena aparte (`saria.html`, copia de `ocarina.html`) en vez de parametrizar la de la tormenta: la ocarina, la cinta
  y la cámara son las mismas; cambia todo el mundo. Bosque de noche hecho con código: troncos torcidos con
  enredaderas de luz en espiral, un Gran Árbol propio (sin cara) con halo, casitas en tocón, hongos neón, rayos de
  luna, aurora y estrellas, luciérnagas y esporas, y hadas que orbitan la ocarina con estela (las del drop aceleran
  sumando fase, sin saltos). Los relámpagos se vuelven `pulsos`: el bosque destella y salen anillos de luz del piso.
- Audio en `saria.py`: reusa la ocarina, el bajo, el colchón y la subida de `ocarina.py` (se importa después de
  vaciar `sys.argv`), con un arpegio en semicorcheas que gira desde el segundo 0 (el gancho hipnótico), ambiente de
  bosque (viento, grillos) y barridos de campanitas de hada en las entradas. Fa lidio a 124 BPM.
- Botones de Switch 2 según guías del remake: Saria's Song = R A Y (C▶ = A, C◀ = Y). Por confirmar en el juego.

**Consecuencias.** Mismo riesgo de derechos que ADR-028. Si se hace un tercer tributo conviene sacar la ocarina a un
módulo común en vez de otra copia.

## ADR-030 · Beat explicado #5: trance que abre terminado y escenario de láseres (`escenas3d/trance.py`)

**Contexto.** El dueño pidió otro beat de la serie, ahora trance "chido, bailable y poderoso", que **empiece con todo
sonando** ("¿Sabes hacer esto?") y luego se arme desde cero. Eligió la paleta "amanecer de festival" y láseres de
festival como clímax. Pidió ir directo a la versión larga.

**Decisión.** Misma forma que `psytrance.py` (PATRONES + SECCIONES → golpes, audio, textos y guion), 138 BPM en Re
menor (Rem – Si♭ – Fa – Do). Carriles KICK · BAJO · CLAP · HATS · PAD · ARP; lo que define al género: bajo a
contratiempo, pad supersaw propio primero largo y luego **cortado en semicorcheas (trance gate)**, arpegio con eco,
sidechain en todo lo melódico y una melodía propia en supersaw de Surge XT ("Super") que no tiene carril: en la escena
son los láseres. El gancho usa capas con sufijo " INTRO" (como " MAL" en el psytrance): ya están armadas en el
cuadro 0 y se caen con un **tape stop** que frena el audio y también la imagen (`mapa_vis` congela el tiempo que se ve;
el texto sigue el tiempo real). La construcción va 1.5 dB abajo para que el drop pegue (−16.8 LUFS en el drop, como
el psytrance). Clímax: 152 piezas salen de las baldosas y arman un escenario (dos torres, armadura y un aro que gira)
con 11 emisores de láser que barren en tres figuras que cambian cada 2 compases; cada nota del lead hace destellar un
grupo y el aro corre colores. En el break, seis láseres suben al cielo desde atrás del tablero y crecen con la subida.

**Consecuencias.** El drop cae al 70 % (50.4 s de 71.7 s). Los láseres no apuntan a la cámara (de frente queman la
imagen con el bloom): siempre salen hacia los lados o hacia arriba.

**Revisión (10-nov).** El dueño pidió explicar más: el gancho ahora dice "Seguimos con los tutoriales de música
electrónica… ¿Quieres aprender a hacer esto?" con todo sonando y el tape stop cae en "Vamos paso a paso". La voz nombra
las notas de cada parte (kick afinado en Fa1, bajo Re – Si♭ – Fa – Do, las tres notas de cada acorde, el arpegio) y
salen flotando sobre su carril; el pad gana un **delay ping-pong** (corchea con puntillo) desde su propia sección, antes
suena seco para que se note el cambio; el sidechain se explica en dos frases. Las secciones que nombran notas empiezan en
el acorde que nombran y el drop cae en Rem (compás 40). Se quitó el dato de Alemania para no pasar de ~90 s.


## ADR-031 · Beat explicado #6: hard techno en un osciloscopio CRT (`hardtechno.py`)

**Contexto.** El dueño pidió un beat "dark" (hard techno / electro tipo Boys Noize) **con otra UI**, para que la serie
no se vea siempre como el secuenciador 3D. De tres propuestas (osciloscopio CRT, rack modular, bodega industrial)
eligió el osciloscopio. La prueba de 16 s le gustó y pidió el largo "súper bien".

**Decisión.** Script propio en Python (Pillow + numpy, sin Three.js ni `grabar.js`): la imagen es 2D y así cada cuadro
sale directo a ffmpeg. Toda la pantalla es el osciloscopio; cada instrumento es un canal (KICK, RUMBLE, HATS + CLAP,
STAB, GRITO) y su onda es **la envolvente real de su pista de audio** por una portadora visible, con barrido que
avanza por compás, rastro del compás anterior y persistencia de fósforo (cada cuadro hereda el anterior). 150 BPM en
Fa menor; síntesis con numpy reusando `clap`, `hat`, `eco`, `filtro` y `ping_pong` de `techno.py`. Abre terminado,
tape stop, y se enseña con antes/después: kick limpio → saturado, rumble encimado → con sidechain. Clímax distinto a
los anteriores: el osciloscopio pasa a **modo X-Y** y dibuja el NK, que se deshace en una figura de Lissajous y se
vuelve una calavera cuya quijada se abre con cada kick. Cierre: la pantalla se apaga como tele vieja (línea → punto).
Mismas secciones/JSON que los otros beats para pegar la voz con `techno_voz.py --beat beat-hardtechno` y volver a
renderizar con `hardtechno.py --datos … --audio …`.

**Consecuencias.** Render de ~80 s en unos 20–25 min en esta Mac. Los subtítulos van arriba (y≈230) para no tapar
las ondas. Falta agregar `beat-hardtechno` a `PEDAZOS`/`LUGAR_FRASE` de `techno_voz.py` cuando llegue la voz.

**Revisión (12-nov).** Al dueño le gustó mucho que el kick entre limpio y luego saturado, y pidió lo mismo con todo:
cada instrumento entra **limpio y luego con su proceso** (rumble seno → distorsionado → sidechain, hats limpios →
saturados, clap seco → con reverb, acorde de senos → FM + delay, sierra simple → saturación + bitcrush + filtro). Las
secciones aceptan capas `(compás 1, compás 2)` para el antes/después, cada caso lleva su etiqueta en la pantalla y la
onda cambia de forma (redonda → cuadrada / rota) además del sonido. El gancho va sin el sinte que grita: completo
sonaba demasiado saturado.
