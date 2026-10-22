import { useCurrentFrame, useVideoConfig } from "remotion";
import { FRASES, golpe, resorte, SPS, type Frase } from "./ritmo";

// Globo de texto con palabras que brincan, objetos que entran volando y apertura del pico
// sincronizada con las sílabas del balbuceo (mismo cálculo que sonido.py).

const TINTA = "#141414";
const RESALTE = "#FF2F8E";
const AMARILLO = "#FFC83A";
const NEON = "#C8FF2E";

export const fraseEn = (t: number) => FRASES.find((f) => t >= f.inicio && t < f.fin);

export const aperturaPico = (t: number): number => {
  const f = fraseEn(t);
  if (!f) return 0;
  const s = (t - f.inicio) * SPS;
  if (s >= f.habla * SPS) return 0;
  return Math.sin(Math.PI * (s % 1));
};

// Salida rápida al terminar la frase (1 → 0 en 4 cuadros).
const salida = (f: Frase, frame: number, fps: number) => Math.min(1, Math.max(0, (f.fin * fps - frame) / 4));

type Palabra = { texto: string; resaltada: boolean; desde: number };

// Separa el texto en renglones y palabras; cada palabra sabe en qué segundo aparece
// (según cuántas letras van dichas) y si va resaltada (*entre asteriscos*).
const palabras = (f: Frase): Palabra[][] => {
  const total = f.texto.replace(/[\n*\s]/g, "").length;
  let letras = 0;
  let resaltado = false;
  return f.texto.split("\n").map((linea) =>
    linea.split(" ").map((w) => {
      let resto = w;
      if (resto.startsWith("*")) {
        resaltado = true;
        resto = resto.slice(1);
      }
      const cierra = resto.includes("*");
      const palabra = { texto: resto.replace(/\*/g, ""), resaltada: resaltado, desde: f.inicio + (letras / total) * f.habla };
      if (cierra) resaltado = false;
      letras += palabra.texto.length;
      return palabra;
    }),
  );
};

export const Globo = ({ fontFamily }: { fontFamily: string }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const f = fraseEn(t);
  if (!f) return null;

  const entra = resorte(frame, fps, f.inicio, { damping: 9, stiffness: 190 });
  // Al entrar se estira de lado y se encoge de alto (aplastar y estirar); late con la música.
  const late = 1 + 0.015 * golpe(t, 8);
  const forma = Math.sin(Math.min(1, entra) * Math.PI);
  const ex = entra * salida(f, frame, fps) * late * (1 + 0.08 * forma);
  const ey = entra * salida(f, frame, fps) * late * (1 - 0.06 * forma);

  const renglones = palabras(f);
  const alto = 90 + renglones.length * 78;
  const arriba = 200;
  const abajo = arriba + alto;
  const caja = `M 90 ${arriba + 30} Q 80 ${arriba} 130 ${arriba - 4} L 950 ${arriba + 6} Q 1000 ${arriba + 10} 994 ${arriba + 50} ` +
    `L 990 ${abajo - 40} Q 990 ${abajo} 940 ${abajo} L 770 ${abajo} L 790 ${abajo + 140} L 690 ${abajo} ` +
    `L 140 ${abajo + 8} Q 86 ${abajo + 8} 86 ${abajo - 34} Z`;

  return (
    <g transform={`translate(790 ${abajo + 140}) scale(${ex} ${ey}) translate(-790 ${-(abajo + 140)})`}>
      <g filter="url(#linea)" strokeLinejoin="round">
        <path d={caja} fill={TINTA} stroke={TINTA} strokeWidth={30} />
        <path d={caja} fill="white" />
      </g>
      {/* Texto en HTML para que cada palabra brinque sola sin tener que medirla */}
      <foreignObject x={90} y={arriba + 40} width={900} height={alto - 40}>
        <div style={{ fontFamily, fontSize: 64, lineHeight: "78px", textAlign: "center", color: TINTA, filter: "url(#letra)" }}>
          {renglones.map((ws, i) => (
            <div key={i} style={{ whiteSpace: "nowrap" }}>
              {ws.map((w, j) => {
                const s = resorte(frame, fps, w.desde, { damping: 14, stiffness: 240 });
                const vibra = w.resaltada && s > 0.9 ? 3 * Math.sin(t * 22 + j) : 0;
                return (
                  <span
                    key={j}
                    style={{
                      display: "inline-block",
                      margin: "0 12px",
                      color: w.resaltada ? RESALTE : TINTA,
                      opacity: s > 0.01 ? 1 : 0,
                      scale: `${s * (w.resaltada ? 1.06 : 1)}`,
                      rotate: `${(1 - s) * -25 + vibra}deg`,
                      translate: `0px ${(1 - s) * 40}px`,
                    }}
                  >
                    {w.texto}
                  </span>
                );
              })}
            </div>
          ))}
        </div>
      </foreignObject>
    </g>
  );
};

