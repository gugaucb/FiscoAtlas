# 06: Titularidade — OwnershipService central aplicado aos cálculos

**What to build:** A participação fiscal do titular na conta (`ownership_share`)
passa a ser aplicada nos cálculos, não só na exibição. Hoje o motor tributa o valor
integral e o relatório aplica a proporção só na exibição — incorreto. Um único
serviço central decide o fator do titular da conta (100% → 1, 50% → 0,5) e é usado
em dividendos, juros, ganhos, perdas e crédito de imposto exterior. Contas de
terceiros têm a participação definida explicitamente pelo usuário (a faixa atual não
permite 0%) — sem regra fiscal silenciosa: conta sem participação definida com
propósito fiscal bloqueia com orientação clara.

**Blocked by:** None (can start immediately).

**Status:** done (commit f01a0c5)

- [ ] Serviço central de participação do titular, usado por dividendos, juros, ganhos, perdas e crédito (teste que falha no código atual)
- [ ] Teste obrigatório: conta 50%, dividendo bruto R$ 10.000 → base atribuída R$ 5.000, IR R$ 750 (não R$ 1.500)
- [ ] Participação aplicada no crédito de imposto exterior
- [ ] Participação 0% decidida explicitamente no modelo (permitida como valor explícito, não silenciosa)
- [ ] Relatório e memória de cálculo exibem a atribuição coerente com o cálculo (uma só fonte de verdade)
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
