# 04: Corporate actions — Stock Splits, Reverse Splits e Cash-in-Lieu (Parte 4 — P0)

**What to build:** Usuário registra desdobramento (2:1), grupamento (1:10) e fração em dinheiro (cash-in-lieu). Split preserva o custo total histórico em BRL; posição e venda posterior apuram ganho/perda corretamente.

**Requisitos:** RF-CA-001..003, CT-016, CT-017.
**Branch:** `feat/corporate-actions-split`.

**Blocked by:** None (can start immediately — toca ledger, independente de 01–03; executado após 03 na ordem linear).
**Status:** resolved

- [x] CT-016: 10 @ US$100 (PTAX 5 = R$5.000) + split 2:1 → 20 ações, custo BRL R$5.000, custo médio R$250
- [x] Venda de 15 ações pós-split baixa 15 × R$250 e apura ganho/perda
- [x] CT-017: reverse 1:10 com cash-in-lieu de fração gera baixa de custo e apuração proporcional
- [x] EVENT_TYPES += STOCK_SPLIT, REVERSE_SPLIT, CASH_IN_LIEU; campos split_ratio_from/to
- [x] EventService.record/EventForm aceitam splits sem exigir price_usd
- [x] Suíte completa verde
