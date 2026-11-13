#!/usr/bin/env python3
"""Trava do selo: nenhum sandestin sela tomos sem o julgamento do Mestre.

Hook PreToolUse (matcher "Bash") do Claude Code. Se o comando cria um commit
(git commit em qualquer forma: git -C dir commit, git -c k=v commit, --amend,
encadeado com && ou ;, ou npm run commit / git cz), devolve
permissionDecision "ask": o Claude Code para e pede a aprovação do Mestre na
tela, mesmo no modo automático. Qualquer outro comando passa sem resposta.

Nunca bloqueia por erro: se algo falhar aqui, o comando segue o fluxo normal.
"""
import json
import re
import sys

# git [opções globais] commit — opções globais: -C <dir>, -c <k=v>, --flag[=valor]
SEAL = re.compile(
    r"""(?:^|[\s;&|(`$])git(?:\s+(?:-C\s+\S+|-c\s+\S+|--[\w-]+(?:=\S+)?))*\s+commit\b"""
    r"""|(?:^|[\s;&|(`$])(?:npm|pnpm|yarn)\s+(?:run\s+)?commit\b"""
    r"""|(?:^|[\s;&|(`$])git\s+cz\b"""
)

REASON = (
    "Trava do selo: o Mestre ordenou que nenhum sandestin sele tomos por conta própria. "
    "Este comando cria um commit. Antes de aprovar, o Mestre deve julgar as alterações "
    "(botão JULGAR no Espelho das Alterações do Herdr). "
    "Sandestin: se o Mestre recusar, não insista nem contorne; avise que os tomos aguardam o Julgamento."
)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        return
    if event.get("tool_name") != "Bash":
        return
    command = (event.get("tool_input") or {}).get("command") or ""
    if not SEAL.search(command):
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": REASON,
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
