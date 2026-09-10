# 13: Suíte adversarial de regressão fiscal

**What to build:** Suíte dedicada de testes de regressão fiscal cobrindo a matriz de
cenários abaixo — cada teste com **valores esperados calculados explicitamente**
(nunca comparar dois métodos do próprio sistema) e que **falharia no código
anterior** à correção correspondente:

| Cenário | Resultado obrigatório |
|---|---|
| Duas corretoras com o mesmo ativo | abertura e custo independentes |
| Posição de abertura por conta | nenhuma duplicação |
| CSV com SELL | venda importada ou pendência bloqueante |
| CSV com evento desconhecido | nunca desaparecer silenciosamente |
| CBE 31/03 / 30/06 / 30/09 / 31/12 | cada data-base apurada independente |
| Perda 2.000 → uso 1.000 → refechar | saldo continua 1.000 |
| Conta 50% | imposto e rendimento em 50% |
| Retenção exterior 30% | fechamento passa; crédito limitado |
| DARF R$ 9,99 | não paga agora; saldo preservado (adiamento) |
| DARF R$ 99 | quota única |
| DARF R$ 100 | mínimo de quota respeitado |
| DARF R$ 300 | nº válido de quotas |
| Trade 31/12 / recebimento 02/01 | ano definido pela regra fiscal |
| 2 pagamentos de imposto no mesmo rendimento | ambos aparecem e são calculados |
| Imposto exterior com classificação UNKNOWN | fechamento bloqueado até classificar |

**Blocked by:** 03, 04, 05, 06, 07, 08, 09 (suíte exercita os cenários corrigidos).

**Status:** ready-for-agent

- [ ] Suíte dedicada criada (ex.: testes de auditoria fiscal separados dos testes unitários existentes)
- [ ] Todos os cenários da matriz cobertos com valores esperados explícitos calculados à mão
- [ ] Cada teste documenta a qual correção do backlog corresponde e por que o comportamento anterior estava errado
- [ ] Suíte verde completa na ponta da fronteira (todos os blockers fechados)
