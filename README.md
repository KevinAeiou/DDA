# Dungeon Drop Analyzer (DDA)

Aplicação desktop, local e offline, para registrar as recompensas obtidas em cinco masmorras e investigar
estatisticamente se a distribuição dos itens difere entre elas.

Cada incursão concluída garante exatamente um item. O catálogo de itens é cadastrado manualmente. O sistema
estima frequências, proporções com intervalo de Wilson de 95%, testes globais e por item (com correção de Holm)
e **não presume** que masmorras mais difíceis dão melhores recompensas — isso é uma hipótese a investigar.

> Status: **Fases 0 a 3 concluídas** (fundação, núcleo estatístico, persistência/domínio e interface de coleta). Dashboard, análise na interface e exportação ainda não existem.

## Documentação

| Documento | Conteúdo |
|---|---|
| [SPECIFICATION.md](docs/SPECIFICATION.md) | Especificação de produto, requisitos, metodologia estatística e modelo de dados |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Plano de implementação por fases, com critérios de saída |
| [STATISTICS.md](docs/STATISTICS.md) | Convenções e decisões do núcleo estatístico |
| [PERSISTENCE.md](docs/PERSISTENCE.md) | Banco, migrações, regras de domínio, filtros e auditoria |
| [UI.md](docs/UI.md) | Interface: páginas, fluxo de registro, histórico e testes |

## Stack

Python · PySide6 · SQLite · SQLAlchemy 2 · Alembic · SciPy · statsmodels · pandas · openpyxl · Matplotlib ·
pytest · PyInstaller. Plataforma inicial: Windows.

A especificação pede Python 3.12 "ou versão estável compatível validada na preparação". O ambiente de
desenvolvimento atual usa **Python 3.11.9**, validado com todas as dependências (`requires-python >= 3.11`).
As versões resolvidas ficam em [`requirements-lock.txt`](requirements-lock.txt).

## Configuração do ambiente

Pré-requisito: Python 3.11+ no PATH.

PowerShell (Windows):

```powershell
.\scripts\setup_venv.ps1
.\.venv\Scripts\Activate.ps1
```

Manual:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

Para reproduzir exatamente as versões validadas: `pip install -r requirements-lock.txt` e depois
`pip install -e . --no-deps`.

## Comandos úteis

```bash
python -m dungeon_drop_analyzer   # abre a aplicação
pytest            # testes
ruff check .      # lint
ruff format .     # formatação
```

## Estrutura

```text
src/dungeon_drop_analyzer/
├── core/          configuração, banco, logs, inicialização
├── models/        entidades e ORM
├── repositories/  consultas e persistência
├── services/      regras e casos de uso
├── statistics/    funções puras de análise (sem UI/banco)
├── reports/       exportações CSV/XLSX
└── ui/            windows, pages, dialogs, widgets
tests/             unit, integration, fixtures (apenas dados sintéticos identificados)
docs/  scripts/  data/
```

Regra de camadas: a UI não contém fórmulas estatísticas nem acessa o banco diretamente.

## Dados

`data/` e arquivos `*.db`/`*.sqlite` estão no `.gitignore`. Nunca versionar dados reais nem inserir dados
sintéticos como se fossem reais; fixtures de teste devem ser claramente sintéticas.

## Decisões em aberto

Nomes das masmorras, confirmação dos níveis 1–5, catálogo de itens, efeito de bônus/eventos, existência de
pity system, versão mínima do Windows e margem de equivalência (TOST). Não bloqueiam infraestrutura,
cadastros e coleta (ver especificação, seção 14).
