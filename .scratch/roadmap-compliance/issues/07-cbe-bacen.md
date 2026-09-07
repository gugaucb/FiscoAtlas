# 07: CBE / Banco Central (Parte 7 — P1)

**What to build:** Serviço avalia patrimônio em 31/12 (caixa + custódia) e retorna status: CBE_REQUIRED (≥ US$1M, anual), alerta trimestral (≥ US$100M), CBE_NOT_REQUIRED (completude declarada), CBE_UNDETERMINED (sem confirmação de completude).

**Requisitos:** RF-CBE-001..007, CT-019, CT-020, CT-021.
**Branch:** `feat/cbe-compliance`.

**Blocked by:** 06.
**Status:** ready-for-agent — Fase 2, fora do ciclo atual.

- [ ] CT-019: US$999.999 sem flag de completude → CBE_UNDETERMINED
- [ ] US$999.999 com external_assets_declared_complete=True → CBE_NOT_REQUIRED
- [ ] CT-020: US$1.000.000 → CBE_REQUIRED
- [ ] ≥ US$100.000.000 → alerta de obrigação trimestral
- [ ] Integrado ao ReportService e tela de encerramento
- [ ] Suíte completa verde
