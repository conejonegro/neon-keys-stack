# Cineclub Forever · intro de collage (prueba de 10 s, vertical 1080×1920, 24 fps, 120 BPM)

Skill: `paper-collage-film` (motor y transiciones) con escenas propias para vertical en `comp/scenes.js`.
Color: `comp/grade_cineclub.js` (lo cálido → ámbar `#FCBB00`; lo demás → blanco y negro con crema).

| t | música | lo que se ve | texto en pantalla |
|---|---|---|---|
| 0–0.5 | groove bajo filtro | hoja de papel negra con círculo ámbar; el proyector cae y aterriza en 0.5, las bobinas giran | CINECLUB FOREVER ✦ GDL (0.5) |
| 0.875 | clic | el proyector se enciende: destello en la lente y haz de luz | |
| 1.0 | DROP + rasgado | la hoja se rompe por el centro → bandas diagonales | CINE DE CULTO (1.08) |
| 1.75 | whoosh | Nosferatu (1922) cruza por el centro | |
| 2.0 | golpe de papel | el cartel del Cinématographe Lumière (1896) se estampa | |
| 2.5 | rasgado | barrido de papel → la Luna de *Viaje a la Luna* (1902) | OBRAS MAESTRAS (2.58) |
| 2.65–3.46 | subida | empujón al ojo de la Luna; iris de papel 2.9–3.4 | |
| 3.5–4.5 | remolino | caleidoscopio con anillos de bobinas y claquetas; vuelan claqueta, kinetoscopio y Luna (4.2/4.3/4.4) | |
| 4.5 | golpe | la claqueta cae | CICLO ACTUAL (4.55) · CICLO (4.6) · SNOB (5.0) · ● EN CURSO (5.25) |
| 5.5–5.95 | redoble | la hoja cae, cohete de tiras se lleva una bobina | |
| 6.0 | golpe del título | CINECLUB / FOREVER (Montserrat Black) + estallido, haces de proyector | GUADALAJARA · JALISCO (6.5) |
| 7.5–7.92 | rasgado largo | la hoja se rasga → franja crema con el logo real | |
| 8.0–8.5 | tartamudeo | parpadeo de looks del logo solo dentro de la franja (ámbar → periódico → puntos → tinta) | |
| 8.5–10 | golpe final | confeti, empujón lento | ÚNETE AL CINECLUB · cineclub-forever.vercel.app · GUADALAJARA · JALISCO |

## Imágenes (todas de dominio público, Wikimedia Commons; ver `refs/fuentes/creditos.json`)

- Proyector con bobinas: *Reel (PSF).png* (Pearson Scott Foresman), sin la palabra "REEL".
- *Le Voyage dans la Lune* (Georges Méliès, 1902).
- Max Schreck en *Nosferatu* (F. W. Murnau, 1922).
- Cartel del *Cinématographe Lumière* (Marcellin Auzolle, 1896).
- Kinetoscopio de Edison (grabado).
- Claqueta: dibujada con código. Logo: `marcas/cineclub-forever/logo.png`.

## Comandos

```bash
../../.venv/bin/python preparar_recortes.py                   # refs/fuentes + logo → cutouts/
node tools/capture.mjs comp/index.html review/st --stills 0.95,3.3,6.9,9.5
node tools/render_audio.mjs "$PWD/audio/score.html" audio/score.wav && afconvert -f m4af -d aac -b 256000 audio/score.wav audio/score.m4a
tools/render_film.sh final audio/score.m4a "$PWD/../../out/.tmp/cineclub-intro-collage-prueba.mp4"
```
