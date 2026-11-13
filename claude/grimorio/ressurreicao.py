#!/usr/bin/env python3
"""Ressurreição dos sandestins: reabre as sessões do Claude Code que estavam
abertas no Herdr quando o core perdeu os programas (reboot, logout, crash).

Fechar e abrir o app Herdr NÃO derruba sessões: os terminais vivem no core
(`hc-hold-*.service`). Numa perda, o core devolve cada terminal mantido
(`keep: true`) como um shell vazio, no mesmo endereço, aba e pasta, mas nunca
re-executa o programa original. Este vigia cobre esse buraco.

Ciclo (a cada INTERVALO_S):
  1. Lê a instância do holder (`hc server status`). Se mudou desde a última
     fotografia, houve perda: as sessões fotografadas viram "pendentes".
  2. Para cada pendente: se o terminal existe, está vivo, o primeiro plano é um
     shell e aquele sessionId não está aberto em nenhum outro claude, digita
     `cd <cwd> && claude --resume <sessionId>` naquele terminal.
     Só reabre a sessão; nunca envia prompt nenhum.
  3. Fotografa as sessões vivas: terminal → foreground.pid →
     ~/.claude/sessions/<pid>.json → sessionId.

Garantias:
  - Saída deliberada (/exit, ctrl+d) com o holder igual NÃO é ressuscitada:
    a próxima fotografia simplesmente não tem a sessão.
  - Nunca digita num terminal cujo primeiro plano não seja um shell (um claude
    num diálogo de permissão, um vim, um script rodando).
  - Pendentes expiram após JANELA_S sem terminal adequado.

Uso:
  ressurreicao.py vigiar [--sim]   laço (o serviço systemd roda este)
  ressurreicao.py uma [--sim]      um ciclo só
  ressurreicao.py ls               fotografia e pendentes atuais
  ressurreicao.py simular-perda    marca a fotografia atual como pendente (teste;
                                   combine com `uma --sim` para ver o que faria)
Estado: ~/.claude/grimorio/ressurreicao.json   Log: ~/.claude/grimorio/ressurreicao.log
"""
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time

HC = os.path.expanduser("~/.local/bin/herdr-core")
GRIMORIO = os.path.expanduser("~/.claude/grimorio")
ESTADO = os.path.join(GRIMORIO, "ressurreicao.json")
LOG = os.path.join(GRIMORIO, "ressurreicao.log")
SESSOES = os.path.expanduser("~/.claude/sessions")
INTERVALO_S = 15
JANELA_S = 30 * 60
SHELLS = {"zsh", "bash", "sh", "fish"}


def agora_ms():
    return int(time.time() * 1000)


def log(msg):
    linha = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    with open(LOG, "a") as f:
        f.write(linha + "\n")
    if sys.stdout.isatty():
        print(linha)


def hc(*args, timeout=20):
    r = subprocess.run([HC, *args, "--json"], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"hc {' '.join(args)}: rc={r.returncode} {r.stderr.strip()[:300]}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def carregar():
    try:
        with open(ESTADO) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"instance": None, "sessions": {}, "pending": None}


def salvar(st):
    fd, tmp = tempfile.mkstemp(dir=GRIMORIO, prefix=".ressurreicao.")
    with os.fdopen(fd, "w") as f:
        json.dump(st, f, indent=2, ensure_ascii=False)
    os.replace(tmp, ESTADO)


