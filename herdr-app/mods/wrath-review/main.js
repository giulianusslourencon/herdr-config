// Julgamento do Mago: revisão das alterações de um repositório, no espírito da do Cursor.
// Abre como aba (tab.new {mod: "wrath-review", props: {root, on, name}}), em geral pelo
// botão JULGAR do Espelho das Alterações.
//
// O que os sandestins mudaram e o Mestre ainda não julgou é o diff da cópia de trabalho
// contra o índice (git diff). Julgar usa o próprio git:
//   aceitar trecho  -> git apply --cached (o trecho vai para o stage)
//   aceitar tomo    -> git add -- <arquivo>
//   rejeitar trecho -> git apply -R (o trecho é desfeito na cópia de trabalho)
//   rejeitar tomo   -> git restore --worktree (rastreado) ou git clean -f (novo)
//   desfazer aceite -> git restore --staged
// Rejeitar apaga trabalho de verdade: pede um segundo clique para confirmar.
// Teclas: a aceitar tomo · r rejeitar tomo · n/→/j próximo · p/←/k anterior.

import { View, div, svg, image } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { props, exec, readTextFile, watchFolder, theme, appHome } from "herdr";
import { plaque, rivets, hatch } from "./kit.js";

const TITLE = "Cinzel";
const BODY = "EB Garamond";
const MONO = "JetBrains Mono";
const READ = ["--no-optional-locks", "-c", "core.fsmonitor=false", "-c", "diff.autoRefreshIndex=false"];
const MAX_LINES = 2500;
const FULL_LINES = 8000; // the whole tomo, with its changes marked in place

