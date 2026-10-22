// Física de las bolitas "armonía": bolitas pesadas y ligeras caen en un tazón invisible sobre una plataforma.
// Simula con Rapier (física real) y guarda, para cada cuadro de video, la posición de cada bolita y,
// aparte, cada golpe fuerte (cuándo, qué bolita, qué tan fuerte) para que bolitas_sonido.py lo haga sonar.
//
// Uso: node bolitas.mjs [segundos] [salida.json]
//      node bolitas.mjs 5 ../out/.tmp/bolitas-armonia.json
import fs from 'node:fs';
import path from 'node:path';
import RAPIER from '@dimforge/rapier3d-compat';

const SEGUNDOS = parseFloat(process.argv[2] || '5');
const SALIDA = path.resolve(process.argv[3] || '../out/.tmp/bolitas-armonia.json');
const FPS = 30;
const PASOS = 8;                 // pasos de física por cuadro (240 Hz: sin que las bolitas atraviesen paredes)
const ANTES = 0.6;               // segundos simulados antes del cuadro 0 (ya vienen cayendo al empezar)

// Tazón: se abre de radio 0.75 (abajo) a 1.35 (arriba), 2.4 de alto, sobre un disco de radio 2.6
const R_ABAJO = 0.75, R_ARRIBA = 1.35, ALTO = 2.4, R_DISCO = 2.6, SEGMENTOS = 40;

const TIPOS = {
  // freno = cuánto les cuesta rodar (sin esto las esferas ruedan sin fin y no se apilan)
  pesada: { radio: 0.14, densidad: 6, rebote: 0.25, friccion: 1.0, freno: 6 },
  ligera: { radio: 0.085, densidad: 1, rebote: 0.4, friccion: 0.9, freno: 4 },
};
const N_PESADAS = 170, N_LIGERAS = 560;
const GOLPE_MIN = 0.9;           // cambio de velocidad (m/s) para que un golpe suene
const DESCANSO = 0.12;           // una bolita no vuelve a sonar antes de esto

await RAPIER.init();
const mundo = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
mundo.timestep = 1 / (FPS * PASOS);

// Disco (plataforma)
mundo.createCollider(RAPIER.ColliderDesc.cylinder(0.06, R_DISCO).setTranslation(0, -0.06, 0).setFriction(0.6));

// Pared del tazón: tablitas delgadas inclinadas hacia afuera, en círculo
const inclinacion = Math.atan((R_ARRIBA - R_ABAJO) / ALTO);
const rMedio = (R_ABAJO + R_ARRIBA) / 2;
const largo = Math.hypot(R_ARRIBA - R_ABAJO, ALTO);
for (let i = 0; i < SEGMENTOS; i++) {
  const th = (i / SEGMENTOS) * Math.PI * 2;
  // giro = (eje Y, th) · (eje X, inclinación)
  const qy = [0, Math.sin(th / 2), 0, Math.cos(th / 2)];
  const qx = [Math.sin(inclinacion / 2), 0, 0, Math.cos(inclinacion / 2)];
  const q = {
    x: qy[3] * qx[0] + qy[0] * qx[3] + qy[1] * qx[2] - qy[2] * qx[1],
    y: qy[3] * qx[1] - qy[0] * qx[2] + qy[1] * qx[3] + qy[2] * qx[0],
    z: qy[3] * qx[2] + qy[0] * qx[1] - qy[1] * qx[0] + qy[2] * qx[3],
    w: qy[3] * qx[3] - qy[0] * qx[0] - qy[1] * qx[1] - qy[2] * qx[2],
  };
  const ancho = (Math.PI * 2 * R_ARRIBA) / SEGMENTOS * 0.6;
  mundo.createCollider(
    RAPIER.ColliderDesc.cuboid(ancho, largo / 2, 0.05)
      .setTranslation((rMedio + 0.05) * Math.sin(th), ALTO / 2, (rMedio + 0.05) * Math.cos(th))
      .setRotation(q)
      .setFriction(0.8),
  );
}

