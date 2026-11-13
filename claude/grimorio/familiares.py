#!/usr/bin/env python3
"""Ponte entre o Claude Code e o Círculo de Invocação do Herdr.

Hook global (SubagentStart, SubagentStop, PreToolUse:Agent, Stop, SessionEnd).
Cada sessão do Claude que roda dentro do Herdr (HC_TERMINAL_ID no ambiente)
mantém ~/.claude/grimorio/familiares/<terminal>.json com o que roda em
segundo plano nela:

  {"session_id": ..., "terminal": "t9", "updated": 1794240000,
   "agents": {"<agent_id>": {"type": "Explore", "description": "...", "since": ...}},
   "shells": [{"id": ..., "description": ..., "command": ..., "status": "running"}],
   "pending": [{"type": ..., "description": ..., "at": ...}]}

- PreToolUse(Agent) guarda a descrição do pedido; SubagentStart a casa com o
  agent_id pelo tipo (o mais antigo primeiro); SubagentStop remove o agente.
- Stop traz o retrato `background_tasks` do fim do turno: dele saem os shells
  em segundo plano (nenhum hook avisa quando um shell termina).
- SessionEnd apaga o arquivo.
Fora do Herdr não faz nada. Nunca bloqueia o Claude: sai sempre com 0, sem saída.
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

DIR = Path.home() / ".claude/grimorio/familiares"
PENDING_TTL = 120  # segundos que uma descrição espera o SubagentStart


def load(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save(path, data):
    DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DIR, prefix=".tmp-")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def main():
    terminal = os.environ.get("HC_TERMINAL_ID")
    if not terminal:
        return
    try:
        event = json.load(sys.stdin)
    except Exception:
        return
    name = event.get("hook_event_name")
    path = DIR / f"{terminal}.json"
    now = time.time()

    if name == "SessionEnd":
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return

    data = load(path)
    if data.get("session_id") != event.get("session_id"):
        data = {"session_id": event.get("session_id"), "terminal": terminal, "agents": {}, "shells": [], "pending": []}
    data.setdefault("agents", {})
    data.setdefault("shells", [])
    data["pending"] = [p for p in data.get("pending", []) if now - p.get("at", 0) < PENDING_TTL]

    if name == "PreToolUse" and event.get("tool_name") in ("Agent", "Task"):
        inp = event.get("tool_input") or {}
        data["pending"].append({"type": inp.get("subagent_type") or "general-purpose",
                                "description": inp.get("description") or "", "at": now})
    elif name == "SubagentStart":
        aid, kind = event.get("agent_id"), event.get("agent_type") or ""
        if not aid or not kind:
            return  # agentes internos (sugestões, /btw) não entram no círculo
        desc = ""
        for i, p in enumerate(data["pending"]):
            if p.get("type") == kind:
                desc = data["pending"].pop(i).get("description", "")
                break
        prev = data["agents"].get(aid, {})
        data["agents"][aid] = {"type": kind, "description": desc or prev.get("description", ""),
                               "since": prev.get("since", now)}
    elif name == "SubagentStop":
        data["agents"].pop(event.get("agent_id"), None)
    elif name == "Stop":
        tasks = event.get("background_tasks") or []
        data["shells"] = [
            {"id": t.get("id"), "description": t.get("description") or "", "command": t.get("command") or "",
             "status": t.get("status")}
            for t in tasks if t.get("type") == "shell" and t.get("status") in ("running", "pending", None)
        ]
    else:
        return

    data["updated"] = now
    save(path, data)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
