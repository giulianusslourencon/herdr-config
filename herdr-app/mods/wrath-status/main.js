import { View, div, svg } from "gpui-kit";
import { h_flex } from "gpui-base";
import { plaque, rivet } from "./kit.js";
import { spaces, agents, theme, run, window, keys, exec, appHome, setShared, notify } from "herdr";

const GB = (b) => (b / 1e9).toFixed(1).replace(".", ",");

export default class WorkspaceStatus extends View {
  // O Espírito da Máquina: lê o consumo do computador a cada 3 s (espirito.py) e o
  // compartilha como shared("espirito") para a Crônica do Mestre.
  init(_props, cx) {
    this.esp = null;
    const read = (cx) => cx.spawn(async (cx) => {
      try {
        const r = await exec("python3", [`${appHome()}/mods/wrath-status/espirito.py`], { timeout: 5000 });
        if (r.code === 0) { this.esp = JSON.parse(r.stdout); setShared("espirito", this.esp); this.guard(this.esp.guarda); cx.notify(); }
      } catch {}
    });
    read(cx);
    cx.timer.every(3000, (cx) => read(cx));
  }

  // O guardião (~/.claude/grimorio/guardiao.py, serviço systemd) conteve algo: avisa uma vez.
  guard(g) {
    const at = g?.ultimo?.at ?? 0;
    if (this.lastGuard !== undefined && at > this.lastGuard) {
      notify({ title: g.ultimo.kind === "contido" ? "O guardião conteve um sandestin" : "Máquina sob pressão",
        body: g.ultimo.text, level: g.ultimo.kind === "contido" ? "warning" : "info", timeout: 15000 });
    }
    this.lastGuard = at;
  }

  // The palette key as actually bound, not a hardcoded one; without a
  // binding the hint stays useful ("Índice do tomo") instead of lying.
  hint(t) {
    const mac = window()?.platform === "macos";
    const mod = { cmd: mac ? "⌘" : "Ctrl+", ctrl: mac ? "⌃" : "Ctrl+", shift: mac ? "⇧" : "Shift+", alt: mac ? "⌥" : "Alt+", option: mac ? "⌥" : "Alt+" };
    const b = keys().find((k) => k.section === "global" && k.action === "app.palette");
    const parts = b && b.keys.endsWith("--") ? [...b.keys.slice(0, -2).split("-"), "-"] : b?.keys.split("-");
    const key = parts && parts.map((p) => mod[p.toLowerCase()] ?? p.toUpperCase()).join("");
    return key ? `${key}  Índice do tomo` : "Índice do tomo";
  }

  render() {
    const t = theme();
    const space = spaces().find(s => s.active);
    const list = agents();
    const needs = list.filter(a => a.status === "blocked").length;
    const plate = (id, icon, text, color) => h_flex().id(id).relative().h(20).px(9).gap(6).items_center().rounded(2)
      .overflow_hidden().border(1).border_color(color ? color + "aa" : t.accent + "55")
      .children(plaque(t))
      .when(Boolean(icon), el => el.child(svg(`mods/wrath-chrome/${icon}.svg`).size(12).text_color(color ?? t.accent)))
      .child(div().text_color(color ?? t.muted).child(text));
    const stud = () => rivet(t, 5).flex_none();
    const plates = [plate("st-place", space?.machine ? "server" : "monitor", space?.machine ?? "Torre natal")];
    if (space?.branch) plates.push(plate("st-branch", "branch", space.branch));
    plates.push(plate("st-agents", null, `${list.length} ${list.length === 1 ? "sandestin" : "sandestins"}`));
    if (needs > 0) plates.push(plate("st-needs", null, `${needs} ${needs === 1 ? "clamor" : "clamores"} por você`, t.blocked));
    const row = [];
    plates.forEach((p, i) => { if (i) row.push(stud()); row.push(p); });
    return h_flex().size_full().px(10).gap(7).items_center().bg(t.chrome).border_t(1).border_color(t.border)
      .font_family("EB Garamond").text_size(13)
      .children(row)
      .child(div().flex_1())
      .when(Boolean(this.esp), (el) => {
        const e = this.esp, memPct = (100 * e.mem.used) / e.mem.total;
        const strain = Math.max(e.cpu ?? 0, memPct, e.temp ? (e.temp - 55) * 2.5 : 0);
        const tone = strain < 70 ? null : strain < 90 ? t.working : t.blocked;
        const text = [`${e.cpu == null ? "…" : Math.round(e.cpu)}%`, `${GB(e.mem.used)}/${GB(e.mem.total)} GB`]
          .concat(e.temp ? [`${Math.round(e.temp)}°`] : []).join(" · ");
        return el.child(plate("st-espirito", "cog", text, tone)
          .tooltip(`Espírito da Máquina · CPU ${e.cpu ?? "…"}% de ${e.cores} núcleos · carga ${e.load.join(" ")} · memória ${GB(e.mem.used)} de ${GB(e.mem.total)} GB · disco ${GB(e.disk.used)} de ${GB(e.disk.total)} GB${e.temp ? ` · ${e.temp} °C` : ""}`)
          .cursor_pointer().on_click(() => { run("layout.select", { stack: "panel-body", child: "chronicle" }); run("layout.show", { id: "panel" }); }))
          .child(stud());
      })
      .child(plate("palette", null, this.hint(t)).cursor_pointer().on_click(() => run("app.palette")));
  }
}
