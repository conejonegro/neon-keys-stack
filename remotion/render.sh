#!/bin/zsh
# Render de un video de Remotion en esta Mac (macOS 12).
# El ffmpeg que trae Remotion no corre en macOS 12, así que Remotion solo saca los cuadros (JPEG)
# y el .mp4 se arma con el ffmpeg de ~/.local/bin junto con el WAV de sonido.py.
#
# Uso:  ./render.sh COMPOSICION NOMBRE SEGUNDOS [pruebas|videos]
# Ej.:  ./render.sh RaroSustancia caricatura-sustancia-prueba 10 pruebas
set -euo pipefail

COMP=$1
NOMBRE=$2
SEG=$3
DESTINO=${4:-pruebas}

AQUI=${0:A:h}
OUT=$AQUI/../out
TMP=$OUT/.tmp/$NOMBRE
FFMPEG=~/.local/bin/ffmpeg

cd $AQUI
rm -rf $TMP && mkdir -p $TMP

echo "1/3 Sonido…"
../.venv/bin/python sonido.py $SEG public/raro-sustancia.wav

echo "2/3 Cuadros con Remotion…"
npx remotion render $COMP $TMP/cuadros --sequence --image-format=jpeg --jpeg-quality=95 --concurrency=1

echo "3/3 Armando el .mp4…"
# Remotion numera con ceros a la izquierda (element-000.jpeg) según el total de cuadros
LARGOS=$(ls $TMP/cuadros | sed -E 's/element-([0-9]+)\.jpeg/\1/' | awk '{print length}' | sort -u)
if [[ $(echo $LARGOS | wc -w) -eq 1 ]]; then PATRON="element-%0${LARGOS}d.jpeg"; else PATRON="element-%d.jpeg"; fi
$FFMPEG -v error -y -framerate 30 -i $TMP/cuadros/$PATRON -i public/raro-sustancia.wav \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest \
  -movflags +faststart $TMP/$NOMBRE.mp4

mv $TMP/$NOMBRE.mp4 $OUT/$DESTINO/$NOMBRE.mp4
rm -rf $TMP
echo "Listo: out/$DESTINO/$NOMBRE.mp4"
