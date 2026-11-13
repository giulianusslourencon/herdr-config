// Crônica do Mestre: o cogitador do Tomo anota cada feito dos sandestins.
// Lê os mesmos dados do Círculo (agents(), sub-agentes do Herdr e a ponte de hooks
// do Claude em ~/.claude/grimorio/familiares) e registra as transições:
// invocações, dispensas, mudanças de status, subagentes e encantamentos.
// Os nomes saem de names.js (cópia do wrath-ritual), os mesmos do Círculo.
// O registro fica no localStorage deste mod, até 300 linhas.

import { View, div, svg, PathBuilder, Background } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { agents, theme, run, terminals, home, readTextFile, watchFolder, shared, exec, hc, notify } from "herdr";
import { christen, cleanTask } from "./names.js";
import { plaque, rivets, hatch } from "./kit.js";

const TITLE_FONT = "Cinzel";
const BODY_FONT = "EB Garamond";
const MONO = "JetBrains Mono";
const MAX = 300;
const GRIMORIO = () => `${home()}/.claude/grimorio`;
const FAMILIARS = () => `${GRIMORIO()}/familiares`;
const LEDGER = () => `${GRIMORIO()}/tesouro.json`; // written by the Claude statusline
const STALE_MS = 2 * 60 * 60 * 1000;

const programOf = (a) => (a.program?.agent && a.program.name) || a.app || "sandestin";
const taskOf = (a) => cleanTask(a.title) || (/^\d+$/.test(a.tab_name ?? "") ? "" : a.tab_name) || "";

function clock(ms) {
  const d = new Date(ms);
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map((n) => String(n).padStart(2, "0")).join(":");
}

function terces(v) {
  return (v ?? 0).toFixed(2).replace(".", ",");
}

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Points of a gauge arc, fraction `from`..`to` of the upper half circle, left to right, in % of a w×h box. */
function arc(w, h, cx, cy, r, from, to, steps = 40) {
  const pts = [];
  for (let i = 0; i <= steps; i++) {
    const ang = Math.PI + (from + ((to - from) * i) / steps) * Math.PI;
    pts.push([`${((cx + r * Math.cos(ang)) / w) * 100}%`, `${((cy + r * Math.sin(ang)) / h) * 100}%`]);
  }
  return pts;
}

function stroke(width, pts) {
  let p = PathBuilder.stroke(width).move_to(pts[0][0], pts[0][1]);
  for (const [x, y] of pts.slice(1)) p = p.line_to(x, y);
  return p.build();
}

function load() {
  try { return JSON.parse(localStorage.getItem("diario") ?? "[]"); } catch { return []; }
}

export default class Chronicle extends View {
  init(_props, cx) {
    this.entries = load();
    this.status = null; // address -> last seen status (null until the first census)
    this.inner = {};
    this.seenInner = null; // key -> { name, master } of subagents/shells last seen
    this.book = null; // the ledger: terces per session per day, and the motive force
    cx.spawn(async (cx) => {
      await this.reload();
      cx.notify();
      for (;;) {
        try { await watchFolder(GRIMORIO()); } catch { return; }
        await this.reload();
        cx.notify();
      }
    });
  }

  async reload() {
    const next = {};
    for (const a of agents()) {
      if (a.address.includes("/")) continue;
      const text = await readTextFile(`${FAMILIARS()}/${a.address}.json`).catch(() => null);
      if (!text) continue;
      try {
        const rec = JSON.parse(text);
        if (Date.now() - (rec.updated ?? 0) * 1000 < STALE_MS) next[a.address] = rec;
      } catch {}
    }
    this.inner = next;
    const book = await readTextFile(LEDGER()).catch(() => null);
    try { this.book = book ? JSON.parse(book) : null; } catch {}
  }

