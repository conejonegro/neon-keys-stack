/* scenes.js — Cineclub Forever, intro de collage de papel rasgado, 10 s VERTICAL (1080×1920, 24 fps, 120 BPM).
 * Motor y transiciones del skill paper-collage-film (CL / CLX); escenas re-acomodadas para 9:16 (ver ../script.md).
 *   0.25–0.5 el proyector cae (4 dibujos) y aterriza · 0.5 etiqueta · 0.875 se enciende (haz de luz + destello) · 1.0 la hoja se rasga
 *   1.0–2.5 CINE DE CULTO: bandas diagonales; Nosferatu cruza (centro 1.75); el cartel Lumière se estampa en 2.0
 *   2.5 barrido de papel → la Luna de Méliès · 2.65–3.46 empujón al ojo · iris 2.9–3.4 (caleidoscopio en el centro)
 *   3.5–4.5 caleidoscopio (anillos de bobinas y claquetas; voladores 4.2/4.3/4.4; agujero 4.33–4.42)
 *   4.5–5.5 CICLO ACTUAL: claqueta 4.5, letras de recorte "CICLO" / "SNOB" · 5.5–5.92 sube la cámara, cohete de tiras con la bobina
 *   6.0 CINECLUB / FOREVER (9 dibujos expo-out) + estallido · 7.5–7.92 la hoja se rasga → franja con el logo real
 *   8.0–8.5 parpadeo de looks SOLO dentro de la franja · 8.5 ÚNETE AL CINECLUB + sitio + ciudad, empujón lento a 10.0
 * Todo es función de t; el movimiento va "en dos" (q(t)); lo que no depende de t está en caché.
 * Colores: se dibuja con la paleta original del motor y grade.js la pasa a 'cineclub' (negro, crema y ámbar).
 */
