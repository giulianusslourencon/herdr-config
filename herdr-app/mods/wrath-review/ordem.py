#!/usr/bin/env python3
"""Ordem de edição dos tomos alterados de um repositório, para o Julgamento do Mago.

Uso: python3 ordem.py <raiz-do-repositório>

Lê `git status` da raiz e procura, nos registros das sessões do Claude Code dos
últimos 14 dias (~/.claude/projects/*/*.jsonl, inclusive subagents/), cada
Edit / Write / MultiEdit / NotebookEdit que tocou um desses arquivos. Devolve,
em JSON e já na ordem da PRIMEIRA edição:

  [{"path": "src/a.ts", "seq": 1, "first": "2026-11-09T14:57:13Z", "last": "...",
    "edits": 3, "session": "20cd22b5…", "tomo": "Estilo do herdr", "source": "edicao" | "terminal"},
   {"path": "x.md", ..., "source": "disco"}]

Arquivos que nenhuma sessão registrou (editados à mão, por um comando de shell,
ou numa sessão mais antiga) vêm depois, pela hora de modificação no disco.
Só lê; não escreve nada.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DAYS = 14
TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# A shell command counts as an edit of a file it names only if it also writes something.
WRITES = re.compile(r"""open\([^)]*['"][wa]\+?['"]|write_text|\.write\(|(?<![<>&0-9])>{1,2}\s*[\w./'"$~-]|sed\s+(-\w*\s+)*-i|perl\s+-\w*i|\btee\b|\b(cp|mv|install)\s|git\s+(apply|checkout|restore|mv)|\bpatch\b|\bedit\(""")


def changed(root):
    r = subprocess.run(["git", "--no-optional-locks", "-C", root, "status", "--porcelain=v1", "-z",
                        "--no-renames", "--untracked-files=all"], capture_output=True, text=True)
    return [e[3:] for e in r.stdout.split("\0") if e]


def sealed_at(root, files):
    """Each file's last commit time (ISO, UTC): edits before it were already sealed and judged."""
    out = {}
    for f in files:
        r = subprocess.run(["git", "--no-optional-locks", "-C", root, "log", "-1", "--format=%ct", "--", f],
                           capture_output=True, text=True)
        t = r.stdout.strip()
        if t:
            out[f] = datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return out


def tomes():
    """session id -> session name, from the Claude statusline ledger (best effort)."""
    try:
        book = json.load(open(Path.home() / ".claude/grimorio/tesouro.json"))
    except Exception:
        return {}
    out = {}
    for day in book.get("dias", {}).values():
        for sid, x in day.get("sessoes", {}).items():
            if x.get("tomo"):
                out[sid] = x["tomo"]
    return out


def transcripts():
    cutoff = time.time() - DAYS * 86400
    base = Path.home() / ".claude/projects"
    for p in base.glob("*/*.jsonl"):
        if p.stat().st_mtime >= cutoff:
            yield p
    for p in base.glob("*/*/subagents/*.jsonl"):
        if p.stat().st_mtime >= cutoff:
            yield p


def main():
    root = os.path.realpath(sys.argv[1])
    files = changed(root)
    wanted = {os.path.join(root, f): f for f in files}
    seen = {}
    since = sealed_at(root, files)
    needle = root.encode()
    for path in transcripts():
        try:
            fh = open(path, "rb")
        except OSError:
            continue
        with fh:
            for raw in fh:
                if b'"tool_use"' not in raw:
                    continue
                if needle not in raw and b'"Bash"' not in raw:
                    continue
                try:
                    d = json.loads(raw)
                except Exception:
                    continue
                content = (d.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                ts = d.get("timestamp") or ""
                if not ts:
                    continue  # without a time it cannot be placed in the order
                cwd = d.get("cwd") or ""
                for c in content:
                    if c.get("type") != "tool_use":
                        continue
                    inp = c.get("input") or {}
                    hits = []
                    if c.get("name") in TOOLS:
                        target = inp.get("file_path") or inp.get("notebook_path")
                        rel = wanted.get(os.path.realpath(target)) if target else None
                        if rel:
                            hits.append((rel, "edicao"))
                    elif c.get("name") == "Bash":
                        cmd = inp.get("command") or ""
                        here = cwd.startswith(root) or root in cmd
                        if here and WRITES.search(cmd):
                            for rel in files:
                                if rel in cmd or os.path.join(root, rel) in cmd:
                                    hits.append((rel, "terminal"))
                    for rel, how in hits:
                        if rel in since and ts[:19] <= since[rel]:
                            continue  # an edit already sealed in a commit
                        s = seen.setdefault(rel, {"first": ts, "last": ts, "edits": 0, "session": d.get("sessionId"), "how": how})
                        s["edits"] += 1
                        if ts and ts < s["first"]:
                            s["first"], s["session"], s["how"] = ts, d.get("sessionId"), how
                        if ts > s["last"]:
                            s["last"] = ts
    names = tomes()
    known = sorted(seen.items(), key=lambda kv: kv[1]["first"])
    rest = []
    for f in files:
        if f in seen:
            continue
        try:
            mt = os.stat(os.path.join(root, f)).st_mtime
        except OSError:
            mt = 0  # deleted on disk: no time left, goes last
        rest.append((f, mt))
    rest.sort(key=lambda x: (x[1] == 0, x[1]))
    out = []
    for rel, s in known:
        out.append({"path": rel, "first": s["first"], "last": s["last"], "edits": s["edits"],
                    "session": s["session"], "tomo": names.get(s["session"]), "source": s["how"]})
    for rel, mt in rest:
        iso = datetime.fromtimestamp(mt, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if mt else None
        out.append({"path": rel, "first": iso, "last": iso, "edits": 0, "session": None, "tomo": None, "source": "disco"})
    for i, x in enumerate(out, 1):
        x["seq"] = i
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
