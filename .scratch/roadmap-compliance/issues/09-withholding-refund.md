# 09: Restituição de imposto retido no exterior (Parte 9 — P1)

**What to build:** Evento WITHHOLDING_REFUND estorna retenção original e recalcula crédito aproveitável. Refund em ano posterior ao fechamento → alerta bloqueante de necessidade de retificação da DAA.

**Requisitos:** RF-FTC-009, CT-008.
**Branch:** `feat/withholding-refund`.

**Blocked by:** 08.
**Status:** ready-for-agent — Fase 2, fora do ciclo atual.

- [ ] WITHHOLDING_REFUND US$10 do mesmo ano estorna retenção e recalcula crédito
- [ ] Refund em ano subsequente fechado → alerta de retificação
- [ ] Tratado no TaxEngine e report.py
- [ ] Suíte completa verde