  /** O Fator de Lucro: quanto do dízimo diário ainda resta, de 0 a 100, num mostrador de bronze. */
  /** O Espírito da Máquina: o consumo do computador, lido pela barra de status (shared "espirito"). */
  machine(t, named, list) {
    const e = shared("espirito");
    const head = () => div().pt(2).font_family(TITLE_FONT).font_weight(700).text_size(9.5).text_color(t.dim);
    if (!e) return v_flex().flex_none().px(12).py(8).border_b(1).border_color(t.accent + "44")
      .child(head().child("ESPÍRITO DA MÁQUINA"))
      .child(div().font_family(BODY_FONT).italic().text_size(12.5).text_color(t.dim).child("o Espírito da Máquina ainda não respondeu…"));
    const GB = (b) => (b / 1e9).toFixed(1).replace(".", ",");
    const MB = (b) => (b >= 1e9 ? `${GB(b)} GB` : `${Math.round(b / 1e6)} MB`);
    const toneOf = (pct) => (pct < 70 ? t.accent : pct < 90 ? t.working : t.blocked);
    const bar = (label, pct, text) => h_flex().gap(6).items_center()
      .child(div().w(58).font_family(BODY_FONT).text_size(12).text_color(t.muted).child(label))
      .child(div().relative().flex_1().h(5).rounded(1).bg("#00000088").overflow_hidden()
        .child(div().absolute().top(0).left(0).h_full().w(`${Math.max(0, Math.min(100, pct ?? 0))}%`).bg(toneOf(pct ?? 0))))
      .child(div().w(92).text_right().font_family(MONO).text_size(10).text_color(t.muted).child(text));
    const memPct = (100 * e.mem.used) / e.mem.total;
    const diskPct = (100 * e.disk.used) / e.disk.total;
    const heat = e.temp == null ? null : Math.max(0, Math.min(100, ((e.temp - 30) / 75) * 100));
    // Every terminal the Spirit measured, not only agents: a plain shell can be the glutton too.
    const live = new Map(terminals().map((k) => [k.address, k]));
    const nameOf = (addr) => named.get(addr)?.full ?? live.get(addr)?.name ?? addr;
    const isAgent = new Set(list.map((a) => a.address));
    const button = (id, label, tip, color, act) => div().id(id).flex_none().px(5).h(15).flex().items_center().rounded(2)
      .border(1).border_color(t.border).font_family(TITLE_FONT).font_weight(700).text_size(8.5).text_color(t.dim)
      .cursor_pointer().hover((st) => st.border_color(color).text_color(color)).tooltip(tip)
      .on_click((_e, cx) => act(cx)).child(label);
    const rows = Object.entries(e.terminals ?? {})
      .filter(([addr, m]) => live.has(addr) && (isAgent.has(addr) || m.rss > 50e6 || m.spells?.length))
      .sort((x, y) => y[1].rss - x[1].rss)
      .flatMap(([addr, m]) => {
        const busy = this.containing?.has(addr);
        const top = h_flex().gap(6).items_center().h(17)
          .child(div().flex_1().min_w(0).truncate().font_family(BODY_FONT).text_size(12.5).text_color(t.foreground)
            .child(nameOf(addr)))
          .child(div().flex_none().font_family(MONO).text_size(10.5).text_color(m.rss > 2e9 ? t.blocked : t.accent)
            .child(`${m.cpu == null ? "…" : `${m.cpu.toFixed(1).replace(".", ",")}%`} · ${MB(m.rss)}`))
          .when(isAgent.has(addr), (el) => el.child(button(`int-${addr}`, "ESC", "Interromper o sandestin (como apertar Esc nele)", t.working,
            (cx) => this.interrupt(cx, addr, nameOf(addr)))))
          .when(m.spells?.length > 0, (el) => el.child(button(`con-${addr}`, busy ? "…" : "CONTER", "Matar todos os comandos em curso deste sandestin (o sandestin continua vivo)", t.blocked,
            (cx) => this.contain(cx, addr, nameOf(addr)))));
        const spells = (m.spells ?? []).slice(0, 4).map((sp) => h_flex().gap(6).items_center().h(15).pl(10)
          .child(div().flex_1().min_w(0).truncate().font_family(MONO).text_size(10).text_color(t.dim).child(`└ ${sp.label}`))
          .child(div().flex_none().font_family(MONO).text_size(10).text_color(sp.rss > 1e9 ? t.blocked : t.muted)
            .child(`${sp.cpu == null ? "…" : `${sp.cpu.toFixed(0)}%`} · ${MB(sp.rss)}`))
          .child(button(`con-${sp.pid}`, "✕", `Matar este comando (pid ${sp.pid}, ${sp.procs} processos)`, t.blocked,
            (cx) => this.contain(cx, String(sp.pid), nameOf(addr)))));
        return [top, ...spells];
      });
    const g = e.guarda;
    const guardText = !g ? "Guardião ausente (~/.claude/grimorio/guardiao.py)"
      : `Guardião ${!g.ativo ? "dispensado" : g.simular ? "em simulação" : "vigilante"}` +
        (g.ultimo ? ` · ${clock(g.ultimo.at * 1000)} ${g.ultimo.text}` : " · nenhum ato");
    return v_flex().flex_none().px(12).pt(8).pb(8).gap(5).border_b(1).border_color(t.accent + "44")
      .child(h_flex().gap(6).items_center()
        .child(svg("mods/wrath-chrome/cog.svg").size(13).text_color(t.accent).spin(e.cpu > 50 ? 4000 : 12000))
        .child(head().pt(0).child("ESPÍRITO DA MÁQUINA"))
        .child(div().flex_1().text_right().font_family(BODY_FONT).italic().text_size(12).text_color(t.dim)
          .child(`carga ${e.load.map((x) => x.toFixed(2).replace(".", ",")).join(" ")} · ${e.cores} núcleos`)))
      .child(bar("Cogitação", e.cpu, e.cpu == null ? "…" : `${Math.round(e.cpu)}%`))
      .child(bar("Memória", memPct, `${GB(e.mem.used)}/${GB(e.mem.total)} GB`))
      .when(e.swap?.used > 0, (el) => el.child(bar("Abismo", (100 * e.swap.used) / e.swap.total, `${GB(e.swap.used)}/${GB(e.swap.total)} GB`)))
      .child(bar("Arquivo", diskPct, `${GB(e.disk.used)}/${GB(e.disk.total)} GB`))
      .when(e.temp != null, (el) => el.child(bar("Calor", heat, `${e.temp.toFixed(0)} °C`)))
      .when(rows.length > 0, (el) => el.child(head().pt(4).child("CONSUMO POR SANDESTIN")).children(rows))
      .child(div().truncate().font_family(BODY_FONT).italic().text_size(11.5)
        .text_color(g?.ultimo && Date.now() / 1000 - g.ultimo.at < 600 ? t.blocked : t.dim)
        .tooltip(guardText).child(guardText));
  }

