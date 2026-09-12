# 01: Cenário rico por browser — 5 stocks + 2 ETFs em 2 contas

**What to build:** Suíte E2E Playwright que, atuando como usuário final pelo browser, cria o cenário canônico completo: perfil do contribuinte, duas contas de corretora (uma remunerada), 7 ativos cadastrados explicitamente (5 stocks FOREIGN_EQUITY e 2 ETFs FOREIGN_ETF) e um ano-calendário completo de eventos por UI. Verificável nas telas de Posições e Caixa.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Perfil criado via UI (nome, CPF, residência BRAZIL_RESIDENT)
- [ ] 2 contas criadas via UI (uma CASH simples, uma remunerada com is_interest_bearing)
- [ ] 5 stocks + 2 ETFs cadastrados via UI (ativos com tipo definido, nenhum UNKNOWN)
- [ ] Eventos por tipo no form real: aportes em ambas as contas, compras múltiplas do mesmo ativo em datas/preços distintos (custo médio ponderado visível em Posições), dividendos com retenção na fonte, venda com ganho, venda com prejuízo (outro ativo), juros (conta remunerada), taxa, retirada, split e reverse split
- [ ] Transferência de custódia: sem formulário web — semear par IN/OUT via camada de serviço (EventService/BrokerTransferService) e verificar no browser o efeito visível (posição aparece nas duas contas, custo médio preservado, sem alienação fiscal)
- [ ] Posições e Caixa conferidos por asserção browser: quantidades, custo médio USD/BRL e saldo de caixa com valores calculados manualmente no cenário
- [ ] Suíte roda headless, isolada (banco descartável) e verde; fixes reusáveis ficam no conftest de tests/e2e/