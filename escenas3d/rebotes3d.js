// Física de las bolitas en 3D (versión esfera de rebotes.py): las bolitas rebotan dentro de una esfera que
// tiene un hueco redondo que gira. Cada bolita que se escapa por el hueco hace nacer 2 en el centro.
// Es determinista (azar con semilla): la misma configuración da siempre el mismo video.
//
// La usan los dos lados: rebotes3d.mjs (en Node, saca los golpes para el sonido) y escenas/rebotes.html
// (en Chrome, vuelve a simular para dibujar). Por eso no depende de nada.

export const CFG = {
  semilla: 7,
  faseInicial: 2,      // hacia dónde mira el hueco al empezar (radianes)
  duracion: 70,        // segundos del video
  fps: 30,
  pasos: 8,            // pasos de física por cuadro (240 Hz)
  R: 3,                // radio de la esfera
  r: 0.1,              // radio de cada bolita
  gravedad: 4.2,
  vMin: 10.5, vMax: 14.5,
  maxDentro: 1400,     // tope de bolitas dentro de la esfera
  lleno: 56,           // segundo en que se llega al tope
  // Tiempos alineados al compás de la música (125 BPM → compás de 1.92 s)
  bpm: 125,
  climax: 57.6,        // compás 30: el hueco se abre de golpe y gira rápido (el "drop" de la música)
  glitch: 65.28,       // compás 34: empieza a trabarse
  congelado: 66.5,     // congelado total
  cierre: 67.3,        // corte al logo
  bombo: [[15.36, 53.76], [57.6, 65.28]],   // tramos con bombo (compases 8–28 y 30–34)
  // sonido: como máximo POR_VENTANA golpes suenan cada VENTANA segundos
  ventana: 0.03, porVentana: 3,
};

