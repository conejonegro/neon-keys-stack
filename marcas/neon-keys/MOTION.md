# MOTION.md · Neon Keys

Leer completo antes de diseñar, generar o animar cualquier cosa para Neon Keys. Cada color, fuente,
tiempo y regla de movimiento sale de aquí. Esto fija el look, no la ambición: cuando se pida "con todo",
se va con todo. Lo que diga **ASK ME** se pregunta, no se adivina.

Fuente de verdad: los valores de `neon_keys.py`, `datos_curiosos.py`, `rebotes.py` y `escenas3d/` (ADR-007,
016 y 017). Si un número de aquí no coincide con el código, manda el código y se corrige este archivo.

## 1. Colores

| Hex | Uso |
|---|---|
| `#080416` → `#1A082C` | Fondo: degradado vertical casi negro → morado noche (arriba → abajo) |
| `#FF28C8` | Cuadrícula del piso synthwave en perspectiva |
| `#00F0FF` | **Cian**: color principal A (mano derecha, la N del monograma, agudos) |
| `#FF32D2` | **Magenta**: color principal B (mano izquierda, la K, graves, halo de la marca) |
| `#00DCFF` | Halo de los títulos |
| `#FFFFFF` | Texto de títulos y subtítulos; núcleo de las partículas recién nacidas |
| `#FF78E6` | Resaltado de palabras clave en subtítulos |
| `#FFE146` `#5AFFA0` `#FF8C3C` `#AA64FF` | Acentos secundarios (solo en formatos con muchos objetos, como las bolitas) |

Regla: cian y magenta dominan siempre. Los acentos nunca pasan de ~1/3 de la pantalla. La luz es
**aditiva**: lo que brilla nace casi blanco y se enfría a su color.

## 2. Tipografía

- **Futura Bold** (índice 2 de `/System/Library/Fonts/Supplemental/Futura.ttc`): títulos, 92 px, blanco con
  halo cian. Etiquetas cortas en mayúsculas ("¿SABÍAS QUÉ?").
- **Avenir Next**: subtítulos y texto de apoyo. Ancho máximo 940 px, interlineado 98 px.
- Texto mínimo legible en el teléfono: 30 px sobre un lienzo de 1080 px de ancho.

## 3. Formato y zonas seguras

- 1080×1920, 30 fps, H.264 + AAC 192 kbps.
- Título arriba, centrado en y≈230. Nada importante por debajo de y=1600 (ahí van la descripción y los
  botones de TikTok) ni pegado a la derecha (columna de botones).
- Videos para monetizar: 62 s o más (ideal 70–90 s). Pruebas: ~10 s, y se dice que son pruebas.

## 4. Tiempo: cómo entra, cuánto dura, cómo sale

- **Gancho en el primer segundo**: algo ya se mueve en el cuadro 0. Nunca arrancar en negro ni con un logo.
  Lo que pasa en los primeros 5 s decide si cuenta la vista.
- **Entrada del piano**: ~3.24 s de notas cayendo antes del primer sonido (`LEAD_IN`).
- **Texto palabra por palabra**: cada palabra entra en 0.18 s, con 0.17 s entre palabras. Con voz en off,
  ~0.33 s por palabra.
- **Estructura de 70 s**: crecimiento parejo → subida → **clímax hacia el 80–85 % del video** (≈57–62 s
  en uno de 70 s) → **glitch final** (franjas + separación RGB, y el audio se traba con trozos repetidos y
  bitcrush) → corte al cierre.
- **Cierre**: 3.5 s con marca grande y llamada a seguir ("Sígueme para más", "Sígueme para la parte 2").
- Todo lo importante cae **a tiempo con la música** (compases y beats). Si hay BPM, los cambios van en el
  compás, no en un segundo cualquiera.

## 5. Cómo se mueve

- 30 fps. Todo es **función de `t`**: el mismo segundo da siempre el mismo cuadro (azar con semilla fija).
  Así una vista previa sale idéntica al video.
- Entradas rápidas que se frenan (ease-out). Los objetos físicos (bolitas, esquirlas) usan física real o
  fórmulas balísticas, no curvas inventadas.
- Cada golpe o nota = un evento visual (chispas, anillo de luz que se abre, tecla que se hunde) **y** un
  sonido. Nada suena sin verse ni se ve sin sonar.
- Cámara: casi quieta. Se aleja o gira solo en el clímax.
- Movimiento ambiental continuo (piso que avanza, sol retro, latido al BPM) para que nunca haya un cuadro
  muerto.

## 6. Textura y acabado

- Brillo neón con blur (bloom), sin quemar a blanco toda la pantalla: si el usuario dice "mucho brillo",
  se baja.
- Piso synthwave en perspectiva y sol retro de franjas en las escenas 3D.
- Partículas con halo y freno de aire. Fondo oscuro siempre, para que el neón resalte.
- El texto se mezcla encima en modo *screen*, sin bloom propio, para que se lea limpio.
- Audio hecho con código: piano con soundfont, o síntesis (plucks con eco, pad, bombo con sidechain,
  chiptune para el pixel art). Sin samples con derechos.

## 7. Cinco cosas que nunca hace

1. Nunca es lento ni contemplativo (Clair de Lune se descartó por "muy aburrido").
2. Nunca cambia el look aprobado (teclado, paleta cian/magenta, piso synthwave, fuentes) sin preguntar.
3. Nunca pone texto o logos generados por una IA de video: el texto va con código.
4. Nunca pone algo importante bajo y=1600 ni deja un cuadro inicial vacío.
5. Nunca repite el video anterior tal cual: cada uno cambia pieza, tramo, semilla, colores o formato
   (TikTok castiga lo de plantilla).

## 8. Un ejemplo bien hecho, toma por toma

`out/videos/bolitas/rebotes-esfera-3d.mp4` (1:10, "increíble" según el dueño):

1. **0 s**: la esfera neón de alambre ya gira con una bolita dentro. Título arriba. Cada rebote es una
   nota pluck con eco.
2. **0–10 s**: cada bolita que sale hace nacer dos. Crecimiento rápido para enganchar y contador que sube.
3. **10–55 s**: crecimiento exponencial al compás (125 BPM, Am–F–C–G). Entran hi-hats, bajo y una
   subida con redoble.
4. **57.6 s, el clímax (compás 30)**: el hueco se abre de golpe, gira rápido, la cámara se aleja y cae el
   drop.
5. **Compás 34**: glitch en video y audio con el mismo mapa de tiempo.
6. **Cierre**: marca y llamada a seguir.

## Cómo revisar antes de entregar

- Mirar cuadros sueltos: inicio, mitad, clímax y cierre. ¿Se lee todo en tamaño teléfono? ¿Algo cae bajo
  y=1600?
- Comparar contra este archivo, corregir lo que falle y solo entonces enseñarlo.
- `ffmpeg -v error -i VIDEO.mp4 -f null - 2>&1 | wc -l` debe dar 0.
