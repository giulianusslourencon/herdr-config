// Encargos do Mestre: as tarefas do Jira atribuídas a quem está logado no acli, ainda não concluídas
// e numa sprint em andamento (openSprints()).
// Lê `acli jira workitem search --json` (login OAuth do acli: `acli jira auth login --web`);
// nenhum token passa por aqui. Consulta de novo a cada 5 minutos ou pelo botão CONSULTAR.
// Agrupa por status (em curso primeiro); épicos ficam ocultos até o botão ÉPICOS.
// Clique numa tarefa abre no navegador.

import { View, div, svg } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { exec, theme } from "herdr";
import { plaque, rivets, hatch } from "./kit.js";

const TITLE = "Cinzel";
const BODY = "EB Garamond";
const MONO = "JetBrains Mono";
const EVERY = 5 * 60 * 1000;
const JQL = "assignee = currentUser() AND statusCategory != Done AND sprint in openSprints() ORDER BY updated DESC";
const FIELDS = "key,summary,status,priority,issuetype";
const CATEGORY_ORDER = { indeterminate: 0, new: 1 };
const PRIORITY = { Highest: "⇈", High: "↑", Medium: "·", Low: "↓", Lowest: "⇊" };

const open = (url) => url && exec("xdg-open", [url]).catch(() => null);

function ago(ms) {
  const m = Math.round((Date.now() - ms) / 60000);
  return m < 1 ? "agora" : m < 60 ? `há ${m} min` : `há ${Math.round(m / 60)} h`;
}

function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}

export default class Encargos extends View {
  init(_props, cx) {
    this.items = null; this.site = null; this.at = null;
    this.loading = false; this.error = null; this.epics = false;
    this.consult(cx);
    cx.timer.every(EVERY, (cx) => this.consult(cx));
  }

  consult(cx) {
    if (this.loading) return;
    this.loading = true;
    cx.notify();
    cx.spawn(async (cx) => {
      if (!this.site) {
        const s = await exec("acli", ["jira", "auth", "status"], { timeout: 20000 }).catch(() => null);
        const m = (s?.stdout ?? "").match(/Site:\s*(\S+)/);
        if (m) this.site = m[1].startsWith("http") ? m[1] : `https://${m[1]}`;
      }
      const r = await exec("acli", ["jira", "workitem", "search", "--jql", JQL, "--fields", FIELDS, "--limit", "200", "--json"], { timeout: 60000 })
        .catch((e) => ({ stdout: "", stderr: String(e) }));
      try {
        const d = JSON.parse(r.stdout);
        if (!Array.isArray(d)) throw new Error("resposta inesperada");
        this.items = d.map((i) => ({
          key: i.key,
          summary: i.fields?.summary ?? "",
          status: i.fields?.status?.name ?? "?",
          category: i.fields?.status?.statusCategory?.key ?? "new",
          priority: i.fields?.priority?.name ?? "",
          type: i.fields?.issuetype?.name ?? "",
          epic: i.fields?.issuetype?.hierarchyLevel === 1,
          sub: Boolean(i.fields?.issuetype?.subtask),
        }));
        this.error = null; this.at = Date.now();
      } catch {
        const msg = `${r.stderr || ""} ${r.stdout || ""}`.trim();
        this.error = /unauthori[sz]ed|auth login/i.test(msg)
          ? "sessão do acli expirada: rode `acli jira auth login --web`"
          : (msg || "o Jira não respondeu").slice(0, 300);
      }
      this.loading = false;
      cx.notify();
    });
  }

  tone(t, p) {
    return { Highest: t.blocked, High: t.working, Low: t.dim, Lowest: t.dim }[p] ?? t.muted;
  }