// ------------------------------------------------------------------ azar con semilla (mulberry32)
function azar(semilla) {
  let a = semilla >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ------------------------------------------------------------------ hueco
// Dirección del hueco: gira alrededor de un eje inclinado (barre frente, lados y atrás de la esfera).
// La fase acelera un poco con el tiempo y mucho en el clímax.
export function faseHueco(t, cfg = CFG) {
  const base = cfg.faseInicial + 0.55 * t + 0.0035 * t * t;
  const extra = t > cfg.climax ? 1.6 * (t - cfg.climax) ** 1.5 : 0;
  return base + extra;
}

export function dirHueco(t, cfg = CFG) {
  const f = faseHueco(t, cfg);
  // Círculo en un plano inclinado 35°, que a su vez cabecea despacio
  const inc = 0.6 + 0.25 * Math.sin(t * 0.21);
  const x = Math.cos(f), z = Math.sin(f);
  return [x, z * Math.sin(inc) + 0.25, z * Math.cos(inc)].map((v, _, a) => v / Math.hypot(...a));
}

// Cuántas bolitas "deberían" estar dentro en t: arranca rápido (gancho de los primeros segundos)
// y crece exponencial hasta el tope en cfg.lleno.
export function objetivo(t, cfg = CFG) {
  return Math.exp(Math.log(cfg.maxDentro) * Math.min(1, t / cfg.lleno) ** 0.7);
}

// ------------------------------------------------------------------ tiempo "trabado" (glitch final)
export function tiempoFuente(t, cfg = CFG) {
  const g = cfg.glitch;
  if (t < g) return t;
  if (t < g + 0.6) {  // cada pedacito de 0.1 s se repite dos veces
    const k = Math.floor((t - g) / 0.2);
    return g + k * 0.1 + (((t - g) - k * 0.2) % 0.1);
  }
  if (t < cfg.congelado) return g + 0.3 + Math.floor((t - g - 0.6) / 0.1) * 0.034;  // a saltitos
  return g + 0.3 + Math.floor((cfg.congelado - g - 0.6) / 0.1) * 0.034;             // congelado
}

export function fuerzaGlitch(t, cfg = CFG) {
  const ini = cfg.glitch - 0.35;
  if (t < ini || t >= cfg.cierre) return 0;
  return Math.min(1, (t - ini) / (cfg.cierre - 0.1 - ini));
}

// ------------------------------------------------------------------ simulación
// Avanza cuadro por cuadro. Cada bolita tiene un id fijo; en `bolitas` se guarda cuándo nació y su color.
// alCuadro(f, estado) se llama al inicio de cada cuadro (antes de moverse), con todas las bolitas vivas.
export function crearSimulacion(cfg = CFG) {
  const rnd = azar(cfg.semilla);
  const dt = 1 / (cfg.fps * cfg.pasos);
  const R = cfg.R, r = cfg.r;

  // Arreglos que crecen: posición, velocidad, id, fuera (ya escapó)
  let cap = 8192;
  let P = new Float64Array(cap * 3), V = new Float64Array(cap * 3);
  let ID = new Int32Array(cap), FUERA = new Uint8Array(cap);
  let n = 0;
  const bolitas = [];      // por id: { nace, color }
  const golpes = [];       // [t, id, x, y, z] (punto en la esfera) — solo los que suenan
  const escapes = [];      // [t, x, y, z]
  let total = 0, dentro = 0, cuadro = 0, angulo = 60 * Math.PI / 180;
  const porVentana = new Map();
  const ultimoSonido = [];

  function crecer() {
    cap *= 2;
    const P2 = new Float64Array(cap * 3); P2.set(P); P = P2;
    const V2 = new Float64Array(cap * 3); V2.set(V); V = V2;
    const I2 = new Int32Array(cap); I2.set(ID); ID = I2;
    const F2 = new Uint8Array(cap); F2.set(FUERA); FUERA = F2;
  }

  function nacer(t, x, y, z, vx, vy, vz, color) {
    if (n >= cap) crecer();
    P[3 * n] = x; P[3 * n + 1] = y; P[3 * n + 2] = z;
    V[3 * n] = vx; V[3 * n + 1] = vy; V[3 * n + 2] = vz;
    ID[n] = bolitas.length; FUERA[n] = 0;
    bolitas.push({ nace: t, color });
    ultimoSonido.push(-1);
    n++; total++; dentro++;
  }

  function direccionAzar() {
    const u = rnd() * 2 - 1, a = rnd() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    return [s * Math.cos(a), u, s * Math.sin(a)];
  }

  // Bolita inicial blanca (color -1)
  nacer(0, -0.4, 1.0, 0.3, 6.5, -3.2, 4.1, -1);

  function paso(t) {
    const h = dirHueco(t, cfg);
    // Ancho del hueco: se ajusta solo para seguir la curva objetivo (más ancho si faltan bolitas)
    let meta = 60 * Math.PI / 180 * Math.pow(objetivo(t, cfg) / Math.max(1, dentro), 1.0);
    meta = Math.min(t < 12 ? 62 : 40, Math.max(9, meta * 180 / Math.PI)) * Math.PI / 180;
    if (t > cfg.climax) meta = Math.max(meta, Math.min(68, 30 + 40 * (t - cfg.climax)) * Math.PI / 180);
    angulo += (meta - angulo) * Math.min(1, dt / 0.5);
    const cosHueco = Math.cos(angulo);

    const g = cfg.gravedad * dt;
    for (let i = 0; i < n; i++) {
      const k = 3 * i;
      V[k + 1] -= g;
      P[k] += V[k] * dt; P[k + 1] += V[k + 1] * dt; P[k + 2] += V[k + 2] * dt;
      if (FUERA[i]) continue;
      const d = Math.hypot(P[k], P[k + 1], P[k + 2]);
      if (d + r < R) continue;
      const nx = P[k] / d, ny = P[k + 1] / d, nz = P[k + 2] / d;
      const vn = V[k] * nx + V[k + 1] * ny + V[k + 2] * nz;
      if (vn <= 0) continue;
      if (nx * h[0] + ny * h[1] + nz * h[2] > cosHueco) {
        // Se escapa: sigue de largo con un empujón hacia afuera
        FUERA[i] = 1; dentro--;
        V[k] += nx * 2.5; V[k + 1] += ny * 2.5; V[k + 2] += nz * 2.5;
        escapes.push([t, nx * R, ny * R, nz * R]);
        const nuevas = Math.max(0, Math.min(2, cfg.maxDentro - dentro));
        for (let j = 0; j < nuevas; j++) {
          const [ax, ay, az] = direccionAzar();
          const v = 7 + rnd() * 3;
          nacer(t, ax * 0.05, ay * 0.05, az * 0.05, ax * v, ay * v, az * v, Math.floor(rnd() * 6));
        }
        continue;
      }
      // Rebote
      V[k] -= 2 * vn * nx; V[k + 1] -= 2 * vn * ny; V[k + 2] -= 2 * vn * nz;
      P[k] = nx * (R - r - 1e-3); P[k + 1] = ny * (R - r - 1e-3); P[k + 2] = nz * (R - r - 1e-3);
      const sp = Math.hypot(V[k], V[k + 1], V[k + 2]);
      const s = Math.min(cfg.vMax, Math.max(cfg.vMin, sp)) / sp;
      V[k] *= s; V[k + 1] *= s; V[k + 2] *= s;
      // ¿Suena? Máximo porVentana golpes cada ventana, y la misma bolita no antes de 0.15 s
      const id = ID[i];
      const w = Math.floor(t / cfg.ventana);
      const c = porVentana.get(w) || 0;
      if (c < cfg.porVentana && t - ultimoSonido[id] > 0.15) {
        porVentana.set(w, c + 1);
        ultimoSonido[id] = t;
        golpes.push([t, id, nx * R, ny * R, nz * R]);
      }
    }
    // Quita las que ya salieron lejos (compacta los arreglos)
    let j = 0;
    for (let i = 0; i < n; i++) {
      const k = 3 * i;
      if (FUERA[i] && (P[k + 1] < -14 || Math.abs(P[k]) > 16 || Math.abs(P[k + 2]) > 16 || P[k + 1] > 16)) continue;
      if (i !== j) {
        const q = 3 * j;
        P[q] = P[k]; P[q + 1] = P[k + 1]; P[q + 2] = P[k + 2];
        V[q] = V[k]; V[q + 1] = V[k + 1]; V[q + 2] = V[k + 2];
        ID[j] = ID[i]; FUERA[j] = FUERA[i];
      }
      j++;
    }
    n = j;
  }

  return {
    bolitas, golpes, escapes,
    get cuadro() { return cuadro; },
    // Estado actual (vistas sobre los arreglos internos: copiar si se quiere guardar)
    estado() {
      return { n, P, V, ID, FUERA, total, dentro, angulo, t: cuadro / cfg.fps };
    },
    // Avanza un cuadro completo
    avanzar() {
      for (let s = 0; s < cfg.pasos; s++) paso((cuadro * cfg.pasos + s) * dt);
      cuadro++;
    },
  };
}

// Golpe del bombo (1 justo en el golpe y se apaga rápido); 0 en los tramos sin bombo.
// La escena lo usa para que la esfera "lata" con la música.
export function pulsoBombo(t, cfg = CFG) {
  if (!cfg.bombo.some(([a, b]) => t >= a && t < b)) return 0;
  const pulso = 60 / cfg.bpm;
  return Math.exp(-((t % pulso) / pulso) * 6);
}
