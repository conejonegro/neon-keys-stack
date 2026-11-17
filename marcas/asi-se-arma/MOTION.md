# MOTION.md · Así se arma

Leer completo antes de diseñar o animar cualquier cosa para Así se arma. Los valores exactos están en
`marca.json`. Borrador del 17-nov-2026: paleta tapatía elegida por el dueño; el resto se ajusta con la primera
prueba (`escenas3d/escenas/torta.html`). Lo que diga **ASK ME** se pregunta.

## 1. Colores (paleta tapatía)

| Hex | Uso |
|---|---|
| `#F4ECDD` | Crema cálido: pared y fondo |
| `#BFE3F2` | Azul cielo claro: cielo, degradado de arriba |
| `#2453A6` | Azul talavera: azulejos, detalles, el contorno de las etiquetas |
| `#E7B7A3` | Cantera rosa: muros, barra, piso |
| `#F2C14E` | Amarillo maíz: palabra resaltada en los textos, pan |
| `#6FA85A` | Verde nopal: plantas, detalles |
| `#C8402F` | Rojo chile: salsas, acentos fuertes |
| `#9B7FD1` | Morado jacaranda: cebolla, flores, acentos |
| `#2B2230` | Contorno: línea oscura suave en los bordes de todo lo 3D |

Luz de día. Las sombras van azuladas, nunca negras.

## 2. Tipografía

- **Lilita One** (`fuentes/LilitaOne-Regular.ttf`), redonda y gruesa, para títulos, etiquetas y subtítulos.
- Texto blanco con contorno grueso oscuro (como un sticker), sin halo ni fondo detrás. La palabra clave va en
  amarillo maíz.
- Mínimo legible: 44 px sobre 1080 de ancho.

## 3. Formato y zonas seguras

1080×1920, 30 fps. Títulos arriba (y≈230–420). Etiquetas pegadas a la pieza que señalan. Nada importante debajo
de y=1600.

## 4. Tiempo

- Gancho en el primer segundo: ya está cayendo algo.
- Cada pieza entra con rebote (cae, se aplasta, se asienta en ~0.4 s) y su etiqueta aparece 0.15 s después.
- Una idea por paso; la cámara se mueve sin parar, despacio.

## 5. Cómo se mueve

- 3D low-poly / de bloques con sombreado de caricatura (3 tonos) y contorno oscuro suave.
- Personaje: cocinerito de bloques (mandil, gorro) que acompaña cada paso con un gesto.
- Etiquetas con línea y puntito que señalan la pieza (estilo tortilladora).
- Todo depende solo de `t`: la vista previa sale igual que el video.

## 6. Acabado

Limpio, sin grano ni bloom. Viñeta muy leve.

## 7. Cinco cosas que nunca hace

1. Nunca usa neón ni la paleta cian/magenta (eso es Neon Keys).
2. Nunca fondo oscuro de noche.
3. Nunca texto con halo o caja detrás.
4. Nunca sombras negras puras.
5. Nunca mete una pieza sin decir qué es.

## 8. Ejemplo bien hecho

ASK ME: falta que se apruebe la primera prueba.
