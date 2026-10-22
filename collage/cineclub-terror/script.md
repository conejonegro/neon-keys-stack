# Cineclub Forever · Temporada de Terror (prueba de 15 s, vertical 1080×1920, 30 fps "en dos")

Imagen corporativa: Cineclub presenta la temporada de terror de octubre, patrocinada por True Love Design.
Collage de recortes como la intro (`../cineclub-intro/`), más pausado: una idea por pantalla, cada texto ≥1.2 s.
Se arma con **HyperFrames** (`hf/index.html`, HTML + GSAP). Referencias: carteles de *Rosemary's Baby* (dos),
*Nosferatu* (2024), *The Substance* y *Possession* (en `refs/`, pieza sin monetizar).

Paleta especial de temporada: negro y papel gris/crema, **un acento por cartel** (lila `#D888F2`, menta
`#9FE0A8`, rojo `#C8141F`; Nosferatu en blanco). El ámbar `#FCBB00` de Cineclub solo en la apertura y el cierre.

| t | escena | texto (fuente) | corte de salida |
|---|---|---|---|
| 0–1.6 | Papel negro, el haz del proyector titubea y se enciende | CINECLUB FOREVER (Montserrat, ámbar) · *presenta* (Pinyon Script) | destello de proyector |
| 1.6–4.0 | Rosemary de perfil (papel rasgado) cae y se acerca | *Una nueva* (Pinyon) · TEMPORADA (Rye, lila, letra por letra) | la hoja se cierra y se rasga |
| 4.0–6.4 | Nosferatu: la sombra en el arco, empujón lento | ENTRÉGATE A LA OSCURIDAD (Cormorant) · *de Terror* (UnifrakturMaguntia, se enciende como vela) | destello |
| 6.4–8.6 | Possession: la franja azul baja y golpea | TODO · OCTUBRE (Shrikhand, menta, letras que ondulan) | la hoja se cierra y se rasga |
| 8.6–10.8 | The Substance: cara con eco movido, la tira de ojos se estampa | cada semana (Lato) · UN CLÁSICO · DEL MIEDO (Anton, rojo) | rasgo en papel gris |
| 10.8–12.6 | Rosemary con la carriola sobre papel gris; las manos negras se estiran desde las orillas | PATROCINADO POR · logo True Love sobre papel negro (aparece en escalones) | destello |
| 12.6–15 | Logo de Cineclub barrido por la luz del proyector | TEMPORADA DE TERROR (ámbar) · Más cine en Cineclub Forever · sitio | fundido a negro |

Sonido (`audio/terror.py`): cuerdas graves en Re, caja de música desafinada (canción de cuna) en Rosemary, chelo
en "de Terror", pizzicato que sube con cada letra de OCTUBRE, trémolo disonante que crece, latido que se acelera,
proyector, papel que se rasga y golpes en cada estampado.

## Comandos

```bash
../../.venv/bin/python preparar.py                        # refs/ → cutouts/ (recortes, logo sin fondo, texturas)
cp cutouts/* hf/assets/                                   # la composición solo ve hf/
../../.venv/bin/python audio/terror.py hf/assets/terror.wav
cd hf && npx hyperframes check                            # revisión de HyperFrames
npx hyperframes snapshot --at 1.2,3.6,5.9,8.2,10.4,12.3,14.3 --no-end --describe false -o ../review/st
npx hyperframes render -o ../../../out/.tmp/cineclub-terror-prueba.mp4 --quality delivery --fps 30
```

`--describe false` evita que HyperFrames mande los cuadros a Gemini si hay una clave en el entorno.
No usar `npm run publish` (sube el proyecto a internet).
