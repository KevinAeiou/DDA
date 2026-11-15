# Guia de instalação e uso

## Instalação (Windows)

1. Extraia o arquivo `DungeonDropAnalyzer-<versão>-win64.zip` em uma pasta de sua preferência (por exemplo,
   `C:\Programas\DungeonDropAnalyzer`). Não é necessário instalar Python nem outros programas.
2. Execute `DungeonDropAnalyzer.exe`, dentro da pasta extraída.
3. O aplicativo funciona sem internet e não envia nenhum dado para fora do computador.

O Windows pode exibir um aviso do SmartScreen na primeira execução, porque o executável não é assinado
digitalmente. Escolha "Mais informações" e "Executar assim mesmo" somente se o arquivo veio de uma fonte confiável.

Para desinstalar, apague a pasta do aplicativo. Seus dados ficam em outra pasta (veja abaixo) e não são apagados.

## Onde ficam seus dados

Por padrão em `%LOCALAPPDATA%\DungeonDropAnalyzer`: banco `dda.db`, `logs\`, `backups\` e `exports\`. Os caminhos
aparecem em **Configurações e backup**, onde também é possível escolher outro diretório (vale após reiniciar; os
dados existentes não são movidos: crie um backup e restaure-o depois).

## Primeiros passos

1. **Masmorras:** cadastre as cinco masmorras com nome e dificuldade de 1 a 5.
2. **Itens:** cadastre o catálogo de itens. Cada item pertence a uma das categorias padrão: armas, armaduras,
   acessórios, relíquias, recursos de amplificação, recursos de artesanato, consumíveis e barras preciosas.
3. **Registrar incursão:** escolha a masmorra e o item recebido e clique em "Salvar incursão". Em "Mais opções" é
   possível ajustar data/hora, duração, versão do jogo, bônus de drop, evento ativo e observações. Cada incursão
   concluída rende exatamente um item.
4. **Histórico:** consulte, filtre, corrija ou exclua incursões. Correções e exclusões ficam registradas na auditoria.

Itens e masmorras não são excluídos; para tirá-los de uso, inative-os (o histórico é preservado).

## Análise

- **Dashboard:** totais, distribuição dos itens, comparação entre masmorras e evolução ao longo do tempo. Os filtros
  valem para toda a página e cada seção mostra o tamanho da amostra (`n`).
- **Análise estatística:** compara as masmorras item a item e na distribuição completa, com intervalo de confiança,
  valor-p bruto e ajustado, método usado e interpretação. A aba de dificuldade é exploratória.

Como interpretar:

- "Não foi detectada diferença estatisticamente significativa" **não prova** que as masmorras sejam iguais.
- Masmorra e dificuldade estão confundidas: uma diferença não prova que a dificuldade, sozinha, a causou.
- Os testes supõem incursões independentes; sistemas de proteção contra azar, recompensas rotativas e bônus
  podem violar essa hipótese. Use os filtros de versão, bônus e evento para separar períodos diferentes.
- Amostras abaixo de 50 incursões por masmorra são sinalizadas como insuficientes (valor de piloto, sem garantia
  de poder estatístico). Evite parar a coleta apenas porque um resultado ficou significativo.

## Relatórios

Em **Relatórios**, exporte o histórico, as frequências e os resultados estatísticos em CSV (abre direto no Excel em
português) ou gere o relatório consolidado em XLSX. As exportações respeitam os filtros e registram a data/hora.

## Backup e restauração

Em **Configurações e backup**:

- **Criar backup:** gera uma cópia consistente do banco no local escolhido (sugestão: pasta `backups`). Faça
  backups com frequência e guarde uma cópia fora do computador.
- **Restaurar backup:** o arquivo é validado e o conteúdo é mostrado para confirmação. Antes de substituir os
  dados atuais, o aplicativo guarda uma cópia de segurança (`pre-restore-...db`) na pasta `backups`.

## Problemas comuns

- **"Não foi possível abrir o banco de dados":** verifique as permissões da pasta de dados e consulte o arquivo
  `logs\dda.log`.
- **Exportação falhou:** feche o arquivo de destino se ele estiver aberto no Excel.
- **Atualização do banco recusada por itens sem categoria:** atribua uma categoria aos itens indicados na mensagem
  e abra o aplicativo novamente.
