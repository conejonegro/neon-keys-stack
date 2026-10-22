// Graba una escena 3D cuadro por cuadro con Chrome invisible y arma el .mp4 con ffmpeg.
// Uso: node grabar.js escenas/prueba.html out/pruebas/prueba-3d.mp4 [--segundos N] [--preview T]
//        [--datos out/.tmp/X.json --audio out/.tmp/X.wav]   (los genera preparar.py)
// El video se escribe en out/.tmp/ y se mueve a su destino (out/videos/ u out/pruebas/) solo al terminar.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(AQUI, '..');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const FFMPEG = path.join(process.env.HOME, '.local/bin/ffmpeg');
const W = 1080, H = 1920, FPS = 30;

const args = process.argv.slice(2);
const opcion = (nombre, porDefecto) => {
  const i = args.indexOf(nombre);
  return i >= 0 ? args[i + 1] : porDefecto;
};
const [escenaRel, salidaRel] = args;
if (!escenaRel || !salidaRel) {
  console.error('Uso: node grabar.js escenas/ESCENA.html out/videos/VIDEO.mp4 [--segundos N] [--preview T] [--datos J --audio W]');
  process.exit(1);
}
const preview = opcion('--preview', null);
const datosRuta = opcion('--datos', null);
const audioRuta = opcion('--audio', null);
const datos = datosRuta ? JSON.parse(fs.readFileSync(path.resolve(RAIZ, datosRuta), 'utf8')) : null;
const segundos = parseFloat(opcion('--segundos', datos ? String(datos.total) : '3'));

// Servidor local mínimo: los módulos de JavaScript no cargan desde file://
const TIPOS = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const servidor = http.createServer((req, res) => {
  const archivo = path.join(AQUI, decodeURIComponent(req.url.split('?')[0]));
  if (!archivo.startsWith(AQUI) || !fs.existsSync(archivo)) {
    res.writeHead(404).end();
    return;
  }
  res.writeHead(200, { 'Content-Type': TIPOS[path.extname(archivo)] || 'application/octet-stream' });
  fs.createReadStream(archivo).pipe(res);
});
await new Promise(r => servidor.listen(0, '127.0.0.1', r));
const url = `http://127.0.0.1:${servidor.address().port}/${escenaRel}`;

const navegador = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ['--use-angle=gl', '--ignore-gpu-blocklist'],
});
const pagina = await navegador.newPage();
pagina.on('pageerror', e => console.error('Error en la escena:', e.message));
await pagina.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
await pagina.goto(url);
await pagina.waitForFunction('window.listo === true', { timeout: 30000 });
await pagina.evaluate((d) => window.cargar(d), datos);

const cuadroPNG = async (t) => {
  const datos = await pagina.evaluate((t) => {
    window.dibujar(t);
    return document.querySelector('canvas').toDataURL('image/png').split(',')[1];
  }, t);
  return Buffer.from(datos, 'base64');
};

const salida = path.resolve(RAIZ, salidaRel);
const tmp = path.join(RAIZ, 'out/.tmp');
fs.mkdirSync(tmp, { recursive: true });

try {
  if (preview !== null) {
    const png = salida.replace(/\.mp4$/, '') + `-t${preview}.png`;
    fs.writeFileSync(png, await cuadroPNG(parseFloat(preview)));
    console.log(`Vista previa: ${png}`);
  } else {
    const carpeta = path.join(tmp, path.basename(salida, '.mp4'));
    fs.rmSync(carpeta, { recursive: true, force: true });
    fs.mkdirSync(carpeta);
    const total = Math.round(segundos * FPS);
    const inicio = Date.now();
    for (let i = 0; i < total; i++) {
      fs.writeFileSync(path.join(carpeta, `${String(i).padStart(5, '0')}.png`), await cuadroPNG(i / FPS));
      if (i % 30 === 0) console.log(`Cuadro ${i}/${total}`);
    }
    const porCuadro = (Date.now() - inicio) / total / 1000;
    console.log(`Cuadros listos: ${porCuadro.toFixed(2)} s por cuadro`);

    const mp4Tmp = path.join(tmp, path.basename(salida));
    const entradaAudio = audioRuta ? ['-i', path.resolve(RAIZ, audioRuta)] : [];
    const salidaAudio = audioRuta ? ['-map', '0:v', '-map', '1:a', '-shortest', '-c:a', 'aac', '-b:a', '192k'] : [];
    execFileSync(FFMPEG, ['-y', '-v', 'error', '-framerate', String(FPS), '-i', path.join(carpeta, '%05d.png'),
      ...entradaAudio, ...salidaAudio,
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', mp4Tmp]);
    fs.mkdirSync(path.dirname(salida), { recursive: true });
    fs.renameSync(mp4Tmp, salida);
    fs.rmSync(carpeta, { recursive: true, force: true });
    console.log(`Video: ${salida}`);
  }
} finally {
  await navegador.close();
  servidor.close();
}
