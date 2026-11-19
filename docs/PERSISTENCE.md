# Persistência e domínio

Complementa as seções 5, 8 e 11 de [SPECIFICATION.md](SPECIFICATION.md).

## Armazenamento

- Banco SQLite em `dda.db` dentro do diretório de dados do usuário: `%LOCALAPPDATA%\DungeonDropAnalyzer` no
  Windows (ou `~/.local/share/DungeonDropAnalyzer` sem `LOCALAPPDATA`). A variável `DDA_DATA_DIR` ou o argumento
  de `Settings.load(data_dir)` sobrescrevem o caminho. Subpastas: `logs/`, `backups/` e `exports/`.
- Prioridade do diretório de dados: argumento explícito, variável `DDA_DATA_DIR`, escolha salva na interface
  (`config.json` em `%LOCALAPPDATA%\DungeonDropAnalyzer`, que é sempre a pasta fixa de configuração) e, por fim,
  a pasta padrão. A troca vale a partir da próxima inicialização e não move os dados existentes.
- Backup e restauração: ver [REPORTS.md](REPORTS.md).
- `initialize(settings)` cria os diretórios, configura o log rotativo (1 MB × 5 arquivos), abre o banco com
  `PRAGMA foreign_keys=ON` em toda conexão e aplica as migrações até `head`.

## Datas

Todas as datas são gravadas em UTC (coluna sem fuso) e devolvidas com fuso UTC. O tipo `UTCDateTime` recusa
`datetime` sem fuso. Na camada de serviços, datas sem fuso são interpretadas como horário local da máquina e
convertidas. A exibição em formato local fica para a interface.

## Esquema e migrações

- Migração `0001` cria `dungeons`, `items`, `runs` e `audit_log`. Os scripts ficam em
  `src/dungeon_drop_analyzer/migrations/` (dentro do pacote, para o empacotamento) e são executados
  programaticamente por `upgrade_database`/`downgrade_database`.
- Migração `0002`: categorias padrão de itens (ver abaixo). Como o SQLite não adiciona constraints a tabelas
  existentes, ela recria `items`; por isso `upgrade_database`/`downgrade_database` desligam as foreign keys
  durante a migração, executam `PRAGMA foreign_key_check` ao final (falhando se houver violação) e religam.
- Migração `0004`: tabela `item_dungeons` (masmorras em que cada item pode ser obtido). Itens existentes ficam
  sem masmorras até serem editados manualmente (a migração não inventa associações).
- Migração `0003`: categoria de item obrigatória (`NOT NULL` e CHECK sem `NULL`), com a mesma recriação de
  tabela e as mesmas verificações da `0002`.
- Um teste garante que o esquema migrado é idêntico ao definido nos modelos, inclusive após a `0002` aplicada
  sobre dados existentes.
- Constraints têm nomes determinísticos (convenção de nomes no `MetaData`).
- `runs.dungeon_id` e `runs.item_id` usam `ON DELETE RESTRICT`; masmorras e itens nunca são excluídos, apenas
  inativados. Índices em `runs.completed_at`, `runs.dungeon_id`, `runs.item_id`.
- Nomes de masmorras e itens são únicos sem diferenciar maiúsculas de minúsculas (`COLLATE NOCASE`, que só
  cobre letras ASCII; acentos diferentes contam como nomes distintos).
- Dificuldade (1–5), duração (≥ 0) e os estados `yes`/`no`/`unknown` são validados no banco e nos serviços.
- A dificuldade não é única por masmorra, pois a confirmação dos níveis 1–5 é uma decisão em aberto.

## Categorias de itens

Conjunto fixo de oito categorias (armas, armaduras, acessórios, relíquias, recursos de amplificação, recursos de artesanato, consumíveis e barras preciosas), definido por `ItemCategory` em `models/entities.py`, com o
rótulo em português em `ItemCategory.label`. O banco guarda o código (`weapons`, `armor`, `accessories`,
`relics`, `amplification_resources`, `crafting_resources`, `consumables`, `precious_bars`) e uma restrição
CHECK impede qualquer outro valor. A categoria é obrigatória (`NOT NULL`).

`ItemService` aceita o enum ou o código e rejeita ausência, texto vazio e qualquer outro valor com
`ValidationError`. Na migração `0002`, categorias de texto livre existentes são convertidas quando coincidem
com um rótulo padrão (sem diferenciar maiúsculas, plural/singular ou acentuação nos casos previstos); as
demais ficam sem categoria. A migração `0003` torna a coluna obrigatória e, se ainda houver itens sem
categoria, aborta listando os nomes (sem alterar o banco); atribua uma categoria a eles e atualize novamente.
Não havia dados reais antes desta mudança.

## Masmorras do item

Tabela de associação `item_dungeons(item_id, dungeon_id)` com PK composta, FKs `ON DELETE RESTRICT` e índice em
`dungeon_id`. `Item.dungeons` (carregado junto com o item, ordenado por dificuldade e nome) é a lista de masmorras
em que o item pode ser obtido.

- `ItemService.create(nome, categoria, dungeon_ids, ...)` exige ao menos uma masmorra existente (ids repetidos são
  unificados). `update(..., dungeon_ids=[...])` substitui o conjunto; omitir `dungeon_ids` não o altera, então itens
  legados (sem masmorras) ainda podem ser inativados ou renomeados.
- Remover uma masmorra do item é recusado se houver incursões desse item nela.
- A trilha de auditoria do item inclui `dungeon_ids` nos dados antes e depois.
- `RunService.register`/`update` recusam item fora das masmorras dele (mensagem com as masmorras do item). Item sem
  masmorras definidas fica liberado até ser corrigido. Uma correção que não troca masmorra nem item não revalida
  incursões antigas.
- `ItemRepository.dungeon_map()` devolve `item_id → {dungeon_id}`; `RunRepository.count_item_in_dungeon()` apoia a
  regra de remoção.

## Camadas

- `repositories`: consultas e persistência a partir de uma `Session`; nunca confirmam transação.
- `services`: casos de uso; cada operação roda em uma transação (`session_scope`) que confirma ou desfaz tudo,
  incluindo a auditoria. Erros de domínio (`ValidationError`, `NotFoundError`, `DuplicateError`) têm mensagens
  em português para a interface.

## Regras de negócio

- Uma incursão tem exatamente um item (um único `item_id` inteiro; listas são rejeitadas).
- Novas incursões só aceitam masmorras e itens ativos. Itens inativados continuam no histórico e podem permanecer
  em incursões editadas, mas não podem ser selecionados em uma correção.
- Data/hora da conclusão é opcional na chamada e assume o instante atual.

## Histórico e filtros

`RunFilter` combina (E lógico): período (inclusivo), masmorras, itens, dificuldades, bônus, evento e versão do
jogo. A listagem é da incursão mais recente para a mais antiga por padrão (`descending=False` inverte) e aceita
`limit`/`offset`. Uma lista vazia em um filtro (por exemplo `dungeon_ids=[]`) resulta em nenhuma incursão.

## Auditoria

`audit_log` registra criação, atualização e exclusão de masmorras, itens e incursões, na mesma transação da
alteração, com `old_data`/`new_data` em JSON. Atualizações sem mudança real não geram registro nem alteram
`updated_at`. `AuditTrailService.history(tipo, id)` lista a trilha de uma entidade.
