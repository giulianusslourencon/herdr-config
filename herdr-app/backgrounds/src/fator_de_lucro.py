"""Mostrador do Fator de Lucro e litanias na Crônica do Mestre (mods/wrath-chronicle).

Lê ~/.claude/grimorio/tesouro.json, o livro-caixa escrito pela statusline do Claude.
Cada troca precisa casar exatamente; se algo não casar, nada é gravado.
Uso: python3 fator_de_lucro.py
"""
from pathlib import Path

P = Path.home() / ".config/herdr-app/mods/wrath-chronicle/main.js"

TREASURY = '''    this.inner = next;
    const book = await readTextFile(LEDGER()).catch(() => null);
    try { this.book = book ? JSON.parse(book) : null; } catch {}
  }

  /** O Fator de Lucro: quanto do dízimo diário ainda resta, de 0 a 100, num mostrador de bronze. */
  treasury(t, named) {
    const budget = Number(this.book?.orcamento_diario) || 50;
    const sessions = Object.values(this.book?.dias?.[today()]?.sessoes ?? {});
    const spent = sessions.reduce((n, x) => n + (x.terces ?? 0), 0);
    const frac = Math.min(1, spent / budget);
    const factor = Math.max(0, Math.round(100 * (1 - spent / budget)));
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
            .child(`${terces(spent)} de ${terces(budget)} terces do dízimo de hoje`))))
      .child(div().pt(2).font_family(TITLE_FONT).font_weight(700).text_size(9.5).text_color(t.dim).child("FORÇA MOTRIZ"))
      .child(bar("5h", motive.cinco_horas))
      .child(bar("7d", motive.sete_dias))
      .when(rows.length > 0, (el) => el.child(div().pt(4).font_family(TITLE_FONT).font_weight(700).text_size(9.5).text_color(t.dim)
        .child("TERCES POR SANDESTIN")).children(rows));
  }'''

HELPERS = '''function terces(v) {
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

function load() {'''

EDITS = [
    ('import { View, div, svg } from "gpui-kit";', 'import { View, div, svg, PathBuilder, Background } from "gpui-kit";'),
    ('const FAMILIARS = () => `${home()}/.claude/grimorio/familiares`;',
     'const GRIMORIO = () => `${home()}/.claude/grimorio`;\nconst FAMILIARS = () => `${GRIMORIO()}/familiares`;\n'
     'const LEDGER = () => `${GRIMORIO()}/tesouro.json`; // written by the Claude statusline'),
    ('function load() {', HELPERS),
    ('    cx.spawn(async (cx) => {\n      await this.reload();',
     '    this.book = null; // the ledger: terces per session per day, and the motive force\n    cx.spawn(async (cx) => {\n      await this.reload();'),
    ('        try { await watchFolder(FAMILIARS()); } catch { return; }', '        try { await watchFolder(GRIMORIO()); } catch { return; }'),
    ('    this.inner = next;\n  }', TREASURY),
    ('      this.note("wake", `Cogitador desperto · ${list.length}',
     '      this.note("wake", `Litania da Ignição recitada · o cogitador desperta · ${list.length}'),
    ('this.note("summon", `${who} foi invocado ao serviço${task}`);',
     'this.note("summon", `${who} foi invocado ao serviço${task} · entoada a Litania da Ignição`);'),
    ('            .child("o cogitador anota cada feito da tripulação")))', '            .child("os cogitadores anotam cada feito dos sandestins de Vossa Sapiência")))'),
    ('      .child(div().relative().flex_none().h(5).overflow_hidden().child(hatch(t.accent + "30", 1, 3)))',
     '      .child(div().relative().flex_none().h(5).overflow_hidden().child(hatch(t.accent + "30", 1, 3)))\n      .child(this.treasury(t, named))'),
    ('"+++ Nenhum feito registrado. O vazio aguarda. +++"', '"+++ Nenhum feito registrado. O Espírito da Máquina aguarda. +++"'),
]

s = P.read_text()
missing = [a[:70] for a, _ in EDITS if s.count(a) != 1]
if missing:
    raise SystemExit("não casaram, nada gravado:\n  " + "\n  ".join(missing))
for a, b in EDITS:
    s = s.replace(a, b)
P.write_text(s)
print("ok")
