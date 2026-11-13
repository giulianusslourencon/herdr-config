#!/bin/sh
# Vigília de um encantamento: acompanha um workflow do GitHub Actions ao vivo, no terminal.
# Uso: vigia.sh <run-id> <owner/repo>
# Só lê (gh run watch). Ao fim toca o som de concluído ou de falha do Herdr e fecha a
# própria aba (terminal.kill no terminal do Herdr em que roda).
id="$1"; repo="$2"
sounds="$HOME/.config/herdr-app/sounds"
gh run watch "$id" -R "$repo" --interval 5 --exit-status
if [ $? -eq 0 ]; then
  echo; echo "O encantamento se cumpriu."
  pw-play "$sounds/encantamento-cumprido.wav" 2>/dev/null
else
  echo; echo "O encantamento falhou."
  pw-play "$sounds/encantamento-desfeito.wav" 2>/dev/null
fi
[ -n "$HC_TERMINAL_ID" ] && "$HOME/.local/bin/herdr-app" do terminal.kill "{\"terminal\":\"$HC_TERMINAL_ID\"}" >/dev/null 2>&1
