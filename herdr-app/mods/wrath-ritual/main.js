// Círculo de Invocação: every agent (familiar) as a candle on a summoning circle.
// Ley lines run from each familiar to the circle's heart, coloured by its status;
// the heart's sigil shows the most urgent state (Sending > Concentrando >
// Missão cumprida > Descanso longo). Click a familiar to go to its pane.

import { View, div, svg, image, PathBuilder, Background } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { agents, theme, run, terminals, panes, home, readTextFile, watchFolder } from "herdr";
import { christen, cleanTask } from "./names.js";

const DIR = "mods/wrath-ritual";
const TITLE_FONT = "Cinzel";
const BODY_FONT = "EB Garamond";

// Ritual names for each status, most urgent first.
const RITES = [
  { status: "blocked", name: "Clamor Insistente", hint: "precisa de você" },
  { status: "working", name: "Tecendo encantamento", hint: "trabalho em curso" },
  { status: "done", name: "Servidão cumprida", hint: "voltou com notícias" },
  { status: "idle", name: "Repouso sob o sol rubro", hint: "aguardando ordens" },
];
const riteOf = (s) => RITES.find((r) => r.status === s) ?? RITES[3];

// True names given this render: key (terminal address, subagent or shell key) -> { proper, title, full }.
let NAMED = new Map();
const programOf = (a) => (a.program?.agent && a.program.name) || a.app || "sandestin";
/** What a main sandestin is doing: its terminal title (spinner glyphs stripped), else its tab. */
const taskOf = (a) => cleanTask(a.title) || (/^\d+$/.test(a.tab_name ?? "") ? "" : a.tab_name) || "";
const nameOf = (a) => NAMED.get(a.address)?.full ?? programOf(a);
const properOf = (a) => NAMED.get(a.address)?.proper ?? programOf(a);

const NODE = 36;
const LESSER = 18;

// A sub-agent without a pane reports to its parent: error counts as blocked,
// and it is never "done" on its own (the parent's done is the news).
const lesserStatus = (s) => (s === "error" ? "blocked" : s === "done" ? "idle" : s ?? "idle");

/** Every live descendant of `addr` among the core's terminals (sub-agents started with hc run). */
function descendants(all, addr) {
  const kids = all.filter((k) => k.parent === addr && k.state === "live");
  return kids.flatMap((k) => [k, ...descendants(all, k.address)]);
}

/** Opens a background terminal: its pane if it has one, else a peek over the tab. */
function reveal(address) {
  if (panes().some((p) => p.terminal === address)) run("pane.focus", { terminal: address });
  else run("terminal.peek", { terminal: address });
}

// Where the Claude Code hook bridge (~/.claude/grimorio/familiares.py) writes,
// per Herdr terminal, the subagents and background shells running inside it.
const FAMILIARS = () => `${home()}/.claude/grimorio/familiares`;
const STALE_MS = 2 * 60 * 60 * 1000; // a crashed Claude fires no hook: forget after 2h

export default class Ritual extends View {
  init(_props, cx) {
    this.size = { width: 360, height: 600 };
    this.inner = {}; // terminal address -> bridge record
    cx.spawn(async (cx) => {
      await this.reload();
      cx.notify();
      for (;;) {
        try { await watchFolder(FAMILIARS()); } catch { return; }
        await this.reload();
        cx.notify();
      }
    });
  }

  async reload() {
    const next = {};
    for (const a of agents()) {
      if (a.address.includes("/")) continue; // the bridge only knows this machine
      const text = await readTextFile(`${FAMILIARS()}/${a.address}.json`).catch(() => null);
      if (!text) continue;
      try {
        const rec = JSON.parse(text);
        if (Date.now() - (rec.updated ?? 0) * 1000 < STALE_MS) next[a.address] = rec;
      } catch {}
    }
    this.inner = next;
  }

