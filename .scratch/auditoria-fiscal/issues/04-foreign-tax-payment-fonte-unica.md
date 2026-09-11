# 04: ForeignTaxPayment como fonte única — N pagamentos por evento

**What to build:** O imposto retido no exterior tem uma fonte canônica só:
`ForeignTaxPayment`. O campo duplicado `FinancialEvent.tax_usd` (marcado como
DEPRECATED) é migrado e removido. O motor fiscal lida corretamente com **vários
pagamentos de imposto para o mesmo evento** (ex.: dividendo com retenção federal e
estadual dos EUA): hoje o motor efetivamente considera apenas um. Todos os cálculos,
relatórios e memórias passam a somar todos os pagamentos por evento.

**Blocked by:** None (can start immediately).

**Status:** done (commit fb27c20)

- [ ] Engine, relatório, memória de cálculo e serviços usam somente `ForeignTaxPayment` (com teste que falha no código atual)
- [ ] Evento com 2+ pagamentos de imposto: todos aparecem e entram no cálculo do crédito (teste explícito)
- [ ] `FinancialEvent.tax_usd` migrado para `ForeignTaxPayment` e removido do modelo
- [ ] Formulário de pagamento de imposto exterior permite editar os fatos necessários (incluindo país e valor)
- [ ] Testes existentes que formalizavam a fonte duplicada substituídos, com documentação do porquê
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
