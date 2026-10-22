// Curvas suaves para los brazos "de fideo": puntos → curva Catmull-Rom → path SVG.

export type Punto = [number, number];

type Tramo = [Punto, Punto, Punto, Punto];

const tramos = (pts: Punto[]): Tramo[] => {
  const salida: Tramo[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] ?? p2;
    const c1: Punto = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2: Punto = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    salida.push([p1, c1, c2, p2]);
  }
  return salida;
};

export const curva = (pts: Punto[]): string => {
  const t = tramos(pts);
  return (
    `M ${pts[0][0]} ${pts[0][1]} ` +
    t.map(([, c1, c2, p]) => `C ${c1[0]} ${c1[1]} ${c2[0]} ${c2[1]} ${p[0]} ${p[1]}`).join(" ")
  );
};

// Puntos repartidos sobre la curva con su normal (para poner las ventosas a un lado del brazo).
export const muestras = (pts: Punto[], n: number, desde = 0.15, hasta = 0.85) => {
  const t = tramos(pts);
  const res: { x: number; y: number; nx: number; ny: number }[] = [];
  for (let k = 0; k < n; k++) {
    const u = desde + ((hasta - desde) * k) / Math.max(1, n - 1);
    const pos = u * t.length;
    const i = Math.min(t.length - 1, Math.floor(pos));
    const s = pos - i;
    const [a, b, c, d] = t[i];
    const m = 1 - s;
    const x = m * m * m * a[0] + 3 * m * m * s * b[0] + 3 * m * s * s * c[0] + s * s * s * d[0];
    const y = m * m * m * a[1] + 3 * m * m * s * b[1] + 3 * m * s * s * c[1] + s * s * s * d[1];
    const dx = 3 * m * m * (b[0] - a[0]) + 6 * m * s * (c[0] - b[0]) + 3 * s * s * (d[0] - c[0]);
    const dy = 3 * m * m * (b[1] - a[1]) + 6 * m * s * (c[1] - b[1]) + 3 * s * s * (d[1] - c[1]);
    const len = Math.hypot(dx, dy) || 1;
    res.push({ x, y, nx: -dy / len, ny: dx / len });
  }
  return res;
};

// Estrellita de 4 picos con lados curvos (como las del póster de referencia).
export const estrella = (cx: number, cy: number, r: number): string =>
  `M ${cx} ${cy - r} Q ${cx} ${cy} ${cx + r * 0.8} ${cy} Q ${cx} ${cy} ${cx} ${cy + r} ` +
  `Q ${cx} ${cy} ${cx - r * 0.8} ${cy} Q ${cx} ${cy} ${cx} ${cy - r} Z`;