  /** Contém (mata) os comandos de um sandestin, ou um só pelo pid, pelo guardião. */
  contain(cx, target, who) {
    this.containing ??= new Set();
    if (this.containing.has(target)) return;
    this.containing.add(target);
    cx.notify();
    cx.spawn(async (cx) => {
      const r = await exec("python3", [`${GRIMORIO()}/guardiao.py`, "conter", target], { timeout: 15000 })
        .catch((err) => ({ code: 1, stdout: "", stderr: String(err) }));
      let out = null;
      try { out = JSON.parse(r.stdout); } catch {}
      if (out?.ok) {
        const n = out.contained.length, mb = Math.round(out.contained.reduce((x, c) => x + c.rss, 0) / 1e6);
        notify({ title: `Contido: ${who}`, body: `${n} ${n === 1 ? "comando" : "comandos"} encerrados, ${mb} MB liberados`, level: "success" });
      } else {
        notify({ title: `Não contido: ${who}`, body: out?.error ?? (r.stderr || "o guardião não respondeu").slice(0, 200), level: "error" });
      }
      this.containing.delete(target);
      cx.notify();
    });
  }

  interrupt(cx, addr, who) {
    cx.spawn(async () => {
      const r = await hc(["interrupt", addr, "--json"]).catch((err) => ({ code: 1, stderr: String(err) }));
      notify({ title: r.code === 0 ? `Interrompido: ${who}` : `Falha ao interromper ${who}`,
        body: r.code === 0 ? "Esc enviado ao sandestin" : (r.stderr || "").slice(0, 200), level: r.code === 0 ? "info" : "error" });
    });
  }

