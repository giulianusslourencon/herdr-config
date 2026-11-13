"""Julgamento compacto: o diff no centro, uma só coluna lateral estreita com abas.

Tira a faixa de motivações do topo e a põe na aba "Domínio" da coluna lateral
(340 px, antes 420), que também tem a aba "Propósito do tomo". `i` recolhe a
coluna, `m` alterna as abas. Cada troca precisa casar; se algo falhar, nada é gravado.
"""
from pathlib import Path

P = Path.home() / ".config/herdr-app/mods/wrath-review/main.js"

PAIRS = [
    # smaller type in the purpose column (must run before the column header is replaced)
    ('''    const prose = (text, color, italic) => (italic ? div().italic() : div())
      .font_family(BODY).text_size(13.5).line_height("19px").text_color(color ?? t.foreground).child(text);
    const col''', '''    const prose = (text, color, italic) => (italic ? div().italic() : div())
      .font_family(BODY).text_size(12.5).line_height("17px").text_color(color ?? t.foreground).child(text);
    const col'''),
    ('''    this.motives = null; this.motivesSig = null; this.scribe = null; this.showMotives = true; // the domain's motivations''',
     '''    this.motives = null; this.motivesSig = null; this.scribe = null; this.ctxTab = "tomo"; // side column: "tomo" | "dominio"'''),
    ('''    const band = v_flex().id("mv-band").flex_none().max_h(300).border_b(1).border_color(t.accent + "55").bg(t.chrome)
      .child(h_flex().flex_none().h(34).px(14).gap(10).items_center()
        .child(image("mods/wrath-chrome/seal-mini.svg").w(14).h(14))
        .child(div().font_family(TITLE).font_weight(700).text_size(11).text_color(t.accent).child("MOTIVAÇÕES DO DOMÍNIO"))
        .child(div().flex_1().font_family(BODY).italic().text_size(12).text_color(t.dim)
          .child(m ? `${m.motivos.length} ${m.motivos.length === 1 ? "motivação" : "motivações"} para ${m.total} tomos${m.sem_registro.length ? ` · ${m.sem_registro.length} sem registro` : ""} · m oculta` : "lendo os registros…"))
        .when(Boolean(m), (el) => el.child(scribeBtn)));
    if (!m) return band;
    const body = v_flex().id("mv-body").flex_1().min_h(0).px(14).pb(10).gap(8).overflow_y_scroll()''',
     '''    if (!m) return v_flex().px(14).pt(10).child(prose("Lendo os registros…", t.dim, true));
    const body = v_flex().id("mv-body").flex_1().min_h(0).px(14).pt(8).pb(12).gap(8).overflow_y_scroll()
      .child(h_flex().gap(8).items_center()
        .child(div().flex_1().font_family(BODY).italic().text_size(12).text_color(t.dim)
          .child(`${m.motivos.length} ${m.motivos.length === 1 ? "motivação" : "motivações"} · ${m.total} tomos${m.sem_registro.length ? ` · ${m.sem_registro.length} sem registro` : ""}`))
        .child(scribeBtn))'''),
    ('''    return band.child(body);''', '''    return body;'''),
    ('''    const col = v_flex().id("rv-purpose").flex_none().w(420).h_full().border_l(1).border_color(t.border).bg(t.chrome)
      .child(h_flex().relative().flex_none().h(34).px(12).gap(8).items_center().overflow_hidden()
        .children(plaque(t))
        .child(div().flex_1().font_family(TITLE).font_weight(700).text_size(11).text_color(t.accent).child("PROPÓSITO DA MAGIA"))
        .child(div().font_family(BODY).italic().text_size(11.5).text_color(t.dim).child("i oculta")));''',
     '''    const tab = (id, label) => div().id(`rv-tab-${id}`).px(10).h(26).flex().items_center().rounded(2)
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
    if (this.ctxTab === "dominio") return col.child(this.motivesBand(t));'''),
    ('''    else if (k === "m") { this.showMotives = !this.showMotives; cx.notify(); }''',
     '''    else if (k === "m") { this.showCtx = true; this.ctxTab = this.ctxTab === "dominio" ? "tomo" : "dominio"; cx.notify(); }'''),
    ('''      .when(Boolean(this.showMotives && total), (el) => el.child(this.motivesBand(t)))
''', ''),
    ('''    const list = v_flex().flex_none().w(300)''', '''    const list = v_flex().flex_none().w(250)'''),
    ('''        .child("a aceitar · r rejeitar · n/→ próximo · p/← anterior · i propósito · m motivações"));''',
     '''        .child("a aceitar · r rejeitar · n/p navegar · i recolhe a coluna · m domínio"));'''),
]

s = P.read_text()
for a, b in PAIRS:
    if s.count(a) != 1:
        raise SystemExit("não casou, nada gravado: " + a[:80])
    s = s.replace(a, b)
P.write_text(s)
print("ok")
