# 10: Tributação mínima de altas rendas 2026 (Parte 10 — P1)

**What to build:** HighIncomeService verifica gatilho da Lei 15.270/2025: < 2026 inativo; 2026 com rendimentos exterior R$100k → UNDETERMINED instrutivo; > R$600k → THRESHOLD_EXCEEDED com alerta na DAA.

**Requisitos:** RF-HI-001..004, CT-024, CT-025.
**Branch:** `feat/high-income-tax-2026`.

**Blocked by:** 09.
**Status:** ready-for-agent — Fase 2, fora do ciclo atual.

- [ ] tax_year < 2026 → módulo não acionado
- [ ] CT-024: 2026, R$100.000 exterior → HIGH_INCOME_TEST_UNDETERMINED com instrução
- [ ] CT-025: 2026, > R$600.000 → HIGH_INCOME_THRESHOLD_EXCEEDED com alerta
- [ ] Exposto no relatório anual
- [ ] Suíte completa verde