(function () {
  'use strict';
  const { W, H, clamp, lerp, prog, E } = ENG;
  const K = KIT, X = CLX, U = CLX._, C = CL.C, DEG = Math.PI / 180;

  /* ---------- textos: cada palabra en pantalla vive aquí ---------- */
  const COPY = {
    marca: 'CINECLUB FOREVER ✦ GDL',
    culto: 'CINE DE CULTO',
    maestras: 'OBRAS MAESTRAS',
    cicloTag: 'CICLO ACTUAL',
    ciclo1: 'CICLO', ciclo2: 'SNOB',
    enCurso: '● EN CURSO',
    title: ['CINECLUB', 'FOREVER'], titleFont: '"Montserrat"',
    unete: 'ÚNETE AL CINECLUB',
    url: 'cineclub-forever.vercel.app',
    ciudad: 'GUADALAJARA · JALISCO',
  };
  // 8.0–8.5: 4 looks del logo dentro de la franja, de claro a oscuro (la luminosidad solo baja; 8.5 regresa al crema)
  const FLICK = ['ambar', 'periodico', 'puntos', 'tinta'];
  const FLICK_FR = [0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 3];

  K.setup({ bars: [1.0, 2.5, 4.5, 6.0, 7.5, 8.5] });

  /* ---------- ayudantes (los mismos del ejemplo del skill) ---------- */
  const q = (t) => Math.floor(t * 12 + 1e-6) / 12;
  const drawingIdx = (t, t0) => Math.floor((t - t0) * 12 + 1e-6);
  const BUFS = new Map();
  function buf(name, w = W, h = H) {
    let c = BUFS.get(name); if (!c) { c = document.createElement('canvas'); c.width = w; c.height = h; BUFS.set(name, c); }
    const x = c.getContext('2d'); x.setTransform(1, 0, 0, 1, 0, 0); x.globalAlpha = 1; x.globalCompositeOperation = 'source-over'; x.filter = 'none'; x.clearRect(0, 0, c.width, c.height);
    return c;
  }
  const PAD = 170;
  function padBuf(name) { const c = buf(name, W + 2 * PAD, H + 2 * PAD), x = c.getContext('2d'); x.fillStyle = '#FBF8F1'; x.fillRect(0, 0, c.width, c.height); x.translate(PAD, PAD); c.pad = PAD; return c; }
  const ONCE = new Map();
  const once = (k, fn) => { if (!ONCE.has(k)) ONCE.set(k, fn()); return ONCE.get(k); };
  const mkc = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  const paperPat = (ctx) => ctx.createPattern(CL.paper(C.paper, 3, { tex: 0.8 }), 'repeat');
  const pc = (x, shape, fill, o) => CL.piece(x, shape, fill, Object.assign({ cache: false }, o));
  async function zoomAbout(ctx, z, fx, fy, fn, rot = 0) { ctx.save(); ctx.translate(fx, fy); if (rot) ctx.rotate(rot); ctx.scale(z, z); ctx.translate(-fx, -fy); await fn(); ctx.restore(); }
  const TAG = { size: 46, font: 'sans' };
  const worldTag = (ctx, t, t0, str, color, o = {}) => X.tag(ctx, o.x ?? 70, o.y ?? 1470, str, Object.assign({ t: q(t), t0, color, anchor: 'left', rot: -0.03, tape: 'top' }, TAG, o));
  const fondoOscuro = (x, seed) => pc(x, [-200, -200, W + 400, H + 400], { color: C.ink, speck: 0.4 }, { seed, amp: 0, shadow: false });

  /* ---------- precalentado (una vez, dentro de __seek con las fuentes listas) ---------- */
  const TEAR = { y0: Math.round(H * 0.30), y1: Math.round(H * 0.63), seed: 5, flapW: 330 };
  const LOGO = { x: W / 2, y: Math.round((TEAR.y0 + TEAR.y1) / 2), h: 500 };
  const TTL = { size: 0, off: 0 };
  let WARM = null;
  const warm = () => WARM || (WARM = (async () => {
    await CL.preload();
    const m = mkc(8, 8).getContext('2d'); m.font = `900 100px ${COPY.titleFont}`;
    const tw = Math.max(...COPY.title.map((s) => [...s].reduce((a, c) => a + m.measureText(c).width, 0)));
    TTL.size = 100 * (W * 0.84) / Math.max(1, tw);
    await X.warm({ iris: 6, kaleido: 8, title: { lines: COPY.title, size: TTL.size, font: COPY.titleFont }, tear: TEAR,
      cuts: ['proyector', 'bobina_izq', 'bobina_der', 'luna', 'claqueta', 'kinetoscopio', 'logo', 'logo_blanco'] });
    const P = U.titleSprite(COPY.title, TTL.size, { font: COPY.titleFont }); TTL.off = P.bottom - P.ay;
  })());

  /* ======================================================================= transiciones de papel (del ejemplo) */
  const SHEETS = new Map();
  const sheetPath = (edges, seed) => { const k = edges.join('') + seed; if (!SHEETS.has(k)) SHEETS.set(k, CL.torn({ rect: [-170, -170, W + 340, H + 340], edges }, seed, { amp: 18, white: [3, 17], bite: 3 })); return SHEETS.get(k); };
  function drawSheet(ctx, cv, ox, oy, edges, seed, sh = [0, 14]) {
    const T = sheetPath(edges, seed);
    ctx.save(); ctx.translate(ox, oy);
    ctx.save(); ctx.shadowColor = 'rgba(10,16,30,0.5)'; ctx.shadowBlur = 34; ctx.shadowOffsetX = sh[0]; ctx.shadowOffsetY = sh[1]; ctx.fillStyle = paperPat(ctx); ctx.fill(T); ctx.restore();
    ctx.save(); ctx.clip(T.inner); ctx.drawImage(cv, -(cv.pad || 0), -(cv.pad || 0)); ctx.restore();
    ctx.restore();
  }
  async function wipe(ctx, t, t0, drawA, drawB, o) {
    const ks = o.ks || [0.34, 0.74, 0.95], i = drawingIdx(t, t0);
    if (i >= ks.length || i < 0) { await drawB(ctx, t); return; }
    const k = ks[i], [dx, dy] = o.from, A = padBuf('wipeA'), B = padBuf('wipeB');
    await drawA(A.getContext('2d'), t); await drawB(B.getContext('2d'), t);
    const pa = (o.push ?? 0.28) * k, sa = 1 + (o.zoomA ?? 0.06) * k;
    ctx.save(); ctx.translate(W / 2 - dx * W * pa, H / 2 - dy * H * pa); ctx.rotate((o.roll || 0) * k * DEG); ctx.scale(sa, sa); ctx.drawImage(A, -W / 2 - PAD, -H / 2 - PAD); ctx.restore();
    const ox = dx * (W + 340) * (1 - k), oy = dy * (H + 340) * (1 - k);
    if (o.rollB) { ctx.save(); ctx.translate(W / 2 + ox, H / 2 + oy); ctx.rotate(o.rollB * (1 - k) * DEG); ctx.translate(-W / 2 - ox, -H / 2 - oy); }
    drawSheet(ctx, B, ox, oy, o.edges, o.seed || 3, [-dx * 22, -dy * 22 + 10]);
    if (o.rollB) ctx.restore();
    if (o.speed) await X.speed(ctx, t, o.speed);
  }
  const RIP = (() => {
    const r = CL.R(901), pts = []; for (let y = -140; y <= H + 140; y += 70) pts.push([W / 2 + (r() - 0.5) * 90 + (y - H / 2) * 0.06, y]);
    const top = pts[0], bot = pts[pts.length - 1];
    const L = [[-500, top[1], 0], ...pts.map((p, i) => [p[0], p[1], i < pts.length - 1 ? 1 : 0]), [-500, bot[1], 0]];
    const Rr = [[top[0], top[1], 0], [W + 500, top[1], 0], [W + 500, bot[1], 0], ...pts.slice().reverse().map((p, i) => [p[0], p[1], i < pts.length - 1 ? 1 : 0])];
    return { L: CL.torn({ poly: L }, 911, { amp: 14, white: [4, 18], bite: 4 }), R: CL.torn({ poly: Rr }, 912, { amp: 14, white: [4, 18], bite: 4 }) };
  })();
  function ripDraw(ctx, k, cv) {
    for (const side of [-1, 1]) {
      const T = side < 0 ? RIP.L : RIP.R, dx = side * (22 + k * W * 0.7);
      ctx.save(); ctx.translate(W / 2 + dx, H / 2 + k * k * 120); ctx.rotate(side * k * 6 * DEG); ctx.translate(-W / 2, -H / 2);
      ctx.save(); ctx.shadowColor = 'rgba(10,16,30,0.5)'; ctx.shadowBlur = 28; ctx.shadowOffsetX = side * 10; ctx.shadowOffsetY = 12; ctx.fillStyle = paperPat(ctx); ctx.fill(T); ctx.restore();
      ctx.save(); ctx.clip(T.inner); ctx.drawImage(cv, -PAD, -PAD); ctx.restore();
      ctx.restore();
    }
  }

  /* ======================================================================= 0–1 · HOJA + PROYECTOR */
  // proyector.png 1820×1652: bobinas en (434,440) r418 y (1398,444) r424; lente ≈ (1470,1078)
  const PROJ = { x: 540, y: 1360, h: 760 }, PS = PROJ.h / 1652, PW = 1820 * PS;
  const pLocal = (px, py) => [-PW / 2 + px * PS, -PROJ.h + py * PS];
  const REELS = [['bobina_izq', ...pLocal(434, 440), 2 * 418 * PS, 1], ['bobina_der', ...pLocal(1398, 444), 2 * 424 * PS, -1]];
  const LENTE = (() => { const [lx, ly] = pLocal(1470, 1078); return { x: PROJ.x + lx, y: PROJ.y + ly }; })();
  const T_ON = 0.875;
  const pageLayer = () => CL.layer('cc_page', async (x) => {
    await fondoOscuro(x, 301);
    await pc(x, { circle: [540, 980, 560] }, { color: C.sun, brush: 0.6 }, { seed: 302, amp: 12, halftone: { color: 'rgba(240,122,46,0.92)', cell: 17, angle: 30, r: [0.42, 0.03], grad: [540, 1540, 540, 420] } });
    await pc(x, { circle: [540, 980, 430] }, C.paper, { seed: 303, amp: 10, dotgrid: { cell: 20, r: 0.09, angle: 12 } });
    await pc(x, { band: [-170, 420, W + 170, 330, 130, 100] }, { color: C.red, speck: 0.3 }, { seed: 304, amp: 11, halftone: { color: '#FBEFE4', cell: 14, angle: 20, r: [0.04, 0.36], grad: [0, 0, W, 0] } });
    await pc(x, { band: [-170, 540, W + 170, 590, 64, 52] }, C.news, { seed: 305, amp: 7, news: { alpha: 0.55, angle: 3 } });
    await pc(x, { band: [-170, 1600, W + 170, 1500, 360, 300] }, { color: C.ink }, { seed: 306, amp: 13, fx: [{ type: 'grunge', seed: 3 }] });
    await pc(x, { band: [-170, 1420, W + 170, 1470, 70, 60] }, C.paper, { seed: 307, amp: 7, news: { alpha: 0.5 } });
    await pc(x, { poly: [[60, 760], [250, 690], [190, 900]] }, C.sun, { seed: 308, amp: 6 });
    await pc(x, { poly: [[1010, 1120], [880, 1210], [1040, 1260]] }, C.paper, { seed: 309, amp: 6 });
  }, { bleed: 200 });
  const HAZ = () => once('haz', () => CL.torn({ poly: [[LENTE.x - 10, LENTE.y - 34], [W + 260, -120], [W + 260, 760], [LENTE.x - 10, LENTE.y + 30]] }, 321, { amp: 10, white: [2, 8] }));
  async function proyectorAt(c, t, x, y, o = {}) {
    const tq = q(t), giro = (tq * 70 + Math.max(0, tq - T_ON) * 320) * (o.giro ?? 1);
    c.save(); c.translate(x, y); if (o.rot) c.rotate(o.rot * DEG); if (o.sx || o.sy) c.scale(o.sx ?? 1, o.sy ?? 1);
    await CL.sprite(c, 'proyector', 0, 0, { h: PROJ.h, ax: 0.5, ay: 1, boil: 0.5, t, shadow: { dx: 14, dy: 22, blur: 22, alpha: 0.5 } });
    for (const [n, rx, ry, d, dir] of REELS) await CL.sprite(c, n, rx, ry, { h: d, rot: giro * dir, shadow: false });
    c.restore();
  }
  async function pageScene(ctx, t) {
    const tq = q(t), z = 1 + 0.03 * tq;
    await zoomAbout(ctx, z, 540, 1000, async () => {
      const L = await pageLayer(); ctx.drawImage(L, -L.bleed, -L.bleed);
      // haz de luz del proyector al encenderse (0.875): papel ámbar translúcido hacia la esquina de arriba
      if (tq >= T_ON) { const T = HAZ(); ctx.save(); ctx.globalAlpha = 0.55; ctx.fillStyle = CL.pat(ctx, CL.paper(C.paper, 5, { brush: 0.8 })); ctx.fill(T); ctx.restore(); }
      const d = CL.drop(tq, 0.25, { h: PROJ.y + 40, tilt: 6, dur: 0.25 });
      if (d.on) await proyectorAt(ctx, t, PROJ.x, PROJ.y + d.dy, { rot: d.rot, sx: d.sx, sy: d.sy });
      if (t >= T_ON && t < T_ON + 2 / 24) await X.star(ctx, LENTE.x, LENTE.y, 160, t, { points: 14, inner: 0.6, color: X.PAL.yellow, seed: 3, pop: 1 });
    });
  }
  async function marcaTag(ctx, t) {
    const tq = q(t); if (tq < 0.5) return;
    const k = Math.max(0, drawingIdx(t, 1.0) - 1); if (k > 2) return;
    await X.tag(ctx, 70 + [0, -130, -420][k], 250 + [0, -12, -30][k], COPY.marca, { t: tq, t0: 0.5, color: 'white', font: 'sans', size: 44, anchor: 'left', rot: -0.035 + 0.05 * k, tape: 'top' });
  }

  /* ======================================================================= 1–2.5 · CINE DE CULTO */
  const ANG = -24, PER = 1000;
  const bandas = () => once('bandas', async () => {
    const c = mkc(2600, 3 * PER), x = c.getContext('2d');
    x.fillStyle = CL.pat(x, CL.paper(C.ink, 9, { speck: 0.4 })); x.fillRect(0, 0, c.width, c.height);
    for (let rep = 0; rep < 3; rep++) {
      const y = rep * PER, B = (y0, w, fill, o) => pc(x, { band: [-120, y + y0, 2720, y + y0 + 18, w, w * 0.92] }, fill, Object.assign({ amp: 9 }, o));
      await B(70, 130, C.news, { seed: 401, news: { alpha: 0.55 } });
      await B(250, 70, { color: C.red, speck: 0.3 }, { seed: 402 });
      await B(400, 170, { color: C.sun, brush: 0.6 }, { seed: 403, halftone: { color: 'rgba(240,122,46,0.8)', cell: 13, angle: 30, r: [0.36, 0.04], grad: [0, y + 330, 0, y + 480] } });
      await B(590, 90, C.paper, { seed: 404, dotgrid: { cell: 18, r: 0.1, angle: 12 } });
      await B(760, 150, C.news, { seed: 405, news: { alpha: 0.5, angle: 2 } });
      await B(905, 46, { color: C.red, speck: 0.3 }, { seed: 406 });
    }
    return c;
  });
  async function cultoScene(ctx, t, o = {}) {
    const tq = q(t), lt = tq - 1.0, z = 1 + 0.03 * clamp(lt / 1.5);
    await zoomAbout(ctx, z, W / 2, H / 2, async () => {
      const Bd = await bandas(), off = (lt * 520) % PER;
      ctx.save(); ctx.translate(W / 2, H / 2); ctx.rotate(ANG * DEG); ctx.drawImage(Bd, -1300, -1.5 * PER - off + PER / 2); ctx.restore();
      // Nosferatu cruza por la diagonal y pasa por el centro justo en 1.75
      const b = CL.bob(t, 3, 4), u = E.inOut3(clamp(lt / 1.5)), a = ANG * DEG, dist = lerp(-1250, 1250, u);
      await CL.piece(ctx, [-250, -320, 500, 640], { img: 'nosferatu' }, { seed: 41, amp: 12, rot: -6, x: W / 2 + Math.cos(a) * dist + b.dx, y: H / 2 + Math.sin(a) * dist + b.dy, shadow: { dx: 22, dy: 30, blur: 22, alpha: 0.5 } });
    });
    await X.speed(ctx, t, { n: 8, angle: Math.PI + ANG * DEG, speed: 3000, alpha: 0.85, seed: 31 });
    // el cartel Lumière entra desde abajo a la derecha (1.833, 1.917) y se estampa en 2.0 abajo, lejos de Nosferatu
    if (tq >= 22 / 12) {
      const i = drawingIdx(t, 22 / 12), s = CL.slap(tq, 2.0, { from: 1.3, rot0: 8 });
      let x = 540, y = 1210, sc = 1, rot = 5;
      if (i === 0) { x = 1250; y = 1700; sc = 1.3; rot = 26; } else if (i === 1) { x = 820; y = 1420; sc = 1.18; rot = 14; }
      else { sc = s.s; rot = 5 + s.rot; y += (tq - 2.0) * 24; }
      await CL.piece(ctx, [-400, -300, 800, 600], { img: 'lumiere' }, { seed: 42, amp: 12, x, y, sc, spin: rot, shadow: { dx: 16, dy: 24, blur: 20, alpha: 0.48 } });
    }
    if (!o.noTag) await worldTag(ctx, t, 13 / 12, COPY.culto, 'yellow', { y: 1500 });
  }

  /* ======================================================================= 2.5–3.5 · LA LUNA (empujón al ojo → iris) */
  // luna.png 791×743; ojo derecho en (525,346), radio ≈ 46
  const MOON = { x: 540, y: 880, h: 880 }, MS = MOON.h / 743;
  const OJO = { x: MOON.x + (525 - 791 / 2) * MS, y: MOON.y + (346 - 743 / 2) * MS, r: 50 * MS };
  const lunaLayer = () => CL.layer('cc_luna', async (x) => {
    await fondoOscuro(x, 501);
    for (let i = 0, r = CL.R(77); i < 26; i++) { const sx = r() * W, sy = r() * 1500, rr = 8 + r() * 16; await pc(x, { star: [sx, sy, rr, rr * 0.42, 5, r() * 60] }, C.paper, { seed: 520 + i, amp: 2, shadow: false }); }
    await pc(x, { circle: [MOON.x, MOON.y, 560] }, { color: C.sun, brush: 0.6 }, { seed: 502, amp: 12, halftone: { color: 'rgba(240,122,46,0.92)', cell: 17, angle: 30, r: [0.4, 0.03], grad: [540, 1440, 540, 320] } });
    await pc(x, { band: [-170, 200, W + 170, 150, 90, 70] }, C.news, { seed: 503, amp: 8, news: { alpha: 0.5, angle: -4 } });
    await pc(x, { band: [-170, 1560, W + 170, 1470, 300, 260] }, { color: C.red, speck: 0.3 }, { seed: 504, amp: 13, fx: [{ type: 'grunge', seed: 3 }] });
    await pc(x, { band: [-170, 1400, W + 170, 1450, 60, 50] }, C.paper, { seed: 505, amp: 7, news: { alpha: 0.5 } });
    await CL.sprite(x, 'kinetoscopio', 150, 1330, { h: 330, rot: -8, shadow: { dx: 8, dy: 12, blur: 14, alpha: 0.4 } });
    await CL.sprite(x, 'claqueta', 905, 1350, { h: 200, rot: 12, shadow: { dx: 8, dy: 12, blur: 14, alpha: 0.4 } });
  }, { bleed: 380 });
  const PUSH = [2.65, 3.46];
  async function lunaScene(ctx, t, o = {}) {
    const tq = q(t), pz = prog(tq, PUSH[0], PUSH[1]), e = pz * pz, hk = prog(tq, 2.5, 3.0), z0 = 1.05 + 0.10 * hk, z = z0 * Math.pow(30, e), m = E.inOut3(clamp(pz * 1.3));
    const sx = lerp(OJO.x, W / 2, m), sy = lerp(OJO.y, H / 2, m), rS = OJO.r * z;
    const covered = rS * 0.95 > Math.hypot(Math.max(sx, W - sx), Math.max(sy, H - sy)) + 40;
    if (!covered) {
      ctx.save(); ctx.translate(sx, sy); ctx.scale(z, z); ctx.translate(-OJO.x, -OJO.y);
      const L = await lunaLayer(); ctx.drawImage(L, -L.bleed, -L.bleed);
      const b = CL.bob(t, 5, 2.5);
      await CL.sprite(ctx, 'luna', MOON.x + b.dx * 0.5, MOON.y + b.dy * 0.5, { h: MOON.h, boil: 0.6, t, shadow: { dx: 16, dy: 24, blur: 22, alpha: 0.5 } });
      ctx.restore();
    }
    if (tq >= 2.75) {
      const ki = prog(tq, 2.9, 3.4), pop = lerp(0.55, 1, clamp(drawingIdx(t, 2.75) / 2));
      await X.iris(ctx, sx, sy, rS * pop, ki, t, { n: 6, spin: 1.2, drawCenter: ki > 0.12 ? async (c, cx, cy, rr, tt) => {
        const kb = await kalBuf(tt), s = rr / (Math.hypot(W, H) / 2); c.drawImage(kb, cx - (KS / 2) * s, cy - (KS / 2) * s, KS * s, KS * s);
      } : null });
    }
    if (!o.noTag && tq >= 2.5 && tq < 3.4) await worldTag(ctx, t, 31 / 12, COPY.maestras, 'yellow', { y: 1500 });
  }

  /* ======================================================================= 3.5–4.5 · CALEIDOSCOPIO */
  const KSS = 2.0;   // escala de la fuente: en vertical la mitad derecha mide 540 px y el disco ≈ 1100 px de radio
  const KSRC = () => once('ksrc', async () => {
    const c = mkc(W, H), x = c.getContext('2d');
    x.fillStyle = CL.pat(x, CL.paper(C.ink, 9, { speck: 0.4 })); x.fillRect(0, 0, W, H);
    const V = (x0, w0, w1, dx = 0) => ({ band: [x0, -40, x0 + dx, H + 40, w0, w1 ?? w0], tips: false });
    const BANDS = [['news', 575, 60], ['amb', 632, 34], ['papel', 676, 40], ['tinta', 715, 30], ['amb', 752, 44], ['news', 806, 58], ['roj', 860, 30], ['papel', 900, 46], ['amb', 952, 40], ['news', 1010, 70]];
    let i = 0;
    for (const [k, cx, w] of BANDS) {
      const sh = { dx: 6, dy: 0, blur: 10, alpha: 0.35 }, seed = 960 + i++, dx = ((seed * 37) % 15) - 7, s = V(cx - dx / 2, w, w * 0.94, dx), oo = { seed, amp: 5, shadow: sh, cache: false };
      if (k === 'news') await CL.piece(x, s, C.news, Object.assign(oo, { news: { alpha: 0.5, angle: 90 } }));
      else if (k === 'papel') await CL.piece(x, s, C.paper, Object.assign(oo, { dotgrid: { cell: 12, r: 0.12, angle: 12 } }));
      else if (k === 'tinta') await CL.piece(x, s, { color: C.ink }, oo);
      else if (k === 'roj') await CL.piece(x, s, { color: C.red, speck: 0.3 }, oo);
      else await CL.piece(x, s, { color: C.sun, brush: 0.6 }, Object.assign(oo, { halftone: { color: 'rgba(240,122,46,0.8)', cell: 9, angle: 30, r: [0.36, 0.04], grad: [cx - w / 2, 0, cx + w / 2, 0] } }));
    }
    return c;
  });
  const FLYERS = [{ name: 'claqueta', t0: 3.705, dur: 0.55, angle: -1.2, spin: 0.5, scale: 0.8 }, { name: 'kinetoscopio', t0: 3.805, dur: 0.55, angle: 2.0, spin: -0.8, scale: 0.8 },
    { name: 'luna', t0: 3.905, dur: 0.55, angle: 1.1, spin: 0.7, scale: 0.75 }];
  const HOLE = [[52 / 12, 0.34], [53 / 12, 0.85]];
  const holeAt = (t) => { let h = 0; for (const [t0, v] of HOLE) if (t >= t0 - 1e-6) h = v; return h; };
  const kOpts = (t) => ({ segments: 8, rot: 0, twist: 0, zoom: 2.6, ratio: 0.5, levels: 7, srcScale: KSS, rims: ['red', 'yellow', 'dots', 'red', 'yellow', 'dots'], flyers: FLYERS, hole: holeAt(t), drawNext: (c, tt) => cicloScene(c, tt), holeColor: '#F3A51C' });
  const KST = [['bobina_der', 10, 300, 0, 120, 0], ['claqueta', 11, 230, Math.PI / 8, 90, 90]];
  async function kalStickers(ctx, tq) {
    const c = tq * 2.6;
    for (const [n, m, d, a0, h, rot] of KST) {
      const k = KSS * Math.pow(0.5, m - c), R = d * k; if (R < 12 || (d - h) * k > 1160) continue;
      for (let i = 0; i < 8; i++) {
        ctx.save(); ctx.translate(W / 2, H / 2); ctx.rotate(i * Math.PI / 4 + a0); if (i % 2) ctx.scale(1, -1);
        await CL.sprite(ctx, n, R, 0, { h: h * k, rot: rot + tq * 40, shadow: { dx: 5 * k, dy: 8 * k, blur: 9 * k, alpha: 0.4 } }); ctx.restore();
      }
    }
  }
  const kalDraw = async (ctx, t) => {
    const tq = q(t), src = await KSRC(), o = kOpts(tq);
    await X.kaleido(ctx, tq, async (c) => c.drawImage(src, 0, 0), Object.assign({}, o, { hole: 0, flyers: [] }));
    await kalStickers(ctx, tq);
    if (o.hole > 0 || FLYERS.some((f) => tq > f.t0 && tq < f.t0 + f.dur)) await X.kaleido(ctx, tq, async () => {}, Object.assign({}, o, { levels: -1 }));
  };
  const KS = Math.ceil(Math.hypot(W, H)) + 8;
  async function kalBuf(t) { const cv = buf('kal', KS, KS), x = cv.getContext('2d'); x.translate((KS - W) / 2, (KS - H) / 2); await kalDraw(x, t); return cv; }

  /* ======================================================================= 4.5–5.5 · CICLO ACTUAL */
  const CLAQ = { x: 540, y: 1585, h: 390 };
  const cicloLayer = () => CL.layer('cc_ciclo', async (x) => {
    await pc(x, [-200, -200, W + 400, H + 400], C.news, { seed: 601, amp: 0, shadow: false, news: { alpha: 0.35 } });
    await pc(x, [60, 470, 960, 760], { color: C.ink, speck: 0.3 }, { seed: 602, rot: -2, amp: 14 });
    await pc(x, { band: [-170, 420, W + 170, 380, 70, 56] }, { color: C.sun, brush: 0.6 }, { seed: 603, amp: 8 });
    await pc(x, { band: [-170, 1330, W + 170, 1290, 120, 100] }, { color: C.red, speck: 0.3 }, { seed: 604, amp: 10, halftone: { color: '#FBEFE4', cell: 14, angle: 20, r: [0.04, 0.36], grad: [0, 0, W, 0] } });
    await pc(x, { circle: [930, 300, 120] }, C.paper, { seed: 605, amp: 8, dotgrid: { cell: 16, r: 0.12 } });
  }, { bleed: 200 });
  async function cicloScene(ctx, t) {
    const tq = q(t), pz = E.inOut3(prog(tq, 4.5, 5.5));
    await zoomAbout(ctx, 1 + 0.12 * pz, 540, 860, async () => {
      const L = await cicloLayer(); ctx.drawImage(L, -L.bleed, -L.bleed);
      if (tq >= 4.55) await X.tag(ctx, 130, 560, COPY.cicloTag, { t: tq, t0: 4.55, color: 'yellow', font: 'sans', size: 38, anchor: 'left', rot: -0.03, tape: 'left' });
      if (tq >= 4.6) await X.ransom(ctx, COPY.ciclo1, 520, 790, tq, 4.6, { size: 150, seed: 11, step: 0.1 });
      if (tq >= 5.0) await X.ransom(ctx, COPY.ciclo2, 520, 1010, tq, 5.0, { size: 160, seed: 12, step: 0.0833 });
      if (tq >= 5.25) await X.tag(ctx, 770, 1125, COPY.enCurso, { t: tq, t0: 5.25, color: 'white', font: 'mono', size: 30, rot: 0.03, tape: false });
      const d = CL.drop(tq, 4.25, { h: 1600, tilt: 5, dur: 0.25 });
      if (d.on) { ctx.save(); ctx.translate(CLAQ.x, CLAQ.y + d.dy); ctx.rotate((-4 + d.rot) * DEG); ctx.scale(d.sx, d.sy);
        await CL.sprite(ctx, 'claqueta', 0, 0, { h: CLAQ.h, ax: 0.5, ay: 1, shadow: { dx: 12, dy: 20, blur: 20, alpha: 0.45 } }); ctx.restore(); }
    });
  }

  /* ======================================================================= 5.5–7.5 · cohete de tiras → CINECLUB / FOREVER */
  const TITLE_Y = 640;
  const cicloOff = (t) => H * 1.18 * Math.pow(prog(q(t), 5.5, 71 / 12), 1.6);
  const rayosLayer = () => CL.layer('cc_rayos', async (x) => {
    await fondoOscuro(x, 701);
    const r = CL.R(702);
    for (let i = 0; i < 9; i++) {   // haces de luz de proyector, desde abajo hacia arriba
      const a = lerp(-62, 62, i / 8) * DEG + (r() - 0.5) * 0.06, len = 2400;
      await pc(x, { band: [540, H + 120, 540 + Math.sin(a) * len, H + 120 - Math.cos(a) * len, 26, 210] }, i % 3 === 1 ? { color: C.sun, brush: 0.7 } : C.paper, { seed: 710 + i, amp: 8, shadow: { dx: 0, dy: 8, blur: 16, alpha: 0.35 } });
    }
    await pc(x, { circle: [540, H + 60, 260] }, { color: C.sun, brush: 0.6 }, { seed: 720, amp: 12, halftone: { color: 'rgba(240,122,46,0.9)', cell: 15, angle: 30, r: [0.4, 0.04], grad: [540, H - 200, 540, H + 300] } });
  }, { bleed: 200 });
  async function rider(c, x, y, tt) {
    const qq = q(tt), lk = prog(qq, 68 / 12, 71 / 12); if (lk >= 1) return;
    const s = lerp(1, 0.6, lk);
    c.save(); c.translate(x, y - 700 * Math.pow(lk, 1.5)); c.scale(s, s); await CL.sprite(c, 'bobina_der', 0, 0, { h: 230, rot: qq * 300, shadow: { dx: 8, dy: 14, blur: 12, alpha: 0.45 } }); c.restore();
  }
  async function titleBg(ctx, t) {
    const tq = q(t), z = 1 + 0.03 * prog(tq, 6.0, 10.0);
    await zoomAbout(ctx, z, 540, 900, async () => { const L = await rayosLayer(); ctx.drawImage(L, -L.bleed, -L.bleed); });
    if (tq < 71 / 12) { const B = padBuf('cicloS'); await cicloScene(B.getContext('2d'), t); drawSheet(ctx, B, 0, cicloOff(t), [1, 0, 0, 0], 17, [0, -18]); }
    const rby = Math.min(CLAQ.y - CLAQ.h + cicloOff(t), H + 70), rhy = lerp(rby, H * 0.30, E.out3(clamp((q(t) - 5.5) / 0.42)));
    await X.rocket(ctx, t, 5.5, { vx: W / 2, vy: H * 0.30, by: rby, bx: CLAQ.x, dur: 0.42, n: 64, width: clamp((rby - rhy) * 1.6, 260, 760), narrow: 0.66, seed: 7, drawRider: rider });
    await X.burst(ctx, t, 6.0, { cx: W / 2, cy: TITLE_Y, n: 26, seed: 9 });
  }
  const TFR = [0, 0.256, 0.471, 0.62, 0.752, 0.835, 0.917, 0.95, 0.983, 1];
  async function titleScene(ctx, t) {
    await titleBg(ctx, t);
    const tq = q(t); if (tq < 6.0) return;
    const i = drawingIdx(t, 6.0), f = i < TFR.length ? TFR[i] : 1, dy0 = H * 0.06 - (TITLE_Y + TTL.off);
    await X.title(ctx, COPY.title, W / 2, TITLE_Y + dy0 * (1 - f), tq, 6.0, { size: TTL.size, font: COPY.titleFont, drop: false, zoom: 0.03 });
    if (tq >= 6.5) await X.tag(ctx, W / 2, 1060, COPY.ciudad, { t: tq, t0: 6.5, color: 'white', font: 'sans', size: 38, rot: -0.02, tape: 'top' });
  }

  /* ======================================================================= 7.5–10 · rasgado → franja con el logo → parpadeo → ÚNETE */
  function vnoise(seed) { const r = ENG.rng(seed * 7 + 3), N = 1024, v = new Float32Array(N); for (let i = 0; i < N; i++) v[i] = r() * 2 - 1; return (x) => { x = ((x % N) + N) % N; const i = Math.floor(x), f = x - i, s = f * f * (3 - 2 * f); return v[i] + (v[(i + 1) % N] - v[i]) * s; }; }
  function fbm(seed) { const a = vnoise(seed), b = vnoise(seed + 17), c = vnoise(seed + 29); return (x) => a(x) * 0.58 + b(x * 2.17 + 5.3) * 0.29 + c(x * 4.73 + 1.1) * 0.13; }
  const TEARDONE = (() => {
    const { y0, y1, seed } = TEAR, st = 6, n = Math.ceil((W + 80) / st) + 1, nA = fbm(seed), nB = fbm(seed + 9), nC = vnoise(seed + 3), nD = vnoise(seed + 5), r = ENG.rng(seed), xs = [], top = [], bot = [], wt = [], wb = [];
    for (let i = 0; i < n; i++) { const x = -40 + i * st; xs.push(x); top.push(y0 + nA(x / 60) * 13 + (r() - 0.5) * 3); bot.push(y1 + nB(x / 60) * 13 + (r() - 0.5) * 3); wt.push(3 + 12 * Math.pow(clamp(0.5 + 0.8 * nC(x / 70)), 1.5) + r() * 1.5); wb.push(2 + 10 * Math.pow(clamp(0.5 + 0.8 * nD(x / 70)), 1.5) + r() * 1.5); }
    const R = new Path2D(), Ts = new Path2D(), tp = new Path2D(), bp = new Path2D(), m = n - 1;
    R.moveTo(xs[0], top[0]); for (let i = 1; i <= m; i++) R.lineTo(xs[i], top[i]); for (let i = m; i >= 0; i--) R.lineTo(xs[i], bot[i]); R.closePath();
    Ts.moveTo(xs[0], top[0] - 200); for (let i = 0; i <= m; i++) Ts.lineTo(xs[i], top[i]); Ts.lineTo(xs[m], top[m] - 200); Ts.closePath();
    for (let i = 0; i <= m; i++) i ? tp.lineTo(xs[i], top[i] - wt[i]) : tp.moveTo(xs[i], top[i] - wt[i]); for (let i = m; i >= 0; i--) tp.lineTo(xs[i], top[i]); tp.closePath();
    for (let i = 0; i <= m; i++) i ? bp.lineTo(xs[i], bot[i]) : bp.moveTo(xs[i], bot[i]); for (let i = m; i >= 0; i--) bp.lineTo(xs[i], bot[i] + wb[i]); bp.closePath();
    return { R, Ts, tp, bp };
  })();
  function tearDone(ctx, A, B) {
    const T = TEARDONE; ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.clip(T.R); ctx.drawImage(B, 0, 0); ctx.shadowColor = 'rgba(0,0,0,0.42)'; ctx.shadowBlur = 16; ctx.shadowOffsetY = 7; ctx.fillStyle = '#000'; ctx.fill(T.Ts); ctx.restore();
    ctx.save(); ctx.fillStyle = U.pat(ctx, X.PAL.paper); ctx.fill(T.tp); ctx.fill(T.bp); ctx.strokeStyle = 'rgba(80,60,40,0.18)'; ctx.lineWidth = 1; ctx.stroke(T.tp); ctx.stroke(T.bp); ctx.restore();
  }
  // la franja: papel crema con el logo real; los looks del parpadeo cambian el papel y el color del logo
  async function franja(c, t, look) {
    const tq = q(t);
    if (!look) { c.fillStyle = paperPat(c); c.fillRect(0, 0, W, H); }
    else if (look === 'ambar') { c.fillStyle = CL.pat(c, CL.paper(C.sun, 4, { brush: 0.6 })); c.fillRect(0, 0, W, H); }
    else if (look === 'periodico') { c.fillStyle = CL.pat(c, CL.paper(C.news, 6)); c.fillRect(0, 0, W, H); CL.newsprint(c, [0, TEAR.y0 - 20, W, TEAR.y1 - TEAR.y0 + 40], { alpha: 0.45 }); }
    else { c.fillStyle = CL.pat(c, CL.paper(C.ink, 9, { speck: 0.4 })); c.fillRect(0, 0, W, H); if (look === 'puntos') CL.halftone(c, [0, TEAR.y0 - 20, W, TEAR.y1 - TEAR.y0 + 40], 'rgba(255,194,26,0.85)', { cell: 16, angle: 30, r: [0.05, 0.4], grad: [0, TEAR.y1, 0, TEAR.y0] }); }
    const oscuro = look === 'puntos' || look === 'tinta';
    await CL.sprite(c, oscuro ? 'logo_blanco' : 'logo', LOGO.x, LOGO.y, { h: LOGO.h, boil: !look ? 0.5 : 0, t: tq, shadow: false });
  }
  const flashAt = (t) => { const i = Math.floor((t - 8.0) * 24 + 1e-6); return i >= 0 && i < FLICK_FR.length ? FLICK[FLICK_FR[i]] : null; };
  const T_CTA = 8.5;
  async function endScene(ctx, t) {
    const tq = q(t), st = flashAt(t), z = 1 + 0.025 * Math.max(0, tq - 95 / 12);
    await zoomAbout(ctx, z, W / 2, 900, async () => {
      const BG = buf('tbg'); await titleBg(BG.getContext('2d'), t);
      const under = async (c) => { c.drawImage(BG, 0, 0); await franja(c, t, null); };
      if (tq < 7.9) await X.tear(ctx, prog(tq, 89 / 12, 7.92), async (c) => titleScene(c, t), under, TEAR);
      else {
        const Bc = buf('tunder'); await under(Bc.getContext('2d')); tearDone(ctx, BG, Bc);
        if (st) { const F = buf('flash'); await franja(F.getContext('2d'), t, st); ctx.save(); ctx.clip(TEARDONE.R); ctx.drawImage(F, 0, 0); ctx.restore(); }   // solo dentro de la franja
      }
      if (tq >= T_CTA) await X.confetti(ctx, t, T_CTA, { x: W / 2, y: TEAR.y0, n: 22, speed: 1200, spread: Math.PI * 1.1, gravity: 1300, dur: 0.95, seed: 28, colors: [C.paper, C.paper, C.sun, C.ink] });
      if (tq >= T_CTA) await X.tag(ctx, W / 2, 380, COPY.unete, { t: tq, t0: T_CTA, color: 'yellow', font: 'sans', size: 56, rot: -0.025, tape: 'top' });
      if (tq >= 8.75) await X.tag(ctx, W / 2, 1330, COPY.url, { t: tq, t0: 8.75, color: 'ink', font: 'mono', size: 40, rot: 0.015, tape: false });
      if (tq >= 9.0) await X.tag(ctx, W / 2, 1440, COPY.ciudad, { t: tq, t0: 9.0, color: 'white', font: 'sans', size: 34, rot: -0.02, tape: 'left' });
    });
  }

  /* ======================================================================= línea de tiempo */
  const cuts = [];
  const Cut = (t0, t1, draw) => cuts.push({ t0, t1, draw: async (ctx, t, k, lt) => {
    await warm();
    const z = K.punch(q(t)); ctx.fillStyle = '#FBF8F1'; ctx.fillRect(0, 0, W, H);
    await zoomAbout(ctx, z, W / 2, H / 2, () => draw(ctx, t, k, lt));
  } });
  Cut(0.0, 1.0, async (ctx, t) => { await pageScene(ctx, t); await marcaTag(ctx, t); });
  Cut(1.0, 2.5, async (ctx, t) => {
    await cultoScene(ctx, t);
    const i = drawingIdx(t, 1.0);
    if (i < 3) { const A = padBuf('ripA'); await pageScene(A.getContext('2d'), t); ripDraw(ctx, [0.05, 0.36, 0.8][i], A); await X.confetti(ctx, t, 1.0, { x: W / 2, y: H / 2, n: 30, speed: 1500, spread: Math.PI * 2, gravity: 900, dur: 0.6, seed: 20, colors: [C.paper, C.paper, C.red, C.sun] }); }
    await marcaTag(ctx, t);
  });
  Cut(2.5, 3.5, (ctx, t) => wipe(ctx, t, 2.5, (c) => cultoScene(c, t), (c) => lunaScene(c, t), { from: [1, 0], edges: [0, 0, 0, 1], seed: 4, push: 0.22, roll: -10, rollB: 6, speed: { n: 10, angle: Math.PI, speed: 3600, alpha: 0.9, seed: 41 } }));
  Cut(3.5, 4.5, (ctx, t) => kalDraw(ctx, t));
  Cut(4.5, 5.5, (ctx, t) => cicloScene(ctx, t));
  Cut(5.5, 6.0, (ctx, t) => titleBg(ctx, t));
  Cut(6.0, 7.5, (ctx, t) => titleScene(ctx, t));
  Cut(7.5, 10.0, (ctx, t) => endScene(ctx, t));

  window.SCENES = {
    duration: 10.0,
    cuts,
    overlay: async (ctx, t) => { CL.printGrain(ctx, t, 0.06); },
  };
  window.COPY = COPY;
})();
