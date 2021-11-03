#!/usr/bin/bash
#img-optimize assets/ --jpg --png --webp
for f in **/*.png.webp; do
    mv -- "$f" "${f%.png.webp}.webp"
done

for f in **/*.jpeg.webp; do
    mv -- "$f" "${f%.jpeg.webp}.webp"
done

for f in **/*.jpg.webp; do
    mv -- "$f" "${f%.jpg.webp}.webp"
done
