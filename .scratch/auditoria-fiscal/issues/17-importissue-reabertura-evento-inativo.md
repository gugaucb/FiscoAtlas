# 17: Reconciliação reabre RESOLVED_IMPORTED com evento inativo; re-vinculação ao substituto

**What to build:** ciclo completo da pendência de importação: se o evento vinculado a um `RESOLVED_IMPORTED` é corrigido (desativado) ou a vinculação desaparece, a pendência volta a ser bloqueante na reconciliação anual (mesmo critério de data das PENDING) e pode ser re-vinculada ao evento substituto pela tela de pendências, sem SQL manual. A regra é computada no momento da reconciliação — o status gravado não é mutado de volta para PENDING; `resolve_imported` permite re-vinculação quando o evento atual está inativo, e a trilha (`resolution`/`resolved_at`) registra a nova vinculação.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Reconciliação reporta como bloqueante `RESOLVED_IMPORTED` com `resolved_event=None` ou `resolved_event.active=False` (data do evento no ano-calendário, mesmo critério das PENDING)
- [x] Pendência reaberta pode ser re-vinculada ao evento substituto pela tela existente (`resolve_imported` sem SQL manual)
- [x] Regressão: issue resolvido → evento desativado → reconciliação bloqueia; re-vinculação ao substituto → fechamento passa (falha no código atual)