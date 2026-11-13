#!/usr/bin/env python3
"""Statusline do Tomo do Mago Rubro para o Claude Code.

Lê o JSON que o Claude Code envia pelo stdin e escreve duas linhas no tom do
Sol Moribundo (Jack Vance), nas cores do tema Wrath do Herdr:

  ✦ TOMO RUBRO ✦ Sandestin Opus 5.5 · grande ritual · tomo «Estilo do herdr»   ♜ iam_core ⎇ rc ±3
  ☽ cogitador ▰▰▰▱▱▱▱▱▱▱ 26%  ⚖ 7,94 terces  ◷ 37 min  ✎ runas +1402 −31  ⚙ força motriz 5h 6% · 7d 10%

Também escreve o livro-caixa ~/.claude/grimorio/tesouro.json (terces por sessão,
por dia, e a força motriz) que a Crônica do Mestre, no Herdr, lê para o Fator de Lucro.

Falha em silêncio: se faltar um campo, a parte some; nunca derruba a linha.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

E = "\033["
RESET = E + "0m"


def rgb(hexcolor, bold=False, italic=False):
    h = hexcolor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{E}{'1;' if bold else ''}{'3;' if italic else ''}38;2;{r};{g};{b}m"


GOLD = rgb("#d4a24c", bold=True)
GOLD_SOFT = rgb("#d4a24c")
PARCH = rgb("#e9dcc0")
MUTED = rgb("#bfa883")
DIM = rgb("#806c57")
ITAL = rgb("#bfa883", italic=True)
EMBER = rgb("#e8742a")
CRIMSON = rgb("#d23a2f", bold=True)
FEL = rgb("#a8cc5c")
VIOLET = rgb("#c98ae0")

EFFORT = {
    "low": "murmúrio",
    "medium": "encantamento",
    "high": "ritual",
    "xhigh": "grande ritual",
    "max": "invocação suprema",
}


def get(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def git_info(cwd):
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        out = subprocess.run(
            ["git", "--no-optional-locks", "-C", cwd, "status", "--porcelain=v2", "--branch"],
            capture_output=True, text=True, timeout=1.5,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    branch, dirty = None, 0
    for line in out.stdout.splitlines():
        if line.startswith("# branch.head "):
            branch = line.split(" ", 2)[2]
        elif line and not line.startswith("#"):
            dirty += 1
    return branch, dirty


def mana_bar(pct, width=10):
    filled = max(0, min(width, round(pct / 100 * width)))
    color = FEL if pct < 50 else EMBER if pct < 80 else CRIMSON
    return f"{color}{'▰' * filled}{DIM}{'▱' * (width - filled)}{RESET}", color


def duration(ms):
    m = int(ms // 60000)
    return f"{m} min" if m < 60 else f"{m // 60}h{m % 60:02d}"


def money(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pact(pct):
    c = MUTED if pct < 60 else EMBER if pct < 85 else CRIMSON
    return f"{c}{pct:.0f}%{RESET}"


LEDGER = os.path.expanduser("~/.claude/grimorio/tesouro.json")
DEFAULT_BUDGET = 50.0  # dízimo diário em terces (US$); edite "orcamento_diario" no tesouro.json


def ledger(data):
    """Records this session's terces in the day's book. A session that crosses
    midnight keeps a baseline, so each day counts only what was spent in it."""
    sid = get(data, "session_id")
    cost = get(data, "cost", "total_cost_usd")
    if not sid or not isinstance(cost, (int, float)):
        return
    try:
        with open(LEDGER) as f:
            book = json.load(f)
    except Exception:
        book = {}
    book.setdefault("orcamento_diario", DEFAULT_BUDGET)
    days = book.setdefault("dias", {})
    today = time.strftime("%Y-%m-%d")
    base = 0.0
    for day in sorted(days, reverse=True):
        if day < today and sid in days[day].get("sessoes", {}):
            prev = days[day]["sessoes"][sid]
            base = prev.get("base", 0.0) + prev.get("terces", 0.0)
            break
    entry = days.setdefault(today, {"sessoes": {}})["sessoes"].setdefault(sid, {"base": base})
    entry.update({
        "terces": round(max(0.0, cost - entry.get("base", 0.0)), 4),
        "terminal": os.environ.get("HC_TERMINAL_ID"),
        "tomo": get(data, "session_name"),
        "atualizado": time.time(),
    })
    five = get(data, "rate_limits", "five_hour", "used_percentage")
    week = get(data, "rate_limits", "seven_day", "used_percentage")
    if five is not None or week is not None:
        book["forca_motriz"] = {"cinco_horas": five, "sete_dias": week, "atualizado": time.time()}
    for day in sorted(days)[:-30]:
        del days[day]
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(LEDGER), prefix=".tesouro-")
    with os.fdopen(fd, "w") as f:
        json.dump(book, f, ensure_ascii=False)
    os.replace(tmp, LEDGER)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(f"{GOLD}✦ TOMO RUBRO ✦{RESET} {DIM}as páginas estão em branco{RESET}")
        return

    try:
        ledger(data)
    except Exception:
        pass

    sep = f"  {DIM}·{RESET}  "

    # ── linha 1: quem serve, com que intensidade, em qual domínio
    model = get(data, "model", "display_name") or "sandestin"
    style = get(data, "output_style", "name")
    who = f"{PARCH}{'Sandestin ' if style == 'Sandestin' else ''}{model}{RESET}"
    head = [f"{GOLD}✦ TOMO RUBRO ✦{RESET} {who}"]
    effort = EFFORT.get(get(data, "effort", "level") or "")
    if effort:
        head.append(f"{MUTED}{effort}{RESET}")
    if get(data, "thinking", "enabled"):
        head.append(f"{VIOLET}✠ Rito do Pensamento Puro{RESET}")
    if get(data, "fast_mode"):
        head.append(f"{EMBER}⚡ pressa{RESET}")
    tome = get(data, "session_name")
    if tome:
        head.append(f"{ITAL}tomo «{tome}»{RESET}")

    cwd = get(data, "workspace", "current_dir") or get(data, "cwd")
    project = get(data, "workspace", "project_dir") or cwd
    place = f"{GOLD_SOFT}♜{RESET} {PARCH}{os.path.basename(project or '') or '?'}{RESET}"
    if cwd and project and cwd != project:
        place += f"{DIM}/{os.path.relpath(cwd, project)}{RESET}"
    g = git_info(cwd)
    if g and g[0]:
        place += f" {VIOLET}⎇ {g[0]}{RESET}"
        if g[1]:
            place += f" {EMBER}±{g[1]}{RESET}"
    line1 = sep.join(head) + f"   {place}"

    # ── linha 2: mana, ouro, vigília, runas, pactos
    parts = []
    pct = get(data, "context_window", "used_percentage")
    if isinstance(pct, (int, float)):
        bar, c = mana_bar(pct)
        size = get(data, "context_window", "context_window_size")
        cap = (f" {DIM}de {size // 1_000_000}M{RESET}" if isinstance(size, int) and size >= 1_000_000
               else f" {DIM}de {size // 1000}k{RESET}" if isinstance(size, int) else "")
        parts.append(f"{GOLD_SOFT}☽{RESET} {MUTED}cogitador{RESET} {bar} {c}{pct:.0f}%{RESET}{cap}")
    cost = get(data, "cost", "total_cost_usd")
    if isinstance(cost, (int, float)):
        parts.append(f"{GOLD_SOFT}⚖{RESET} {PARCH}{money(cost)}{RESET} {MUTED}terces{RESET}")
    ms = get(data, "cost", "total_duration_ms")
    if isinstance(ms, (int, float)):
        parts.append(f"{GOLD_SOFT}◷{RESET} {PARCH}{duration(ms)}{RESET} {MUTED}de vigília{RESET}")
    add, rem = get(data, "cost", "total_lines_added"), get(data, "cost", "total_lines_removed")
    if isinstance(add, int) and isinstance(rem, int) and (add or rem):
        parts.append(f"{GOLD_SOFT}✎{RESET} {MUTED}runas{RESET} {FEL}+{add}{RESET} {CRIMSON}−{rem}{RESET}")
    five = get(data, "rate_limits", "five_hour", "used_percentage")
    week = get(data, "rate_limits", "seven_day", "used_percentage")
    pacts = []
    if isinstance(five, (int, float)):
        pacts.append(f"{MUTED}5h{RESET} {pact(five)}")
    if isinstance(week, (int, float)):
        pacts.append(f"{MUTED}7d{RESET} {pact(week)}")
    if pacts:
        parts.append(f"{GOLD_SOFT}⚙{RESET} {MUTED}força motriz{RESET} " + f" {DIM}·{RESET} ".join(pacts))
    warm = get(data, "prompt_cache", "warm")
    if warm is False:
        parts.append(f"{EMBER}❄ o Espírito da Máquina esfriou{RESET}")

    print(line1)
    if parts:
        print(f"  {DIM}·{RESET}  ".join(parts))


if __name__ == "__main__":
    main()
