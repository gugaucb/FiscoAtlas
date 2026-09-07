# 01: Cadastro explícito de ativos e fim da auto-inferência silenciosa (Parte 1 — P0)

**What to build:** Usuário cadastra ativos explicitamente (ticker, descrição, natureza jurídica, confirmação de não-controle) antes de lançar eventos. EventForm rejeita ticker inexistente em vez de criar STOCK silenciosamente. TaxEngine bloqueia apuração de ativos CONTROLLED_ENTITY/TRUST/UNKNOWN ou entidades controladas.

**Requisitos:** RF-AST-003, RF-AST-006, RF-AST-007, RF-AST-009, RF-ARQ-006, RF-VAL-002.
**Branch:** `fix/explicit-asset-types`.

**Blocked by:** None (can start immediately).
**Status:** resolved

- [ ] EventForm rejeita com ValidationError ticker não cadastrado (fim do get_or_create implícito)
- [ ] Asset suporta FOREIGN_EQUITY, FOREIGN_ETF, REIT, US_TREASURY, FOREIGN_BOND, FOREIGN_FUND, CONTROLLED_ENTITY, TRUST, UNKNOWN
- [ ] Asset tem is_controlled_entity (bool) e ownership_share_pct (decimal, default 0)
- [ ] TaxEngine.compute lança ValidationError explicativo para legal_asset_type in (CONTROLLED_ENTITY, TRUST, UNKNOWN) ou is_controlled_entity=True
- [ ] AssetForm + view/template de cadastro explícito (descrição, natureza jurídica, não-controle)
- [ ] Suíte completa verde
