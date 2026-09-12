# 27: Patrimônio carregado entre anos no histórico e na reconciliação (P0)

**What to build:** conta integra o histórico/reconciliação na data-base se: ativa, OU evento fiscal do ano, OU OpeningPosition até a data-base, OU posição de custódia > 0 na data-base, OU saldo de caixa ≠ 0 na data-base — independente de quando os eventos que originaram o patrimônio ocorreram. Cobre custódia E caixa carregados: (a) AAPL comprado em 2026, nada em 2027, caixa zero → exige extrato/posição documentada em 31/12/2027; (b) conta desativada sem evento em 2027 com caixa carregado de 2026 ≠ 0 → permanece no relatório e na reconciliação de 2027.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] `_conta_relevante` considera posição de custódia > 0 na data-base (PositionService), não só OpeningPosition explícita
- [ ] `historico_do_ano` inclui conta desativada com posição de custódia > 0 ou caixa ≠ 0 na data-base
- [ ] Teste TDD: AAPL 2026, sem movimento 2027, caixa zero → reconciliação 2027 exige DocumentedBalance
- [ ] Teste TDD: conta desativada com caixa carregado (sem evento no ano) → permanece no relatório 2027
- [ ] Formulários de entrada continuam restritos a contas ativas