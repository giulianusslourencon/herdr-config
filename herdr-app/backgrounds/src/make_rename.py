"""Gera mods/wrath-rename-tab e mods/wrath-rename-space a partir de rename_template.js."""
import json
from pathlib import Path
H = Path.home() / ".config/herdr-app"
src = (H / "backgrounds/src/rename_template.js").read_text()
for kind, target, title in [("tab", "aba", "Rebatizar aba"), ("space", "domínio", "Rebatizar domínio")]:
    d = H / f"mods/wrath-rename-{kind}"
    d.mkdir(exist_ok=True)
    (d / "main.js").write_text(src.replace("__KIND__", kind).replace("__TARGET__", target))
    (d / "mod.json").write_text(json.dumps({"place": "none", "title": title, "overlay": {"kind": "dialog", "width": 440}}, ensure_ascii=False) + "\n")
    (d / "jsconfig.json").write_text((H / "mods/wrath-pane/jsconfig.json").read_text())
print("ok")
