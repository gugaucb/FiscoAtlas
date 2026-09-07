# 03: Filtro rigoroso de jurisdição no crédito de imposto exterior (Parte 3 — P0)

**What to build:** Crédito de imposto exterior só para tributos FEDERAIS de país com reciprocidade (ex.: IRS/EUA). Impostos STATE/LOCAL geram crédito 0 e aparecem segregados no relatório como inelegíveis.

**Requisitos:** RF-FTC-002, RF-FTC-003, RF-FTC-004, RF-VAL-009.
**Branch:** `fix/foreign-tax-federal-filter`.

**Blocked by:** 02 (mesmo arquivo engine; residência antes).
**Status:** resolved

- [x] Dividendo US$100 com tax 30 FEDERAL/US gera crédito aproveitável conforme regra vigente
- [x] jurisdiction_level STATE ou LOCAL → credit_used = 0 e segregado como imposto não elegível no relatório
- [x] País sem reciprocidade/tratado → crédito rejeitado
- [x] report.py expõe ineligible_foreign_tax_brl
- [x] Suíte completa verde

Notas: usa a entidade ForeignTaxPayment (ticket ptax-foreign-tax já entregou estrutura; aqui entra só o julgamento de elegibilidade — conversões VENDA/COMPRA já corretas).
