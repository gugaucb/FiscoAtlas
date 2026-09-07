# 08: Ledger de perdas e carryforward multianual (Parte 8 — P1)

**What to build:** LossRecord audita origem e uso de cada prejuízo: ano de origem, compensado por ano, saldo remanescente. Compensação anual FIFO de prejuízos acumulados; relatório discrimina origem.

**Requisitos:** RF-LOS-006, RF-LOS-007, CT-004, CT-005.
**Branch:** `feat/loss-ledger-carryforward`.

**Blocked by:** 07.
**Status:** ready-for-agent — Fase 2, fora do ciclo atual.

- [ ] CT-004/005: 2024 perda R$20.000, rendimentos R$5.000 → compensa 5.000, saldo 15.000; 2025 rendimentos R$10.000 → compensa 10.000, saldo 5.000 para 2026
- [ ] Relatório anual discrimina "R$ 5.000 originados em 2024"
- [ ] LossRecord criado por alienação com resultado negativo; FIFO na compensação
- [ ] Suíte completa verde
