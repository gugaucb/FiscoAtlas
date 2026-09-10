# 05: Crédito exterior — elegibilidade central e limites corretos

**What to build:** O crédito de imposto pago no exterior deixa de ter a retenção
>15% como erro bloqueante no fechamento do ano: uma retenção estrangeira maior
(ex.: 30% dos EUA) é legítima e deve aparecer no documento — o que a lei limita é o
*crédito aproveitável*, limitado ao IR devido, e o excedente é simplesmente não
aproveitado (não há crédito a transportar). O fechamento passa nesses casos, com o
relatório mostrando separadamente: imposto pago, elegível, aproveitado e não
aproveitado. A elegibilidade (país, nível de jurisdição, tipo de tributo,
restituibilidade, evidência documental) fica centralizada num único serviço, e não
espalhada entre engine e validador.

**Blocked by:** 04 (ForeignTaxPayment como fonte única).

**Status:** ready-for-agent

- [ ] Retenção estrangeira > 15% NÃO bloqueia mais o fechamento (teste: retenção 30%, fechamento passa — falha no código atual)
- [ ] Relatório distingue: pago / elegível / aproveitado / não aproveitado (exemplo 30 pago, 15 IR devido → 15 usado, 15 não usado)
- [ ] Serviço central de elegibilidade cobre país, jurisdição, tipo de tributo, refundability e evidência
- [ ] Fechamento bloqueia apenas para pagamento com tratamento fiscal desconhecido (UNKNOWN), com mensagem orientando a classificação
- [ ] Testes que formalizavam a regra bloqueante antiga substituídos, com documentação do porquê
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
