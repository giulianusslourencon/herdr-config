// Wrath kit: forged-iron and carved-stone pieces shared by the wrath-* mods.
// Copied into each mod folder as kit.js by backgrounds/src/install_kit.sh
// (mods import siblings only). Every layer here is absolute: put it inside a
// .relative() parent, before the content, and it paints behind it.

import { div, PathBuilder, Background } from "gpui-kit";

const RECT = () => PathBuilder.fill().move_to("0%", "0%").line_to("100%", "0%").line_to("100%", "100%").line_to("0%", "100%").close().build();

/** A gradient filling the parent. */
export function gradient(from, to, angle = 180) {
  return window.paint_path(RECT(), Background.linear_gradient(angle, from, to)).absolute().top(0).left(0).size_full();
}

/** Slatted iron: diagonal hatching filling the parent. */
export function hatch(color, width = 1.5, interval = 4) {
  return window.paint_path(RECT(), Background.pattern_slash(color, width, interval)).absolute().top(0).left(0).size_full();
}

/** One gilded rivet head. */
export function rivet(t, size = 5) {
  return div().size(size).rounded_full().bg(t.accent).border(1).border_color("#00000099");
}

/** Four rivets, one per corner, `inset` px in. */
export function rivets(t, inset = 3, size = 5) {
  return [
    rivet(t, size).absolute().top(inset).left(inset),
    rivet(t, size).absolute().top(inset).right(inset),
    rivet(t, size).absolute().bottom(inset).left(inset),
    rivet(t, size).absolute().bottom(inset).right(inset),
  ];
}

/** Carved plaque layers: dark stone fill, a lit top edge and a shadowed foot.
 *  `aura` adds the abyssal-violet glow of a chosen thing; `pulse` makes it breathe. */
export function plaque(t, { aura = false, pulse = false, from = "#2e1a1f", to = "#150a0e" } = {}) {
  const layers = [
    gradient(from, to, 180),
    div().absolute().top(0).left(0).w_full().h(1).bg(t.accent + "33"),
    div().absolute().bottom(0).left(0).w_full().h(1).bg("#000000b0"),
  ];
  if (aura) {
    const glow = div().absolute().top(0).left(0).size_full().child(gradient(t.ansi13 + "00", t.ansi13 + "40", 180));
    layers.push(pulse ? glow.loop("opacity", { from: 0.45, to: 1, period: 1800 }) : glow);
  }
  return layers;
}
