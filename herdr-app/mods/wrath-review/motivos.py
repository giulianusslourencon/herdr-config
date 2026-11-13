#!/usr/bin/env python3
"""Motivações das alterações de um domínio inteiro, para o Julgamento do Mago.

Uso:
  python3 motivos.py <raiz>            -> JSON com as motivações agrupadas
  python3 motivos.py <raiz> --guardado -> idem, com o "resumo" só se já estiver guardado
  python3 motivos.py <raiz> --escriba  -> idem, mais "resumo": texto curto escrito
                                          por `claude -p --model haiku` (guardado em
                                          ~/.cache/tomo-rubro/resumos/ pelo conteúdo)

Numa só passada pelos registros das sessões (14 dias), acha cada edição feita
depois do último selo de cada tomo alterado e agrupa os tomos pela ordem do Mestre
que os gerou (a última mensagem antes da primeira edição de cada tomo). Cada grupo
traz a sessão, o pedido que abriu a sessão, o plano aprovado e as intenções que o
sandestin declarou. Tomos sem registro vão em "sem_registro".
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ordem import TOOLS, WRITES, changed, sealed_at, tomes, transcripts  # noqa: E402
from contexto import cut, user_text  # noqa: E402

CACHE = Path.home() / ".cache/tomo-rubro/resumos"


def scan(root, files):
    wanted = {os.path.join(root, f): f for f in files}
    since = sealed_at(root, files)
    first = {}  # rel -> earliest edit record
    sessions = {}  # session -> {origin, plan}
    for path in transcripts():
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if root.encode() not in data and not any(f.encode() in data for f in files[:50]):
            continue
        is_sub = path.parent.name == "subagents"
        prompt = why = origin = plan = None
        for raw in data.splitlines():
            if b'"type":"user"' not in raw and b'"type":"assistant"' not in raw:
                continue
            try:
                d = json.loads(raw)
            except Exception:
                continue
            sid = d.get("sessionId")
            if d.get("type") == "user":
                text = user_text(d)
                if text:
                    prompt, why = text, None
                    origin = origin or text
                continue
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            ts = d.get("timestamp") or ""
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text" and c.get("text", "").strip():
                    why = c["text"]
                    continue
                if c.get("type") != "tool_use":
                    continue
                inp = c.get("input") or {}
                name = c.get("name")
                if name == "ExitPlanMode" and inp.get("plan"):
                    plan = inp["plan"]
                    continue
                hits = []
                if name in TOOLS:
                    target = inp.get("file_path") or inp.get("notebook_path")
                    rel = wanted.get(os.path.realpath(target)) if target else None
                    if rel:
                        hits.append(rel)
                elif name == "Bash":
                    cmd = inp.get("command") or ""
                    cwd = d.get("cwd") or ""
                    if (cwd.startswith(root) or root in cmd) and WRITES.search(cmd):
                        hits += [f for f in files if f in cmd or os.path.join(root, f) in cmd]
                if not ts:
                    continue
                for rel in hits:
                    if rel in since and ts[:19] <= since[rel]:
                        continue
                    rec = first.get(rel)
                    if rec is None or ts < rec["ts"]:
                        first[rel] = {"ts": ts, "session": sid, "prompt": prompt, "why": why, "sub": is_sub}
                    s = sessions.setdefault(sid, {"origin": None, "plan": None, "sub": is_sub})
                    s["origin"] = s["origin"] or origin
                    if plan:
                        s["plan"] = plan
    return first, sessions


def plan_title(plan):
    for line in (plan or "").splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return cut(line, 140)
    return None


def main():
    root = os.path.realpath(sys.argv[1])
    files = changed(root)
    first, sessions = scan(root, files)
    names = tomes()
    groups = {}
    for rel, rec in first.items():
        key = (rec["session"], rec["prompt"] or "")
        g = groups.setdefault(key, {"session": rec["session"], "tomo": names.get(rec["session"]),
                                    "order": cut(rec["prompt"], 900), "sub": rec["sub"], "ts": rec["ts"],
                                    "files": [], "whys": []})
        g["files"].append(rel)
        g["ts"] = min(g["ts"], rec["ts"])
        w = cut(rec["why"], 240)
        if w and w not in g["whys"]:
            g["whys"].append(w)
    out = []
    for g in sorted(groups.values(), key=lambda g: g["ts"]):
        s = sessions.get(g["session"], {})
        g["opened"] = cut(s.get("origin"), 900) if s.get("origin") and s.get("origin") != g["order"] else None
        g["plan"] = plan_title(s.get("plan"))
        g["whys"] = g["whys"][:6]
        out.append(g)
    result = {"root": root, "total": len(files), "motivos": out, "sem_registro": sorted(set(files) - set(first))}
    if "--escriba" in sys.argv or "--guardado" in sys.argv:
        result["resumo"] = escriba(root, result, only_cached="--guardado" in sys.argv)
    print(json.dumps(result, ensure_ascii=False))


def escriba(root, result, only_cached=False):
    lines = [f"Domínio: {os.path.basename(root)} ({result['total']} arquivos alterados, ainda não commitados)."]
    for i, g in enumerate(result["motivos"], 1):
        lines.append(f"\n## Motivação {i}" + (f" (sessão «{g['tomo']}»)" if g.get("tomo") else ""))
        if g.get("opened"):
            lines.append(f"Pedido que abriu a sessão: {g['opened']}")
        lines.append(f"Ordem que gerou as edições: {g['order'] or '(sem texto)'}")
        if g.get("plan"):
            lines.append(f"Plano aprovado: {g['plan']}")
        lines.append("Arquivos: " + ", ".join(g["files"]))
        for w in g["whys"]:
            lines.append(f"- intenção declarada: {w}")
    if result["sem_registro"]:
        lines.append("\nArquivos sem registro de motivação: " + ", ".join(result["sem_registro"]))
    context = "\n".join(lines)
    key = hashlib.sha256(context.encode()).hexdigest()[:24]
    cached = CACHE / f"{key}.txt"
    if cached.exists() and "--novo" not in sys.argv:
        return cached.read_text()
    if only_cached:
        return None
    instruction = (
        "Você recebe o registro das motivações das alterações ainda não commitadas de um repositório. "
        "Escreva em português do Brasil um resumo para quem vai revisar essas alterações: "
        "em até 6 frases curtas, diga o que se pretendia com elas, agrupando por motivação, "
        "citando os arquivos centrais pelo nome e apontando o que o revisor deve conferir. "
        "Não invente nada que não esteja no registro; se algo não tiver motivação registrada, diga isso. "
        "Responda só com o resumo, sem título, sem preâmbulo e sem personagem."
    )
    r = subprocess.run(["claude", "-p", "--model", "haiku", instruction], input=context,
                       capture_output=True, text=True, timeout=180, cwd=os.path.expanduser("~"))
    text = (r.stdout or "").strip()
    if r.returncode != 0 or not text:
        return f"O Escriba não respondeu: {(r.stderr or r.stdout or '').strip()[:300]}"
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(text)
    return text


if __name__ == "__main__":
    main()