// Programa de caída: pesadas al centro primero (forman el domo), ligeras por la orilla después.
// Ángulo dorado para que se repartan parejo.
const ORO = Math.PI * (3 - Math.sqrt(5));
const programa = [];
for (let i = 0; i < N_PESADAS; i++) {
  const r = 0.5 * Math.sqrt((i % 40) / 40);
  programa.push({ t: -ANTES + i * 0.0105, tipo: 'pesada', x: r * Math.cos(i * ORO), z: r * Math.sin(i * ORO), y: 3.2 });
}
for (let i = 0; i < N_LIGERAS; i++) {
  const a = i * ORO;
  programa.push({ t: 0.9 + i * 0.0062, tipo: 'ligera', x: 1.0 * Math.cos(a), z: 1.0 * Math.sin(a), y: 3.3 + (i % 3) * 0.25 });
}
programa.sort((a, b) => a.t - b.t);

const bolitas = [];   // { cuerpo, tipo, vPrev, ultimoGolpe }
const golpes = [];    // [t, índice, fuerza]
const cuadros = [];   // por cuadro: [x,y,z, x,y,z, ...] de las bolitas ya nacidas (en orden de nacimiento)
const totalCuadros = Math.round(SEGUNDOS * FPS);
let siguiente = 0;
const dt = mundo.timestep;
const K0 = Math.round(ANTES * FPS * PASOS);          // paso en el que empieza el video (t = 0)
const KFIN = K0 + totalCuadros * PASOS;

for (let k = 0; k < KFIN; k++) {
  const t = -ANTES + k * dt;
  // Foto del cuadro antes de avanzar la física
  if (k >= K0 && (k - K0) % PASOS === 0) {
    const pos = [];
    for (const b of bolitas) {
      const p = b.cuerpo.translation();
      pos.push(+p.x.toFixed(3), +p.y.toFixed(3), +p.z.toFixed(3));
    }
    cuadros.push(pos);
  }
  while (siguiente < programa.length && programa[siguiente].t <= t) {
    const p = programa[siguiente++];
    const tipo = TIPOS[p.tipo];
    const cuerpo = mundo.createRigidBody(RAPIER.RigidBodyDesc.dynamic().setTranslation(p.x, p.y, p.z).setLinvel(0, -2, 0).setAngularDamping(tipo.freno).setCcdEnabled(true));
    mundo.createCollider(RAPIER.ColliderDesc.ball(tipo.radio).setDensity(tipo.densidad).setRestitution(tipo.rebote).setFriction(tipo.friccion), cuerpo);
    bolitas.push({ cuerpo, tipo: p.tipo, vPrev: { x: 0, y: -2, z: 0 }, ultimoGolpe: -9 });
  }
  mundo.step();
  const tDespues = t + dt;
  bolitas.forEach((b, i) => {
    const v = b.cuerpo.linvel();
    // Golpe = cambio brusco de velocidad (la gravedad sola cambia 0.04 m/s por paso)
    const dv = Math.hypot(v.x - b.vPrev.x, v.y - b.vPrev.y, v.z - b.vPrev.z);
    if (dv > GOLPE_MIN && tDespues - b.ultimoGolpe > DESCANSO && tDespues >= 0) {
      golpes.push([+tDespues.toFixed(4), i, +dv.toFixed(2)]);
      b.ultimoGolpe = tDespues;
    }
    b.vPrev = v;
  });
}

const datos = {
  total: SEGUNDOS,
  fps: FPS,
  tazon: { rAbajo: R_ABAJO, rArriba: R_ARRIBA, alto: ALTO, rDisco: R_DISCO },
  bolitas: bolitas.map(b => ({ tipo: b.tipo, radio: TIPOS[b.tipo].radio })),
  cuadros,
  golpes,
};
fs.mkdirSync(path.dirname(SALIDA), { recursive: true });
fs.writeFileSync(SALIDA, JSON.stringify(datos));
const kb = Math.round(fs.statSync(SALIDA).size / 1024);
console.log(`Física lista: ${bolitas.length} bolitas, ${cuadros.length} cuadros, ${golpes.length} golpes → ${SALIDA} (${kb} KB)`);
