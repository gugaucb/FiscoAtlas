# 30: Ano fechado não pode receber alteração estrutural retroativa (P0)

**What to build:** completar a guarda de ano fechado (ticket 25) para dados ESTRUTURAIS que influenciam a apuração histórica: criar/alterar/remover OpeningPosition com reference_date que possa afetar ano confirmado bloqueia ("O ano-calendário XXXX está fechado. Reabra o ano XXXX antes de alterar dados estruturais que afetam essa apuração"); alterar campos fiscalmente estruturais de BrokerAccount (ownership_type, ownership_share, is_interest_bearing) de conta que participou de ano confirmado também bloqueia. Guarda em camada reutilizável (fiscal/closing.py + model.save), não só na view — UI/outra view/service não burlam. Campos puramente descritivos (nome/apelido) permanecem editáveis. OpeningPosition futura (ex.: 31/12/2027) não é bloqueada por fechamento de 2026. Bloqueio é atômico: nada é salvo; mensagem indica o ano a reabrir.

**Blocked by:** 25 (guarda de ano fechado), 27 (lógica de relevância/patrimônio carregado).

**Status:** ready-for-agent

- [ ] Alterar OpeningPosition existente (custo 50.000→40.000) com 2026 fechado → bloqueado, valor original permanece, mensagem orienta reabrir 2026
- [ ] Criar OpeningPosition retroativa (31/12/2025) com 2026 fechado → bloqueado
- [ ] Após reabrir 2026, criar/alterar a OpeningPosition → permitido
- [ ] OpeningPosition reference_date 31/12/2027 com 2026 fechado → NÃO bloqueada
- [ ] ownership_share 100→50 com conta participante de 2026 fechado → bloqueado; após reabrir → permitido
- [ ] is_interest_bearing False→True com 2026 fechado → bloqueado (altera isenção de caixa do relatório) — ou documentado como fiscalmente neutro, sem guarda artificial
- [ ] Campos descritivos (nome/apelido) permanecem editáveis com ano fechado
- [ ] Guarda central em fiscal/closing.py reutilizando a regra do ticket 25 (sem implementação concorrente)