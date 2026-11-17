# Reglas del proyecto Neon Keys

## Comunicación

1. Responder siempre en **español**. Los comentarios del código y los mensajes de la CLI también van en español.
2. Explicar en términos sencillos: el dueño del canal no es programador de video. Decir qué cambió y dónde
   quedó el archivo.

## Música y derechos

3. Usar solo MIDIs de **dominio público** (Mutopia Project: mutopiaproject.org) o arreglos propios.
   Las canciones modernas tienen derechos: TikTok puede silenciar el video o sacarlo de Creator Rewards.
   Si el usuario pide una moderna, avisarle del riesgo antes de hacerla.
4. Al usuario le gustan las piezas **rápidas, enérgicas y reconocibles**. Evitar piezas lentas
   (Clair de Lune se descartó por aburrida).
5. Para clips cortos, buscar el **clímax**: medir la densidad de notas por segundo del MIDI y elegir el
   tramo más intenso, idealmente terminando en el final de la pieza.

## TikTok

Detalle y fuentes de las reglas de Creator Rewards: `docs/TIKTOK.md` (incluye checklist antes de subir).

6. Los videos para monetizar deben durar **62 s o más** (Creator Rewards pide "más de 1 minuto"; se deja
   margen). Ideal 70–90 s: el pago extra mide retención hasta los 90 s. Clips más cortos están bien como
   prueba o teaser, pero hay que decirlo.
7. Respetar las zonas seguras de la interfaz de TikTok: el título arriba (y≈230), nada importante en la
   franja inferior (y > 1600), donde van la descripción y los botones.
8. Si se usa contenido generado por IA (por ejemplo, intros de fal.ai), recordar marcarlo como
   "contenido generado por IA" al subirlo (obligatorio si es realista).
8b. Los primeros 5 s deben enganchar (una vista cuenta a partir de 5 s) y cada video debe variar respecto
   al anterior (pieza, tramo o formato): TikTok castiga el contenido repetitivo o "de plantilla".

## Identidad visual

9. **No cambiar el look aprobado** sin preguntar: teclado (el usuario lo aprobó como está, aunque salga
   ancho en piezas de rango amplio), paleta cian/magenta, fondo oscuro con piso synthwave, fuentes
   Futura Bold y Avenir Next, marca "NEON KEYS".
10. No pedirle texto a las IAs de video: lo escriben mal. Los títulos y logos se ponen con código/ffmpeg.

## Render y entrega

11. Nunca abrir ni servir un `.mp4` mientras se está generando. El render escribe en `out/.tmp/` y se mueve a
    `out/videos/<tipo>/` (terminados) u `out/pruebas/<tipo>/` (pruebas) solo al terminar (un archivo se corrompió cuando se abrió en QuickTime a medio escribir).
12. Antes de entregar un video, **verificar** que esté sano:
    ```bash
    ffmpeg -v error -i out/videos/TIPO/VIDEO.mp4 -f null - 2>&1 | wc -l   # debe dar 0
    ```
    y revisar visualmente algunos cuadros (inicio, mitad, clímax, cierre).
13. Usar `--preview T` para probar cambios de diseño antes de generar el video completo.
13b. Videos animados con personaje (pixel art, datos curiosos): **1)** diseñar el personaje y mostrar una
    imagen para aprobarla; **2)** preguntar si se hace una prueba de ~10 s; **3)** solo entonces el video
    completo (1 min+). No saltarse pasos.
14. Los renders largos (más de ~30 s de video) van en segundo plano para no bloquear la conversación.

## Entorno

15. Correr siempre con `.venv/bin/python`.
16. No instalar con Homebrew nada que tenga que compilarse (macOS 12 compila desde fuente y tarda horas).
    Preferir wheels de pip, binarios estáticos o `pip install --no-deps` si una dependencia opcional no compila.
17. No arrancar el servidor web (`app.py`) a menos que el usuario lo pida; él lo arranca desde su terminal.

## Código

18. Nombres de archivo en kebab-case: `midi/nombre-cancion.mid` → `out/videos/piano/nombre-cancion.mp4`.
    Cada video va en la subcarpeta de su tipo (`piano/`, `beats/`, `datos/`, `bolitas/`, `podcast/`, `caricatura/`, `cineclub/`, `tienda/`, `otros/`). Las pruebas van en `out/pruebas/<tipo>/` y terminan en `-prueba` cuando conviven con la versión final.
19. Mantener `neon_keys.py` como un solo script autocontenido; la web (`app.py`) solo lo invoca como
    subproceso, no duplica su lógica.
20. Al tomar una decisión técnica importante, registrarla en `docs/ADR.md`.
