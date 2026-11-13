// Wrath pane header: a carved, gilded title bar for each pane.
//   { "tab": "active", "pane": { "header": { "content": { "mod": "wrath-pane" }, "height": 34 } } }
// Shows the program's icon, the agent's name or the terminal's title in Cinzel,
// the folder in italic Garamond, and the agent's status as sigils (a turning
// rune ring while working, a red summons when blocked, a gold star when done).
// Buttons split, zoom and close this pane on hover. Props: { pane, terminal }.

import { View, div, svg, image, PathBuilder, Background } from "gpui-kit";
import { h_flex } from "gpui-base";
import { panes, props, run, theme, home } from "herdr";
import { hatch, rivets } from "./kit.js";

const DIR = "mods/wrath-pane";
const TITLE_FONT = "Cinzel";
const BODY_FONT = "EB Garamond";

const RECT = () => PathBuilder.fill().move_to("0%", "0%").line_to("100%", "0%").line_to("100%", "100%").line_to("0%", "100%").close().build();

/** A layer that fills its (relative) parent with a gradient. */
function gradient(from, to, angle) {
  return window.paint_path(RECT(), Background.linear_gradient(angle, from, to)).absolute().top(0).left(0).size_full();
}

/** The gilded rule along the header's foot: fades in, glows, fades out. */
function rule(t, focused) {
  const gold = t.accent;
  const peak = focused ? "" : "88";
  return h_flex().absolute().left(0).bottom(1).w_full().h(focused ? 2 : 1)
    .child(div().relative().flex_1().h_full().child(gradient(gold + "00", gold + peak, 90)))
    .child(div().relative().flex_1().h_full().child(gradient(gold + peak, gold + "00", 90)));
}

/** The folder as a breadcrumb trail: ~ › Documentos › Workspace › iam_core (last 3 shown). */
function crumbs(t, path, focused) {
  const parts = path.split("/").filter(Boolean);
  const shown = parts.length > 4 ? ["…", ...parts.slice(-3)] : parts;
  const items = [];
  shown.forEach((seg, i) => {
    if (i > 0) items.push(div().flex_none().text_size(12).text_color(t.accent + "aa").child("›"));
    const last = i === shown.length - 1;
    items.push((last ? div().min_w(0).truncate() : div().flex_none())
      .font_family(BODY_FONT).italic().text_size(13.5)
      .text_color(last ? (focused ? t.foreground : t.muted) : t.dim).child(seg));
  });
  return h_flex().flex_1().min_w(0).overflow_hidden().gap(5).items_center().children(items);
}

/** A short slatted-iron block, like the grate on a war banner's bar. */
function grate(t, w) {
  return div().relative().flex_none().w(w).h(10).rounded(1).border(1).border_color("#00000080")
    .bg("#1a0e11").overflow_hidden().child(hatch(t.accent + "40", 1.2, 4));
}

function icon(p, size, color) {
  if (!p?.icon) return null;
  return p.tint ? svg(p.icon).size(size).flex_none().text_color(color) : image(p.icon).w(size).h(size).flex_none();
}

function folder(cwd) {
  if (!cwd) return "";
  const h = home();
  return cwd === h ? "~" : cwd.startsWith(h + "/") ? "~" + cwd.slice(h.length) : cwd;
}

export default class WrathPane extends View {
  init() { this.hovered = false; }

  me() {
    return panes().find((p) => p.pane === props()?.pane);
  }

  button(t, id, icon, command, args) {
    return div()
      .id(id)
      .p(3)
      .rounded(2)
      .text_color(t.dim)
      .hover((s) => s.bg(t.accent + "22").text_color(t.accent))
      .on_click((_e, cx) => {
        cx.stop_propagation();
        run(command, args);
      })
      .child(svg(`${DIR}/${icon}.svg`).size(14));
  }

  status(t, st) {
    if (st === "working")
      return h_flex().flex_none().gap(5).items_center()
        .child(svg(`${DIR}/rune-ring.svg`).size(14).text_color(t.working).spin(2400))
        .child(div().font_family(BODY_FONT).italic().text_size(12.5).text_color(t.working).child("tecendo encantamento…"));
    if (st === "blocked")
      return h_flex().flex_none().gap(5).px(7).h(20).items_center().rounded(2)
        .bg(t.blocked + "2e").border(1).border_color(t.blocked + "aa")
        .child(svg(`${DIR}/swords.svg`).size(12).text_color(t.blocked))
        .child(div().font_family(TITLE_FONT).font_weight(700).text_size(10).text_color(t.blocked).child("CLAMOR · RESPONDA"));
    if (st === "done")
      return h_flex().flex_none().gap(5).items_center()
        .child(image("mods/wrath-chrome/seal-mini.svg").w(17).h(17).flex_none())
        .child(div().font_family(BODY_FONT).italic().text_size(12.5).text_color(t.done).child("selado"));
    return null;
  }

  render(cx) {
    const t = theme();
    const p = this.me();
    if (!p) return div();
    const MOD_TITLES = { "wrath-review": "Julgamento do Mago" };
    const name = MOD_TITLES[p.title] ?? MOD_TITLES[p.program?.name] ?? (((p.program?.agent || p.program?.shell) && p.program.name) || p.title || p.program?.name || "shell");
    const pic = icon(p.program, 14, p.focused ? t.accent : t.dim);
    const pane = p.pane;
    const sigil = this.status(t, p.status);
    return div()
      .id(`wrath-head-${pane}`)
      .relative()
      .size_full()
      .overflow_hidden()
      .on_hover((hovered, cx) => { this.hovered = hovered; cx.notify(); })
      .on_click(() => run("pane.focus", { pane }))
      // carved leather strip with the gilded rule along its foot
      .child(gradient("#2a161b", "#140a0e", 180))
      .child(div().absolute().top(0).left(0).w_full().h(1).bg(t.accent + "1f"))
      .child(div().absolute().bottom(0).left(0).w_full().h(1).bg("#000000aa"))
      .child(rule(t, p.focused))
      .child(
        h_flex()
          .absolute().top(0).left(0)
          .size_full()
          .pl(6).pr(6)
          .gap(8)
          .items_center()
          .child(grate(t, 14))
          .child(image(`${DIR}/flourish.svg`).w(40).h(22).flex_none().opacity(p.focused ? 1 : 0.45))
          .when(Boolean(pic), (el) => el.child(pic))
          .child(div().flex_none().truncate().max_w(280)
            .font_family(TITLE_FONT).font_weight(700).text_size(12.5)
            .text_color(p.focused ? t.accent : t.foreground)
            .child(name.toUpperCase()))
          .child(image(`${DIR}/diamond.svg`).w(7).h(7).flex_none().opacity(0.8))
          .child(crumbs(t, folder(p.cwd), p.focused))
          .when(Boolean(sigil), (el) => el.child(sigil))
          .when(this.hovered, (el) => el
            .child(this.button(t, `wh-r-${pane}`, "split-right", "pane.split", { direction: "right", pane }))
            .child(this.button(t, `wh-d-${pane}`, "split-down", "pane.split", { direction: "down", pane }))
            .child(this.button(t, `wh-z-${pane}`, p.zoomed ? "unzoom" : "zoom", "pane.zoom", { pane }))
            .child(this.button(t, `wh-x-${pane}`, "close", "pane.close", { pane })))
          .child(image(`${DIR}/flourish-r.svg`).w(40).h(22).flex_none().opacity(p.focused ? 1 : 0.45))
          .child(grate(t, 14)))
      .children(rivets(t, 3, 4));
  }
}
