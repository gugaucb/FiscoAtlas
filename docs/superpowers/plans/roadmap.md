# Roadmap — atualizado em 2026-08-30

**Decisão (usuário):** NÃO haverá importação de CSV/statement/PDF. Todos os dados
entram manualmente por telas, no ato da operação. Foco exclusivo em investimentos
nos EUA. Antes de implementar qualquer regra tributária, pesquisar a legislação
vigente (Receita Federal) e documentar a fonte no plano/ADR.

## Sequência de planos (revista)

1. **Fundação** — ✅ concluído (commits e3c4e79..beefb13): scaffold, TaxRule,
   PtaxRate/PtaxService, Asset/BrokerAccount.
2. **Eventos + telas de entrada manual** — FinancialEvent (APORTE, BUY, SELL,
   DIVIDEND, JUROS/RENDIMENTO, TAXA, TAX), custo médio, ledger de caixa,
   posições. Telas para lançar cada operação no ato. Único canal de entrada.
3. **Apuração anual** — TaxRuleEngine com a legislação pesquisada (tabela
   progressiva mensal, crédito de imposto pago nos EUA, compensação de
   prejuízos), fechamento por ano, memória de cálculo.
4. **Relatório DIRPF** — PDF com identificação, caixa, bens e direitos,
   rendimentos, ganhos por ativo + telas de consulta por ano/ativo.

## Restrições que valem para todos os planos

- Sem importação de arquivos — entrada 100% manual via telas.
- Escopo: apenas investimentos nos EUA (USD).
- Regras fiscais: pesquisar legislação RFA vigente antes de codificar; marcar
  como `confirmed=False` até validação com contador.
- Dados versionados, nunca apagados (spec §9).
