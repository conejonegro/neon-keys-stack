"""Neon Keys · Surge XT (sinte de estudio gratis) tocado desde Python con DawDreamer (ADR-026).

Corre en el entorno `.venv-synth`. Los presets de fábrica que se usan están en `plugins/surge-xt/patches/` (se bajan
del repositorio de Surge: resources/data/patches_factory/).
"""

import re
import tempfile
from pathlib import Path

import dawdreamer as daw
import numpy as np

SR = 44100
SURGE = Path(__file__).resolve().parent.parent / "plugins" / "surge-xt"


JUCE64 = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"


def cargar_preset(synth, fxp):
    """DawDreamer no lee los .fxp de Surge, pero el estado del plugin es el mismo parche: se toma el estado actual
    (XML de JUCE con el parche en su base64 propio), se cambia el parche por el del .fxp (sin su cabecera de 60
    bytes) y se vuelve a cargar."""
    parche = fxp.read_bytes()[60:]
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "estado"
        synth.save_state(str(ruta))
        xml = ruta.read_bytes()[8:].decode("utf-8")
        v = int.from_bytes(parche, "little")
        texto = "".join(JUCE64[(v >> (6 * i)) & 63] for i in range((len(parche) * 8 + 5) // 6))
        xml = re.sub(r"<IComponent>[^<]*</IComponent>", f"<IComponent>{len(parche)}.{texto}</IComponent>", xml)
        datos = xml.encode("utf-8")
        ruta.write_bytes(b"VC2!" + len(datos).to_bytes(4, "little") + datos)
        synth.load_state(str(ruta))


def tocar(notas, preset, n, gan_db=0.0):
    """Toca notas (t, nota, velocidad, duración) con un preset de Surge XT; devuelve el audio estéreo (n, 2)."""
    motor = daw.RenderEngine(SR, 256)
    synth = motor.make_plugin_processor("surge", str(SURGE / "Surge XT.vst3"))
    cargar_preset(synth, SURGE / "patches" / f"{preset}.fxp")
    for t, nota, vel, dur in notas:
        synth.add_midi_note(nota, vel, t, dur)
    motor.load_graph([(synth, [])])
    motor.render(n / SR)
    x = synth.get_audio().T.astype(np.float64)
    x = x[:n] if len(x) >= n else np.pad(x, ((0, n - len(x)), (0, 0)))
    return x * 10 ** (gan_db / 20)
