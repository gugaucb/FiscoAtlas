# 01: PTAX manual no formulário de evento

**What to build:** Quando a API do BCB não responde (ou o usuário prefere), o formulário de evento aceita PTAX manual (opcional, com motivo obrigatório). Ao lado do campo, link para o site do Banco Central (fechamento PTAX). Taxa manual tem prioridade sobre a API; fica registrada em PtaxRate como override.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] EventForm com campos ptax_manual (Decimal opcional) e ptax_reason (obrigatório se manual)
- [ ] Link para https://www.bcb.gov.br/estabilidadefinanceira/fechamentoptax ao lado do campo
- [ ] EventService.record usa a taxa manual (PtaxService.override) quando informada; API caso contrário
- [ ] Evento criado com sucesso mesmo com API indisponível (mock de falha) quando manual informada
- [ ] Sem manual e API falha → mensagem de erro amigável sugerindo a taxa manual
- [ ] Suite green
