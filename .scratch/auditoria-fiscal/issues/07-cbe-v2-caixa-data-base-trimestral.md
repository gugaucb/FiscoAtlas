# 07: CBE v2 — caixa real, valor na data-base e quatro datas-base

**What to build:** A apuração da CBE passa a refletir o balanço real dos capitais no
exterior. (1) Caixa: em vez de somar apenas aportes/retiradas, o saldo vem do ledger
de caixa (que já considera compras, vendas, dividendos, taxas) — hoje uma compra não
reduz o caixa e o ativo entra no patrimônio, duplicando o valor. (2) Patrimônio de
ativos: valor na data-base informado pelo usuário (valor de mercado), com método e
confirmação — nunca custo médio como proxy; sem valor confirmado na data-base, o item
fica UNDETERMINED em vez de chutar. (3) Quatro datas-base apuradas separadamente:
31/03, 30/06 e 30/09 (obrigação trimestral a partir de US$ 100 milhões) e 31/12
(anual a partir de US$ 1 milhão) — o patrimônio de 31/12 nunca decide a obrigação
trimestral. Valores atribuíveis respeitam a participação do titular (ticket 06).
Testes com os dois cenários cruzados (alto em março/baixo em dezembro e vice-versa).

**Blocked by:** 06 (Titularidade — OwnershipService central).

**Status:** done

- [ ] Compra reduz o caixa e não duplica o patrimônio (teste que falha no código atual)
- [ ] Caixa vem do ledger (considera BUY, SELL, dividendos, juros, taxas) por data-base
- [ ] Valor de ativos por data-base informado e confirmado; sem valor confirmado → UNDETERMINED
- [ ] Datas-base 31/03, 30/06 e 30/09 apuradas independentes da anual de 31/12
- [ ] Testes cruzados: US$ 120M em 31/03 e US$ 80M em 31/12; US$ 80M em 31/03 e US$ 120M em 31/12 — obrigação correta em cada caso
- [ ] Referência legal exibida é Res. BCB nº 279/2022 (ticket 02)
- [ ] Participação do titular aplicada nos valores atribuíveis
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
