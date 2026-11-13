// Nomes verdadeiros dos sandestins do Círculo.
// Cada um ganha um nome próprio estável (sorteado pelo endereço ou id, sem
// repetir entre os visíveis) e um epíteto que diz sua função, lido da tarefa:
// o título do agente, o tipo e a descrição do subagente, o comando do shell.
// Osherl e Sarsem são sandestins das histórias de Rhialto (Jack Vance);
// os demais nomes são inventados no mesmo som.

const NAMES = [
  "Osherl", "Sarsem", "Zaltzar", "Pheryx", "Ulmaroth", "Vashnae", "Thrumbuld", "Teskeret",
  "Ombrequil", "Saphirel", "Druvanne", "Keltrim", "Ysabrac", "Gorlimax", "Quelvane", "Ixtrove",
  "Marbazen", "Lirrigo", "Fendrasc", "Obbrecht", "Hespiran", "Tolquay", "Vurlitz", "Asmordel",
];

// Ordem importa: a primeira regra que casar vence. Cada regra tem vários epítetos;
// sandestins da mesma função recebem epítetos diferentes (sorteio estável pela chave,
// sem repetir entre os visíveis enquanto houver opção).
const RULES = [
  [/claude-code-guide|docs?\b.*claude|c[oó]dice/i, ["o Sábio do Códice", "o Leitor de Pergaminhos Alheios", "o Intérprete dos Arcanos de Anthropos"]],
  [/\b(jest|vitest|mocha|pytest|spec|tests?|testes?|provas?)\b/i, ["o Provador", "o Ordálio Ambulante", "o Juiz das Provas de Fogo", "o Que Põe à Prova"]],
  [/review|revis|audit|critique|cr[ií]tica|escrut/i, ["o Escrutinador", "o Olho que Não Pisca", "o Pesador de Runas", "o Inquisidor das Linhas"]],
  [/\bplan|planej|design\b(?!.*(css|tema|estilo))|arquitet|\badr\b|estrat/i, ["o Estrategista", "o Arquiteto de Torres Futuras", "o Leitor de Presságios", "o Traçador de Pentáculos"]],
  [/explore|explor|mapear|mapa|search|busca|investig|\bfind\b|grep|varr/i, ["o Cartógrafo", "o Farejador de Tomos", "o Andarilho das Galerias", "o Sondador de Abismos"]],
  [/\bfix|bug|corrig|conserta|erro|debug|falha|quebr/i, ["o Exorcista de Maldições", "o Desfazedor de Pragas", "o Remendador de Encantos", "o Caçador de Diabretes"]],
  [/migra|kratos|transmut|backfill|script/i, ["o Transmutador", "o Transportador de Almas", "o Alquimista de Registros", "o Barqueiro entre Mundos"]],
  [/deploy|release|rollout|\bprod\b|produ[cç][aã]o|runbook/i, ["o Arauto da Torre", "o Erguedor de Torres", "o Mensageiro da Torre Principal", "o Pedreiro das Ameias"]],
  [/keto|tupl|rela[cç]|subject.?set|\bopl\b/i, ["o Tecelão de Laços", "o Fiandeiro das Relações", "o Atador de Nós Invisíveis"]],
  [/role|papel|pap[eé]is|template|perfil|cargo/i, ["o Moldador de Papéis", "o Talhador de Máscaras", "o Mestre das Insígnias"]],
  [/escopo|scope|loja|store|grupo|group|franq|csm|\bcs\b/i, ["o Agrimensor dos Domínios", "o Demarcador de Fronteiras", "o Senhor dos Marcos de Pedra"]],
  [/auth|token|login|senha|identit/i, ["o Porteiro dos Sete Selos", "o Guardião do Limiar", "o Inquiridor de Senhas"]],
  [/perm|acesso|access|\biam\b|grant|concess/i, ["o Guardião das Chaves", "o Distribuidor de Salvo-condutos", "o Chaveiro de Phandaal", "o Senhor das Portas Trancadas", "o Concedente de Licenças"]],
  [/estilo|tema|theme|visual|\bcss\b|\bui\b|interface|herdr|layout|[ií]cone|som|sound/i, ["o Iluminador", "o Pintor de Iluminuras", "o Ourives de Interfaces", "o Encantador de Vitrais"]],
  [/\bdocs?\b|readme|escrev|write|relat[oó]rio|ata\b|notas/i, ["o Escriba", "o Copista Insone", "o Guardião da Pena"]],
  [/\btsc\b|build|compil|lint|biome|knip/i, ["o Ferreiro", "o Fundidor de Runas", "o Martelo da Forja"]],
  [/\bdev\b|serve|server|watch|vigi/i, ["o Vigia da Forja", "o Sentinela das Brasas", "o Que Não Dorme"]],
  [/\bgit\b|commit|\bpr\b|merge|branch|rebase|selar/i, ["o Selador", "o Lacrador de Tomos", "o Fundidor de Ramos"]],
  [/general-purpose/i, ["o Servo de Muitas Mãos", "o Faz-Tudo do Mago", "o Servo Multiforme"]],
  [/status|resumo|summary|[uú]ltima/i, ["o Cronista", "o Contador de Eras", "o Memorialista"]],
];

const DEFAULT = { agent: "o Servidor do Mago", subagente: "o Servo de Muitas Mãos", encantamento: "o Encantamento Errante",
  "sandestin menor": "o Mensageiro" };

function hash(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

/** Strips the spinner/status glyphs agents put in front of terminal titles. */
export function cleanTask(text) {
  return (text ?? "").replace(/^[^\p{L}\p{N}~/]+/u, "").trim();
}

/** The epithet options for a task: the first matching rule's list, or the default. */
function epithets(kind, texts) {
  const hay = texts.filter(Boolean).join(" · ");
  for (const [rx, titles] of RULES) if (rx.test(hay)) return titles;
  return [DEFAULT[kind] ?? DEFAULT.agent];
}

export function epithet(kind, ...texts) {
  return epithets(kind, texts)[0];
}

/** Gives every entity { key, kind, texts } a distinct proper name and an epithet. */
export function christen(entities) {
  const taken = new Set();
  const titled = new Set();
  const out = new Map();
  for (const e of [...entities].sort((a, b) => (a.key < b.key ? -1 : 1))) {
    let i = hash(e.key) % NAMES.length;
    for (let n = 0; n < NAMES.length && taken.has(NAMES[i]); n++) i = (i + 1) % NAMES.length;
    const proper = NAMES[i];
    taken.add(proper);
    const options = epithets(e.kind, e.texts);
    let j = hash(`${e.key}#t`) % options.length;
    for (let n = 0; n < options.length && titled.has(options[j]); n++) j = (j + 1) % options.length;
    const title = options[j];
    titled.add(title);
    out.set(e.key, { proper, title, full: `${proper}, ${title}` });
  }
  return out;
}
