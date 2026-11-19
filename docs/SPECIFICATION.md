# Dungeon Drop Analyzer --- Especificação do Produto e Técnica

**Documento:** SPECIFICATION.md\
**Versão:** 1.0\
**Status:** Especificação inicial do MVP\
**Público:** Desenvolvedor e Claude Code

## 1. Visão geral

O Dungeon Drop Analyzer (DDA) é uma aplicação desktop, local e offline
para registrar recompensas obtidas em cinco masmorras e investigar
estatisticamente se a distribuição dos itens difere entre elas.

O jogador realiza todas as incursões individualmente. Cada incursão
concluída garante exatamente um item. O catálogo completo de itens é
conhecido e cadastrado manualmente.

O objetivo é comparar todos os itens entre as cinco masmorras, estimando
frequências, probabilidades observadas, incerteza e diferenças
estatísticas. O sistema não deve presumir que masmorras mais difíceis
oferecem melhores recompensas: isso é uma hipótese a investigar.

## 2. Objetivos e escopo

### 2.1 Incluído no MVP

-   Cadastrar cinco masmorras com dificuldade ordenada de 1 a 5.
-   Cadastrar manualmente o catálogo de itens.
-   Registrar exatamente um item por incursão concluída.
-   Manter histórico local persistente.
-   Calcular frequências, proporções e intervalos de confiança.
-   Comparar a distribuição geral entre as cinco masmorras.
-   Comparar individualmente cada item entre as cinco masmorras.
-   Sinalizar amostras insuficientes e resultados inconclusivos.
-   Exportar dados e relatórios em CSV/XLSX.
-   Funcionar offline após a instalação.

### 2.2 Fora do MVP

-   Integração com API, memória ou arquivos do jogo.
-   OCR, captura de tela ou reconhecimento automático.
-   Coleta automática de recompensas.
-   Multiusuário ou sincronização em nuvem.
-   Previsão garantida de quando um item cairá.
-   Inferência causal de que a dificuldade isoladamente causa
    diferenças.
-   Automação de jogabilidade.

## 3. Premissas e conceitos

1.  Existem cinco masmorras com dificuldades ordenadas.
2.  O jogador realiza as incursões sozinho.
3.  Cada incursão concluída gera exatamente um item.
4.  A lista de itens possíveis é conhecida; cada item pertence a uma das
    oito categorias padrão (seção 3.1) e pode ser obtido em uma ou mais
    masmorras (seção 3.2).
5.  A seleção do item é manual.
6.  Todos os itens serão analisados individualmente.
7.  Cada incursão concluída é uma unidade de observação.

**Variável explicativa principal:** masmorra.\
**Variável explicativa ordinal:** dificuldade (1--5).\
**Resultado:** item recebido.\
**Variáveis auxiliares:** data/hora, duração, versão do jogo, bônus,
evento e observações.

### 3.1 Categorias padrão de itens

Qualquer masmorra pode fornecer itens de qualquer uma das categorias abaixo. O
usuário apenas seleciona a categoria; não há categorias livres.

| Código | Categoria |
|---|---|
| `weapons` | Armas |
| `armor` | Armaduras |
| `accessories` | Acessórios |
| `relics` | Relíquias |
| `amplification_resources` | Recursos de amplificação |
| `crafting_resources` | Recursos de artesanato |
| `consumables` | Consumíveis |
| `precious_bars` | Barras preciosas |

A categoria é obrigatória no cadastro do item.

### 3.2 Masmorras em que cada item pode ser obtido

Cada item informa em quais masmorras pode ser obtido (campo **Masmorra**,
uma ou mais). Exemplos: a Esfera de Aprimoramento de Defesa I pode ser
obtida em todas as masmorras; a Capa do Mercenário, apenas em Minas
Abandonadas. Consequências:

-   Uma incursão só pode ser registrada com um item disponível na
    masmorra escolhida.
-   Onde o item não pode cair, a proporção é um *zero estrutural* (não
    uma observação de zero). Esses casos não entram nos testes (seções 7.3 a 7.5).
-   Itens cadastrados antes desse campo ficam sem masmorras definidas até
    serem editados manualmente. Enquanto isso, são tratados como
    disponíveis em todas as masmorras e o sistema exibe um aviso.

### Limitações de interpretação

Como cada nível de dificuldade corresponde a uma masmorra específica,
identidade da masmorra e dificuldade estão confundidas. O sistema pode
testar diferenças entre masmorras e explorar tendências associadas à
dificuldade, mas não afirmar que a dificuldade isoladamente causou uma
diferença.

A independência entre incursões é uma hipótese. Sistemas de pity,
proteção contra azar, recompensas rotativas, bônus temporários e
atualizações podem violá-la.

## 4. Fluxo principal

