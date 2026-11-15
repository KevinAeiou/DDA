# Plano de Implementação — Dungeon Drop Analyzer

Derivado de [SPECIFICATION.md](SPECIFICATION.md). Regras: uma fase por vez; testes antes ou junto das
funcionalidades; não avançar se os critérios da fase anterior falharem; ao final de cada fase relatar decisões,
arquivos, testes, critérios e pendências.

Legenda: ☐ pendente · ☑ concluído

## Fase 0 — Fundação do repositório ☑

- Estrutura de diretórios e pacote `dungeon_drop_analyzer`.
- `pyproject.toml`, venv `.venv`, `requirements-lock.txt`, `.gitignore`, `.editorconfig`.
- README, plano de implementação, teste de fumaça.

**Saída:** venv criada, dependências instaladas, `pytest` passa.

## Fase 1 — Núcleo estatístico (funções puras) ☑

Primeiro por ser o maior risco técnico e independente de UI/banco (RF-06, RF-07, seção 7).

- Proporção e intervalo de Wilson 95%.
- Qui-quadrado de homogeneidade com inspeção das frequências esperadas.
- Alternativa exata/Monte Carlo para tabelas R×C esparsas, com nº de simulações e semente reportados.
- Teste por item (tabela 5×2), comparações pareadas, correção de Holm (por família).
- Diferença em p.p., razão de proporções/odds ratio com tratamento de zeros.
- Sinalização de amostra insuficiente.

**Decisões (Fase 1):**
- Pacote `statistics/`: `proportions` (Wilson), `homogeneity` (qui-quadrado/Monte Carlo/pareado), `multiplicity`
  (Holm), `effects` (p.p., razão, odds ratio) e `analysis` (orquestração por item).
- Critério de escolha do método: qui-quadrado se esperadas mín ≥ 1 e ≤ 20% das células < 5 (Cochran); caso
  contrário, Monte Carlo por permutação com marginais fixas (padrão 10.000 simulações, semente 12345, ambos
  reportados). Pareado: qui-quadrado sem correção ou Fisher exato 2×2 pelo mesmo critério.
- Linhas/colunas totalmente nulas são removidas; tabela degenerada devolve método `indefinido` (p = None).
- Holm aplicado em duas famílias distintas: pareadas dentro de cada item, e testes globais entre itens.
- Zeros: razão indefinida vira `None` com nota; odds ratio usa Haldane-Anscombe (+0,5) com aviso.
- Limite piloto de 50 incursões/masmorra é apenas sinalização, configurável (`min_n`).
- Tendência ordinal por dificuldade (RF-08): implementada na Fase 4 (`trend_test`).

**Saída (critérios 6–9):** testes contra valores de referência (SciPy/statsmodels e cálculos manuais), fixtures
sintéticas identificadas, nenhuma dependência de UI ou banco.

## Fase 2 — Persistência e domínio ☑

- Modelos ORM: `dungeons`, `items`, `runs`, `audit_log` (seção 8).
- Alembic com migração inicial; SQLite com foreign keys habilitadas; índices em `completed_at`, `dungeon_id`,
  `item_id`; sem cascata em registros referenciados.
- Repositórios e serviços: CRUD de masmorras/itens (inativação), registro de incursão em transação, histórico
  com filtros, edição/exclusão com auditoria.
- Banco no diretório de dados do usuário (caminho configurável), logging rotativo.

Decisões e convenções: [PERSISTENCE.md](PERSISTENCE.md). Inclui as categorias padrão de itens (migrações
`0002` e `0003`), adicionadas após a Fase 3.

**Saída (critérios 2–5):** testes de integração com SQLite temporário; persistência após reabertura; filtros
corretos; validações (1 item por incursão, duração ≥ 0, dificuldade 1–5, nomes únicos).

## Fase 3 — Interface base e coleta ☑

- Janela principal PySide6 em pt-BR, menu (seção 10).
- Páginas: Masmorras, Itens, Registrar incursão (poucos cliques, opcionais recolhidos), Histórico com filtros.

Decisões e convenções: [UI.md](UI.md).

**Saída:** fluxo completo de cadastro → registro → histórico, com feedback de sucesso/erro.

## Fase 4 — Dashboard e análise estatística na UI ☑

- Dashboard (RF-05): totais, distribuição, mais/menos frequentes com empates, evolução temporal, tamanho da
  amostra, respeito a filtros.
- Análise individual de item e visão global (RF-06/07), dificuldade/tendência ordinal exploratória (RF-08).
- Avisos de limitação: confusão masmorra×dificuldade, hipótese de independência, "não foi detectada diferença
  estatisticamente significativa".

Decisões e convenções: [STATISTICS.md](STATISTICS.md) (serviço de análise e tendência) e [UI.md](UI.md).
Matplotlib foi escolhido para os gráficos (já previsto na especificação). O Monte Carlo passou a usar tabelas de
Patefield vetorizadas para que a análise por item na interface seja instantânea.

**Saída (critérios 8, 10 na UI):** resultados da UI conferem com o núcleo estatístico.

## Fase 5 — Exportação, backup e restauração ☐

- CSV (histórico, frequências) e XLSX consolidado com método, amostra, valor-p, filtros e data/hora.
- Backup manual consistente, validação antes de restaurar, confirmação antes de sobrescrever.

**Saída (critérios 11–12):** arquivos abrem corretamente; backup/restauração testados.

## Fase 6 — Empacotamento e validação final ☐

- Executável com PyInstaller; banco fora da pasta do executável; funcionamento offline.
- Teste em ambiente Windows limpo; documentação de instalação e uso.

**Saída (critérios 1, 13):** executável validado; todos os critérios de aceitação (seção 12) revisados.

## Futuro (fora do MVP)

Estimativa de tamanho amostral/poder após piloto (seção 7.8), TOST com margem predefinida, análise sequencial.

## Riscos e pontos de atenção

- Python 3.11 em uso vs. 3.12 da especificação — revalidar ao migrar.
- Masmorra e dificuldade confundidas: sem inferência causal.
- Independência entre incursões é hipótese (pity, eventos, bônus, versões).
- Muitos testes simultâneos: Holm obrigatório (bruto e ajustado).
- Tamanho do executável PyInstaller com PySide6/SciPy/pandas.
