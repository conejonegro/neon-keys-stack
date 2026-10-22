import { Composition, Folder } from "remotion";
import { Escena } from "./rubberhose/Escena";

export const RemotionRoot: React.FC = () => {
  return (
    <Folder name="RubberHose">
      <Composition
        id="RaroPersonaje"
        component={Escena}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ historia: false }}
      />
      <Composition
        id="RaroSustancia"
        component={Escena}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ historia: true }}
      />
    </Folder>
  );
};