  treasury(t, named) {
    // The real limit of a subscription is the motive force (usage limits), not the
    // list-price terces: the factor is what is left of the more spent of the two windows.
    const sessions = Object.values(this.book?.dias?.[today()]?.sessoes ?? {});
    const spent = sessions.reduce((n, x) => n + (x.terces ?? 0), 0);
    const force = this.book?.forca_motriz ?? {};
    const used = Math.max(Number(force.cinco_horas) || 0, Number(force.sete_dias) || 0);
    const frac = Math.min(1, used / 100);
    const factor = Math.max(0, Math.round(100 - used));
    const tone = frac < 0.6 ? t.done : frac < 0.85 ? t.working : t.blocked;
    const W = 150, Hh = 86, cx0 = 75, cy0 = 76, r = 62;
    const layer = (path, color) => div().absolute().top(0).left(0).size_full()
      .child(window.paint_path(path, Background.solid(color)).size_full());
    const at = (rr, ang) => [`${((cx0 + rr * Math.cos(ang)) / W) * 100}%`, `${((cy0 + rr * Math.sin(ang)) / Hh) * 100}%`];
    const ticks = Array.from({ length: 11 }, (_, i) => {
      const ang = Math.PI + (i / 10) * Math.PI;
      return layer(stroke(i % 5 ? 1 : 1.6, [at(r - 11, ang), at(r - (i % 5 ? 15 : 19), ang)]), t.accent + (i % 5 ? "77" : "cc"));
    });
    const needle = [at(0, 0), at(r - 8, Math.PI + frac * Math.PI)];
    const dial = div().relative().flex_none().w(W).h(Hh)
      .child(layer(stroke(7, arc(W, Hh, cx0, cy0, r, 0, 1)), "#00000099"))
      .child(layer(stroke(5, arc(W, Hh, cx0, cy0, r, 0, 1)), t.accent + "33"))
      .when(frac > 0.005, (el) => el.child(layer(stroke(5, arc(W, Hh, cx0, cy0, r, 0, frac)), tone)))
      .children(ticks)
      .child(layer(stroke(2, needle), t.foreground))
      .child(div().absolute().left(cx0 - 6).top(cy0 - 6).size(12).rounded_full().bg(t.accent).border(2).border_color("#140c10"));

    const motive = this.book?.forca_motriz ?? {};
    const bar = (label, pct) => h_flex().gap(6).items_center()
      .child(div().w(18).font_family(MONO).text_size(10).text_color(t.dim).child(label))
      .child(div().relative().flex_1().h(5).rounded(1).bg("#00000088").overflow_hidden()
        .child(div().absolute().top(0).left(0).h_full().w(`${Math.max(0, Math.min(100, pct ?? 0))}%`)
          .bg((pct ?? 0) < 60 ? t.accent : (pct ?? 0) < 85 ? t.working : t.blocked)))
      .child(div().w(30).font_family(MONO).text_size(10).text_color(t.muted).child(pct == null ? "—" : `${Math.round(pct)}%`));

    const byTerminal = new Map();
    for (const x of sessions) {
      const key = x.terminal && named.has(x.terminal) ? x.terminal : `tomo:${x.tomo ?? "?"}`;
      byTerminal.set(key, (byTerminal.get(key) ?? 0) + (x.terces ?? 0));
    }
    const rows = [...byTerminal].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([key, v]) =>
      h_flex().gap(6).items_center().h(17)
        .child(div().flex_1().min_w(0).truncate().font_family(BODY_FONT).text_size(12.5)
          .text_color(key.startsWith("tomo:") ? t.dim : t.foreground)
          .child(key.startsWith("tomo:") ? `dispensado · «${key.slice(5)}»` : named.get(key).full))
        .child(div().flex_none().font_family(MONO).text_size(10.5).text_color(t.accent).child(`${terces(v)} ⚖`)));

