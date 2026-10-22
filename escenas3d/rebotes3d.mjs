// Simula las bolitas de la esfera (rebotes3d.js) y guarda lo que necesita el sonido: cada golpe que suena,
// cada escape y el mapa de tiempo del glitch. La escena (escenas/rebotes.html) vuelve a simular igual.
//
// Uso: node rebotes3d.mjs ../out/.tmp/rebotes-esfera-3d.json [--semilla N] [--stats]
import fs from 'node:fs';
import path from 'node:path';
import { CFG, crearSimulacion, tiempoFuente, fuerzaGlitch } from './rebotes3d.js';

const args = process.argv.slice(2);
const opcion = (nombre, porDefecto) => {
  const i = args.indexOf(nombre);
  return i >= 0 ? args[i + 1] : porDefecto;
};
const cfg = { ...CFG, semilla: parseInt(opcion('--semilla', String(CFG.semilla)), 10) };
const stats = args.includes('--stats');

const sim = crearSimulacion(cfg);
const cuadros = Math.ceil(cfg.congelado * cfg.fps) + 2;
const totales = [], angulos = [];
for (let f = 0; f < cuadros; f++) {
  const e = sim.estado();
  totales.push(e.total);
  angulos.push(Math.round(e.angulo * 1e4) / 1e4);
  if (stats && (f % (cfg.fps * 5) === 0 || f === cfg.fps * 2)) {
    const t = f / cfg.fps;
    const escapes = sim.escapes.filter(x => x[0] < t).length;
    console.log(`${t.toFixed(0).padStart(3)}s  dentro: ${String(e.dentro).padStart(5)}  total: ${String(e.total).padStart(6)}  ` +
      `escapes: ${String(escapes).padStart(6)}  hueco: ${(e.angulo * 180 / Math.PI).toFixed(0)}°  golpes que suenan: ${sim.golpes.filter(g => g[0] < t).length}`);
  }
  sim.avanzar();
}
if (stats) {
  const primero = sim.escapes[0];
  console.log(`Primer escape: ${primero ? primero[0].toFixed(2) + ' s' : 'nunca'}`);
  process.exit(0);
}

const r4 = (x) => Math.round(x * 1e4) / 1e4;
const nVideo = Math.round(cfg.duracion * cfg.fps);
const datos = {
  total: cfg.duracion,
  fps: cfg.fps,
  cfg,
  // Para comprobar que la escena simula exactamente lo mismo
  firma: { bolitas: sim.bolitas.length, golpes: sim.golpes.length },
  golpes: sim.golpes.map(([t, id, x, y, z]) => [r4(t), id, r4(x), r4(y), r4(z)]),
  colores: sim.bolitas.map(b => b.color),
  nacen: sim.bolitas.map(b => r4(b.nace)),
  escapes: sim.escapes.map(([t, x, y, z]) => [r4(t), r4(x), r4(y), r4(z)]),
  totales,
  angulos,   // ancho del hueco (radianes) al inicio de cada cuadro de simulación
  // Por cada cuadro del video: segundo de la simulación que se muestra (el glitch lo traba) y fuerza del glitch
  mapa: Array.from({ length: nVideo }, (_, f) => r4(tiempoFuente(f / cfg.fps, cfg))),
  glitch: Array.from({ length: nVideo }, (_, f) => r4(fuerzaGlitch(f / cfg.fps, cfg))),
};
const salida = path.resolve(args[0] && !args[0].startsWith('--') ? args[0] : '../out/.tmp/rebotes-esfera-3d.json');
fs.mkdirSync(path.dirname(salida), { recursive: true });
fs.writeFileSync(salida, JSON.stringify(datos));
console.log(`Simulación: ${sim.bolitas.length} bolitas en total, ${sim.golpes.length} golpes suenan, ` +
  `${sim.escapes.length} escapes → ${salida}`);