const Jeringa = () => (
  <g stroke={TINTA} strokeWidth={10} strokeLinejoin="round" strokeLinecap="round">
    <line x1={-200} y1={0} x2={-120} y2={0} strokeWidth={26} />
    <line x1={-200} y1={0} x2={-120} y2={0} stroke="#E8E8E8" strokeWidth={12} />
    <rect x={-222} y={-42} width={26} height={84} rx={8} fill="#E8E8E8" />
    <rect x={-120} y={-40} width={22} height={80} rx={6} fill="#E8E8E8" />
    <rect x={-100} y={-34} width={210} height={68} rx={14} fill="white" />
    <rect x={-40} y={-26} width={142} height={52} rx={8} fill={NEON} strokeWidth={0} />
    {[-10, 30, 70].map((x) => (
      <line key={x} x1={x} y1={-34} x2={x} y2={-12} strokeWidth={6} />
    ))}
    <rect x={-100} y={-34} width={210} height={68} rx={14} fill="none" />
    <path d="M 110 -14 L 136 -10 L 136 10 L 110 14 Z" fill="#E8E8E8" />
    <line x1={136} y1={0} x2={240} y2={0} strokeWidth={6} />
    <circle cx={258} cy={8} r={9} fill={NEON} strokeWidth={5} />
  </g>
);

const Diez = ({ fontFamily }: { fontFamily: string }) => (
  <g>
    <path
      d={Array.from({ length: 24 }, (_, i) => {
        const a = (i / 24) * Math.PI * 2;
        const r = i % 2 === 0 ? 170 : 128;
        return `${i === 0 ? "M" : "L"} ${Math.cos(a) * r} ${Math.sin(a) * r}`;
      }).join(" ") + " Z"}
      fill={AMARILLO}
      stroke={TINTA}
      strokeWidth={12}
      strokeLinejoin="round"
    />
    <text y={22} textAnchor="middle" style={{ fontFamily }} fontSize={86} fill={RESALTE} stroke={TINTA} strokeWidth={12} paintOrder="stroke">
      10/10
    </text>
  </g>
);

// Dónde termina cada objeto (en pantalla) y su giro de reposo.
const DESTINO: Record<string, { x: number; y: number; giro: number }> = {
  jeringa: { x: 860, y: 1170, giro: -35 },
  diez: { x: 860, y: 1400, giro: 0 },
};

export const Objeto = ({ fontFamily }: { fontFamily: string }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = fraseEn(frame / fps);
  if (!f?.objeto) return null;
  const d = DESTINO[f.objeto];
  const esJeringa = f.objeto === "jeringa";

  // Entra volando en arco desde abajo a la derecha, girando; deja estela mientras va rápido.
  const pos = (fr: number) => {
    const s = resorte(fr, fps, f.inicio + 0.2, { damping: 12, stiffness: 120 });
    const t = fr / fps;
    return {
      x: 1250 + (d.x - 1250) * s,
      y: 1800 + (d.y - 1800) * s - 380 * Math.sin(Math.PI * Math.min(1, Math.max(0, s))) + 14 * Math.sin(t * 3),
      giro: d.giro - 540 * (1 - s) + (esJeringa ? 6 * Math.sin(t * 2.5) : 8 * Math.sin(t * 4)),
      s,
    };
  };
  const dibujo = esJeringa ? <Jeringa /> : <Diez fontFamily={fontFamily} />;
  const sale = salida(f, frame, fps);
  const capa = (fr: number, opacidad: number) => {
    const p = pos(fr);
    return (
      <g key={fr} opacity={opacidad} transform={`translate(${p.x} ${p.y}) rotate(${p.giro}) scale(${0.85 * sale})`}>
        {dibujo}
      </g>
    );
  };
  const rapido = Math.abs(pos(frame).s - pos(frame - 1).s) > 0.03;
  return (
    <g filter="url(#linea)">
      {rapido ? [capa(frame - 2, 0.18), capa(frame - 1, 0.35)] : null}
      {capa(frame, 1)}
    </g>
  );
};
