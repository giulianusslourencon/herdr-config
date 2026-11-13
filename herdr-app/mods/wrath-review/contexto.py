#!/usr/bin/env python3
"""Propósito de um tomo alterado, para o Julgamento do Mago.

Uso: python3 contexto.py <raiz-do-repositório> <caminho-relativo>

Percorre os registros das sessões do Claude Code dos últimos 14 dias
(~/.claude/projects/*/*.jsonl e subagents/) que mencionam o tomo e, para cada
edição feita depois do último selo dele, recolhe:

  - o pedido: a última mensagem do Mestre (ou, num subagente, a tarefa que o
    sandestin-mestre lhe deu) antes da edição;
  - a intenção: o último texto do sandestin antes da edição;
  - o comando, quando a edição foi por encantamento de terminal;
  - o relato: o primeiro texto do sandestin depois da última edição;
  - o plano: o último plano aprovado (ExitPlanMode) da sessão, se houver.

Devolve JSON. Só lê; não escreve nada.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ordem import TOOLS, WRITES, tomes, transcripts  # noqa: E402

LIMIT = {"prompt": 1500, "why": 900, "report": 1200, "plan": 6000, "cmd": 300}


def cut(text, n):
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def sealed_at(root, rel):
    r = subprocess.run(["git", "--no-optional-locks", "-C", root, "log", "-1", "--format=%ct", "--", rel],
                       capture_output=True, text=True)
    t = r.stdout.strip()
    return datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") if t else ""


def user_text(d):
    """The Mestre's own words in a user line (not tool results, not harness notices)."""
    c = (d.get("message") or {}).get("content")
    if isinstance(c, str):
        texts = [c]
    elif isinstance(c, list):
        texts = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
    else:
        return None
    text = "\n".join(t for t in texts if t).strip()
    if not text or text.startswith("<") or text.startswith("[Request interrupted") or "tool_use_id" in text[:80]:
        return None
    return text


def main():
    root = os.path.realpath(sys.argv[1])
    rel = sys.argv[2]
    full = os.path.join(root, rel)
    since = sealed_at(root, rel)
    names = tomes()
    edits, plans, reports = [], {}, {}
    for path in transcripts():
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if rel.encode() not in data and full.encode() not in data:
            continue
        is_sub = path.parent.name == "subagents"
        prompt, why, plan, last_hit, origin = None, None, None, None, None
        for raw in data.splitlines():
            if b'"type":"user"' not in raw and b'"type":"assistant"' not in raw:
                continue
            try:
                d = json.loads(raw)
            except Exception:
                continue
            kind = d.get("type")
            ts = d.get("timestamp") or ""
            if kind == "user":
                text = user_text(d)
                if text:
                    prompt, why = text, None
                    origin = origin or text
                continue
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text" and c.get("text", "").strip():
                    why = c["text"]
                    if last_hit is not None and last_hit not in reports:
                        reports[last_hit] = c["text"]
                    continue
                if c.get("type") != "tool_use":
                    continue
                inp = c.get("input") or {}
                name = c.get("name")
                if name == "ExitPlanMode" and inp.get("plan"):
                    plan = {"text": inp["plan"], "ts": ts, "session": d.get("sessionId")}
                    continue
                how, cmd = None, None
                if name in TOOLS:
                    target = inp.get("file_path") or inp.get("notebook_path")
                    if target and os.path.realpath(target) == full:
                        how = "edicao"
                elif name == "Bash":
                    command = inp.get("command") or ""
                    cwd = d.get("cwd") or ""
                    if (cwd.startswith(root) or root in command) and WRITES.search(command) and (rel in command or full in command):
                        how, cmd = "terminal", command
                if not how or not ts or (since and ts[:19] <= since):
                    continue
                key = len(edits)
                edits.append({
                    "ts": ts, "how": how, "session": d.get("sessionId"),
                    "tomo": names.get(d.get("sessionId")), "sub": is_sub,
                    "prompt": cut(prompt, LIMIT["prompt"]), "why": cut(why, LIMIT["why"]),
                    "origin": cut(origin, LIMIT["prompt"]),
                    "cmd": cut(cmd, LIMIT["cmd"]) if cmd else None,
                })
                last_hit = key
                if plan:
                    plans[d.get("sessionId")] = plan
        # the report belongs to the last edit of this transcript
    for key, text in reports.items():
        edits[key]["report"] = cut(text, LIMIT["report"])
    edits.sort(key=lambda e: e["ts"])
    plan = None
    if edits:
        p = plans.get(edits[-1]["session"]) or next((plans[s] for s in plans), None)
        if p:
            plan = {"text": cut(p["text"], LIMIT["plan"]), "ts": p["ts"]}
    last_report = next((e.get("report") for e in reversed(edits) if e.get("report")), None)
    origin = edits[0].get("origin") if edits else None
    print(json.dumps({"path": rel, "since": since, "edits": edits, "plan": plan, "report": last_report, "origin": origin},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
