#!/usr/bin/env python3
"""Reaplica o toast traduzido do Wrath sobre o mod `toast` embutido do Herdr.

O Herdr restaura seus mods embutidos a cada início e trata como "editado"
qualquer arquivo cujo hash (FNV-1a 64) difira do registrado em installed.json.
Este script grava toast_template.js em mods/toast/main.js e registra o hash
do arquivo novo, para que o próximo início restaure em silêncio (sem criar
toast-edited) e o wrath-toast.path dispare este script de novo.

Idempotente: se o arquivo já é o patch, não grava nada (evita laço no .path).
Uso: python3 toast_patch.py [--check]
"""
import json
import os
import sys
import tempfile
from pathlib import Path

HOME = Path.home() / ".config/herdr-app"
TARGET = HOME / "mods/toast/main.js"
TEMPLATE = HOME / "backgrounds/src/toast_template.js"
INSTALLED = HOME / "installed.json"
MARK = b"WRATH PATCH"


def fnv1a64(data: bytes) -> str:
    h = 0xCBF29CE484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return format(h, "016x")


def atomic_write(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def main() -> int:
    if not TARGET.exists() or not TEMPLATE.exists():
        print("toast ou template ausente; nada a fazer")
        return 0
    current = TARGET.read_bytes()
    patched = TEMPLATE.read_bytes()
    installed = json.loads(INSTALLED.read_text())
    want = fnv1a64(patched)
    if "--check" in sys.argv:
        print("patch aplicado" if current == patched else "original do Herdr", "| hash registrado:",
              installed.get("toast", {}).get("main.js"), "| hash do patch:", want)
        return 0
    if current == patched and installed.get("toast", {}).get("main.js") == want:
        return 0
    if MARK not in current and b"export default class Toast" not in current:
        print("toast embutido mudou de forma inesperada; não aplico o patch")
        return 1
    atomic_write(TARGET, patched)
    installed.setdefault("toast", {})["main.js"] = want
    atomic_write(INSTALLED, (json.dumps(installed, indent=2) + "\n").encode())
    print("toast traduzido aplicado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