  /** Subagents and background shells a Claude session reported through the bridge. */
  innerOf(a) {
    const rec = this.inner[a.address];
    if (!rec) return [];
    const agents = Object.entries(rec.agents ?? {}).map(([id, g]) => ({
      key: `${a.address}-ag-${id}`, address: null, pane: a.pane, kind: "subagente",
      name: g.description || g.type || "subagente", texts: [g.type, g.description], status: "working", master: properOf(a) }));
    const shells = (rec.shells ?? []).map((sh, i) => ({
      key: `${a.address}-sh-${sh.id ?? i}`, address: null, pane: a.pane, kind: "encantamento",
      name: sh.description || sh.command || "encantamento", texts: [sh.description, sh.command], status: "working", master: properOf(a) }));
    return [...agents, ...shells];
  }

  color(t, s) {
    return { blocked: t.blocked, working: t.working, done: t.done }[s] ?? t.idle ?? t.dim;
  }

  leyLine(t, S, x, y, s) {
    const pct = (v) => `${(v / S) * 100}%`;
    let p = PathBuilder.stroke(s === "blocked" ? 2.2 : 1.6).move_to("50%", "50%").line_to(pct(x), pct(y));
    if (s === "idle" || !s) p = p.dash_array([3, 4]);
    const color = this.color(t, s) + (s === "idle" || !s ? "55" : "99");
    const line = window.paint_path(p.build(), Background.solid(color)).size_full();
    const layer = div().absolute().top(0).left(0).size_full().child(line);
    return s === "blocked" ? layer.loop("opacity", { from: 0.35, to: 1, period: 1100 }) : layer;
  }

  node(t, a, x, y) {
    const s = a.status;
    const c = this.color(t, s);
    const rite = riteOf(s);
    const pic = a.program?.icon
      ? (a.program.tint ? svg(a.program.icon).size(16).text_color(c) : image(a.program.icon).w(16).h(16))
      : div().font_family(TITLE_FONT).font_weight(700).text_size(14).text_color(c).child(nameOf(a).slice(0, 1).toUpperCase());
    const halo = 52, off = (halo - NODE) / 2;
    return div()
      .id(`familiar-${a.address}`)
      .absolute().left(x - NODE / 2).top(y - NODE / 2).size(NODE)
      .cursor_pointer()
      .tooltip(`${nameOf(a)}${taskOf(a) ? ` · ${taskOf(a)}` : ""} · ${rite.name} (${rite.hint}) · ${a.space_name}`)
      .on_click(() => run("pane.focus", { pane: a.pane }))
      .when(s === "blocked", (el) => el.child(
        div().absolute().left(-off).top(-off).size(halo).rounded_full().bg(c + "55")
          .loop("opacity", { from: 0.15, to: 0.9, period: 900 })))
      .when(s === "done", (el) => el.child(
        div().absolute().left(-off + 4).top(-off + 4).size(halo - 8).rounded_full().bg(c + "2a")))
      .when(s === "working", (el) => el.child(
        svg(`${DIR}/node-ring.svg`).absolute().left(-off).top(-off).size(halo).text_color(c).spin(2600)))
      .child(div().absolute().left(0).top(0).size(NODE).rounded_full()
        .bg("#140c10").border(a.focused ? 2.5 : 1.5).border_color(a.focused ? t.accent : c)
        .flex().items_center().justify_center()
        .when(s === "idle" || !s, (el) => el.opacity(0.7))
        .child(pic));
  }

  // Inside the circle only the proper name fits; the epithet goes in the list below it.
  label(t, a, x, y, S) {
    const w = 86;
    const below = y < S * 0.5;
    const named = NAMED.get(a.address);
    return div().absolute().left(Math.max(0, Math.min(S - w, x - w / 2))).top(below ? y + 26 : y - 26 - 15).w(w)
      .text_center().truncate().font_family(TITLE_FONT).font_weight(700).text_size(10)
      .text_color(a.focused ? t.accent : t.foreground).child((named?.proper ?? programOf(a)).toUpperCase());
  }

  /** A thread of light between two points of the circle (percent of S). */
  thread(t, S, x1, y1, x2, y2, s) {
    const pct = (v) => `${(v / S) * 100}%`;
    let p = PathBuilder.stroke(1).move_to(pct(x1), pct(y1)).line_to(pct(x2), pct(y2));
    if (s === "idle") p = p.dash_array([2, 3]);
    const line = window.paint_path(p.build(), Background.solid(this.color(t, s) + (s === "idle" ? "55" : "aa"))).size_full();
    return div().absolute().top(0).left(0).size_full().child(line);
  }