1.  Cadastrar ou revisar as cinco masmorras.
2.  Cadastrar todos os itens conhecidos.
3.  Realizar uma incursão.
4.  Selecionar a masmorra.
5.  Selecionar o único item recebido.
6.  Informar data/hora e, opcionalmente, duração, versão e
    modificadores.
7.  Salvar.
8.  Consultar histórico e dashboard.
9.  Executar análises estatísticas.
10. Exportar dados e relatórios.

## 5. Requisitos funcionais

### RF-01 --- Masmorras

Permitir criar, consultar e editar: - Nome: obrigatório e único. -
Dificuldade: inteiro de 1 a 5. - Descrição: opcional. - Ativa: sim/não.

O MVP deve suportar cinco masmorras sem depender de nomes fixos como
M1--M5.

### RF-02 --- Itens

Permitir criar, consultar, editar e inativar: - Nome: obrigatório e
único. - Categoria: obrigatória, escolhida entre as oito categorias padrão
(seção 3.1). - Masmorra(s): obrigatória, uma ou mais masmorras em que
o item pode ser obtido (seção 3.2). - Descrição: opcional. - Ativo: sim/não.

Masmorras inativas não são oferecidas no cadastro e na edição do item
(vínculos já existentes com elas são preservados). Não remover uma
masmorra do cadastro do item se houver incursões desse item nela.

Itens inativos permanecem associados ao histórico. Não excluir em
cascata itens já utilizados.

### RF-03 --- Registro de incursão

Campos: - Masmorra: obrigatório. - Item obtido: obrigatório. - Data/hora
da conclusão: obrigatório, preenchido automaticamente e editável. -
Duração em segundos: opcional e não negativa. - Versão do jogo:
opcional. - Bônus de drop: sim/não/desconhecido. - Evento ativo:
sim/não/desconhecido. - Observações: opcional.

Regras: - Uma incursão concluída possui exatamente uma recompensa. - Não
salvar incursão concluída sem item. - Não permitir mais de um item na
mesma incursão. - O item deve poder ser obtido na masmorra escolhida
(seção 3.2). - Salvar em transação. - Exibir feedback de sucesso ou
erro.

### RF-04 --- Histórico

Listar registros cronologicamente e filtrar por período, masmorra, item,
dificuldade, bônus/evento e versão do jogo. Permitir corrigir e excluir
registros com auditoria.

### RF-05 --- Dashboard

Exibir: - Total de incursões. - Incursões por masmorra. - Quantidade de
itens distintos obtidos. - Distribuição geral dos itens. - Itens mais e
menos frequentes, indicando empates. - Comparação por masmorra. -
Evolução temporal.

Indicadores e gráficos respeitam filtros e exibem o tamanho da amostra.

### RF-06 --- Análise individual de item

Para cada item: - Obtenções por masmorra. - Total de incursões por
masmorra. - Proporção observada. - Intervalo de confiança de Wilson de
95%. - Teste global de igualdade das cinco proporções. - Comparações
pareadas quando aplicáveis. - Correção de Holm. - Diferença absoluta em
pontos percentuais. - Razão de proporções, tratando denominadores
nulos. - Sinalização de amostra insuficiente.

### RF-07 --- Distribuição completa

Comparar a distribuição categórica dos itens entre as cinco masmorras
usando tabela de contingência 5×K. Informar contagens observadas e
esperadas, estatística, graus de liberdade quando aplicável, valor-p,
método, amostra e interpretação.

### RF-08 --- Dificuldade

Exibir proporções por nível de dificuldade e permitir análise
exploratória de tendência ordinal. Não interpretar associação como
causalidade.

### RF-09 --- Exportação

Exportar: - Histórico bruto CSV. - Frequências e proporções CSV. -
Relatório consolidado XLSX. - Resultados estatísticos com método,
amostra e valor-p.

Respeitar filtros e registrar data/hora da exportação.

### RF-10 --- Persistência e backup

-   SQLite local.
-   Migrações versionadas.
-   Foreign keys habilitadas.
-   Backup manual.
-   Restauração validada.
-   Confirmação antes de sobrescrever dados.

## 6. Requisitos não funcionais

-   Windows como plataforma desktop inicial.
-   Execução offline.
-   Interface em português do Brasil.
-   Datas armazenadas consistentemente e exibidas em formato local.
-   Persistência transacional.
-   Separação entre interface, serviços, repositórios e estatística.
-   Testes automatizados para regras e fórmulas.
-   Logs locais.
-   Empacotamento em executável.
-   Nenhuma dependência de serviço externo em tempo de execução.

## 7. Metodologia estatística

### 7.1 Notação

Para masmorra `d` e item `i`: - `n_d`: total de incursões válidas na
masmorra. - `x_id`: quantidade de vezes que o item `i` foi obtido na
masmorra. - `p_hat(i,d) = x_id / n_d`: proporção observada.

