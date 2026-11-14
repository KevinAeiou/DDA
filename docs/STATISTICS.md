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
  caso contrário, Monte Carlo por permutação com marginais fixas.
- Monte Carlo: `p = (extremos + 1) / (n_sim + 1)`; o resultado informa `n_sim` (padrão 10.000) e `seed`
  (padrão 12345).
- Tabela com menos de 2 linhas ou 2 colunas efetivas devolve método `indefinido` com `p_value = None`.
- Pareado: qui-quadrado sem correção ou Fisher exato 2×2, pelo mesmo critério; pares indefinidos ficam sem
  valor-p e fora da correção de Holm.

## Amostra insuficiente

O limite padrão de 50 incursões por masmorra (`DEFAULT_MIN_PER_DUNGEON`) é apenas sinalização de piloto e não
garante poder estatístico (especificação, seção 7.8). É configurável via `min_n`.
