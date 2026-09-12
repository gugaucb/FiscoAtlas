# 26: Reabrir ano devolve compensações de prejuízo (P0)

**What to build:** reabrir o ano X devolve o prejuízo consumido no fechamento dele: em UMA transação atômica (`select_for_update` nos LossRecord, como apply_compensation), devolve cada `LossCompensation(year=X)` ao `remaining_brl` do registro de origem, apaga as compensações e apaga o snapshot — indivisível. Bloqueio de ano posterior usa `confirmed=True`. Antes: reabrir 2025 que consumiu R$600 de prejuízo de R$1.000 deixava o saldo em R$400 e a apuração refeita enxergava prejuízo errado.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Reabrir 2025 (consumo R$600 de R$1.000) → `LossLedgerService.available(until=2025)` volta a R$1.000
- [ ] `LossCompensation(year=2025)` zerada após reabertura
- [ ] Reversão + restauração + remoção do snapshot na mesma `transaction.atomic()` (falha no meio não deixa estado parcial)
- [ ] `select_for_update()` nos LossRecord durante a devolução
- [ ] Bloqueio de anos posteriores considera apenas `AnnualAssessment(confirmed=True)`