# 11: Schema versionado da DIRPF por exercício (Parte 11 — P2)

**What to build:** Códigos de bens/direitos da DIRPF movidos de constantes estáticas para DirpfSchema versionado por filing_year. Exercício sem IN homologada → relatório com status PRELIMINAR.

**Requisitos:** RF-ARQ-002, RF-ARQ-003, RF-DIR-005, RF-DIR-013.
**Branch:** `feat/versioned-dirpf-schema`.

**Blocked by:** 10.
**Status:** resolved — Fase 3, fora do ciclo atual.

- [x] DirpfSchema por filing_year
- [x] Schema com is_homologated=False → relatório status PRELIMINAR
- [x] ReportService busca códigos no schema
- [x] Suíte completa verde
