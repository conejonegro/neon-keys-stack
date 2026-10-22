---
name: render-video
description: Genera un video de piano Neon Keys a partir de un MIDI siguiendo el proceso completo (tramo, duración, vista previa, render en segundo plano, verificación y entrega). Usar cuando el usuario pida hacer, generar o renderizar un video de una canción, un clip, un teaser o una "parte 2".
argument-hint: "<midi o canción> [duración del video] [título]"
---

# Render de un video Neon Keys

Sigue estos pasos en orden. No te saltes la verificación final. Responde siempre en español.

## 1. Elegir la pieza

- El MIDI debe estar en `midi/` en kebab-case. Si no existe, búscalo en Mutopia Project (dominio público)
  o usa un arreglo propio de `arreglos/`.
- Si la canción es moderna (con derechos), **avisa del riesgo** antes de seguir (TikTok puede silenciarla
  o sacarla de Creator Rewards).
- Si es lenta, comenta que al usuario le gustan las piezas rápidas y enérgicas.

## 2. Elegir el tramo

- **Video completo / parte N:** `--inicio` donde terminó la parte anterior (ver `CLAUDE.md`).
- **Clip corto:** busca el clímax midiendo notas por segundo y prefiere un tramo que termine en el final
  de la pieza:

  ```bash
  .venv/bin/python - midi/CANCION.mid 13.3 <<'EOF'
  import sys, mido
  path, win = sys.argv[1], float(sys.argv[2])
  t, onsets = 0.0, []
  for msg in mido.MidiFile(path):
      t += msg.time
      if msg.type == "note_on" and msg.velocity > 0:
          onsets.append(t)
  end = onsets[-1]
  best = max((sum(s <= o < s + win for o in onsets), s) for s in [x / 2 for x in range(int((end - win) * 2) + 1)])
  print(f"duración pieza {end:.1f}s · tramo más denso: --inicio {best[1]:.1f} ({best[0] / win:.1f} notas/s)")
  print(f"tramo final: --inicio {max(0, end - win):.1f}")
  EOF
  ```

## 3. Calcular la duración

`--duracion = (segundos de video deseados) − 6.74` (entrada 3.24 s + cierre 3.5 s).
Ejemplos: 20 s → `13.3`, 70 s → `63.26`, 80 s → `73.3`.

- Si dura **menos de 62 s**, avisa que no paga en Creator Rewards (sirve como prueba o teaser). Ideal 70–90 s.
- Antes de entregar, repasa el checklist de `docs/TIKTOK.md`.

## 4. Vista previa

Genera 2 o 3 cuadros y míralos con Read antes del render completo:

```bash
.venv/bin/python neon_keys.py midi/CANCION.mid --titulo "Título" --subtitulo "Autor" \
  --inicio X --duracion Y --preview 5
```

El PNG queda junto a la salida (`out/videos/CANCION.preview-5s.png`). Revisa: título dentro de la zona segura
(y≈230), nada importante por debajo de y=1600, teclado y colores sin cambios respecto al look aprobado.
Borra los PNG de vista previa al terminar.

## 5. Render completo

Mismo comando sin `--preview`. Si el video dura más de ~30 s, córrelo **en segundo plano**
(`run_in_background`). Escribe en `out/.tmp/` y se mueve a `out/videos/` al terminar (un clip de prueba o teaser: `--salida out/pruebas/CANCION-prueba.mp4`): **no abras ni sirvas el
`.mp4` mientras se genera**.

## 6. Verificar

```bash
ffmpeg -v error -i out/videos/CANCION.mp4 -f null - 2>&1 | wc -l    # debe dar 0
ffprobe -v error -show_entries format=duration -of csv=p=0 out/videos/CANCION.mp4
```

Extrae y mira cuadros de inicio, mitad, clímax y cierre:

```bash
for t in 1 MITAD CLIMAX FINAL; do
  ffmpeg -v error -y -ss $t -i out/videos/CANCION.mp4 -frames:v 1 "$SCRATCHPAD/cuadro-$t.png"
done
```

## 7. Entregar y registrar

- Dile al usuario, en palabras sencillas, dónde quedó el archivo, cuánto dura y si sirve para monetizar.
- Agrega la entrada del video en `out/videos.json` (titulo, descripcion con gancho y "La Bamba"-style
  palabras buscables, hashtags 8–10, ia, estado "listo", nota si es teaser). Así aparece en la web con el
  botón de copiar. Lee el archivo antes y conserva lo que ya tiene (el usuario marca estados desde la web).
- Agrega la fila a la tabla "Videos hechos" de `CLAUDE.md`.
- Agrega una línea a la entrada de hoy en `docs/BITACORA.md` (créala arriba si no existe).
- Si hubo una decisión técnica nueva, regístrala en `docs/ADR.md`.
