import { AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio } from "@remotion/media";
import { loadFont } from "@remotion/google-fonts/BowlbyOne";
import { estrella } from "./geometria";
import { mezclarPoses, POSES, Raro, TINTA } from "./Raro";
import { aperturaPico, Globo, Objeto } from "./Dialogo";
import { FRASES, golpe, porFrase, resorte } from "./ritmo";

const { fontFamily } = loadFont("normal", { weights: ["400"], subsets: ["latin"] });

const AMARILLO = "#FFC83A";
const FONDO = "#8E8C8A";
// Punto al que apunta la cámara (más o menos la panza del personaje)
const FOCO = { x: 560, y: 1000 };

export type EscenaProps = {
  readonly historia: boolean;
};

// "Hervido" de línea estilo Waking Life: la textura de ruido cambia cada 3 cuadros,
// así el dibujo tiembla como si estuviera hecho a mano cuadro por cuadro.
const Hervor = ({ id, semilla, fuerza, frecuencia }: { id: string; semilla: number; fuerza: number; frecuencia: number }) => (
  <filter id={id} x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency={frecuencia} numOctaves={2} seed={semilla} result="ruido" />
    <feDisplacementMap in="SourceGraphic" in2="ruido" scale={fuerza} xChannelSelector="R" yChannelSelector="G" />
  </filter>
);

