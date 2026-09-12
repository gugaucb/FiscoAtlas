# 03: Multi-ano por browser — carry-forward, guarda de ano fechado e reabertura

**What to build:** Extensão do cenário para o ano 2027 como usuário final pelo browser: prejuízo do ano fechado 2026 compensa automaticamente na apuração 2027; tentativas de edição retroativa pela UI são bloqueadas com a mensagem do ticket 30; reabrir 2026 devolve prejuízos e permite corrigir e fechar de novo. É o teste de regressão browser da guarda estrutural.

**Blocked by:** 02 (ano 2026 fechado com valores conhecidos).

**Status:** ready-for-agent

- [ ] Apuração 2027 usa o saldo de prejuízo carregado de 2026 (base = rendimentos 2027 − carry-forward, com valor esperado explícito)
- [ ] Edição retroativa bloqueada por UI: corrigir evento do ano fechado, override de PTAX, criar/alterar posição de abertura afetando 2026, alterar titularidade/is_interest_bearing — todas mostram "Reabra o ano 2026…"; campo descritivo (apelido) permanece editável
- [ ] Reabrir ano 2026 via UI (confirm digitando o ano) devolve prejuízos consumidos; reabertura de ano anterior a um ano posterior fechado é bloqueada
- [ ] Após reabrir, corrigir um dado e fechar 2026 novamente funciona; apuração 2027 recalcula com o novo arrasto
- [ ] Posições de abertura com data futura não são bloqueadas pelo fechamento de ano anterior