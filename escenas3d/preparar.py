"""Prepara un tramo de MIDI para una escena 3D: notas en JSON + audio WAV.

Reutiliza la lectura del MIDI y la síntesis de piano de neon_keys.py, así el audio suena igual
que en los videos 2D. Los tiempos del JSON ya son tiempos del video (incluyen el LEAD_IN).

Uso:
  .venv/bin/python escenas3d/preparar.py midi/marcha-turca.mid --inicio 0 --duracion 10
  → out/.tmp/marcha-turca-3d.json y out/.tmp/marcha-turca-3d.wav
  Con --titulo/--subtitulo/--cierre el JSON lleva además las capas de texto (para escenas/piano.html).
"""
import argparse
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import neon_keys as nk  # noqa: E402


def png_base64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def capa_cierre(texto):
    """Como make_outro_layer de neon_keys.py, pero con el texto de abajo a elegir."""
    capa = nk.glow_text(Image.new("RGB", (nk.W, nk.H)), (nk.W / 2, 820), "NEON KEYS",
                        nk.font(nk.FONT_BOLD, 130, 2), (255, 255, 255), nk.BRAND_GLOW, radius=26)
    return nk.glow_text(capa, (nk.W / 2, 980), texto, nk.font(nk.FONT_TEXT, 54, 0),
                        (255, 255, 255), nk.TITLE_GLOW, radius=14)


def main():
    ap = argparse.ArgumentParser(description="Prepara notas y audio de un MIDI para una escena 3D.")
    ap.add_argument("midi")
    ap.add_argument("--inicio", type=float, default=None,
                    help="segundo de la canción donde empieza (por defecto, la primera nota)")
    ap.add_argument("--duracion", type=float, default=10.0, help="segundos de música")
    ap.add_argument("--nombre", default=None, help="nombre base de salida (por defecto, <midi>-3d)")
    ap.add_argument("--titulo", default=None, help="título arriba (como en los videos 2D)")
    ap.add_argument("--subtitulo", default=None)
    ap.add_argument("--cierre", default=None,
                    help="texto bajo NEON KEYS en el cierre (sin --titulo no hay capas de texto)")
    ap.add_argument("--soundfont", default=str(RAIZ / "soundfonts" / "FluidR3Mono_GM.sf3"))
    args = ap.parse_args()

    midi = Path(args.midi)
    notas, eventos = nk.load_midi(midi)
    if not notas:
        sys.exit("El MIDI no tiene notas.")
    inicio = args.inicio if args.inicio is not None else max(0.0, notas[0].start - 0.2)
    largo = min(args.duracion, notas[-1].end - inicio)
    total = nk.LEAD_IN + largo + nk.OUTRO

    tramo = [n for n in notas if inicio <= n.start <= inicio + largo]
    datos = {
        "total": round(total, 3),
        "notaMin": min(n.pitch for n in tramo) - 2,
        "notaMax": max(n.pitch for n in tramo) + 2,
        "notas": [
            {"n": n.pitch,
             "ini": round(nk.LEAD_IN + n.start - inicio, 4),
             "dur": round(min(n.end, inicio + largo) - n.start, 4),
             "mano": n.hand,
             "vel": n.velocity}
            for n in tramo
        ],
    }
    # Capas de texto ya dibujadas con Pillow (mismas fuentes y halo que el 2D); la escena las mezcla
    # en modo "screen", igual que neon_keys.py
    if args.titulo:
        datos["capas"] = {
            "titulo": png_base64(nk.make_title_layer(args.titulo, args.subtitulo)),
            "marca": png_base64(nk.make_brand_layer()),
            "cierre": png_base64(capa_cierre(args.cierre or "Sígueme para más")),
            "outro": nk.OUTRO,
        }

    tmp = RAIZ / "out" / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    base = tmp / (args.nombre or f"{midi.stem}-3d")
    base.with_suffix(".json").write_text(json.dumps(datos))
    print(f"Audio: {largo:.1f}s de música desde {inicio:.1f}s …")
    nk.render_audio(eventos, args.soundfont, inicio, largo, total, base.with_suffix(".wav"))
    print(f"Notas: {base.with_suffix('.json')} ({len(tramo)} notas, video de {total:.1f}s)")
    print(f"Audio: {base.with_suffix('.wav')}")


if __name__ == "__main__":
    main()
