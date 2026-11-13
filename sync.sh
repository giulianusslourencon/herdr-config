#!/usr/bin/env bash
# Sincroniza a configuração pessoal do Herdr (tema Tomo Rubro / mods wrath-*)
# entre este repositório e a máquina.
#
#   ./sync.sh export   máquina → repo (rode antes de commitar)
#   ./sync.sh install  repo → máquina (arquivos sobrescritos ganham backup *.pre-install)
#   ./sync.sh diff     mostra o que difere entre repo e máquina
#
# Só copia o que está na allowlist abaixo. Estado de runtime (data/, shared.json,
# telemetry/, tesouro.json, logs) nunca entra no repo.
set -euo pipefail
shopt -s nullglob

REPO="$(cd "$(dirname "$0")" && pwd)"
HERDR="$HOME/.config/herdr-app"
CLAUDE="$HOME/.claude"
SYSTEMD="$HOME/.config/systemd/user"

# Arquivos e pastas do usuário dentro de ~/.config/herdr-app (relativos).
HERDR_PATHS=(
  keys.json
  settings.json
  layouts/tomo-rubro.json
  layouts/tomo-rubro.svg
  themes/tomo-rubro.json
  backgrounds/
  fonts/
  sounds/
)
SYSTEMD_UNITS=(
  guardiao-sandestins.service
  ressurreicao-sandestins.service
  wrath-toast.path
  wrath-toast.service
)
EXCLUDES=(
  --exclude=__pycache__/ --exclude='*.pyc' --exclude='*.bak-*' --exclude='*.pre-install'
  --exclude=gpui-kit.d.ts --exclude=src/original/
)

mode="${1:-}"
case "$mode" in
  export) RS=(rsync -a "${EXCLUDES[@]}") ;;
  install) RS=(rsync -a --backup --suffix=.pre-install "${EXCLUDES[@]}") ;;
  diff) RS=(rsync -a --dry-run --itemize-changes --checksum "${EXCLUDES[@]}") ;;
  *) sed -n '2,10p' "$0"; exit 1 ;;
esac

# copy <from-root> <to-root> <relative path>
copy() {
  local src="$1/$3" dst="$2/$3"
  [[ -e "$src" ]] || { echo "aviso: ausente $src" >&2; return 0; }
  mkdir -p "$(dirname "$dst")"
  if [[ -d "$src" ]]; then "${RS[@]}" "$src/" "$dst/"; else "${RS[@]}" "$src" "$dst"; fi
}

pairs() { # emite "<lado-máquina> <lado-repo> <path>"
  for p in "${HERDR_PATHS[@]}"; do echo "$HERDR $REPO/herdr-app ${p%/}"; done
  for d in "$HERDR"/mods/wrath-*/ "$REPO"/herdr-app/mods/wrath-*/; do
    echo "$HERDR $REPO/herdr-app mods/$(basename "$d")"
  done | sort -u
  for f in "$CLAUDE"/grimorio/*.py "$REPO"/claude/grimorio/*.py; do
    echo "$CLAUDE $REPO/claude grimorio/$(basename "$f")"
  done | sort -u
  echo "$CLAUDE $REPO/claude grimorio/guardiao.json"
  echo "$CLAUDE $REPO/claude output-styles/sandestin.md"
  for u in "${SYSTEMD_UNITS[@]}"; do echo "$SYSTEMD $REPO/systemd $u"; done
}

while read -r machine repo path; do
  if [[ "$mode" == install ]]; then copy "$repo" "$machine" "$path"; else copy "$machine" "$repo" "$path"; fi
done < <(pairs)

case "$mode" in
  export)
    if [[ -f "$CLAUDE/settings.json" ]]; then
      jq '{statusLine, hooks}' "$CLAUDE/settings.json" > "$REPO/claude/settings.fragment.json"
    fi
    echo "exportado para $REPO — revise com: git -C \"$REPO\" status"
    ;;
  install)
    # gpui-kit.d.ts de cada mod é regravado pelo próprio Herdr ao abrir o mod.
    cat <<MSG
instalado. Passos manuais restantes:
  1. Mesclar claude/settings.fragment.json em ~/.claude/settings.json (statusLine + hooks).
  2. Em ~/.claude/settings.json: "outputStyle": "Sandestin".
  3. python3 ~/.config/herdr-app/backgrounds/src/toast_patch.py
  4. systemctl --user daemon-reload
     systemctl --user enable --now guardiao-sandestins.service ressurreicao-sandestins.service wrath-toast.path
  5. No Herdr: layout.switch {"name":"tomo-rubro"} (ou ctrl-shift-l).
MSG
    ;;
esac
