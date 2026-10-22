"""Recortes y texturas de "Temporada de Terror" (Cineclub Forever) → cutouts/*.png.

Fuentes: refs/ (carteles que mandó el dueño; pieza sin monetizar) y refs/true-love.png (logo del patrocinador).
Cada recorte es un pedazo de papel rasgado con su borde blanco fibroso, como en la intro de collage.

Uso: ../../.venv/bin/python preparar.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

AQUI = Path(__file__).resolve().parent
R = AQUI / "refs"
OUT = AQUI / "cutouts"
OUT.mkdir(exist_ok=True)


# ---------- ayudantes ----------

def borde_rasgado(w, h, semilla, inset=14, aspereza=7):
    """Máscara L de un rectángulo con orillas rasgadas (paseo aleatorio en cada lado)."""
    rng = np.random.default_rng(semilla)

    def orilla(n):
        paso = rng.normal(0, 1, n // 6 + 2).cumsum()
        paso = (paso - paso.mean()) / (paso.std() + 1e-6) * aspereza * 0.6
        fino = rng.normal(0, aspereza * 0.25, n)
        return np.interp(np.arange(n), np.linspace(0, n, len(paso)), paso) + fino

    arriba, abajo = orilla(w) + inset, h - inset - orilla(w)
    izq, der = orilla(h) + inset, w - inset - orilla(h)
    yy, xx = np.mgrid[0:h, 0:w]
    m = (yy > arriba[None, :]) & (yy < abajo[None, :]) & (xx > izq[:, None]) & (xx < der[:, None])
    return Image.fromarray((m * 255).astype(np.uint8))


def papel(im, semilla, fibra=10):
    """Pega `im` (RGB) sobre papel rasgado: la foto queda adentro y una orilla blanca fibrosa la rodea."""
    w, h = im.size
    afuera = borde_rasgado(w, h, semilla, inset=4, aspereza=9)
    adentro = borde_rasgado(w, h, semilla + 99, inset=4 + fibra, aspereza=6)
    rng = np.random.default_rng(semilla + 7)
    crema = np.clip(236 + rng.normal(0, 9, (h, w)), 200, 255).astype(np.uint8)
    base = Image.merge("RGB", [Image.fromarray(crema)] * 3)
    base.paste(im, (0, 0), adentro.filter(ImageFilter.GaussianBlur(0.8)))
    # fibras: la orilla exterior se deshilacha un poco
    ruido = Image.fromarray((rng.random((h, w)) > 0.35).astype(np.uint8) * 255)
    alfa = ImageChops.multiply(afuera, ImageChops.lighter(adentro.filter(ImageFilter.MaxFilter(5)), ruido))
    alfa = alfa.filter(ImageFilter.GaussianBlur(0.7))
    return Image.merge("RGBA", [*base.split(), alfa])


def tapar(im, mascara, pasos=60):
    """Rellena los píxeles marcados (texto encima de la foto) difundiendo los vecinos: un inpainting simple."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    m = np.asarray(mascara) > 0
    conocido = (~m).astype(np.float32)
    acum = a * conocido[..., None]
    for _ in range(pasos):
        acum_b = np.asarray(Image.fromarray(np.clip(acum, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(2))).astype(np.float32)
        peso = np.asarray(Image.fromarray((conocido * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(2))).astype(np.float32) / 255
        lleno = acum_b / np.maximum(peso[..., None], 1e-3)
        acum = np.where(m[..., None], lleno, a)
        conocido = np.maximum(conocido, (peso > 0.05).astype(np.float32))
        acum = acum * conocido[..., None]
    grano = np.random.default_rng(5).normal(0, 9, a.shape[:2])[..., None]
    return Image.fromarray(np.clip(np.where(m[..., None], acum + grano, a), 0, 255).astype(np.uint8))


def color_fuerte(im, umbral=45):
    """Máscara de píxeles saturados (las letras de color de los carteles)."""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    sat = a.max(2) - a.min(2)
    return Image.fromarray(((sat > umbral) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))


def gris(im):
    g = im.convert("L")
    return Image.merge("RGB", [g, g, g])


# ---------- recortes ----------

def rosemary_perfil():
    # solo ojo, nariz y boca: arriba el pelo está tapado por el título y el relleno se notaría
    im = Image.open(R / "rosemary-perfil.png").convert("RGB").crop((110, 730, 650, 1560))
    texto = color_fuerte(im).filter(ImageFilter.MaxFilter(9))          # letras lila + su sombra
    a = np.asarray(im.convert("L"))
    blanco = np.zeros(a.shape, bool)
    blanco[420:560, 0:200] = a[420:560, 0:200] > 120                   # "ALL OF THEM WITCHES!"
    texto = ImageChops.lighter(texto, Image.fromarray((blanco * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)))
    im = gris(tapar(im, texto))
    papel(im, 11).save(OUT / "rosemary-perfil.png")


def rosemary_manos():
    im = Image.open(R / "rosemary-manos.png").convert("RGB")
    g = np.asarray(im.convert("L"))
    oscuro = g < 80
    h, w = g.shape
    zona = np.zeros_like(oscuro)
    zona[80:1470, 75:1125] = True                 # dentro del marco negro
    zona[730:900, 460:715] = False                # Rosemary: cabeza y hombros
    zona[900:1040, 410:715] = False               # Rosemary: brazos
    zona[1040:1150, 300:900] = False              # la carriola
    zona[1150:1470, 300:945] = False
    m = Image.fromarray(((oscuro & zona) * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    tinta = Image.new("RGB", im.size, (14, 13, 15))
    manos = Image.merge("RGBA", [*tinta.split(), m])
    cuadrantes = {"mano-ai": (60, 60, 620, 700), "mano-ad": (600, 60, 1140, 760),
                  "mano-bi": (60, 700, 520, 1300), "mano-bd": (700, 700, 1140, 1300)}
    for nombre, caja in cuadrantes.items():
        p = manos.crop(caja)
        p.crop(p.getbbox()).save(OUT / f"{nombre}.png")
    # Rosemary con la carriola, como pedazo de papel (sin las manos: esas se animan aparte)
    limpio = im.copy()
    sombra = Image.fromarray((((g < 185) & zona) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))
    fondo = np.asarray(im)[80:500, 500:700].reshape(-1, 3)
    limpio.paste(tuple(int(v) for v in np.median(fondo, 0)), (0, 0), sombra)
    papel(limpio.crop((290, 540, 950, 1475)), 21).save(OUT / "rosemary-carriola.png")


def nosferatu():
    im = Image.open(R / "nosferatu.png").convert("RGB")
    a = np.asarray(im.convert("L"))
    # el texto blanco de la derecha: píxeles muy claros a la derecha de Ellen
    m = np.zeros(a.shape, bool)
    m[60:800, 400:736] = a[60:800, 400:736] > 150
    m[515:640, 390:565] = False                   # su brazo y su mano
    m[640:1000, 390:505] = False                  # el camisón
    mk = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    im = tapar(im, mk)
    papel(im.crop((0, 110, 736, 1104)), 31).save(OUT / "nosferatu.png")


def substance():
    im = Image.open(R / "substance.png").convert("RGB")
    papel(im.crop((0, 225, 700, 830)), 41).save(OUT / "substance-cara.png")
    papel(im.crop((360, 850, 556, 930)).resize((588, 240), Image.LANCZOS), 42, fibra=6).save(OUT / "substance-ojos.png")


def possession():
    im = Image.open(R / "possession.png").convert("RGB")
    papel(im.crop((150, 70, 590, 620)), 51).save(OUT / "possession.png")


# ---------- logo del patrocinador ----------

def true_love():
    """Blanco sobre negro → la luminosidad es la transparencia. Se agranda ×4 sin suavizar (letra pixel)."""
    im = Image.open(R / "true-love.png").convert("L")
    a = np.asarray(im).astype(np.float32)
    alfa = np.clip((a - 35) * 255 / 190, 0, 255).astype(np.uint8)
    blanco = Image.new("L", im.size, 255)
    logo = Image.merge("RGBA", [blanco, blanco, blanco, Image.fromarray(alfa)])
    logo = logo.crop(logo.getbbox())
    logo = logo.resize((logo.width * 4, logo.height * 4), Image.NEAREST)
    logo.save(OUT / "true-love.png")


# ---------- texturas ----------

def texturas():
    rng = np.random.default_rng(3)
    w, h = 1080, 1920
    for nombre, tono, var in [("papel-gris", 214, 7), ("papel-negro", 18, 5), ("papel-crema", 232, 7)]:
        base = rng.normal(0, var, (h // 2, w // 2))
        fibras = np.asarray(Image.fromarray(np.clip(128 + rng.normal(0, 60, (h // 2, w // 2)), 0, 255).astype(np.uint8))
                            .filter(ImageFilter.GaussianBlur(2))).astype(np.float32) - 128
        v = np.clip(tono + base + fibras * 0.25, 0, 255).astype(np.uint8)
        t = Image.fromarray(v).resize((w, h), Image.BICUBIC)
        if nombre == "papel-gris":                 # gris lavanda como el cartel de Rosemary
            t = Image.merge("RGB", [t, t, t.point(lambda x: min(255, x + 6))])
        t.convert("RGB").save(OUT / f"{nombre}.jpg", quality=90)
    # grano de película: 6 cuadros, se alternan cada 2 cuadros
    for i in range(6):
        g = np.clip(128 + rng.normal(0, 38, (h // 2, w // 2)), 0, 255).astype(np.uint8)
        Image.fromarray(g).resize((w, h), Image.NEAREST).save(OUT / f"grano-{i}.png")


def pedazo_negro():
    """Pedazo de papel negro rasgado: va detrás del logo del patrocinador (blanco) sobre la hoja gris."""
    hoja = Image.open(OUT / "papel-negro.jpg").convert("RGB").crop((100, 300, 900, 760))
    papel(hoja, 61).save(OUT / "pedazo-negro.png")


def rasgos():
    """Hojas completas partidas en dos por una rasgadura horizontal (para los cortes): cada mitad lleva su orilla
    blanca fibrosa, como cuando se rompe una hoja de revista."""
    w, h = 1080, 1920
    rng = np.random.default_rng(13)
    paso = rng.normal(0, 1, 40).cumsum()
    paso = (paso - paso.mean()) / paso.std() * 38
    linea = h / 2 + np.interp(np.arange(w), np.linspace(0, w, 40), paso) + rng.normal(0, 3, w)
    yy = np.mgrid[0:h, 0:w][0]
    for base in ("papel-negro", "papel-gris"):
        hoja = Image.open(OUT / f"{base}.jpg").convert("RGB")
        for lado, signo in (("arriba", -1), ("abajo", 1)):
            fibra = 10 + rng.random(w) * 12                     # ancho de la orilla blanca en cada columna
            d = (yy - linea[None, :]) * signo                   # >0 dentro de esta mitad
            dentro = d > 0
            orilla = dentro & (d < fibra[None, :])
            ruido = rng.random((h, w)) > 0.3
            alfa = np.where(dentro & ~orilla, 255, np.where(orilla & ruido, 255, 0)).astype(np.uint8)
            crema = np.clip(238 + rng.normal(0, 10, (h, w)), 200, 255).astype(np.uint8)
            px = np.asarray(hoja).copy()
            px[orilla] = np.stack([crema] * 3, -1)[orilla]
            im = Image.merge("RGBA", [*Image.fromarray(px).split(), Image.fromarray(alfa).filter(ImageFilter.GaussianBlur(0.6))])
            im.save(OUT / f"rasgo-{base.split('-')[1]}-{lado}.png")


if __name__ == "__main__":
    rosemary_perfil()
    rosemary_manos()
    nosferatu()
    substance()
    possession()
    true_love()
    texturas()
    rasgos()
    pedazo_negro()
    print("listo →", OUT)