  /** A lesser sandestin: a small mote orbiting its master, or wandering the rune band. */
  mote(t, m, x, y) {
    const s = m.status;
    const c = this.color(t, s);
    const rite = riteOf(s);
    const halo = 28, off = (halo - LESSER) / 2;
    return div()
      .id(`lesser-${m.key}`)
      .absolute().left(x - LESSER / 2).top(y - LESSER / 2).size(LESSER)
      .cursor_pointer()
      .tooltip(`${NAMED.get(m.key)?.full ?? m.name} · ${m.name} · ${m.kind ?? "sandestin menor"}${m.master ? ` de ${m.master}` : " errante"} · ${rite.name} (${rite.hint})`)
      .on_click(() => (m.address ? reveal(m.address) : m.pane && run("pane.focus", { pane: m.pane })))
      .when(s === "blocked", (el) => el.child(
        div().absolute().left(-off).top(-off).size(halo).rounded_full().bg(c + "55")
          .loop("opacity", { from: 0.15, to: 0.9, period: 900 })))
      .when(s === "working", (el) => el.child(
        svg(`${DIR}/node-ring.svg`).absolute().left(-off).top(-off).size(halo).text_color(c).spin(1800)))
      .child(div().absolute().left(0).top(0).size(LESSER).rounded_full()
        .bg("#140c10").border(1.2).border_color(c)
        .flex().items_center().justify_center()
        .when(s === "idle", (el) => el.opacity(0.65))
        .child(m.kind === "encantamento" ? div().size(6).rounded(1).bg(c) : div().size(6).rounded_full().bg(c)));
  }

  heart(t, S, top) {
    const rite = top ? riteOf(top) : null;
    const c = top ? this.color(t, top) : t.dim;
    const z = 56;
    const sigil = svg(`${DIR}/sigil-${top ?? "idle"}.svg`).size(z).text_color(c);
    return div().id("ritual-heart").absolute().left(S / 2 - z / 2).top(S / 2 - z / 2).size(z)
      .child(div().absolute().left(-14).top(-14).size(z + 28).rounded_full().bg(c + "22")
        .loop("opacity", { from: 0.4, to: 1, period: top === "blocked" ? 900 : 2600 }))
      .child(top === "blocked" || top === "working"
        ? sigil.loop("opacity", { from: 0.55, to: 1, period: top === "blocked" ? 900 : 1800 })
        : sigil)
      .when(Boolean(rite), (el) => el.tooltip(`${rite.name}: ${rite.hint}`));
  }

