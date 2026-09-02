# 02: date_rule no TaxRule + resolver de data fiscal + PTAX COMPRA para o imposto

**What to build:** O motor tributário passa a resolver a data fiscal e o tipo de cotação por componente, via `TaxRule`: cada componente (compra de ativo, venda, dividendo, juros/cupom, imposto pago no exterior) declara `date_rule` e `quote_type` independentes. O serviço de PTAX recebe a data já resolvida e o tipo BCB (VENDA/COMPRA). Imposto pago no exterior usa PTAX COMPRA na `foreign_tax_payment_date` — nunca a data do rendimento, nunca PTAX VENDA.

**Blocked by:** 01 (Entidade ForeignTaxPayment).

**Status:** ready-for-agent

- [ ] Campo `date_rule` em `TaxRule`, separado de `quote_type`; enum: ACQUISITION_DATE / DISPOSAL_DATE / INCOME_RECEIPT_DATE / FOREIGN_TAX_PAYMENT_DATE / REFERENCE_DATE
- [ ] Regras do seed: compra de ativo = ACQUISITION_DATE + BCB_SELL; venda = DISPOSAL_DATE + BCB_SELL; dividendo/juros/cupom = INCOME_RECEIPT_DATE + BCB_SELL; imposto exterior = FOREIGN_TAX_PAYMENT_DATE + BCB_BUY
- [ ] Resolver de data fiscal (`TaxDateResolver`) recebe evento, pagamento de imposto e regra, devolve a data efetiva; `PtaxService.get_rate(date, quote_type)` consumido só com data resolvida
- [ ] `BUY`/`SELL` da operação NÃO implicam BCB_BUY/BCB_SELL da cotação
- [ ] Teste obrigatório: dividendo 10/03/2026 US$100 + imposto 12/03/2026 US$30 → rendimento BCB_SELL 10/03, imposto BCB_BUY 12/03; teste falha se qualquer componente usar a data ou cotação do outro
- [ ] Teste com datas iguais (10/03 e 10/03): rendimento BCB_SELL, imposto BCB_BUY — cotações continuam distintas