    return v_flex().flex_none().px(12).pt(10).pb(8).gap(6).border_b(1).border_color(t.accent + "44")
      .child(h_flex().gap(10).items_center()
        .child(dial)
        .child(v_flex().flex_1().min_w(0).gap(2)
          .child(div().font_family(TITLE_FONT).font_weight(700).text_size(10.5).text_color(t.accent).child("FATOR DE LUCRO"))
          .child(div().font_family(TITLE_FONT).font_weight(700).text_size(30).line_height("32px").text_color(tone).child(String(factor)))
          .child(div().font_family(BODY_FONT).italic().text_size(12.5).text_color(t.muted)
            .child(`resta ${factor}% da força motriz`))
          .child(div().font_family(BODY_FONT).italic().text_size(12).text_color(t.dim)
            .child(`${terces(spent)} terces de tabela hoje, sem cobrança`))))
      .child(div().pt(2).font_family(TITLE_FONT).font_weight(700).text_size(9.5).text_color(t.dim).child("FORÇA MOTRIZ"))
      .child(bar("5h", motive.cinco_horas))
      .child(bar("7d", motive.sete_dias))
      .when(rows.length > 0, (el) => el.child(div().pt(4).font_family(TITLE_FONT).font_weight(700).text_size(9.5).text_color(t.dim)
        .child("TERCES POR SANDESTIN")).children(rows));
  }

  innerOf(a) {
    const rec = this.inner[a.address];
    if (!rec) return [];
    return [
      ...Object.entries(rec.agents ?? {}).map(([id, g]) => ({
        key: `${a.address}-ag-${id}`, kind: "subagente", task: g.description || g.type || "", texts: [g.type, g.description] })),
      ...(rec.shells ?? []).map((sh, i) => ({
        key: `${a.address}-sh-${sh.id ?? i}`, kind: "encantamento", task: sh.description || sh.command || "", texts: [sh.description, sh.command] })),
    ];
  }

  note(kind, text) {
    this.entries.unshift({ at: Date.now(), kind, text });
    if (this.entries.length > MAX) this.entries.length = MAX;
    try { localStorage.setItem("diario", JSON.stringify(this.entries)); } catch {}
  }

  /** Compares this census with the last one and writes what changed. */
  census(list, named, innerByMaster) {
    const full = (key, fallback) => named.get(key)?.full ?? fallback;
    const proper = (key, fallback) => named.get(key)?.proper ?? fallback;
    const now = new Map(list.map((a) => [a.address, a.status]));
    const nowInner = new Map();
    for (const [master, items] of innerByMaster) for (const m of items) nowInner.set(m.key, { ...m, master });

    if (this.status === null) {
      this.note("wake", `Litania da Ignição recitada · o cogitador desperta · ${list.length} ${list.length === 1 ? "sandestin" : "sandestins"} a serviço do Mestre`);
    } else {
      for (const a of list) {
        const was = this.status.get(a.address), is = a.status, who = full(a.address, programOf(a));
        const task = taskOf(a) ? ` «${taskOf(a)}»` : "";
        if (was === undefined) this.note("summon", `${who} foi invocado ao serviço${task} · entoada a Litania da Ignição`);
        else if (was !== is) {
          if (is === "working") this.note("working", `${who} começa a tecer o encantamento${task} · o Espírito da Máquina se agita`);
          else if (is === "blocked") this.note("blocked", `${who} ergue um Clamor Insistente · aguarda a palavra do Mestre`);
          else if (is === "done") this.note("done", `${who} cumpriu sua servidão · o selo está posto`);
          else if (is === "idle" && was !== "done") this.note("idle", `${who} recolhe-se ao repouso sob o sol rubro`);
        }
      }
      for (const [addr] of this.status) if (!now.has(addr)) this.note("dismiss", `Um sandestin (${addr}) foi dispensado do serviço`);
      for (const [key, m] of nowInner) {
        if (this.seenInner?.has(key)) continue;
        const who = full(key, m.kind), lord = proper(m.master, "o Mestre");
        this.note(m.kind === "encantamento" ? "spell" : "summon",
          m.kind === "encantamento" ? `${lord} acendeu o encantamento «${m.task}»` : `${lord} invocou ${who}${m.task ? ` · ${m.task}` : ""}`);
      }
      for (const [key, m] of this.seenInner ?? []) {
        if (nowInner.has(key)) continue;
        this.note(m.kind === "encantamento" ? "spell-end" : "return",
          m.kind === "encantamento" ? `O encantamento «${m.task}» se apagou` : `${m.name ?? "Um subagente"} retornou a ${m.lordName ?? "seu mestre"}`);
      }
    }
    this.status = now;
    this.seenInner = new Map([...nowInner].map(([k, m]) => [k, { ...m, name: full(k, m.kind), lordName: proper(m.master, "seu mestre") }]));
  }

  color(t, kind) {
    return { blocked: t.blocked, working: t.working, done: t.done, summon: t.accent, spell: t.ansi13,
      "spell-end": t.dim, return: t.done, idle: t.idle ?? t.dim, dismiss: t.dim, wake: t.ansi6 }[kind] ?? t.muted;
  }

  render(cx) {
    const t = theme();
    const list = agents();
    const all = terminals();
    const kin = (k) => ({ key: k.address, kind: "sandestin menor", texts: [k.name, k.template, (k.argv ?? []).join(" ")] });
    const desc = (addr) => {
      const kids = all.filter((k) => k.parent === addr && k.state === "live");
      return kids.flatMap((k) => [k, ...desc(k.address)]);
    };
    const innerByMaster = new Map(list.map((a) => [a.address, this.innerOf(a)]));
    const named = christen([
      ...list.map((a) => ({ key: a.address, kind: "agent", texts: [taskOf(a), a.tab_name] })),
      ...list.flatMap((a) => desc(a.address).map(kin)),
      ...[...innerByMaster.values()].flat().map((m) => ({ key: m.key, kind: m.kind, texts: m.texts })),
      ...all.filter((k) => k.state === "live" && k.status && !k.parent && !list.some((a) => a.address === k.address)).map(kin),
    ]);
    this.census(list, named, innerByMaster);

    const line = (e, i) => h_flex().id(`log-${i}`).w_full().gap(8).px(12).py(3).items_start()
      .child(div().flex_none().pt(1).font_family(MONO).text_size(11).text_color(t.dim).child(clock(e.at)))
      .child(div().flex_none().mt(5).size(6).rounded(1).bg(this.color(t, e.kind)))
      .child(div().flex_1().min_w(0).font_family(MONO).text_size(11.5).line_height("16px")
        .text_color(e.kind === "blocked" ? t.blocked : i === 0 ? t.accent : t.accent + "c8")
        .child(`+++ ${e.text} +++`));

    return v_flex().id("chronicle").size_full().bg("#0b0706").text_color(t.accent)
      .child(h_flex().relative().flex_none().h(46).px(14).gap(8).items_center().overflow_hidden()
        .border_b(1).border_color(t.accent + "55")
        .children(plaque(t))
        .children(rivets(t, 4, 4))
        .child(svg("mods/wrath-chronicle/icon.svg").size(16).text_color(t.accent))
        .child(v_flex().flex_1().min_w(0)
          .child(div().font_family(TITLE_FONT).font_weight(700).text_size(12).text_color(t.accent).child("CRÔNICA DO MESTRE"))
          .child(div().truncate().font_family(BODY_FONT).italic().text_size(12).text_color(t.muted)
            .child("os cogitadores anotam cada feito dos sandestins de Vossa Sapiência")))
        .child(div().id("purge").flex_none().px(8).h(22).flex().items_center().rounded(2).border(1).border_color(t.border)
          .font_family(TITLE_FONT).font_weight(700).text_size(9.5).text_color(t.dim).cursor_pointer()
          .hover((s) => s.border_color(t.blocked).text_color(t.blocked))
          .tooltip("Apaga todo o registro deste diário")
          .on_click((_e, cx) => { this.entries = []; try { localStorage.setItem("diario", "[]"); } catch {} cx.notify(); })
          .child("EXPURGAR")))
      .child(div().relative().flex_none().h(5).overflow_hidden().child(hatch(t.accent + "30", 1, 3)))
      .child(this.treasury(t, named))
      .child(this.machine(t, named, list))
      .child(v_flex().id("log").flex_1().min_h(0).py(6).overflow_y_scrollbar()
        .when(this.entries.length === 0, (el) => el.child(div().px(14).py(10).font_family(MONO).text_size(11.5).text_color(t.dim)
          .child("+++ Nenhum feito registrado. O Espírito da Máquina aguarda. +++")))
        .children(this.entries.map(line)));
  }
}
