# 12: Ingestão automatizada de extratos CSV com deduplicação (Parte 12 — P2)

**What to build:** Upload de CSV de corretoras (Schwab/Avenue) com preview, criação de eventos e idempotência: reimportar o mesmo arquivo (hash + identificadores) não duplica eventos. ImportBatch registra file_hash/data/contagem.

**Requisitos:** RF-IMP-001..004, CT-030.
**Branch:** `feat/csv-importer`.

**Blocked by:** 11.
**Status:** ready-for-agent — Fase 3, fora do ciclo atual.

- [ ] Importa CSV de exemplo Schwab (1 compra + 1 dividendo) com eventos corretos
- [ ] CT-030: reimport do mesmo arquivo → zero eventos novos
- [ ] ImportBatch com file_hash
- [ ] View/upload com pré-visualização
- [ ] Suíte completa verde
