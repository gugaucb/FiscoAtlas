# MEMORY — Roadmap de Compliance

Log de progresso e decisões. Uma entrada por ticket (data, branch, testes, decisões, desvios do roadmap).

## Estado

- Fase 1 (P0): 1/5 concluídos
- Fase 2 (P1): 0/5 — fora do ciclo atual
- Fase 3 (P2): 0/3 — fora do ciclo atual

## Entradas

### 2026-09-07 — Ticket 01: cadastro explícito de ativos (resolved)
- Branch `fix/explicit-asset-types` @ 7d96c0e; suíte: 232 passed.
- Decisões:
  - Taxonomia legal SUBSTITUI os códigos legados (STOCK/ETF/BOND/FUND/OTHER) em `ASSET_TYPES`; migration 0007 mapeia dados antigos (STOCK→FOREIGN_EQUITY, ETF→FOREIGN_ETF, BOND→FOREIGN_BOND, FUND→FOREIGN_FUND, OTHER→UNKNOWN).
  - Rejeição de ticker inexistente implementada em DUAS camadas: EventForm (ValidationError) e EventService.record (ValueError) — a segunda cobre uso programático.
  - Bloqueio do TaxEngine no INÍCIO de compute(): consulta ativos de eventos ativos/corretores do ano; lança ValidationError ("Regime não coberto…").
  - GRUPO_CODIGO do report re-mapeado para a nova taxonomia (FOREIGN_EQUITY→03/01 etc.).
  - Desvio do roadmap: nenhum material. E2E ajustados com helper `cadastrar_ativo`.

### 2026-09-07 — Setup (ticket 00)
- Publicados 13 tickets em `issues/`, spec.md e este MEMORY.md.
- Decisões: escopo do ciclo = Fase 1; 1 ticket por Parte; juiz = suíte completa verde + critérios.
- Ponto de partida: main @ 62974ff (v0.3.0).
