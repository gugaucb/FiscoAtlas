# 14: Perda vinculada a evento inativo deixa de compensar

**What to build:** quando o usuário corrige/desativa uma venda com prejuízo, a perda registrada no ledger não pode mais entrar na compensação FIFO — evento desativado não é lançamento fiscal válido (a correção gera um novo evento, logo um novo LossRecord). Registros sem source_event (manual/legado) permanecem compensáveis.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] `open_records()` retorna somente registros com source_event nulo ou com evento ativo
- [ ] Regressão: venda com perda → evento desativado → perda sai de open_records/available e do loss_inherited do ano seguinte
- [ ] Regressão: compensação já feita sobre perda de evento inativo é devolvida e não re-consumida no refechamento