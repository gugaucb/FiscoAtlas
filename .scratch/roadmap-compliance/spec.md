# Roadmap de Compliance — Fase 1 (P0)

Fonte: `roadmap.md` (13 partes, 3 fases). Referência legal: Lei 14.754/2023 e IN RFB 2.180/2024.

## Decisões

- **Escopo do ciclo atual:** Fase 1 (P0, Partes 1–5). Partes 6–13 publicadas como `ready-for-agent`, mas marcadas "Fase 2/3 — fora do ciclo atual".
- **Granularidade:** 1 ticket por Parte (13 tickets 1:1 com o checklist do roadmap).
- **Método:** orquestrador/juiz + TDD. Cada ticket em branch própria; juiz = suíte completa verde + critérios de aceitação; progresso em `MEMORY.md`.
- **Estado de partida:** main @ 62974ff (tag v0.3.0 — PTAX por componente). Premissas do roadmap verificadas: auto-criação STOCK em EventForm ativa; Profile só name/cpf; sem filtro FEDERAL no crédito; PositionService só BUY/SELL; sem validator de fechamento.

## Ordem de execução (blockers)

01 → (02, 04 em paralelo conceitual, 03 bloqueado por 02) → 05 bloqueado por 01..04.
Cadeia linear executada: 01, 02, 03, 04, 05.
