/* grade_cineclub.js — filtro de marca de Cineclub Forever, última pasada de cada cuadro (cargar después de grade.js y antes de film.js).
 * Reemplaza la paleta por anclas de grade.js (que tiñe de verde los grises y de morado el cobalto): aquí cada píxel va a
 *   · ámbar #FCBB00 si es un color cálido y saturado (rojo → amarillo), más oscuro o claro según su brillo, o
 *   · blanco y negro (blancos en crema #F1ECE2, negros en tinta) si es cualquier otro color.
 * Así todo lo que dibuja el motor (tiras, iris, caleidoscopio) y las fotos quedan en negro, crema y un solo acento ámbar.
 * Se apaga con ?pal=orig.
 */
(function () {
  'use strict';
  if (!window.SCENES || new URLSearchParams(location.search).get('pal') === 'orig') return;
  const AMBAR = [252, 187, 0], CREMA = [241, 236, 226], TINTA = [10, 10, 10];
  const sstep = (a, b, x) => { const k = Math.min(1, Math.max(0, (x - a) / (b - a))); return k * k * (3 - 2 * k); };
  const N = 64, lut = new Uint8ClampedArray(N * N * N * 3);
  for (let ri = 0; ri < N; ri++) for (let gi = 0; gi < N; gi++) for (let bi = 0; bi < N; bi++) {
    const r = ri * 4 + 2, g = gi * 4 + 2, b = bi * 4 + 2, mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    const sat = mx > 0 ? (mx - mn) / mx : 0;
    let h = 0; // tono en grados
    if (mx !== mn) { if (mx === r) h = 60 * (((g - b) / (mx - mn)) % 6); else if (mx === g) h = 60 * ((b - r) / (mx - mn) + 2); else h = 60 * ((r - g) / (mx - mn) + 4); }
    if (h < 0) h += 360;
    const calido = h <= 62 ? 1 : h <= 80 ? 1 - sstep(62, 80, h) : h >= 345 ? 1 : h > 300 ? sstep(300, 345, h) : 0;   // rojo → amarillo (y rosa → rojo)
    const w = calido * sstep(0.28, 0.6, sat) * sstep(40, 110, mx);
    const L = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    const k = Math.min(1, (0.8 * mx + 0.2 * L * 255 * 1.35) / 245);   // brillo del ámbar: amarillo = ámbar pleno, rojo ≈ 83 %
    const o = ((ri * N + gi) * N + bi) * 3;
    for (let c = 0; c < 3; c++) {
      const gris = TINTA[c] + (CREMA[c] - TINTA[c]) * Math.pow(L, 1.05);
      lut[o + c] = gris * (1 - w) + AMBAR[c] * k * w;
    }
  }
  const ov = window.SCENES.overlay;
  window.SCENES.overlay = async (ctx, t, cut) => {
    if (ov) await ov(ctx, t, cut);
    const cw = ctx.canvas.width, ch = ctx.canvas.height, im = ctx.getImageData(0, 0, cw, ch), p = im.data;
    for (let i = 0; i < p.length; i += 4) {
      const o = (((p[i] >> 2) * N + (p[i + 1] >> 2)) * N + (p[i + 2] >> 2)) * 3;
      p[i] = lut[o]; p[i + 1] = lut[o + 1]; p[i + 2] = lut[o + 2];
    }
    ctx.putImageData(im, 0, 0);
  };
})();
