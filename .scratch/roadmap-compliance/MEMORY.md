# MEMORY — Roadmap de Compliance

Log de progresso e decisões. Uma entrada por ticket (data, branch, testes, decisões, desvios do roadmap).

## Estado

- Fase 1 (P0): 5/5 concluídos
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

### 2026-09-07 — Ticket 02: residência fiscal e titularidade (resolved)
- Branch `fix/tax-residency-profile` @ 8f0325f; suíte: 244 passed.
- Decisões:
  - `tax_residency_status` default UNKNOWN (honesto) → apuração bloqueada até o usuário se declarar residente pleno. Fixture compartilhada `residente` em `tests/conftest.py`; ~18 arquivos de teste receberam a pré-condição.
  - ReportService: acumuladores por conta MOVIDOS para fora do guard `if pos["quantity"]` — rendimentos de alienações que zeram posição também são atribuídos (bug detectado no TDD).
  - Atribuição proporcional: nova seção `ownership_attribution` (income/custody/cash × share%); linhas de assets/cash do DIRPF ficaram intocadas (bens do casal entram no titular no DIRPF — atribuição é demonstrativa).
  - ProfileForm: tax_residency_status não-obrigatório (default UNKNOWN) para não quebrar cadastro antigo.
  - Desvio do roadmap: relatório demonstra atribuição em seção própria em vez de reescrever as fichas Bens/Rendimentos.

### 2026-09-07 — Ticket 03: filtro FEDERAL no crédito (resolved)
- Branch `fix/foreign-tax-federal-filter` @ 5ae5016; suíte: 252 passed.
- Decisões:
  - `RECIPROCITY_COUNTRIES = {"US"}` como constante de engine (RF-FTC-002) — país+jurisdição FEDERAL; UNKNOWN não gera crédito (fato sem julgamento não vira crédito).
  - Evento legado (sem ForeignTaxPayment) mantém crédito durante a transição — punir eventos históricos mudaria apurações passadas sem base documental nova.
  - Segregação: engine agrega `ineligible_foreign_tax_brl`; report/template exibem o total não elegível e flag por linha.
  - Desvio do roadmap: nenhum.

### 2026-09-07 — Ticket 04: corporate actions (resolved)
- Branch `feat/corporate-actions-split`; suíte: 261 passed.
- Decisões:
  - Splits preservam o CUSTO TOTAL (USD e BRL), não o unitário — bug detectado no TDD: escalonar o custo pelo ratio duplicava perda de base; correto é multiplicar só a quantidade (unitário se ajusta naturalmente).
  - CASH_IN_LIEU tratado como alienação em TODAS as camadas: posição (baixa de custo + posição suficiente), realized (sale = amount_usd × PTAX) e engine (gain/loss, não rendimento) — bug de rota no engine (caía no ramo DIVIDEND) pego no TDD.
  - Razão do split obrigatória em EventService (ValueError) e EventForm/REQUIRED_BY_TYPE; sem preço/valor. UI: FIELDS JS por tipo.
  - Desvio do roadmap: nenhum material.

### 2026-09-07 — Ticket 05: validações de fechamento anual (resolved)
- Branch `feat/annual-closing-validations` @ 61e6bdc; suíte: 274 passed.
- Decisões:
  - Violações AGREGADAS: o validador coleta todas as violações e levanta ValidationError único — usuário corrige tudo de uma vez (mensagens explicativas com referência ao RF).
  - Checagem de crédito chama TaxEngine.compute(); wrap em try/except ValidationError porque o engine tem bloqueios próprios (residência, regime) que não devem mascarar o agregado do validador.
  - Carryforward de crédito proibido: retenção total > crédito efetivamente usado (teto = IR devido) bloqueia — excedente de crédito exterior não compensa em anos seguintes (Lei 14.754/2023, art. 4º).
  - Short sale: compara quantity do SELL/CASH_IN_LIEU contra PositionService.position(until=trade_date) por par conta×ativo.
  - CloseYearView: validação + snapshot dentro de transaction.atomic; erro → messages.error por violação + redirect (sem confirmed).
  - Desvio do roadmap: erro volta com redirect + mensagens (não render 200) — idempotente e testável.

### 2026-09-07 — Setup (ticket 00)
- Publicados 13 tickets em `issues/`, spec.md e este MEMORY.md.
- Decisões: escopo do ciclo = Fase 1; 1 ticket por Parte; juiz = suíte completa verde + critérios.
- Ponto de partida: main @ 62974ff (v0.3.0).
