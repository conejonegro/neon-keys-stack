"""Recortes de la intro de collage de Cineclub Forever → cutouts/*.png (con transparencia).

Fuentes: refs/fuentes/ (Wikimedia Commons, todas de dominio público; ver refs/fuentes/creditos.json) y el logo
de marcas/cineclub-forever/logo.png. La claqueta se dibuja con código.

Uso: ../../.venv/bin/python preparar_recortes.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).resolve().parent
F = AQUI / "refs" / "fuentes"
OUT = AQUI / "cutouts"
MARCA = AQUI.parent.parent / "marcas" / "cineclub-forever"
OUT.mkdir(exist_ok=True)


def fondo_fuera(gris, umbral=200):
    """Dibujo de tinta sobre blanco: el blanco que toca el borde se vuelve transparente; el de adentro queda
    como papel blanco opaco (así el recorte parece una calcomanía)."""
    tinta = (np.asarray(gris) < umbral).astype(np.uint8) * 255
    # cerrar huecos chicos de la línea para que el relleno no se cuele
    cerrada = Image.fromarray(tinta).filter(ImageFilter.MaxFilter(7))
    relleno = cerrada.copy()
    w, h = relleno.size
    for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if relleno.getpixel(p) == 0:
            ImageDraw.floodfill(relleno, p, 128)
    fuera = np.asarray(relleno) == 128
    alfa = np.where(fuera, 0, 255).astype(np.uint8)
    alfa = Image.fromarray(alfa).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    rgba = Image.merge("RGBA", [gris, gris, gris, alfa])
    return rgba.crop(rgba.getbbox())


def proyector():
    im = Image.open(F / "reel.png").convert("L")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 175], fill=255)                     # la palabra "REEL"
    d.line([(745, 140), (668, 214)], fill=255, width=46)             # flecha izquierda
    d.line([(1045, 140), (1132, 226)], fill=255, width=46)           # flecha derecha
    d.rectangle([0, 1450, 90, 1520], fill=255)                       # puntito suelto
    fondo_fuera(im).save(OUT / "proyector.png")
    # las dos bobinas sueltas (para que giren encima del proyector) y una como calcomanía
    for nombre, (cx, cy, r) in {"bobina_izq": (450, 612, 418), "bobina_der": (1414, 616, 424)}.items():
        caja = (cx - r, cy - r, cx + r, cy + r)
        b = Image.open(F / "reel.png").convert("L").crop(caja)
        m = Image.new("L", b.size, 0)
        ImageDraw.Draw(m).ellipse([2, 2, 2 * r - 2, 2 * r - 2], fill=255)
        Image.merge("RGBA", [b, b, b, m.filter(ImageFilter.GaussianBlur(1))]).save(OUT / f"{nombre}.png")


def luna():
    im = Image.open(F / "luna.jpg").convert("L")
    m = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(m)
    d.ellipse([490 - 370, 430 - 371, 490 + 370, 430 + 371], fill=255)
    d.polygon([(70, 300), (150, 228), (430, 318), (440, 440), (330, 505), (100, 425)], fill=255)   # el cohete
    rgba = Image.merge("RGBA", [im, im, im, m.filter(ImageFilter.GaussianBlur(1.5))])
    rgba.crop(m.getbbox()).save(OUT / "luna.png")
    print("luna: bbox", m.getbbox(), "→ ojo derecho en px del recorte:", (595 - m.getbbox()[0], 405 - m.getbbox()[1]))


def fotos():
    Image.open(F / "nosferatu.jpg").convert("RGB").save(OUT / "nosferatu.png")
    c = Image.open(F / "cartel_lumiere.jpg").convert("RGB")
    c.crop((0, 0, int(c.width * 0.955), c.height)).save(OUT / "lumiere.png")    # sin la carta de color del escaneo
    k = Image.open(F / "kinetoscopio.jpg").convert("L")
    k = k.crop((0, 0, k.width, int(k.height * 0.95)))                           # sin la firma
    fondo_fuera(k, umbral=185).save(OUT / "kinetoscopio.png")


def claqueta():
    """Claqueta clásica en blanco y negro, dibujada con código."""
    w, h = 900, 760
    im = Image.new("RGBA", (w + 40, h + 160))
    d = ImageDraw.Draw(im)
    negro, blanco = (12, 12, 12, 255), (245, 242, 235, 255)
    d.rounded_rectangle([0, 170, w, h], radius=26, fill=negro)
    def barra():
        b = Image.new("RGBA", (w, 130))
        db = ImageDraw.Draw(b)
        db.rounded_rectangle([0, 0, w - 1, 129], radius=18, fill=negro)
        rayas = Image.new("RGBA", (w, 130))
        dr = ImageDraw.Draw(rayas)
        for k in range(-1, 8):
            x = k * 130 + 40
            dr.polygon([(x, 10), (x + 65, 10), (x + 5, 119), (x - 60, 119)], fill=blanco)
        mascara = Image.new("L", (w, 130), 0)
        ImageDraw.Draw(mascara).rounded_rectangle([8, 8, w - 9, 121], radius=12, fill=255)
        b.paste(rayas, (0, 0), Image.composite(rayas.split()[3], Image.new("L", (w, 130), 0), mascara))
        return b

    # barra fija y brazo de arriba abierto unos grados (gira sobre la bisagra de la izquierda)
    im.alpha_composite(barra(), (0, 170))
    brazo = barra().rotate(9, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(brazo, (0, 165 - brazo.height + 6))
    d.rectangle([0, 296, w, 306], fill=negro)
    fuente = ImageFont.truetype(str(MARCA / "fuentes" / "Montserrat-Bold.ttf"), 64)
    chica = ImageFont.truetype(str(MARCA / "fuentes" / "Montserrat-SemiBold.ttf"), 40)
    for y in (430, 560):
        d.line([(40, y), (w - 40, y)], fill=blanco, width=4)
    d.line([(w // 2, 430), (w // 2, 560)], fill=blanco, width=4)
    d.text((w // 2, 370), "CINECLUB FOREVER", font=fuente, fill=blanco, anchor="mm")
    d.text((w // 4, 495), "ESCENA  1", font=chica, fill=blanco, anchor="mm")
    d.text((3 * w // 4, 495), "TOMA  1", font=chica, fill=blanco, anchor="mm")
    d.text((w // 2, 640), "GUADALAJARA · JAL.", font=chica, fill=blanco, anchor="mm")
    im.crop(im.getbbox()).save(OUT / "claqueta.png")


def logo():
    # el archivo trae fondo blanco opaco: la transparencia sale de la tinta (oscuro = opaco)
    im = Image.open(MARCA / "logo.png").convert("RGBA")
    fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
    gris = Image.alpha_composite(fondo, im).convert("L")
    tinta = gris.point(lambda v: 255 - v)
    for nombre, tono in (("logo", 12), ("logo_blanco", 245)):
        Image.merge("RGBA", [Image.new("L", im.size, tono)] * 3 + [tinta]).save(OUT / f"{nombre}.png")


if __name__ == "__main__":
    proyector()
    luna()
    fotos()
    claqueta()
    logo()
    for p in sorted(OUT.glob("*.png")):
        print(p.name, Image.open(p).size)
