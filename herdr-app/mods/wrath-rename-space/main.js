// Rebatizar domínio: o diálogo de renomear do Wrath, em português.
// Abre por F2/Shift+F2 (mod.open, sem props: usa a aba/domínio em foco),
// pelo duplo-clique na aba ou pelo menu de clique direito (props: { id }).
// Enter inscreve o nome, Esc desiste. Gerado por backgrounds/src/make_rename.py.

import { View, div, svg, image } from "gpui-kit";
import { v_flex, h_flex, InputState, Input } from "gpui-base";
import { run, props, closeOverlay, theme, spaces, focused } from "herdr";
import { rivets } from "./kit.js";

const KIND = "space";
const TITLE_FONT = "Cinzel";
const BODY_FONT = "EB Garamond";

const TEXT = {
  tab: {
    title: "REBATIZAR ABA",
    lore: "Todo nome verdadeiro carrega poder; escolha com cuidado.",
    hint: "Vazio: a aba volta a ser chamada pelo número.",
    command: "tab.rename",
  },
  space: {
    title: "REBATIZAR DOMÍNIO",
    lore: "O domínio responderá ao nome que você inscrever.",
    hint: "Vazio: o domínio toma de novo o nome da pasta.",
    command: "space.rename",
  },
}[KIND];

function target() {
  const id = props()?.id;
  const f = focused();
  if (KIND === "space") {
    const s = spaces().find((x) => x.id === (id ?? f?.space));
    return { id: s?.id, name: s?.name ?? "" };
  }
  for (const s of spaces()) {
    const tab = (s.tabs ?? []).find((x) => x.id === (id ?? f?.tab));
    if (tab) return { id: tab.id, name: /^tb\d+$/.test(tab.name ?? "") ? "" : tab.name ?? "" };
  }
  return { id: id ?? f?.tab, name: "" };
}

export default class Rename extends View {
  init(_props, cx) {
    this.target = target();
    this.text = this.target.name;
    this.input = InputState.new({ value: this.text, placeholder: "um nome verdadeiro…" });
    if (this.text) this.input.set_selected_range({ start: 0, end: this.text.length });
    this.input.on("change", (_e, cx) => { this.text = this.input.value(); cx.notify(); });
    this.input.on("submit", () => this.submit());
    this.inputFocused = true;
    this.input.on("focus", (_e, cx) => { this.inputFocused = true; cx.notify(); });
    this.input.on("blur", (_e, cx) => { this.inputFocused = false; cx.notify(); });
    this.input.focus();
    cx.timer.after(600, () => this.input.focus());
    this.handle = cx.focus_handle();
  }

  close() { closeOverlay(props()?.overlay); }

  submit() {
    this.close();
    if (this.target.id) run(TEXT.command, { id: this.target.id, name: this.text.trim() });
  }

  key(e, cx) {
    if (e.key === "escape") { this.close(); cx.stop_propagation(); }
  }

  render() {
    const t = theme();
    const button = (id, text, primary, action) => h_flex().id(id).h(32).px(16).items_center().rounded(2)
      .border_1().border_color(primary ? t.accent : t.input).bg(primary ? t.accent : t.raised)
      .text_color(primary ? t.accent_foreground : t.foreground)
      .font_family(TITLE_FONT).font_weight(700).text_size(11.5).cursor_pointer()
      .hover((s) => s.opacity(0.88)).on_click(action).child(text);
    return v_flex().id("wrath-rename").track_focus(this.handle).on_key_down((e, cx) => this.key(e, cx))
      .w_full().min_h(0).p(20).bg(t.popover).text_color(t.foreground)
      .relative().border_t(2).border_color(t.accent).children(rivets(t, 4, 5))
      .child(image("mods/wrath-chrome/seal.svg").absolute().top(6).right(46).w(30).h(53))
      .child(h_flex().items_center().gap(10)
        .child(svg("mods/wrath-chrome/square-pen.svg").size(16).text_color(t.accent))
        .child(div().flex_1().font_family(TITLE_FONT).font_weight(700).text_size(14).text_color(t.accent).child(TEXT.title))
        .child(div().text_size(11).text_color(t.dim).child("Esc")))
      .child(div().pt(4).font_family(BODY_FONT).italic().text_size(13.5).text_color(t.muted).child(TEXT.lore))
      .child(div().pt(16).pb(7).font_family(TITLE_FONT).text_size(10.5).text_color(t.dim).child("NOVO NOME"))
      .child(Input.new(this.input).h(36).px(10).rounded(2).border_1()
        .border_color(this.inputFocused ? t.accent : t.input).bg(t.background).text_size(13).text_color(t.foreground))
      .child(div().pt(6).font_family(BODY_FONT).italic().text_size(12.5).text_color(t.dim).child(TEXT.hint))
      .child(h_flex().pt(20).gap(8).justify_end()
        .child(button("rn-cancel", "DESISTIR", false, () => this.close()))
        .child(button("rn-save", "INSCREVER", true, () => this.submit())));
  }
}
