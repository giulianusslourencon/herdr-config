"""Tomo do Mago Rubro: troca o nome, deixa só referências vanceanas, põe moldura
rebitada nos diálogos e menus e transforma a barra de status em plaquinhas.

Cada troca precisa casar exatamente; se algo não casar, nada é gravado.
Uso: python3 forja_tomo_rubro.py
"""
import re
from pathlib import Path

H = Path.home() / ".config/herdr-app"
M = H / "mods"
CLAUDE = Path.home() / ".claude"

FRAME = '.relative().border_t(2).border_color(theme().accent).children(rivets(theme(), 4, 5))'

EDITS = {
    # ── nome e emblema
    M / "wrath-chrome/main.js": [
        ('child("GRIMÓRIO DO CRUZADO")', 'child("TOMO DO MAGO RUBRO")'),
        ('svg("mods/wrath-chrome/d20.svg").size(15)', 'svg("mods/wrath-chrome/ioun.svg").size(15)'),
        ('"Grimório · ajustes"', '"Tomo · ajustes"'),
    ],
    M / "wrath-status/main.js": [
        ('("Índice do grimório")', '("Índice do tomo")'),
    ],
    M / "wrath-menu/main.js": [
        ('["Atalhos do grimório", "app.help", {}]', '["Atalhos do tomo", "app.help", {}]'),
        ('["Imagem Especular · nova worktree", "worktree"', '["Reflexo Gêmeo · nova worktree", "worktree"'),
        ('.id("menu")', '.id("menu")' + FRAME),
    ],
    # ── feitiços de D&D trocados por feitiços do Sol Moribundo
    M / "wrath-agents/main.js": [
        ('isPinned ? "Romper o glifo" : "Selar no topo com o Glifo de Guarda"',
         'isPinned ? "Libertar do Encistamento" : "Encistar no topo (Feitiço do Encistamento Desolado)"'),
        ('label: "Glifo de Guarda · selados"', 'label: "Encistados no topo"'),
    ],
    M / "wrath-new-menu/main.js": [
        ('"Mão Prestidigitadora · terminal"', '"Girador de Phandaal · terminal"'),
        ('"Dissipação: falha ao listar os sandestins"', '"Coceira Desesperadora de Lugwiler: falha ao listar os sandestins"'),
        ('"Imagem Especular · nova worktree…"', '"Reflexo Gêmeo · nova worktree…"'),
        ('.id("new-menu")', '.id("new-menu")' + FRAME),
    ],
    M / "wrath-files/main.js": [
        ('"Treva Impenetrável: esta pasta não se deixa ler"', '"Malepsia Física de Xarfaggio: esta pasta está paralisada"'),
    ],
    M / "wrath-worktree/main.js": [
        ('`Imagem Especular · nova worktree${r ? ` de ${r.name}` : ""}`', '`Reflexo Gêmeo · nova worktree${r ? ` de ${r.name}` : ""}`'),
        ('.id("worktree")', '.id("worktree")' + FRAME),
    ],
    M / "wrath-picker/main.js": [
        ('.id("picker")', '.id("picker")' + FRAME),
    ],
    M / "wrath-machine-add/main.js": [
        ('.id("machine-add")', '.id("machine-add")' + FRAME),
    ],
    H / "backgrounds/src/rename_template.js": [
        ('.border_t(2).border_color(t.accent)', '.relative().border_t(2).border_color(t.accent).children(rivets(t, 4, 5))'),
        ('import { run, props, closeOverlay, theme, spaces, focused } from "herdr";',
         'import { run, props, closeOverlay, theme, spaces, focused } from "herdr";\nimport { rivets } from "./kit.js";'),
    ],
    H / "backgrounds/src/toast_template.js": [
        ('() => "Novo grimório pronto"', '() => "Novo tomo pronto"'),
        ('() => "Grimório atualizado"', '() => "Tomo atualizado"'),
        ('      .border_l(3)\n      .border_color(color)',
         '      .relative()\n      .border_l(3)\n      .border_color(color)\n'
         '      .children([["top", "left"], ["top", "right"], ["bottom", "right"]].map(([v, h]) =>\n'
         '        div().absolute()[v](4)[h](4).size(5).rounded_full().bg(t.accent).border(1).border_color("#00000099")))'),
    ],
    # ── statusline do Claude
    CLAUDE / "grimorio/statusline.py": [
        ('"""Statusline do Grimório do Cruzado para o Claude Code.', '"""Statusline do Tomo do Mago Rubro para o Claude Code.'),
        ('  ✦ GRIMÓRIO ✦ Sandestin', '  ✦ TOMO RUBRO ✦ Sandestin'),
        ('  ☽ mana ▰▰▰▱▱▱▱▱▱▱', '  ☽ memória ▰▰▰▱▱▱▱▱▱▱'),
        ('print(f"{GOLD}✦ GRIMÓRIO ✦{RESET} {DIM}as páginas estão em branco{RESET}")',
         'print(f"{GOLD}✦ TOMO RUBRO ✦{RESET} {DIM}as páginas estão em branco{RESET}")'),
        ('head = [f"{GOLD}✦ GRIMÓRIO ✦{RESET} {who}"]', 'head = [f"{GOLD}✦ TOMO RUBRO ✦{RESET} {who}"]'),
        ('{MUTED}mana{RESET}', '{MUTED}memória{RESET}'),
    ],
}

# Barra de status: plaquinhas de pedra separadas por rebites.
STATUS_RENDER = '''  render() {
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
      .child(plate("palette", null, this.hint(t)).cursor_pointer().on_click(() => run("app.palette")));
  }
}
'''


def main():
    staged, missing = {}, []
    for path, pairs in EDITS.items():
        s = staged.get(path) or path.read_text()
        for old, new in pairs:
            if old not in s:
                missing.append(f"{path.name}: {old[:80]}")
                continue
            s = s.replace(old, new)
        staged[path] = s
    sp = M / "wrath-status/main.js"
    s = staged.get(sp) or sp.read_text()
    m = re.search(r"\n  render\(\) \{.*\Z", s, re.S)
    if not m:
        missing.append("wrath-status: render()")
    else:
        s = s[: m.start()] + "\n" + STATUS_RENDER
        s = s.replace('import { h_flex } from "gpui-base";', 'import { h_flex } from "gpui-base";\nimport { plaque, rivet } from "./kit.js";', 1)
        staged[sp] = s
    for p in [M / "wrath-menu/main.js", M / "wrath-new-menu/main.js", M / "wrath-worktree/main.js",
              M / "wrath-picker/main.js", M / "wrath-machine-add/main.js"]:
        s = staged[p]
        if "./kit.js" not in s:
            lines = s.split("\n")
            i = max(k for k, l in enumerate(lines) if l.startswith("import "))
            lines.insert(i + 1, 'import { rivets } from "./kit.js";')
            staged[p] = "\n".join(lines)
    if missing:
        print("NÃO casaram — nada gravado:", *missing, sep="\n  ")
        return 1
    for p, s in staged.items():
        p.write_text(s)
    print(f"gravados {len(staged)} arquivos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
