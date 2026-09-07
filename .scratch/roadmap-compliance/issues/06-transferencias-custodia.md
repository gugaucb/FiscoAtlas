# 06: Transferências de custódia entre corretoras (Parte 6 — P1)

**What to build:** Transferência de ativos/caixa entre contas do mesmo titular transporta quantidade e custo BRL integralmente, sem apuração de ganho (não é alienação). Par pareado via transfer_pair_id; sem ponta pareada → alerta.

**Requisitos:** RF-IMP-008, RF-CST-003, RF-CST-004, CT-014, CT-015.
**Branch:** `feat/broker-transfers`.

**Blocked by:** 05.
**Status:** resolved

- [x] CT-014: 100 AAPL @US$150 (R$75.000) na Conta A; transferir 40 → A fica 60 (R$45.000), B fica 40 (R$30.000)
- [x] Nenhuma alienação tributável gerada no TaxEngine/realized()
- [x] transfer_pair_id sem ponta pareada → alerta de inconsistência
- [x] Suíte completa verde
