# Exportações, backup e restauração

Complementa as seções RF-09, RF-10 e 11 de [SPECIFICATION.md](SPECIFICATION.md). Código em
`src/dungeon_drop_analyzer/reports/` e `services/backup.py`.

## Exportações

Todas respeitam o filtro escolhido (período, masmorra, item, dificuldade, bônus, evento e versão) e registram a
data/hora da exportação (coluna `exportado_em`, e linha "Exportado em" no resumo do XLSX). Sem incursões, os
arquivos saem só com o cabeçalho.

| Arquivo | Conteúdo |
|---|---|
| Histórico (CSV) | uma linha por incursão, do mais antigo ao mais recente: id, data/hora local e UTC, masmorra, dificuldade, item, categoria, duração, versão, bônus, evento e observações |
| Frequências e proporções (CSV) | por masmorra × item: obtenções, incursões da masmorra, proporção, IC de Wilson 95% e sinalização de amostra insuficiente |
| Resultados estatísticos (CSV) | distribuição completa, testes globais por item, comparações pareadas (com diferença em p.p., razão e odds ratio com IC), tendência por dificuldade; sempre com método, amostra, estatística, graus de liberdade, valor-p bruto e ajustado (Holm), família do ajuste, simulações, semente, interpretação e notas |
| Relatório consolidado (XLSX) | abas Resumo (versão, data/hora, amostra, filtros, parâmetros e limitações), Histórico, Frequências, Resultados estatísticos, Distribuição observada e Distribuição esperada |

Formato dos CSV, pensado para abrir corretamente no Excel em português: separador `;`, vírgula decimal e UTF-8 com
BOM. No XLSX os números são numéricos (proporções e intervalos em formato percentual, valores-p com quatro casas),
com cabeçalho em negrito, primeira linha congelada e colunas ajustadas.

Erros de gravação (pasta inválida, arquivo aberto em outro programa) viram `ExportError` com mensagem em português.

## Backup

`BackupService.create_backup(destino, overwrite=False)` usa a API de backup online do SQLite, que gera uma cópia
consistente mesmo com o banco em uso. A cópia é feita em arquivo temporário na pasta de destino, validada e só então
substitui o destino; uma falha nunca destrói um backup existente. Recusa sobrescrever sem `overwrite=True` (a
interface já pergunta pela seletora de arquivo). Nome padrão: `dda-backup-AAAAMMDD-HHMMSS.db` em `backups/`.

## Validação

`validate_backup(caminho)` abre o arquivo somente leitura e exige: arquivo existente e não vazio, banco SQLite
válido, `PRAGMA integrity_check` = ok, tabelas do DDA presentes (`dungeons`, `items`, `runs`, `audit_log`,
`alembic_version`), versão do esquema conhecida (backups de versão desconhecida ou mais nova são recusados) e
`PRAGMA foreign_key_check` vazio. Devolve contagens (masmorras, itens, incursões), a versão do esquema e se precisa
de atualização.

## Restauração

1. Valida o backup.
2. Copia o backup para um arquivo temporário e, se o esquema for antigo, atualiza-o com as migrações; qualquer
   falha aqui (por exemplo, itens sem categoria ao subir para a `0003`) aborta sem tocar nos dados atuais.
3. Cria uma cópia de segurança dos dados atuais (`pre-restore-AAAAMMDD-HHMMSS.db`, em `backups/`).
4. Copia o backup validado para o banco em uso pela API de backup do SQLite; se falhar, volta a cópia de
   segurança.

A interface mostra o conteúdo do backup e exige confirmação explícita antes de sobrescrever. Os serviços
continuam funcionando sem reiniciar; as páginas se atualizam ao serem abertas.

## Diretório de dados

A página de configurações permite escolher outro diretório (efetivo na próxima inicialização, sem mover os dados:
use backup e restauração para levá-los) ou voltar ao padrão. Prioridade e arquivo de configuração em
[PERSISTENCE.md](PERSISTENCE.md).