  row(t, i) {
    const url = this.site ? `${this.site}/browse/${i.key}` : null;
    return h_flex().id(`jr-${i.key}`).min_h(24).py(2).px(6).gap(6).items_center().rounded(2).cursor_pointer()
      .border_l(2).border_color(i.category === "indeterminate" ? t.accent : t.accent + "00").hover((s) => s.bg(t.hover))
      .tooltip(`${i.key} · ${i.type} · ${i.status} · prioridade ${i.priority}\n${i.summary}`)
      .on_click(() => open(url))
      .child(div().w(12).flex_none().font_family(MONO).text_size(12).text_color(this.tone(t, i.priority)).child(PRIORITY[i.priority] ?? "·"))
      .child(div().flex_none().font_family(MONO).text_size(10.5).text_color(i.epic ? t.ansi13 : t.dim).child(i.key))
      .child(div().flex_1().min_w(0).truncate().font_family(BODY).text_size(13)
        .text_color(i.category === "indeterminate" ? t.foreground : t.muted).when(i.sub, (el) => el.italic()).child(i.summary))
      .when(i.epic || i.type === "Bug", (el) => el.child(div().flex_none().px(4).rounded(2).border(1)
        .border_color(i.type === "Bug" ? t.blocked + "aa" : t.border).font_family(MONO).text_size(9.5)
        .text_color(i.type === "Bug" ? t.blocked : t.muted).child(i.epic ? "épico" : "bug")));
  }

  group(t, status, list) {
    return v_flex().id(`jg-${status}`).px(10).py(8).gap(3).border_b(1).border_color(t.border)
      .child(h_flex().gap(8).items_center()
        .child(div().flex_1().min_w(0).truncate().font_family(BODY).font_weight(700).text_size(14.5).text_color(t.foreground).child(status))
        .child(div().flex_none().font_family(MONO).text_size(10).text_color(t.dim).child(String(list.length))))
      .children(list.map((i) => this.row(t, i)));
  }

  render(cx) {
    const t = theme();
    const all = this.items ?? [];
    const shown = all.filter((i) => this.epics || !i.epic);
    const groups = new Map();
    for (const i of shown) {
      if (!groups.has(i.status)) groups.set(i.status, { category: i.category, list: [] });
      groups.get(i.status).list.push(i);
    }
    const ordered = [...groups.entries()].sort(([, a], [, b]) => (CATEGORY_ORDER[a.category] ?? 2) - (CATEGORY_ORDER[b.category] ?? 2));
    const doing = all.filter((i) => i.category === "indeterminate" && !i.epic).length;
    const epics = all.filter((i) => i.epic).length;
    const btn = (id, label, on, click) => div().id(id).relative().px(8).h(22).flex().items_center().rounded(2).overflow_hidden()
      .border(1).border_color(on ? t.accent : t.border).children(plaque(t))
      .font_family(TITLE).font_weight(700).text_size(9.5).text_color(on ? t.accent : t.muted).cursor_pointer()
      .hover((s) => s.border_color(t.accent)).on_click(click).child(label);
    const sub = this.loading && !this.items ? "consultando o Jira…"
      : this.items ? `${this.at ? ago(this.at) : ""} · ${plural(all.length - epics, "encargo", "encargos")} na sprint · ${doing} em curso${this.loading ? " · consultando…" : ""}`
      : "aguardando o Jira…";
    return v_flex().id("encargos").size_full().bg(t.chrome).text_color(t.foreground)
      .child(h_flex().relative().flex_none().h(46).px(12).gap(8).items_center().overflow_hidden()
        .border_b(1).border_color(t.accent + "55").children(plaque(t)).children(rivets(t, 4, 4))
        .child(svg("mods/wrath-jira/icon.svg").size(16).flex_none().text_color(t.accent))
        .child(v_flex().flex_1().min_w(0)
          .child(div().font_family(TITLE).font_weight(700).text_size(12).text_color(t.accent).child("ENCARGOS DO MESTRE"))
          .child(div().truncate().font_family(BODY).italic().text_size(12).text_color(t.muted).child(sub)))
        .child(btn("jr-epics", `ÉPICOS ${epics}`, this.epics, (_e, cx) => { this.epics = !this.epics; cx.notify(); }))
        .child(btn("jr-consult", "CONSULTAR", false, (_e, cx) => this.consult(cx))))
      .child(div().relative().flex_none().h(4).overflow_hidden().child(hatch(t.accent + "30", 1, 3)))
      .when(Boolean(this.error), (el) => el.child(div().px(12).py(6).bg(t.blocked + "22").font_family(BODY).text_size(12.5).text_color(t.blocked)
        .child(`O Jira não respondeu: ${this.error}`)))
      .when(Boolean(this.items) && !shown.length, (el) => el.child(div().px(12).py(10).font_family(BODY).italic().text_size(13).text_color(t.dim)
        .child("Nenhum encargo em aberto na sprint.")))
      .child(v_flex().id("encargos-list").flex_1().min_h(0).overflow_y_scroll()
        .children(ordered.map(([status, g]) => this.group(t, status, g.list))));
  }
}
