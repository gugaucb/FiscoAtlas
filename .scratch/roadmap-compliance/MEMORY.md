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

### 2026-09-07 — Ticket 06: transferências de custódia (resolved)
- Branch `feat/broker-transfers` @ 44c9959; suíte: 281 passed. Início da Fase 2 (P1).
- Decisões:
  - Transferência de ativo sai pelo CUSTO MÉDIO do momento (quantidade × média USD; proporção do custo BRL) — IN entra com o mesmo valor: custo total global preservado, custo médio idêntico nas duas contas.
  - realized() inclui transferências no walk de custo (sem apuração) para que a base do custo médio das vendas posteriores fique correta por conta.
  - Ponta solta (CT-015) verificada no AnnualClosingValidator via agregação de transfer_pair_id com n<2 pontas.
  - event_type max_length 16→32 (necessário para os novos valores).
  - Desvio do roadmap: caixa (amount_usd) transferível além de ativos — mesmo mecanismo de par.

### 2026-09-07 — Ticket 07: CBE / Banco Central (resolved)
- Branch `feat/cbe-compliance` @ 0e98a73; suíte: 288 passed.
- Decisões:
  - Valor patrimonial = posição 31/12 × CUSTO MÉDIO USD (proxy conservador) — a plataforma não registra preço de mercado; decisão documentada no serviço.
  - Caixa = soma de eventos sem ativo (APORTE − retiradas/juros/taxas), recortada até 31/12 do ano (eventos do ano seguinte não contam — CT-019 testado).
  - Abaixo de US$1M: CBE_UNDETERMINED (honesto: plataforma não vê bens externos); CBE_NOT_REQUIRED somente com declaração formal no Profile (novo campo, migration 0007 fiscal).
  - ≥ US$100M marca quarterly=True na mesma seção do relatório.
  - Desvio do roadmap: nenhum material.

### 2026-09-07 — Ticket 08: ledger granular de perdas (resolved)
- Branch `feat/loss-ledger` @ f664782; suíte: 293 passed.
- Decisões:
  - LossRecord idempotente por (origin_year, source_event): refechamento ajusta o saldo pelo DELTA do valor, preservando compensações já feitas.
  - Compensação FIFO consolidada em save_snapshot (não em compute) — compute é consulta pura/idempotente; efeitos no ledger só no fechamento. Reexecução do ano com rendimento re-aplica do saldo remanescente (trilha regravada).
  - Engine usa o ledger quando existem registros; fallback para o scalar legado do AnnualAssessment (transição).
  - Bug de infraestrutura pego no TDD: driver sqlcipher3 não registra adapter Decimal (o stdlib sqlite3 recebe um do Django em conf. de teste) — adaptado no wrapper do cursor (Decimal→str).
  - save_snapshot agora tolera linhas de detail sem evento (loss_carryforward herdado) — d["event"] None.
  - Desvio do roadmap: CT-004 numerado com perda 20.000 contra custo 5.000 é aritmeticamente inviável em uma venda; cenário multianual reimplementado com perdas 1.500+500 (mesma lógica FIFO).

### 2026-09-07 — Ticket 09: withholding refund (resolved)
- Branch `feat/withholding-refund` @ 38c707e; suíte: 298 passed.
- Decisões:
  - Estorno reduz a RETENÇÃO EFETIVA do rendimento de origem (crédito recalculado); rendimento bruto inalterado (o bruto nunca incluiu indevidamente retenção) — refund é devolução de tributo, não rendimento.
  - FK `refund_of` no FinancialEvent (migração 0011); exige origem no EventService.
  - Refund retroativo a ano FECHADO: AnnualClosingValidator do ano do estorno bloqueia com pedido de retificação da DAA de origem (CT-008). Refund no mesmo ano não bloqueia.
  - Desvio do roadmap: nenhum.

### 2026-09-07 — Ticket 10: tributação mínima de altas rendas (resolved)
- Branch `feat/high-income-min-tax` @ fdded42; suíte: 302 passed.
- Decisões:
  - Limiar testado contra a renda exterior APURADA (engine): se só esse recorte já > R$600.000 → THRESHOLD_EXCEEDED com highlight; abaixo → UNDETERMINED com mensagem instrutiva (plataforma não vê renda global).
  - Ano < 2026 → NOT_APPLICABLE.
  - Alerta avaliado no report (engine reutilizado; nenhuma duplicação de cálculo).
  - Desvio do roadmap: nenhum.

### 2026-09-07 — Ticket 11: schema versionado da DIRPF (resolved)
- Branch `feat/dirpf-schema-versioning` @ 65dd10d; suíte: 307 passed.
- Decisões:
  - DirpfSchema único por filing_year; resolução faz MERGE schema sobre defaults estáticos (campos novos de exercício futuro não quebram o relatório).
  - Trava de homologação: sem cadastro → default/HOMOLOGADO; com cadastro não homologado → PRELIMINAR exposto no relatório.
  - Desvio do roadmap: nenhum.

### 2026-09-07 — Ticket 12: importador CSV (resolved)
- Branch `feat/csv-importer` @ 269cdff; suíte: 312 passed.
- Decisões:
  - Dedup principal pelo hash SHA-256 do conteúdo do arquivo (CT-030); import atômico (transaction.atomic) — falha de linha revoga tudo.
  - Ações não suportadas (Sell/Transfer) são IGNORADAS na preview, não erro — mantém o importer minimalista; linhas de ativo não cadastrado falham com mensagem clara (RF-AST-003 se mantém).
  - Dividendo importado: per_share derivado do amount líquido (sem imposto no CSV de exemplo); tax_usd 0.
  - Desvio do roadmap: reimport idempotente retorna o batch existente com events_created=0 em vez de duplicar lote.

### 2026-09-07 — Setup (ticket 00)
- Publicados 13 tickets em `issues/`, spec.md e este MEMORY.md.
- Decisões: escopo do ciclo = Fase 1; 1 ticket por Parte; juiz = suíte completa verde + critérios.
- Ponto de partida: main @ 62974ff (v0.3.0).
