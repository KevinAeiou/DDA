# Interface

Complementa a seção 10 de [SPECIFICATION.md](SPECIFICATION.md). Código em `src/dungeon_drop_analyzer/ui/`.

## Execução

```bash
python -m dungeon_drop_analyzer
```

O comando `dda` (instalado com o projeto) faz o mesmo sem abrir janela de console no Windows. O banco e os logs
ficam no diretório de dados descrito em [PERSISTENCE.md](PERSISTENCE.md).

## Estrutura

- `app.py`: cria a `QApplication`, define a localidade pt-BR (e carrega as traduções do Qt para botões padrão),
  inicializa o banco e abre a janela. Se o banco não abrir, mostra o caminho e encerra.
- `windows/main_window.py`: menu lateral com as oito entradas da especificação e páginas empilhadas. Cada página
  é recarregada ao ser aberta. Mensagens de sucesso aparecem na barra de status.
- `pages/`: `RegisterRunPage`, `HistoryPage`, `DungeonsPage`, `ItemsPage`, `DashboardPage`, `AnalysisPage`,
  `ReportsPage` e `SettingsPage` (caminhos de dados, diretório configurável, backup e restauração).
- `dialogs/`: cadastro/edição de masmorras e itens e correção de incursão. Um diálogo só fecha quando o serviço
  aceita os dados; erros de domínio aparecem como aviso e o formulário permanece aberto.
- `widgets/`: `FilterPanel` (filtros compartilhados), `charts` (Matplotlib incorporado), `analysis_format`
  (números em pt-BR), `RunForm` (formulário de incursão), `category_combo` (seleção das categorias padrão), formatação
  em pt-BR e caixas de mensagem.
- A interface só usa `Services`; não contém fórmulas estatísticas nem acessa o banco.

## Itens, categorias e masmorras

No cadastro e na edição de item há também a lista **Masmorra(s)** (marcação múltipla, com os botões "Todas" e
"Nenhuma"): ao menos uma é obrigatória. Exemplo: a Esfera de Aprimoramento de Defesa I em todas as masmorras e a
Capa do Mercenário apenas em Minas Abandonadas. A página de itens mostra a coluna Masmorras ("Todas (N)", os
nomes ou "⚠ Não definidas" para itens antigos), filtra por masmorra e avisa quantos itens estão sem definição.

No cadastro e na edição de item, a categoria é escolhida em uma lista com as oito categorias padrão, obrigatória e sem seleção inicial; não há campo de texto livre. A página de itens exibe o rótulo da categoria e permite filtrar
por categoria combinado com o filtro por nome.

## Registro por masmorra

Ao escolher a masmorra, a lista de itens passa a mostrar só os que podem ser obtidos nela (mais os itens ainda sem
masmorras definidas). Sem itens para a masmorra, a página orienta a editar o cadastro do item. O serviço valida de
novo ao salvar.

## Dashboard

Filtros (período, masmorra, item, dificuldade, bônus, evento e versão) valem para toda a página, e cada seção
mostra o tamanho da amostra (`n`). Conteúdo: totais (amostra, itens distintos, masmorras com dados), incursões
por masmorra, distribuição geral dos itens (gráfico dos 15 mais frequentes, tabela completa e texto com o item
mais e o menos frequente, indicando empates e itens nunca obtidos), comparação por masmorra (proporção por
categoria em barras empilhadas e tabela item × masmorra com contagem e percentual) e evolução temporal
(incursões acumuladas por masmorra). Sem dados, os gráficos mostram "Sem dados para exibir". A tabela de itens
mostra as masmorras de cada item, a tabela item × masmorra exibe "—" onde o item não pode ser obtido, e um aviso
lista itens sem masmorras definidas e incursões fora das masmorras do item.

## Análise estatística

Três abas sobre o mesmo relatório, com os filtros da página (sem filtro de item) e as limitações sempre visíveis:

- **Por item:** escolha de um item; proporção, x/n e IC de Wilson 95% por masmorra com sinalização de amostra
  insuficiente; teste global (método, estatística, graus de liberdade, simulações e semente, valor-p bruto e
  ajustado por Holm entre itens, justificativa do método e interpretação); comparações pareadas com valor-p
  bruto e ajustado dentro da família do item, diferença em p.p., razão e odds ratio com IC.
- **Distribuição completa:** tabela masmorras × itens com contagem observada e esperada, teste de homogeneidade,
  método, amostra, simulações e interpretação.
- Em todas as abas, cada item é comparado apenas entre as masmorras em que pode ser obtido ("Masmorras
  consideradas"); a distribuição completa usa só os itens comuns (marcados com `*`) e células indisponíveis
  aparecem como "—". Os mesmos avisos de cadastro aparecem no topo da página.
- **Dificuldade (exploratória):** proporção de cada item por nível e teste de tendência de Cochran-Armitage com
  Holm entre itens, com o aviso de que associação não implica causalidade.

Sem incursões em ao menos duas masmorras, as abas orientam o usuário em vez de exibir resultados.

## Relatórios e configurações

`ReportsPage` tem os filtros da página e quatro botões (histórico CSV, frequências CSV, resultados estatísticos
CSV e relatório consolidado XLSX); cada um pede o arquivo de destino (pasta padrão `exports/`) e informa o
resultado. `SettingsPage` mostra todos os caminhos e oferece criar backup, restaurar backup (com validação,
resumo do conteúdo e confirmação explícita antes de sobrescrever), alterar o diretório de dados e voltar ao
padrão. Detalhes em [REPORTS.md](REPORTS.md). Os seletores de arquivo ficam em `widgets/files.py` e são
substituídos nos testes.

## Registrar incursão

Masmorra e item ficam em destaque; os demais campos (data/hora, duração, versão, bônus, evento e observações)
ficam em "Mais opções", recolhido por padrão. O item pode ser digitado com busca por trecho do nome e precisa
corresponder a um item cadastrado. Após salvar, o item e as observações são limpos, a data/hora volta para o
instante atual e a masmorra permanece selecionada para registros em sequência. Sem masmorras ou itens ativos,
a página orienta o cadastro e desabilita o botão.

## Histórico

Filtros por período (opcionais), masmorra, item, dificuldade, bônus, evento e versão do jogo. A lista mostra
200 incursões por página, da mais recente para a mais antiga, com o total filtrado. "Corrigir" (ou duplo clique)
abre o diálogo de correção e "Excluir" pede confirmação. Ambos geram auditoria.

## Datas

Exibidas no horário local no formato `dd/MM/yyyy HH:mm:ss`. Os campos de data/hora têm precisão de segundos;
na correção, a data só é enviada se foi alterada.

## Testes de interface

`tests/ui/` roda com `QT_QPA_PLATFORM=offscreen` (configurado na fixture `qapp`), sem dependência extra como
pytest-qt. As caixas de mensagem são interceptadas. Em modo offscreen no Windows não há fontes, então capturas de
tela mostram quadrados no lugar do texto dos widgets Qt (os gráficos Matplotlib mostram o texto); isso não ocorre
na execução normal. A fixture `dialogs` intercepta avisos, mensagens, confirmações e seletores de arquivo em todos os módulos da
interface; sem ela,
um `QMessageBox` real bloquearia o teste.

## Armadilha conhecida

Atributos de widgets não devem ter o mesmo nome de métodos do Qt (por exemplo, `event`), pois sobrescrevem o
método e derrubam o processo. Por isso o formulário usa `bonus_combo` e `event_combo`.
