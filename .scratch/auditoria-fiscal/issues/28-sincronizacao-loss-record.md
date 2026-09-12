# 28: Sincronização completa do LossRecord com o resultado fiscal atual (P0)

**What to build:** o LossRecord persistido reflete o resultado fiscal ATUAL da alienação — não só "perda virou lucro": (1) SELL com perda e sem registro → cria; (2) perda muda de valor (ex.: R$1.500 → R$500 por correção do custo-base) → atualiza amount/remaining; (3) perda vira zero/lucro → remove. Se o registro tiver QUALQUER LossCompensation, não alterar silenciosamente: bloquear pedindo reabertura em cascata (ticket 26 garante o mecanismo). Arquitetura: TaxEngine.compute() fica read-only — a gravação de LossRecord (hoje em compute, engine.py:171) e a sincronização migram para o fechamento (save_snapshot/CloseYearView); consultar /apuracao/ ou gerar relatório/PDF não modifica o banco.

**Blocked by:** 25 (guarda de ano fechado), 26 (reabertura devolve compensações).

**Status:** ready-for-agent

- [x] compute() não grava LossRecord (read-only); relatório/PDF/apuração não persistem nada
- [ ] Sincronização no fechamento cria/atualiza/remove LossRecord conforme o resultado atual da venda
- [ ] Perda que muda de valor atualiza o registro (sem remaining negativo)
- [ ] Perda que vira lucro/remove registro: sem compensações → removido; com compensações → bloqueia com orientação de reabertura em cascata
- [ ] Teste TDD: correção do BUY transforma prejuízo em lucro → perda sai do ledger após novo fechamento
- [ ] Teste TDD: perda R$1.500 → R$500 com compensação anterior → bloqueia até reabrir o ano consumidor