# 24: Contas desativadas preservadas nos históricos (P0)

**What to build:** relatório anual, memória de cálculo e PDF incluem contas DESATIVADAS que tiveram atividade no ano-calendário (eventos ativos, posição de abertura ou saldo) — desativar uma conta não pode apagar o passado fiscal dela do relatório do ano em que ela operou. Formulários de entrada continuam listando só contas ativas (nada novo entra em conta desativada).

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Relatório anual (HTML/PDF) inclui conta desativada com atividade no ano-calendário (caixa, custódia, rendimentos)
- [x] Memória de cálculo inclui a conta desativada com atividade no ano
- [x] Formulários de lançamento/saldo continuam restringidos a contas ativas
- [x] Regressão: conta com eventos em 2026 desativada após o fechamento → relatório 2026 continua exibindo seus valores (falha no código atual — some do relatório)