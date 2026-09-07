# 05: Validações bloqueantes de fechamento anual (Parte 5 — P0)

**What to build:** Confirmar fechamento anual roda AnnualClosingValidator com as condições RF-VAL-001..020; qualquer violação bloqueia com mensagem explicativa na interface.

**Requisitos:** RF-VAL-001..020.
**Branch:** `feat/annual-closing-validations`.

**Blocked by:** 01, 02, 03, 04.
**Status:** resolved

- [x] Bloqueia residência != BRAZIL_RESIDENT confirmada
- [x] Bloqueia qualquer Asset UNKNOWN
- [x] Bloqueia evento com amount_brl/fx_rate nulos
- [x] Bloqueia venda acima do saldo em custódia na data
- [x] Bloqueia ForeignTaxPayment > 15% do rendimento bruto individual
- [x] Bloqueia carryforward de imposto retido no exterior
- [x] CloseYearView invoca validate_or_raise dentro de transação, com mensagens claras
- [x] Suíte completa verde
