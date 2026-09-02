# 01: Entidade ForeignTaxPayment com data fiscal e fonte documental próprias

**What to build:** Ao registrar um evento financeiro com imposto pago no exterior (ex.: dividendo da Avenue com withholding EUA), o sistema passa a representar o imposto como entidade própria vinculada ao evento — com data de pagamento, jurisdição, tipo de tributo e fonte documental independentes da data do rendimento. Não existe legado: não criar migração de `tax_usd` antigo, nem fallback baseado na data do evento, nem status de revisão por legado. O modelo correto nasce direto.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] Modelo `ForeignTaxPayment` relacionado 0..N a `FinancialEvent`, com: `tax_usd`, `foreign_tax_payment_date`, `country_code`, `jurisdiction_level`, `tax_type`, `capture_method`, `date_evidence_source`, `source_document_id`, `source_reference`, timestamps
- [ ] Enum `jurisdiction_level`: FEDERAL / STATE / LOCAL / UNKNOWN
- [ ] Enum `tax_type`: WITHHOLDING_INCOME_TAX / INCOME_TAX / OTHER / UNKNOWN (somente imposto sobre renda alimenta o crédito)
- [ ] Enum `capture_method`: IMPORT / MANUAL / SYSTEM — separado de `date_evidence_source`: BROKER_STATEMENT / BROKER_TAX_REPORT / USER_PROVIDED_DOCUMENT / OTHER_DOCUMENT / USER_CONFIRMED / UNKNOWN
- [ ] Campos `tax_usd`, `foreign_tax_payment_date`, `country_code`, `jurisdiction_level`, `tax_type` obrigatórios para o registro valer como crédito fiscal
- [ ] Fallback automático de data proibido: sem `foreign_tax_payment_date`, o sistema exige a data ou confirmação explícita de que coincide com a data do rendimento — erro explícito, nunca silencioso
- [ ] Datas de rendimento e de imposto são independentes: podem coincidir, desde que por evidência documental registrada
- [ ] Crédito fiscal automático somente para country_code=US e jurisdiction_level=FEDERAL; UNKNOWN fica com status PENDING_VALIDATION, sem crédito automático
- [ ] Registro do evento com `tax_usd > 0` cria o `ForeignTaxPayment` correspondente
- [ ] Testes: criação de retenção com data própria; erro sem data; 0..N retenções por evento