def pid_vivo(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def sessoes_abertas():
    """sessionIds com um processo claude vivo, de ~/.claude/sessions/<pid>.json."""
    abertas = {}
    try:
        nomes = os.listdir(SESSOES)
    except FileNotFoundError:
        return abertas
    for nome in nomes:
        if not nome.endswith(".json"):
            continue
        try:
            with open(os.path.join(SESSOES, nome)) as f:
                s = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        pid, sid = s.get("pid"), s.get("sessionId")
        if isinstance(pid, int) and sid and pid_vivo(pid):
            abertas[pid] = s
    return abertas


def fotografar():
    """{endereço: {sessionId, cwd, name, where}} das sessões claude interativas vivas."""
    abertas = sessoes_abertas()
    foto = {}
    for t in (hc("ls") or {}).get("terminals", []):
        if t.get("state") != "live":
            continue
        try:
            d = hc("get", t["address"])
        except Exception:
            continue
        fg = d.get("foreground") or {}
        s = abertas.get(fg.get("pid"))
        if fg.get("name") != "claude" or not s or s.get("kind") != "interactive":
            continue
        foto[t["address"]] = {
            "sessionId": s["sessionId"],
            "cwd": s.get("cwd") or fg.get("cwd"),
            "name": s.get("name"),
            "where": (d.get("labels") or {}).get("where"),
        }
    return foto


def ressuscitar(st, sim):
    pend = st.get("pending")
    if not pend:
        return
    abertos = {s["sessionId"] for s in sessoes_abertas().values()}
    for addr, e in list(pend["entries"].items()):
        rotulo = f"{addr} [{e.get('where') or '?'}] {e.get('name') or ''} {e['sessionId']}"
        if e["sessionId"] in abertos:
            log(f"já aberta, ignoro: {rotulo}")
            del pend["entries"][addr]
            continue
        try:
            d = hc("get", addr)
        except Exception:
            continue  # terminal ainda não voltou; tenta no próximo ciclo
        if d.get("state") != "live":
            continue
        fg = d.get("foreground") or {}
        if fg.get("name") not in SHELLS:
            log(f"primeiro plano é {fg.get('name')!r}, não um shell; desisto: {rotulo}")
            del pend["entries"][addr]
            continue
        cmd = f"cd -- {shlex.quote(e['cwd'])} && claude --resume {shlex.quote(e['sessionId'])}"
        if sim:
            log(f"[sim] digitaria em {addr}: {cmd}")
            continue
        try:
            hc("send", addr, cmd, timeout=60)
            log(f"ressuscitada: {rotulo}")
        except Exception as ex:
            log(f"falhou ao digitar em {rotulo}: {ex}")
        del pend["entries"][addr]
    if pend["entries"] and agora_ms() - pend["since_ms"] > JANELA_S * 1000:
        log(f"janela expirou; {len(pend['entries'])} pendentes descartadas: {sorted(pend['entries'])}")
        pend["entries"] = {}
    if not pend["entries"]:
        st["pending"] = None


def ciclo(sim=False):
    try:
        inst = hc("server", "status")["holder"]["instance"]
    except Exception:
        return  # core fora do ar; tenta de novo
    st = carregar()
    if st.get("instance") and st["instance"] != inst:
        if st.get("sessions"):
            log(f"holder mudou ({st['instance'][:8]} → {inst[:8]}): {len(st['sessions'])} sessões pendentes")
            pend = st.get("pending") or {"entries": {}}
            pend["entries"].update(st["sessions"])
            pend["since_ms"] = agora_ms()
            st["pending"] = pend
        st["sessions"] = {}
    st["instance"] = inst
    ressuscitar(st, sim)
    if not sim:
        st["sessions"] = fotografar()
        st["updated_ms"] = agora_ms()
        salvar(st)


def main():
    os.makedirs(GRIMORIO, exist_ok=True)
    args = sys.argv[1:]
    sim = "--sim" in args
    cmd = args[0] if args else "ls"
    if cmd == "vigiar":
        log(f"vigia iniciado (sim={sim})")
        while True:
            try:
                ciclo(sim)
            except Exception as ex:
                log(f"erro no ciclo: {ex}")
            time.sleep(INTERVALO_S)
    elif cmd == "uma":
        ciclo(sim)
    elif cmd == "ls":
        print(json.dumps(carregar(), indent=2, ensure_ascii=False))
    elif cmd == "simular-perda":
        st = carregar()
        st["instance"] = "simulada-" + str(agora_ms())
        salvar(st)
        print("instância marcada como antiga; o próximo ciclo trata a fotografia como perdida")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