export const Escena = ({ historia }: EscenaProps) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const t = frame / fps;
  const paso = Math.floor(frame / 3);

  const giro = (v: number, x: number, y: number) => `rotate(${12 * Math.sin(t * 2 + v)} ${x} ${y})`;
  const latido = (v: number) => 1 + 0.12 * Math.sin(t * 4 + v);

  // Cámara: arranca cerca y se abre mientras el personaje cae; en cada frase se acerca un poco más
  // y se ladea con resorte; golpecito con cada pulso; temblor cuando cae el 10/10.
  // `fuerza` < 1 = capa más lejana (parallax): se mueve menos que el personaje.
  const [, f2, f3] = FRASES;
  const entrada = resorte(frame, fps, 0, { damping: 13, stiffness: 90 });
  const zoom = porFrase(frame, fps, [1, 1, 1.08, 1.15], { damping: 12, stiffness: 110 }) * (1 + 0.22 * (1 - entrada)) * (1 + 0.012 * golpe(t, 8));
  const ladeo = porFrase(frame, fps, [0, 0, -2.5, 2.2], { damping: 10, stiffness: 120 });
  const dt = t - (f3.inicio + 0.45);
  const tiembla = dt > 0 ? Math.exp(-dt * 7) : 0;
  const camara = (fuerza: number) =>
    historia
      ? `translate(${FOCO.x + 18 * tiembla * Math.sin(dt * 70) * fuerza} ${FOCO.y + 14 * tiembla * Math.cos(dt * 55) * fuerza}) ` +
        `rotate(${ladeo * fuerza}) scale(${1 + (zoom - 1) * fuerza}) translate(${-FOCO.x} ${-FOCO.y})`
      : undefined;

  // Entrada del personaje: salta desde abajo, se estira mientras va rápido y rebota al llegar.
  const llega = resorte(frame, fps, 0, { damping: 10, stiffness: 120 });
  const velocidad = Math.abs(llega - resorte(frame - 1, fps, 0, { damping: 10, stiffness: 120 }));
  const estira = 1 + Math.min(0.35, velocidad * 4);
  const personaje = historia
    ? `translate(0 ${(1 - llega) * 1100}) translate(560 1560) scale(${1 / Math.sqrt(estira)} ${estira}) translate(-560 -1560) translate(65 215) scale(0.88)`
    : undefined;

  // Poses por frase (con rebote al cambiar) y ojos de asombro en la segunda frase.
  const s2 = resorte(frame, fps, f2.inicio, { damping: 10, stiffness: 150 });
  const s3 = resorte(frame, fps, f3.inicio, { damping: 10, stiffness: 150 });
  const pose = mezclarPoses(mezclarPoses(POSES.baile, POSES.emocion, s2), POSES.senala, s3);
  const asombro = Math.min(1, Math.max(0, s2 - s3));

  // Rayos de caricatura detrás, desde la segunda frase; en la tercera se vuelven amarillos.
  const rayos = Math.max(0, resorte(frame, fps, f2.inicio, { damping: 14, stiffness: 100 }));
  const amarillos = Math.min(1, Math.max(0, s3));
  const cuña = (i: number) => {
    const a = ((i * 20 + t * 25) * Math.PI) / 180;
    const b = a + (10 * Math.PI) / 180;
    const r = 1600 * rayos;
    return `M ${FOCO.x} ${FOCO.y} L ${FOCO.x + Math.cos(a) * r} ${FOCO.y + Math.sin(a) * r} L ${FOCO.x + Math.cos(b) * r} ${FOCO.y + Math.sin(b) * r} Z`;
  };

  return (
    <AbsoluteFill style={{ backgroundColor: FONDO }}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <Hervor id="linea" semilla={paso} fuerza={7} frecuencia={0.018} />
          <Hervor id="color" semilla={paso + 50} fuerza={14} frecuencia={0.012} />
          <Hervor id="letra" semilla={paso + 99} fuerza={6} frecuencia={0.03} />
          {/* Grano de colores del fondo (como impresión risográfica) */}
          <filter id="grano" x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency={0.9} numOctaves={1} seed={paso % 4} />
            <feColorMatrix values="6 0 0 0 -2.5  0 6 0 0 -2.5  0 0 6 0 -2.5  0 0 0 0 1" />
          </filter>
          <filter id="papel" x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency={0.75} numOctaves={2} seed={(paso % 4) + 10} />
            <feColorMatrix type="saturate" values="0" />
          </filter>
        </defs>

        <rect width={width} height={height} filter="url(#grano)" opacity={0.7} />

        {historia && rayos > 0 ? (
          <g transform={camara(0.5)}>
            {Array.from({ length: 18 }, (_, i) => (
              <path key={i} d={cuña(i)} fill="white" opacity={0.13 * (1 - amarillos)} />
            ))}
            {Array.from({ length: 18 }, (_, i) => (
              <path key={i} d={cuña(i)} fill={AMARILLO} opacity={0.3 * amarillos} />
            ))}
          </g>
        ) : null}

        {/* Estrellitas (capa lejana) */}
        <g transform={camara(0.5)} filter="url(#linea)" stroke={TINTA} strokeWidth={9} strokeLinejoin="round">
          <g transform={giro(0, 180, 880)}>
            <g style={{ transformOrigin: "180px 880px", scale: `${latido(0)}` }}>
              <path d={estrella(180, 880, 105)} fill={AMARILLO} />
            </g>
          </g>
          <g style={{ transformOrigin: "930px 720px", scale: `${latido(1.5)}` }}>
            <path d={estrella(930, 720, 64)} fill={TINTA} />
          </g>
          <g style={{ transformOrigin: "880px 1480px", scale: `${latido(3)}` }}>
            <path d={estrella(880, 1480, 55)} fill={TINTA} />
          </g>
          <g style={{ transformOrigin: "160px 600px", scale: `${latido(4.2)}` }}>
            <path d={estrella(160, 600, 45)} fill={AMARILLO} />
          </g>
        </g>

        {/* Con diálogo, el personaje baja y se achica para dejar arriba el globo de texto */}
        <g transform={camara(1)}>
          <g transform={personaje}>
            {historia ? (
              <Raro filtroLinea="linea" filtroColor="color" apertura={aperturaPico(t)} pose={pose} asombro={asombro} />
            ) : (
              <Raro filtroLinea="linea" filtroColor="color" />
            )}
          </g>
          {historia ? <Objeto fontFamily={fontFamily} /> : null}
        </g>

        {/* El globo se mueve poquito con la cámara para que se lea bien */}
        {historia ? (
          <g transform={camara(0.3)}>
            <Globo fontFamily={fontFamily} />
          </g>
        ) : null}

        {/* Textura de papel encima de todo */}
        <rect width={width} height={height} filter="url(#papel)" opacity={0.13} style={{ mixBlendMode: "multiply" }} />
      </svg>
      {historia ? <Audio src={staticFile("raro-sustancia.wav")} premountFor={fps} /> : null}
    </AbsoluteFill>
  );
};
