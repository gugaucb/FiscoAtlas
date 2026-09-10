# 10: Data de recebimento para rendimentos e imposto pago no exterior

**What to build:** Fato gerador de **rendimento** passa a ser o recebimento
efetivo (ex.: dividendo negociado 31/12 mas creditado 02/01 pertence ao ano do
recebimento, conforme regra fiscal), e a PTAX do rendimento é resolvida pela data
fiscal correta — não direto pela data da operação. O imposto pago no exterior tem
sua própria data de pagamento. **Ganhos de alienação continuam usando a data da
operação (trade_date)** — mudar isso seria errado: a data da operação é o fato
gerador correto para ganhos no IRPF. Quando a data exigida não existe, o sistema
falha explicitamente (nunca fallback silencioso para a trade_date).

**Blocked by:** 04 (ForeignTaxPayment como fonte única).

**Status:** ready-for-agent

- [ ] Rendimentos: data fiscal = data de recebimento (novo campo opcional no evento; teste: dividendo 31/12 creditado 02/01 → ano do recebimento — falha no código atual)
- [ ] Imposto pago no exterior usa a própria data de pagamento (teste: crédito pago 02/01 → ano do pagamento)
- [ ] PTAX de rendimento resolvida pela data fiscal efetiva, via resolver (não trade_date direta)
- [ ] Ganhos de alienação: ano fiscal continua pela data da operação (teste de não-regressão)
- [ ] Data exigida ausente → erro explícito, sem fallback silencioso
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
