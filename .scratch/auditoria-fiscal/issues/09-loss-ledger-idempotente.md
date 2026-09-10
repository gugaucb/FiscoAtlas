# 09: Ledger de perdas idempotente — saldo restaurado antes de recalcular

**What to build:** Refazer o fechamento de um ano não corrompe mais o saldo de
prejuízos. Hoje o serviço apaga as compensações do ano sem devolver os valores
consumidos ao saldo das perdas antes de recalcular, podendo zerar um saldo que ainda
existia. A recomputação passa a: dentro de uma transação atômica, devolver cada
compensação existente ao registro de origem, apagar as compensações e recalcular
FIFO — com bloqueio concorrente nos registros. Se um ano anterior for recalculado e
um ano posterior já estiver fechado, o sistema bloqueia (ou exige reabertura em
cascata explícita) — nunca altera história fechada invisivelmente.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Teste de regressão: perda R$ 2.000 em 2024, lucro R$ 1.000 em 2025; fechar 2025 → saldo restante R$ 1.000; fechar 2025 de novo → saldo CONTINUA R$ 1.000 (falha no código atual)
- [ ] Saldo das perdas restaurado antes do recálculo dentro de transação atômica
- [ ] Bloqueio concorrente (select_for_update) nos registros de perda
- [ ] Recalcular ano anterior com ano posterior fechado → bloqueado (ou reabertura em cascata explícita)
- [ ] Teste de idempotência antigo (cenário sem consumo efetivo) substituído, com documentação do porquê
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
