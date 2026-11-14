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
- `pages/`: `RegisterRunPage`, `HistoryPage`, `DungeonsPage`, `ItemsPage`, página de configurações (mostra os
  caminhos de dados) e marcadores para Dashboard, Análise estatística e Relatórios (Fases 4 e 5).
- `dialogs/`: cadastro/edição de masmorras e itens e correção de incursão. Um diálogo só fecha quando o serviço
  aceita os dados; erros de domínio aparecem como aviso e o formulário permanece aberto.
- `widgets/`: `RunForm` (formulário de incursão), formatação em pt-BR e caixas de mensagem.
- A interface só usa `Services`; não contém fórmulas estatísticas nem acessa o banco.

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
tela mostram quadrados no lugar do texto; isso não ocorre na execução normal.

## Armadilha conhecida

Atributos de widgets não devem ter o mesmo nome de métodos do Qt (por exemplo, `event`), pois sobrescrevem o
método e derrubam o processo. Por isso o formulário usa `bonus_combo` e `event_combo`.
