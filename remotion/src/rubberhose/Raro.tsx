import { useCurrentFrame, useVideoConfig } from "remotion";
import { curva, type Punto } from "./geometria";
import { fasePulso, PULSO } from "./ritmo";

// Personaje raro estilo "rubber hose": cabeza grumosa con pico enorme, ojos disparejos,
// antenas, brazos y piernas de fideo, guantes blancos y tenis rosas.
// Igual que en los cartoons viejos: primero se dibuja todo el contorno negro y encima el color,
// así cabeza, cuello, cuerpo y extremidades se funden en una sola silueta.

export const TINTA = "#141414";
const PIEL = "#5B6CFF";
const PIEL_OSCURA = "#3B47D1";
const PICO = "#FF8C1A";
const PICO_OSCURO = "#D9620A";
const TENIS = "#FF4FA3";
const BOLITA = "#FFC83A";
const BABA = "#C6F7FF";
const CACHETE = "#FF9DB5";

const C = 16; // grosor del contorno

const CABEZA =
  "M 400 760 C 388 652 468 588 540 600 C 612 586 676 642 662 722 " +
  "C 692 792 650 884 560 892 C 468 906 404 852 400 760 Z";

const CUERPO =
  "M 440 930 C 378 962 358 1082 380 1162 C 402 1242 482 1262 542 1256 " +
  "C 622 1250 672 1200 666 1110 C 660 1010 622 940 562 926 C 520 916 470 916 440 930 Z";

const PICO_ARRIBA = "M 628 690 C 760 668 884 742 934 856 C 842 818 742 800 640 802 Z";
const PICO_ABAJO = "M 640 802 C 732 806 822 832 884 878 C 792 896 702 874 646 846 Z";

type Fideo = { pts: Punto[]; grosor: number; color: string };

const ondear = (pts: Punto[], t: number, amp: number, fase: number): Punto[] =>
  pts.map(([x, y], j) => {
    if (j === 0) return [x, y];
    const k = j / (pts.length - 1);
    const a = t * Math.PI * 2 + fase + j * 0.6;
    return [x + amp * k * Math.sin(a), y + amp * 0.7 * k * Math.cos(a)];
  });

const Guante = ({ x, y, giro }: { x: number; y: number; giro: number }) => (
  <g transform={`rotate(${giro} ${x} ${y})`} stroke={TINTA} strokeWidth={11} strokeLinecap="round" strokeLinejoin="round">
    <path d={`M ${x - 46} ${y + 30} Q ${x - 60} ${y - 40} ${x} ${y - 52} Q ${x + 62} ${y - 50} ${x + 52} ${y + 18} Q ${x + 40} ${y + 56} ${x - 46} ${y + 30} Z`} fill="white" />
    <path d={`M ${x - 18} ${y - 48} Q ${x - 22} ${y - 18} ${x - 10} ${y - 4}`} fill="none" />
    <path d={`M ${x + 14} ${y - 50} Q ${x + 12} ${y - 22} ${x + 22} ${y - 6}`} fill="none" />
    <path d={`M ${x - 42} ${y + 4} Q ${x - 10} ${y + 2} ${x + 4} ${y + 24}`} fill="none" />
  </g>
);

const Tenis = ({ x, y, giro }: { x: number; y: number; giro: number }) => (
  <g transform={`rotate(${giro} ${x} ${y}) translate(${x} ${y}) scale(1.35) translate(${-x} ${-y})`} stroke={TINTA} strokeWidth={12} strokeLinejoin="round">
    <path d={`M ${x - 40} ${y - 30} Q ${x - 50} ${y + 34} ${x + 10} ${y + 36} L ${x + 90} ${y + 36} Q ${x + 116} ${y + 4} ${x + 70} ${y - 14} Q ${x + 20} ${y - 28} ${x - 40} ${y - 30} Z`} fill={TENIS} />
    <path d={`M ${x - 46} ${y + 20} L ${x + 104} ${y + 22}`} fill="none" strokeWidth={10} />
    <circle cx={x + 30} cy={y - 6} r={9} fill="white" strokeWidth={6} />
  </g>
);