O denominador inclui todas as incursões válidas da masmorra, inclusive
as que resultaram em outros itens. A proporção de um item só é
definida nas masmorras em que ele pode ser obtido (`D_i`, seção 3.2).

### 7.2 Intervalos de confiança

Utilizar intervalo de Wilson de 95% para cada proporção binomial
item/masmorra. Evitar o intervalo normal de Wald. Exibir `x/n`,
proporção e limites do intervalo.

### 7.3 Teste global da distribuição

Hipótese nula: a distribuição dos itens é igual nas cinco masmorras.\
Alternativa: pelo menos uma masmorra possui distribuição diferente.

Usar qui-quadrado de homogeneidade quando as aproximações forem
adequadas. Para tabelas esparsas, usar teste exato de
Fisher-Freeman-Halton ou procedimento Monte Carlo apropriado para tabela
R×C.

Como há itens exclusivos de algumas masmorras, o teste usa apenas os
itens disponíveis em todas as masmorras analisadas (distribuição
condicional a esses itens), evitando que os zeros estruturais
produzam diferenças triviais. Sem itens comuns, o teste é indefinido.

Documentar o critério de escolha. Não aplicar limite simplista sem
inspecionar frequências esperadas. Relatar quantidade de simulações e
semente aleatória para reprodutibilidade.

### 7.4 Teste individual por item

Para cada item, montar tabela K×2 (obtido/não obtido), com uma linha por
masmorra em que o item pode ser obtido (`D_i`), e testar igualdade das
proporções entre elas. Item disponível em uma única masmorra não tem
comparação entre masmorras (teste indefinido; as proporções e os
intervalos continuam sendo exibidos). Usar qui-quadrado quando adequado e alternativa
exata/Monte Carlo quando necessário.

Como vários itens serão testados, ajustar os valores-p dos testes por
item usando Holm. Informar valores-p bruto e ajustado.

### 7.5 Comparações pareadas

Após diferença global por item, comparar pares de masmorras (apenas
entre as de `D_i`) usando teste
de duas proporções ou método exato apropriado. Aplicar Holm dentro da
família de comparações daquele item. Informar claramente a família
ajustada.

### 7.6 Tamanho de efeito

Apresentar diferenças absolutas em pontos percentuais e, quando
apropriado, razão de proporções ou odds ratio com intervalo de
confiança. Tratar células e denominadores zero sem produzir valores
infinitos sem explicação.

### 7.7 Equivalência

Resultado não significativo não prova igualdade. No MVP, apresentar "não
foi detectada diferença estatisticamente significativa". Teste de
equivalência (TOST) é futuro/configurável e exige margem definida antes
de observar os resultados.

### 7.8 Amostra e poder

A sugestão inicial de 50 incursões por masmorra é somente piloto, não
garantia de poder. Após a etapa piloto, estimar tamanho amostral para
diferenças mínimas relevantes, poder de 80% ou 90% e significância
definida. Considerar multiplicidade no planejamento.

Não interromper a coleta por significância intermediária sem plano
sequencial apropriado.

### 7.9 Independência e condições

Permitir filtrar por versão, evento e bônus. Sinalizar períodos
heterogêneos. Se houver pity system, sequência que altere chances ou
recompensas rotativas, a hipótese de tentativas independentes pode ser
inválida e exige análise específica.

## 8. Modelo de dados

### `dungeons`

-   `id`: PK.
-   `name`: texto obrigatório, único.
-   `difficulty`: inteiro 1--5.
-   `description`: opcional.
-   `is_active`: booleano.
-   `created_at`, `updated_at`.

### `items`

-   `id`: PK.
-   `name`: texto obrigatório, único.
-   `category`: obrigatório; um dos códigos da seção 3.1 (NOT NULL e CHECK).
-   `description`: opcional.
-   `is_active`: booleano.
-   `created_at`, `updated_at`.

### `item_dungeons`

-   `item_id`, `dungeon_id`: PK composta; FKs com `ON DELETE RESTRICT`.
-   Associação muitos-para-muitos: masmorras em que o item pode ser
    obtido. Índice em `dungeon_id`.

### `runs`

-   `id`: PK.
-   `dungeon_id`: FK obrigatória.
-   `item_id`: FK obrigatória.
-   `completed_at`: data/hora obrigatória.
-   `duration_seconds`: inteiro opcional, não negativo.
-   `game_version`: texto opcional.
-   `bonus_status`: `yes`, `no`, `unknown`.
-   `event_status`: `yes`, `no`, `unknown`.
-   `notes`: opcional.
-   `created_at`, `updated_at`.

### `audit_log`

