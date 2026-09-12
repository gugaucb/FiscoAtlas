# 25: Guarda de ano fechado em toda mutação fiscal (P0)

**What to build:** existindo `AnnualAssessment(year=X, confirmed=True)`, nenhuma operação que altere fatos fiscais do ano X ocorre até o usuário reabrir explicitamente (ticket 23): cadastrar evento retroativo, corrigir evento, desativar evento, editar/criar ForeignTaxPayment e sobrescrever PTAX da data-base do ano X bloqueiam com orientação "Reabra o ano X". A guarda usa UMA função central (`assert_fiscal_year_open`) e determina o ano fiscal pela MESMA semântica do engine: SELL/CASH_IN_LIEU/demais → trade_date; DIVIDEND/JUROS → income_receipt_date (sem fallback silencioso). Correção de evento valida os DOIS anos fiscais (original e corrigido) — mover fatos de um ano fechado para outro é alterar história fechada. ForeignTaxPayment pertence fiscalmente ao ano do rendimento vinculado (income_receipt_date), não à data do pagamento.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] EventService.record() bloqueia gravação cujo ano fiscal do evento esteja fechado (confirmed=True)
- [ ] Corrigir evento bloqueia se o ano fiscal ORIGINAL ou o do evento corrigido estiver fechado (ex.: DIVIDEND recebido 31/12/2026 corrigido para 02/01/2027 com 2026 fechado → bloqueia)
- [ ] Desativar evento bloqueia se o ano fiscal dele estiver fechado
- [ ] Criar/editar ForeignTaxPayment bloqueia pelo ano fiscal do rendimento vinculado (imposto pago 02/01/2027 de rendimento recebido 31/12/2026 → ano 2026)
- [ ] PtaxService.override() bloqueia override cuja data integre ano fechado (ex.: 31/12/2026)
- [ ] Mensagem de bloqueio orienta reabrir o ano pela interface
- [ ] Regressão TDD: cada operação falha no código atual com ano fechado e passa após reabrir