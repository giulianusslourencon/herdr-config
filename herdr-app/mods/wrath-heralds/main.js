// Arautos das Torres: o estado das petições (PRs) e dos deploys de cada domínio, via GitHub.
// Lê arautos.py (uma consulta GraphQL pelo gh); mostra o último resultado guardado na hora
// e convoca os arautos de novo a cada 3 minutos ou pelo botão CONVOCAR.
// Torre principal = ambiente prod; torre de prova = rc. Clique abre no navegador.
// Enquanto houver encantamentos em curso (workflows do Actions rodando ou na fila), vigia só
// esses domínios a cada 20 s. Clicar num encantamento, ou numa torre ainda em curso, abre uma
// aba de vigília (vigia.sh: gh run watch) que toca o som de concluído ou de falha e se fecha.

import { View, div, svg } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { exec, appHome, home, readTextFile, theme, run } from "herdr";
import { plaque, rivets, hatch } from "./kit.js";

const TITLE = "Cinzel";
const BODY = "EB Garamond";
const MONO = "JetBrains Mono";
const TOWERS = { prod: "TORRE PRINCIPAL", main: "TORRE PRINCIPAL", rc: "TORRE DE PROVA" };
const EVERY = 3 * 60 * 1000;
const QUICK = 20 * 1000;
const LIVE = ["PENDING", "IN_PROGRESS", "QUEUED", "WAITING"];

