#!/usr/bin/env python3
"""Guardião dos sandestins: mede o que cada Claude Code está gastando da máquina e
contém os encantamentos que ameaçam derrubá-la.

Um "encantamento" é a árvore de processos de um comando do Bash tool: um filho
direto do processo `claude` cujo cmdline passa pelo shell-snapshot do Claude
(`zsh -c source ~/.claude/shell-snapshots/...`). É onde moram jest, tsc, builds,
scripts. O guardião NUNCA mata:
  - o próprio processo `claude` (a sessão segue viva, só o comando falha);
  - servidores MCP e outros filhos do claude que não sejam encantamentos;
  - qualquer processo fora de um claude (terminais do Mestre, apps).

Uso:
  guardiao.py ls [--json]            sandestins, consumo, encantamentos (amostra de 1 s)
  guardiao.py conter <tN|pid> [--sim]  mata os encantamentos de um terminal, ou um só (pid raiz)
  guardiao.py vigiar [--sim] [--uma]   laço automático (o serviço systemd roda este)
  guardiao.py estado                 config + último evento, em JSON

Config: ~/.claude/grimorio/guardiao.json (criado com os padrões na primeira vez).
Log:    ~/.claude/grimorio/guardiao.log
Último evento: $XDG_RUNTIME_DIR/guardiao-evento.json (lido pelo Herdr).

Gatilho do vigia: memória disponível abaixo de `mem_minima_gb` OU pressão de memória
(PSI `full avg10`) acima de `psi_full_limite`, por `leituras` leituras seguidas.
Ação: mata (SIGTERM, depois SIGKILL) o encantamento com mais RSS, se passar de
`rss_minimo_mb`; depois espera `pausa_s` antes de agir de novo. Se nenhum
encantamento é grande o bastante, só registra; não toca em mais nada.
Só Linux; lê /proc. Nada a instalar.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

GRIMORIO = os.path.expanduser("~/.claude/grimorio")
CONFIG = os.path.join(GRIMORIO, "guardiao.json")
LOG = os.path.join(GRIMORIO, "guardiao.log")
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
EVENT = os.path.join(RUNTIME, "guardiao-evento.json")
SNAPSHOT_MARK = "/.claude/shell-snapshots/"
TICK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")

DEFAULTS = {
    "ativo": True,           # false: o vigia só observa
    "simular": False,        # true: registra o que mataria, não mata
    "mem_minima_gb": 1.2,    # MemAvailable abaixo disto conta como ameaça
    "psi_full_limite": 25.0, # % do tempo com todas as tarefas travadas por memória (avg10)
    "leituras": 3,           # leituras seguidas em ameaça antes de agir
    "intervalo_s": 2.0,
    "rss_minimo_mb": 300,    # encantamento menor que isto nunca é morto pelo vigia
    "pausa_s": 15,           # depois de conter, espera isto antes de agir de novo
    "notificar": True,       # notify-send no desktop
    "som": "~/.config/herdr-app/sounds/encantamento-desfeito.wav",  # "" silencia
}


# ── leitura de /proc ──────────────────────────────────────────────────────────

def read_procs():
    """{pid: {ppid, comm, cmd, start, jiffies, rss, tid}} de todos os processos legíveis."""
    out = {}
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        try:
            stat = open(f"/proc/{pid}/stat").read()
            comm = stat[stat.index("(") + 1:stat.rindex(")")]
            f = stat[stat.rindex(")") + 2:].split()
            ppid, jiffies, start = int(f[1]), int(f[11]) + int(f[12]), int(f[19])
            rss = int(open(f"/proc/{pid}/statm").read().split()[1]) * PAGE
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace").strip()
        except Exception:
            continue
        tid = None
        if comm == "claude":
            try:
                env = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
                tid = next((e[15:].decode() for e in env if e.startswith(b"HC_TERMINAL_ID=")), None)
            except Exception:
                pass
        out[pid] = {"ppid": ppid, "comm": comm, "cmd": cmd, "start": start, "jiffies": jiffies, "rss": rss, "tid": tid}
    return out


def children_map(procs):
    kids = {}
    for pid, p in procs.items():
        kids.setdefault(p["ppid"], []).append(pid)
    return kids


def subtree(root, kids):
    seen, stack = [], [root]
    while stack:
        pid = stack.pop()
        seen.append(pid)
        stack.extend(kids.get(pid, []))
    return seen


def spell_label(root, pids, procs):
    """O processo mais pesado da árvore descreve o encantamento (o jest, não o zsh)."""
    inner = [p for p in pids if p != root] or [root]
    heavy = max(inner, key=lambda p: procs[p]["rss"])
    cmd = procs[heavy]["cmd"] or procs[heavy]["comm"]
    if SNAPSHOT_MARK in cmd:  # só sobrou o zsh: mostra o que ele avalia
        i = cmd.find("eval '")
        cmd = cmd[i + 6:] if i >= 0 else "encantamento"
        cmd = cmd.split("' < /dev/null")[0]
    home = os.path.expanduser("~")
    return cmd.replace(home, "~")[:160]


def sandestins(procs, prev_jiffies=None, elapsed=None):
    """Cada claude com HC_TERMINAL_ID (ou sem, como 'fora'): consumo e encantamentos."""
    kids = children_map(procs)
    cores = os.cpu_count() or 1

    def cpu_of(pids):
        if not prev_jiffies or not elapsed:
            return None
        used = 0
        for p in pids:
            key = f"{p}:{procs[p]['start']}"
            if key in prev_jiffies:
                used += max(0, procs[p]["jiffies"] - prev_jiffies[key])
        return round(100 * used / TICK / elapsed / cores, 1)

    result = []
    for pid, p in procs.items():
        if p["comm"] != "claude" or procs.get(p["ppid"], {}).get("comm") == "claude":
            continue
        all_pids = subtree(pid, kids)
        spells = []
        for child in kids.get(pid, []):
            if SNAPSHOT_MARK not in procs[child]["cmd"]:
                continue
            tree = subtree(child, kids)
            if os.getpid() in tree:  # o próprio guardião, chamado por um sandestin
                continue
            spells.append({
                "pid": child,
                "start": procs[child]["start"],
                "label": spell_label(child, tree, procs),
                "rss": sum(procs[x]["rss"] for x in tree),
                "cpu": cpu_of(tree),
                "procs": len(tree),
            })
        spells.sort(key=lambda s: -s["rss"])
        result.append({
            "terminal": p["tid"],
            "pid": pid,
            "rss": sum(procs[x]["rss"] for x in all_pids),
            "cpu": cpu_of(all_pids),
            "procs": len(all_pids),
            "spells": spells,
        })
    result.sort(key=lambda s: -s["rss"])
    return result


def jiffies_snapshot(procs):
    return {f"{pid}:{p['start']}": p["jiffies"] for pid, p in procs.items()}


def sample(seconds=1.0):
    a = read_procs()
    t0 = time.time()
    time.sleep(seconds)
    b = read_procs()
    return b, sandestins(b, jiffies_snapshot(a), time.time() - t0)


def meminfo():
    m = {}
    for line in open("/proc/meminfo"):
        k, v = line.split(":", 1)
        m[k] = int(v.split()[0]) * 1024
    return m


def psi_full_avg10():
    try:
        for line in open("/proc/pressure/memory"):
            if line.startswith("full"):
                return float(line.split()[1].split("=")[1])
    except Exception:
        pass
    return 0.0


# ── config, log, eventos ──────────────────────────────────────────────────────

def load_config():
    try:
        cfg = json.load(open(CONFIG))
    except FileNotFoundError:
        cfg = {}
        write_json(CONFIG, DEFAULTS)
    except Exception:
        cfg = {}
    return {**DEFAULTS, **cfg}


def write_json(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".guardiao-")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
        if os.path.getsize(LOG) > 512 * 1024:
            os.replace(LOG, LOG + ".1")
    except Exception:
        pass
    print(line, file=sys.stderr, flush=True)


def event(kind, text, extra=None):
    data = {"at": time.time(), "kind": kind, "text": text, **(extra or {})}
    try:
        write_json(EVENT, data)
    except Exception:
        pass


def chime(cfg):
    """Toca o som do guardião sem esperar por ele (funciona com o Herdr fechado)."""
    path = os.path.expanduser(cfg.get("som") or "")
    if not path or not os.path.exists(path):
        return
    for player in ("pw-play", "paplay", "aplay"):
        try:
            subprocess.Popen([player, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
            return
        except FileNotFoundError:
            continue
        except Exception:
            return


def desktop(title, body, cfg):
    chime(cfg)
    if not cfg.get("notificar"):
        return
    try:
        subprocess.run(["notify-send", "-u", "critical", "-a", "Guardião", title, body], timeout=3,
                       capture_output=True)
    except Exception:
        pass


# ── conter ────────────────────────────────────────────────────────────────────

def alive(pid, start):
    try:
        stat = open(f"/proc/{pid}/stat").read()
        return int(stat[stat.rindex(")") + 2:].split()[19]) == start
    except Exception:
        return False


def kill_tree(root, start, simulate=False, grace=3.0):
    """SIGTERM na árvore toda (folhas primeiro), SIGKILL no que sobrar após `grace` s.
    Confere pid+starttime antes de cada sinal: pid reciclado nunca é atingido."""
    procs = read_procs()
    if root not in procs or procs[root]["start"] != start:
        return {"killed": 0, "gone": True}
    tree = subtree(root, children_map(procs))
    targets = [(p, procs[p]["start"]) for p in reversed(tree)]
    if simulate:
        return {"killed": 0, "would": len(targets)}
    for p, s in targets:
        if alive(p, s):
            try:
                os.kill(p, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.time() + grace
    while time.time() < deadline and any(alive(p, s) for p, s in targets):
        time.sleep(0.2)
    forced = 0
    for p, s in targets:
        if alive(p, s):
            try:
                os.kill(p, signal.SIGKILL)
                forced += 1
            except ProcessLookupError:
                pass
    return {"killed": len(targets), "forced": forced}


def find_spell(procs, pid):
    """O encantamento cuja raiz é `pid`, ou que contém `pid`, sob algum claude."""
    for s in sandestins(procs):
        for sp in s["spells"]:
            if sp["pid"] == pid:
                return s, sp
    kids = children_map(procs)
    for s in sandestins(procs):
        for sp in s["spells"]:
            if pid in subtree(sp["pid"], kids):
                return s, sp
    return None, None


def contain(target, simulate=False, why="pedido do Mestre"):
    procs = read_procs()
    chosen = []
    if target.isdigit():
        s, sp = find_spell(procs, int(target))
        if not sp:
            return {"ok": False, "error": f"pid {target} não é encantamento de nenhum sandestin"}
        chosen = [(s, sp)]
    else:
        for s in sandestins(procs):
            if s["terminal"] == target:
                chosen += [(s, sp) for sp in s["spells"]]
        if not chosen:
            return {"ok": False, "error": f"nenhum encantamento em curso no terminal {target}"}
    done = []
    for s, sp in chosen:
        r = kill_tree(sp["pid"], sp["start"], simulate)
        mb = round(sp["rss"] / 1e6)
        verb = "simularia conter" if simulate else "conteve"
        log(f"{verb} {s['terminal'] or 'claude:' + str(s['pid'])} pid {sp['pid']} ({mb} MB, {sp['procs']} proc) — {why}: {sp['label']}")
        done.append({"terminal": s["terminal"], "pid": sp["pid"], "rss": sp["rss"], "label": sp["label"], **r})
    return {"ok": True, "simulate": simulate, "contained": done}


# ── vigia ─────────────────────────────────────────────────────────────────────

def watch(simulate_flag=False, once=False):
    strikes, quiet_until = 0, 0.0
    log(f"vigia desperto (pid {os.getpid()})")
    while True:
        cfg = load_config()
        simulate = simulate_flag or bool(cfg["simular"])
        m = meminfo()
        avail = m.get("MemAvailable", m["MemFree"])
        psi = psi_full_avg10()
        threat = cfg["ativo"] and (avail < cfg["mem_minima_gb"] * 1e9 or psi > cfg["psi_full_limite"])
        strikes = strikes + 1 if threat else 0
        if strikes >= cfg["leituras"] and time.time() >= quiet_until:
            procs = read_procs()
            spells = [(s, sp) for s in sandestins(procs) for sp in s["spells"]]
            spells.sort(key=lambda x: -x[1]["rss"])
            why = f"memória livre {avail / 1e9:.1f} GB, pressão {psi:.0f}%"
            if spells and spells[0][1]["rss"] >= cfg["rss_minimo_mb"] * 1e6:
                s, sp = spells[0]
                r = kill_tree(sp["pid"], sp["start"], simulate)
                who = s["terminal"] or f"claude:{s['pid']}"
                mb = round(sp["rss"] / 1e6)
                verb = "SIMULAÇÃO: conteria" if simulate else "conteve"
                log(f"{verb} {who} pid {sp['pid']} ({mb} MB) — {why}: {sp['label']}")
                text = f"{'Conteria' if simulate else 'Contive'} o encantamento de {who} ({mb} MB): {sp['label'][:90]}"
                event("contido", text, {"terminal": s["terminal"], "simulate": simulate, "rss": sp["rss"]})
                desktop("Guardião dos sandestins", f"{text}\nMotivo: {why}", cfg)
                quiet_until = time.time() + cfg["pausa_s"]
            else:
                log(f"ameaça ({why}), mas nenhum encantamento de sandestin passa de {cfg['rss_minimo_mb']} MB; nada contido")
                event("ameaca", f"Máquina sob pressão ({why}); nenhum sandestin é o culpado")
                quiet_until = time.time() + cfg["pausa_s"]
            strikes = 0
        if once:
            return
        time.sleep(cfg["intervalo_s"])


# ── CLI ───────────────────────────────────────────────────────────────────────

def fmt_mb(b):
    return f"{b / 1e9:.1f} GB" if b >= 1e9 else f"{round(b / 1e6)} MB"


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "ls"
    flags = set(a for a in argv[2:] if a.startswith("--"))
    args = [a for a in argv[2:] if not a.startswith("--")]
    if cmd == "ls":
        _, ss = sample()
        if "--json" in flags:
            print(json.dumps(ss, ensure_ascii=False))
            return 0
        m = meminfo()
        print(f"memória livre {fmt_mb(m['MemAvailable'])} de {fmt_mb(m['MemTotal'])} · pressão full avg10 {psi_full_avg10():.0f}%")
        for s in ss:
            print(f"{s['terminal'] or '(fora do Herdr)':>8}  claude {s['pid']:<7} {s['cpu'] or 0:5.1f}%  {fmt_mb(s['rss']):>8}  {s['procs']} proc")
            for sp in s["spells"]:
                print(f"{'':>10}└ pid {sp['pid']:<7} {sp['cpu'] or 0:5.1f}%  {fmt_mb(sp['rss']):>8}  {sp['label'][:90]}")
        return 0
    if cmd == "conter" and args:
        r = contain(args[0], "--sim" in flags)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r["ok"] else 1
    if cmd == "vigiar":
        try:
            watch("--sim" in flags, "--uma" in flags)
        except KeyboardInterrupt:
            log("vigia dispensado")
        return 0
    if cmd == "estado":
        try:
            last = json.load(open(EVENT))
        except Exception:
            last = None
        print(json.dumps({"config": load_config(), "ultimo": last}, ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
