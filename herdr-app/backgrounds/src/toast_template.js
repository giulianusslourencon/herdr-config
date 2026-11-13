// How notifications look. Anything can post one with notify({ title, body,
// level, icon, action }); replace this mod to restyle them all. Click to
// run its action (e.g. go to the agent) and dismiss it.
//
// WRATH PATCH: versão traduzida (fantasia vanceana) e estilizada deste mod.
// Escrita por ~/.config/herdr-app/backgrounds/src/toast_patch.py, que a
// reaplica sempre que o Herdr restaura o original (ver wrath-toast.path).

import { View, div, image, svg } from "gpui-kit";
import { v_flex, h_flex } from "gpui-base";
import { props, closeOverlay, run, theme } from "herdr";

const DOT = { error: "blocked", warning: "working", success: "done", info: "accent" };
const SIGIL = { error: "blocked", warning: "working", success: "done", info: "idle" };
const TITLE_FONT = "Cinzel";
const BODY_FONT = "EB Garamond";

// The app's own English toasts, rewritten; anything else passes unchanged.
const RULES = [
  [/^(.+?) (?:has )?finished$/i, (m) => `${m[1]} cumpriu sua servidão`],
  [/^(.+?) needs you$/i, (m) => `${m[1]} ergue um Clamor Insistente`],
  [/^(.+?) is working$/i, (m) => `${m[1]} tece um encantamento`],
  [/^(\d+) agents? need(?:s)? you$/i, (m) => `${m[1]} sandestins clamam por você`],
  [/^Update ready$/i, () => "Novo tomo pronto"],
  [/^Updated$/i, () => "Tomo atualizado"],
  [/^Restart$/i, () => "Reiniciar"],
  [/^(.+?) failed$/i, (m) => `Contramágica: ${m[1]} falhou · aplique o Rito da Manutenção Percussiva`],
  [/^Couldn't (.+)$/i, (m) => `Não foi possível ${m[1]}`],
];
const WORDS = [
  [/\bagents\b/gi, "sandestins"],
  [/\bagent\b/gi, "sandestin"],
  [/\bspace\b/gi, "domínio"],
  [/\bthis computer\b/gi, "a torre natal"],
  [/\bClick to go there\b/gi, "Clique para ir até lá"],
];

function translate(text, words) {
  if (!text) return "";
  for (const [rx, fn] of RULES) {
    const m = text.match(rx);
    if (m) return fn(m);
  }
  return words ? WORDS.reduce((s, [rx, to]) => s.replace(rx, to), text) : text;
}

export default class Toast extends View {
  render(cx) {
    const t = theme();
    const p = props() ?? {};
    const level = p.level ?? "info";
    const color = t[DOT[level] ?? "accent"] ?? t.accent;
    const mark = p.icon
      ? image(p.icon).w(18).h(18).flex_none()
      : level === "success" ? image("mods/wrath-chrome/seal-mini.svg").w(20).h(20).flex_none()
      : svg(`mods/wrath-ritual/sigil-${SIGIL[level] ?? "idle"}.svg`).size(18).flex_none().text_color(color);
    return h_flex()
      .id("toast")
      .size_full()
      .px(16)
      .gap(12)
      .items_center()
      .bg(t.popover)
      .relative()
      .border_l(3)
      .border_color(color)
      .children([["top", "left"], ["top", "right"], ["bottom", "right"]].map(([v, h]) =>
        div().absolute()[v](4)[h](4).size(5).rounded_full().bg(t.accent).border(1).border_color("#00000099")))
      .cursor_pointer()
      .hover((s) => s.bg(t.hover))
      .on_click(() => {
        if (p.action?.name) run(p.action.name, p.action.args ?? {});
        closeOverlay(p.overlay);
      })
      .child(mark)
      .child(
        v_flex()
          .flex_1()
          .overflow_hidden()
          .child(div().truncate().font_family(TITLE_FONT).font_weight(700).text_size(12.5).text_color(t.accent)
            .child(translate(p.title ?? "", true)))
          .when(Boolean(p.body), (el) => el.child(div().truncate().font_family(BODY_FONT).italic().text_size(13)
            .text_color(t.muted).child(translate(p.body ?? "", true)))),
      );
  }
}