function when(iso) {
  if (!iso) return "";
  const d = new Date(iso), p = (n) => String(n).padStart(2, "0");
  return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function ago(sec) {
  const m = Math.round((Date.now() / 1000 - sec) / 60);
  return m < 1 ? "agora" : m < 60 ? `há ${m} min` : `há ${Math.round(m / 60)} h`;
}

function since(iso) {
  if (!iso) return "";
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  return s < 3600 ? `${Math.floor(s / 60)}m${String(s % 60).padStart(2, "0")}s` : `${Math.floor(s / 3600)}h${String(Math.floor(s / 60) % 60).padStart(2, "0")}`;
}

const open = (url) => url && exec("xdg-open", [url]).catch(() => null);

// A tower is live while its last deploy has not settled (and is recent: stale PENDINGs exist).
const liveTower = (x) => LIVE.includes(x.state) && Date.now() - new Date(x.at).getTime() < 2 * 3600 * 1000;
const runOf = (x) => Number((x.log || "").match(/\/runs\/(\d+)/)?.[1]) || null;

function watch(repo, id) {
  run("tab.new", { name: `Vigília · ${repo.name}`, argv: ["sh", `${appHome()}/mods/wrath-heralds/vigia.sh`, String(id), repo.full] });
}

export default class Heralds extends View {
  init(_props, cx) {
    this.data = null; this.loading = false; this.onlyMine = false; this.error = null;
    cx.spawn(async (cx) => {
      const cached = await readTextFile(`${home()}/.cache/tomo-rubro/arautos.json`).catch(() => null);
      try { if (cached && !this.data) { this.data = JSON.parse(cached); cx.notify(); } } catch {}
    });
    this.summon(cx);
    cx.timer.every(EVERY, (cx) => this.summon(cx));
    cx.timer.every(QUICK, (cx) => {
      const busy = this.busy();
      if (busy.length) this.summon(cx, busy);
    });
  }

  // Domains with a workflow running or queued, or a deploy that has not settled.
  busy() {
    return (this.data?.repos ?? []).filter((r) => !r.error
      && ((r.runs ?? []).length || Object.values(r.envs ?? {}).some(liveTower))).map((r) => r.name);
  }

  summon(cx, only) {
    if (this.loading) return;
    this.loading = true; this.quick = Boolean(only);
    if (!only) cx.notify();
    const args = [`${appHome()}/mods/wrath-heralds/arautos.py`].concat(only ? ["--repos", only.join(",")] : []);
    cx.spawn(async (cx) => {
      const r = await exec("python3", args, { timeout: 90000 }).catch((e) => ({ stdout: "", stderr: String(e) }));
      try {
        const d = JSON.parse(r.stdout);
        if (d.error) this.error = d.error; else { this.data = d; this.error = null; }
      } catch { this.error = (r.stderr || "os arautos não voltaram").slice(0, 300); }
      this.loading = false; this.quick = false;
      cx.notify();
    });
  }

  spell(t, repo, w) {
    const c = w.failed ? t.blocked : t.working;
    const j = w.job;
    const where = j ? `${j.name}${j.step ? ` · passo ${j.n}/${j.of} «${j.step}»` : j.status === "in_progress" ? "" : " · na fila"}`
      : { queued: "na fila", waiting: "aguarda aprovação", pending: "na fila" }[w.status] ?? `em curso · jobs ${w.jobs_done}/${w.jobs}`;
    return h_flex().id(`sp-${w.id}`).min_h(24).py(2).px(6).gap(6).items_center().rounded(2).cursor_pointer()
      .bg(c + "14").border_l(2).border_color(c).hover((s) => s.bg(t.hover))
      .tooltip(`${w.name} · ${w.branch} · ${w.event}\n${w.title ?? ""}\njobs: ${w.jobs_done}/${w.jobs}${w.failed ? " · um job já falhou" : ""}\nclique: vigiar no Herdr`)
      .on_click(() => watch(repo, w.id))
      .child(div().w(12).flex_none().font_family(MONO).text_size(11).text_color(c).child(w.failed ? "✗" : "◌"))
      .child(div().flex_none().font_family(BODY).font_weight(700).text_size(12.5).text_color(t.foreground).child(w.name ?? "workflow"))
      .child(div().flex_none().px(4).rounded(2).border(1).border_color(t.border).font_family(MONO).text_size(9.5).text_color(t.muted).child(w.branch ?? "?"))
      .child(div().flex_1().min_w(0).truncate().font_family(BODY).italic().text_size(12).text_color(t.muted).child(where))
      .child(div().flex_none().font_family(MONO).text_size(10).text_color(c).child(since(w.started)))
      .child(div().id(`sp-web-${w.id}`).flex_none().px(3).font_family(MONO).text_size(11).text_color(t.dim)
        .hover((s) => s.text_color(t.accent)).tooltip("abrir no navegador")
        .on_click((_e, cx) => { cx.stop_propagation(); open(j?.url || w.url); }).child("↗"));
  }

  tone(t, state) {
    const s = (state || "").toUpperCase();
    if (["SUCCESS", "APPROVED"].includes(s)) return t.done;
    if (["FAILURE", "ERROR", "CHANGES_REQUESTED"].includes(s)) return t.blocked;
    if (["PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED", "WAITING"].includes(s)) return t.working;
    return t.dim;
  }

  tower(t, repo, env, x) {
    const c = this.tone(t, x.state);
    const glyph = x.state === "SUCCESS" ? "✓" : ["FAILURE", "ERROR"].includes(x.state) ? "✗" : x.state === "INACTIVE" ? "·" : "◌";
    return h_flex().id(`tw-${repo.name}-${env}`).relative().h(24).px(7).gap(5).items_center().rounded(2).overflow_hidden()
      .border(1).border_color(c + "99").children(plaque(t)).cursor_pointer()
      .tooltip(`${env} · ${x.state} · ${when(x.at)}${x.oid ? ` · ${x.oid}` : ""}${x.headline ? ` · ${x.headline}` : ""}${x.behind ? ` · atrás da ponta de ${x.ref}` : ""}`)
      .on_click(() => {
        const id = liveTower(x) ? (runOf(x) || (repo.runs ?? []).find((w) => w.branch === x.ref)?.id) : null;
        if (id) watch(repo, id); else open(x.log || `${repo.url}/deployments`);
      })
      .child(div().font_family(MONO).text_size(11).text_color(c).child(glyph))
      .child(div().font_family(TITLE).font_weight(700).text_size(9).text_color(t.accent).child(TOWERS[env] ?? env.toUpperCase()))
      .child(div().font_family(MONO).text_size(9.5).text_color(t.muted).child(when(x.at)))
      .when(Boolean(x.behind), (el) => el.child(div().font_family(BODY).italic().text_size(11).text_color(t.working).child("atrás")));
  }

  petition(t, p) {
    const checks = p.checks ? (p.checks === "SUCCESS" ? "✓" : ["FAILURE", "ERROR"].includes(p.checks) ? "✗" : "◌") : "–";
    const review = { APPROVED: "abençoada", CHANGES_REQUESTED: "contestada", REVIEW_REQUIRED: "aguarda revisão" }[p.review] ?? null;
    return h_flex().id(`pr-${p.url}`).min_h(24).py(2).px(6).gap(6).items_center().rounded(2).cursor_pointer()
      .border_l(2).border_color(p.mine ? t.accent : t.accent + "00").hover((s) => s.bg(t.hover))
      .tooltip(`#${p.number} ${p.title}\n${p.author} · ${p.head} → ${p.base}${p.draft ? " · rascunho" : ""}${p.mergeable === "CONFLICTING" ? " · em conflito" : ""}`)
      .on_click(() => open(p.url))
      .child(div().w(12).flex_none().font_family(MONO).text_size(11).text_color(this.tone(t, p.checks)).child(checks))
      .child(div().flex_none().font_family(MONO).text_size(10.5).text_color(p.mine ? t.accent : t.dim).child(`#${p.number}`))
      .child(div().flex_1().min_w(0).truncate().font_family(BODY).text_size(13)
        .text_color(p.draft ? t.dim : t.foreground).child(p.title))
      .when(p.mergeable === "CONFLICTING", (el) => el.child(div().flex_none().font_family(BODY).italic().text_size(11).text_color(t.blocked).child("conflito")))
      .when(Boolean(review), (el) => el.child(div().flex_none().font_family(BODY).italic().text_size(11).text_color(this.tone(t, p.review)).child(review)))
      .child(div().flex_none().px(4).rounded(2).border(1).border_color(t.border).font_family(MONO).text_size(9.5).text_color(t.muted).child(p.base));
  }

  card(t, repo) {
    if (repo.error) return div().px(12).py(6).font_family(BODY).italic().text_size(12.5).text_color(t.blocked).child(`${repo.name}: ${repo.error}`);
    const humans = repo.prs.filter((p) => !p.bot && (!this.onlyMine || p.mine));
    const bots = repo.prs.filter((p) => p.bot).length;
    const envs = Object.entries(repo.envs).sort(([a], [b]) => (a === "prod" ? -1 : b === "prod" ? 1 : a < b ? -1 : 1));
    return v_flex().id(`dom-${repo.name}`).px(10).py(8).gap(5).border_b(1).border_color(t.border)
      .child(h_flex().gap(8).items_center()
        .child(div().flex_1().min_w(0).truncate().id(`dn-${repo.name}`).font_family(BODY).font_weight(700).text_size(14.5)
          .text_color(t.foreground).cursor_pointer().hover((s) => s.text_color(t.accent)).on_click(() => open(repo.url)).child(repo.name))
        .when(repo.rc_ahead > 0, (el) => el.child(div().id(`ahead-${repo.name}`).flex_none().px(6).h(18).flex().items_center().rounded(2)
          .border(1).border_color(t.working + "aa").font_family(BODY).italic().text_size(11.5).text_color(t.working).cursor_pointer()
          .tooltip(`${repo.rc_ahead} commits em rc que main ainda não tem: aguardam a torre principal`)
          .on_click(() => open(`${repo.url}/compare/main...rc`))
          .child(`${repo.rc_ahead} aguardam a torre principal`))))
      .children((repo.runs ?? []).map((w) => this.spell(t, repo, w)))
      .when(envs.length > 0, (el) => el.child(h_flex().flex_wrap().gap(5).children(envs.map(([env, x]) => this.tower(t, repo, env, x)))))
      .when(!envs.length, (el) => el.child(div().font_family(BODY).italic().text_size(12).text_color(t.dim).child("nenhum deploy registrado")))
      .children(humans.map((p) => this.petition(t, p)))
      .when(bots > 0 && !this.onlyMine, (el) => el.child(div().id(`bots-${repo.name}`).px(6).font_family(BODY).italic().text_size(12)
        .text_color(t.dim).cursor_pointer().hover((s) => s.text_color(t.accent))
        .on_click(() => open(`${repo.url}/pulls?q=is%3Aopen+is%3Apr+author%3Aapp%2Fdependabot`))
        .child(`${bots} ${bots === 1 ? "petição" : "petições"} de autômatos (dependabot)`)));
  }

  render(cx) {
    const t = theme();
    const d = this.data;
    const repos = (d?.repos ?? []).slice().sort((a, b) => {
      const score = (r) => (r.error ? 0 : (Object.values(r.envs).some((x) => ["FAILURE", "ERROR"].includes(x.state)) ? 4 : 0)
        + (r.prs.some((p) => p.mine && ["FAILURE", "ERROR"].includes(p.checks)) ? 4 : 0)
        + ((r.runs ?? []).length ? 3 : 0) + (r.prs.some((p) => p.mine) ? 2 : 0) + (r.rc_ahead > 0 ? 1 : 0));
      return score(b) - score(a) || (a.name < b.name ? -1 : 1);
    });
    const mine = repos.reduce((n, r) => n + (r.prs ?? []).filter((p) => p.mine).length, 0);
    const spells = repos.reduce((n, r) => n + (r.runs ?? []).length, 0);
    const fails = repos.reduce((n, r) => n + Object.values(r.envs ?? {}).filter((x) => ["FAILURE", "ERROR"].includes(x.state)).length, 0);
    const btn = (id, label, on, click) => div().id(id).relative().px(8).h(22).flex().items_center().rounded(2).overflow_hidden()
      .border(1).border_color(on ? t.accent : t.border).children(plaque(t))
      .font_family(TITLE).font_weight(700).text_size(9.5).text_color(on ? t.accent : t.muted).cursor_pointer()
      .hover((s) => s.border_color(t.accent)).on_click(click).child(label);
    return v_flex().id("heralds").size_full().bg(t.chrome).text_color(t.foreground)
      .child(h_flex().relative().flex_none().h(46).px(12).gap(8).items_center().overflow_hidden()
        .border_b(1).border_color(t.accent + "55").children(plaque(t)).children(rivets(t, 4, 4))
        .child(v_flex().flex_1().min_w(0)
          .child(div().font_family(TITLE).font_weight(700).text_size(12).text_color(t.accent).child("ARAUTOS DAS TORRES"))
          .child(div().truncate().font_family(BODY).italic().text_size(12).text_color(t.muted)
            .child(this.loading && !this.quick ? "os arautos cavalgam…" : d ? `${ago(d.at)}${spells ? ` · ${spells} ${spells === 1 ? "encantamento" : "encantamentos"} em curso · vigília de 20 s` : ""} · ${mine} ${mine === 1 ? "petição vossa" : "petições vossas"}${fails ? ` · ${fails} torre${fails > 1 ? "s" : ""} em ruína` : ""}` : "aguardando os arautos…")))
        .child(btn("hr-mine", "SÓ AS VOSSAS", this.onlyMine, (_e, cx) => { this.onlyMine = !this.onlyMine; cx.notify(); }))
        .child(btn("hr-summon", "CONVOCAR", false, (_e, cx) => this.summon(cx))))
      .child(div().relative().flex_none().h(4).overflow_hidden().child(hatch(t.accent + "30", 1, 3)))
      .when(Boolean(this.error), (el) => el.child(div().px(12).py(6).bg(t.blocked + "22").font_family(BODY).text_size(12.5).text_color(t.blocked)
        .child(`Os arautos não voltaram: ${this.error}`)))
      .child(v_flex().id("heralds-list").flex_1().min_h(0).overflow_y_scroll().children(repos.map((r) => this.card(t, r))));
  }
}
