# 03: Cálculo fiscal e relatório com conversões independentes por componente

**What to build:** O cálculo do imposto devido passa a converter rendimento e imposto pago no exterior como componentes independentes — rendimento pela PTAX VENDA da data do fato gerador, imposto pela PTAX COMPRA da data do pagamento. O crédito de imposto no exterior deixa de ser superestimado (hoje usa a mesma cotação VENDA para tudo). Relatório DIRPF e memória de cálculo refletem os valores corretos.

**Blocked by:** 02 (date_rule no TaxRule).

**Status:** ready-for-agent

- [ ] Motor de cálculo trata rendimento e foreign tax como componentes independentes; não reutilizar cotação nem data de um no outro
- [ ] Rendimento bruto convertido por BCB_SELL na data do rendimento; imposto por BCB_BUY na `foreign_tax_payment_date`
- [ ] Crédito de imposto no exterior calculado com a conversão COMPRA correta; automaticamente apenas para US/FEDERAL com tax_type de imposto sobre renda; UNKNOWN fica pendente de validação
- [ ] Serviço de relatório e memória de cálculo usam as conversões separadas (comportamento idêntico em todos os pontos que hoje multiplicam por `fx` do evento)
- [ ] Testes de regressão com VENDA ≠ COMPRA em cada ponto de conversão (engine, relatório, memória)
