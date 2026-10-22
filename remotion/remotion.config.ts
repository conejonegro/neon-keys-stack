import { Config } from "@remotion/cli/config";

// macOS 12: el Chrome que descarga Remotion no arranca aquí; se usa el Chrome instalado
// (igual que escenas3d/grabar.js).
Config.setBrowserExecutable("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome");
Config.setChromeMode("chrome-for-testing");
Config.setChromiumOpenGlRenderer("angle");
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
