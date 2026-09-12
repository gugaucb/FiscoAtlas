# 29: Apuração histórica de prejuízos invariável após fechamento (P0)

**What to build:** o resultado fiscal de um ano é reproduzível independentemente das compensações efetuadas no próprio ano ou em anos posteriores: o prejuízo herdado por `TaxEngine.compute(year)` é reconstruído historicamente (amount_brl − compensações de anos ANTERIORES ao ano apurado), nunca pelo `remaining_brl` mutável do ledger. API explícita `LossLedgerService.available_at_start_of(year)` (+ composição por registro para a memória de cálculo). Ano com snapshot confirmado não pode ser fechado novamente: backend bloqueia com "O ano-calendário XXXX já está fechado. Reabra o ano antes de realizar novo fechamento"; a interface mostra Reabrir (não Fechar) quando fechado. Compute permanece read-only; reabertura (ticket 26) continua devolvendo compensações; FIFO, perdas sem source_event, source_event inativo inválido, titularidade, teto de 15% e datas fiscais inalterados.

**Blocked by:** 26 (reabrir devolve compensações), 28 (sincronização LossRecord).

**Status:** ready-for-agent

- [x] Invariância: fechar 2025 não altera `compute(2025)` (loss_inherited 1.000, taxable 0, carryforward 400)
- [ ] Invariância: compensações em 2025 e 2026 não alteram `compute(2025)` (1.000) nem `compute(2026)` (400); saldo operacional 2027 = 200
- [ ] Reabertura continua devolvendo compensações (ticket 26 não quebra)
- [ ] Fechamento de ano confirmado bloqueia no backend sem recalcular/mutar nada, com mensagem para reabrir
- [ ] Interface mostra Reabrir (não Fechar) quando o ano está fechado
- [ ] `compute()` repetido não cria/altera/remove LossRecord, LossCompensation nem AnnualAssessment