const Ojo = ({ cx, cy, rx, ry, px, py, parpado, id, pupila = 1 }: { cx: number; cy: number; rx: number; ry: number; px: number; py: number; parpado: number; id: string; pupila?: number }) => {
  const linea = cy - ry + parpado * ry * 2;
  return (
    <g>
      <clipPath id={id}>
        <ellipse cx={cx} cy={cy} rx={rx} ry={ry} />
      </clipPath>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="white" />
      <g clipPath={`url(#${id})`}>
        <circle cx={cx + px} cy={cy + py} r={rx * 0.42 * pupila} fill={TINTA} />
        <circle cx={cx + px + rx * 0.15} cy={cy + py - rx * 0.15} r={rx * 0.13} fill="white" />
        {parpado > 0.02 ? (
          <path d={`M ${cx - rx - 5} ${cy - ry - 10} L ${cx + rx + 5} ${cy - ry - 10} L ${cx + rx + 5} ${linea + 4} L ${cx - rx - 5} ${linea - 8} Z`} fill={PIEL} />
        ) : null}
      </g>
      {parpado > 0.02 ? (
        <line x1={cx - rx + 2} y1={linea - 8} x2={cx + rx - 2} y2={linea + 4} stroke={TINTA} strokeWidth={10} strokeLinecap="round" />
      ) : null}
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={TINTA} strokeWidth={10} />
    </g>
  );
};

// Pose de los brazos (puntos de hombro a muñeca). Escena.tsx pasa de una a otra con resortes.
export type Pose = { brazoDer: Punto[]; brazoIzq: Punto[]; cabeza: number };

export const POSES: Record<string, Pose> = {
  // Puño arriba, el otro brazo abajo (la pose del personaje aprobado)
  baile: {
    brazoDer: [[628, 990], [722, 902], [782, 762], [800, 628]],
    brazoIzq: [[430, 990], [328, 1078], [262, 1170], [232, 1232]],
    cabeza: 0,
  },
  // Los dos brazos arriba: emocionado
  emocion: {
    brazoDer: [[628, 990], [748, 930], [850, 800], [912, 650]],
    brazoIzq: [[430, 990], [330, 925], [244, 805], [196, 655]],
    cabeza: -6,
  },
  // Señala hacia abajo a la derecha (el sello 10/10) con la otra mano en la cadera
  senala: {
    brazoDer: [[628, 990], [736, 1020], [830, 1080], [905, 1150]],
    brazoIzq: [[430, 990], [338, 1036], [318, 1110], [384, 1140]],
    cabeza: 8,
  },
};

export const mezclarPoses = (a: Pose, b: Pose, s: number): Pose => {
  const m = (pa: Punto[], pb: Punto[]): Punto[] => pa.map(([x, y], i) => [x + (pb[i][0] - x) * s, y + (pb[i][1] - y) * s]);
  return { brazoDer: m(a.brazoDer, b.brazoDer), brazoIzq: m(a.brazoIzq, b.brazoIzq), cabeza: a.cabeza + (b.cabeza - a.cabeza) * s };
};

type RaroProps = {
  filtroLinea: string;
  filtroColor: string;
  apertura?: number; // 0–1, del diálogo; sin diálogo el pico se mueve solo
  pose?: Pose;
  asombro?: number; // 0–1: ojo grande bien abierto y pupila chiquita
};

