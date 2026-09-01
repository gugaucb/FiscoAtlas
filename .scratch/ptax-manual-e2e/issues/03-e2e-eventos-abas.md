# 03: E2E browser — 8 tipos de evento + abas

**What to build:** Bateria Playwright preenchendo os 8 tipos de evento (APORTE, WITHDRAWAL, BUY, SELL, DIVIDEND, JUROS, FEE, TAX_WITHHELD) pelo formulário real e validando Eventos, Posições e Caixa com valores esperados (quantidades, custo médio, saldos USD).

**Blocked by:** 01 (PTAX manual), 02 (Playwright infra).

**Status:** resolved

- [ ] Um cenário por tipo de evento (form real no browser, com PTAX manual onde necessário)
- [ ] Aba Eventos lista os 8 eventos com datas/valores
- [ ] Aba Posições: quantidade e custo médio corretos após BUY/SELL
- [ ] Aba Caixa: saldo USD correto (aportes − retiradas − taxas + juros)
- [ ] Dividendos/TAX_WITHHELD aparecem com withholding para a apuração