const HOW = { edicao: "edição direta", terminal: "por encantamento", disco: "fora das sessões" };
function clock(iso) {
  const d = new Date(iso);
  return isNaN(d) ? "" : `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function stateOf(xy) {
  if (xy === "??") return "pending";
  const staged = xy[0] !== " ", unstaged = xy[1] !== " ";
  return staged && unstaged ? "partial" : staged ? "accepted" : "pending";
}

/** Splits a one-file `git diff` into its header and hunks (each keeps its own text for git apply). */
function parse(text) {
  const lines = text.replace(/\n$/, "").split("\n");
  const first = lines.findIndex((l) => l.startsWith("@@"));
  if (first < 0) return { header: "", hunks: [], binary: /Binary files/.test(text) };
  const header = lines.slice(0, first).join("\n") + "\n";
  const hunks = [];
  for (const line of lines.slice(first)) {
    if (line.startsWith("@@")) hunks.push({ head: line, lines: [] });
    else hunks.at(-1).lines.push(line);
  }
  for (const h of hunks) h.text = [h.head, ...h.lines].join("\n") + "\n";
  return { header, hunks, binary: false };
}

export default class Review extends View {
  init(_props, cx) {
    const p = props() ?? {};
    this.root = p.root; this.on = p.on ?? null; this.name = p.name ?? (p.root ?? "").split("/").pop();
    this.files = []; this.path = null; this.view = null; this.busy = false; this.note = null; this.confirm = null;
    this.full = false; // false: only the changes (hunks) · true: the whole tomo with changes in place
    this.ctx = {}; this.showCtx = true; this.planOpen = false; // path -> purpose read from the session logs
    this.motives = null; this.motivesSig = null; this.scribe = null; this.ctxTab = "tomo"; // side column: "tomo" | "dominio"
    this.handle = cx.focus_handle();
    this.handle.focus();
    this.refresh(cx);
    if (this.root && !this.on) cx.spawn(async (cx) => {
      try { for (;;) { await watchFolder(this.root); if (!this.busy) this.refresh(cx); } } catch {}
    });
  }

  git(args) { return exec("git", [...READ, ...args], { cwd: this.root, on: this.on, timeout: 20000 }); }
  refresh(cx, then) {
    if (!this.root) return;
    if (this.loading) { this.queued = then ?? this.queued ?? true; return; } // runs right after the current one
    this.loading = true;
    cx.spawn(async (cx) => {
      try {
        const branch = await this.git(["rev-parse", "--abbrev-ref", "HEAD"]);
        this.branch = branch.code === 0 ? branch.stdout.trim() : "?";
        const st = await this.git(["status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all"]);
        if (st.code !== 0) throw new Error(st.stderr);
        const stats = {};
        for (const args of [["diff", "--numstat", "-z", "--no-renames"], ["diff", "--cached", "--numstat", "-z", "--no-renames"]]) {
          const r = await this.git(args);
          for (const entry of r.stdout.split("\0")) {
            const [a, d, ...rest] = entry.split("\t");
            if (!rest.length) continue;
            const path = rest.join("\t"), old = stats[path] ?? { add: 0, del: 0 };
            stats[path] = { add: old.add + (Number(a) || 0), del: old.del + (Number(d) || 0) };
          }
        }
        const files = st.stdout.split("\0").filter(Boolean).map((e) => {
          const xy = e.slice(0, 2), path = e.slice(3);
          return { path, xy, state: stateOf(xy), untracked: xy === "??", deleted: xy.includes("D"), ...(stats[path] ?? { add: 0, del: 0 }) };
        });
        // Judgement follows the order the sandestins edited (ordem.py reads their session logs);
        // what no session recorded comes after, by time of change on disk.
        const ord = this.on ? null : await exec("python3", [`${appHome()}/mods/wrath-review/ordem.py`, this.root], { timeout: 20000 }).catch(() => null);
        let order = [];
        try { order = JSON.parse(ord?.stdout || "[]"); } catch {}
        const pos = new Map(order.map((o) => [o.path, o]));
        for (const f of files) {
          const o = pos.get(f.path);
          Object.assign(f, { seq: o?.seq ?? 1e9, when: o?.first ?? null, how: o?.source ?? null, tomo: o?.tomo ?? null, edits: o?.edits ?? 0 });
        }
        files.sort((a, b) => a.seq - b.seq || (a.path < b.path ? -1 : 1));
        this.files = files;
        if (!files.some((f) => f.path === this.path)) this.path = (files.find((f) => f.state !== "accepted") ?? files[0])?.path ?? null;
        await this.load(cx);
        if (this.path) this.purpose(this.path, cx);
        const sig = files.map((f) => f.path).sort().join("\n");
        if (sig !== this.motivesSig) { this.motivesSig = sig; this.motivations(cx, false); }
      } catch (e) { this.note = `Contramágica: ${String(e).slice(0, 300)}`; }
      finally {
        this.loading = false;
        if (then) then(cx);
        const q = this.queued; this.queued = null;
        if (q) this.refresh(cx, typeof q === "function" ? q : undefined);
        cx.notify();
      }
    });
  }

  current() { return this.files.find((f) => f.path === this.path) ?? null; }

  async load() {
    const f = this.current();
    if (!f) { this.view = null; return; }
    if (f.untracked) {
      const text = await readTextFile(`${this.root}/${f.path}`, { on: this.on }).catch(() => null);
      const body = text === null ? ["(tomo ilegível ou binário)"] : text.includes("\0") ? ["(tomo binário)"]
        : text.replace(/\n$/, "").split("\n").slice(0, this.full ? FULL_LINES : MAX_LINES).map((l) => `+${l}`);
      this.view = { path: f.path, header: "", hunks: [{ head: `@@ -0,0 +1,${body.length} @@ tomo novo · ${body.length} ${body.length === 1 ? "linha" : "linhas"}`, lines: body, text: null }], fresh: true };
      return;
    }
    const ctx = this.full ? "-U100000" : "-U3";
    const pending = await this.git(["diff", "--no-color", "--no-ext-diff", ctx, "--", f.path]);
    let parsed = parse(pending.stdout), staged = false;
    if (!parsed.hunks.length && !parsed.binary) {
      const done = await this.git(["diff", "--cached", "--no-color", "--no-ext-diff", ctx, "--", f.path]);
      parsed = parse(done.stdout); staged = true;
    }
    if (this.full) for (const h of parsed.hunks) h.lines = h.lines.slice(0, FULL_LINES);
    this.view = { path: f.path, ...parsed, staged, full: this.full };
  }

  /** Switches between only the changes and the whole tomo (changes marked in place). */
  toggleFull(cx) {
    this.full = !this.full; this.view = null;
    cx.spawn(async (cx) => { await this.load(); cx.notify(); });
    cx.notify();
  }

  select(path, cx) {
    this.path = path; this.confirm = null; this.note = null; this.view = null; this.planOpen = false;
    cx.spawn(async (cx) => { await this.load(); cx.notify(); });
    this.purpose(path, cx);
    cx.notify();
  }

  /** Groups the domain's changes by the order that begot them (motivos.py); with `scribe`, asks Haiku to summarize. */
  motivations(cx, scribe) {
    if (this.on) return;
    const fresh = scribe && this.scribe && this.scribe !== "loading";
    if (scribe) this.scribe = "loading";
    cx.spawn(async (cx) => {
      const r = await exec("python3", [`${appHome()}/mods/wrath-review/motivos.py`, this.root, ...(scribe ? ["--escriba", ...(fresh ? ["--novo"] : [])] : ["--guardado"])],
        { timeout: 240000 }).catch((e) => ({ code: 1, stderr: String(e) }));
      try {
        const d = JSON.parse(r.stdout || "null");
        if (d) { this.motives = d; this.scribe = d.resumo ?? (scribe ? "O Escriba nada escreveu." : null); }
      } catch { if (scribe) this.scribe = `O Escriba não respondeu: ${(r.stderr || "").slice(0, 200)}`; }
      cx.notify();
    });
    cx.notify();
  }

  /** The band under the header: why this domain changed, grouped, with the Scribe's summary on demand. */
  motivesBand(t) {
    const m = this.motives;
    const prose = (text, color, italic) => (italic ? div().italic() : div())
      .font_family(BODY).text_size(13.5).line_height("19px").text_color(color ?? t.foreground).child(text);
    const fileLink = (rel) => div().id(`mv-${rel}`).font_family(BODY).text_size(12).text_color(rel === this.path ? t.accent : t.muted)
      .cursor_pointer().hover((s) => s.text_color(t.accent)).on_click((_e, cx) => this.select(rel, cx)).child(rel.split("/").pop());
    const scribeBtn = this.scribe === "loading"
      ? div().font_family(BODY).italic().text_size(12.5).text_color(t.dim).child("o Escriba está escrevendo…")
      : this.button(t, "mv-scribe", this.scribe ? "PEDIR NOVO RESUMO" : "PEDIR RESUMO AO ESCRIBA", { primary: !this.scribe }, (cx) => this.motivations(cx, true))
        .tooltip("Um sandestin leve (Claude Haiku) resume as motivações registradas. Leva alguns segundos e usa um pouco de força motriz.");
    if (!m) return v_flex().px(14).pt(10).child(prose("Lendo os registros…", t.dim, true));
    const body = v_flex().id("mv-body").flex_1().min_h(0).px(14).pt(8).pb(12).gap(8).overflow_y_scroll()
      .child(h_flex().gap(8).items_center()
        .child(div().flex_1().font_family(BODY).italic().text_size(12).text_color(t.dim)
          .child(`${m.motivos.length} ${m.motivos.length === 1 ? "motivação" : "motivações"} · ${m.total} tomos${m.sem_registro.length ? ` · ${m.sem_registro.length} sem registro` : ""}`))
        .child(scribeBtn))
      .when(Boolean(this.scribe && this.scribe !== "loading"), (el) => el.child(v_flex().p(10).rounded(2).border(1).border_color(t.accent + "55").bg("#00000040")
        .child(div().pb(4).font_family(TITLE).font_weight(700).text_size(9.5).text_color(t.accent).child("O RESUMO DO ESCRIBA"))
        .child(prose(this.scribe))))
      .children(m.motivos.map((g, i) => v_flex().id(`mv-g-${i}`).gap(3)
        .child(h_flex().gap(6).items_start()
          .child(div().pt(1).font_family(TITLE).font_weight(700).text_size(11).text_color(t.accent).child(`${i + 1}.`))
          .child(v_flex().flex_1().min_w(0).gap(2)
            .child(prose(g.order ? `«${g.order.length > 320 ? g.order.slice(0, 320) + "…" : g.order}»` : "(ordem sem texto)"))
            .when(Boolean(g.opened), (el) => el.child(prose(`a sessão nasceu de: «${g.opened.length > 260 ? g.opened.slice(0, 260) + "…" : g.opened}»`, t.muted, true)))
            .child(div().font_family(BODY).italic().text_size(12).text_color(t.dim)
              .child([`${clock(g.ts)}`, g.tomo ? `sessão «${g.tomo}»` : null, g.sub ? "subagente" : null, g.plan ? `plano: ${g.plan}` : null,
                `${g.files.length} ${g.files.length === 1 ? "tomo" : "tomos"}`].filter(Boolean).join(" · ")))
            .child(h_flex().flex_wrap().gap(8).children(g.files.map(fileLink)))))))
      .when(m.sem_registro.length > 0, (el) => el.child(v_flex().gap(2)
        .child(div().font_family(TITLE).font_weight(700).text_size(9.5).text_color(t.dim).child("SEM MOTIVAÇÃO REGISTRADA"))
        .child(h_flex().flex_wrap().gap(8).children(m.sem_registro.map(fileLink)))));
    return body;
  }

  /** Reads why the sandestins made this change (contexto.py over their session logs), once per tomo. */
  purpose(path, cx) {
    if (this.on || this.ctx[path]) return;
    this.ctx[path] = "loading";
    cx.spawn(async (cx) => {
      const r = await exec("python3", [`${appHome()}/mods/wrath-review/contexto.py`, this.root, path], { timeout: 30000 }).catch(() => null);
      try { this.ctx[path] = JSON.parse(r?.stdout || "null") ?? { edits: [] }; } catch { this.ctx[path] = { edits: [] }; }
      cx.notify();
    });
  }

  /** The purpose column: what was asked, the plan, how each edit was meant, and what was reported. */
  purposeColumn(t) {
    const c = this.ctx[this.path];
    const title = (text) => div().pt(10).pb(3).font_family(TITLE).font_weight(700).text_size(10).text_color(t.accent).child(text);
    const prose = (text, color, italic) => (italic ? div().italic() : div())
      .font_family(BODY).text_size(12.5).line_height("17px").text_color(color ?? t.foreground).child(text);
    const tab = (id, label) => div().id(`rv-tab-${id}`).px(10).h(26).flex().items_center().rounded(2)
      .font_family(TITLE).font_weight(700).text_size(10)
      .border(1).border_color(this.ctxTab === id ? t.accent : t.accent + "00")
      .text_color(this.ctxTab === id ? t.accent : t.dim).cursor_pointer().hover((s) => s.text_color(t.accent))
      .on_click((_e, cx) => { this.ctxTab = id; cx.notify(); }).child(label);
    const col = v_flex().id("rv-purpose").flex_none().w(340).h_full().border_l(1).border_color(t.border).bg(t.chrome)
      .child(h_flex().relative().flex_none().h(34).px(8).gap(4).items_center().overflow_hidden()
        .children(plaque(t))
        .child(tab("tomo", "PROPÓSITO DO TOMO"))
        .child(tab("dominio", "DOMÍNIO"))
        .child(div().flex_1())
        .child(div().font_family(BODY).italic().text_size(11).text_color(t.dim).child("i recolhe")));
    if (this.ctxTab === "dominio") return col.child(this.motivesBand(t));
    const body = v_flex().id("rv-purpose-body").flex_1().min_h(0).px(14).pb(14).overflow_y_scroll();
    if (this.on) return col.child(body.child(prose("Os registros das sessões ficam nesta máquina; esta torre não os tem.", t.dim, true)));
    if (!c || c === "loading") return col.child(body.child(prose("Consultando os registros dos sandestins…", t.dim, true)));
    const edits = c.edits ?? [];
    if (!edits.length) return col.child(body.child(prose(
      "Nenhum registro de sessão explica esta magia: ela foi tecida fora das sessões dos sandestins (à mão, num editor ou por outra ferramenta). Julgue-a pelo diff.", t.dim, true)));
    const first = edits[0], last = edits[edits.length - 1];
    // The order right before the first edit is the most specific; the one that opened the session
    // carries the spec when that order was only "continue"; the last one shows late corrections.
    const begot = first.prompt ?? null;
    const opened = c.origin && c.origin !== begot ? c.origin : null;
    const lastOrder = last.prompt && last.prompt !== begot && last.prompt !== c.origin ? last.prompt : null;
    const planText = c.plan?.text ?? "";
    return col.child(body
      .child(title(first.sub ? "A TAREFA DADA AO SUBAGENTE" : "A ORDEM QUE GEROU ESTA MAGIA"))
      .child(prose(begot ?? "—"))
      .when(Boolean(opened), (el) => el.child(title(`O PEDIDO QUE ABRIU A SESSÃO${first.tomo ? ` «${first.tomo}»` : ""}`)).child(prose(opened, t.muted)))
      .when(Boolean(lastOrder), (el) => el.child(title("A ÚLTIMA ORDEM ANTES DA EDIÇÃO")).child(prose(lastOrder)))
      .when(Boolean(planText), (el) => el
        .child(title("O PLANO APROVADO"))
        .child(div().font_family(MONO).text_size(11).line_height("16px").text_color(t.muted)
          .child(this.planOpen || planText.length <= 900 ? planText : planText.slice(0, 900) + "…"))
        .when(planText.length > 900, (e) => e.child(div().id("rv-plan-toggle").pt(4).font_family(TITLE).font_weight(700).text_size(9.5)
          .text_color(t.accent).cursor_pointer().on_click((_e, cx) => { this.planOpen = !this.planOpen; cx.notify(); })
          .child(this.planOpen ? "RECOLHER O PLANO" : "VER O PLANO INTEIRO"))))
      .child(title(edits.length === 1 ? "COMO O SANDESTIN A TECEU" : `COMO O SANDESTIN A TECEU · ${edits.length} EDIÇÕES`))
      .children(edits.map((e, i) => v_flex().id(`rv-edit-${i}`).pt(6).gap(2)
        .child(div().font_family(BODY).italic().text_size(11.5).text_color(t.dim)
          .child(`${clock(e.ts)} · ${HOW[e.how] ?? e.how}${e.tomo ? ` · tomo «${e.tomo}»` : ""}${e.sub ? " · subagente" : ""}`))
        .when(Boolean(e.why), (el) => el.child(prose(e.why, t.foreground, true)))
        .when(Boolean(e.cmd), (el) => el.child(div().p(4).rounded(2).bg("#00000066").font_family(MONO).text_size(10.5)
          .text_color(t.muted).child(e.cmd.split("\n").slice(0, 4).join("\n"))))))
      .when(Boolean(c.report), (el) => el.child(title("O RELATO DEPOIS DE TECER")).child(prose(c.report, t.muted, true))));
  }

  step(dir, cx) {
    if (!this.files.length) return;
    const i = Math.max(0, this.files.findIndex((f) => f.path === this.path));
    this.select(this.files[(i + dir + this.files.length) % this.files.length].path, cx);
  }

  /** Runs one judgement, then moves on to the next unjudged tomo when this one is settled. */
  /** The next tomo still to judge after position `at` in edit order (wrapping), skipping `skip`. */
  nextUnjudged(at, skip) {
    const n = this.files.length;
    for (let k = 1; k <= n; k++) {
      const c = this.files[(at + k) % n];
      if (c && c.path !== skip && c.state !== "accepted") return c;
    }
    return null;
  }

  /** Runs one judgement. `settles` (a whole-tomo verdict) jumps to the next tomo at once;
   *  a hunk verdict jumps only when the re-read shows the tomo fully judged. */
  act(label, run_, cx, settles = false) {
    if (this.busy) return;
    this.busy = true; this.confirm = null; this.note = null;
    const before = this.path, at = Math.max(0, this.files.findIndex((x) => x.path === before));
    cx.spawn(async (cx) => {
      let ok = true;
      try {
        const r = await run_();
        if (r && r.code !== 0) throw new Error((r.stderr || r.stdout || "").trim());
      } catch (e) { ok = false; this.note = `Contramágica ao ${label}: ${String(e).slice(0, 300)}`; }
      this.busy = false;
      if (ok && settles && this.path === before) {
        const next = this.nextUnjudged(at, before);
        // shown at once (an accepted tomo gets its seal, a rejected one leaves the list); the re-read confirms it
        if (label.startsWith("aceitar")) { const f = this.files.find((x) => x.path === before); if (f) f.state = "accepted"; }
        else this.files = this.files.filter((x) => x.path !== before);
        if (next) this.select(next.path, cx);
      }
      this.refresh(cx, (cx) => {
        if (!ok || settles || this.path !== before) return;
        const f = this.files.find((x) => x.path === before);
        if (!f || f.state === "accepted") {
          const next = this.nextUnjudged(f ? this.files.indexOf(f) : at - 1, before);
          if (next) this.select(next.path, cx);
        }
      });
      cx.notify();
    });
    cx.notify();
  }

  /** Destructive buttons need two clicks: the first arms them for 4 s. */
  armed(key, cx, fire) {
    if (this.confirm === key) { fire(); return; }
    this.confirm = key;
    cx.timer.after(4000, (cx) => { if (this.confirm === key) { this.confirm = null; cx.notify(); } });
    cx.notify();
  }

  pipe(args, patch) {
    return exec("sh", ["-c", 'p="$1"; shift; printf "%s" "$p" | git "$@"', "sh", patch, ...args, "-"], { cwd: this.root, on: this.on, timeout: 20000 });
  }

  acceptFile(cx) { const f = this.current(); if (f && f.state !== "accepted") this.act("aceitar o tomo", () => this.git(["add", "--", f.path]), cx, true); }
  rejectFile(cx) {
    const f = this.current();
    if (!f) return;
    this.armed(`file:${f.path}`, cx, () => this.act("rejeitar o tomo", () => f.untracked
      ? exec("git", ["clean", "-f", "--", f.path], { cwd: this.root, on: this.on })
      : exec("git", ["restore", "--worktree", "--", f.path], { cwd: this.root, on: this.on }), cx, true));
  }
  unaccept(cx) { const f = this.current(); if (f) this.act("desfazer o aceite", () => exec("git", ["restore", "--staged", "--", f.path], { cwd: this.root, on: this.on }), cx); }
  acceptHunk(i, cx) {
    const v = this.view; if (!v?.hunks[i]?.text) return;
    this.act("aceitar o trecho", () => this.pipe(["apply", "--cached", "--recount"], v.header + v.hunks[i].text), cx);
  }
  rejectHunk(i, cx) {
    const v = this.view; if (!v?.hunks[i]?.text) return;
    this.armed(`hunk:${v.path}:${i}`, cx, () => this.act("rejeitar o trecho", () => this.pipe(["apply", "-R", "--recount"], v.header + v.hunks[i].text), cx));
  }
  acceptAll(cx) { this.act("aceitar todos", () => this.git(["add", "-A"]), cx); }

  key(e, cx) {
    const k = e.key;
    if (k === "a") this.acceptFile(cx);
    else if (k === "r") this.rejectFile(cx);
    else if (k === "i") { this.showCtx = !this.showCtx; cx.notify(); }
    else if (k === "t") this.toggleFull(cx);
    else if (k === "m") { this.showCtx = true; this.ctxTab = this.ctxTab === "dominio" ? "tomo" : "dominio"; cx.notify(); }
    else if (k === "n" || k === "right" || k === "j") this.step(1, cx);
    else if (k === "p" || k === "left" || k === "k") this.step(-1, cx);
    else return;
    cx.stop_propagation();
  }

  // ── drawing

  button(t, id, label, { primary = false, danger = false, armed = false, icon = null } = {}, onClick) {
    const color = armed || danger ? t.blocked : primary ? t.accent : t.border;
    return h_flex().id(id).relative().h(26).px(10).gap(6).flex_none().items_center().rounded(2).overflow_hidden()
      .border(1).border_color(armed ? t.blocked : color)
      .children(primary && !armed ? plaque(t, { from: "#e3b964", to: "#9c6f28" }) : plaque(t))
      .font_family(TITLE).font_weight(700).text_size(10)
      .text_color(armed ? t.blocked : primary ? t.solid_foreground : danger ? t.blocked : t.muted)
      .cursor_pointer().hover((s) => s.border_color(armed || danger ? t.blocked : t.accent))
      .on_mouse_down("left", (_e, cx) => cx.stop_propagation())
      .on_click((_e, cx) => onClick(cx))
      .when(Boolean(icon), (el) => el.child(svg(icon).size(12)))
      .child(armed ? "CONFIRMAR? IRREVERSÍVEL" : label);
  }

  mark(t, f) {
    if (f.state === "accepted") return image("mods/wrath-chrome/seal-mini.svg").w(14).h(14).flex_none();
    if (f.state === "partial") return div().size(9).flex_none().rounded_full().border(2).border_color(t.accent);
    return div().size(8).flex_none().rounded_full().bg(t.working);
  }

  row(t, f) {
    const parts = f.path.split("/"), name = parts.pop(), on = f.path === this.path;
    const tag = f.untracked ? "N" : f.deleted ? "D" : "M";
    return h_flex().id(`rv-${f.path}`).min_h(28).flex_none().px(8).py(3).gap(7).items_center().rounded(2).cursor_pointer()
      .border_l(2).border_color(on ? t.accent : t.accent + "00").when(on, (e) => e.bg(t.selected)).hover((s) => s.bg(t.hover))
      .on_click((_e, cx) => this.select(f.path, cx))
      .child(this.mark(t, f))
      .child(div().w(10).flex_none().font_family(MONO).text_size(10.5).text_color(tag === "N" ? t.ansi2 : tag === "D" ? t.ansi1 : t.working).child(tag))
      .child(div().w(22).flex_none().text_right().font_family(TITLE).font_weight(700).text_size(10).text_color(on ? t.accent : t.dim)
        .child(f.seq < 1e9 ? `${f.seq}` : "·"))
      .child(v_flex().flex_1().min_w(0)
        .child(div().truncate().font_family(BODY).text_size(13).text_color(f.state === "accepted" ? t.dim : on ? t.accent : t.foreground).child(name))
        .child(div().truncate().font_family(BODY).italic().text_size(11).text_color(t.dim)
          .child([f.when ? clock(f.when) : null, f.how ? HOW[f.how] : null, parts.join("/") || null].filter(Boolean).join(" · "))))
      .when(f.add > 0, (e) => e.child(div().flex_none().font_family(MONO).text_size(10).text_color(t.ansi2).child(`+${f.add}`)))
      .when(f.del > 0, (e) => e.child(div().flex_none().font_family(MONO).text_size(10).text_color(t.ansi1).child(`−${f.del}`)));
  }

  hunk(t, h, i, readonly) {
    let oldN = 0, newN = 0;
    const m = /^@@ -(\d+)(?:,\d+)? \+(\d+)/.exec(h.head);
    if (m) { oldN = +m[1]; newN = +m[2]; }
    const lines = h.lines.map((line, j) => {
      const k = line[0];
      const num = k === "-" ? oldN++ : k === "+" ? newN++ : k === " " ? (oldN++, newN++) : "";
      return h_flex().id(`ln-${i}-${j}`).w_full().min_h(19).gap(10).px(6)
        .when(k === "+", (e) => e.bg(t.ansi2 + "1c")).when(k === "-", (e) => e.bg(t.ansi1 + "1c"))
        .child(div().w(38).flex_none().text_right().text_color(t.dim).child(num === "" ? "" : String(num)))
        .child(div().w(10).flex_none().text_color(k === "+" ? t.ansi2 : k === "-" ? t.ansi1 : t.dim).child(k === " " ? "" : k))
        .child(div().flex_1().min_w(0).text_color(t.foreground).child((line.slice(1) || " ").slice(0, 600)));
    });
    const armed = this.confirm === `hunk:${this.view?.path}:${i}`;
    return v_flex().id(`hk-${i}`).w_full().flex_none().mb(10).rounded(2).overflow_hidden().border(1).border_color(t.border)
      .child(h_flex().relative().h(30).px(8).gap(8).items_center().overflow_hidden()
        .children(plaque(t))
        .child(div().flex_1().min_w(0).truncate().font_family(MONO).text_size(10.5).text_color(t.ansi13).child(h.head))
        .when(!readonly && Boolean(h.text), (el) => el
          .child(this.button(t, `hk-ok-${i}`, "ACEITAR TRECHO", { primary: true }, (cx) => this.acceptHunk(i, cx)))
          .child(this.button(t, `hk-no-${i}`, "REJEITAR", { danger: true, armed }, (cx) => this.rejectHunk(i, cx)))))
      .child(v_flex().w_full().py(4).font_family(MONO).text_size(11.5).children(lines));
  }

  render(cx) {
    const t = theme();
    if (!this.root) return div().p(20).text_color(t.dim).child("Abra o Julgamento pelo botão JULGAR do Espelho das Alterações.");
    const total = this.files.length, done = this.files.filter((f) => f.state === "accepted").length;
    const idx = Math.max(0, this.files.findIndex((f) => f.path === this.path));
    const f = this.current(), v = this.view;
    const readonly = Boolean(v?.staged);
    const armedFile = f && this.confirm === `file:${f.path}`;

    const header = h_flex().relative().flex_none().h(58).px(16).gap(12).items_center().overflow_hidden()
      .border_b(1).border_color(t.accent + "66")
      .children(plaque(t)).children(rivets(t, 4, 4))
      .child(image("mods/wrath-chrome/seal.svg").w(22).h(39).flex_none())
      .child(v_flex().flex_none()
        .child(div().font_family(TITLE).font_weight(700).text_size(14).text_color(t.accent).child("JULGAMENTO DO MAGO"))
        .child(div().font_family(BODY).italic().text_size(13).text_color(t.muted).child(`${this.name} · ${this.branch ?? "…"}`)))
      .child(v_flex().flex_1().min_w(0).gap(3).px(10)
        .child(div().font_family(BODY).italic().text_size(12.5).text_color(t.muted)
          .child(total ? `${done} de ${total} tomos aceitos pelo Mestre · na ordem em que os sandestins os editaram` : "nenhuma alteração aguarda julgamento"))
        .child(div().relative().h(6).rounded(1).bg("#00000088").overflow_hidden()
          .child(div().absolute().top(0).left(0).h_full().w(`${total ? (100 * done) / total : 0}%`).bg(t.accent))))
      .child(this.button(t, "rv-prev", "◂", {}, (cx) => this.step(-1, cx)))
      .child(div().flex_none().font_family(MONO).text_size(11).text_color(t.muted).child(total ? `${idx + 1}/${total}` : "0/0"))
      .child(this.button(t, "rv-next", "▸", {}, (cx) => this.step(1, cx)))
      .child(this.button(t, "rv-all", "ACEITAR TUDO", { primary: true }, (cx) => this.acceptAll(cx)));

    const list = v_flex().flex_none().w(250).h_full().border_r(1).border_color(t.border).bg(t.chrome)
      .child(div().relative().flex_none().h(4).overflow_hidden().child(hatch(t.accent + "30", 1, 3)))
      .child(v_flex().id("rv-list").flex_1().min_h(0).p(6).gap(1).overflow_y_scroll()
        .children(this.files.map((x) => this.row(t, x)))
        .when(!total, (el) => el.child(div().p(10).font_family(BODY).italic().text_size(13).text_color(t.dim)
          .child(this.loading ? "Consultando o espelho…" : "Os sandestins nada deixaram por julgar."))))
      .child(div().flex_none().px(10).py(6).border_t(1).border_color(t.border).font_family(BODY).italic().text_size(11.5).text_color(t.dim)
        .child("a aceitar · r rejeitar · n/p navegar · t tomo completo · i coluna · m domínio"));

    const fileBar = f && h_flex().flex_none().h(44).px(14).gap(8).items_center().border_b(1).border_color(t.border)
      .child(this.mark(t, f))
      .child(v_flex().flex_1().min_w(0)
        .child(div().truncate().font_family(MONO).text_size(12).text_color(t.foreground).child(f.path))
        .child(div().truncate().font_family(BODY).italic().text_size(12).text_color(t.dim)
          .child(f.seq < 1e9
            ? `${f.seq}º tomo editado${f.when ? ` · ${clock(f.when)}` : ""}${f.how ? ` · ${HOW[f.how]}` : ""}${f.tomo ? ` · tomo «${f.tomo}»` : ""}${f.edits > 1 ? ` · ${f.edits} edições` : ""}`
            : "")))
      .child(this.button(t, "rv-full", this.full ? "SÓ AS MUDANÇAS" : "TOMO COMPLETO", { icon: "mods/wrath-chrome/file-text.svg" }, (cx) => this.toggleFull(cx))
        .tooltip(this.full ? "Voltar aos trechos alterados, com aceite e rejeição por trecho (t)" : "Ver o tomo inteiro com as mudanças destacadas no lugar (t)"))
      .when(readonly, (el) => el
        .child(div().font_family(BODY).italic().text_size(12.5).text_color(t.done).child("aceito · aguarda o selo"))
        .child(this.button(t, "rv-undo", "DESFAZER ACEITE", {}, (cx) => this.unaccept(cx))))
      .when(!readonly, (el) => el
        .child(this.button(t, "rv-ok", "ACEITAR TOMO", { primary: true }, (cx) => this.acceptFile(cx)))
        .child(this.button(t, "rv-no", f.untracked ? "APAGAR TOMO NOVO" : "REJEITAR TOMO", { danger: true, armed: armedFile }, (cx) => this.rejectFile(cx))));

    const body = v_flex().id("rv-diff").flex_1().min_h(0).p(12).overflow_y_scroll()
      .when(!f, (el) => el.child(div().p(20).font_family(BODY).italic().text_size(14).text_color(t.dim)
        .child(total ? "Escolha um tomo à esquerda." : "Tudo julgado. Volte ao Espelho para selar o que aceitou.")))
      .when(Boolean(f && !v), (el) => el.child(div().p(10).text_color(t.dim).child("Revelando a aura…")))
      .when(Boolean(v?.binary), (el) => el.child(div().p(10).font_family(BODY).italic().text_color(t.dim).child("Tomo binário: julgue-o inteiro.")))
      .when(Boolean(v && !v.binary), (el) => el.children(v.hunks.map((h, i) => this.hunk(t, h, i, readonly || v.fresh || v.full))));

    return v_flex().id("review").size_full().bg(t.background).text_color(t.foreground)
      .track_focus(this.handle).on_key_down((e, cx) => this.key(e, cx))
      .child(header)
      .when(Boolean(this.note), (el) => el.child(div().flex_none().px(16).py(6).bg(t.blocked + "22").font_family(BODY).text_size(13).text_color(t.blocked).child(this.note)))
      .child(h_flex().flex_1().min_h(0)
        .child(list)
        .child(v_flex().flex_1().min_w(0).h_full().when(Boolean(fileBar), (el) => el.child(fileBar)).child(body))
        .when(Boolean(f && this.showCtx), (el) => el.child(this.purposeColumn(t))));
  }
}