export const Raro = ({ filtroLinea, filtroColor, apertura, pose = POSES.baile, asombro = 0 }: RaroProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // Rebote al ritmo con "aplastar y estirar": se aplasta al caer y se estira en el aire.
  const p = fasePulso(t);
  const aire = Math.sin(Math.PI * p);
  const aplasta = Math.exp(-p * 10);
  const salto = 30 * aire;
  const sy = 1 - 0.1 * aplasta + 0.05 * aire;
  const sx = 1 + 0.09 * aplasta - 0.03 * aire;
  // La cabeza llega tarde: se hunde al caer y se mece de lado a lado con cada pulso.
  const meneo = 7 * Math.sin(((t - 0.08) * Math.PI) / PULSO);
  const hunde = 16 * aplasta;
  // Retraso para que antenas y baba sigan al cuerpo como látigo.
  const tarde = Math.exp(-((p - 0.1 + 1) % 1) * 7);

  const boca = apertura === undefined ? 6 + 10 * Math.max(0, Math.sin(t * Math.PI * 2.4)) : 3 + 20 * apertura;
  const parpado = t % 2.7 > 2.55 ? 0.95 : 0.38 * (1 - asombro);

  const brazoDer = ondear(pose.brazoDer, t * 0.6, 12, 0);
  const brazoIzq = ondear(pose.brazoIzq, t * 0.6, 10, 2);
  // La pierna de atrás patea con cada salto.
  const piernaIzq: Punto[] = [[470, 1230], [392, 1320 - 20 * aire], [318, 1352 - 50 * aire], [252, 1392 - 85 * aire]];
  const piernaDer = [[592, 1232], [622, 1350], [606, 1478]] as Punto[];
  // Mismo movimiento que el grupo de la cabeza (translate + rotate), para pegarle antenas y cuello.
  const giroCabeza = ((meneo + pose.cabeza) * Math.PI) / 180;
  const enCabeza = ([x, y]: Punto): Punto => {
    const dx = x - 540;
    const dy = y - 880;
    return [
      540 + dx * Math.cos(giroCabeza) - dy * Math.sin(giroCabeza) + meneo * 0.6,
      880 + dx * Math.sin(giroCabeza) + dy * Math.cos(giroCabeza) + hunde,
    ];
  };
  const antena = (pts: Punto[], k: number): Punto[] =>
    pts.map(([x, y], j) => enCabeza([x + (j / 2) * 16 * Math.sin((2 * Math.PI * t) / PULSO + k), y + (j / 2) * 40 * tarde]));
  const antenas: Punto[][] = [
    antena([[500, 612], [478, 548], [432, 504]], 0),
    antena([[542, 600], [560, 524], [598, 478]], 1.5),
    antena([[582, 610], [646, 566], [672, 520]], 3),
  ];

  const fideos: Fideo[] = [
    { pts: [enCabeza([530, 870]), [526, 950]], grosor: 66, color: PIEL },
    { pts: brazoDer, grosor: 50, color: PIEL },
    { pts: brazoIzq, grosor: 50, color: PIEL },
    { pts: piernaIzq, grosor: 56, color: PIEL },
    { pts: piernaDer, grosor: 56, color: PIEL },
    ...antenas.map((pts) => ({ pts, grosor: 14, color: PIEL_OSCURA })),
  ];

  const fin = (pts: Punto[]) => pts[pts.length - 1];
  const mano = (pts: Punto[]) => {
    const [x1, y1] = pts[pts.length - 2];
    const [x2, y2] = fin(pts);
    const largo = Math.hypot(x2 - x1, y2 - y1) || 1;
    const dx = (x2 - x1) / largo;
    const dy = (y2 - y1) / largo;
    return { x: x2 + dx * 22, y: y2 + dy * 22, giro: (Math.atan2(dy, dx) * 180) / Math.PI + 90 };
  };
  const giroPico = `rotate(${boca} 646 806)`;
  const cabeza = `translate(${meneo * 0.6} ${hunde}) rotate(${meneo + pose.cabeza} 540 880)`;

  // Baba que cuelga del pico y se estira.
  const baba = 30 + 40 * ((t * 0.8) % 1) + 30 * tarde;

  return (
    <g transform={`translate(0 ${-salto}) translate(560 1530) scale(${sx} ${sy}) translate(-560 -1530)`}>
      {/* Contorno de todo */}
      <g filter={`url(#${filtroLinea})`} fill="none" stroke={TINTA} strokeLinecap="round" strokeLinejoin="round">
        {fideos.map((f, i) => (
          <path key={i} d={curva(f.pts)} strokeWidth={f.grosor + C * 2} />
        ))}
        <path d={CUERPO} fill={TINTA} strokeWidth={C * 2} />
        <g transform={cabeza}>
          <path d={CABEZA} fill={TINTA} strokeWidth={C * 2} />
          <path d={PICO_ABAJO} fill={TINTA} strokeWidth={C * 2} transform={giroPico} />
          <path d={PICO_ARRIBA} fill={TINTA} strokeWidth={C * 2} />
        </g>
      </g>

      {/* Color plano con su propio temblor */}
      <g filter={`url(#${filtroColor})`}>
        <g fill="none" strokeLinecap="round" strokeLinejoin="round">
          {fideos.map((f, i) => (
            <path key={i} d={curva(f.pts)} strokeWidth={f.grosor} stroke={f.color} />
          ))}
        </g>
        <path d={CUERPO} fill={PIEL} />
        <g transform={cabeza}>
          <path d={CABEZA} fill={PIEL} />
          <path d={PICO_ABAJO} fill={PICO_OSCURO} transform={giroPico} />
          <path d={PICO_ARRIBA} fill={PICO} />
        </g>
      </g>

      {/* Detalles con tinta */}
      <g filter={`url(#${filtroLinea})`} strokeLinecap="round">
        {/* Manchas y ombligo */}
        <ellipse cx={445} cy={1050} rx={24} ry={18} fill={PIEL_OSCURA} />
        <ellipse cx={600} cy={1170} rx={30} ry={22} fill={PIEL_OSCURA} />
        <ellipse cx={420} cy={1170} rx={13} ry={10} fill={PIEL_OSCURA} />
        <path d="M 520 1110 q 12 12 0 22" fill="none" stroke={TINTA} strokeWidth={9} />
        <path d="M 610 975 Q 640 1010 646 1060" fill="none" stroke="white" strokeWidth={14} />

        <Guante {...mano(brazoDer)} />
        <Guante {...mano(brazoIzq)} />
        <Tenis x={fin(piernaIzq)[0] - 40} y={fin(piernaIzq)[1] + 10} giro={-25} />
        <Tenis x={fin(piernaDer)[0]} y={fin(piernaDer)[1] + 20} giro={0} />

        {antenas.map((a, i) => (
          <circle key={i} cx={fin(a)[0]} cy={fin(a)[1]} r={20} fill={BOLITA} stroke={TINTA} strokeWidth={10} />
        ))}
        <g transform={cabeza}>
          <path d="M 440 650 Q 470 618 510 612" fill="none" stroke="white" strokeWidth={14} />
          <ellipse cx={462} cy={830} rx={30} ry={17} fill={CACHETE} />
          <Ojo cx={488} cy={738} rx={58} ry={66} px={18 - 14 * asombro} py={16 - 12 * asombro} parpado={parpado} pupila={1 - 0.4 * asombro} id="ojo-grande" />
          <Ojo cx={596} cy={700} rx={26} ry={30} px={-8 + 8 * Math.sin(t * 3)} py={-6} parpado={0} id="ojo-chico" />
          {/* Boca: interior oscuro y la línea de cada mitad del pico */}
          <path d={PICO_ABAJO} fill="none" stroke={TINTA} strokeWidth={10} strokeLinejoin="round" transform={giroPico} />
          <path d={PICO_ARRIBA} fill="none" stroke={TINTA} strokeWidth={10} strokeLinejoin="round" />
          {/* Narina y dientito */}
          <ellipse cx={760} cy={738} rx={9} ry={6} fill={TINTA} />
          <path d={`M 700 ${806} l 14 22 l 14 -20`} fill="white" stroke={TINTA} strokeWidth={6} strokeLinejoin="round" transform={giroPico} />
          {/* Baba */}
          <path
            d={`M 868 ${872} q 6 ${baba * 0.6} 0 ${baba} q -12 10 -14 -4 q -2 ${-baba * 0.5} 8 ${-baba + 4}`}
            fill={BABA}
            stroke={TINTA}
            strokeWidth={7}
            transform={giroPico}
          />
        </g>
      </g>
    </g>
  );
};
