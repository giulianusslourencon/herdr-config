#!/bin/sh
# Copia o wrath_kit.js para cada mod wrath-* como kit.js.
for d in "$HOME"/.config/herdr-app/mods/wrath-*/; do cp "$HOME/.config/herdr-app/backgrounds/src/wrath_kit.js" "$d/kit.js"; done
