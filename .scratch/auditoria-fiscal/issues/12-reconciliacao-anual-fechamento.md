# 12: Reconciliação anual + bloqueio no fechamento

**What to build:** Antes da apuração definitiva, um serviço de reconciliação —
**separado** do validador fiscal — responde "os dados de entrada estão completos e
conciliados?". Ele verifica: (1) importação — toda pendência de importação com
evento no ano-calendário fecha o ano (uma linha antiga pode virar pendência
descoberta depois; o critério é a data do evento, não da pendência); (2) caixa —
saldo do ledger confrontado com o saldo documental da corretora na data-base
(informado e confirmado pelo usuário); (3) posições — posição calculada confrontada
com a posição documentada em 31/12; (4) retenções — todo rendimento tributável tem
estado conhecido de imposto exterior (sem imposto ≠ retenção zero assumida
silenciosamente: exige declaração explícita); (5) eventos/atamentos fiscais
desconhecidos. O fechamento anual executa primeiro a reconciliação, depois as
regras fiscais — e só então apura e confirma o snapshot.

**Blocked by:** 01 (Importador sem omissão silenciosa), 04 (ForeignTaxPayment como fonte única).

**Status:** ready-for-agent

- [ ] Serviço de reconciliação separado do validador de fechamento (regras de importação/custódia não entram no validator fiscal)
- [ ] Pendência de importação com evento no ano-calendário → bloqueia fechamento (teste que falha no código atual — hoje nem existem pendências)
- [ ] Saldos de caixa e posições confrontados com documentos confirmados; divergência → pendência, não bloqueio silencioso nem passagem automática
- [ ] Rendimento sem imposto exterior exige estado explícito (sem retenção declarada / imposto registrado / pendência de revisão)
- [ ] Evento fiscal desconhecido → bloqueio com orientação
- [ ] CloseYearView executa: reconciliação → validação fiscal → apuração → confirmação do snapshot
- [ ] Princípio da regra de ouro respeitado (ver README do tracker)
