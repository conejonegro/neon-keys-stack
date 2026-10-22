import { spring } from "remotion";
import guion from "./guion.json";

// Tiempos compartidos: guion, pulso de la música (mismo BPM que sonido.py) y resortes.

export type Frase = { inicio: number; fin: number; habla: number; texto: string; objeto?: string };
export const FRASES: Frase[] = guion.frases;
export const SPS = guion.silabasPorSegundo;

export const BPM = 96;
export const PULSO = 60 / BPM;

// 0 justo al caer el pulso → 1 justo antes del siguiente.
export const fasePulso = (t: number) => (t % PULSO) / PULSO;
// Golpe que dura poquito después de cada pulso (1 al caer, se apaga rápido).
export const golpe = (t: number, rapidez = 10) => Math.exp(-fasePulso(t) * rapidez);

// Índice de la frase actual (o la última que ya empezó); -1 antes de la primera.
export const indiceFrase = (t: number) => {
  let k = -1;
  FRASES.forEach((f, i) => {
    if (t >= f.inicio) k = i;
  });
  return k;
};

type Config = { damping?: number; stiffness?: number; mass?: number };

// Resorte que arranca en el segundo `desde`. Puede pasarse de 1 (rebote) antes de asentarse.
export const resorte = (frame: number, fps: number, desde: number, config: Config = {}) =>
  spring({ frame: frame - Math.round(desde * fps), fps, config: { damping: 11, stiffness: 140, ...config } });

// Valor que cambia de nivel en cada frase con un resorte (niveles[0] antes de la primera).
export const porFrase = (frame: number, fps: number, niveles: number[], config: Config = {}) => {
  let v = niveles[0];
  FRASES.forEach((f, i) => {
    if (niveles[i + 1] === undefined) return;
    v += (niveles[i + 1] - niveles[i]) * resorte(frame, fps, f.inicio, config);
  });
  return v;
};
