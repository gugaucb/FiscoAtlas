# 05: Validações bloqueantes de fechamento anual (Parte 5 — P0)

**What to build:** Confirmar fechamento anual roda AnnualClosingValidator com as condições RF-VAL-001..020; qualquer violação bloqueia com mensagem explicativa na interface.

**Requisitos:** RF-VAL-001..020.
**Branch:** `feat/annual-closing-validations`.

**Blocked by:** 01, 02, 03, 04.
**Status:** ready-for-agent

- [ ] Bloqueia residência != BRAZIL_RESIDENT confirmada
- [ ] Bloqueia qualquer Asset UNKNOWN
- [ ] Bloqueia evento com amount_brl/fx_rate nulos
- [ ] Bloqueia venda acima do saldo em custódia na data
- [ ] Bloqueia ForeignTaxPayment > 15% do rendimento bruto individual
- [ ] Bloqueia carryforward de imposto retido no exterior
- [ ] CloseYearView invoca validate_or_raise dentro de transação, com mensagens claras
- [ ] Suíte completa verde
