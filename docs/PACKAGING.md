# Empacotamento

Complementa a seção 6 de [SPECIFICATION.md](SPECIFICATION.md) (empacotamento em executável) e a Fase 6 do
[plano](IMPLEMENTATION_PLAN.md). Instruções para o usuário final: [USER_GUIDE.md](USER_GUIDE.md).

## Gerar o executável

Pré-requisito: venv criada com `.\scripts\setup_venv.ps1` (instala o PyInstaller como dependência de
desenvolvimento).

```powershell
.\scripts\build_exe.ps1
```

O script executa o PyInstaller com `packaging/dda.spec`, roda a autoverificação no executável gerado (falha se
qualquer etapa falhar) e cria `dist\DungeonDropAnalyzer-<versão>-win64.zip`. Saídas: `dist\DungeonDropAnalyzer\`
(pasta com o `.exe` e `_internal\`), o zip e `dist\self-check.json`. `build/` e `dist/` não são versionados.

Medidas da primeira geração (Windows 11, Python 3.11.9, PySide6 6.12.0): cerca de 3,5 minutos de build, pasta de
271 MB e zip de 116,5 MB.

## Decisões

- **Modo pasta (`onedir`)** e janela sem console: inicia mais rápido que um arquivo único e não extrai nada para
  pastas temporárias a cada execução (o banco nunca fica em pasta temporária do executável).
- **Migrações como dados:** o Alembic carrega os scripts de migração do disco, então `migrations/` é copiado para
  `_internal\dungeon_drop_analyzer\migrations` (sem `__pycache__`).
- **Importações ocultas:** submódulos do Alembic, dialeto SQLite do SQLAlchemy, backend `qtagg` do Matplotlib e o
  gravador do openpyxl.
- **Exclusões:** `statsmodels` (usado só nos testes como referência numérica, não é importado pelo aplicativo),
  `pytest`, `tkinter`, IPython/Jupyter e módulos Qt não usados (WebEngine, Qml, Quick, 3D, Multimedia, Charts,
  DataVisualization).
- **Dados fora do executável:** o banco, os logs, os backups e as exportações ficam em
  `%LOCALAPPDATA%\DungeonDropAnalyzer` (ou no diretório escolhido), nunca na pasta do programa; a autoverificação
  falha se o banco ficar dentro dela. Desinstalar é apagar a pasta do programa.
- **Sem dependência externa em tempo de execução:** nenhum serviço de rede é usado.

## Autoverificação

`DungeonDropAnalyzer.exe --self-check [--output arquivo.json]` (também `python -m dungeon_drop_analyzer
--self-check`) exercita o aplicativo de ponta a ponta em um diretório temporário, sem tocar nos dados do usuário:
bibliotecas, banco e migrações, cadastros e incursões, dashboard e análise, as quatro exportações, backup e
restauração, e a interface (Qt em modo offscreen: renderiza as oito páginas e desenha os gráficos). Como o
executável não tem console, o resultado vai para o JSON; o código de saída é 0 em sucesso e 1 em falha. O código
está em `selfcheck.py` e é coberto por testes. `--version` mostra a versão.

## Validação realizada

Executável gerado e testado a partir de uma cópia extraída do zip em uma pasta com espaço no nome, com diretório
de trabalho diferente e ambiente mínimo (somente `System32` no `PATH`, sem Python, sem a venv):

- `--version` e autoverificação completa: sucesso nas 7 etapas, com `frozen: true`.
- Interface real (sem offscreen): janela "Dungeon Drop Analyzer" aberta, banco criado no perfil do usuário e log
  gravado; nenhum arquivo `.db` dentro da pasta do executável.
- Primeira abertura leva cerca de 8 s (partida a frio de uma pasta grande, com SciPy, pandas e Matplotlib).

## Limitações conhecidas

- **Ambiente limpo:** o teste acima simula isolamento, mas rodou na mesma máquina de desenvolvimento (Windows 11).
  O critério 13 da especificação ainda pede um teste em outra máquina ou VM Windows sem ambiente de desenvolvimento,
  de preferência também no Windows 10. Isso precisa ser feito por quem tiver esse ambiente.
- **Versão mínima do Windows:** não validada além do Windows 11. O Qt 6 e o Python 3.11 miram Windows 10 ou
  superior (64 bits); trate isso como a expectativa até haver teste.
- **Sem assinatura digital:** o Windows SmartScreen e alguns antivírus podem alertar sobre o executável.
- **Sem metadados de versão do Windows** no `.exe` (o ícone existe; veja a seção abaixo).
- **Tamanho e partida:** o pacote é grande e a primeira abertura é lenta; reduzir exigiria importações sob demanda
  das bibliotecas científicas.
- **Dados reais:** a restauração e a troca de diretório já funcionam, mas a primeira instalação deve ser
  acompanhada de um backup antes de atualizar para versões futuras do aplicativo.

## Ícone

- Fontes em `src/dungeon_drop_analyzer/resources/`: `icon.svg` (256, 128, 64 e 48 px), `icon-medio.svg` (32 e 24 px) e
  `icon-pequeno.svg` (16 px). Os tamanhos pequenos têm menos detalhes para continuar legíveis.
- `python scripts/build_icon.py` renderiza os SVGs com o Qt e gera `icon.ico` (multitamanho, PNG embutido) e os
  `icon-16.png`, `icon-32.png` e `icon-256.png`. Rode-o ao alterar um SVG e versione os arquivos gerados.
- O `.ico` é o ícone do `.exe` (`icon=` em `packaging/dda.spec`); os PNGs são usados pela janela
  (`ui/app_icon.py`, aplicado em `QApplication.setWindowIcon`). A pasta `resources` vai para o pacote sem os SVGs.
- No Windows, `SetCurrentProcessExplicitAppUserModelID` agrupa a janela sob o ícone do aplicativo na barra de tarefas.
- A autoverificação confere que o ícone carrega. O desenho é o conceito "Portal de barras": arco de porta, cinco barras
  (uma por masmorra) e uma destacada com barra de erro.
