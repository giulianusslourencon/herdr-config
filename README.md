# herdr-config

Configuração pessoal do [Herdr](https://herdr.dev): layout e tema **Tomo Rubro**, os mods `wrath-*`
e os scripts do Claude Code que conversam com eles (guardião de memória, ressurreição de sessões,
statusline, hooks de subagentes e trava de commit).

## Estrutura

| Pasta | Destino na máquina | Conteúdo |
|---|---|---|
| `herdr-app/` | `~/.config/herdr-app/` | `keys.json`, `settings.json`, `layouts/tomo-rubro.*`, `themes/tomo-rubro.json`, `mods/wrath-*`, `backgrounds/` (arte + geradores em `src/`), `fonts/`, `sounds/` |
| `claude/grimorio/` | `~/.claude/grimorio/` | `guardiao.py`, `ressurreicao.py`, `familiares.py`, `selo.py`, `statusline.py`, `guardiao.json` |
| `claude/output-styles/` | `~/.claude/output-styles/` | output style `Sandestin` |
| `claude/settings.fragment.json` | — (mesclar à mão) | `statusLine` + `hooks` de `~/.claude/settings.json` |
| `systemd/` | `~/.config/systemd/user/` | `guardiao-sandestins`, `ressurreicao-sandestins`, `wrath-toast.{path,service}` |

Fica de fora tudo que o Herdr instala ou regenera (`AGENTS.md`, `*.d.ts`, `frame/`, `icons/`,
mods e layouts embutidos, `installed.json`) e todo estado de runtime (`data/`, `shared.json`,
`view.json`, `window.json`, `telemetry/`, `tesouro.json`, logs, `familiares/`).

## Uso

```sh
./sync.sh export   # máquina → repo; depois revisar com git diff
./sync.sh diff     # o que difere entre repo e máquina
./sync.sh install  # repo → máquina; arquivos sobrescritos ganham backup *.pre-install
```

Depois do `install`, o script imprime os passos manuais:

1. Mesclar `claude/settings.fragment.json` em `~/.claude/settings.json` e definir `"outputStyle": "Sandestin"`.
2. `python3 ~/.config/herdr-app/backgrounds/src/toast_patch.py` (reaplica o toast traduzido sobre o mod embutido).
3. `systemctl --user daemon-reload && systemctl --user enable --now guardiao-sandestins.service ressurreicao-sandestins.service wrath-toast.path`
4. No Herdr, trocar para o layout `tomo-rubro` (`ctrl-shift-l`).

## Dependências

- Herdr app + `herdr-core` (`~/.local/bin/herdr-core`), Python 3, `rsync`, `jq`.
- `wrath-jira`: [`acli`](https://developer.atlassian.com/cloud/acli/) logado (`acli jira auth login --web`); nenhum token fica no repo.
- `wrath-heralds`: `gh` autenticado; os repositórios vigiados vêm de `mods/wrath-heralds/dominios.json` (fora do git — copie `dominios.example.json` e edite).

## Licenças

As fontes em `herdr-app/fonts/` são EB Garamond (SIL Open Font License 1.1).
