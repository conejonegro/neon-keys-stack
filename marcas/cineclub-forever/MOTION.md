# MOTION.md · Cineclub Forever

Leer completo antes de diseñar, generar o animar cualquier cosa para Cineclub Forever. Cada color, fuente,
tiempo y regla de movimiento sale de aquí (los valores exactos están en `marca.json`). Esto fija el look, no
la ambición: cuando se pida "con todo", se va con todo. Lo que diga **ASK ME** se pregunta, no se adivina.

Fuente: el sitio https://cineclub-forever.vercel.app/ (CSS y capturas del 21-oct-2026) y `logo.png`.
Este archivo es un primer borrador sin aprobar: el dueño lo revisa antes del primer video.

## 1. Colores

| Hex | Uso |
|---|---|
| `#0A0A0A` | Fondo: casi negro, como una sala con las luces apagadas |
| `#18181B` / `#27272A` | Tarjetas y bordes finos (paneles de "ciclo", fichas de película) |
| `#FFFFFF` | Títulos y el logo (invertido a blanco sobre el fondo oscuro) |
| `#FCBB00` | **Ámbar**, el único acento: etiquetas ("PELÍCULA DESTACADA", "CICLO ACTUAL"), botones, la palabra clave |
| `#FFD236` | Ámbar claro, para el brillo del proyector y el destello del acento |
| `#EDEDED` / `#99A1AF` | Texto de lectura / texto secundario (créditos, "Propuesta por…") |
| `#E40014` | Rojo cine: solo como luz de ambiente (telón, letrero de sala), nunca en texto |
| `#00D294` | El puntito verde de "EN CURSO", nada más |

Regla: casi todo es blanco y negro y el ámbar aparece en un solo lugar a la vez.
Excepción aprobada por el dueño (21-oct): una **temporada** puede traer su paleta propia, con un acento por cartel
(p. ej. Terror: lila, menta, rojo); el ámbar se queda en la apertura y el cierre (ADR-021). Es al revés de Neon Keys:
aquí la elegancia sale de lo que **no** brilla.

## 2. Tipografía

- **Montserrat Bold**: títulos grandes en tipo oración ("Los domingos", "Ciclo Snob"), blanco, interlineado
  apretado. En vertical: 110–150 px.
- **Montserrat SemiBold en MAYÚSCULAS**: etiquetas pequeñas en ámbar, 30–34 px, con mucho espaciado entre
  letras ("PELÍCULA DESTACADA", "DATO DE CINE").
- **Lato Regular**: texto de lectura y subtítulos, 44–52 px, gris claro `#EDEDED`.
- Texto mínimo legible en el teléfono: 30 px sobre 1080 px de ancho.

## 3. Formato y zonas seguras

- 1080×1920, 30 fps (el movimiento se puede animar "en dos": cambiar pose cada 2 cuadros, para que se sienta
  a 24/12 fps de cine). H.264 + AAC.
- Etiqueta y título arriba (y≈230–420) o en el tercio inferior alto (y≈1200–1550), como en la portada del
  sitio. Nada importante por debajo de y=1600 ni pegado a la derecha.
- Videos para monetizar: 62 s o más (ideal 70–90 s). Pruebas: ~10 s.

## 4. Tiempo: cómo entra, cuánto dura, cómo sale

- **Gancho en el primer segundo**: una pregunta o un dato raro ya en pantalla, o la luz del proyector que se
  enciende. Nunca empezar con el logo solo.
- **Entradas**: fundidos desde negro y textos que suben 20–40 px mientras aparecen (0.5–0.7 s, ease-out
  suave). Las etiquetas ámbar entran primero y el título 0.2 s después.
- **Ritmo**: más pausado que Neon Keys pero nunca lento. Una idea por pantalla, cada 2.5–4 s.
- **Cortes**: a negro o con un parpadeo de proyector (2–3 cuadros), no con glitch.
- **Cierre**: logo completo en blanco al centro, firma del sitio debajo y llamada a la acción
  ("Más cine en Cineclub Forever"), 3–3.5 s.

## 5. Cómo se mueve

- Cámara: lentos acercamientos (Ken Burns) y paneos suaves, como un travelling. Nada de sacudidas.
- Todo es función de `t` (grano y parpadeo con semilla fija): la vista previa sale igual que el video.
- El logo se trata como una pieza gráfica: se revela por partes (perfiles que aparecen uno a uno, de humano a
  ave) o con el haz de luz del proyector que lo barre.
- Sonido hecho con código: zumbido y traqueteo del proyector, golpe grave en los cortes, cuerdas o piano
  suave de fondo (sin bandas sonoras de películas).

## 6. Textura y acabado

- Grano de película fino en todo el cuadro y un poco de viñeta (esquinas más oscuras).
- Leve temblor de cuadro ("gate weave", 1–2 px) y polvo o rayas muy de vez en cuando.
- Degradado negro de abajo hacia arriba detrás del texto, como en la portada del sitio, para que siempre
  se lea.
- Opcional: franjas negras de pantalla ancha arriba y abajo en escenas de "película".

## 7. Cinco cosas que nunca hace

1. Nunca usa neón, synthwave ni colores saturados (eso es Neon Keys).
2. Nunca usa clips, carteles, fotogramas ni música de películas con derechos en videos para monetizar.
3. Nunca inventa un dato de cine: todo se verifica.
4. Nunca pone más de un acento ámbar a la vez ni texto en rojo.
5. Nunca redibuja ni cambia el logo: se usa el archivo.

## 8. Un ejemplo bien hecho, toma por toma

ASK ME. Todavía no hay un video aprobado. Cuando el primero guste, se describe aquí toma por toma.
