# Convenções do núcleo estatístico

Complementa a seção 7 de [SPECIFICATION.md](SPECIFICATION.md). Código em `src/dungeon_drop_analyzer/statistics/`.

## Entrada

`analyze_items` recebe uma matriz masmorras × itens com a contagem de incursões. O denominador de cada
masmorra (`n_d`) é a soma da linha, ou seja, inclui incursões que resultaram em outros itens.

## Resultados por item

| Campo | Significado |
|---|---|
| `proportions` | por masmorra: `x`, `n`, proporção, intervalo de Wilson 95% e sinalização de amostra insuficiente |
| `global_test` | teste de igualdade das proporções em tabela 5×2 (obtido / não obtido) |
| `p_holm_across_items` | Holm aplicado sobre os testes globais de todos os itens |
| `pairwise` | comparações entre pares de masmorras; Holm aplicado dentro da família do item |
| `effects` | chave `(a, b)`: efeito de `a` em relação a `b` |

## Tamanhos de efeito

- `diff_pp`: `(p_a − p_b)` em pontos percentuais.
- `ratio`: `p_a / p_b`; `None` quando `p_b = 0` ou há denominador nulo.
- `odds_ratio` com IC de Wald no logaritmo; se alguma célula for zero, aplica-se Haldane-Anscombe (+0,5 em todas
  as células) e `odds_ratio_corrected` fica `True`.
- Nenhum valor infinito é produzido; o motivo fica em `notes`.

## Teste de homogeneidade

- Linhas (masmorras sem incursões) e colunas (itens nunca obtidos) totalmente nulas são removidas antes do teste.
- Método `auto`: qui-quadrado se esperadas mínimas ≥ 1 e no máximo 20% das células com esperada < 5 (Cochran);
  caso contrário, Monte Carlo com marginais fixas (tabelas aleatórias de Patefield, `scipy.stats.random_table`,
  vetorizado: 10.000 simulações levam milissegundos).
- Monte Carlo: `p = (extremos + 1) / (n_sim + 1)`; o resultado informa `n_sim` (padrão 10.000) e `seed`
  (padrão 12345).
- Tabela com menos de 2 linhas ou 2 colunas efetivas devolve método `indefinido` com `p_value = None`.
- Pareado: qui-quadrado sem correção ou Fisher exato 2×2, pelo mesmo critério; pares indefinidos ficam sem
  valor-p e fora da correção de Holm.

## Amostra insuficiente

O limite padrão de 50 incursões por masmorra (`DEFAULT_MIN_PER_DUNGEON`) é apenas sinalização de piloto e não
garante poder estatístico (especificação, seção 7.8). É configurável via `min_n`.

## Tendência por dificuldade (exploratória)

`trend_test(x, n, scores)` implementa o teste de Cochran-Armitage bilateral: `T = Σ s_i (x_i − n_i p̄)` e
`Var = p̄ (1 − p̄) [Σ n_i s_i² − (Σ n_i s_i)² / N]`, com `z = T / √Var` e `p = 2 · P(Z > |z|)`. Grupos sem
observações são descartados; é indefinido com menos de dois grupos, escores todos iguais ou item ausente/presente
em todas as incursões. O teste é validado contra o exemplo clássico de Agresti (Z² ≈ 6,6; p ≈ 0,01) e é invariante
a mudança de escala dos escores. É apenas exploratório: não indica causalidade, pois masmorra e dificuldade estão
confundidas.

## Camada de serviço (`AnalyticsService`)

- `dashboard(filtro)`: totais, incursões por masmorra, itens distintos obtidos, distribuição dos itens, mais e
  menos frequentes (com empates), contagens por categoria e por masmorra × item e a evolução acumulada por dia
  (data local). Itens inativos só aparecem se tiverem obtenções. O "menos frequente" considera os itens ativos do
  catálogo e pode ser zero (nunca obtido).
- `analyze(filtro, min_n, n_sim, seed, alpha)`: usa apenas masmorras com incursões e itens obtidos pelo menos uma
  vez (as demais linhas e colunas são nulas). Devolve o teste da distribuição completa, a análise de cada item, os
  níveis de dificuldade (masmorras de mesmo nível são somadas) e a tendência por item com Holm entre itens.
  Retorna relatório não analisável com menos de duas masmorras com dados.
- `interpret(p, alpha)`: texto padrão ("Foi detectada diferença estatisticamente significativa..." ou "Não foi
  detectada diferença estatisticamente significativa. Isso não prova que as distribuições sejam iguais.") e
  mensagem de teste indefinido. A decisão sobre cada item usa o valor-p ajustado por Holm entre itens.
- `LIMITATION_NOTES`: confusão masmorra × dificuldade, hipótese de independência e não significância não prova
  igualdade; exibidas na página de análise.

## Disponibilidade do item por masmorra

Cada item é obtido apenas nas masmorras cadastradas para ele (`D_i`; ver [PERSISTENCE.md](PERSISTENCE.md)). Onde
o item não pode cair, a proporção é um zero estrutural e não uma observação; incluí-lo faria qualquer item
exclusivo de uma masmorra parecer "diferente" por construção. As regras, implementadas em `analyze_items(...,
availability=...)` e `AnalyticsService`:

- **Denominador:** continua sendo o total de incursões da masmorra (`n_d`), inclusive as de outros itens.
- **Teste por item:** tabela K×2 apenas com as masmorras de `D_i` presentes na amostra. Com uma só masmorra o teste
  é `indefinido` (sem comparação), mas proporção e intervalo de Wilson continuam sendo calculados.
- **Comparações pareadas, tamanhos de efeito e Holm por família:** somente entre pares de `D_i`.
- **Holm entre itens:** a família contém apenas os itens com teste definido.
- **Distribuição completa:** teste de homogeneidade restrito aos itens disponíveis em todas as masmorras analisadas
  (distribuição condicional a eles; o resultado informa quantos itens entraram). Sem itens comuns, `indefinido`.
- **Tendência por dificuldade:** para cada item, só entram os níveis em que ele pode ser obtido, e `n` do nível soma
  apenas as masmorras de `D_i` naquele nível.
- **Itens sem masmorras definidas** (cadastro anterior ao campo) são tratados como disponíveis em todas, com aviso.
- **Incursões inconsistentes** (item registrado em masmorra fora de `D_i`, por exemplo porque o cadastro do item foi
  alterado depois) são excluídas da análise daquele item, continuam contando no `n` da masmorra e são listadas em
  um aviso. O serviço impede remover uma masmorra do item enquanto houver incursões dele nela, e impede registrar
  novas incursões fora de `D_i`.

`ItemAnalysis.dungeons` lista as masmorras consideradas em cada item, e `AnalysisReport` expõe a matriz de
disponibilidade, os itens comuns, os itens sem masmorras definidas e as incursões inconsistentes.