-   `id`: PK.
-   `entity_type`, `entity_id`.
-   `action`: criação, atualização ou exclusão.
-   `old_data`, `new_data`: JSON/texto opcional.
-   `changed_at`.

### Integridade

-   Foreign keys habilitadas no SQLite.
-   Não excluir em cascata masmorras/itens referenciados.
-   Índices em `completed_at`, `dungeon_id`, `item_id`.
-   Uma única FK `item_id` em `runs` garante uma recompensa por
    registro.
-   A combinação item × masmorra de uma incursão deve constar em
    `item_dungeons` (validada pelo serviço, não por constraint, para
    preservar histórico anterior ao cadastro das masmorras).
-   Migrações versionadas.

## 9. Arquitetura técnica

### Stack

-   Python 3.12 ou versão estável compatível validada na preparação.
-   PySide6.
-   SQLite.
-   SQLAlchemy 2.
-   Alembic.
-   SciPy.
-   statsmodels.
-   Pandas.
-   openpyxl, se necessário.
-   Matplotlib ou PyQtGraph.
-   pytest.
-   PyInstaller.

Fixar versões após validar compatibilidade.

### Camadas

1.  `ui`: janelas, páginas e componentes.
2.  `services`: regras e casos de uso.
3.  `repositories`: consultas e persistência.
4.  `models`: entidades e ORM.
5.  `statistics`: funções puras de análise.
6.  `reports`: exportações.
7.  `core`: configuração, banco, logs e inicialização.

A interface não contém fórmulas estatísticas nem acessa diretamente o
banco.

### Estrutura sugerida

``` text
dungeon-drop-analyzer/
├── src/dungeon_drop_analyzer/
│   ├── main.py
│   ├── core/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   ├── statistics/
│   ├── ui/
│   │   ├── windows/
│   │   ├── pages/
│   │   ├── dialogs/
│   │   └── widgets/
│   └── reports/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── scripts/
├── data/
├── pyproject.toml
├── README.md
├── IMPLEMENTATION_PLAN.md
└── SPECIFICATION.md
```

## 10. Interface

Menu: - Dashboard. - Registrar incursão. - Histórico. - Masmorras. -
Itens. - Análise estatística. - Relatórios. - Configurações/backup.

O formulário de registro deve priorizar poucos cliques: selecionar
masmorra, selecionar item e confirmar. Campos opcionais podem ficar
recolhidos.

A análise deve permitir selecionar um item e comparar as cinco
masmorras, além de oferecer visão global da distribuição.

## 11. Armazenamento e backup

-   Banco em diretório de dados do usuário, nunca em pasta temporária do
    executável.
-   Caminho configurável e visível.
-   Backup manual consistente.
-   Validação do backup antes da restauração.
-   Confirmação antes de sobrescrever.
-   Sem envio de dados para internet.
-   Log local rotativo.

## 12. Critérios de aceitação

1.  Iniciar sem internet.
2.  Cadastrar cinco masmorras e catálogo de itens.
3.  Registrar uma recompensa por incursão.
4.  Persistir histórico após reiniciar.
5.  Filtrar corretamente.
6.  Frequências e proporções conferirem com referências.
7.  Intervalos de Wilson validados.
8.  Testes globais/individuais selecionarem método adequado.
9.  Correção de Holm validada.
10. Relatórios informarem amostras, métodos e valores-p.
11. CSV/XLSX abrirem corretamente.
12. Backup e restauração testados.
13. Executável testado em ambiente limpo.

## 13. Diretrizes para Claude Code

-   Ler README, SPECIFICATION e IMPLEMENTATION_PLAN antes de alterar.
-   Implementar uma fase por vez.
-   Não inventar taxas de drop nem inserir dados sintéticos como reais.
-   Usar fixtures sintéticas identificadas nos testes.
-   Manter funções estatísticas puras e independentes da UI.
-   Consultar documentação oficial quando houver dúvida de
    API/compatibilidade.
-   Justificar dependências novas.
-   Não introduzir backend web ou nuvem no MVP.
-   Criar testes antes ou junto das funcionalidades.
-   Executar testes após cada fase.
-   Atualizar documentação diante de mudanças.
-   Não avançar se os critérios da fase anterior falharem.
-   Ao final de cada fase, relatar decisões, arquivos, testes, critérios
    e pendências.

## 14. Decisões em aberto

-   Nomes reais das cinco masmorras.
-   Confirmação de níveis exatamente 1--5.
-   Lista completa de itens (as categorias já estão definidas na seção 3.1).
-   Se bônus/eventos alteram o drop.
-   Existência de pity system.
-   Versão mínima do Windows.
-   Margem prática de equivalência, se TOST entrar futuramente.

Essas decisões não impedem iniciar infraestrutura, cadastros e coleta.