  render(cx) {
    const t = theme();
    const list = agents();
    const { width, height } = this.size;
    const S = Math.max(200, Math.min(width - 28, height - 250, 460));
    const R = S * 0.33;
    const counts = Object.fromEntries(RITES.map((r) => [r.status, 0]));
    for (const a of list) counts[riteOf(a.status).status]++;
    const top = RITES.find((r) => counts[r.status] > 0)?.status ?? null;
    const placed = list.map((a, i) => {
      const ang = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(1, list.length);
      return { a, x: S / 2 + R * Math.cos(ang), y: S / 2 + R * Math.sin(ang) };
    });
    const sendings = list.filter((a) => a.status === "blocked");

    // Christen everyone in sight before drawing: each gets a proper name and the epithet of its work.
    const all = terminals();
    const kin = (k) => ({ key: k.address, kind: "sandestin menor", texts: [k.name, k.template, (k.argv ?? []).join(" ")] });
    NAMED = christen([
      ...list.map((a) => ({ key: a.address, kind: "agent", texts: [taskOf(a), a.tab_name] })),
      ...list.flatMap((a) => descendants(all, a.address).map(kin)),
      ...list.flatMap((a) => this.innerOf(a).map((m) => ({ key: m.key, kind: m.kind, texts: m.texts }))),
      ...all.filter((k) => k.state === "live" && k.status && !k.parent && !list.some((a) => a.address === k.address)).map(kin),
    ]);

    // Lesser sandestins: sub-agents orbiting their master, and live terminals
    // that report a status but sit in no pane and have no master (wanderers).
    const listed = new Set(list.map((a) => a.address));
    const orbit = Math.min(46, S * 0.115);
    const motes = [], threads = [], lesser = [];
    for (const { a, x, y } of placed) {
      const kids = [
        ...descendants(all, a.address).map((k) => ({ key: k.address, address: k.address, kind: "sandestin menor",
          name: k.name || k.template || k.program?.name || k.address, status: lesserStatus(k.status), master: properOf(a) })),
        ...this.innerOf(a),
      ];
      const base = Math.atan2(y - S / 2, x - S / 2);
      kids.forEach((m, j) => {
        const spread = kids.length === 1 ? 0 : ((j / (kids.length - 1)) - 0.5) * Math.min(Math.PI * 1.2, kids.length * 0.6);
        const ang = base + spread;
        const mx = x + orbit * Math.cos(ang), my = y + orbit * Math.sin(ang);
        threads.push(this.thread(t, S, x, y, mx, my, m.status));
        motes.push(this.mote(t, m, mx, my));
        lesser.push(m);
      });
    }
    const nested = new Set(lesser.map((m) => m.address).filter(Boolean));
    const wanderers = all.filter((k) => k.state === "live" && k.status && !k.parent && !listed.has(k.address) && !nested.has(k.address));
    wanderers.forEach((k, j) => {
      const ang = -Math.PI / 2 + Math.PI / Math.max(1, wanderers.length) + (j * 2 * Math.PI) / Math.max(1, wanderers.length);
      const rr = S * 0.445;
      const m = { key: k.address, address: k.address, name: k.name || k.template || k.program?.name || k.agent || k.address,
                  status: lesserStatus(k.status), master: null };
      motes.push(this.mote(t, m, S / 2 + rr * Math.cos(ang), S / 2 + rr * Math.sin(ang)));
      lesser.push(m);
    });

    const circle = div().relative().size(S).flex_none()
      .child(svg(`${DIR}/circle-outer.svg`).absolute().left(0).top(0).size(S).text_color(t.accent + "88").spin(120000))
      .child(svg(`${DIR}/circle-inner.svg`).absolute().left(S * 0.12).top(S * 0.12).size(S * 0.76)
        .text_color((top === "blocked" ? t.blocked : t.accent) + "66").spin(70000))
      .children(placed.map(({ a, x, y }) => this.leyLine(t, S, x, y, a.status)))
      .children(threads)
      .child(this.heart(t, S, top))
      .children(placed.map(({ a, x, y }) => this.node(t, a, x, y)))
      .children(placed.map(({ a, x, y }) => this.label(t, a, x, y, S)))
      .children(motes);

    const boundList = v_flex().w_full().gap(2).px(14)
      .child(div().pb(2).font_family(TITLE_FONT).font_weight(700).text_size(10.5).text_color(t.accent).child("PRESOS AO CÍRCULO"))
      .children(placed.map(({ a }) => {
        const named = NAMED.get(a.address);
        return v_flex().id(`bound-row-${a.address}`).px(6).py(3).rounded(2).cursor_pointer().hover((st) => st.bg(t.hover))
          .when(Boolean(a.focused), (el) => el.border_l(2).border_color(t.accent))
          .on_click(() => run("pane.focus", { pane: a.pane }))
          .child(h_flex().gap(8).items_center()
            .child(div().size(7).flex_none().rounded_full().bg(this.color(t, a.status)))
            .child(div().flex_1().min_w(0).truncate().font_family(BODY_FONT).font_weight(600).text_size(13)
              .text_color(a.focused ? t.accent : t.foreground).child(named?.full ?? programOf(a))))
          .when(Boolean(taskOf(a)), (el) => el.child(div().pl(15).truncate().font_family(BODY_FONT).italic().text_size(12)
            .text_color(t.muted).child(`${taskOf(a)} · ${a.space_name}`)));
      }));

    const lesserList = v_flex().w_full().gap(2).px(14)
      .child(div().pb(2).font_family(TITLE_FONT).font_weight(700).text_size(10.5).text_color(t.accent).child("SANDESTINS MENORES"))
      .children(lesser.map((m) => v_flex().id(`lesser-row-${m.key}`).px(6).py(3).rounded(2)
        .cursor_pointer().hover((s) => s.bg(t.hover))
        .on_click(() => (m.address ? reveal(m.address) : m.pane && run("pane.focus", { pane: m.pane })))
        .child(h_flex().gap(8).items_center()
          .child(div().size(7).flex_none().when(m.kind === "encantamento", (e) => e.rounded(1)).when(m.kind !== "encantamento", (e) => e.rounded_full()).bg(this.color(t, m.status)))
          .child(div().flex_1().min_w(0).truncate().font_family(BODY_FONT).font_weight(600).text_size(13).text_color(t.foreground).child(NAMED.get(m.key)?.full ?? m.name)))
        .child(div().pl(15).truncate().font_family(BODY_FONT).italic().text_size(12).text_color(t.muted)
          .child(`${m.name} · ${m.master ? `${m.kind === "sandestin menor" ? "serve a" : `${m.kind} de`} ${m.master}` : "errante"}`))));

    const legend = v_flex().w_full().gap(3).px(14)
      .children(RITES.map((r) => h_flex().gap(8).items_center().h(22)
        .text_color(counts[r.status] ? t.foreground : t.dim)
        .child(svg(`${DIR}/sigil-${r.status}.svg`).size(14).flex_none().text_color(this.color(t, r.status)))
        .child(div().font_family(TITLE_FONT).font_weight(700).text_size(11).child(r.name.toUpperCase()))
        .child(div().flex_1().truncate().font_family(BODY_FONT).italic().text_size(12.5).text_color(t.dim).child(r.hint))
        .child(div().font_family(TITLE_FONT).text_size(12).text_color(counts[r.status] ? this.color(t, r.status) : t.dim)
          .child(String(counts[r.status])))));

    const calls = v_flex().w_full().gap(4).px(14)
      .children(sendings.map((a) => h_flex().id(`call-${a.address}`).gap(8).px(8).h(26).items_center().rounded(2)
        .bg(t.blocked + "22").border(1).border_color(t.blocked + "88").cursor_pointer()
        .hover((s) => s.bg(t.blocked + "3a"))
        .on_click(() => run("pane.focus", { pane: a.pane }))
        .child(svg(`${DIR}/sigil-blocked.svg`).size(13).text_color(t.blocked))
        .child(div().flex_1().truncate().font_family(BODY_FONT).text_size(13).text_color(t.foreground)
          .child(`${nameOf(a)} ergue um Clamor · ${a.space_name}`))
        .child(div().font_family(TITLE_FONT).font_weight(700).text_size(10).text_color(t.blocked).child("RESPONDER"))));

    return v_flex().id("ritual").size_full().bg(t.chrome).overflow_y_scrollbar()
      .on_size_change((size, cx) => { this.size = size; cx.notify(); })
      .child(v_flex().px(14).pt(12).pb(4).gap(1)
        .child(div().font_family(TITLE_FONT).font_weight(700).text_size(13).text_color(t.accent).child("CÍRCULO DE INVOCAÇÃO"))
        .child(div().font_family(BODY_FONT).italic().text_size(13).text_color(t.muted)
          .child((list.length === 0 ? "Nenhum sandestin preso ao círculo"
            : `${list.length} ${list.length === 1 ? "sandestin preso ao círculo" : "sandestins presos ao círculo"}`)
            + (lesser.length ? ` · ${lesser.length} ${lesser.length === 1 ? "menor" : "menores"} em segundo plano` : ""))))
      .child(h_flex().w_full().justify_center().py(10).child(circle))
      .when(list.length === 0, (el) => el.child(div().px(14).pb(8).text_center().font_family(BODY_FONT).italic()
        .text_size(13).text_color(t.dim).child("Use \"Invocar sandestin\" no menu + para prender um ao círculo.")))
      .when(sendings.length > 0, (el) => el.child(calls).child(div().h(8)))
      .when(placed.length > 0, (el) => el.child(boundList).child(div().h(6)))
      .when(lesser.length > 0, (el) => el.child(lesserList).child(div().h(6)))
      .child(div().mx(14).my(6).h(1).bg(t.accent + "44"))
      .child(legend)
      .child(div().h(12));
  }
}
